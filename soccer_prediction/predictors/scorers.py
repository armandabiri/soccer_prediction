"""Player goalscorer and assist market predictor.

Distributes each team's expected goals across its squad using historical goal
and assist shares, then derives anytime-scorer, to-score-or-assist, and
first-goalscorer probabilities. This is a share-based approximation, not a
minutes-aware model; treat the numbers as indicative.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from soccer_prediction.models import (
    PlayerMarketPrediction,
    PlayerStats,
    ScorelineGrid,
    ScorerPrediction,
)

__all__ = ["predict_scorers", "expected_goals_from_grid"]


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
    total_goals = sum(player.goals for player in players)
    total_assists = sum(player.assists for player in players)
    out: list[PlayerMarketPrediction] = []
    for player in players:
        goal_share = player.goals / total_goals if total_goals else 0.0
        assist_share = player.assists / total_assists if total_assists else 0.0
        expected_goals = team_xg * goal_share
        expected_assists = team_xg * assist_share
        anytime = 1.0 - math.exp(-expected_goals)
        score_or_assist = 1.0 - math.exp(-(expected_goals + expected_assists))
        first_scorer = (expected_goals / total_xg) * (1.0 - p_no_goal)
        out.append(
            PlayerMarketPrediction(
                player=player.name,
                team=player.team,
                position=player.position,
                expected_goals=expected_goals,
                expected_assists=expected_assists,
                anytime_scorer=anytime,
                to_score_or_assist=score_or_assist,
                first_scorer=first_scorer,
            )
        )
    return out
