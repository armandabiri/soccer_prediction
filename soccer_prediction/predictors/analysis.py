"""Cross-model comparison and simulated-scenario diagnostics."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date

from soccer_prediction.config import load_config
from soccer_prediction.models import ModelEstimate, ScenarioAnalysis, ScorelineGrid, TeamMatchStats
from soccer_prediction.predictors.base import get_model
from soccer_prediction.predictors.scorers import expected_goals_from_grid

__all__ = ["build_scenario_analysis"]

_COMPARISON_MODELS = (
    "poisson",
    "dixon_coles",
    "negative_binomial",
    "bivariate_poisson",
    "monte_carlo",
)


def build_scenario_analysis(
    history: Sequence[TeamMatchStats],
    home: str,
    away: str,
    selected_grid: ScorelineGrid,
) -> ScenarioAnalysis:
    """Compare model families and summarize the Monte Carlo scenario distribution."""
    grids: dict[str, ScorelineGrid] = {}
    estimates: list[ModelEstimate] = []
    simulations = 0
    for name in _COMPARISON_MODELS:
        model = get_model(name)
        model.fit(history)
        grid = model.predict_scoreline(home, away)
        grids[name] = grid
        if name == "monte_carlo":
            simulations = int(getattr(model, "simulations", 0))
        home_win, draw, away_win = grid.home_draw_away()
        home_xg, away_xg = expected_goals_from_grid(grid)
        estimates.append(ModelEstimate(name, home_win, draw, away_win, home_xg, away_xg))

    outcome_estimates = (
        tuple(item.home_win for item in estimates),
        tuple(item.draw for item in estimates),
        tuple(item.away_win for item in estimates),
    )
    disagreement = max(max(values) - min(values) for values in outcome_estimates)
    agreement_label = "high" if disagreement < 0.05 else "moderate" if disagreement < 0.10 else "low"
    outcome_probabilities = selected_grid.home_draw_away()
    entropy = -sum(probability * math.log(probability) for probability in outcome_probabilities if probability > 0)
    entropy /= math.log(3.0)
    data_uncertainty = _data_uncertainty(history, home, away)
    data_quality = "high" if data_uncertainty < 0.25 else "moderate" if data_uncertainty < 0.55 else "low"

    scenario_grid = grids["monte_carlo"]
    home_marginal = [sum(row) for row in scenario_grid.probabilities]
    away_marginal = [sum(row[index] for row in scenario_grid.probabilities) for index in range(len(home_marginal))]
    total_marginal = _total_goals_marginal(scenario_grid)
    five_plus = 0.0
    wide_margin = 0.0
    for home_goals, row in enumerate(scenario_grid.probabilities):
        for away_goals, probability in enumerate(row):
            if home_goals + away_goals >= 5:
                five_plus += probability
            if abs(home_goals - away_goals) >= 3:
                wide_margin += probability

    return ScenarioAnalysis(
        simulations=simulations,
        home_goals_interval=(_quantile(home_marginal, 0.10), _quantile(home_marginal, 0.90)),
        away_goals_interval=(_quantile(away_marginal, 0.10), _quantile(away_marginal, 0.90)),
        total_goals_interval=(_quantile(total_marginal, 0.10), _quantile(total_marginal, 0.90)),
        home_clean_sheet=sum(row[0] for row in scenario_grid.probabilities),
        away_clean_sheet=sum(scenario_grid.probabilities[0]),
        scoreless_draw=scenario_grid.probabilities[0][0],
        five_plus_goals=five_plus,
        three_plus_goal_margin=wide_margin,
        model_disagreement=disagreement,
        outcome_uncertainty=entropy,
        agreement_label=agreement_label,
        model_estimates=tuple(estimates),
        data_uncertainty=data_uncertainty,
        data_quality_label=data_quality,
    )


def _total_goals_marginal(grid: ScorelineGrid) -> list[float]:
    probabilities = [0.0] * (grid.home_goals_max + grid.away_goals_max + 1)
    for home_goals, row in enumerate(grid.probabilities):
        for away_goals, probability in enumerate(row):
            probabilities[home_goals + away_goals] += probability
    return probabilities


def _quantile(probabilities: Sequence[float], quantile: float) -> int:
    cumulative = 0.0
    for value, probability in enumerate(probabilities):
        cumulative += probability
        if cumulative >= quantile:
            return value
    return len(probabilities) - 1


def _data_uncertainty(history: Sequence[TeamMatchStats], home: str, away: str) -> float:
    """Estimate uncertainty from the smaller team's recency-weighted sample."""
    xi = max(load_config().model.time_decay_xi, 0.0)
    today = date.today()

    def effective_matches(team: str) -> float:
        return sum(
            math.exp(-xi * max((today - record.date).days, 0))
            for record in history
            if record.team.casefold() == team.casefold()
        )

    evidence = min(effective_matches(home), effective_matches(away))
    return math.exp(-evidence / 6.0)
