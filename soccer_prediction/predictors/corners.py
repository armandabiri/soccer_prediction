"""Corners total and minimum predictor."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from soccer_prediction.features import RateBook, compute_rates
from soccer_prediction.models import CornersPrediction, TeamMatchStats
from soccer_prediction.predictors.poisson import poisson_tail_at_least

__all__ = ["CornersPredictor"]


class CornersPredictor:
    """Overdispersed corners approximation using shrunk team rates."""

    def __init__(self) -> None:
        self._rates = compute_rates([])

    def fit(self, history: Sequence[TeamMatchStats], *, as_of: date | None = None) -> None:
        """Fit corner rates."""
        self._rates = compute_rates(history, today=as_of)

    def predict(self, home: str, away: str, *, neutral_venue: bool = False) -> CornersPrediction:
        """Return total and minimum corner estimates."""
        home_expected, away_expected = _corner_expectations(
            self._rates, home, away, neutral_venue=neutral_venue
        )
        total_expected = home_expected + away_expected
        total_lines = {line: poisson_tail_at_least(total_expected, int(line + 0.5)) for line in (7.5, 8.5, 9.5, 10.5)}
        home_minimum = _quantile_floor(home_expected, 0.10)
        away_minimum = _quantile_floor(away_expected, 0.10)
        prob_at_least = {threshold: poisson_tail_at_least(total_expected, threshold) for threshold in range(6, 13)}
        return CornersPrediction(
            home_expected,
            away_expected,
            total_expected,
            total_lines,
            home_minimum,
            away_minimum,
            prob_at_least,
        )


# League-average per-team corner rates, used when the data source has no corner
# data (e.g. martj42 international results, which carry goals only).
_PRIOR_CORNERS_FOR = 5.1
_PRIOR_CORNERS_AGAINST = 4.9
_HOME_CORNER_EDGE = 0.4


def _corner_rate(value: float, prior: float) -> float:
    """Use the observed corner rate, or a league-average prior when it is absent."""
    return value if value > 0.5 else prior


def _corner_expectations(
    rates: RateBook, home: str, away: str, *, neutral_venue: bool = False
) -> tuple[float, float]:
    if rates.corner_attack_factors:
        league_rate = max(rates.global_rates.corners_for, _PRIOR_CORNERS_FOR)
        home_expected = league_rate * rates.corner_attack_for(home) * rates.corner_concession_for(away)
        away_expected = league_rate * rates.corner_attack_for(away) * rates.corner_concession_for(home)
        home_expected, away_expected = _blend_head_to_head_corners(
            rates,
            home,
            away,
            home_expected + (0.0 if neutral_venue else _HOME_CORNER_EDGE),
            away_expected,
        )
        return max(1.0, home_expected), max(1.0, away_expected)
    home_rates = rates.for_team(home)
    away_rates = rates.for_team(away)
    home_for = _corner_rate(home_rates.corners_for, _PRIOR_CORNERS_FOR)
    home_against = _corner_rate(home_rates.corners_against, _PRIOR_CORNERS_AGAINST)
    away_for = _corner_rate(away_rates.corners_for, _PRIOR_CORNERS_FOR)
    away_against = _corner_rate(away_rates.corners_against, _PRIOR_CORNERS_AGAINST)
    home_edge = 0.0 if neutral_venue else _HOME_CORNER_EDGE
    home_expected = max(1.0, (home_for + away_against) / 2.0 + home_edge)
    away_expected = max(1.0, (away_for + home_against) / 2.0)
    return home_expected, away_expected


def _blend_head_to_head_corners(
    rates: RateBook,
    home: str,
    away: str,
    home_expected: float,
    away_expected: float,
) -> tuple[float, float]:
    home_history = rates.for_matchup(home, away)
    away_history = rates.for_matchup(away, home)
    if home_history is None and away_history is None:
        return home_expected, away_expected
    if home_history is not None:
        direct_home = home_history.corners_for
    else:
        assert away_history is not None
        direct_home = away_history.corners_against
    if away_history is not None:
        direct_away = away_history.corners_for
    else:
        assert home_history is not None
        direct_away = home_history.corners_against
    if direct_home <= 0.5 and direct_away <= 0.5:
        return home_expected, away_expected
    meetings = max(
        rates.matchup_effective_sample(home, away),
        rates.matchup_effective_sample(away, home),
    )
    weight = min(0.30, 0.40 * meetings / (meetings + 5.0))
    return (
        home_expected * (1.0 - weight) + direct_home * weight,
        away_expected * (1.0 - weight) + direct_away * weight,
    )


def _quantile_floor(lam: float, quantile: float) -> int:
    cumulative = 0.0
    for value in range(31):
        cumulative += poisson_tail_at_least(lam, value) - poisson_tail_at_least(lam, value + 1)
        if cumulative >= quantile:
            return value
    return 30
