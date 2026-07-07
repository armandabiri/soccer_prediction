"""International results source (martj42): filter by date, skip unplayed (NA) rows."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from soccer_prediction.datasources.international_results import InternationalResultsSource

_CSV = (
    "date,home_team,away_team,home_score,away_score,tournament,city,country,neutral\n"
    "2023-11-20,Switzerland,Kosovo,1,1,UEFA Euro qualification,Basel,Switzerland,False\n"
    "2024-06-15,Switzerland,Hungary,3,1,UEFA Euro,Cologne,Germany,True\n"
    "2026-07-06,Switzerland,Colombia,NA,NA,FIFA World Cup,East Rutherford,United States,True\n"
)


def _source(tmp_path: Path) -> InternationalResultsSource:
    path = tmp_path / "results.csv"
    path.write_text(_CSV, encoding="utf-8")
    return InternationalResultsSource(path, since=date(2024, 1, 1))


def test_filters_by_date_and_skips_unplayed(tmp_path: Path) -> None:
    """Only played matches on or after `since` are returned."""
    records = _source(tmp_path).fetch_team_history("Switzerland")
    assert len(records) == 1
    assert records[0].goals_for == 3
    assert records[0].opponent == "Hungary"


def test_away_perspective(tmp_path: Path) -> None:
    """A team appearing as the away side is emitted from its own perspective."""
    records = _source(tmp_path).fetch_team_history("Hungary")
    assert len(records) == 1
    assert records[0].goals_for == 1
    assert records[0].is_home is False
