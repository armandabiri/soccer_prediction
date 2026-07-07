"""T05 acceptance: the API-Football adapter parses corners, cards, and half-time."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from soccer_prediction.datasources.api_football import ApiFootballSource


def _payload() -> dict[str, Any]:
    return {
        "response": [
            {
                "fixture": {"date": "2025-06-01T18:00:00+00:00", "venue": {"name": "Maracana"}},
                "league": {"name": "World Cup", "round": "Final"},
                "teams": {"home": {"name": "Brazil"}, "away": {"name": "Argentina"}},
                "goals": {"home": 2, "away": 1},
                "score": {"halftime": {"home": 1, "away": 0}},
                "statistics": [
                    {
                        "team": {"name": "Brazil"},
                        "statistics": [
                            {"type": "Corner Kicks", "value": 6},
                            {"type": "Yellow Cards", "value": 2},
                            {"type": "Red Cards", "value": 0},
                        ],
                    },
                    {
                        "team": {"name": "Argentina"},
                        "statistics": [
                            {"type": "Corner Kicks", "value": 4},
                            {"type": "Yellow Cards", "value": 3},
                            {"type": "Red Cards", "value": 1},
                        ],
                    },
                ],
            }
        ]
    }


def test_parses_statistics() -> None:
    """Injected fixture statistics populate corners, cards, and half-time goals."""
    payload = _payload()

    def fetcher(url: str, headers: Mapping[str, str], params: Mapping[str, str]) -> dict[str, Any]:
        assert headers["x-apisports-key"] == "test-key"
        return payload

    source = ApiFootballSource(api_key="test-key", fetcher=fetcher)
    records = source.fetch_team_history("Brazil")
    assert len(records) == 1
    brazil = records[0]
    assert brazil.corners_for == 6
    assert brazil.corners_against == 4
    assert brazil.yellows == 2
    assert brazil.ht_goals_for == 1
    assert brazil.goals_for == 2
