"""Player goalscorer and assist market predictor.

Distributes each team's expected goals using shrinkage-adjusted production per
appearance, optionally blending genuine recent form. It then derives separate
score, assist, combined-involvement, and first-scorer probabilities. This is
not a minutes or lineup model; treat the numbers as indicative.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Literal

from soccer_prediction.models import (
    PlayerMarketPrediction,
    PlayerStats,
    ScorelineGrid,
    ScorerPrediction,
)

__all__ = ["predict_scorers", "expected_goals_from_grid"]

_PRIOR_APPEARANCES = 12.0
_RECENT_PRIOR_APPEARANCES = 5.0
_RECENT_WEIGHT = 0.55
_ASSISTED_GOAL_SHARE = 0.72
_POSITION_RATES = {
    "FW": (0.28, 0.16),
    "MF": (0.10, 0.18),
    "DF": (0.045, 0.07),
    "GK": (0.005, 0.005),
}


def expected_goals_from_grid(grid: ScorelineGrid) -> tuple[float, float]:
    """Return (home, away) expected goals implied by a scoreline grid."""
    home_xg = 0.0
    away_xg = 0.0
    for home_goals, row in enumerate(grid.probabilities):
        for away_goals, probability in enumerate(row):
            home_xg += home_goals * probability
            away_xg += away_goals * probability
    return home_xg, away_xg


def predict_scorers(
    grid: ScorelineGrid,
    home_players: Sequence[PlayerStats],
    away_players: Sequence[PlayerStats],
) -> ScorerPrediction:
    """Rank both squads by scoring markets derived from the scoreline grid."""
    home_xg, away_xg = expected_goals_from_grid(grid)
    p_no_goal = grid.probabilities[0][0] if grid.probabilities and grid.probabilities[0] else 0.0
    total_xg = max(1e-9, home_xg + away_xg)
    predictions = [
        *_team_predictions(home_players, home_xg, total_xg, p_no_goal),
        *_team_predictions(away_players, away_xg, total_xg, p_no_goal),
    ]
    predictions.sort(key=lambda item: item.anytime_scorer, reverse=True)
    return ScorerPrediction(players=tuple(predictions))


def _team_predictions(
    players: Sequence[PlayerStats],
    team_xg: float,
    total_xg: float,
    p_no_goal: float,
) -> list[PlayerMarketPrediction]:
    goal_rates = [_production_rate(player, "goals") for player in players]
    assist_rates = [_production_rate(player, "assists") for player in players]
    total_goal_rate = sum(goal_rates)
    total_assist_rate = sum(assist_rates)
    out: list[PlayerMarketPrediction] = []
    for player, goal_rate, assist_rate in zip(players, goal_rates, assist_rates, strict=True):
        goal_share = goal_rate / total_goal_rate if total_goal_rate else 0.0
        assist_share = assist_rate / total_assist_rate if total_assist_rate else 0.0
        expected_goals = team_xg * goal_share
        expected_assists = team_xg * _ASSISTED_GOAL_SHARE * assist_share
        score_probability = 1.0 - math.exp(-expected_goals)
        assist_probability = 1.0 - math.exp(-expected_assists)
        score_or_assist = 1.0 - math.exp(-(expected_goals + expected_assists))
        first_scorer = (expected_goals / total_xg) * (1.0 - p_no_goal)
        recent_appearances, recent_goals, recent_assists, estimated = _recent_form(player)
        out.append(
            PlayerMarketPrediction(
                player=player.name,
                team=player.team,
                position=player.position,
                expected_goals=expected_goals,
                expected_assists=expected_assists,
                anytime_scorer=score_probability,
                to_score_or_assist=score_or_assist,
                first_scorer=first_scorer,
                score_probability=score_probability,
                assist_probability=assist_probability,
                recent_appearances=recent_appearances,
                recent_goals=recent_goals,
                recent_assists=recent_assists,
                recent_form_estimated=estimated,
            )
        )
    return out


def _production_rate(player: PlayerStats, kind: Literal["goals", "assists"]) -> float:
    position = player.position.strip().upper()
    goal_prior, assist_prior = _POSITION_RATES.get(position, _POSITION_RATES["MF"])
    prior = goal_prior if kind == "goals" else assist_prior
    career_total = player.goals if kind == "goals" else player.assists
    career_rate = (career_total + prior * _PRIOR_APPEARANCES) / (player.appearances + _PRIOR_APPEARANCES)
    recent_total = player.recent_goals if kind == "goals" else player.recent_assists
    if player.recent_appearances is None or recent_total is None or player.recent_appearances <= 0:
        return career_rate
    recent_rate = (recent_total + career_rate * _RECENT_PRIOR_APPEARANCES) / (
        player.recent_appearances + _RECENT_PRIOR_APPEARANCES
    )
    return career_rate * (1.0 - _RECENT_WEIGHT) + recent_rate * _RECENT_WEIGHT


def _recent_form(player: PlayerStats) -> tuple[int, float, float, bool]:
    if (
        player.recent_appearances is not None
        and player.recent_goals is not None
        and player.recent_assists is not None
        and player.recent_appearances > 0
    ):
        return (
            min(player.recent_appearances, 20),
            float(player.recent_goals),
            float(player.recent_assists),
            False,
        )
    appearances = min(max(player.appearances, 0), 20)
    if player.appearances <= 0:
        return appearances, 0.0, 0.0, True
    scale = appearances / player.appearances
    return appearances, player.goals * scale, player.assists * scale, True
