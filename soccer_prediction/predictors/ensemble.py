"""Regularized, validation-aware pool of complementary scoreline models."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from soccer_prediction.models import MarketPrediction, ScorelineGrid, TeamMatchStats
from soccer_prediction.predictors.base import Predictor, register_model
from soccer_prediction.predictors.bivariate_poisson import BivariatePoissonPredictor
from soccer_prediction.predictors.dixon_coles import DixonColesPredictor
from soccer_prediction.predictors.markets import derive_markets
from soccer_prediction.predictors.monte_carlo import MonteCarloPredictor
from soccer_prediction.predictors.negative_binomial import NegativeBinomialPredictor

__all__ = ["DEFAULT_ENSEMBLE_WEIGHTS", "EnsemblePredictor", "pool_scoreline_grids"]

DEFAULT_ENSEMBLE_WEIGHTS = {
    "dixon_coles": 0.35,
    "negative_binomial": 0.15,
    "bivariate_poisson": 0.30,
    "monte_carlo": 0.20,
}


@dataclass(frozen=True, slots=True)
class _ValidationMatch:
    match_date: date
    home_team: str
    away_team: str
    home_score: int
    away_score: int


class EnsemblePredictor:
    """Pool models, modestly adapting weights to a recent temporal holdout."""

    def __init__(self, weights: Mapping[str, float] | None = None) -> None:
        self._custom_weights = weights is not None
        self.weights = _normalize_weights(DEFAULT_ENSEMBLE_WEIGHTS if weights is None else weights)
        self._models = _new_models(self.weights)
        self.validation_log_losses: dict[str, float] = {}
        self.validation_matches = 0
        self.validation_from: date | None = None
        self.validation_to: date | None = None
        self.weight_method = "static_prior"

    def fit(self, history: Sequence[TeamMatchStats], *, as_of: date | None = None) -> None:
        """Calibrate weights on a bounded holdout, then fit components on all prior data."""
        if not self._custom_weights:
            calibration = _calibrated_weights(history)
            self.weights = calibration[0]
            self.validation_log_losses = calibration[1]
            self.validation_matches = calibration[2]
            self.validation_from = calibration[3]
            self.validation_to = calibration[4]
            self.weight_method = calibration[5]
        self._models = _new_models(self.weights)
        for model in self._models.values():
            model.fit(history, as_of=as_of)

    def predict_component_grids(
        self,
        home: str,
        away: str,
        *,
        neutral_venue: bool = False,
    ) -> dict[str, ScorelineGrid]:
        """Return each fitted component grid exactly once."""
        return {
            name: model.predict_scoreline(home, away, neutral_venue=neutral_venue)
            for name, model in self._models.items()
        }

    def predict_scoreline(self, home: str, away: str, *, neutral_venue: bool = False) -> ScorelineGrid:
        """Return the regularized weighted linear probability pool."""
        grids = self.predict_component_grids(home, away, neutral_venue=neutral_venue)
        return pool_scoreline_grids(grids, self.weights)

    def predict_market(
        self, home: str, away: str, market: str, *, neutral_venue: bool = False
    ) -> MarketPrediction:
        """Predict a market from the pooled scoreline distribution."""
        grid = self.predict_scoreline(home, away, neutral_venue=neutral_venue)
        return derive_markets(grid)[market]


def pool_scoreline_grids(
    grids: Mapping[str, ScorelineGrid],
    weights: Mapping[str, float],
) -> ScorelineGrid:
    """Pool same-shaped grids cell by cell and normalize numerical drift."""
    normalized_weights = _normalize_weights(weights)
    missing = set(normalized_weights) - set(grids)
    if missing:
        raise ValueError(f"missing grids for ensemble components: {', '.join(sorted(missing))}")
    first = grids[next(iter(normalized_weights))]
    if any(
        grid.home_goals_max != first.home_goals_max or grid.away_goals_max != first.away_goals_max
        for name, grid in grids.items()
        if name in normalized_weights
    ):
        raise ValueError("ensemble grids must have the same shape")
    rows = tuple(
        tuple(
            sum(
                normalized_weights[name] * grids[name].probabilities[home_goals][away_goals]
                for name in normalized_weights
            )
            for away_goals in range(first.away_goals_max + 1)
        )
        for home_goals in range(first.home_goals_max + 1)
    )
    total = sum(value for row in rows for value in row)
    return ScorelineGrid(
        first.home_goals_max,
        first.away_goals_max,
        tuple(tuple(value / total for value in row) for row in rows),
    )


def _normalize_weights(weights: Mapping[str, float]) -> dict[str, float]:
    supported = set(DEFAULT_ENSEMBLE_WEIGHTS)
    if not weights or any(weight < 0 for weight in weights.values()):
        raise ValueError("ensemble weights must be non-negative and non-empty")
    unknown = set(weights) - supported
    if unknown:
        raise ValueError(f"unsupported ensemble component {sorted(unknown)[0]!r}")
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("at least one ensemble weight must be positive")
    return {name: weight / total for name, weight in weights.items() if weight > 0}


def _new_models(weights: Mapping[str, float], *, validation: bool = False) -> dict[str, Predictor]:
    available: dict[str, Predictor] = {
        "dixon_coles": DixonColesPredictor(),
        "negative_binomial": NegativeBinomialPredictor(),
        "bivariate_poisson": BivariatePoissonPredictor(),
        "monte_carlo": MonteCarloPredictor(simulations=2_500 if validation else None),
    }
    return {name: available[name] for name in weights}


def _calibrated_weights(
    history: Sequence[TeamMatchStats],
) -> tuple[dict[str, float], dict[str, float], int, date | None, date | None, str]:
    matches = _canonical_matches(history)
    if len(matches) < 14:
        return dict(DEFAULT_ENSEMBLE_WEIGHTS), {}, 0, None, None, "static_prior_insufficient_history"
    validation_count = min(12, max(6, len(matches) // 4))
    cutoff = matches[-validation_count].match_date
    train = [record for record in history if record.date < cutoff]
    validation = tuple(match for match in matches if match.match_date >= cutoff)
    if len(train) < 12 or len(validation) < 6:
        return dict(DEFAULT_ENSEMBLE_WEIGHTS), {}, 0, None, None, "static_prior_insufficient_history"
    losses: dict[str, float] = {}
    for name, model in _new_models(DEFAULT_ENSEMBLE_WEIGHTS, validation=True).items():
        model.fit(train, as_of=cutoff)
        loss = 0.0
        for match in validation:
            probabilities = model.predict_scoreline(match.home_team, match.away_team).home_draw_away()
            loss -= math.log(max(probabilities[_actual_index(match)], 1e-12))
        losses[name] = loss / len(validation)
    best_loss = min(losses.values())
    skill = {name: math.exp(-3.0 * (loss - best_loss)) for name, loss in losses.items()}
    skill = _normalize_weights(skill)
    strength = min(0.45, len(validation) / 30.0)
    blended = {
        name: (1.0 - strength) * DEFAULT_ENSEMBLE_WEIGHTS[name] + strength * skill[name]
        for name in DEFAULT_ENSEMBLE_WEIGHTS
    }
    return (
        _normalize_weights(blended),
        losses,
        len(validation),
        validation[0].match_date,
        validation[-1].match_date,
        "regularized_temporal_holdout",
    )


def _canonical_matches(history: Sequence[TeamMatchStats]) -> tuple[_ValidationMatch, ...]:
    unique: dict[tuple[date, str, str], _ValidationMatch] = {}
    for record in history:
        if record.is_home:
            home, away = record.team, record.opponent
            home_score, away_score = record.goals_for, record.goals_against
        else:
            home, away = record.opponent, record.team
            home_score, away_score = record.goals_against, record.goals_for
        key = (record.date, home.casefold(), away.casefold())
        unique[key] = _ValidationMatch(record.date, home, away, home_score, away_score)
    return tuple(sorted(unique.values(), key=lambda item: (item.match_date, item.home_team, item.away_team)))


def _actual_index(match: _ValidationMatch) -> int:
    if match.home_score > match.away_score:
        return 0
    if match.home_score == match.away_score:
        return 1
    return 2


@register_model("ensemble")
def _factory() -> EnsemblePredictor:
    return EnsemblePredictor()
