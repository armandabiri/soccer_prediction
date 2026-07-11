"""Uncertainty-adjusted value screening tests."""

from __future__ import annotations

from decimal import Decimal

from soccer_prediction.models import ContractQuote, MatchForecast, StrategyRequest
from soccer_prediction.strategy.valuation import evaluate_contracts


def test_high_ask_is_excluded_after_costs(strategy_forecast: MatchForecast) -> None:
    quote = ContractQuote("match_result", "home", Decimal("0.99"), bid=Decimal("0.98"))
    evaluation = evaluate_contracts(strategy_forecast, (quote,), StrategyRequest())[0]
    assert not evaluation.eligible
    assert evaluation.net_edge is not None and evaluation.net_edge < 0
    assert "not positive" in evaluation.reason


def test_unknown_player_is_explicitly_excluded(strategy_forecast: MatchForecast) -> None:
    quote = ContractQuote("player_to_score", "Unknown Player", Decimal("0.01"))
    evaluation = evaluate_contracts(strategy_forecast, (quote,), StrategyRequest())[0]
    assert evaluation.model_probability is None
    assert evaluation.reason == "No matching model probability is available."

