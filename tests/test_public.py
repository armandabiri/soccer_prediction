"""T21 acceptance: the public facade returns a fully populated forecast."""

from __future__ import annotations

from soccer_prediction.models import CardsPrediction, CornersPrediction, MatchForecast, PerHalfPrediction
from soccer_prediction.public import forecast_fixture, predict_match


def test_forecast_fixture_shape() -> None:
    """forecast_fixture returns every market for a fixture using bundled data."""
    forecast = forecast_fixture("Brazil", "Argentina", source="bundled_wc2026")
    assert isinstance(forecast, MatchForecast)
    assert isinstance(forecast.corners, CornersPrediction)
    assert isinstance(forecast.per_half, PerHalfPrediction)
    assert isinstance(forecast.cards, CardsPrediction)
    assert 0.0 <= forecast.result.probability <= 1.0
    assert forecast.corners.total_expected > 0.0
    assert forecast.model_name == "ensemble"
    assert forecast.scenario_analysis is not None
    assert len(forecast.scenario_analysis.model_estimates) == 6
    assert forecast.scenario_analysis.simulations > 0
    assert forecast.ensemble_scoreline == forecast.correct_score
    for estimate in forecast.scenario_analysis.model_estimates:
        assert estimate.home_win_interval[0] <= estimate.home_win <= estimate.home_win_interval[1]
        assert estimate.draw_interval[0] <= estimate.draw <= estimate.draw_interval[1]
        assert estimate.away_win_interval[0] <= estimate.away_win <= estimate.away_win_interval[1]


def test_predict_match_single_market() -> None:
    """predict_match returns a single named market for the fixture."""
    btts = predict_match("Brazil", "Argentina", "btts", source="bundled_wc2026")
    assert 0.0 <= btts.probability <= 1.0


def test_selected_model_is_distinct_from_ensemble_conclusion() -> None:
    """A non-default selection controls headline markets while the ensemble remains available."""
    forecast = forecast_fixture("Brazil", "Argentina", model="poisson", source="bundled_wc2026")
    assert forecast.scenario_analysis is not None
    selected = next(item for item in forecast.scenario_analysis.model_estimates if item.is_selected)
    ensemble = next(item for item in forecast.scenario_analysis.model_estimates if item.is_ensemble)
    assert selected.model_name == "poisson"
    assert forecast.correct_score.home_draw_away() == (selected.home_win, selected.draw, selected.away_win)
    assert forecast.ensemble_scoreline is not None
    assert forecast.ensemble_scoreline.home_draw_away() == (ensemble.home_win, ensemble.draw, ensemble.away_win)


def test_neutral_prior_fixture_is_symmetric() -> None:
    """Equal unseen teams have no artificial home edge at a neutral venue."""
    forecast = forecast_fixture("A", "B", source="auto", neutral_venue=True)
    home, _draw, away = forecast.correct_score.home_draw_away()
    assert abs(home - away) < 0.01
