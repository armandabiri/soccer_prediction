"""Overdispersed Negative-Binomial goal model."""

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

__all__ = ["NegativeBinomialPredictor", "negative_binomial_grid"]


class NegativeBinomialPredictor:
    """Goal model with a fitted variance above the Poisson mean."""

    def __init__(self, max_goals: int | None = None, dispersion: float | None = None) -> None:
        self.max_goals = load_config().model.max_goals if max_goals is None else max_goals
        self._fixed_dispersion = dispersion
        self.dispersion = 10.0 if dispersion is None else dispersion
        self._rates = compute_rates([])

    def fit(self, history: Sequence[TeamMatchStats], *, as_of: date | None = None) -> None:
        """Fit rates and estimate the Gamma-Poisson dispersion from observed goals."""
        self._rates = compute_rates(history, today=as_of)
        if self._fixed_dispersion is None:
            self.dispersion = _estimate_dispersion(history)

    def predict_scoreline(self, home: str, away: str, *, neutral_venue: bool = False) -> ScorelineGrid:
        """Predict a grid with heavier tails than independent Poisson."""
        home_mean, away_mean = expected_goals(self._rates, home, away, neutral_venue=neutral_venue)
        return negative_binomial_grid(home_mean, away_mean, self.max_goals, self.dispersion)

    def predict_market(
        self, home: str, away: str, market: str, *, neutral_venue: bool = False
    ) -> MarketPrediction:
        """Predict a market derived from the scoreline grid."""
        return derive_markets(self.predict_scoreline(home, away, neutral_venue=neutral_venue))[market]


def negative_binomial_grid(
    home_mean: float,
    away_mean: float,
    max_goals: int,
    dispersion: float,
) -> ScorelineGrid:
    """Build a normalized independent Negative-Binomial scoreline grid."""
    if dispersion <= 0:
        raise ValueError("dispersion must be positive")
    if max_goals < 0:
        raise ValueError("max_goals must be non-negative")
    if max_goals == 0:
        return ScorelineGrid(0, 0, ((1.0,),))
    home_exact = tuple(_negative_binomial_pmf(goal, home_mean, dispersion) for goal in range(max_goals))
    away_exact = tuple(_negative_binomial_pmf(goal, away_mean, dispersion) for goal in range(max_goals))
    home_probs = (*home_exact, max(0.0, 1.0 - sum(home_exact)))
    away_probs = (*away_exact, max(0.0, 1.0 - sum(away_exact)))
    rows = tuple(tuple(home_prob * away_prob for away_prob in away_probs) for home_prob in home_probs)
    return ScorelineGrid(max_goals, max_goals, rows)


def _negative_binomial_pmf(goals: int, mean: float, dispersion: float) -> float:
    log_probability = (
        math.lgamma(goals + dispersion)
        - math.lgamma(dispersion)
        - math.lgamma(goals + 1)
        + dispersion * math.log(dispersion / (dispersion + mean))
        + goals * math.log(mean / (dispersion + mean))
    )
    return math.exp(log_probability)


def _estimate_dispersion(history: Sequence[TeamMatchStats]) -> float:
    if len(history) < 4:
        return 10.0
    goals = [float(record.goals_for) for record in history]
    mean = sum(goals) / len(goals)
    variance = sum((value - mean) ** 2 for value in goals) / (len(goals) - 1)
    if variance <= mean + 0.05:
        return 15.0
    estimate = mean * mean / max(variance - mean, 1e-9)
    return min(30.0, max(1.25, estimate))


@register_model("negative_binomial")
def _factory() -> NegativeBinomialPredictor:
    return NegativeBinomialPredictor()
