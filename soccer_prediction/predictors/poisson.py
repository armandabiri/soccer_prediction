"""Independent-Poisson goal model."""

from __future__ import annotations

import math
from collections.abc import Sequence

from soccer_prediction.config import load_config
from soccer_prediction.features import RateBook, compute_rates
from soccer_prediction.models import MarketPrediction, ScorelineGrid, TeamMatchStats
from soccer_prediction.predictors.base import register_model
from soccer_prediction.predictors.markets import derive_markets

__all__ = ["PoissonPredictor", "poisson_grid", "poisson_tail_at_least"]


class PoissonPredictor:
    """Independent-Poisson predictor with rate shrinkage."""

    def __init__(self, max_goals: int | None = None) -> None:
        self.max_goals = load_config().model.max_goals if max_goals is None else max_goals
        self._rates = compute_rates([])

    def fit(self, history: Sequence[TeamMatchStats]) -> None:
        """Fit team rates from match history."""
        self._rates = compute_rates(history)

    def predict_scoreline(self, home: str, away: str) -> ScorelineGrid:
        """Predict a normalized scoreline grid."""
        home_lambda, away_lambda = expected_goals(self._rates, home, away)
        return poisson_grid(home_lambda, away_lambda, self.max_goals)

    def predict_market(self, home: str, away: str, market: str) -> MarketPrediction:
        """Predict a market derived from the scoreline grid."""
        markets = derive_markets(self.predict_scoreline(home, away))
        try:
            return markets[market]
        except KeyError as exc:
            raise KeyError(f"unsupported market {market!r}") from exc


def expected_goals(rates: RateBook, home: str, away: str) -> tuple[float, float]:
    """Estimate home and away goal expectations."""
    home_rates = rates.for_team(home)
    away_rates = rates.for_team(away)
    prior = max(rates.global_rates.goals_for, 0.8)
    home_lambda = max(0.05, (home_rates.goals_for + away_rates.goals_against) / 2.0 + 0.12 * prior)
    away_lambda = max(0.05, (away_rates.goals_for + home_rates.goals_against) / 2.0)
    return home_lambda, away_lambda


def poisson_grid(home_lambda: float, away_lambda: float, max_goals: int) -> ScorelineGrid:
    """Build a normalized independent-Poisson scoreline grid."""
    home_probs = [_poisson_pmf(goal, home_lambda) for goal in range(max_goals + 1)]
    away_probs = [_poisson_pmf(goal, away_lambda) for goal in range(max_goals + 1)]
    rows = tuple(tuple(home_prob * away_prob for away_prob in away_probs) for home_prob in home_probs)
    total = sum(value for row in rows for value in row)
    return ScorelineGrid(max_goals, max_goals, tuple(tuple(value / total for value in row) for row in rows))


def poisson_tail_at_least(lam: float, threshold: int, max_count: int = 30) -> float:
    """Return P(X >= threshold) for a Poisson variable."""
    if threshold <= 0:
        return 1.0
    below = sum(_poisson_pmf(value, lam) for value in range(threshold))
    remainder = max(0.0, 1.0 - sum(_poisson_pmf(value, lam) for value in range(max_count + 1)))
    return min(1.0, max(0.0, 1.0 - below + remainder))


def _poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


@register_model("poisson")
def _factory() -> PoissonPredictor:
    return PoissonPredictor()
