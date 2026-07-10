"""Player goalscorer/assist market predictions (who might score, score or assist)."""

from __future__ import annotations

import pytest

from soccer_prediction.models import PlayerStats, ScorelineGrid
from soccer_prediction.predictors import predict_scorers
from soccer_prediction.predictors.scorers import expected_goals_from_grid
from soccer_prediction.public import forecast_fixture
from soccer_prediction.reporting import render_html


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
        assert player.score_probability == player.anytime_scorer
        assert 0.0 <= player.assist_probability <= 1.0
        assert player.to_score_or_assist >= player.anytime_scorer - 1e-9
        assert player.to_score_or_assist >= player.assist_probability - 1e-9
    # first-goalscorer probabilities cannot exceed P(at least one goal) <= 1.
    assert sum(player.first_scorer for player in prediction.players) <= 1.0 + 1e-9


def test_empty_squads_yield_no_players() -> None:
    """No squad data means no player markets, not an error."""
    assert predict_scorers(_grid(), [], []).players == ()


def test_recent_form_is_used_and_fallback_is_marked() -> None:
    """Real recent production affects ranking; aggregate fallback stays explicit."""
    players = [
        PlayerStats("Hot", "H", "FW", 50, 10, 5, 10, 8, 3),
        PlayerStats("Cold", "H", "FW", 50, 10, 5, 10, 0, 1),
        PlayerStats("Estimated", "H", "MF", 40, 8, 12),
    ]
    predictions = predict_scorers(_grid(), players, []).players
    by_name = {player.player: player for player in predictions}
    assert by_name["Hot"].score_probability > by_name["Cold"].score_probability
    assert by_name["Hot"].recent_goals == 8
    assert by_name["Hot"].recent_form_estimated is False
    assert by_name["Estimated"].recent_appearances == 20
    assert by_name["Estimated"].recent_form_estimated is True


def test_recent_form_requires_a_complete_max_20_sample() -> None:
    """Partial or oversized recent-form payloads are rejected."""
    with pytest.raises(ValueError):
        PlayerStats("A", "H", "FW", 10, 2, 1, recent_appearances=10)
    with pytest.raises(ValueError):
        PlayerStats("A", "H", "FW", 30, 3, 2, 21, 3, 2)


def test_forecast_includes_scorers() -> None:
    """A source that exposes squads attaches ranked scorer markets to the forecast."""
    forecast = forecast_fixture("Switzerland", "Colombia", source="bundled_swi_col")
    assert forecast.scorers is not None
    assert len(forecast.scorers.players) == 20
    assert all(0.0 <= player.to_score_or_assist <= 1.0 for player in forecast.scorers.players)
    html = render_html(forecast)
    assert "Recent scoring (max 20)" in html
    assert 'class="formbar"' in html
    assert ">Score</th>" in html
    assert ">Assist</th>" in html


def test_forecast_without_players_has_no_scorers() -> None:
    """The auto source (priors only) produces no player markets."""
    assert forecast_fixture("Switzerland", "Colombia", source="auto").scorers is None
