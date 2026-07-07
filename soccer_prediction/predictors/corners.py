"""Corners total and minimum predictor."""

from __future__ import annotations

from collections.abc import Sequence

from soccer_prediction.features import RateBook, compute_rates
from soccer_prediction.models import CornersPrediction, TeamMatchStats
from soccer_prediction.predictors.poisson import poisson_tail_at_least

__all__ = ["CornersPredictor"]


class CornersPredictor:
    """Overdispersed corners approximation using shrunk team rates."""

    def __init__(self) -> None:
        self._rates = compute_rates([])

    def fit(self, history: Sequence[TeamMatchStats]) -> None:
        """Fit corner rates."""
        self._rates = compute_rates(history)

    def predict(self, home: str, away: str) -> CornersPrediction:
        """Return total and minimum corner estimates."""
        home_expected, away_expected = _corner_expectations(self._rates, home, away)
        total_expected = home_expected + away_expected
        total_lines = {line: poisson_tail_at_least(total_expected, int(line + 0.5)) for line in (7.5, 8.5, 9.5, 10.5)}
        home_minimum = _quantile_floor(home_expected, 0.10)
        away_minimum = _quantile_floor(away_expected, 0.10)
        prob_at_least = {threshold: poisson_tail_at_least(total_expected, threshold) for threshold in range(6, 13)}
        return CornersPrediction(
            home_expected,
            away_expected,
            total_expected,
            total_lines,
            home_minimum,
            away_minimum,
            prob_at_least,
        )


def _corner_expectations(rates: RateBook, home: str, away: str) -> tuple[float, float]:
    home_rates = rates.for_team(home)
    away_rates = rates.for_team(away)
    home_expected = max(0.1, (home_rates.corners_for + away_rates.corners_against) / 2.0 + 0.25)
    away_expected = max(0.1, (away_rates.corners_for + home_rates.corners_against) / 2.0)
    return home_expected, away_expected


def _quantile_floor(lam: float, quantile: float) -> int:
    cumulative = 0.0
    for value in range(31):
        cumulative += poisson_tail_at_least(lam, value) - poisson_tail_at_least(lam, value + 1)
        if cumulative >= quantile:
            return value
    return 30
