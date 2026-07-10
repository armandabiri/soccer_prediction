"""Typed domain models for soccer_prediction."""

from __future__ import annotations

from .match import Fixture, Match, TeamMatchStats
from .player import PlayerMarketPrediction, PlayerStats, ScorerPrediction
from .prediction import (
    CardsPrediction,
    CornersPrediction,
    KnockoutPrediction,
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
    "KnockoutPrediction",
    "MarketPrediction",
    "Match",
    "MatchForecast",
    "PerHalfPrediction",
    "PlayerMarketPrediction",
    "PlayerStats",
    "ScorelineGrid",
    "ScorerPrediction",
    "Team",
    "TeamMatchStats",
    "TeamRates",
]
