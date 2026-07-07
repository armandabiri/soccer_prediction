"""Open World Cup fixture/history source."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from soccer_prediction.datasources.base import register_source
from soccer_prediction.models import Fixture, TeamMatchStats

__all__ = ["WorldCupOpenSource", "example_usage", "main"]

logger = logging.getLogger(__name__)


class WorldCupOpenSource:
    """Read openfootball-style World Cup JSON files."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = None if path is None else Path(path)

    def fetch_team_history(self, team: str, competition: str | None = None) -> list[TeamMatchStats]:
        """Return completed World Cup records for a team."""
        records = [record for match in self._matches() for record in _records_from_match(match)]
        filtered = [record for record in records if record.team.casefold() == team.casefold()]
        logger.info("loaded %d open World Cup records for %s", len(filtered), team)
        return filtered

    def fetch_fixtures(self, competition: str) -> list[Fixture]:
        """Return all fixtures in the configured World Cup JSON."""
        return [_fixture_from_match(match, competition) for match in self._matches()]

    def _matches(self) -> list[Mapping[str, Any]]:
        if self.path is None or not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if isinstance(payload, Mapping):
            matches = payload.get("matches", payload.get("rounds", []))
        else:
            matches = payload
        return _flatten_matches(matches)


def _flatten_matches(value: object) -> list[Mapping[str, Any]]:
    if isinstance(value, list):
        result: list[Mapping[str, Any]] = []
        for item in value:
            if isinstance(item, Mapping) and isinstance(item.get("matches"), list):
                result.extend(_flatten_matches(item["matches"]))
            elif isinstance(item, Mapping):
                result.append(item)
        return result
    return []


def _records_from_match(match: Mapping[str, Any]) -> list[TeamMatchStats]:
    team1 = str(match.get("team1", match.get("home_team", "")))
    team2 = str(match.get("team2", match.get("away_team", "")))
    score = _score(match.get("score", match.get("ft")))
    halftime = _score(match.get("score1i", match.get("ht", match.get("halftime"))))
    if not team1 or not team2 or score is None:
        return []
    match_date = _parse_date(match.get("date"))
    fetched_at = datetime.now(UTC)
    ht_home, ht_away = halftime if halftime is not None else (0, 0)
    return [
        TeamMatchStats(
            team1,
            team2,
            match_date,
            True,
            score[0],
            score[1],
            ht_home,
            ht_away,
            0,
            0,
            0,
            0,
            "openfootball",
            fetched_at,
        ),
        TeamMatchStats(
            team2,
            team1,
            match_date,
            False,
            score[1],
            score[0],
            ht_away,
            ht_home,
            0,
            0,
            0,
            0,
            "openfootball",
            fetched_at,
        ),
    ]


def _fixture_from_match(match: Mapping[str, Any], competition: str) -> Fixture:
    return Fixture(
        home_team=str(match.get("team1", match.get("home_team", ""))),
        away_team=str(match.get("team2", match.get("away_team", ""))),
        kickoff=None,
        competition=competition,
        round_name=str(match.get("round", match.get("group", ""))) or None,
    )


def _score(value: object) -> tuple[int, int] | None:
    if isinstance(value, list | tuple) and len(value) >= 2:
        return int(value[0]), int(value[1])
    if isinstance(value, Mapping):
        home = value.get("ft1", value.get("home", value.get("team1")))
        away = value.get("ft2", value.get("away", value.get("team2")))
        if home is not None and away is not None:
            return int(home), int(away)
    return None


def _parse_date(value: object) -> date:
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value[:10]).date()
    return datetime.now(UTC).date()


@register_source("worldcup_open")
def _factory() -> WorldCupOpenSource:
    return WorldCupOpenSource()


def example_usage() -> None:
    """Print an empty source."""
    print(WorldCupOpenSource())


def main() -> None:
    """Module entry point."""
    example_usage()
