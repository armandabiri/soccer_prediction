"""Bankroll, liquidity, and concentration invariants."""

from __future__ import annotations

from decimal import Decimal

from soccer_prediction.models import BettingStrategy


def test_balanced_allocation_obeys_all_caps(betting_strategy: BettingStrategy) -> None:
    deployed = sum((item.amount for item in betting_strategy.allocations), Decimal(0))
    exact = [item for item in betting_strategy.allocations if item.evaluation.quote.market == "correct_score"]
    assert deployed <= Decimal("8.00")
    assert betting_strategy.uninvested_cash + deployed == Decimal("10.00")
    assert sum((item.amount for item in exact), Decimal(0)) <= Decimal("6.00")
    assert all(item.amount <= Decimal("3.00") for item in exact)
    assert all(item.contracts <= item.evaluation.quote.available_at_ask for item in betting_strategy.allocations)


def test_presets_preserve_minimum_cash_reserves(betting_strategy: BettingStrategy) -> None:
    expected = {"conservative": Decimal("3"), "balanced": Decimal("2"), "aggressive": Decimal("1")}
    for preset in betting_strategy.presets:
        assert preset.reserve == expected[preset.name]
        assert preset.uninvested_cash >= preset.reserve
        assert sum(preset.exit_fractions) == Decimal(1)

