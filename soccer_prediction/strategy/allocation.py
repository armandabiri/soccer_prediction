"""Deterministic bankroll allocation under liquidity and exposure limits."""

from __future__ import annotations

from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from soccer_prediction.models import Allocation, ContractEvaluation, StrategyRequest
from soccer_prediction.strategy.presets import reserve_percentage

__all__ = ["allocate_bankroll"]

CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _floor_step(value: Decimal, step: Decimal) -> Decimal:
    if value <= 0:
        return Decimal(0)
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


def allocate_bankroll(
    evaluations: tuple[ContractEvaluation, ...],
    request: StrategyRequest,
    *,
    plan: str | None = None,
) -> tuple[tuple[Allocation, ...], Decimal]:
    """Allocate eligible contracts greedily by net edge and return residual cash."""
    preset = request.plan if plan is None else plan
    reserve = _money(request.bankroll * reserve_percentage(preset, request))
    deploy_limit = request.bankroll - reserve
    single_score_limit = request.bankroll * Decimal("0.30")
    score_pool_limit = request.bankroll * Decimal("0.60")
    deployed = Decimal(0)
    score_deployed = Decimal(0)
    allocations: list[Allocation] = []
    eligible = [item for item in evaluations if item.eligible and item.net_edge is not None]
    eligible.sort(key=lambda item: (item.net_edge or Decimal(0), item.quote.key), reverse=True)
    for item in eligible:
        if item.all_in_cost is None or item.all_in_cost <= 0:
            continue
        quote = item.quote
        available_cash = deploy_limit - deployed
        if quote.market == "correct_score":
            available_cash = min(available_cash, single_score_limit, score_pool_limit - score_deployed)
        quantity = _floor_step(available_cash / item.all_in_cost, quote.quantity_step)
        quantity = min(quantity, _floor_step(quote.available_at_ask, quote.quantity_step))
        while quantity > 0 and _money(quantity * item.all_in_cost) > available_cash:
            quantity -= quote.quantity_step
        if quantity <= 0:
            continue
        amount = _money(quantity * item.all_in_cost)
        allocation = Allocation(
            evaluation=item,
            amount=amount,
            contracts=quantity,
            maximum_loss=amount,
            gross_payout=_money(quantity),
            net_profit_if_win=_money(quantity - amount),
        )
        allocations.append(allocation)
        deployed += amount
        if quote.market == "correct_score":
            score_deployed += amount
    return tuple(allocations), _money(request.bankroll - deployed)
