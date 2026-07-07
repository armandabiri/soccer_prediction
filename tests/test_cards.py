"""T17 acceptance: card expectations and over/under lines are well-formed."""

from __future__ import annotations

from soccer_prediction.models import TeamMatchStats
from soccer_prediction.predictors import CardsPredictor


def test_card_lines_valid(sample_history: list[TeamMatchStats]) -> None:
    """Expected counts are non-negative and line probabilities are valid."""
    predictor = CardsPredictor()
    predictor.fit(sample_history)
    prediction = predictor.predict("Brazil", "Argentina")
    assert prediction.yellows_expected >= 0.0
    assert prediction.reds_expected >= 0.0
    assert prediction.total_expected >= 0.0
    assert all(0.0 <= probability <= 1.0 for probability in prediction.over_under_lines.values())
    assert prediction.booking_points_expected is not None
