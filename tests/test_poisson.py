"""T12 acceptance: the Poisson scoreline grid is a valid probability distribution."""

from __future__ import annotations

from soccer_prediction.predictors.poisson import PoissonPredictor, poisson_grid, poisson_tail_at_least


def test_grid_sums_to_one() -> None:
    """A fitted Poisson grid sums to one within tolerance."""
    grid = poisson_grid(1.6, 1.1, 8)
    assert round(grid.total_probability(), 6) == 1.0


def test_symmetric_teams_are_symmetric() -> None:
    """Equal home/away rates give near-equal win probabilities."""
    predictor = PoissonPredictor(max_goals=6)
    predictor.fit([])
    grid = poisson_grid(1.3, 1.3, 6)
    home, _draw, away = grid.home_draw_away()
    assert abs(home - away) < 1e-9


def test_tail_is_monotone() -> None:
    """Poisson upper-tail probability is non-increasing in the threshold."""
    assert poisson_tail_at_least(3.0, 2) >= poisson_tail_at_least(3.0, 5)
