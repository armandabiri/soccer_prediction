"""Robust mixture of complementary scoreline models."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from soccer_prediction.models import MarketPrediction, ScorelineGrid, TeamMatchStats
from soccer_prediction.predictors.base import Predictor, register_model
from soccer_prediction.predictors.bivariate_poisson import BivariatePoissonPredictor
from soccer_prediction.predictors.dixon_coles import DixonColesPredictor
from soccer_prediction.predictors.markets import derive_markets
from soccer_prediction.predictors.monte_carlo import MonteCarloPredictor
from soccer_prediction.predictors.negative_binomial import NegativeBinomialPredictor

__all__ = ["EnsemblePredictor"]

_DEFAULT_WEIGHTS = {
    "dixon_coles": 0.30,
    "negative_binomial": 0.25,
    "bivariate_poisson": 0.20,
    "monte_carlo": 0.25,
}


class EnsemblePredictor:
    """Average structurally different models to reduce single-model risk."""

    def __init__(self, weights: Mapping[str, float] | None = None) -> None:
        raw_weights = dict(_DEFAULT_WEIGHTS if weights is None else weights)
        if not raw_weights or any(weight < 0 for weight in raw_weights.values()):
            raise ValueError("ensemble weights must be non-negative and non-empty")
        total = sum(raw_weights.values())
        if total <= 0:
            raise ValueError("at least one ensemble weight must be positive")
        self.weights = {name: weight / total for name, weight in raw_weights.items() if weight > 0}
        factories: dict[str, Predictor] = {
            "dixon_coles": DixonColesPredictor(),
            "negative_binomial": NegativeBinomialPredictor(),
            "bivariate_poisson": BivariatePoissonPredictor(),
            "monte_carlo": MonteCarloPredictor(),
        }
        try:
            self._models = {name: factories[name] for name in self.weights}
        except KeyError as exc:
            raise ValueError(f"unsupported ensemble component {exc.args[0]!r}") from exc

    def fit(self, history: Sequence[TeamMatchStats]) -> None:
        """Fit every component to the same history."""
        for model in self._models.values():
            model.fit(history)

    def predict_scoreline(self, home: str, away: str) -> ScorelineGrid:
        """Return the weighted linear probability pool of component grids."""
        grids = {name: model.predict_scoreline(home, away) for name, model in self._models.items()}
        first = next(iter(grids.values()))
        rows = []
        for home_goals in range(first.home_goals_max + 1):
            row = []
            for away_goals in range(first.away_goals_max + 1):
                probability = sum(
                    self.weights[name] * grid.probabilities[home_goals][away_goals]
                    for name, grid in grids.items()
                )
                row.append(probability)
            rows.append(tuple(row))
        total = sum(value for row in rows for value in row)
        normalized = tuple(tuple(value / total for value in row) for row in rows)
        return ScorelineGrid(first.home_goals_max, first.away_goals_max, normalized)

    def predict_market(self, home: str, away: str, market: str) -> MarketPrediction:
        """Predict a market from the pooled scoreline distribution."""
        return derive_markets(self.predict_scoreline(home, away))[market]


@register_model("ensemble")
def _factory() -> EnsemblePredictor:
    return EnsemblePredictor()
