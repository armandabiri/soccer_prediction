"""Typed domain models for soccer_prediction."""

from __future__ import annotations

from .match import Fixture, Match, TeamMatchStats
from .player import PlayerGame, PlayerMarketPrediction, PlayerStats, ScorerPrediction
from .prediction import (
    CardsPrediction,
    CornersPrediction,
    KnockoutPrediction,
    MarketPrediction,
    MatchForecast,
    MatchupContext,
    ModelEstimate,
    PerHalfPrediction,
    ScenarioAnalysis,
    ScorelineGrid,
    TeamForm,
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
    "MatchupContext",
    "ModelEstimate",
    "PerHalfPrediction",
    "PlayerGame",
    "PlayerMarketPrediction",
    "PlayerStats",
    "ScorelineGrid",
    "ScenarioAnalysis",
    "ScorerPrediction",
    "Team",
    "TeamForm",
    "TeamMatchStats",
    "TeamRates",
]
