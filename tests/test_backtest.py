"""T18 acceptance: walk-forward backtesting trains only on prior matches."""

from __future__ import annotations

from soccer_prediction.calibration import walk_forward
from soccer_prediction.models import TeamMatchStats


def test_no_leakage(sample_history: list[TeamMatchStats]) -> None:
    """Walk-forward completes (its internal leakage guard holds) and predicts."""
    result = walk_forward(sample_history, "poisson")
    assert result.count >= 1
    home_matches = sum(1 for record in sample_history if record.is_home)
    # The earliest match has no prior training data and is skipped.
    assert result.count < home_matches
    for prediction in result.predictions:
        assert round(sum(prediction.probabilities), 6) == 1.0
        assert 0 <= prediction.actual_index <= 2
