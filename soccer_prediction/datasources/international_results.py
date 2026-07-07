"""International results source (martj42 international_results CSV).

Public-domain (CC0) results for every men's international from 1872 to today,
updated continuously. Columns: date, home_team, away_team, home_score,
away_score, tournament, city, country, neutral. Goals only -- no half-time,
corners, or cards (those default to zero). Unplayed fixtures carry ``NA``
scores and are skipped.
"""

from __future__ import annotations

import csv
import logging
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.request import urlopen

from soccer_prediction.datasources.base import register_source
from soccer_prediction.models import Fixture, TeamMatchStats

__all__ = ["INTERNATIONAL_RESULTS_URL", "InternationalResultsSource", "example_usage", "main"]

logger = logging.getLogger(__name__)

INTERNATIONAL_RESULTS_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
_DEFAULT_SINCE = date(2024, 1, 1)
_CACHE: dict[str, list[dict[str, str]]] = {}


class InternationalResultsSource:
    """Read martj42 international results from a URL or local path, since a date."""

    def __init__(self, source: str | Path | None = None, since: date = _DEFAULT_SINCE) -> None:
        self.source: str | Path = INTERNATIONAL_RESULTS_URL if source is None else source
        self.since = since

    def fetch_team_history(self, team: str, competition: str | None = None) -> list[TeamMatchStats]:
        """Return one team's played results on or after ``since``."""
        team_key = team.strip().casefold()
        records = [
            record for row in _rows(self.source) if (record := _record_for_team(row, team_key, self.since)) is not None
        ]
        logger.info("loaded %d international records for %s since %s", len(records), team, self.since)
        return records

    def fetch_fixtures(self, competition: str) -> list[Fixture]:
        """martj42 lists results, not a forward fixture schedule."""
        return []


def _rows(source: str | Path) -> list[dict[str, str]]:
    key = str(source)
    if key not in _CACHE:
        _CACHE[key] = _read_csv(source)
    return _CACHE[key]


def _read_csv(source: str | Path) -> list[dict[str, str]]:
    if isinstance(source, str) and source.startswith(("http://", "https://")):
        with urlopen(source, timeout=45) as response:  # noqa: S310 - configured public data URL.
            text = response.read().decode("utf-8-sig")
    else:
        path = Path(source)
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8-sig")
    return [dict(row) for row in csv.DictReader(text.splitlines())]


def _record_for_team(row: dict[str, str], team_key: str, since: date) -> TeamMatchStats | None:
    home = row.get("home_team", "")
    away = row.get("away_team", "")
    if team_key not in (home.casefold(), away.casefold()):
        return None
    match_date = _parse_date(row.get("date", ""))
    if match_date is None or match_date < since:
        return None
    home_score = _int(row.get("home_score"))
    away_score = _int(row.get("away_score"))
    if home_score is None or away_score is None:
        return None
    is_home = home.casefold() == team_key
    team, opponent = (home, away) if is_home else (away, home)
    goals_for, goals_against = (home_score, away_score) if is_home else (away_score, home_score)
    return TeamMatchStats(
        team,
        opponent,
        match_date,
        is_home,
        goals_for,
        goals_against,
        0,
        0,
        0,
        0,
        0,
        0,
        "international_results",
        datetime.now(UTC),
    )


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _int(value: str | None) -> int | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned or cleaned.upper() == "NA":
        return None
    try:
        return int(float(cleaned))
    except ValueError:
        return None


@register_source("international_results")
def _factory() -> InternationalResultsSource:
    return InternationalResultsSource()


def example_usage() -> None:
    """Print the international results data URL."""
    print(INTERNATIONAL_RESULTS_URL)


def main() -> None:
    """Module entry point."""
    example_usage()
