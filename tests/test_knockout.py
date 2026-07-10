"""Extra-time and penalty-shootout (knockout) predictions."""

from __future__ import annotations

import math

from soccer_prediction.models import ScorelineGrid
from soccer_prediction.predictors import predict_knockout, shootout_win_probability
from soccer_prediction.public import forecast_fixture


def _grid() -> ScorelineGrid:
    return ScorelineGrid(2, 2, ((0.20, 0.10, 0.05), (0.15, 0.12, 0.03), (0.10, 0.05, 0.20)))


def test_shootout_equal_conversion_is_fair() -> None:
    """Equal penalty conversion gives an exactly fair shootout."""
    assert math.isclose(shootout_win_probability(0.75, 0.75), 0.5, abs_tol=1e-9)
    assert math.isclose(shootout_win_probability(0.70, 0.70), 0.5, abs_tol=1e-9)


def test_shootout_rewards_better_conversion() -> None:
    """A higher conversion rate wins the shootout more often, within [0, 1]."""
    edge = shootout_win_probability(0.82, 0.68)
    assert 0.5 < edge < 1.0
    # symmetry: swapping the sides complements the probability.
    assert math.isclose(edge + shootout_win_probability(0.68, 0.82), 1.0, abs_tol=1e-9)


def test_advance_and_decomposition_are_coherent() -> None:
    """Advancement sums to one and the normal/extra-time/penalty split sums to one."""
    knockout = predict_knockout(_grid())
    assert math.isclose(knockout.home_advance + knockout.away_advance, 1.0, abs_tol=1e-9)
    stages = knockout.decided_in_normal_time + knockout.decided_in_extra_time + knockout.goes_to_penalties
    assert math.isclose(stages, 1.0, abs_tol=1e-9)
    assert knockout.goes_to_penalties <= knockout.goes_to_extra_time + 1e-9
    assert 0.66 <= knockout.home_penalty_conversion <= 0.83
    assert 0.66 <= knockout.away_penalty_conversion <= 0.83


def test_forecast_includes_knockout() -> None:
    """forecast_fixture attaches a knockout prediction."""
    forecast = forecast_fixture("Brazil", "Argentina", source="bundled_wc2026")
    assert forecast.knockout is not None
    assert math.isclose(forecast.knockout.home_advance + forecast.knockout.away_advance, 1.0, abs_tol=1e-6)
