"""Load packaged offline example history into typed records."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, date, datetime
from importlib import resources
from typing import Any, cast

from soccer_prediction.models import PlayerGame, PlayerStats, TeamMatchStats

__all__ = ["load_packaged_history", "load_packaged_players"]

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


def load_packaged_players(resource: str) -> list[PlayerStats]:
    """Load a packaged JSON squad file (under this package) as typed players."""
    raw = resources.files(__package__).joinpath(resource).read_text(encoding="utf-8")
    parsed: object = json.loads(raw)
    players: list[PlayerStats] = []
    if isinstance(parsed, list):
        for row in parsed:
            if isinstance(row, dict):
                players.append(_row_to_player(cast("dict[str, Any]", row)))
    return players


def _row_to_player(row: Mapping[str, Any]) -> PlayerStats:
    return PlayerStats(
        name=str(row["name"]),
        team=str(row["team"]),
        position=str(row["position"]),
        appearances=int(row["appearances"]),
        goals=int(row["goals"]),
        assists=int(row["assists"]),
        recent_appearances=_optional_int(row.get("recent_appearances")),
        recent_goals=_optional_int(row.get("recent_goals")),
        recent_assists=_optional_int(row.get("recent_assists")),
        recent_games=_recent_games(row.get("recent_games")),
    )


def _recent_games(value: object) -> tuple[PlayerGame, ...]:
    """Parse compact ``[played, goals, assists]`` rows into typed player games.

    Each entry is a 3-element list ordered oldest-to-newest; ``played`` is 0/1
    (or a bool) and a not-played game carries no goals or assists.
    """
    if value is None:
        return ()
    if not isinstance(value, list):
        raise TypeError(f"expected a list of recent games, got {type(value).__name__}")
    games: list[PlayerGame] = []
    for raw in cast("list[object]", value):
        if not isinstance(raw, list):
            raise ValueError("each recent game must be a [played, goals, assists] triple")
        entry = raw
        if len(entry) != 3:
            raise ValueError("each recent game must be a [played, goals, assists] triple")
        played, goals, assists = entry
        games.append(PlayerGame(played=bool(played), goals=int(goals), assists=int(assists)))
    return tuple(games)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int | float | str):
        return int(value)
    raise TypeError(f"expected an integer-compatible recent player stat, got {type(value).__name__}")


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
