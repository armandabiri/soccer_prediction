"""Advanced goal-model and uncertainty-analysis coverage."""

from __future__ import annotations

from soccer_prediction.models import ScorelineGrid, TeamMatchStats
from soccer_prediction.predictors import EnsemblePredictor, MonteCarloPredictor, get_model
from soccer_prediction.predictors.bivariate_poisson import bivariate_poisson_grid
from soccer_prediction.predictors.negative_binomial import negative_binomial_grid
from soccer_prediction.predictors.poisson import poisson_grid


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


def test_every_advanced_registry_model_predicts(sample_history: list[TeamMatchStats]) -> None:
    """All newly registered strategies satisfy the Predictor interface."""
    for name in ("negative_binomial", "bivariate_poisson", "monte_carlo", "ensemble"):
        model = get_model(name)
        model.fit(sample_history)
        assert round(model.predict_scoreline("Brazil", "Argentina").total_probability(), 6) == 1.0
