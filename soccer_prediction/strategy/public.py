"""Public orchestration for price-aware betting strategy reports."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from soccer_prediction.models import (
    BettingStrategy,
    ContractEvaluation,
    LiveMatchContext,
    MatchForecast,
    PresetSummary,
    QuoteSnapshot,
    StrategyRequest,
)
from soccer_prediction.strategy.allocation import allocate_bankroll
from soccer_prediction.strategy.live import build_live_exit_ladder
from soccer_prediction.strategy.paths import simulate_score_paths
from soccer_prediction.strategy.presets import exit_fractions, reserve_percentage
from soccer_prediction.strategy.valuation import evaluate_contracts

__all__ = ["build_betting_strategy"]

_PRESETS = ("conservative", "balanced", "aggressive")


def _validate_freshness(snapshot: QuoteSnapshot, request: StrategyRequest) -> None:
    if request.max_quote_age_seconds is None:
        return
    age = (datetime.now(UTC) - snapshot.observed_at).total_seconds()
    if age < -300:
        raise ValueError("quote snapshot observation time is in the future")
    if age > request.max_quote_age_seconds:
        raise ValueError(
            f"quote snapshot is stale ({int(age)} seconds old; maximum {request.max_quote_age_seconds})"
        )


def _preset_summaries(
    evaluations: tuple[ContractEvaluation, ...], request: StrategyRequest
) -> tuple[PresetSummary, ...]:
    summaries: list[PresetSummary] = []
    for name in _PRESETS:
        allocations, cash = allocate_bankroll(evaluations, request, plan=name)
        deployed = sum((item.amount for item in allocations), Decimal(0))
        summaries.append(
            PresetSummary(
                name=name,
                reserve=(request.bankroll * reserve_percentage(name, request)).quantize(Decimal("0.01")),
                deployed=deployed,
                uninvested_cash=cash,
                maximum_loss=deployed,
                exit_fractions=exit_fractions(name),
                allocations=allocations,
            )
        )
    return tuple(summaries)


def build_betting_strategy(
    forecast: MatchForecast,
    quotes: QuoteSnapshot,
    *,
    request: StrategyRequest | None = None,
    live_context: LiveMatchContext | None = None,
) -> BettingStrategy:
    """Build one immutable strategy result from a forecast and quote snapshot."""
    strategy_request = StrategyRequest() if request is None else request
    _validate_freshness(quotes, strategy_request)
    evaluations = evaluate_contracts(forecast, quotes.contracts, strategy_request)
    allocations, cash = allocate_bankroll(evaluations, strategy_request)
    live_scores = build_live_exit_ladder(
        forecast, evaluations, allocations, strategy_request, context=live_context
    )
    paths = simulate_score_paths(live_scores, allocations, strategy_request.bankroll)
    warnings = [
        "Model probabilities are estimates, not guarantees; use executable asks to buy and bids to sell.",
        "Planned limit orders may not fill; a goal can invalidate the current-score position before sale.",
        "Recovering one position does not recover all active positions or the complete bankroll.",
    ]
    if not allocations:
        warnings.append("No quote cleared the safety-adjusted value and risk constraints; bankroll remains cash.")
    warnings.extend(quotes.notes)
    return BettingStrategy(
        schema_version=1,
        venue=quotes.venue,
        quote_observed_at=quotes.observed_at,
        request=strategy_request,
        evaluations=evaluations,
        allocations=allocations,
        uninvested_cash=cash,
        live_scores=live_scores,
        path_ledger=paths,
        presets=_preset_summaries(evaluations, strategy_request),
        warnings=tuple(warnings),
    )
