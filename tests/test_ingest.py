"""T08 acceptance: malformed records are quarantined; empty input raises."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from soccer_prediction.datasources.errors import InsufficientHistoryError
from soccer_prediction.ingest import normalize_records
from soccer_prediction.models import TeamMatchStats


def _record(goals_for: int) -> TeamMatchStats:
    return TeamMatchStats(
        "Brazil", "Argentina", date(2025, 6, 1), True, goals_for, 1, 0, 0, 6, 4, 2, 0, "test", datetime.now(UTC)
    )


def test_quarantines_malformed() -> None:
    """A record with a negative count is quarantined and counted."""
    result = normalize_records([_record(2), _record(-3)])
    assert len(result.records) == 1
    assert result.quarantined == 1


def test_all_invalid_raises() -> None:
    """When no record survives validation, ingestion raises."""
    with pytest.raises(InsufficientHistoryError):
        normalize_records([_record(-1)])
