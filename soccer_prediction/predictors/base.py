"""Predictor protocol and registry."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date
from typing import Protocol

from soccer_prediction.models import MarketPrediction, ScorelineGrid, TeamMatchStats

__all__ = ["Predictor", "PredictorFactory", "get_model", "list_models", "register_model"]


class Predictor(Protocol):
    """Common model strategy interface."""

    def fit(self, history: Sequence[TeamMatchStats], *, as_of: date | None = None) -> None:
        """Fit model state from history."""

    def predict_scoreline(self, home: str, away: str, *, neutral_venue: bool = False) -> ScorelineGrid:
        """Predict a scoreline grid."""

    def predict_market(
        self,
        home: str,
        away: str,
        market: str,
        *,
        neutral_venue: bool = False,
    ) -> MarketPrediction:
        """Predict one named market."""


PredictorFactory = Callable[[], Predictor]
_MODEL_REGISTRY: dict[str, PredictorFactory] = {}


def register_model(name: str) -> Callable[[PredictorFactory], PredictorFactory]:
    """Register a predictor factory."""

    def decorator(factory: PredictorFactory) -> PredictorFactory:
        normalized = name.strip().lower().replace("-", "_")
        if not normalized:
            raise ValueError("model name cannot be empty")
        _MODEL_REGISTRY[normalized] = factory
        return factory

    return decorator


def get_model(name: str) -> Predictor:
    """Create a registered predictor by name."""
    normalized = name.strip().lower().replace("-", "_")
    try:
        return _MODEL_REGISTRY[normalized]()
    except KeyError as exc:
        available = ", ".join(list_models()) or "none"
        raise KeyError(f"unknown model {name!r}; available: {available}") from exc


def list_models() -> tuple[str, ...]:
    """Return registered model names."""
    return tuple(sorted(_MODEL_REGISTRY))
