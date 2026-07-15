"""Independent-Poisson goal model."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date

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

    def fit(self, history: Sequence[TeamMatchStats], *, as_of: date | None = None) -> None:
        """Fit team rates from match history."""
        self._rates = compute_rates(history, today=as_of)

    def predict_scoreline(self, home: str, away: str, *, neutral_venue: bool = False) -> ScorelineGrid:
        """Predict a normalized scoreline grid."""
        home_lambda, away_lambda = self.goal_expectations(home, away, neutral_venue=neutral_venue)
        return poisson_grid(home_lambda, away_lambda, self.max_goals)

    def goal_expectations(self, home: str, away: str, *, neutral_venue: bool = False) -> tuple[float, float]:
        """Return fitted home and away mean-goal parameters."""
        return expected_goals(self._rates, home, away, neutral_venue=neutral_venue)

    def predict_market(
        self, home: str, away: str, market: str, *, neutral_venue: bool = False
    ) -> MarketPrediction:
        """Predict a market derived from the scoreline grid."""
        markets = derive_markets(self.predict_scoreline(home, away, neutral_venue=neutral_venue))
        try:
            return markets[market]
        except KeyError as exc:
            raise KeyError(f"unsupported market {market!r}") from exc


def expected_goals(
    rates: RateBook,
    home: str,
    away: str,
    *,
    neutral_venue: bool = False,
) -> tuple[float, float]:
    """Estimate home and away goal expectations."""
    model = load_config().model
    league_rate = max(rates.global_rates.goals_for, 0.8)
    home_edge, away_edge = (1.0, 1.0) if neutral_venue else (1.08, 0.92)
    away_defence = _effective_defence(rates, defender=away, attacker=home, exponent=model.elite_defence_exponent)
    home_defence = _effective_defence(rates, defender=home, attacker=away, exponent=model.elite_defence_exponent)
    home_lambda = league_rate * rates.attack_for(home) * away_defence * home_edge
    away_lambda = league_rate * rates.attack_for(away) * home_defence * away_edge
    home_lambda, away_lambda = _blend_head_to_head(
        rates, home, away, home_lambda, away_lambda, neutral_venue=neutral_venue
    )
    morale_edge = min(1.0, max(-1.0, (rates.morale_for(home) - rates.morale_for(away)) / 2.0))
    morale_effect = min(0.15, max(0.0, model.morale_max_effect))
    home_lambda *= 1.0 + morale_effect * morale_edge
    away_lambda *= 1.0 - morale_effect * morale_edge
    tempo = _elite_match_tempo(rates, home, away, strength=model.elite_tempo_strength)
    home_lambda *= tempo
    away_lambda *= tempo
    home_lambda = min(4.5, max(0.2, home_lambda))
    away_lambda = min(4.5, max(0.2, away_lambda))
    return home_lambda, away_lambda


def _effective_defence(rates: RateBook, *, defender: str, attacker: str, exponent: float) -> float:
    """Soften ultra-tight defence ratings when the attacker is also strong.

    Concession factors earned mostly against weaker sides understate scoring in
    elite-vs-elite games; raising weakness toward 1.0 (via exponent < 1) fixes
    that without globally inflating mismatches.
    """
    weakness = rates.defence_weakness_for(defender)
    if exponent >= 0.999 or rates.attack_for(attacker) < 0.95 or weakness >= 0.70:
        return weakness
    return max(0.35, weakness**exponent)


def _elite_match_tempo(rates: RateBook, home: str, away: str, *, strength: float) -> float:
    """Raise expected totals when two strong, low-concession sides meet.

    Multiplicative attack×defence models systematically understate open elite
    knockouts: both teams look like they "never concede" because their history
    is dominated by weaker opponents. A modest tempo uplift corrects that
    without globally inflating mismatches against weak sides.
    """
    if strength <= 0:
        return 1.0
    attack = (rates.attack_for(home) * rates.attack_for(away)) ** 0.5
    defence_strength = (
        (1.0 / max(rates.defence_weakness_for(home), 0.35))
        * (1.0 / max(rates.defence_weakness_for(away), 0.35))
    ) ** 0.5
    if attack < 0.90 or defence_strength < 1.35:
        return 1.0
    excess = (defence_strength - 1.35) * attack
    return min(1.40, 1.0 + strength * excess)


def _blend_head_to_head(
    rates: RateBook,
    home: str,
    away: str,
    home_lambda: float,
    away_lambda: float,
    *,
    neutral_venue: bool,
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
    if not neutral_venue:
        direct_home *= 1.08
        direct_away *= 0.92
    return (
        home_lambda * (1.0 - weight) + direct_home * weight,
        away_lambda * (1.0 - weight) + direct_away * weight,
    )


def poisson_grid(home_lambda: float, away_lambda: float, max_goals: int) -> ScorelineGrid:
    """Build a grid whose last row/column include all overflow goal counts."""
    home_probs = _bounded_poisson_probabilities(home_lambda, max_goals)
    away_probs = _bounded_poisson_probabilities(away_lambda, max_goals)
    rows = tuple(tuple(home_prob * away_prob for away_prob in away_probs) for home_prob in home_probs)
    return ScorelineGrid(max_goals, max_goals, rows)


def _bounded_poisson_probabilities(rate: float, maximum: int) -> tuple[float, ...]:
    if maximum < 0:
        raise ValueError("maximum goals must be non-negative")
    if maximum == 0:
        return (1.0,)
    exact = tuple(_poisson_pmf(goal, rate) for goal in range(maximum))
    return (*exact, max(0.0, 1.0 - sum(exact)))


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
