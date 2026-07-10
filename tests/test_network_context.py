"""Opponent-network, head-to-head, and recent-form behavior."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from soccer_prediction.datasources import register_source
from soccer_prediction.features import build_matchup_context, compute_rates
from soccer_prediction.models import CardsPrediction, CornersPrediction, Fixture, TeamMatchStats
from soccer_prediction.predictors.poisson import poisson_grid
from soccer_prediction.public import forecast_fixture


def _record(
    team: str,
    opponent: str,
    goals_for: int,
    goals_against: int,
    *,
    match_date: date | None = None,
    is_home: bool = True,
    corners_for: int = 5,
    corners_against: int = 5,
) -> TeamMatchStats:
    return TeamMatchStats(
        team,
        opponent,
        match_date or date.today(),
        is_home,
        goals_for,
        goals_against,
        0,
        0,
        corners_for,
        corners_against,
        2,
        0,
        "network_test",
        datetime.now(UTC),
    )


_NETWORK_HISTORY = (
    _record("A", "D", 1, 0, corners_for=5, corners_against=3),
    _record("D", "A", 0, 1, is_home=False, corners_for=3, corners_against=5),
    _record("D", "F", 4, 0, corners_for=10, corners_against=2),
    _record("F", "D", 0, 4, is_home=False, corners_for=2, corners_against=10),
    _record("Z", "F", 1, 0, corners_for=5, corners_against=3),
    _record("F", "Z", 0, 1, is_home=False, corners_for=3, corners_against=5),
)


class _NetworkSource:
    def fetch_team_history(self, team: str, competition: str | None = None) -> list[TeamMatchStats]:
        return [record for record in _NETWORK_HISTORY if record.team.casefold() == team.casefold()]

    def fetch_fixtures(self, competition: str) -> list[Fixture]:
        return [Fixture("A", "Z", competition=competition)]


@register_source("network_test")
def _network_factory() -> _NetworkSource:
    return _NetworkSource()


def test_network_schedule_adjustment_propagates_strength() -> None:
    """A result against strong D is valued above the same result against weak F."""
    rates = compute_rates(_NETWORK_HISTORY)
    assert rates.attack_for("A") > rates.attack_for("Z")
    assert rates.defence_weakness_for("F") > rates.defence_weakness_for("D")
    assert rates.corner_attack_for("A") > rates.corner_attack_for("Z")


def test_forecast_loads_indirect_comparison_path() -> None:
    """One-hop opponent expansion creates the requested A-D-F-Z chain."""
    forecast = forecast_fixture("A", "Z", source="network_test")
    assert forecast.matchup_context is not None
    assert ("A", "D", "F", "Z") in forecast.matchup_context.connection_paths
    assert {record.team for record in forecast.history} == {"A", "D", "F", "Z"}


def test_head_to_head_and_recent_form_are_explicit() -> None:
    """Direct meetings are counted once and newer form dominates old results."""
    old = date.today() - timedelta(days=500)
    history = [
        _record("A", "Z", 2, 1),
        _record("Z", "A", 1, 2, is_home=False),
        _record("A", "Q", 0, 3, match_date=old),
    ]
    context = build_matchup_context(
        history,
        "A",
        "Z",
        poisson_grid(1.4, 1.0, 8),
        CornersPrediction(5.0, 5.0, 10.0),
        CardsPrediction(3.0, 0.1, 3.1),
    )
    assert context.head_to_head_matches == 1
    assert context.home_head_to_head_wins == 1
    assert context.home_form.points_per_match > 2.0
    assert context.home_form.recent_results[0].startswith("W 2-1")
