"""Report section: spread a fixed bankroll across correct-score grids.

Renders one table per goal cap (0-1, 0-2, 0-3, 0-4). Each row carries the score's
probability and the stake it takes; each grid carries the headline numbers --
most you can lose, most you can profit, and the probability-weighted expectation
that decides whether the plan is worth placing at all.
"""

from __future__ import annotations

from html import escape
from importlib import resources
from pathlib import Path

from soccer_prediction.models import MatchForecast
from soccer_prediction.reporting.html_components import _pct
from soccer_prediction.strategy.score_hedge import (
    GridHedgePlan,
    ScoreGrid,
    ScoreStake,
    build_grid_hedges,
    load_score_grid,
)

__all__ = ["score_hedge_section"]

_CAPS = (1, 2, 3, 4)


def score_hedge_section(forecast: MatchForecast) -> str:
    """Render the per-grid bankroll tables, or say why they are missing.

    Staking grids need real market prices, which only exist for fixtures with a
    bundled ``correct_score_<home>_<away>.yaml``. Rather than vanish silently
    (which reads as a broken report), an unpriced fixture gets a short note
    naming the file it would need.
    """
    grid = _load_fixture_grid(forecast)
    if grid is None:
        return _missing_grid_note(forecast)
    plans = build_grid_hedges(grid, caps=_CAPS)
    cards = "".join(_plan_card(grid, plan) for plan in plans)
    return (
        "<h2>Score-grid staking plans</h2>"
        '<div class="card"><p class="sub">'
        f"Each plan spreads <strong>${grid.bankroll:.0f}</strong> across every exact score inside a goal "
        "cap, staking proportional to price so <strong>every covered score returns the same amount</strong>. "
        "Wider grids win more often but pay less; tighter grids pay more but miss more. "
        "<strong>Max loss is the whole bankroll</strong> whenever the real score escapes the grid - "
        "including any 5+ score, which no plan here can cover."
        "</p>"
        f"{_comparison_table(plans)}"
        f"{cards}"
        '<p class="foot">Prices are the market percentages as displayed in the app. A plan only profits '
        "when they sum below 1.00 - and even then the expected value can be negative once the chance of "
        "an uncovered score is counted. Rows marked <em>est.</em> are scores never visible in the "
        "screenshots (assumed 1%, matching every 4-goal score that is visible). Note real fills can cost "
        "more than the screen: two payout quotes (0-3: $20&rarr;$645; 3-3: $100&rarr;$4,879) imply about "
        "+1.1pp on those longshots, which would thin every profit below - "
        "<code>score_optimizer</code> can re-run any plan on that pessimistic view. Not betting "
        "advice.</p></div>"
    )


def _comparison_table(plans: tuple[GridHedgePlan, ...]) -> str:
    """A one-look summary of every grid: cost, upside, downside, expectation."""
    rows = "".join(
        f"<tr><td><strong>0-{plan.max_goals}</strong></td>"
        f'<td class="n">{len(plan.stakes)}</td>'
        f'<td class="n">{plan.total_price:.3f}</td>'
        f'<td class="n">{_pct(plan.covered_probability)}</td>'
        f'<td class="n">{_pct(1.0 - plan.covered_probability)}</td>'
        f'<td class="n {"pos" if plan.guaranteed_profit >= 0 else "neg"}">'
        f"${plan.guaranteed_profit:+.2f}</td>"
        f'<td class="n neg">-${plan.bankroll:.2f}</td>'
        f'<td class="n {"pos" if plan.expected_profit >= 0 else "neg"}">'
        f"${plan.expected_profit:+.2f}</td></tr>"
        for plan in plans
    )
    header = (
        "<thead><tr><th>Grid</th><th class=\"n\">Scores</th><th class=\"n\">Price sum</th>"
        '<th class="n">P(win)</th><th class="n">P(lose)</th>'
        '<th class="n">Max profit</th><th class="n">Max loss</th>'
        '<th class="n">Expected</th></tr></thead>'
    )
    return (
        "<h3>All grids at a glance</h3>"
        '<div style="overflow-x:auto"><table>'
        f"{header}<tbody>{rows}</tbody></table></div>"
    )


def _plan_card(grid: ScoreGrid, plan: GridHedgePlan) -> str:
    profit_class = "pos" if plan.guaranteed_profit >= 0 else "neg"
    ev_class = "pos" if plan.expected_profit >= 0 else "neg"
    summary = (
        '<div class="hedge-summary">'
        f"{_stat('Total staked', f'${plan.bankroll:.2f}')}"
        f"{_stat('Most you can profit', f'${plan.guaranteed_profit:+.2f}', profit_class)}"
        f"{_stat('Most you can lose', f'-${plan.bankroll:.2f}', 'neg')}"
        f"{_stat('P(win)', _pct(plan.covered_probability))}"
        f"{_stat('P(lose it all)', _pct(1.0 - plan.covered_probability))}"
        f"{_stat('Expected profit', f'${plan.expected_profit:+.2f}', ev_class)}"
        f"{_stat('Arbitrage', 'yes' if plan.is_true_arbitrage else 'no')}"
        "</div>"
    )
    caption = (
        f"Every cell is one exact score: <strong>{grid.home} goals down the side, {grid.away} goals "
        f"across the top</strong>. <strong>bet</strong> is that cell's slice of the ${plan.bankroll:.0f}; "
        f"<strong>win</strong> is the cash back if that score lands (${plan.guaranteed_return:.2f} - the "
        f"same from any cell, which is the point); <strong>others</strong> is the stake on every other "
        f"cell, lost the instant this one lands; <strong>this</strong> is that cell's own stake, lost if "
        f"any other score lands. <strong>net</strong> = win minus the ${plan.bankroll:.0f} you put in. "
        f"Anything outside the square loses all ${plan.bankroll:.0f}."
    )
    return (
        f"<h3>0-{plan.max_goals} grid &mdash; {len(plan.stakes)} scores</h3>"
        f'<p class="sub2">{caption}</p>'
        f"{_score_square(grid, plan)}"
        f"{summary}"
    )


def _score_square(grid: ScoreGrid, plan: GridHedgePlan) -> str:
    """Lay the plan out as a real score matrix: home goals x away goals.

    Cells are shaded by probability -- the likeliest score is solid blue and the
    longshots fade to the card background -- so the plan's shape is readable at a
    glance instead of needing a 25-row list.
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
                _square_cell(
                    stakes.get((home_goals, away_goals)), grid, home_goals, away_goals, peak, plan.bankroll
                )
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
        f'<div class="sgrid" style="{columns}max-width:{max_width}px">{"".join(cells)}</div>'
        f"</div></div>{legend}"
    )


def _square_cell(
    stake: ScoreStake | None,
    grid: ScoreGrid,
    home_goals: int,
    away_goals: int,
    peak: float,
    bankroll: float,
) -> str:
    """One score tile: what it pays if it lands, and what dies either way.

    Three money lines, per the plan's two possible worlds:
      * ``win``    - gross cash back if this exact score lands.
      * ``others`` - the stake on every *other* cell, dead the moment this lands.
      * ``this``   - this cell's own stake, dead if any other score lands.
    ``win`` minus the bankroll is the net, shown underneath.
    """
    if stake is None:  # defensive: a full grid always funds every cell
        return '<div class="scell blank"></div>'
    # Shade linearly against the grid's own likeliest score, floored so the
    # rarest cell still reads as a cell rather than blank card.
    share = min(1.0, max(0.0, stake.probability / peak))
    strength = 6.0 + 88.0 * share
    emphasis = " strong" if share >= 0.62 else ""
    est = '<span class="sc-est">est.</span>' if stake.estimated_price else ""
    others_lost = max(0.0, bankroll - stake.stake)
    net_class = "pos" if stake.profit_if_hit >= 0 else "neg"
    tooltip = (
        f"{home_goals}-{away_goals} {_result_label(home_goals, away_goals, grid)} "
        f"(probability {stake.probability * 100:.1f}%, price {stake.price * 100:.1f}%): "
        f"bet ${stake.stake:.2f}. If it lands you get ${stake.payout_if_hit:.2f} back while the other "
        f"${others_lost:.2f} of bets lose, netting ${stake.profit_if_hit:+.2f}. "
        f"If any other score lands, this ${stake.stake:.2f} is lost."
    )
    return (
        f'<div class="scell prob{emphasis}" style="--strength:{strength:.0f}%" title="{escape(tooltip)}">'
        f'<span class="sc-score">{home_goals}-{away_goals}</span>'
        f'<span class="sc-prob">{_pct(stake.probability)}</span>'
        f'<span class="sc-bet">bet ${stake.stake:.2f}</span>'
        f'<span class="sc-win">win ${stake.payout_if_hit:.2f}</span>'
        f'<span class="sc-loss">others -${others_lost:.2f}</span>'
        f'<span class="sc-loss">this -${stake.stake:.2f}</span>'
        f'<span class="sc-net {net_class}">net ${stake.profit_if_hit:+.2f}</span>'
        f"{est}</div>"
    )


def _result_label(home_goals: int, away_goals: int, grid: ScoreGrid) -> str:
    if home_goals > away_goals:
        return f"{grid.home} win"
    if away_goals > home_goals:
        return f"{grid.away} win"
    return "Draw"


def _stat(label: str, value: str, value_class: str = "") -> str:
    cls = f" {value_class}" if value_class else ""
    return (
        '<div class="hedge-stat">'
        f'<span class="hedge-stat-k">{escape(label)}</span>'
        f'<span class="hedge-stat-v{cls}">{value}</span></div>'
    )


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
