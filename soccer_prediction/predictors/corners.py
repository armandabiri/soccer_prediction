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


# League-average per-team corner rates, used when the data source has no corner
# data (e.g. martj42 international results, which carry goals only).
_PRIOR_CORNERS_FOR = 5.1
_PRIOR_CORNERS_AGAINST = 4.9
_HOME_CORNER_EDGE = 0.4


def _corner_rate(value: float, prior: float) -> float:
    """Use the observed corner rate, or a league-average prior when it is absent."""
    return value if value > 0.5 else prior


def _corner_expectations(rates: RateBook, home: str, away: str) -> tuple[float, float]:
    home_rates = rates.for_team(home)
    away_rates = rates.for_team(away)
    home_for = _corner_rate(home_rates.corners_for, _PRIOR_CORNERS_FOR)
    home_against = _corner_rate(home_rates.corners_against, _PRIOR_CORNERS_AGAINST)
    away_for = _corner_rate(away_rates.corners_for, _PRIOR_CORNERS_FOR)
    away_against = _corner_rate(away_rates.corners_against, _PRIOR_CORNERS_AGAINST)
    home_expected = max(1.0, (home_for + away_against) / 2.0 + _HOME_CORNER_EDGE)
    away_expected = max(1.0, (away_for + home_against) / 2.0)
    return home_expected, away_expected


def _quantile_floor(lam: float, quantile: float) -> int:
    cumulative = 0.0
    for value in range(31):
        cumulative += poisson_tail_at_least(lam, value) - poisson_tail_at_least(lam, value + 1)
        if cumulative >= quantile:
            return value
    return 30
