"""T13 acceptance: Dixon-Coles lifts draw mass versus naive Poisson."""

from __future__ import annotations

from soccer_prediction.models import TeamMatchStats
from soccer_prediction.predictors import get_model
from soccer_prediction.predictors.dixon_coles import DixonColesPredictor


def test_draw_mass_ge_poisson(sample_history: list[TeamMatchStats]) -> None:
    """The low-score correction assigns at least as much draw probability."""
    poisson = get_model("poisson")
    poisson.fit(sample_history)
    dixon = get_model("dixon_coles")
    dixon.fit(sample_history)
    _, poisson_draw, _ = poisson.predict_scoreline("Brazil", "Argentina").home_draw_away()
    _, dixon_draw, _ = dixon.predict_scoreline("Brazil", "Argentina").home_draw_away()
    assert dixon_draw >= poisson_draw - 1e-9


def test_grid_normalized(sample_history: list[TeamMatchStats]) -> None:
    """The corrected grid remains a normalized distribution."""
    dixon = get_model("dixon_coles")
    dixon.fit(sample_history)
    grid = dixon.predict_scoreline("Brazil", "Argentina")
    assert round(grid.total_probability(), 6) == 1.0


def test_standard_four_low_score_cells_are_corrected(sample_history: list[TeamMatchStats]) -> None:
    """The correction boosts 0-0/1-1 and suppresses 0-1/1-0 relative to untouched cells."""
    poisson = get_model("poisson")
    poisson.fit(sample_history)
    base = poisson.predict_scoreline("Brazil", "Argentina")
    dixon = DixonColesPredictor(draw_boost=0.08)
    dixon.fit(sample_history)
    corrected = dixon.predict_scoreline("Brazil", "Argentina")
    unchanged_ratio = corrected.probabilities[2][2] / base.probabilities[2][2]
    assert corrected.probabilities[0][0] / base.probabilities[0][0] > unchanged_ratio
    assert corrected.probabilities[1][1] / base.probabilities[1][1] > unchanged_ratio
    assert corrected.probabilities[0][1] / base.probabilities[0][1] < unchanged_ratio
    assert corrected.probabilities[1][0] / base.probabilities[1][0] < unchanged_ratio
