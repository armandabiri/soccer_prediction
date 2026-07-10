"""Correlated bivariate-Poisson goal model."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date

from soccer_prediction.config import load_config
from soccer_prediction.features import compute_rates
from soccer_prediction.models import MarketPrediction, ScorelineGrid, TeamMatchStats
from soccer_prediction.predictors.base import register_model
from soccer_prediction.predictors.markets import derive_markets
from soccer_prediction.predictors.poisson import expected_goals

__all__ = ["BivariatePoissonPredictor", "bivariate_poisson_grid"]


class BivariatePoissonPredictor:
    """Poisson model with a shared match-tempo scoring component."""

    def __init__(self, max_goals: int | None = None, shared_share: float | None = None) -> None:
        self.max_goals = load_config().model.max_goals if max_goals is None else max_goals
        self._fixed_shared_share = shared_share
        self.shared_share = 0.08 if shared_share is None else shared_share
        self._rates = compute_rates([])

    def fit(self, history: Sequence[TeamMatchStats], *, as_of: date | None = None) -> None:
        """Fit goal rates and estimate positive within-match goal covariance."""
        self._rates = compute_rates(history, today=as_of)
        if self._fixed_shared_share is None:
            self.shared_share = _estimate_shared_share(history)

    def predict_scoreline(self, home: str, away: str, *, neutral_venue: bool = False) -> ScorelineGrid:
        """Predict a correlated scoreline grid."""
        home_mean, away_mean = expected_goals(self._rates, home, away, neutral_venue=neutral_venue)
        shared = min(home_mean, away_mean) * self.shared_share
        return bivariate_poisson_grid(home_mean, away_mean, self.max_goals, shared)

    def predict_market(
        self, home: str, away: str, market: str, *, neutral_venue: bool = False
    ) -> MarketPrediction:
        """Predict a market derived from the scoreline grid."""
        return derive_markets(self.predict_scoreline(home, away, neutral_venue=neutral_venue))[market]


def bivariate_poisson_grid(
    home_mean: float,
    away_mean: float,
    max_goals: int,
    shared_rate: float,
) -> ScorelineGrid:
    """Build a normalized grid from two private and one shared Poisson process."""
    if shared_rate < 0 or shared_rate >= min(home_mean, away_mean):
        raise ValueError("shared_rate must be non-negative and below both means")
    if max_goals < 0:
        raise ValueError("max_goals must be non-negative")
    if max_goals == 0:
        return ScorelineGrid(0, 0, ((1.0,),))
    home_private = home_mean - shared_rate
    away_private = away_mean - shared_rate
    rows = [[0.0 for _ in range(max_goals + 1)] for _ in range(max_goals + 1)]
    for home_goals in range(max_goals):
        for away_goals in range(max_goals):
            probability = sum(
                _poisson_pmf(home_goals - shared, home_private)
                * _poisson_pmf(away_goals - shared, away_private)
                * _poisson_pmf(shared, shared_rate)
                for shared in range(min(home_goals, away_goals) + 1)
            )
            rows[home_goals][away_goals] = probability
    for away_goals in range(max_goals):
        away_marginal = _poisson_pmf(away_goals, away_mean)
        rows[max_goals][away_goals] = max(
            0.0, away_marginal - sum(rows[home][away_goals] for home in range(max_goals))
        )
    for home_goals in range(max_goals):
        home_marginal = _poisson_pmf(home_goals, home_mean)
        rows[home_goals][max_goals] = max(0.0, home_marginal - sum(rows[home_goals][:max_goals]))
    rows[max_goals][max_goals] = max(
        0.0,
        1.0 - sum(value for row in rows for value in row),
    )
    total = sum(value for row in rows for value in row)
    normalized = tuple(tuple(value / total for value in row) for row in rows)
    return ScorelineGrid(max_goals, max_goals, normalized)


def _poisson_pmf(goals: int, rate: float) -> float:
    if rate == 0.0:
        return 1.0 if goals == 0 else 0.0
    return math.exp(-rate) * rate**goals / math.factorial(goals)


def _estimate_shared_share(history: Sequence[TeamMatchStats]) -> float:
    if len(history) < 4:
        return 0.08
    home = [float(record.goals_for) for record in history]
    away = [float(record.goals_against) for record in history]
    home_mean = sum(home) / len(home)
    away_mean = sum(away) / len(away)
    covariance = sum((x - home_mean) * (y - away_mean) for x, y in zip(home, away, strict=True))
    covariance /= len(history) - 1
    pooled_mean = max(0.2, min(home_mean, away_mean))
    return min(0.20, max(0.03, covariance / pooled_mean))


@register_model("bivariate_poisson")
def _factory() -> BivariatePoissonPredictor:
    return BivariatePoissonPredictor()
