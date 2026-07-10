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
    assert len(forecast.scenario_analysis.model_estimates) == 5
    assert forecast.scenario_analysis.simulations > 0


def test_predict_match_single_market() -> None:
    """predict_match returns a single named market for the fixture."""
    btts = predict_match("Brazil", "Argentina", "btts", source="bundled_wc2026")
    assert 0.0 <= btts.probability <= 1.0
