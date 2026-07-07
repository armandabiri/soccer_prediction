"""Load packaged offline example history into typed records."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, date, datetime
from importlib import resources
from typing import Any, cast

from soccer_prediction.models import TeamMatchStats

__all__ = ["load_packaged_history"]

_FETCHED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def load_packaged_history(resource: str, source: str) -> list[TeamMatchStats]:
    """Load a packaged JSON history file (under this package) as typed records."""
    raw = resources.files(__package__).joinpath(resource).read_text(encoding="utf-8")
    parsed: object = json.loads(raw)
    records: list[TeamMatchStats] = []
    if isinstance(parsed, list):
        for row in parsed:
            if isinstance(row, dict):
                records.append(_row_to_stats(cast("dict[str, Any]", row), source))
    return records


def _row_to_stats(row: Mapping[str, Any], source: str) -> TeamMatchStats:
    return TeamMatchStats(
        team=str(row["team"]),
        opponent=str(row["opponent"]),
        date=date.fromisoformat(str(row["date"])),
        is_home=bool(row["is_home"]),
        goals_for=int(row["goals_for"]),
        goals_against=int(row["goals_against"]),
        ht_goals_for=int(row["ht_goals_for"]),
        ht_goals_against=int(row["ht_goals_against"]),
        corners_for=int(row["corners_for"]),
        corners_against=int(row["corners_against"]),
        yellows=int(row["yellows"]),
        reds=int(row["reds"]),
        source=source,
        fetched_at=_FETCHED_AT,
    )
