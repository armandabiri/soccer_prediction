"""Independent per-half Poisson score model."""

from __future__ import annotations

from collections.abc import Sequence

from soccer_prediction.features import RateBook, compute_rates
from soccer_prediction.models import MarketPrediction, PerHalfPrediction, TeamMatchStats
from soccer_prediction.predictors.poisson import poisson_grid

__all__ = ["HalfTimePredictor"]


class HalfTimePredictor:
    """Practitioner-grade independent-halves model."""

    def __init__(self, max_goals: int = 5) -> None:
        self.max_goals = max_goals
        self._rates = compute_rates([])

    def fit(self, history: Sequence[TeamMatchStats]) -> None:
        """Fit half-time and second-half rates."""
        self._rates = compute_rates(history)

    def predict(self, home: str, away: str) -> PerHalfPrediction:
        """Return per-half score grids and summary markets."""
        first_home, first_away = _half_expectations(self._rates, home, away, first_half=True)
        second_home, second_away = _half_expectations(self._rates, home, away, first_half=False)
        first_grid = poisson_grid(first_home, first_away, self.max_goals)
        second_grid = poisson_grid(second_home, second_away, self.max_goals)
        ht_home, ht_draw, ht_away = first_grid.home_draw_away()
        result = max((("home", ht_home), ("draw", ht_draw), ("away", ht_away)), key=lambda item: item[1])
        return PerHalfPrediction(
            first_grid,
            second_grid,
            first_home,
            first_away,
            second_home,
            second_away,
            half_time_result=MarketPrediction("half_time_result", result[0], result[1]),
        )


_FIRST_HALF_SHARE = 0.45


def _first_half_rate(full: float, half: float) -> float:
    """Half-time rate, falling back to a 45% split when no half-time data exists."""
    return half if half > 0.02 else _FIRST_HALF_SHARE * full


def _half_expectations(rates: RateBook, home: str, away: str, *, first_half: bool) -> tuple[float, float]:
    home_rates = rates.for_team(home)
    away_rates = rates.for_team(away)
    home_first_for = _first_half_rate(home_rates.goals_for, home_rates.ht_goals_for)
    home_first_against = _first_half_rate(home_rates.goals_against, home_rates.ht_goals_against)
    away_first_for = _first_half_rate(away_rates.goals_for, away_rates.ht_goals_for)
    away_first_against = _first_half_rate(away_rates.goals_against, away_rates.ht_goals_against)
    if first_half:
        home_rate = (home_first_for + away_first_against) / 2.0
        away_rate = (away_first_for + home_first_against) / 2.0
    else:
        home_rate = ((home_rates.goals_for - home_first_for) + (away_rates.goals_against - away_first_against)) / 2.0
        away_rate = ((away_rates.goals_for - away_first_for) + (home_rates.goals_against - home_first_against)) / 2.0
    return max(0.05, home_rate), max(0.05, away_rate)
