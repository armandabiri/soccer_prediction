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


def test_safe_sell_target_covers_worst_next_goal_branch(betting_strategy: BettingStrategy) -> None:
    """Recovery targets include all exact-score stakes invalidated by either next goal."""
    score_positions = {
        item.evaluation.quote.selection: item
        for item in betting_strategy.allocations
        if item.evaluation.quote.market == "correct_score"
    }
    plans = {item.score: item for item in betting_strategy.live_scores}
    for score in ("0-0", "1-0", "0-1", "1-1"):
        plan = plans[score]
        home, away = (int(value) for value in score.split("-"))
        expected_home_loss = sum(
            (
                position.amount
                for final, position in score_positions.items()
                if int(final.split("-")[0]) < home + 1 or int(final.split("-")[1]) < away
            ),
            Decimal(0),
        )
        expected_away_loss = sum(
            (
                position.amount
                for final, position in score_positions.items()
                if int(final.split("-")[0]) < home or int(final.split("-")[1]) < away + 1
            ),
            Decimal(0),
        )
        assert plan.next_home_goal_loss == expected_home_loss
        assert plan.next_away_goal_loss == expected_away_loss
        assert plan.safe_recovery_target >= max(expected_home_loss, expected_away_loss)


def test_safe_star_only_appears_after_cumulative_recovery(betting_strategy: BettingStrategy) -> None:
    for plan in betting_strategy.live_scores:
        for stage in plan.stages:
            assert stage.safe_to_sell == (
                stage.recovery_target > 0 and stage.cumulative_cash >= stage.recovery_target
            )
