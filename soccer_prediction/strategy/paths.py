"""Pathwise cash-flow and capital-recovery ledgers."""

from __future__ import annotations

from decimal import Decimal

from soccer_prediction.models import Allocation, LiveScorePlan, PathLedgerRow

__all__ = ["simulate_score_paths"]

_PATHS = (
    ("0-0", "1-0", "1-1", "2-1", "2-2"),
    ("0-0", "0-1", "1-1", "1-2", "2-2"),
    ("0-0", "1-0", "2-0"),
    ("0-0", "0-1", "0-2"),
)


def simulate_score_paths(
    live_scores: tuple[LiveScorePlan, ...],
    allocations: tuple[Allocation, ...],
    bankroll: Decimal,
) -> tuple[PathLedgerRow, ...]:
    """Replay required paths with first-stage fills before each next goal."""
    plans = {item.score: item for item in live_scores}
    positions = {
        item.evaluation.quote.selection: item
        for item in allocations
        if item.evaluation.quote.market == "correct_score"
    }
    score_portfolio_cost = sum((item.amount for item in positions.values()), Decimal(0))
    rows: list[PathLedgerRow] = []
    for path_values in _PATHS:
        path = " → ".join(path_values)
        cumulative = Decimal(0)
        for index, score in enumerate(path_values):
            plan = plans.get(score)
            position = positions.get(score)
            if plan is None or position is None:
                stage_cash = Decimal(0)
            elif index == len(path_values) - 1:
                stage_cash = sum((stage.cash_received for stage in plan.stages), Decimal(0))
            else:
                stage_cash = plan.stages[0].cash_received
            cumulative += stage_cash
            profit = cumulative - score_portfolio_cost
            individual_cost = position.amount if position else Decimal(0)
            rows.append(
                PathLedgerRow(
                    path=path,
                    score=score,
                    stage_cash=stage_cash,
                    cumulative_cash=cumulative,
                    active_position_costs=score_portfolio_cost,
                    realized_profit=profit,
                    individual_recovered=position is not None and stage_cash >= individual_cost,
                    active_positions_recovered=score_portfolio_cost > 0 and cumulative >= score_portfolio_cost,
                    full_bankroll_recovered=cumulative >= bankroll,
                    fixed_profit_025=profit >= Decimal("0.25"),
                    fixed_profit_050=profit >= Decimal("0.50"),
                    fixed_profit_100=profit >= Decimal("1.00"),
                )
            )
    return tuple(rows)

