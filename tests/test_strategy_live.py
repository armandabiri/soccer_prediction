"""Conditional score-state and staged-exit tests."""

from __future__ import annotations

from decimal import Decimal

from soccer_prediction.models import BettingStrategy


def test_required_score_states_and_transitions_exist(betting_strategy: BettingStrategy) -> None:
    plans = {item.score: item for item in betting_strategy.live_scores}
    required = {"0-0", "1-0", "0-1", "1-1", "2-0", "0-2", "2-1", "1-2", "2-2"}
    assert required <= set(plans)
    assert plans["1-1"].next_home_score == "2-1"
    assert plans["1-1"].next_away_score == "1-2"


def test_fixed_rate_fair_value_rises_and_stages_reconcile(betting_strategy: BettingStrategy) -> None:
    for plan in betting_strategy.live_scores:
        fair_values = [stage.fair_value for stage in plan.stages]
        assert fair_values == sorted(fair_values)
        assert sum(stage.fraction for stage in plan.stages) == Decimal(1)
        assert sum(stage.contracts for stage in plan.stages) == plan.allocated_contracts
        assert all(stage.bid_depth >= 0 for stage in plan.stages)
