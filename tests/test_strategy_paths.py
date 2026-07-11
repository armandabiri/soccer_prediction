"""Pathwise cash flow and recovery semantics."""

from __future__ import annotations

from soccer_prediction.models import BettingStrategy


def test_required_paths_and_recovery_scopes_are_reported(betting_strategy: BettingStrategy) -> None:
    paths = {row.path for row in betting_strategy.path_ledger}
    assert "0-0 → 1-0 → 1-1 → 2-1 → 2-2" in paths
    assert "0-0 → 0-1 → 0-2" in paths
    assert all(row.full_bankroll_recovered <= row.active_positions_recovered for row in betting_strategy.path_ledger)


def test_unfilled_or_inactive_scores_do_not_create_cash(betting_strategy: BettingStrategy) -> None:
    inactive = {plan.score for plan in betting_strategy.live_scores if not plan.position_active}
    assert all(row.stage_cash == 0 for row in betting_strategy.path_ledger if row.score in inactive)

