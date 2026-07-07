"""T06 acceptance: the football-data.co.uk loader maps corner/card/half-time columns."""

from __future__ import annotations

from pathlib import Path

from soccer_prediction.datasources.football_data_csv import FootballDataCsvSource

_CSV = "Date,HomeTeam,AwayTeam,FTHG,FTAG,HTHG,HTAG,HC,AC,HY,AY,HR,AR\n01/06/2025,Brazil,Argentina,2,1,1,0,6,4,2,3,0,1\n"


def test_column_mapping(tmp_path: Path) -> None:
    """HC/AC, HY/AY/HR/AR, and HTHG/HTAG columns map onto TeamMatchStats."""
    csv_path = tmp_path / "season.csv"
    csv_path.write_text(_CSV, encoding="utf-8")
    source = FootballDataCsvSource([str(csv_path)])
    records = source.fetch_team_history("Brazil")
    assert len(records) == 1
    brazil = records[0]
    assert brazil.corners_for == 6
    assert brazil.corners_against == 4
    assert brazil.yellows == 2
    assert brazil.reds == 0
    assert brazil.ht_goals_for == 1
    assert brazil.goals_for == 2
