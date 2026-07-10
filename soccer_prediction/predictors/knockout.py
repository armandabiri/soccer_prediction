"""Extra-time and penalty-shootout predictor for knockout fixtures.

Three stages, each modelled explicitly:

1. **Extra time** -- if level after 90', two 15-minute periods are played at a
   fatigue/caution-suppressed fraction of the full-match scoring rate.
2. **Penalty shootout** -- if still level, a best-of-five shootout followed by
   sudden death, computed analytically from each team's penalty-conversion rate
   (binomial regulation phase + geometric sudden-death phase) rather than a
   coin flip.
3. The stages combine into each team's probability of advancing, plus a
   breakdown of whether the tie is settled in normal time, extra time, or on
   penalties.
"""

from __future__ import annotations

import math

from soccer_prediction.models import KnockoutPrediction, ScorelineGrid
from soccer_prediction.predictors.poisson import poisson_grid
from soccer_prediction.predictors.scorers import expected_goals_from_grid

__all__ = ["predict_knockout", "shootout_win_probability"]

# Extra time is 30 of 90 minutes, discounted for tournament caution/fatigue.
_EXTRA_TIME_FRACTION = 1.0 / 3.0
_EXTRA_TIME_FATIGUE = 0.80
# Penalty shootout: best-of-five then sudden death; conversion near the ~0.75
# historical average, nudged by relative attacking strength, and bounded.
_SHOOTOUT_KICKS = 5
_BASE_CONVERSION = 0.75
_CONVERSION_TILT = 0.03
_CONVERSION_MIN = 0.66
_CONVERSION_MAX = 0.83


def predict_knockout(grid: ScorelineGrid) -> KnockoutPrediction:
    """Derive extra-time, penalty, and advancement probabilities from a scoreline grid."""
    ft_home, ft_draw, ft_away = grid.home_draw_away()
    home_xg, away_xg = expected_goals_from_grid(grid)
    et_rate = _EXTRA_TIME_FRACTION * _EXTRA_TIME_FATIGUE
    extra_time = poisson_grid(home_xg * et_rate, away_xg * et_rate, grid.home_goals_max)
    et_home, et_draw, et_away = extra_time.home_draw_away()
    home_conversion = _conversion_rate(home_xg, away_xg)
    away_conversion = _conversion_rate(away_xg, home_xg)
    home_shootout = shootout_win_probability(home_conversion, away_conversion)
    goes_to_pens = ft_draw * et_draw
    return KnockoutPrediction(
        goes_to_extra_time=ft_draw,
        goes_to_penalties=goes_to_pens,
        home_advance=ft_home + ft_draw * (et_home + et_draw * home_shootout),
        away_advance=ft_away + ft_draw * (et_away + et_draw * (1.0 - home_shootout)),
        home_shootout_win=home_shootout,
        away_shootout_win=1.0 - home_shootout,
        home_penalty_conversion=home_conversion,
        away_penalty_conversion=away_conversion,
        decided_in_normal_time=ft_home + ft_away,
        decided_in_extra_time=ft_draw * (et_home + et_away),
    )


def shootout_win_probability(home_conversion: float, away_conversion: float) -> float:
    """Probability the home side wins a best-of-five-plus-sudden-death shootout."""
    home_regulation = 0.0
    tie = 0.0
    for home_goals in range(_SHOOTOUT_KICKS + 1):
        home_pmf = _binomial_pmf(_SHOOTOUT_KICKS, home_goals, home_conversion)
        for away_goals in range(_SHOOTOUT_KICKS + 1):
            joint = home_pmf * _binomial_pmf(_SHOOTOUT_KICKS, away_goals, away_conversion)
            if home_goals > away_goals:
                home_regulation += joint
            elif home_goals == away_goals:
                tie += joint
    home_edge = home_conversion * (1.0 - away_conversion)
    away_edge = away_conversion * (1.0 - home_conversion)
    denominator = home_edge + away_edge
    sudden_death = 0.5 if denominator == 0.0 else home_edge / denominator
    return home_regulation + tie * sudden_death


def _conversion_rate(team_xg: float, opponent_xg: float) -> float:
    rate = _BASE_CONVERSION + _CONVERSION_TILT * (team_xg - opponent_xg)
    return min(_CONVERSION_MAX, max(_CONVERSION_MIN, rate))


def _binomial_pmf(kicks: int, scored: int, conversion: float) -> float:
    return math.comb(kicks, scored) * conversion**scored * (1.0 - conversion) ** (kicks - scored)
