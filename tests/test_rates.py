"""T10 acceptance: team rates match a known hand-computed fixture."""

from __future__ import annotations

from datetime import UTC, date, datetime

from soccer_prediction.features import compute_rates
from soccer_prediction.models import TeamMatchStats


def test_known_rates() -> None:
    """Identical records collapse shrinkage to the exact observed rates."""
    fetched_at = datetime.now(UTC)
    records = [
        TeamMatchStats("Brazil", "X", date(2025, 1, 1), True, 2, 1, 1, 0, 6, 4, 2, 0, "test", fetched_at)
        for _ in range(8)
    ]
    rates = compute_rates(records).for_team("Brazil")
    assert rates.goals_for == 2.0
    assert rates.corners_for == 6.0
    assert rates.yellows == 2.0
    assert rates.sample_size == 8


def test_unseen_team_uses_prior() -> None:
    """An unseen team falls back to the global prior rather than raising."""
    rates = compute_rates([]).for_team("Nowhere")
    assert rates.goals_for > 1.0


def test_as_of_excludes_future_records() -> None:
    """Retrospective rates cannot see matches after the forecast anchor."""
    fetched_at = datetime.now(UTC)
    past = TeamMatchStats(
        "A", "B", date(2024, 1, 1), True, 1, 0, 0, 0, 3, 2, 1, 0, "test", fetched_at
    )
    future = TeamMatchStats(
        "A", "B", date(2026, 1, 1), True, 9, 0, 4, 0, 12, 1, 0, 0, "test", fetched_at
    )
    with_future = compute_rates([past, future], today=date(2025, 1, 1)).for_team("A")
    past_only = compute_rates([past], today=date(2025, 1, 1)).for_team("A")
    assert with_future == past_only
