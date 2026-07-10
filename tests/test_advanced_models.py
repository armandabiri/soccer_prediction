"""Advanced goal-model and uncertainty-analysis coverage."""

from __future__ import annotations

from soccer_prediction.models import ScorelineGrid, TeamMatchStats
from soccer_prediction.predictors import EnsemblePredictor, MonteCarloPredictor, get_model
from soccer_prediction.predictors.bivariate_poisson import bivariate_poisson_grid
from soccer_prediction.predictors.ensemble import pool_scoreline_grids
from soccer_prediction.predictors.negative_binomial import negative_binomial_grid
from soccer_prediction.predictors.poisson import poisson_grid
from soccer_prediction.predictors.scorers import expected_goals_from_grid


def _five_plus_probability(grid: ScorelineGrid) -> float:
    probabilities = grid.probabilities
    return sum(
        probability
        for home_goals, row in enumerate(probabilities)
        for away_goals, probability in enumerate(row)
        if home_goals + away_goals >= 5
    )


def test_negative_binomial_widens_high_score_tail() -> None:
    """Overdispersion assigns more mass to extreme totals than Poisson."""
    poisson = poisson_grid(1.4, 1.1, 8)
    negative_binomial = negative_binomial_grid(1.4, 1.1, 8, dispersion=2.0)
    assert round(negative_binomial.total_probability(), 8) == 1.0
    assert _five_plus_probability(negative_binomial) > _five_plus_probability(poisson)


def test_bivariate_poisson_adds_scoring_dependence() -> None:
    """A shared process raises the chance that both teams score."""
    independent = poisson_grid(1.4, 1.1, 8)
    correlated = bivariate_poisson_grid(1.4, 1.1, 8, shared_rate=0.15)
    assert round(correlated.total_probability(), 8) == 1.0
    assert correlated.both_teams_to_score() > independent.both_teams_to_score()


def test_monte_carlo_is_reproducible(sample_history: list[TeamMatchStats]) -> None:
    """Stable fixture seeding makes reports and tests repeatable."""
    model = MonteCarloPredictor(simulations=2_000, seed=7)
    model.fit(sample_history)
    first = model.predict_scoreline("Brazil", "Argentina")
    second = model.predict_scoreline("Brazil", "Argentina")
    assert first == second
    assert round(first.total_probability(), 8) == 1.0


def test_ensemble_is_normalized(sample_history: list[TeamMatchStats]) -> None:
    """The linear probability pool remains a valid scoreline distribution."""
    model = EnsemblePredictor(weights={"dixon_coles": 0.5, "negative_binomial": 0.5})
    model.fit(sample_history)
    grid = model.predict_scoreline("Brazil", "Argentina")
    assert round(grid.total_probability(), 8) == 1.0


def test_ensemble_pool_is_exact_weighted_cell_average() -> None:
    """The conclusion is one linear pool, not a vote or second model run."""
    first = ScorelineGrid(1, 1, ((0.4, 0.1), (0.2, 0.3)))
    second = ScorelineGrid(1, 1, ((0.1, 0.2), (0.3, 0.4)))
    pooled = pool_scoreline_grids(
        {"dixon_coles": first, "negative_binomial": second},
        {"dixon_coles": 0.25, "negative_binomial": 0.75},
    )
    assert pooled.probabilities[0][0] == 0.175
    assert pooled.probabilities[1][1] == 0.375


def test_monte_carlo_scenario_mix_preserves_baseline_mean() -> None:
    """Random match states widen outcomes without silently increasing expected goals."""
    poisson = get_model("poisson")
    poisson.fit([])
    baseline = poisson.predict_scoreline("A", "B", neutral_venue=True)
    simulation = MonteCarloPredictor(simulations=50_000, seed=31)
    simulation.fit([])
    simulated = simulation.predict_scoreline("A", "B", neutral_venue=True)
    baseline_total = sum(expected_goals_from_grid(baseline))
    simulated_total = sum(expected_goals_from_grid(simulated))
    assert abs(simulated_total - baseline_total) < 0.08


def test_poisson_last_bucket_contains_full_tail() -> None:
    """The terminal score bucket means max-plus and no probability mass is discarded."""
    grid = poisson_grid(1.4, 1.1, 4)
    exact_below = sum(math.exp(-1.4) * 1.4**goal / math.factorial(goal) for goal in range(4))
    home_tail = sum(grid.probabilities[4])
    assert abs(home_tail - (1.0 - exact_below)) < 1e-12


def test_every_advanced_registry_model_predicts(sample_history: list[TeamMatchStats]) -> None:
    """All newly registered strategies satisfy the Predictor interface."""
    for name in ("negative_binomial", "bivariate_poisson", "monte_carlo", "ensemble"):
        model = get_model(name)
        model.fit(sample_history)
        assert round(model.predict_scoreline("Brazil", "Argentina").total_probability(), 6) == 1.0
