"""T16 acceptance: corners give a total and a minimum (low-quantile) estimate."""

from __future__ import annotations

from soccer_prediction.models import TeamMatchStats
from soccer_prediction.predictors import CornersPredictor
from soccer_prediction.predictors.poisson import poisson_tail_at_least


def test_total_and_minimum(sample_history: list[TeamMatchStats]) -> None:
    """Total equals home+away, and the minimum is the 10th-percentile floor."""
    predictor = CornersPredictor()
    predictor.fit(sample_history)
    prediction = predictor.predict("Brazil", "Argentina")
    assert abs(prediction.total_expected - (prediction.home_expected + prediction.away_expected)) < 1e-9
    assert prediction.home_minimum <= round(prediction.home_expected)
    # The minimum is the smallest count whose cumulative probability reaches ~10%:
    # P(X >= minimum + 1) <= 0.90, and P(X >= minimum) > 0.90 once above zero.
    assert poisson_tail_at_least(prediction.home_expected, prediction.home_minimum + 1) <= 0.90
    if prediction.home_minimum > 0:
        assert poisson_tail_at_least(prediction.home_expected, prediction.home_minimum) > 0.90


def test_prob_at_least_is_monotone(sample_history: list[TeamMatchStats]) -> None:
    """Upper-tail 'N or more corners' probability is non-increasing in N."""
    predictor = CornersPredictor()
    predictor.fit(sample_history)
    prediction = predictor.predict("Brazil", "Argentina")
    assert prediction.prob_at_least[6] >= prediction.prob_at_least[12]
