"""HTML rendering for model robustness and simulated scenarios."""

from __future__ import annotations

from html import escape

from soccer_prediction.models import MatchForecast

__all__ = ["confidence_interval_section", "scenario_section"]


def confidence_interval_section(forecast: MatchForecast) -> str:
    """Render the ensemble 1X2 conclusion with approximate uncertainty whiskers."""
    analysis = forecast.scenario_analysis
    if analysis is None:
        return ""
    ensemble = next((item for item in analysis.model_estimates if item.is_ensemble), None)
    if ensemble is None:
        return ""
    outcomes = (
        (forecast.fixture.home_team, ensemble.home_win, ensemble.home_win_interval),
        ("Draw", ensemble.draw, ensemble.draw_interval),
        (forecast.fixture.away_team, ensemble.away_win, ensemble.away_win_interval),
    )
    rows: list[str] = []
    for label, probability, interval in outcomes:
        lower, upper = interval
        rows.append(
            f'<div class="ci-row"><div>{escape(label)}</div><div class="ci-track">'
            f'<span class="ci-range" style="left:{lower * 100:.1f}%;width:{(upper - lower) * 100:.1f}%"></span>'
            f'<span class="ci-point" style="left:{probability * 100:.1f}%"></span></div>'
            f'<div class="ci-value">{probability:.1%} ({lower:.1%}–{upper:.1%})</div></div>'
        )
    level = analysis.confidence_level
    return (
        f'<h2>Ensemble conclusion uncertainty</h2><div class="card"><div class="ci-chart">{"".join(rows)}</div>'
        f'<p class="foot">Point marker and approximate {level:.0%} sensitivity range for the ensemble. '
        f"It combines recency-weighted effective evidence with model-family disagreement and is not a "
        f"calibrated confidence guarantee.</p></div>"
    )


def scenario_section(forecast: MatchForecast) -> str:
    """Render cross-model agreement and tail-scenario diagnostics."""
    analysis = forecast.scenario_analysis
    if analysis is None:
        return ""
    home = escape(forecast.fixture.home_team)
    away = escape(forecast.fixture.away_team)
    scenarios = (
        f"<tr><td>Middle 80% home goals</td><td class=\"n\">"
        f"{analysis.home_goals_interval[0]}-{analysis.home_goals_interval[1]}</td></tr>"
        f"<tr><td>Middle 80% away goals</td><td class=\"n\">"
        f"{analysis.away_goals_interval[0]}-{analysis.away_goals_interval[1]}</td></tr>"
        f"<tr><td>Middle 80% total goals</td><td class=\"n\">"
        f"{analysis.total_goals_interval[0]}-{analysis.total_goals_interval[1]}</td></tr>"
        f'<tr><td>{home} clean sheet</td><td class="n">{analysis.home_clean_sheet:.1%}</td></tr>'
        f'<tr><td>{away} clean sheet</td><td class="n">{analysis.away_clean_sheet:.1%}</td></tr>'
        f'<tr><td>Scoreless draw</td><td class="n">{analysis.scoreless_draw:.1%}</td></tr>'
        f'<tr><td>Five or more goals</td><td class="n">{analysis.five_plus_goals:.1%}</td></tr>'
        f'<tr><td>Winning margin of 3+</td><td class="n">{analysis.three_plus_goal_margin:.1%}</td></tr>'
    )
    label = escape(analysis.agreement_label.title())
    note = (
        f'<p class="foot"><strong>{label} model agreement:</strong> maximum 1X2 spread '
        f"{analysis.model_disagreement:.1%}. Outcome uncertainty {analysis.outcome_uncertainty:.0%}. "
        f"Recent-data quality is {escape(analysis.data_quality_label)} "
        f"(data uncertainty {analysis.data_uncertainty:.0%}). "
        f"Intervals contain the middle 80% of {analysis.simulations:,} reproducible simulated scenarios; "
        f"they are ranges of possible match outcomes, not guarantees.</p>"
    )
    tails = (
        ("0-0", analysis.scoreless_draw),
        ("5+ goals", analysis.five_plus_goals),
        ("3+ goal margin", analysis.three_plus_goal_margin),
        (f"{home} clean sheet", analysis.home_clean_sheet),
        (f"{away} clean sheet", analysis.away_clean_sheet),
    )
    bars = "".join(
        f'<div class="tail-row"><span>{label}</span><span class="tail-track">'
        f'<i style="width:{probability * 100:.1f}%"></i></span>'
        f'<small>{probability:.1%}</small></div>'
        for label, probability in tails
    )
    return (
        f'<h2>Robustness &amp; random scenarios</h2><div class="card"><h3>Tail scenario probabilities</h3>'
        f'<div class="tail-chart">{bars}</div><div class="table-scroll">'
        f'<table><thead><tr><th>Scenario</th><th class="n">Range / probability</th></tr></thead>'
        f"<tbody>{scenarios}</tbody></table></div>{note}</div>"
    )
