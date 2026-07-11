"""Conditional current-score valuation and staged live exits."""

from __future__ import annotations

import math
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from soccer_prediction.models import (
    Allocation,
    ContractEvaluation,
    ExitStage,
    LiveMatchContext,
    LiveScorePlan,
    MatchForecast,
    StrategyRequest,
)
from soccer_prediction.strategy.presets import exit_fractions

__all__ = ["build_live_exit_ladder"]

CENT = Decimal("0.01")
_MINUTES = (55, 70, 82)
_RANGES = ("45-60", "61-75", "76-90+")
_LABELS = ("first", "second", "final")
_REQUIRED = ((0, 0), (1, 0), (0, 1), (1, 1), (2, 0), (0, 2), (2, 1), (1, 2), (2, 2))


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _floor_step(value: Decimal, step: Decimal) -> Decimal:
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step if value > 0 else Decimal(0)


def _expected_goals(forecast: MatchForecast) -> tuple[float, float]:
    grid = forecast.correct_score
    home = sum(index * sum(row) for index, row in enumerate(grid.probabilities))
    away = sum(
        index * sum(row[index] for row in grid.probabilities)
        for index in range(grid.away_goals_max + 1)
    )
    return home, away


def _modal_score(forecast: MatchForecast) -> tuple[int, int]:
    best = max(
        ((prob, home, away) for home, row in enumerate(forecast.correct_score.probabilities)
         for away, prob in enumerate(row)),
        key=lambda item: item[0],
    )
    return best[1], best[2]


def _states(forecast: MatchForecast) -> tuple[tuple[int, int], ...]:
    modal_home, modal_away = _modal_score(forecast)
    grid = forecast.correct_score
    max_home = min(grid.home_goals_max - 1, max(2, modal_home + 2))
    max_away = min(grid.away_goals_max - 1, max(2, modal_away + 2))
    values = set(_REQUIRED)
    values.update((home, away) for home in range(max_home + 1) for away in range(max_away + 1))
    return tuple(sorted(values, key=lambda item: (sum(item), item[0], item[1])))


def _fair_at_minute(
    home_mean: float,
    away_mean: float,
    score: tuple[int, int],
    minute: int,
    context: LiveMatchContext,
) -> Decimal:
    regulation = 90 + context.added_minutes
    remaining = max(0.0, float(regulation - minute) / 90.0)
    home_rate = home_mean * float(context.home_rate_multiplier)
    away_rate = away_mean * float(context.away_rate_multiplier)
    home_rate *= 0.85 ** context.home_red_cards * 1.10 ** context.away_red_cards
    away_rate *= 0.85 ** context.away_red_cards * 1.10 ** context.home_red_cards
    home_goals, away_goals = score
    if home_goals != away_goals:
        if context.leading_team_defending:
            if home_goals > away_goals:
                home_rate *= 0.90
            else:
                away_rate *= 0.90
        if context.trailing_team_pressure:
            if home_goals < away_goals:
                home_rate *= 1.10
            else:
                away_rate *= 1.10
    tempo = context.injury_multiplier * context.substitution_multiplier * context.pressure_multiplier
    rate = (home_rate + away_rate) * float(tempo)
    return Decimal(str(math.exp(-rate * remaining)))


def _target(fair: Decimal, margin: Decimal, tick: Decimal) -> Decimal:
    value = min(Decimal("0.99"), max(tick, fair - margin / Decimal(2)))
    return (value / tick).to_integral_value(rounding=ROUND_DOWN) * tick


def _stages(
    allocation: Allocation | None,
    evaluation: ContractEvaluation | None,
    request: StrategyRequest,
    context: LiveMatchContext,
    means: tuple[float, float],
    score: tuple[int, int],
) -> tuple[ExitStage, ...]:
    quote = evaluation.quote if evaluation is not None else None
    tick = quote.tick_size if quote else CENT
    sell_fee = quote.sell_fee_rate if quote else Decimal(0)
    step = quote.quantity_step if quote else Decimal(1)
    total = allocation.contracts if allocation else Decimal(0)
    cost = allocation.amount if allocation else Decimal(0)
    remaining = total
    stages: list[ExitStage] = []
    fractions = exit_fractions(request.plan)
    values = zip(_LABELS, _MINUTES, _RANGES, fractions, strict=True)
    for index, (label, minute, minute_range, fraction) in enumerate(values):
        quantity = remaining if index == 2 else _floor_step(total * fraction, step)
        remaining -= quantity
        fair = _fair_at_minute(*means, score, minute, context)
        target = _target(fair, request.safety_margin, tick)
        cash = _money(quantity * target * (Decimal(1) - sell_fee))
        allocated_cost = _money(cost * quantity / total) if total > 0 else Decimal(0)
        current_bid = quote.bid if quote else None
        bid_depth = quote.available_at_bid if quote else Decimal(0)
        executable_now = current_bid is not None and current_bid >= target and bid_depth >= quantity
        stages.append(
            ExitStage(
                label, minute_range, minute, fair, current_bid, bid_depth, target, executable_now,
                fraction, quantity, cash, cash - allocated_cost,
            )
        )
    return tuple(stages)


def build_live_exit_ladder(
    forecast: MatchForecast,
    evaluations: tuple[ContractEvaluation, ...],
    allocations: tuple[Allocation, ...],
    request: StrategyRequest,
    *,
    context: LiveMatchContext | None = None,
) -> tuple[LiveScorePlan, ...]:
    """Build conditional current-score values and exits for relevant states."""
    live_context = LiveMatchContext() if context is None else context
    by_score = {
        item.quote.selection: item for item in evaluations if item.quote.market == "correct_score"
    }
    allocated = {
        item.evaluation.quote.selection: item
        for item in allocations
        if item.evaluation.quote.market == "correct_score"
    }
    means = _expected_goals(forecast)
    grid = forecast.correct_score
    assumptions = (
        f"Poisson remaining-goal baseline; home rate x{live_context.home_rate_multiplier}, "
        f"away rate x{live_context.away_rate_multiplier}; red cards {live_context.home_red_cards}-"
        f"{live_context.away_red_cards}; defending={live_context.leading_team_defending}; "
        f"trailing pressure={live_context.trailing_team_pressure}; injury x{live_context.injury_multiplier}; "
        f"substitution x{live_context.substitution_multiplier}; pressure x{live_context.pressure_multiplier}; "
        f"added time {live_context.added_minutes}m."
    )
    plans: list[LiveScorePlan] = []
    for home, away in _states(forecast):
        score = f"{home}-{away}"
        probability = Decimal(str(grid.cell_probability(home, away)))
        position = allocated.get(score)
        plans.append(
            LiveScorePlan(
                score=score,
                model_probability=probability,
                position_active=position is not None,
                allocated_contracts=position.contracts if position else Decimal(0),
                position_cost=position.amount if position else Decimal(0),
                stages=_stages(position, by_score.get(score), request, live_context, means, (home, away)),
                next_home_score=f"{home + 1}-{away}",
                next_away_score=f"{home}-{away + 1}",
                goal_before_fill="Cancel the unfilled old-score order; its unsold contracts lose most or all value.",
                assumptions=assumptions,
            )
        )
    return tuple(plans)
