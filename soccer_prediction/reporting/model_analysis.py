"""Shared text and Markdown rendering for multi-model diagnostics."""

from __future__ import annotations

from soccer_prediction.models import MatchForecast

__all__ = ["model_analysis_markdown", "model_analysis_text"]


def _ensemble(forecast: MatchForecast):  # type: ignore[no-untyped-def]
    analysis = forecast.scenario_analysis
    if analysis is None:
        return None
    return next((item for item in analysis.model_estimates if item.is_ensemble), None)


def model_analysis_markdown(forecast: MatchForecast) -> list[str]:
    """Render uncertainty, random scenarios, and every model as Markdown."""
    analysis = forecast.scenario_analysis
    ensemble = _ensemble(forecast)
    if analysis is None or ensemble is None:
        return []
    home, away = forecast.fixture.home_team, forecast.fixture.away_team
    validation = "static prior weights"
    if analysis.ensemble_validation_matches:
        validation = (
            f"regularized temporal validation over {analysis.ensemble_validation_matches} matches "
            f"({analysis.ensemble_validation_from} to {analysis.ensemble_validation_to})"
        )
    rows = [
        "### Ensemble conclusion, robustness & random scenarios",
        "",
        f"- Selected output model: **{analysis.selected_model_name}**; ensemble weights: {validation}.",
        f"- Model agreement: **{analysis.agreement_label}** "
        f"(maximum component 1X2 disagreement {analysis.model_disagreement:.1%}).",
        f"- Recent-data quality: **{analysis.data_quality_label}** "
        f"(estimated data uncertainty {analysis.data_uncertainty:.0%}).",
        f"- Outcome uncertainty: {analysis.outcome_uncertainty:.0%} "
        "(0% concentrated on one result, 100% evenly split).",
        f"- Middle 80% of {analysis.simulations:,} simulated scenarios: "
        f"{home} {analysis.home_goals_interval[0]}-{analysis.home_goals_interval[1]} goals, "
        f"{away} {analysis.away_goals_interval[0]}-{analysis.away_goals_interval[1]}, "
        f"total {analysis.total_goals_interval[0]}-{analysis.total_goals_interval[1]}.",
        f"- Tail scenarios: 5+ goals {analysis.five_plus_goals:.1%}; "
        f"winning margin of 3+ {analysis.three_plus_goal_margin:.1%}; 0-0 {analysis.scoreless_draw:.1%}.",
        "",
        f"#### Ensemble result sensitivity ranges ({analysis.confidence_level:.0%})",
        "",
        "| Outcome | Estimate | Approximate range |",
        "| --- | ---: | ---: |",
        f"| {home} win | {ensemble.home_win:.1%} "
        f"| {ensemble.home_win_interval[0]:.1%}–{ensemble.home_win_interval[1]:.1%} |",
        f"| Draw | {ensemble.draw:.1%} "
        f"| {ensemble.draw_interval[0]:.1%}–{ensemble.draw_interval[1]:.1%} |",
        f"| {away} win | {ensemble.away_win:.1%} "
        f"| {ensemble.away_win_interval[0]:.1%}–{ensemble.away_win_interval[1]:.1%} |",
        "",
        "#### All goal algorithms",
        "",
        f"| Model | Role | Weight | {home} | Draw | {away} | Model goals | O2.5 | BTTS | Top score | Val loss |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in analysis.model_estimates:
        weight = f"{item.ensemble_weight:.0%}" if item.ensemble_weight else "—"
        loss = f"{item.validation_log_loss:.3f}" if item.validation_log_loss is not None else "—"
        marker = " (selected)" if item.is_selected else ""
        rows.append(
            f"| {item.model_name}{marker} | {item.role} | {weight} | {item.home_win:.1%} | "
            f"{item.draw:.1%} | {item.away_win:.1%} | "
            f"{item.home_expected_goals:.2f}–{item.away_expected_goals:.2f} | {item.over_2_5:.1%} | "
            f"{item.btts_yes:.1%} | {item.most_likely_score} ({item.most_likely_score_probability:.1%}) | {loss} |"
        )
    rows.extend(
        [
            "",
            f"_Ranges use {analysis.interval_method}. They are sensitivity diagnostics, not calibrated guarantees. "
            "The component models share data and rate features, so they are not independent votes. The Poisson "
            "row is an unweighted benchmark; lower temporal validation log loss is better._",
            "",
        ]
    )
    return rows


def model_analysis_text(forecast: MatchForecast) -> list[str]:
    """Render compact ensemble and model diagnostics for plain text."""
    analysis = forecast.scenario_analysis
    ensemble = _ensemble(forecast)
    if analysis is None or ensemble is None:
        return []
    lines = [
        f"Ensemble 1X2: home {ensemble.home_win:.1%} "
        f"({ensemble.home_win_interval[0]:.1%}-{ensemble.home_win_interval[1]:.1%}), "
        f"draw {ensemble.draw:.1%} ({ensemble.draw_interval[0]:.1%}-{ensemble.draw_interval[1]:.1%}), "
        f"away {ensemble.away_win:.1%} ({ensemble.away_win_interval[0]:.1%}-{ensemble.away_win_interval[1]:.1%})",
        f"Model agreement: {analysis.agreement_label} (maximum disagreement {analysis.model_disagreement:.1%})",
        f"Recent-data quality: {analysis.data_quality_label} (uncertainty {analysis.data_uncertainty:.0%})",
        f"Simulated 80% goal range: home {analysis.home_goals_interval[0]}-{analysis.home_goals_interval[1]}, "
        f"away {analysis.away_goals_interval[0]}-{analysis.away_goals_interval[1]}, "
        f"total {analysis.total_goals_interval[0]}-{analysis.total_goals_interval[1]} "
        f"({analysis.simulations:,} scenarios)",
        f"Tail scenarios: 0-0 {analysis.scoreless_draw:.1%}, 5+ goals {analysis.five_plus_goals:.1%}, "
        f"3+ goal margin {analysis.three_plus_goal_margin:.1%}",
        "Algorithms: "
        + "; ".join(
            f"{item.model_name} H/D/A {item.home_win:.0%}/{item.draw:.0%}/{item.away_win:.0%} "
            f"O2.5 {item.over_2_5:.0%} BTTS {item.btts_yes:.0%}"
            for item in analysis.model_estimates
        ),
    ]
    return lines
