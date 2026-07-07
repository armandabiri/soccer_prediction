"""T13 acceptance: Dixon-Coles lifts draw mass versus naive Poisson."""

from __future__ import annotations

from soccer_prediction.models import TeamMatchStats
from soccer_prediction.predictors import get_model


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
