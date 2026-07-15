"""Report section: distribute a fixed bankroll across a correct-score grid.

Renders the equal-payout "guarantee a win if any covered score happens" hedge
for the 0-3 and 0-2 goal grids, and -- because a guarantee that ignores how
often the real score falls outside the grid is misleading -- pairs it with the
model-weighted probability of winning and the resulting expected profit.
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


def score_hedge_section(forecast: MatchForecast) -> str:
    """Render the $500 correct-score hedge plans, or empty when no price grid exists."""
    grid = _load_fixture_grid(forecast)
    if grid is None:
        return ""
    plans = build_grid_hedges(grid, caps=(3, 2))
    intro = (
        "<h2>Guaranteed-win score hedge - $500</h2>"
        '<div class="card"><p class="sub">'
        f"Spread <strong>${grid.bankroll:.0f}</strong> across every exact score inside a goal cap so "
        "that <strong>whichever covered score lands, the payout is identical</strong> (stake is set "
        "proportional to each contract price). The 0-3 plan covers all 16 scores with no side above 3; "
        "the 0-2 plan covers the 9 scores with no side above 2 - fewer scores, bigger payout, but a "
        "larger chance the real score escapes the grid. "
        "<strong>Read the expected profit, not just the guarantee:</strong> the plan only pays if the "
        "final score is actually inside the grid, and the model's outcome probabilities price that in."
        "</p>"
        f"{_plan_card(grid, plans[0])}"
        f"{_plan_card(grid, plans[1])}"
        '<p class="foot">Contracts settle at $1.00 each. A plan is a real arbitrage only when its prices '
        "sum below 1.00; even then, expected profit turns negative once the chance of an uncovered score "
        "is large enough. Prices flagged <em>est.</em> were scrolled off the screenshots and filled from "
        "the model - replace them with the real market percentages before staking. Not betting advice.</p>"
        "</div>"
    )
    return intro


def _plan_card(grid: ScoreGrid, plan: GridHedgePlan) -> str:
    arb = "yes" if plan.is_true_arbitrage else "no"
    ev_class = "pos" if plan.expected_profit >= 0 else "neg"
    guaranteed_class = "pos" if plan.guaranteed_profit >= 0 else "neg"
    guaranteed = f"${plan.guaranteed_profit:+.2f} ({plan.guaranteed_roi * 100:+.1f}%)"
    summary = (
        '<div class="hedge-summary">'
        f"{_stat('Scores covered', str(len(plan.stakes)))}"
        f"{_stat('Price sum', f'{plan.total_price:.3f}')}"
        f"{_stat('Guaranteed return', f'${plan.guaranteed_return:.2f}')}"
        f"{_stat('Guaranteed profit', guaranteed, guaranteed_class)}"
        f"{_stat('P(win) - covered', _pct(plan.covered_probability))}"
        f"{_stat('Expected profit', f'${plan.expected_profit:+.2f}', ev_class)}"
        f"{_stat('True arbitrage', arb)}"
        "</div>"
    )
    rows = "".join(_stake_row(stake, grid) for stake in plan.stakes)
    header = (
        "<thead><tr><th>Score</th><th>Result</th><th class=\"n\">Price</th>"
        '<th class="n">Model prob</th><th class="n">Stake</th>'
        '<th class="n">Contracts</th><th class="n">Value edge</th></tr></thead>'
    )
    return (
        f"<h3>{escape(plan.label)}</h3>"
        '<div style="overflow-x:auto"><table>'
        f"{header}<tbody>{rows}</tbody></table></div>"
        f"{summary}"
    )


def _stake_row(stake: ScoreStake, grid: ScoreGrid) -> str:
    badge = '<span class="prior-badge" title="Filled from the model, not the screenshots">est.</span>'
    est = f" {badge}" if stake.estimated_price else ""
    edge_class = "pos" if stake.value_edge >= 0 else "neg"
    result = _result_label(stake.home_goals, stake.away_goals, grid)
    return (
        f"<tr><td>{stake.home_goals}-{stake.away_goals}{est}</td>"
        f"<td>{escape(result)}</td>"
        f'<td class="n">{_pct(stake.price)}</td>'
        f'<td class="n">{_pct(stake.probability)}</td>'
        f'<td class="n">${stake.stake:.2f}</td>'
        f'<td class="n">{stake.contracts:.1f}</td>'
        f'<td class="n {edge_class}">{stake.value_edge * 100:+.1f}%</td></tr>'
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
