"""Report section: spread a fixed bankroll across correct-score grids.

Renders one square score matrix per goal cap (0-1, 0-2, 0-3, 0-4), each with a
live risk slider. Every tile carries the score's probability, its stake, what it
pays if it is the final score, and -- reading the grid *live* -- how much of the
book is already dead at that score versus still reachable.

The slider re-shapes the money in the browser: 0% stakes proportional to price
(flat, every covered score returns the same), 100% stakes proportional to the
model's probabilities (bigger payouts on the scores it likes, smaller elsewhere).
"""

from __future__ import annotations

import json
from html import escape
from importlib import resources
from pathlib import Path

from soccer_prediction.models import MatchForecast
from soccer_prediction.reporting.html_components import _pct
from soccer_prediction.strategy.score_hedge import (
    DEFAULT_RISK,
    GridHedgePlan,
    ScoreGrid,
    ScoreStake,
    build_grid_hedges,
    load_score_grid,
)

__all__ = ["score_hedge_section"]

_CAPS = (1, 2, 3, 4)

# Recomputes a grid in the browser when its risk slider moves. Mirrors
# strategy.score_hedge.build_grid_hedge exactly: stake = bankroll * ((1-r) *
# price_share + r * prob_share), payout = stake / price. Server-rendered values
# are the slider's default, so the page is correct before this ever runs.
_HEDGE_SCRIPT = """<script>
(function () {
  var money = function (v) { return '$' + v.toFixed(2); };
  var signed = function (v) { return (v >= 0 ? '+$' : '-$') + Math.abs(v).toFixed(2); };
  document.querySelectorAll('.sgrid[data-cells]').forEach(function (grid) {
    var cells = JSON.parse(grid.dataset.cells);
    var bankroll = parseFloat(grid.dataset.bankroll);
    var cap = grid.dataset.cap;
    var slider = document.querySelector('input.risk-slider[data-cap="' + cap + '"]');
    if (!slider) { return; }
    var priceSum = cells.reduce(function (s, c) { return s + c.price; }, 0);
    var probSum = cells.reduce(function (s, c) { return s + c.prob; }, 0);
    var stat = function (key) {
      return document.querySelector('[data-stat="' + key + '"][data-cap="' + cap + '"]');
    };
    var setText = function (el, text) { if (el) { el.textContent = text; } };
    var setClass = function (el, cls) {
      if (el) { el.className = el.className.replace(/\\b(pos|neg)\\b/g, '').trim() + ' ' + cls; }
    };
    function render(risk) {
      var priced = cells.map(function (c) {
        var share = (1 - risk) * (c.price / priceSum) + risk * (c.prob / probSum);
        var stake = bankroll * share;
        var payout = stake / c.price;
        return { h: c.h, a: c.a, prob: c.prob, stake: stake, payout: payout, net: payout - bankroll };
      });
      var worst = Infinity, best = -Infinity, ev = 0, pwin = 0;
      priced.forEach(function (p) {
        worst = Math.min(worst, p.net); best = Math.max(best, p.net);
        ev += p.prob * p.payout; pwin += p.prob;
      });
      priced.forEach(function (p) {
        var dead = 0, lo = null, hi = null;
        priced.forEach(function (q) {
          if (q.h === p.h && q.a === p.a) { return; }
          if (q.h < p.h || q.a < p.a) { dead += q.stake; }
          else {
            lo = (lo === null) ? q.net : Math.min(lo, q.net);
            hi = (hi === null) ? q.net : Math.max(hi, q.net);
          }
        });
        var el = grid.querySelector('.scell[data-h="' + p.h + '"][data-a="' + p.a + '"]');
        if (!el) { return; }
        setText(el.querySelector('.sc-bet'), 'bet ' + money(p.stake));
        setText(el.querySelector('.sc-win'), 'win ' + money(p.payout));
        setText(el.querySelector('.sc-lost'), 'LOST -' + money(dead));
        setText(el.querySelector('.sc-poss'),
          lo === null ? 'POSSIBLE none' : 'POSSIBLE (' + signed(lo) + ', ' + signed(hi) + ')');
        setText(el.querySelector('.sc-loss'), 'this -' + money(p.stake));
        var net = el.querySelector('.sc-net');
        setText(net, 'net ' + signed(p.net));
        setClass(net, p.net >= 0 ? 'pos' : 'neg');
      });
      setText(stat('worst'), signed(worst));
      setClass(stat('worst'), worst >= 0 ? 'pos' : 'neg');
      setText(stat('best'), signed(best));
      setClass(stat('best'), best >= 0 ? 'pos' : 'neg');
      setText(stat('ev'), signed(ev - bankroll));
      setClass(stat('ev'), ev - bankroll >= 0 ? 'pos' : 'neg');
      setText(stat('arb'), worst > 0 ? 'yes' : 'no');
      setText(stat('pwin'), (pwin * 100).toFixed(1) + '%');
      setText(stat('plose'), ((1 - pwin) * 100).toFixed(1) + '%');
    }
    slider.addEventListener('input', function () {
      var risk = parseInt(slider.value, 10) / 100;
      setText(document.querySelector('.risk-value[data-cap="' + cap + '"]'), slider.value + '%');
      render(risk);
    });
    render(parseInt(slider.value, 10) / 100);
  });
})();
</script>"""


def score_hedge_section(forecast: MatchForecast) -> str:
    """Render the per-grid staking squares, or say why they are missing."""
    grid = _load_fixture_grid(forecast)
    if grid is None:
        return _missing_grid_note(forecast)
    plans = build_grid_hedges(grid, caps=_CAPS, risk=DEFAULT_RISK)
    cards = "".join(_plan_card(grid, plan) for plan in plans)
    return (
        "<h2>Score-grid staking plans</h2>"
        '<div class="card"><p class="sub">'
        f"Each plan spreads <strong>${grid.bankroll:.0f}</strong> across every exact score inside a goal "
        "cap. The <strong>risk slider</strong> on each grid re-shapes the money live: at "
        "<strong>0%</strong> stakes follow the prices, so every covered score returns the same - flat, "
        "opinion-free, and an arbitrage whenever the prices sum under 1.00. At <strong>100%</strong> they "
        "follow the model's probabilities, paying far more on the scores it likes and under the stake on "
        "the rest. <strong>Max loss is the whole bankroll</strong> whenever the real score escapes the "
        "grid - including any 5+ score, which no plan here can cover."
        "</p>"
        f"{_comparison_table(plans)}"
        f"{cards}"
        '<p class="foot">Prices are the market percentages as displayed in the app. Rows marked '
        "<em>est.</em> are scores never visible in the screenshots (assumed 1%, matching every 4-goal "
        "score that is visible). Real fills can cost more than the screen: two payout quotes "
        "(0-3: $20&rarr;$645; 3-3: $100&rarr;$4,879) imply about +1.1pp on those longshots, which would "
        "thin every profit below. Not betting advice.</p></div>"
        f"{_HEDGE_SCRIPT}"
    )


def _comparison_table(plans: tuple[GridHedgePlan, ...]) -> str:
    """A one-look summary of every grid at the default risk setting."""
    rows = "".join(
        f"<tr><td><strong>0-{plan.max_goals}</strong></td>"
        f'<td class="n">{len(plan.stakes)}</td>'
        f'<td class="n">{plan.total_price:.3f}</td>'
        f'<td class="n">{_pct(plan.covered_probability)}</td>'
        f'<td class="n">{_pct(1.0 - plan.covered_probability)}</td>'
        f'<td class="n {"pos" if plan.guaranteed_profit >= 0 else "neg"}">${plan.guaranteed_profit:+.2f}</td>'
        f'<td class="n {"pos" if plan.max_profit >= 0 else "neg"}">${plan.max_profit:+.2f}</td>'
        f'<td class="n neg">-${plan.bankroll:.2f}</td>'
        f'<td class="n {"pos" if plan.expected_profit >= 0 else "neg"}">${plan.expected_profit:+.2f}</td></tr>'
        for plan in plans
    )
    header = (
        '<thead><tr><th>Grid</th><th class="n">Scores</th><th class="n">Price sum</th>'
        '<th class="n">P(win)</th><th class="n">P(lose)</th>'
        '<th class="n">Worst net</th><th class="n">Best net</th>'
        '<th class="n">Max loss</th><th class="n">Expected</th></tr></thead>'
    )
    return (
        f"<h3>All grids at a glance <span class=\"prior-badge\">risk {DEFAULT_RISK * 100:.0f}%</span></h3>"
        '<div style="overflow-x:auto"><table>'
        f"{header}<tbody>{rows}</tbody></table></div>"
    )


def _risk_control(plan: GridHedgePlan) -> str:
    """The per-grid slider: flat price-shaped money at 0, model-shaped at 100."""
    cap = plan.max_goals
    value = int(round(plan.risk * 100))
    return (
        '<div class="risk-control">'
        f'<label class="risk-label" for="risk-{cap}">Risk</label>'
        '<span class="risk-end">flat</span>'
        f'<input class="risk-slider" type="range" id="risk-{cap}" data-cap="{cap}" '
        f'min="0" max="100" step="5" value="{value}" '
        f'aria-label="Risk for the {cap}-goal-cap plan: 0 percent spreads by price, 100 by model probability">'
        '<span class="risk-end">follow model</span>'
        f'<span class="risk-value" data-cap="{cap}">{value}%</span>'
        "</div>"
    )


def _plan_card(grid: ScoreGrid, plan: GridHedgePlan) -> str:
    caption = (
        f"Every cell is one exact score: <strong>{grid.home} goals down the side, {grid.away} goals "
        f"across the top</strong>. <strong>bet</strong> is that cell's slice of the ${plan.bankroll:.0f}, "
        f"<strong>win</strong> the cash back if that score is final, and <strong>net</strong> the win "
        f"minus the ${plan.bankroll:.0f} you staked. Drag <strong>risk</strong> to re-shape every number "
        "below."
        '</p><p class="sub2">'
        "The other two read the grid <strong>live, as the game stands at that score</strong>. Goals only "
        "go up, so a final score is still reachable only if both tallies are at least the current ones: "
        '<strong class="lost-key">LOST</strong> is the stake on cells that can no longer happen whatever '
        'follows, and <strong class="poss-key">POSSIBLE (min, max)</strong> is the range of net you could '
        "still finish on from here. Standing at 2-0, every 0-x and 1-x cell is already dead while 2-1 and "
        "2-2 still play; at the far corner nothing is left, so POSSIBLE reads none. Anything outside the "
        f"square loses all ${plan.bankroll:.0f}."
    )
    return (
        f"<h3>0-{plan.max_goals} grid &mdash; {len(plan.stakes)} scores</h3>"
        f'<p class="sub2">{caption}</p>'
        f"{_risk_control(plan)}"
        f"{_score_square(grid, plan)}"
        f"{_summary(plan)}"
    )


def _summary(plan: GridHedgePlan) -> str:
    cap = plan.max_goals
    worst = _signed(plan.guaranteed_profit)
    best = _signed(plan.max_profit)
    return (
        '<div class="hedge-summary">'
        f"{_stat('Total staked', f'${plan.bankroll:.2f}')}"
        f"{_stat('Worst net (covered)', worst, cap, 'worst', _sign(plan.guaranteed_profit))}"
        f"{_stat('Best net (covered)', best, cap, 'best', _sign(plan.max_profit))}"
        f"{_stat('Most you can lose', f'-${plan.bankroll:.2f}', None, None, 'neg')}"
        f"{_stat('P(win)', _pct(plan.covered_probability), cap, 'pwin')}"
        f"{_stat('P(lose it all)', _pct(1.0 - plan.covered_probability), cap, 'plose')}"
        f"{_stat('Expected profit', _signed(plan.expected_profit), cap, 'ev', _sign(plan.expected_profit))}"
        f"{_stat('Arbitrage', 'yes' if plan.is_true_arbitrage else 'no', cap, 'arb')}"
        "</div>"
    )


def _sign(value: float) -> str:
    return "pos" if value >= 0 else "neg"


def _signed(value: float) -> str:
    """Format money with the sign outside the dollar sign: +$4.28 / -$3.85."""
    return f"{'+' if value >= 0 else '-'}${abs(value):.2f}"


def _stat(
    label: str,
    value: str,
    cap: int | None = None,
    key: str | None = None,
    value_class: str = "",
) -> str:
    cls = f" {value_class}" if value_class else ""
    hook = f' data-stat="{key}" data-cap="{cap}"' if key is not None and cap is not None else ""
    return (
        '<div class="hedge-stat">'
        f'<span class="hedge-stat-k">{escape(label)}</span>'
        f'<span class="hedge-stat-v{cls}"{hook}>{value}</span></div>'
    )


def _score_square(grid: ScoreGrid, plan: GridHedgePlan) -> str:
    """Lay the plan out as a real score matrix: home goals x away goals.

    Cells are shaded by probability -- the likeliest score is solid blue and the
    longshots fade to the card background -- so the plan's shape is readable at a
    glance instead of needing a 25-row list. The raw price/probability of every
    cell rides along as JSON so the risk slider can re-price the grid in place.
    """
    stakes = {(stake.home_goals, stake.away_goals): stake for stake in plan.stakes}
    peak = max((stake.probability for stake in plan.stakes), default=1.0) or 1.0
    size = plan.max_goals + 1
    columns = f"grid-template-columns:34px repeat({size},minmax(96px,1fr));"
    max_width = 34 + size * 116
    cells = ['<div class="scell blank"></div>']
    cells += [f'<div class="scell axis">{goals}</div>' for goals in range(size)]
    for home_goals in range(size):
        cells.append(f'<div class="scell axis">{home_goals}</div>')
        for away_goals in range(size):
            cells.append(
                _square_cell(stakes.get((home_goals, away_goals)), grid, home_goals, away_goals, peak, stakes)
            )
    payload = escape(
        json.dumps(
            [
                {
                    "h": stake.home_goals,
                    "a": stake.away_goals,
                    "price": round(stake.price, 6),
                    "prob": round(stake.probability, 6),
                }
                for stake in plan.stakes
            ],
            separators=(",", ":"),
        ),
        quote=True,
    )
    legend = (
        '<div class="sgrid-legend" role="img" aria-label="Shading scale: white least likely, blue most likely">'
        '<div class="sgrid-gradient"></div><div class="heat-labels">'
        f"<span>least likely</span><span>most likely ({_pct(peak)})</span></div></div>"
    )
    return (
        f'<p class="sgrid-axis">{escape(grid.away)} goals &rarr;</p>'
        '<div class="sgrid-side">'
        f'<span class="sgrid-side-label">{escape(grid.home)} goals &darr;</span>'
        '<div class="sgrid-wrap">'
        f'<div class="sgrid" data-cap="{plan.max_goals}" data-bankroll="{plan.bankroll:.4f}" '
        f'data-cells="{payload}" style="{columns}max-width:{max_width}px">{"".join(cells)}</div>'
        f"</div></div>{legend}"
    )


def _square_cell(
    stake: ScoreStake | None,
    grid: ScoreGrid,
    home_goals: int,
    away_goals: int,
    peak: float,
    stakes: dict[tuple[int, int], ScoreStake],
) -> str:
    """One score tile: what it pays, and what is dead or reachable from here.

    Money lines:
      * ``win``      - gross cash back if this exact score is final.
      * ``LOST``     - stake on cells unreachable from this score (goals only go
        up), already gone no matter what happens next.
      * ``POSSIBLE`` - the (min, max) net still reachable from here, or none at
        the far corner where no other score can follow.
      * ``this``     - this cell's own stake, lost if the game moves on.
    """
    if stake is None:  # defensive: a full grid always funds every cell
        return '<div class="scell blank"></div>'
    # Shade linearly against the grid's own likeliest score, floored so the
    # rarest cell still reads as a cell rather than blank card.
    share = min(1.0, max(0.0, stake.probability / peak))
    strength = 6.0 + 88.0 * share
    emphasis = " strong" if share >= 0.62 else ""
    est = '<span class="sc-est">est.</span>' if stake.estimated_price else ""
    dead, live = _live_split(stakes, home_goals, away_goals)
    live_text = (
        "POSSIBLE none" if live is None else f"POSSIBLE ({_signed(live[0])}, {_signed(live[1])})"
    )
    tooltip = (
        f"{home_goals}-{away_goals} {_result_label(home_goals, away_goals, grid)} "
        f"(probability {stake.probability * 100:.1f}%, price {stake.price * 100:.1f}%): "
        f"bet ${stake.stake:.2f}. If it is the final score you get ${stake.payout_if_hit:.2f} back, "
        f"netting ${stake.profit_if_hit:+.2f}. Standing here, ${dead:.2f} of bets can no longer be "
        f"reached (goals only go up)"
        + (
            "; no other score can follow."
            if live is None
            else f", and the net still reachable ranges from ${live[0]:+.2f} to ${live[1]:+.2f}."
        )
    )
    return (
        f'<div class="scell prob{emphasis}" data-h="{home_goals}" data-a="{away_goals}" '
        f'style="--strength:{strength:.0f}%" title="{escape(tooltip)}">'
        f'<span class="sc-score">{home_goals}-{away_goals}</span>'
        f'<span class="sc-prob">{_pct(stake.probability)}</span>'
        f'<span class="sc-bet">bet ${stake.stake:.2f}</span>'
        f'<span class="sc-win">win ${stake.payout_if_hit:.2f}</span>'
        f'<span class="sc-lost">LOST -${dead:.2f}</span>'
        f'<span class="sc-poss">{live_text}</span>'
        f'<span class="sc-loss">this -${stake.stake:.2f}</span>'
        f'<span class="sc-net {_sign(stake.profit_if_hit)}">net ${stake.profit_if_hit:+.2f}</span>'
        f"{est}</div>"
    )


def _live_split(
    stakes: dict[tuple[int, int], ScoreStake], home_goals: int, away_goals: int
) -> tuple[float, tuple[float, float] | None]:
    """Split the other cells at this score into dead stake and the reachable net range.

    Football scores only go up, so standing at ``home_goals-away_goals`` a final
    score is reachable only if both teams' tallies are at least the current ones.
    Everything else is already lost, however the rest of the match unfolds.
    Returns ``(dead_stake, (min_net, max_net))`` over the other reachable cells,
    or ``(dead_stake, None)`` at the far corner where no other score can follow.
    """
    dead = 0.0
    reachable_nets: list[float] = []
    for (cell_home, cell_away), other in stakes.items():
        if (cell_home, cell_away) == (home_goals, away_goals):
            continue
        if cell_home < home_goals or cell_away < away_goals:
            dead += other.stake
        else:
            reachable_nets.append(other.profit_if_hit)
    if not reachable_nets:
        return dead, None
    return dead, (min(reachable_nets), max(reachable_nets))


def _result_label(home_goals: int, away_goals: int, grid: ScoreGrid) -> str:
    if home_goals > away_goals:
        return f"{grid.home} win"
    if away_goals > home_goals:
        return f"{grid.away} win"
    return "Draw"


def _missing_grid_note(forecast: MatchForecast) -> str:
    """Explain that this fixture has no market prices, and name the file it needs."""
    home = forecast.fixture.home_team
    away = forecast.fixture.away_team
    filename = f"correct_score_{home.casefold().replace(' ', '_')}_{away.casefold().replace(' ', '_')}.yaml"
    return (
        "<h2>Score-grid staking plans</h2>"
        '<div class="card"><p class="sub">No market prices are bundled for '
        f"{escape(home)} vs {escape(away)}, so there is nothing to stake against here. "
        "The staking grids need real correct-score quotes, not model probabilities - pricing a plan "
        "off the model alone would just be betting into its own guesses.</p>"
        f'<p class="foot">To enable this section, add <code>soccer_prediction/example/data/{escape(filename)}</code> '
        "with a <code>displayed</code> percentage and model <code>probability</code> per scoreline "
        "(see <code>correct_score_argentina_england.yaml</code> for the format).</p></div>"
    )


def _load_fixture_grid(forecast: MatchForecast) -> ScoreGrid | None:
    """Resolve ``correct_score_<home>_<away>.yaml`` for the fixture, if bundled."""
    data = resources.files("soccer_prediction.example").joinpath("data")
    home = forecast.fixture.home_team.casefold().replace(" ", "_")
    away = forecast.fixture.away_team.casefold().replace(" ", "_")
    for key in (f"{home}_{away}", f"{away}_{home}"):
        resource = data.joinpath(f"correct_score_{key}.yaml")
        if resource.is_file():
            with resources.as_file(resource) as path:
                return load_score_grid(Path(path))
    return None
