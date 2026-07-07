"""football-data.co.uk CSV source."""

from __future__ import annotations

import csv
import logging
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.request import urlopen

from soccer_prediction.datasources.base import register_source
from soccer_prediction.datasources.errors import DataSourceError
from soccer_prediction.models import Fixture, TeamMatchStats

__all__ = ["FootballDataCsvSource", "example_usage", "main"]

logger = logging.getLogger(__name__)


class FootballDataCsvSource:
    """Read historical club-league CSVs from paths or URLs."""

    def __init__(self, season_urls: list[str] | None = None) -> None:
        self.season_urls = [] if season_urls is None else season_urls

    def fetch_team_history(self, team: str, competition: str | None = None) -> list[TeamMatchStats]:
        """Return records for a team across configured CSV seasons."""
        records: list[TeamMatchStats] = []
        for season_url in self.season_urls:
            rows = _read_rows(season_url)
            for row in rows:
                records.extend(_records_from_row(row, source=f"football_data_csv:{season_url}"))
        filtered = [record for record in records if record.team.casefold() == team.casefold()]
        logger.info("loaded %d football-data CSV records for %s", len(filtered), team)
        return filtered

    def fetch_fixtures(self, competition: str) -> list[Fixture]:
        """football-data.co.uk CSV history does not expose future fixtures."""
        return []


def _read_rows(path_or_url: str) -> list[dict[str, str]]:
    if path_or_url.startswith(("http://", "https://")):
        with urlopen(path_or_url, timeout=30) as response:  # noqa: S310 - configured public CSV URL.
            text = response.read().decode("utf-8-sig")
    else:
        text = Path(path_or_url).read_text(encoding="utf-8-sig")
    return [dict(row) for row in csv.DictReader(text.splitlines())]


def _records_from_row(row: dict[str, str], source: str) -> list[TeamMatchStats]:
    home = row.get("HomeTeam", "")
    away = row.get("AwayTeam", "")
    if not home or not away:
        raise DataSourceError("football-data CSV row missing HomeTeam/AwayTeam")
    match_date = _parse_date(row.get("Date", ""))
    fetched_at = datetime.now(UTC)
    return [
        TeamMatchStats(
            team=home,
            opponent=away,
            date=match_date,
            is_home=True,
            goals_for=_int(row.get("FTHG")),
            goals_against=_int(row.get("FTAG")),
            ht_goals_for=_int(row.get("HTHG")),
            ht_goals_against=_int(row.get("HTAG")),
            corners_for=_int(row.get("HC")),
            corners_against=_int(row.get("AC")),
            yellows=_int(row.get("HY")),
            reds=_int(row.get("HR")),
            source=source,
            fetched_at=fetched_at,
        ),
        TeamMatchStats(
            team=away,
            opponent=home,
            date=match_date,
            is_home=False,
            goals_for=_int(row.get("FTAG")),
            goals_against=_int(row.get("FTHG")),
            ht_goals_for=_int(row.get("HTAG")),
            ht_goals_against=_int(row.get("HTHG")),
            corners_for=_int(row.get("AC")),
            corners_against=_int(row.get("HC")),
            yellows=_int(row.get("AY")),
            reds=_int(row.get("AR")),
            source=source,
            fetched_at=fetched_at,
        ),
    ]


def _parse_date(raw: str) -> date:
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise DataSourceError(f"unsupported football-data date: {raw!r}")


def _int(raw: str | None) -> int:
    if raw is None or raw == "":
        return 0
    return int(float(raw))


@register_source("football_data_csv")
def _factory() -> FootballDataCsvSource:
    return FootballDataCsvSource()


def example_usage() -> None:
    """Print an empty source."""
    print(FootballDataCsvSource())


def main() -> None:
    """Module entry point."""
    example_usage()
