"""Open World Cup fixtures/results source (openfootball worldcup.json format).

Reads the public-domain openfootball data, e.g. the live World Cup 2026 file at
``WC2026_URL``. Each match carries ``score.ft`` (full-time) and ``score.ht``
(half-time) as ``[team1, team2]`` lists; openfootball does not include corners
or cards, so those default to zero (use API-Football or StatsBomb for them).
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from soccer_prediction.datasources.base import register_source
from soccer_prediction.models import Fixture, TeamMatchStats

__all__ = ["WC2026_URL", "WorldCupOpenSource", "example_usage", "main"]

logger = logging.getLogger(__name__)

WC2026_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"

_PLACEHOLDER = re.compile(r"^(?:[WL]\d+|RU-?[A-Z]|[123][A-Z])$")
_CACHE: dict[str, list[Mapping[str, Any]]] = {}


class WorldCupOpenSource:
    """Read openfootball worldcup.json results from a URL or local path."""

    def __init__(self, source: str | Path | None = None) -> None:
        self.source = source

    def fetch_team_history(self, team: str, competition: str | None = None) -> list[TeamMatchStats]:
        """Return completed match records (with results) for a team."""
        records = [record for match in self._matches() for record in _records_from_match(match)]
        filtered = [record for record in records if record.team.casefold() == team.casefold()]
        logger.info("loaded %d openfootball records for %s", len(filtered), team)
        return filtered

    def fetch_fixtures(self, competition: str) -> list[Fixture]:
        """Return scheduled fixtures with concrete (non-placeholder) team names."""
        return [
            _fixture_from_match(match, competition)
            for match in self._matches()
            if not _is_placeholder(str(match.get("team1", ""))) and not _is_placeholder(str(match.get("team2", "")))
        ]

    def _matches(self) -> list[Mapping[str, Any]]:
        if self.source is None:
            return []
        key = str(self.source)
        if key not in _CACHE:
            _CACHE[key] = _extract_matches(_load(self.source))
        return _CACHE[key]


def _load(source: str | Path) -> object:
    if isinstance(source, str) and source.startswith(("http://", "https://")):
        with urlopen(source, timeout=30) as response:  # noqa: S310 - configured public data URL.
            text = response.read().decode("utf-8")
    else:
        path = Path(source)
        if not path.exists():
            return {}
        text = path.read_text(encoding="utf-8")
    return json.loads(text)


def _extract_matches(payload: object) -> list[Mapping[str, Any]]:
    if isinstance(payload, Mapping):
        matches = payload.get("matches")
        if isinstance(matches, list):
            return [match for match in matches if isinstance(match, Mapping)]
        rounds = payload.get("rounds")
        if isinstance(rounds, list):
            nested: list[Mapping[str, Any]] = []
            for entry in rounds:
                if isinstance(entry, Mapping) and isinstance(entry.get("matches"), list):
                    nested.extend(match for match in entry["matches"] if isinstance(match, Mapping))
            return nested
    if isinstance(payload, list):
        return [match for match in payload if isinstance(match, Mapping)]
    return []


def _pair(value: object) -> tuple[int, int] | None:
    if isinstance(value, list | tuple) and len(value) >= 2:
        return int(value[0]), int(value[1])
    return None


def _result(match: Mapping[str, Any]) -> tuple[tuple[int, int], tuple[int, int]] | None:
    score = match.get("score")
    if not isinstance(score, Mapping):
        return None
    full_time = _pair(score.get("ft"))
    if full_time is None:
        return None
    half_time = _pair(score.get("ht")) or (0, 0)
    return full_time, half_time


def _is_placeholder(name: str) -> bool:
    return not name or bool(_PLACEHOLDER.match(name.strip()))


def _records_from_match(match: Mapping[str, Any]) -> list[TeamMatchStats]:
    team1 = str(match.get("team1", ""))
    team2 = str(match.get("team2", ""))
    result = _result(match)
    if _is_placeholder(team1) or _is_placeholder(team2) or result is None:
        return []
    (ft_home, ft_away), (ht_home, ht_away) = result
    match_date = _parse_date(match.get("date"))
    fetched_at = datetime.now(UTC)
    return [
        TeamMatchStats(
            team1, team2, match_date, True, ft_home, ft_away, ht_home, ht_away, 0, 0, 0, 0, "openfootball", fetched_at
        ),
        TeamMatchStats(
            team2, team1, match_date, False, ft_away, ft_home, ht_away, ht_home, 0, 0, 0, 0, "openfootball", fetched_at
        ),
    ]


def _fixture_from_match(match: Mapping[str, Any], competition: str) -> Fixture:
    return Fixture(
        home_team=str(match.get("team1", "")),
        away_team=str(match.get("team2", "")),
        kickoff=None,
        competition=competition,
        round_name=str(match.get("round", match.get("group", ""))) or None,
    )


def _parse_date(value: object) -> date:
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value[:10]).date()
    return datetime.now(UTC).date()


@register_source("worldcup_open")
def _factory_open() -> WorldCupOpenSource:
    return WorldCupOpenSource()


@register_source("worldcup_2026")
def _factory_2026() -> WorldCupOpenSource:
    return WorldCupOpenSource(WC2026_URL)


def example_usage() -> None:
    """Print the live World Cup 2026 data URL."""
    print(WC2026_URL)


def main() -> None:
    """Module entry point."""
    example_usage()
