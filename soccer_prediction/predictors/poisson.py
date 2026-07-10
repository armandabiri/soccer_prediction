"""Independent-Poisson goal model."""

from __future__ import annotations

import math
from collections.abc import Sequence

from soccer_prediction.config import load_config
from soccer_prediction.features import RateBook, compute_rates
from soccer_prediction.models import MarketPrediction, ScorelineGrid, TeamMatchStats
from soccer_prediction.predictors.base import register_model
from soccer_prediction.predictors.markets import derive_markets

__all__ = ["PoissonPredictor", "expected_goals", "poisson_grid", "poisson_tail_at_least"]


class PoissonPredictor:
    """Independent-Poisson predictor with rate shrinkage."""

    def __init__(self, max_goals: int | None = None) -> None:
        self.max_goals = load_config().model.max_goals if max_goals is None else max_goals
        self._rates = compute_rates([])

    def fit(self, history: Sequence[TeamMatchStats]) -> None:
        """Fit team rates from match history."""
        self._rates = compute_rates(history)

    def predict_scoreline(self, home: str, away: str) -> ScorelineGrid:
        """Predict a normalized scoreline grid."""
        home_lambda, away_lambda = expected_goals(self._rates, home, away)
        return poisson_grid(home_lambda, away_lambda, self.max_goals)

    def predict_market(self, home: str, away: str, market: str) -> MarketPrediction:
        """Predict a market derived from the scoreline grid."""
        markets = derive_markets(self.predict_scoreline(home, away))
        try:
            return markets[market]
        except KeyError as exc:
            raise KeyError(f"unsupported market {market!r}") from exc


def expected_goals(rates: RateBook, home: str, away: str) -> tuple[float, float]:
    """Estimate home and away goal expectations."""
    league_rate = max(rates.global_rates.goals_for, 0.8)
    home_lambda = league_rate * rates.attack_for(home) * rates.defence_weakness_for(away) * 1.08
    away_lambda = league_rate * rates.attack_for(away) * rates.defence_weakness_for(home) * 0.92
    home_lambda, away_lambda = _blend_head_to_head(rates, home, away, home_lambda, away_lambda)
    home_lambda = min(4.5, max(0.2, home_lambda))
    away_lambda = min(4.5, max(0.2, away_lambda))
    return home_lambda, away_lambda


def _blend_head_to_head(
    rates: RateBook,
    home: str,
    away: str,
    home_lambda: float,
    away_lambda: float,
) -> tuple[float, float]:
    home_history = rates.for_matchup(home, away)
    away_history = rates.for_matchup(away, home)
    available = tuple(item for item in (home_history, away_history) if item is not None)
    if not available:
        return home_lambda, away_lambda
    meetings = max(
        rates.matchup_effective_sample(home, away),
        rates.matchup_effective_sample(away, home),
    )
    weight = min(0.35, 0.45 * meetings / (meetings + 5.0))
    if home_history is not None:
        direct_home = home_history.goals_for
    else:
        assert away_history is not None
        direct_home = away_history.goals_against
    if away_history is not None:
        direct_away = away_history.goals_for
    else:
        assert home_history is not None
        direct_away = home_history.goals_against
    direct_home *= 1.08
    direct_away *= 0.92
    return (
        home_lambda * (1.0 - weight) + direct_home * weight,
        away_lambda * (1.0 - weight) + direct_away * weight,
    )


def poisson_grid(home_lambda: float, away_lambda: float, max_goals: int) -> ScorelineGrid:
    """Build a normalized independent-Poisson scoreline grid."""
    home_probs = [_poisson_pmf(goal, home_lambda) for goal in range(max_goals + 1)]
    away_probs = [_poisson_pmf(goal, away_lambda) for goal in range(max_goals + 1)]
    rows = tuple(tuple(home_prob * away_prob for away_prob in away_probs) for home_prob in home_probs)
    total = sum(value for row in rows for value in row)
    return ScorelineGrid(max_goals, max_goals, tuple(tuple(value / total for value in row) for row in rows))


def poisson_tail_at_least(lam: float, threshold: int, max_count: int = 30) -> float:
    """Return P(X >= threshold) for a Poisson variable."""
    if threshold <= 0:
        return 1.0
    below = sum(_poisson_pmf(value, lam) for value in range(threshold))
    return min(1.0, max(0.0, 1.0 - below))


def _poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


@register_model("poisson")
def _factory() -> PoissonPredictor:
    return PoissonPredictor()
