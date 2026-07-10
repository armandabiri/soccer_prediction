"""Cross-model comparison and simulated-scenario diagnostics."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from soccer_prediction.config import load_config
from soccer_prediction.models import ModelEstimate, ScenarioAnalysis, ScorelineGrid, TeamMatchStats
from soccer_prediction.predictors.ensemble import EnsemblePredictor, pool_scoreline_grids
from soccer_prediction.predictors.poisson import PoissonPredictor
from soccer_prediction.predictors.scorers import expected_goals_from_grid

__all__ = ["GoalModelRun", "build_goal_model_run", "build_scenario_analysis"]

_COMPARISON_MODELS = (
    "poisson",
    "dixon_coles",
    "negative_binomial",
    "bivariate_poisson",
    "monte_carlo",
    "ensemble",
)

_MODEL_DESCRIPTIONS = {
    "poisson": "Fast independent-goals baseline; narrowest tails.",
    "dixon_coles": "Poisson with a football-specific low-score dependence correction.",
    "negative_binomial": "Overdispersed counts that allow more scoreless and high-scoring surprises.",
    "bivariate_poisson": "Correlated scoring through a shared match-tempo process.",
    "monte_carlo": "Reproducible cagey, open, and momentum match-state simulations.",
    "ensemble": "Weighted conclusion pooling complementary component models.",
}


@dataclass(frozen=True, slots=True)
class GoalModelRun:
    """All base grids plus one reusable ensemble conclusion."""

    grids: dict[str, ScorelineGrid]
    ensemble_weights: dict[str, float]
    validation_log_losses: dict[str, float]
    validation_matches: int
    validation_from: date | None
    validation_to: date | None
    weight_method: str


def build_goal_model_run(
    history: Sequence[TeamMatchStats],
    home: str,
    away: str,
    *,
    as_of: date | None = None,
    neutral_venue: bool = False,
) -> GoalModelRun:
    """Fit each base model once, then form the adaptive ensemble grid."""
    ensemble = EnsemblePredictor()
    ensemble.fit(history, as_of=as_of)
    grids = ensemble.predict_component_grids(home, away, neutral_venue=neutral_venue)
    grids["ensemble"] = pool_scoreline_grids(grids, ensemble.weights)
    poisson = PoissonPredictor()
    poisson.fit(history, as_of=as_of)
    grids["poisson"] = poisson.predict_scoreline(home, away, neutral_venue=neutral_venue)
    return GoalModelRun(
        grids=grids,
        ensemble_weights=dict(ensemble.weights),
        validation_log_losses=dict(ensemble.validation_log_losses),
        validation_matches=ensemble.validation_matches,
        validation_from=ensemble.validation_from,
        validation_to=ensemble.validation_to,
        weight_method=ensemble.weight_method,
    )


def build_scenario_analysis(
    history: Sequence[TeamMatchStats],
    home: str,
    away: str,
    selected_grid: ScorelineGrid,
    *,
    selected_model_name: str = "ensemble",
    as_of: date | None = None,
    neutral_venue: bool = False,
    model_run: GoalModelRun | None = None,
) -> ScenarioAnalysis:
    """Compare model families and summarize the Monte Carlo scenario distribution."""
    run = model_run or build_goal_model_run(
        history,
        home,
        away,
        as_of=as_of,
        neutral_venue=neutral_venue,
    )
    grids = dict(run.grids)
    if selected_model_name not in grids:
        grids[selected_model_name] = selected_grid
    simulations = load_config().model.scenario_simulations

    component_names = tuple(name for name in _COMPARISON_MODELS if name != "ensemble")
    component_outcomes = tuple(grids[name].home_draw_away() for name in component_names)
    outcome_estimates = (
        tuple(values[0] for values in component_outcomes),
        tuple(values[1] for values in component_outcomes),
        tuple(values[2] for values in component_outcomes),
    )
    disagreement = max(max(values) - min(values) for values in outcome_estimates)
    agreement_label = "high" if disagreement < 0.05 else "moderate" if disagreement < 0.10 else "low"
    conclusion_grid = grids["ensemble"]
    outcome_probabilities = conclusion_grid.home_draw_away()
    entropy = -sum(probability * math.log(probability) for probability in outcome_probabilities if probability > 0)
    entropy /= math.log(3.0)
    data_uncertainty = _data_uncertainty(history, home, away, as_of=as_of)
    data_quality = "high" if data_uncertainty < 0.25 else "moderate" if data_uncertainty < 0.55 else "low"
    confidence_intervals = tuple(
        _confidence_interval(probability, model_values, data_uncertainty)
        for probability, model_values in zip(outcome_probabilities, outcome_estimates, strict=True)
    )
    estimates = tuple(
        _model_estimate(
            name,
            grids[name],
            data_uncertainty,
            outcome_estimates,
            run.ensemble_weights.get(name, 1.0 if name == "ensemble" else 0.0),
            selected_model_name,
            run.validation_log_losses.get(name),
            run.validation_matches,
        )
        for name in _COMPARISON_MODELS
    )

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
        model_estimates=estimates,
        data_uncertainty=data_uncertainty,
        data_quality_label=data_quality,
        confidence_level=0.80,
        home_win_interval=confidence_intervals[0],
        draw_interval=confidence_intervals[1],
        away_win_interval=confidence_intervals[2],
        conclusion_model_name="ensemble",
        ensemble_weights=run.ensemble_weights,
        ensemble_validation_log_losses=run.validation_log_losses,
        ensemble_validation_matches=run.validation_matches,
        ensemble_validation_from=run.validation_from.isoformat() if run.validation_from else None,
        ensemble_validation_to=run.validation_to.isoformat() if run.validation_to else None,
        ensemble_weight_method=run.weight_method,
        selected_model_name=selected_model_name,
        interval_method="effective-sample sensitivity range with component spread for ensemble",
    )


def _model_estimate(
    name: str,
    grid: ScorelineGrid,
    data_uncertainty: float,
    component_outcomes: tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]],
    ensemble_weight: float,
    selected_model_name: str,
    validation_log_loss: float | None,
    validation_matches: int,
) -> ModelEstimate:
    home_win, draw, away_win = grid.home_draw_away()
    home_xg, away_xg = expected_goals_from_grid(grid)
    _under, over = grid.over_under(2.5)
    score, score_probability = _best_score(grid)
    intervals = tuple(
        _confidence_interval(
            probability,
            component_outcomes[index] if name == "ensemble" else (probability,),
            data_uncertainty,
        )
        for index, probability in enumerate((home_win, draw, away_win))
    )
    return ModelEstimate(
        model_name=name,
        home_win=home_win,
        draw=draw,
        away_win=away_win,
        home_expected_goals=home_xg,
        away_expected_goals=away_xg,
        ensemble_weight=ensemble_weight,
        is_ensemble=name == "ensemble",
        description=_MODEL_DESCRIPTIONS[name],
        over_2_5=over,
        btts_yes=grid.both_teams_to_score(),
        most_likely_score=score,
        most_likely_score_probability=score_probability,
        home_win_interval=intervals[0],
        draw_interval=intervals[1],
        away_win_interval=intervals[2],
        is_selected=name == selected_model_name,
        role="conclusion" if name == "ensemble" else "benchmark" if name == "poisson" else "component",
        validation_log_loss=validation_log_loss,
        validation_matches=validation_matches if validation_log_loss is not None else 0,
    )


def _best_score(grid: ScorelineGrid) -> tuple[str, float]:
    scored = (
        (f"{home_goals}-{away_goals}", probability)
        for home_goals, row in enumerate(grid.probabilities)
        for away_goals, probability in enumerate(row)
    )
    return max(scored, key=lambda item: item[1])


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


def _data_uncertainty(
    history: Sequence[TeamMatchStats],
    home: str,
    away: str,
    *,
    as_of: date | None = None,
) -> float:
    """Estimate uncertainty from the smaller team's recency-weighted sample."""
    xi = max(load_config().model.time_decay_xi, 0.0)
    today = date.today() if as_of is None else as_of

    def effective_matches(team: str) -> float:
        return sum(
            math.exp(-xi * max((today - record.date).days, 0))
            for record in history
            if record.team.casefold() == team.casefold() and record.date <= today
        )

    evidence = min(effective_matches(home), effective_matches(away))
    return math.exp(-evidence / 6.0)


def _confidence_interval(
    probability: float,
    model_estimates: Sequence[float],
    data_uncertainty: float,
) -> tuple[float, float]:
    """Approximate an 80% interval from effective evidence and model spread."""
    evidence = max(0.0, -6.0 * math.log(max(data_uncertainty, 1e-9)))
    posterior_strength = evidence + 6.0
    sampling_margin = 1.2816 * math.sqrt(probability * (1.0 - probability) / posterior_strength)
    model_margin = (max(model_estimates) - min(model_estimates)) / 2.0
    margin = math.sqrt(sampling_margin**2 + model_margin**2)
    lower = min(probability - margin, min(model_estimates))
    upper = max(probability + margin, max(model_estimates))
    return max(0.0, lower), min(1.0, upper)
