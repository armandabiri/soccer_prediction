"""HTML rendering for form, head-to-head, network, and style context."""

from __future__ import annotations

from html import escape

from soccer_prediction.models import MatchForecast

__all__ = ["context_section"]


def context_section(forecast: MatchForecast) -> str:
    """Render the historical evidence and indirect comparison network."""
    context = forecast.matchup_context
    if context is None:
        return ""
    home = escape(forecast.fixture.home_team)
    away = escape(forecast.fixture.away_team)
    form_rows = "".join(
        f"<tr><td>{escape(form.team)}</td><td class=\"n\">{form.matches}</td>"
        f'<td class="n">{form.effective_matches:.1f}</td><td class="n">{form.points_per_match:.2f}</td>'
        f'<td class="n">{form.goals_for_per_match:.2f}-{form.goals_against_per_match:.2f}</td>'
        f'<td class="n">{form.corners_for_per_match:.2f}</td>'
        f"<td>{escape('; '.join(form.recent_results) or 'n/a')}</td></tr>"
        for form in (context.home_form, context.away_form)
    )
    form_header = (
        '<thead><tr><th>Team</th><th class="n">Matches</th><th class="n">Effective</th>'
        '<th class="n">Pts/match</th><th class="n">Goals F-A</th><th class="n">Corners</th>'
        '<th>Last five</th></tr></thead>'
    )
    if context.head_to_head_matches:
        corners = (
            f"{context.head_to_head_average_corners:.2f} average corners"
            if context.head_to_head_average_corners > 0
            else "corner data unavailable"
        )
        direct = (
            f"{context.head_to_head_matches} meetings: {home} {context.home_head_to_head_wins} wins, "
            f"{context.head_to_head_draws} draws, {away} {context.away_head_to_head_wins} wins; "
            f"{context.head_to_head_average_goals:.2f} average goals; {corners}."
        )
    else:
        direct = "No direct meetings were present in the loaded history."
    paths = (
        "; ".join(" &rarr; ".join(escape(team) for team in path) for path in context.connection_paths)
        if context.connection_paths
        else "No indirect path found within four links."
    )
    evidence = (
        f"<p><strong>Head-to-head:</strong> {direct}</p>"
        f"<p><strong>Opponent network:</strong> {context.network_team_count} teams across "
        f"{context.network_match_count} matches. <strong>Paths:</strong> {paths}</p>"
        f"<p><strong>Inferred style:</strong> {escape(context.style_label)}. "
        f"{escape(context.style_description)}</p>"
        f'<p class="foot">Effective sample size strongly discounts older matches. Network paths adjust '
        f"schedule strength but do not imply transitive wins.</p>"
    )
    return (
        f'<h2>Form, head-to-head &amp; opponent network</h2><div class="card">'
        f'<div style="overflow-x:auto"><table>{form_header}<tbody>{form_rows}</tbody></table></div>'
        f"{evidence}</div>"
    )
