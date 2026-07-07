"""T07 acceptance: World Cup open fixtures/HT parse; StatsBomb events aggregate."""

from __future__ import annotations

import json
from pathlib import Path

from soccer_prediction.datasources.statsbomb import _count_events
from soccer_prediction.datasources.worldcup_open import WorldCupOpenSource

_MATCHES = {
    "matches": [
        {"team1": "Brazil", "team2": "Argentina", "score": [2, 1], "score1i": [1, 0], "date": "2022-11-24"},
    ]
}


def test_fixtures_and_ht(tmp_path: Path) -> None:
    """openfootball-style JSON yields half-time goals and a fixture list."""
    path = tmp_path / "world-cup.json"
    path.write_text(json.dumps(_MATCHES), encoding="utf-8")
    source = WorldCupOpenSource(path)
    records = source.fetch_team_history("Brazil")
    assert len(records) == 1
    assert records[0].goals_for == 2
    assert records[0].ht_goals_for == 1
    fixtures = source.fetch_fixtures("world-cup-2026")
    assert fixtures[0].home_team == "Brazil"


def test_statsbomb_aggregates_corners_cards() -> None:
    """StatsBomb-style events aggregate into per-team corner and card counts."""
    events = [
        {"team": {"name": "Brazil"}, "type": {"name": "Corner"}},
        {"team": {"name": "Brazil"}, "type": {"name": "Corner"}},
        {"team": {"name": "Argentina"}, "type": {"name": "Yellow Card"}},
    ]
    corners = _count_events(events, "corner")
    cards = _count_events(events, "yellow card")
    assert corners["Brazil"] == 2
    assert cards["Argentina"] == 1
