"""HTML section renderer for price-aware betting strategies."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from html import escape

from soccer_prediction.models import Allocation, BettingStrategy

__all__ = ["strategy_section"]


def _money(value: Decimal | None) -> str:
    return "—" if value is None else f"${value:.2f}"


def _prob(value: Decimal | None) -> str:
    return "—" if value is None else f"{value:.1%}"


def _table(heading: str, headers: tuple[str, ...], rows: Sequence[tuple[str, ...]]) -> str:
    head = "".join(f"<th>{escape(value)}</th>" for value in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(value)}</td>" for value in row) + "</tr>" for row in rows
    )
    return (
        f'<h2>{escape(heading)}</h2><div class="card"><table><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
    )


def _allocations(strategy: BettingStrategy) -> str:
    allocated: dict[str, Allocation] = {item.evaluation.quote.key: item for item in strategy.allocations}
    rows: list[tuple[str, ...]] = []
    for item in strategy.evaluations:
        position = allocated.get(item.quote.key)
        rows.append(
            (
                f"{item.quote.market}: {item.quote.selection}",
                _prob(item.model_probability),
                _money(item.quote.ask),
                _money(item.fair_price),
                _money(item.max_buy_price),
                _money(item.net_edge),
                _money(position.amount if position else Decimal(0)),
                str(position.contracts if position else 0),
                _money(position.maximum_loss if position else Decimal(0)),
                _money(position.gross_payout if position else Decimal(0)),
                _money(position.net_profit_if_win if position else Decimal(0)),
                item.reason,
                item.intent,
            )
        )
    intro = (
        f'<p class="foot">Venue <strong>{escape(strategy.venue)}</strong>; quote observed '
        f'{escape(strategy.quote_observed_at.isoformat())}; plan {escape(strategy.request.plan)}; '
        f'cash retained {_money(strategy.uninvested_cash)}.</p>'
    )
    return intro + _table(
        "Betting value & bankroll allocation",
        (
            "Market / score", "Model", "Ask", "Fair", "Max buy", "Net edge", "Allocated", "Contracts",
            "Max loss", "Gross", "Net win", "Reason", "Intent",
        ),
        rows,
    )


def _live(strategy: BettingStrategy) -> str:
    rows: list[tuple[str, ...]] = []
    for item in strategy.live_scores:
        stages = []
        for stage in item.stages:
            stages.append(
                f"m{stage.minute} {stage.minute_range}: fair {_money(stage.fair_value)}, "
                f"bid {_money(stage.current_bid)} x {stage.bid_depth}, limit {_money(stage.target_price)}, "
                f"now {'yes' if stage.executable_now else 'no'}, sell {stage.fraction:.0%}/{stage.contracts}, "
                f"cash if filled {_money(stage.cash_received)}, P/L {_money(stage.profit_locked)}"
            )
        rows.append(
            (item.score, "yes" if item.position_active else "no", *stages, item.goal_before_fill,
             f"{item.next_home_score} or {item.next_away_score}")
        )
    return _table(
        "Live correct-score exit ladder",
        ("Score", "Active", "First", "Second", "Final", "Goal before fill", "Next scores"),
        rows,
    )


def _paths(strategy: BettingStrategy) -> str:
    rows = [
        (
            item.path,
            item.score,
            _money(item.stage_cash),
            _money(item.cumulative_cash),
            _money(item.active_position_costs),
            _money(item.realized_profit),
            "yes" if item.individual_recovered else "no",
            "yes" if item.active_positions_recovered else "no",
            "yes" if item.full_bankroll_recovered else "no",
            "/".join("yes" if value else "no" for value in (
                item.fixed_profit_025, item.fixed_profit_050, item.fixed_profit_100
            )),
        )
        for item in strategy.path_ledger
    ]
    return _table(
        "Major scoring paths & capital recovery",
        (
            "Path", "Score", "Stage cash", "Cumulative", "Active costs", "P/L", "Position",
            "Active", "Full bankroll", "+.25/+.50/+1",
        ),
        rows,
    )


def _presets(strategy: BettingStrategy) -> str:
    rows = []
    for item in strategy.presets:
        allocations = "; ".join(
            f"{position.evaluation.quote.selection}: {_money(position.amount)} / {position.contracts}"
            for position in item.allocations
        ) or "none — retain cash"
        rows.append(
            (item.name, _money(item.reserve), _money(item.deployed), _money(item.uninvested_cash),
             _money(item.maximum_loss), "/".join(f"{value:.0%}" for value in item.exit_fractions), allocations)
        )
    return _table(
        "Conservative, balanced & aggressive plans",
        ("Plan", "Reserve", "Deployed", "Cash", "Max loss", "Exit percentages", "Allocations"),
        rows,
    )


def strategy_section(strategy: BettingStrategy | None) -> str:
    """Return the full optional strategy section."""
    if strategy is None:
        return ""
    warnings = "".join(f"<li>{escape(value)}</li>" for value in strategy.warnings)
    rule = (
        '<h2>Execution rule &amp; risk limits</h2><div class="card"><ul>' + warnings +
        "<li>Buy only at or below the maximum reported buy price; sell only against an executable bid "
        "at or above the staged limit.</li><li>Stage cash is conditional on a full fill; current bid and depth "
        "determine the ‘now’ flag.</li><li>Unfilled orders are not recovered cash. Refresh after every goal.</li>"
        "</ul></div>"
    )
    return _allocations(strategy) + _live(strategy) + _paths(strategy) + _presets(strategy) + rule
