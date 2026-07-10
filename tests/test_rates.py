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
