"""T15 acceptance: per-half grids are valid distributions with sane summaries."""

from __future__ import annotations

from soccer_prediction.models import TeamMatchStats
from soccer_prediction.predictors import HalfTimePredictor


def test_half_probs_valid(sample_history: list[TeamMatchStats]) -> None:
    """Both half grids sum to one and expectations are non-negative."""
    predictor = HalfTimePredictor()
    predictor.fit(sample_history)
    per_half = predictor.predict("Brazil", "Argentina")
    assert round(per_half.first_half_grid.total_probability(), 6) == 1.0
    assert round(per_half.second_half_grid.total_probability(), 6) == 1.0
    assert per_half.first_half_home_expected >= 0.0
    assert per_half.second_half_home_expected >= 0.0
    assert per_half.half_time_result is not None
    assert 0.0 <= per_half.half_time_result.probability <= 1.0
