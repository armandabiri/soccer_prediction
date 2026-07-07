"""Player goalscorer/assist market predictions (who might score, score or assist)."""

from __future__ import annotations

from soccer_prediction.models import PlayerStats, ScorelineGrid
from soccer_prediction.predictors import predict_scorers
from soccer_prediction.predictors.scorers import expected_goals_from_grid
from soccer_prediction.public import forecast_fixture


def _grid() -> ScorelineGrid:
    return ScorelineGrid(2, 2, ((0.20, 0.10, 0.05), (0.15, 0.12, 0.03), (0.10, 0.05, 0.20)))


def test_expected_goals_from_grid() -> None:
    """Expected goals derived from a grid are positive and finite."""
    home_xg, away_xg = expected_goals_from_grid(_grid())
    assert home_xg > 0.0
    assert away_xg > 0.0


def test_predict_scorers_ranks_and_bounds() -> None:
    """Players rank by anytime probability; score-or-assist dominates anytime."""
    grid = _grid()
    home = [PlayerStats("A", "H", "FW", 50, 20, 5), PlayerStats("B", "H", "MF", 50, 5, 15)]
    away = [PlayerStats("C", "A", "FW", 50, 15, 3)]
    prediction = predict_scorers(grid, home, away)
    assert len(prediction.players) == 3
    anytime = [player.anytime_scorer for player in prediction.players]
    assert anytime == sorted(anytime, reverse=True)
    for player in prediction.players:
        assert 0.0 <= player.anytime_scorer <= 1.0
        assert player.to_score_or_assist >= player.anytime_scorer - 1e-9
    # first-goalscorer probabilities cannot exceed P(at least one goal) <= 1.
    assert sum(player.first_scorer for player in prediction.players) <= 1.0 + 1e-9


def test_empty_squads_yield_no_players() -> None:
    """No squad data means no player markets, not an error."""
    assert predict_scorers(_grid(), [], []).players == ()


def test_forecast_includes_scorers() -> None:
    """A source that exposes squads attaches ranked scorer markets to the forecast."""
    forecast = forecast_fixture("Switzerland", "Colombia", source="bundled_swi_col")
    assert forecast.scorers is not None
    assert len(forecast.scorers.players) == 20
    assert all(0.0 <= player.to_score_or_assist <= 1.0 for player in forecast.scorers.players)


def test_forecast_without_players_has_no_scorers() -> None:
    """The auto source (priors only) produces no player markets."""
    assert forecast_fixture("Switzerland", "Colombia", source="auto").scorers is None
