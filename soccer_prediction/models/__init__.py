"""Typed domain models for soccer_prediction."""

from __future__ import annotations

from .match import Fixture, Match, TeamMatchStats
from .prediction import (
    CardsPrediction,
    CornersPrediction,
    MarketPrediction,
    MatchForecast,
    PerHalfPrediction,
    ScorelineGrid,
)
from .team import Team, TeamRates

__all__ = [
    "CardsPrediction",
    "CornersPrediction",
    "Fixture",
    "MarketPrediction",
    "Match",
    "MatchForecast",
    "PerHalfPrediction",
    "ScorelineGrid",
    "Team",
    "TeamMatchStats",
    "TeamRates",
]
