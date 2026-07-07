"""T02 acceptance: typed domain models are frozen and grid helpers are consistent."""

from __future__ import annotations

import dataclasses
from datetime import UTC, date, datetime

import pytest

from soccer_prediction.models import ScorelineGrid, TeamMatchStats


def test_dataclasses_frozen() -> None:
    """TeamMatchStats is immutable (frozen dataclass)."""
    record = TeamMatchStats(
        "Brazil", "Argentina", date(2025, 6, 1), True, 2, 1, 1, 0, 6, 4, 2, 0, "test", datetime.now(UTC)
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.goals_for = 5  # type: ignore[misc]


def test_scoreline_grid_helpers() -> None:
    """1X2 mass sums to the total grid mass."""
    grid = ScorelineGrid(1, 1, ((0.4, 0.1), (0.2, 0.3)))
    home, draw, away = grid.home_draw_away()
    assert round(home + draw + away, 6) == round(grid.total_probability(), 6)
    assert 0.0 <= grid.both_teams_to_score() <= 1.0
