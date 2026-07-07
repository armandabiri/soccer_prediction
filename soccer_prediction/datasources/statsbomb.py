"""StatsBomb open-data source."""

from __future__ import annotations

import importlib
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from soccer_prediction.datasources.base import register_source
from soccer_prediction.datasources.errors import DataSourceError
from soccer_prediction.models import Fixture, TeamMatchStats

__all__ = ["StatsbombSource", "example_usage", "main"]

logger = logging.getLogger(__name__)
logger.info("StatsBomb open-data requires non-commercial use and attribution.")


class StatsbombSource:
    """Aggregate World Cup open-data events into corners and cards."""

    def __init__(self, competitions: tuple[int, ...] = (43,)) -> None:
        self.competitions = competitions

    def fetch_team_history(self, team: str, competition: str | None = None) -> list[TeamMatchStats]:
        """Return StatsBomb event aggregates for a team."""
        sb = _statsbombpy()
        records: list[TeamMatchStats] = []
        for competition_id in self.competitions:
            matches = sb.matches(competition_id=competition_id, season_id=int(competition)) if competition else []
            for match in _iter_dicts(matches):
                records.extend(self._records_from_match(sb, match))
        filtered = [record for record in records if record.team.casefold() == team.casefold()]
        logger.info("loaded %d StatsBomb records for %s", len(filtered), team)
        return filtered

    def fetch_fixtures(self, competition: str) -> list[Fixture]:
        """StatsBomb open-data is historical, so no future fixtures are returned."""
        return []

    def _records_from_match(self, sb: Any, match: Mapping[str, Any]) -> list[TeamMatchStats]:
        events = list(_iter_dicts(sb.events(match_id=match["match_id"])))
        home = str(match.get("home_team", {}).get("home_team_name", match.get("home_team", "")))
        away = str(match.get("away_team", {}).get("away_team_name", match.get("away_team", "")))
        if not home or not away:
            return []
        corners = _count_events(events, "corner")
        yellows = _count_events(events, "yellow card")
        reds = _count_events(events, "red card")
        match_date = datetime.fromisoformat(str(match.get("match_date", datetime.now(UTC).date()))).date()
        fetched_at = datetime.now(UTC)
        home_score = int(match.get("home_score", 0))
        away_score = int(match.get("away_score", 0))
        return [
            TeamMatchStats(
                home,
                away,
                match_date,
                True,
                home_score,
                away_score,
                0,
                0,
                corners.get(home, 0),
                corners.get(away, 0),
                yellows.get(home, 0),
                reds.get(home, 0),
                "statsbomb_open_data",
                fetched_at,
            ),
            TeamMatchStats(
                away,
                home,
                match_date,
                False,
                away_score,
                home_score,
                0,
                0,
                corners.get(away, 0),
                corners.get(home, 0),
                yellows.get(away, 0),
                reds.get(away, 0),
                "statsbomb_open_data",
                fetched_at,
            ),
        ]


def _statsbombpy() -> Any:
    try:
        module = importlib.import_module("statsbombpy")
    except ImportError as exc:
        raise DataSourceError("statsbombpy is required for StatsbombSource") from exc
    return module.sb


def _iter_dicts(value: object) -> list[Mapping[str, Any]]:
    if hasattr(value, "to_dict"):
        value = value.to_dict("records")
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _count_events(events: list[Mapping[str, Any]], needle: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        team = str(event.get("team", {}).get("name", event.get("team", "")))
        event_type = str(event.get("type", {}).get("name", event.get("type", ""))).casefold()
        if needle in event_type:
            counts[team] = counts.get(team, 0) + 1
    return counts


@register_source("statsbomb")
def _factory() -> StatsbombSource:
    return StatsbombSource()


def example_usage() -> None:
    """Print configured competition IDs."""
    print(StatsbombSource().competitions)


def main() -> None:
    """Module entry point."""
    example_usage()
