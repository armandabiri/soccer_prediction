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
from .strategy import (
    Allocation,
    BettingStrategy,
    ContractEvaluation,
    ContractQuote,
    ExitStage,
    LiveMatchContext,
    LiveScorePlan,
    PathLedgerRow,
    PresetSummary,
    QuoteSnapshot,
    StrategyRequest,
)
from .team import Team, TeamRates

__all__ = [
    "Allocation",
    "BettingStrategy",
    "CardsPrediction",
    "CornersPrediction",
    "ContractEvaluation",
    "ContractQuote",
    "Fixture",
    "ExitStage",
    "KnockoutPrediction",
    "MarketPrediction",
    "Match",
    "MatchForecast",
    "LiveMatchContext",
    "LiveScorePlan",
    "MatchupContext",
    "ModelEstimate",
    "PerHalfPrediction",
    "PlayerGame",
    "PlayerMarketPrediction",
    "PlayerStats",
    "PathLedgerRow",
    "PresetSummary",
    "QuoteSnapshot",
    "ScorelineGrid",
    "ScenarioAnalysis",
    "ScorerPrediction",
    "Team",
    "TeamForm",
    "TeamMatchStats",
    "TeamRates",
    "StrategyRequest",
]
