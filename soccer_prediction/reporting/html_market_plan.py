"""HTML rendering for YAML-backed, price-aware market allocations."""

from __future__ import annotations

from html import escape

from soccer_prediction.reporting.html_components import _dot, _pct
from soccer_prediction.reporting.market_optimizer import MarketPlan

__all__ = ["render_market_plan"]


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _side_color(side: str) -> str:
    if side == "home":
        return "var(--home)"
    if side == "away":
        return "var(--away)"
    return "var(--draw)"


def render_market_plan(plan: MarketPlan) -> str:
    """Render selected positive-edge offers sorted by allocated bankroll."""
    rows = []
    for item in plan.allocations:
        color = _side_color(item.side)
        rows.append(
            f'<tr style="background:color-mix(in srgb,{color} 12%,transparent)">'
            f"<td>{escape(item.category)}</td>"
            f"<td>{_dot(color)}{escape(item.market)}</td>"
            f"<td>{escape(item.selection)}</td>"
            f'<td class="n">{_pct(item.model_probability)}</td>'
            f'<td class="n">{_pct(item.ask)}</td>'
            f'<td class="n">{_pct(item.edge)}</td>'
            f'<td class="n">{_money(item.win_profit)}</td>'
            f'<td class="n">{_pct(item.win_roi)}</td>'
            f'<td class="n">{_pct(item.loss_probability)}</td>'
            f'<td class="n">{_money(item.stake)}</td>'
            f'<td class="n">{_money(item.expected_profit)}</td></tr>'
        )
    deployed = sum(item.stake for item in plan.allocations)
    expected = sum(item.expected_profit for item in plan.allocations)
    if rows:
        body = "".join(rows)
    else:
        body = '<tr><td colspan="11">No configured price has positive model edge after the safety threshold.</td></tr>'
    return (
        '<h2>Most confident markets - $100 price-aware bankroll</h2><div class="card">'
        '<p class="sub">Fixture prices are loaded from YAML and compared with model probabilities. '
        f'The allocation objective weights expected return <strong>{plan.profit_weight:.0%}</strong> '
        f'and win-probability safety <strong>{plan.risk_weight:.0%}</strong>. Only positive-edge '
        "contracts are funded; each position is capped and a small cash reserve is held.</p>"
        '<div class="cmap-legend">'
        f'<span>{_dot("var(--home)")}Home-side selection</span>'
        f'<span>{_dot("var(--away)")}Away-side selection</span>'
        f'<span>{_dot("var(--draw)")}Neutral / draw selection</span>'
        "</div>"
        '<div style="overflow-x:auto"><table><thead><tr>'
        "<th>Category</th><th>Market</th><th>Selection</th>"
        '<th class="n">Model</th><th class="n">Price</th><th class="n">Edge</th>'
        '<th class="n">Profit/$1 win</th><th class="n">Win ROI</th><th class="n">Loss risk</th>'
        '<th class="n">Stake</th><th class="n">Expected profit</th>'
        f"</tr></thead><tbody>{body}</tbody></table></div>"
        f'<p class="foot">Source: <code>{escape(plan.source)}</code>. Deployed '
        f"<strong>{_money(deployed)}</strong>; cash held "
        f"<strong>{_money(plan.bankroll - deployed)}</strong>; portfolio expected profit "
        f"<strong>{_money(expected)}</strong>. {plan.rejected} configured offers were excluded "
        "because the model had no matching probability or the price did not clear the minimum edge. "
        "A 59-cent winner earns 41 cents per contract, which is 69.5% ROI on the 59 cents invested "
        "before fees. Prices and forecasts can change and profit is not guaranteed.</p></div>"
    )
