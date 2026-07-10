"""Dixon-Coles-style low-score correction."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import date

from soccer_prediction.models import MarketPrediction, ScorelineGrid, TeamMatchStats
from soccer_prediction.predictors.base import register_model
from soccer_prediction.predictors.markets import derive_markets
from soccer_prediction.predictors.poisson import PoissonPredictor

__all__ = ["DixonColesPredictor"]

logger = logging.getLogger(__name__)


class DixonColesPredictor:
    """Poisson model with the four-cell Dixon-Coles low-score correction."""

    def __init__(self, draw_boost: float | None = None) -> None:
        self._fixed_draw_boost = draw_boost
        self.draw_boost = 0.06 if draw_boost is None else draw_boost
        self._poisson = PoissonPredictor()

    def fit(self, history: Sequence[TeamMatchStats], *, as_of: date | None = None) -> None:
        """Fit the fallback Poisson model."""
        self._poisson.fit(history, as_of=as_of)
        if self._fixed_draw_boost is None:
            self.draw_boost = _estimate_draw_boost(history)

    def predict_scoreline(self, home: str, away: str, *, neutral_venue: bool = False) -> ScorelineGrid:
        """Predict a scoreline grid with low-score dependence."""
        base = self._poisson.predict_scoreline(home, away, neutral_venue=neutral_venue)
        rows = [list(row) for row in base.probabilities]
        home_lambda = sum(
            home_goals * probability
            for home_goals, row in enumerate(base.probabilities)
            for probability in row
        )
        away_lambda = sum(
            away_goals * probability
            for row in base.probabilities
            for away_goals, probability in enumerate(row)
        )
        rho = -min(0.18, max(0.0, self.draw_boost))
        factors = {
            (0, 0): 1.0 - home_lambda * away_lambda * rho,
            (0, 1): 1.0 + home_lambda * rho,
            (1, 0): 1.0 + away_lambda * rho,
            (1, 1): 1.0 - rho,
        }
        for (home_goals, away_goals), factor in factors.items():
            if home_goals <= base.home_goals_max and away_goals <= base.away_goals_max:
                rows[home_goals][away_goals] *= max(0.01, factor)
        total = sum(value for row in rows for value in row)
        corrected = tuple(tuple(value / total for value in row) for row in rows)
        logger.debug("applied four-cell Dixon-Coles correction for %s v %s", home, away)
        return ScorelineGrid(base.home_goals_max, base.away_goals_max, corrected)

    def predict_market(
        self, home: str, away: str, market: str, *, neutral_venue: bool = False
    ) -> MarketPrediction:
        """Predict a market derived from the corrected grid."""
        return derive_markets(self.predict_scoreline(home, away, neutral_venue=neutral_venue))[market]


@register_model("dixon_coles")
def _factory() -> DixonColesPredictor:
    return DixonColesPredictor()


def _estimate_draw_boost(history: Sequence[TeamMatchStats]) -> float:
    """Adapt the low-score correction to the observed low-draw frequency."""
    if not history:
        return 0.06
    low_draws = sum(record.goals_for == record.goals_against <= 1 for record in history)
    rate = low_draws / len(history)
    return min(0.18, max(0.01, 0.04 + 0.35 * (rate - 0.20)))
