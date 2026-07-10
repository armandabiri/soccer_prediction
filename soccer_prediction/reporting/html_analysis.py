"""HTML rendering for model robustness and simulated scenarios."""

from __future__ import annotations

from html import escape

from soccer_prediction.models import MatchForecast

__all__ = ["scenario_section"]


def scenario_section(forecast: MatchForecast) -> str:
    """Render cross-model agreement and tail-scenario diagnostics."""
    analysis = forecast.scenario_analysis
    if analysis is None:
        return ""
    home = escape(forecast.fixture.home_team)
    away = escape(forecast.fixture.away_team)
    estimates = "".join(
        f"<tr><td>{escape(item.model_name.replace('_', ' ').title())}</td>"
        f'<td class="n">{item.home_win:.1%}</td><td class="n">{item.draw:.1%}</td>'
        f'<td class="n">{item.away_win:.1%}</td>'
        f'<td class="n">{item.home_expected_goals:.2f}-{item.away_expected_goals:.2f}</td></tr>'
        for item in analysis.model_estimates
    )
    header = (
        f'<thead><tr><th>Model</th><th class="n">{home}</th><th class="n">Draw</th>'
        f'<th class="n">{away}</th><th class="n">Expected goals</th></tr></thead>'
    )
    scenarios = (
        f"<tr><td>Middle 80% home goals</td><td class=\"n\">"
        f"{analysis.home_goals_interval[0]}-{analysis.home_goals_interval[1]}</td></tr>"
        f"<tr><td>Middle 80% away goals</td><td class=\"n\">"
        f"{analysis.away_goals_interval[0]}-{analysis.away_goals_interval[1]}</td></tr>"
        f"<tr><td>Middle 80% total goals</td><td class=\"n\">"
        f"{analysis.total_goals_interval[0]}-{analysis.total_goals_interval[1]}</td></tr>"
        f'<tr><td>{home} clean sheet</td><td class="n">{analysis.home_clean_sheet:.1%}</td></tr>'
        f'<tr><td>{away} clean sheet</td><td class="n">{analysis.away_clean_sheet:.1%}</td></tr>'
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
    return (
        f'<h2>Robustness &amp; random scenarios</h2><div class="card"><div style="overflow-x:auto">'
        f"<table>{header}<tbody>{estimates}</tbody></table></div>"
        f'<table><thead><tr><th>Scenario</th><th class="n">Range / probability</th></tr></thead>'
        f"<tbody>{scenarios}</tbody></table>{note}</div>"
    )
