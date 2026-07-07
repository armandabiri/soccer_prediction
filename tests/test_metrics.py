"""T19 acceptance: ranked probability score matches a hand-computed value."""

from __future__ import annotations

import math

import pytest

from soccer_prediction.calibration import brier_score, log_loss, ranked_probability_score


def test_rps_known_value() -> None:
    """RPS of (0.2, 0.5, 0.3) with a draw outcome equals 0.065."""
    assert math.isclose(ranked_probability_score((0.2, 0.5, 0.3), 1), 0.065)


def test_metrics_bounds() -> None:
    """A perfect forecast scores zero loss; log-loss is non-negative."""
    assert brier_score((0.0, 1.0, 0.0), 1) == 0.0
    assert log_loss((0.2, 0.5, 0.3), 1) >= 0.0


def test_invalid_probabilities_raise() -> None:
    """Probabilities that do not sum to one are rejected."""
    with pytest.raises(ValueError):
        ranked_probability_score((0.2, 0.2, 0.2), 1)
