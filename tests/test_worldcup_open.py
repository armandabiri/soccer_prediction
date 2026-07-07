"""T07 acceptance: openfootball World Cup results parse; StatsBomb events aggregate."""

from __future__ import annotations

import json
from pathlib import Path

from soccer_prediction.datasources.statsbomb import _count_events
from soccer_prediction.datasources.worldcup_open import WorldCupOpenSource

# Real openfootball worldcup.json shape: score.ft / score.ht as [team1, team2] lists,
# plus unplayed knockout slots with placeholder team codes (W95).
_MATCHES = {
    "name": "World Cup 2026",
    "matches": [
        {
            "round": "Matchday 2",
            "date": "2026-06-18",
            "team1": "Switzerland",
            "team2": "Bosnia & Herzegovina",
            "score": {"ft": [4, 1], "ht": [0, 0]},
            "group": "Group B",
        },
        {"round": "Round of 32", "date": "2026-06-30", "team1": "W95", "team2": "W96"},
    ],
}


def test_fixtures_and_ht(tmp_path: Path) -> None:
    """openfootball score.ft/score.ht parse; placeholder knockout slots are skipped."""
    path = tmp_path / "world-cup.json"
    path.write_text(json.dumps(_MATCHES), encoding="utf-8")
    source = WorldCupOpenSource(path)
    records = source.fetch_team_history("Switzerland")
    assert len(records) == 1
    assert records[0].goals_for == 4
    assert records[0].goals_against == 1
    assert records[0].ht_goals_for == 0
    # The unplayed match with placeholder teams contributes no records or fixtures.
    assert source.fetch_team_history("W95") == []
    fixtures = source.fetch_fixtures("world-cup-2026")
    assert len(fixtures) == 1
    assert fixtures[0].home_team == "Switzerland"


def test_statsbomb_aggregates_corners_cards() -> None:
    """StatsBomb-style events aggregate into per-team corner and card counts."""
    events = [
        {"team": {"name": "Brazil"}, "type": {"name": "Corner"}},
        {"team": {"name": "Brazil"}, "type": {"name": "Corner"}},
        {"team": {"name": "Argentina"}, "type": {"name": "Yellow Card"}},
    ]
    assert _count_events(events, "corner")["Brazil"] == 2
    assert _count_events(events, "yellow card")["Argentina"] == 1
