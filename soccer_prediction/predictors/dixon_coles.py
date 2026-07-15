"""Dixon-Coles-style low-score correction with likelihood-tuned rho."""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from datetime import date

from soccer_prediction.models import MarketPrediction, ScorelineGrid, TeamMatchStats
from soccer_prediction.predictors.base import register_model
from soccer_prediction.predictors.markets import derive_markets
from soccer_prediction.predictors.poisson import PoissonPredictor

__all__ = ["DixonColesPredictor"]

logger = logging.getLogger(__name__)

_RHO_GRID = tuple(round(-0.15 + 0.01 * index, 2) for index in range(18))  # [-0.15, 0.02]


class DixonColesPredictor:
    """Poisson model with the four-cell Dixon-Coles low-score correction."""

    def __init__(self, draw_boost: float | None = None) -> None:
        self._fixed_draw_boost = draw_boost
        self.draw_boost = 0.06 if draw_boost is None else draw_boost
        self.rho = -self.draw_boost
        self._poisson = PoissonPredictor()

    def fit(self, history: Sequence[TeamMatchStats], *, as_of: date | None = None) -> None:
        """Fit rates, then choose rho by maximizing recent low-score likelihood."""
        visible_history = tuple(record for record in history if as_of is None or record.date <= as_of)
        self._poisson.fit(visible_history, as_of=as_of)
        if self._fixed_draw_boost is None:
            self.rho = _estimate_rho(self._poisson, visible_history, as_of=as_of)
            self.draw_boost = min(0.18, max(0.0, -self.rho))
        else:
            self.rho = -min(0.18, max(0.0, self.draw_boost))

    def predict_scoreline(self, home: str, away: str, *, neutral_venue: bool = False) -> ScorelineGrid:
        """Predict a scoreline grid with low-score dependence."""
        base = self._poisson.predict_scoreline(home, away, neutral_venue=neutral_venue)
        home_lambda, away_lambda = self._poisson.goal_expectations(home, away, neutral_venue=neutral_venue)
        corrected = _apply_tau(base, home_lambda, away_lambda, self.rho)
        logger.debug("applied Dixon-Coles tau (rho=%.3f) for %s v %s", self.rho, home, away)
        return corrected

    def predict_market(
        self, home: str, away: str, market: str, *, neutral_venue: bool = False
    ) -> MarketPrediction:
        """Predict a market derived from the corrected grid."""
        return derive_markets(self.predict_scoreline(home, away, neutral_venue=neutral_venue))[market]


@register_model("dixon_coles")
def _factory() -> DixonColesPredictor:
    return DixonColesPredictor()


def _apply_tau(base: ScorelineGrid, home_lambda: float, away_lambda: float, rho: float) -> ScorelineGrid:
    rows = [list(row) for row in base.probabilities]
    # Soften the classical (1,1) boost once expected totals leave the low-score
    # regime; otherwise Dixon-Coles keeps pinning the mode on 1-1 in open games.
    total = home_lambda + away_lambda
    one_one_scale = 1.0 if total <= 2.6 else max(0.20, 1.0 - 0.40 * (total - 2.6))
    factors = {
        (0, 0): 1.0 - home_lambda * away_lambda * rho,
        (0, 1): 1.0 + home_lambda * rho,
        (1, 0): 1.0 + away_lambda * rho,
        (1, 1): 1.0 - rho * one_one_scale,
    }
    for (home_goals, away_goals), factor in factors.items():
        if home_goals <= base.home_goals_max and away_goals <= base.away_goals_max:
            rows[home_goals][away_goals] *= max(0.01, factor)
    total_mass = sum(value for row in rows for value in row)
    return ScorelineGrid(
        base.home_goals_max,
        base.away_goals_max,
        tuple(tuple(value / total_mass for value in row) for row in rows),
    )


def _estimate_rho(poisson: PoissonPredictor, history: Sequence[TeamMatchStats], *, as_of: date | None) -> float:
    """Pick rho that maximizes mean log-score of observed scorelines under tau."""
    matches = _canonical_matches(history)
    if len(matches) < 8:
        return -_estimate_draw_boost(history)
    recent = matches[-min(48, len(matches)) :]
    best_rho = -0.06
    best_score = float("-inf")
    for rho in _RHO_GRID:
        score = 0.0
        for match in recent:
            home_lambda, away_lambda = poisson.goal_expectations(match[1], match[2], neutral_venue=True)
            probability = _tau_cell_probability(
                match[3],
                match[4],
                home_lambda,
                away_lambda,
                rho,
                max_goals=poisson.max_goals,
            )
            score += math.log(max(probability, 1e-12))
        # Mild Gaussian prior around the classical football rho keeps fits interior.
        mean_score = score / len(recent) - 6.0 * (rho + 0.06) ** 2
        if mean_score > best_score:
            best_score = mean_score
            best_rho = rho
    return best_rho


def _tau_cell_probability(
    home_goals: int,
    away_goals: int,
    home_lambda: float,
    away_lambda: float,
    rho: float,
    *,
    max_goals: int,
) -> float:
    """Approximate normalized probability of one observed score under tau-corrected Poisson."""
    from soccer_prediction.predictors.poisson import poisson_grid

    base = poisson_grid(home_lambda, away_lambda, max_goals)
    corrected = _apply_tau(base, home_lambda, away_lambda, rho)
    home_bucket = min(home_goals, corrected.home_goals_max)
    away_bucket = min(away_goals, corrected.away_goals_max)
    return corrected.probabilities[home_bucket][away_bucket]


def _canonical_matches(history: Sequence[TeamMatchStats]) -> list[tuple[date, str, str, int, int]]:
    unique: dict[tuple[date, str, str], tuple[date, str, str, int, int]] = {}
    for record in history:
        if record.is_home:
            home, away = record.team, record.opponent
            home_score, away_score = record.goals_for, record.goals_against
        else:
            home, away = record.opponent, record.team
            home_score, away_score = record.goals_against, record.goals_for
        key = (record.date, home.casefold(), away.casefold())
        unique[key] = (record.date, home, away, home_score, away_score)
    return sorted(unique.values(), key=lambda item: (item[0], item[1], item[2]))


def _estimate_draw_boost(history: Sequence[TeamMatchStats]) -> float:
    """Fallback low-score correction from observed low-draw frequency."""
    if not history:
        return 0.06
    low_draws = sum(record.goals_for == record.goals_against <= 1 for record in history)
    rate = low_draws / len(history)
    return min(0.18, max(0.01, 0.04 + 0.35 * (rate - 0.20)))
