"""Forecast rendering helpers."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime

from soccer_prediction.models import BettingStrategy, MatchForecast
from soccer_prediction.reporting.model_analysis import model_analysis_markdown, model_analysis_text
from soccer_prediction.reporting.strategy_report import strategy_markdown, strategy_text

__all__ = ["render_json", "render_markdown", "render_text", "example_usage", "main"]


def _stamp(generated_at: datetime | None) -> str:
    return (generated_at or datetime.now(UTC)).strftime("%Y-%m-%d_%H-%M-%S")


def _history_summary(forecast: MatchForecast) -> str:
    if not forecast.history:
        return "Historical data used: none (model priors)"
    counts: dict[str, int] = {}
    for record in forecast.history:
        counts[record.team] = counts.get(record.team, 0) + 1
    detail = ", ".join(f"{team} {count}" for team, count in sorted(counts.items()))
    return f"Historical data used: {len(forecast.history)} matches ({detail})"


def _history_table_md(forecast: MatchForecast) -> list[str]:
    if not forecast.history:
        return ["### Historical data used", "", "_No historical data was available; model priors were used._"]
    rows = [
        "### Historical data used",
        "",
        "| Team | Date | Opponent | H/A | Score | HT | Corners | Y/R |",
        "| --- | --- | --- | :-: | :-: | :-: | :-: | :-: |",
    ]
    displayed = sorted(forecast.history, key=lambda item: item.date, reverse=True)[:80]
    for record in displayed:
        venue = "H" if record.is_home else "A"
        rows.append(
            f"| {record.team} | {record.date.isoformat()} | {record.opponent} | {venue} "
            f"| {record.goals_for}-{record.goals_against} | {record.ht_goals_for}-{record.ht_goals_against} "
            f"| {record.corners_for}-{record.corners_against} | {record.yellows}/{record.reds} |"
        )
    if len(forecast.history) > len(displayed):
        rows.extend(["", f"_Showing the newest {len(displayed)} of {len(forecast.history)} network records._"])
    return rows


def _scorers_table_md(forecast: MatchForecast) -> list[str]:
    scorers = forecast.scorers
    if scorers is None or not scorers.players:
        return ["### Goalscorers & assists", "", "_No squad data available for player markets._"]
    rows = [
        "### Goalscorers & assists",
        "",
        "| Player | Team | Pos | Recent (max 20) | Score | Assist | Score/assist | First |",
        "| --- | --- | :-: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for player in scorers.players[:12]:
        rows.append(
            f"| {player.player} | {player.team} | {player.position} "
            f"| {player.recent_goals:.1f}G/{player.recent_assists:.1f}A in {player.recent_appearances}"
            f"{'*' if player.recent_form_estimated else ''} | {player.score_probability:.0%} "
            f"| {player.assist_probability:.0%} | {player.to_score_or_assist:.0%} "
            f"| {player.first_scorer:.0%} |"
        )
    rows.extend(
        [
            "",
            "_* Recent form is an up-to-20 equivalent estimated from aggregate totals when match-level recent data "
            "is unavailable._",
        ]
    )
    return rows


def _knockout_md(forecast: MatchForecast) -> list[str]:
    knockout = forecast.knockout
    if knockout is None:
        return []
    home, away = forecast.fixture.home_team, forecast.fixture.away_team
    return [
        "### Extra time & penalties",
        "",
        f"- {home} to advance: {knockout.home_advance:.1%}",
        f"- {away} to advance: {knockout.away_advance:.1%}",
        f"- Goes to extra time: {knockout.goes_to_extra_time:.1%}",
        f"- Goes to penalties: {knockout.goes_to_penalties:.1%}",
        f"- Settled in: normal time {knockout.decided_in_normal_time:.0%}, "
        f"extra time {knockout.decided_in_extra_time:.0%}, penalties {knockout.goes_to_penalties:.0%}",
        f"- Shootout: {home} {knockout.home_shootout_win:.0%} vs {away} {knockout.away_shootout_win:.0%} "
        f"(penalty conversion {knockout.home_penalty_conversion:.0%} / {knockout.away_penalty_conversion:.0%})",
        "",
    ]


def _context_md(forecast: MatchForecast) -> list[str]:
    context = forecast.matchup_context
    if context is None:
        return []
    home, away = forecast.fixture.home_team, forecast.fixture.away_team
    rows = [
        "### Form, head-to-head & opponent network",
        "",
        "| Team | Matches | Effective | Pts/match | Goals F-A | Corners | Morale proxy | Streak | Last five |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | :-: | --- |",
    ]
    for form in (context.home_form, context.away_form):
        recent = "; ".join(form.recent_results) or "n/a"
        streak = f"W{form.result_streak}" if form.result_streak > 0 else f"L{abs(form.result_streak)}"
        if form.result_streak == 0:
            streak = "—"
        rows.append(
            f"| {form.team} | {form.matches} | {form.effective_matches:.1f} | {form.points_per_match:.2f} "
            f"| {form.goals_for_per_match:.2f}-{form.goals_against_per_match:.2f} "
            f"| {form.corners_for_per_match:.2f} | {form.morale_label} {form.morale_index:+.2f} "
            f"| {streak} | {recent} |"
        )
    rows.extend([""])
    if context.head_to_head_matches:
        corner_text = (
            f"{context.head_to_head_average_corners:.2f} average corners"
            if context.head_to_head_average_corners > 0
            else "corner data unavailable"
        )
        rows.append(
            f"- Direct meetings: {context.head_to_head_matches} — {home} wins "
            f"{context.home_head_to_head_wins}, draws {context.head_to_head_draws}, {away} wins "
            f"{context.away_head_to_head_wins}; {context.head_to_head_average_goals:.2f} average goals; {corner_text}."
        )
    else:
        rows.append("- Direct meetings: none in the loaded history.")
    rows.append(
        f"- Opponent network: {context.network_team_count} teams across {context.network_match_count} matches."
    )
    if context.connection_paths:
        paths = "; ".join(" → ".join(path) for path in context.connection_paths)
        rows.append(f"- Indirect comparison paths: {paths}.")
    else:
        rows.append("- Indirect comparison paths: none found within four links.")
    rows.extend(
        [
            f"- Inferred game style: **{context.style_label}**. {context.style_description}",
            "",
            "_Morale is a bounded recent-results proxy, not a direct psychological measurement. Effective sample "
            "size discounts older matches; network paths adjust schedule strength but do not imply transitive wins._",
            "",
        ]
    )
    return rows


def render_text(
    forecast: MatchForecast,
    *,
    generated_at: datetime | None = None,
    strategy: BettingStrategy | None = None,
) -> str:
    """Render a forecast as readable text."""
    fixture = forecast.fixture
    half = forecast.per_half.half_time_result
    lines = [
        f"{fixture.home_team} vs {fixture.away_team}",
        f"Model: {forecast.model_name}",
        f"Generated: {_stamp(generated_at)}",
        f"1X2: {forecast.result.selection} {forecast.result.probability:.1%}",
        f"BTTS yes: {forecast.btts.probability:.1%}",
        f"Over 2.5: {forecast.over_under.probability:.1%}",
        f"Corners: {forecast.corners.home_expected:.2f} + {forecast.corners.away_expected:.2f}"
        f" = {forecast.corners.total_expected:.2f}",
        f"Minimum corners: {forecast.corners.home_minimum}-{forecast.corners.away_minimum}",
        f"Cards: yellows {forecast.cards.yellows_expected:.2f}, reds {forecast.cards.reds_expected:.2f}",
        f"Half-time: {half.selection if half else 'n/a'}",
        _history_summary(forecast),
    ]
    lines.extend(model_analysis_text(forecast))
    if forecast.matchup_context is not None:
        context = forecast.matchup_context
        paths = "; ".join(" -> ".join(path) for path in context.connection_paths) or "none"
        lines.extend(
            [
                f"Game style: {context.style_label}",
                f"Head-to-head: {context.head_to_head_matches} meetings "
                f"({fixture.home_team} {context.home_head_to_head_wins} wins, "
                f"draws {context.head_to_head_draws}, {fixture.away_team} {context.away_head_to_head_wins} wins)",
                f"Opponent network: {context.network_team_count} teams, paths: {paths}",
                f"Morale proxy: {context.home_form.team} {context.home_form.morale_label} "
                f"({context.home_form.morale_index:+.2f}), {context.away_form.team} "
                f"{context.away_form.morale_label} ({context.away_form.morale_index:+.2f})",
            ]
        )
    if forecast.knockout is not None:
        knockout = forecast.knockout
        home_team, away_team = fixture.home_team, fixture.away_team
        lines.append(f"Advance: {home_team} {knockout.home_advance:.0%} / {away_team} {knockout.away_advance:.0%}")
        lines.append(f"Extra time: {knockout.goes_to_extra_time:.0%}, penalties: {knockout.goes_to_penalties:.0%}")
    if forecast.scorers and forecast.scorers.players:
        top = forecast.scorers.players[:3]
        names = ", ".join(
            f"{player.player} score {player.score_probability:.0%} / assist {player.assist_probability:.0%}"
            for player in top
        )
        lines.append(f"Top player markets: {names}")
    if forecast.generated_notes:
        lines.append("Notes: " + "; ".join(forecast.generated_notes))
    if strategy is not None:
        lines.extend(["", strategy_text(strategy)])
    return "\n".join(lines)


def render_json(forecast: MatchForecast, *, strategy: BettingStrategy | None = None) -> str:
    """Render a forecast as JSON (includes the historical data used)."""
    payload = asdict(forecast)
    if strategy is not None:
        payload["betting_strategy"] = asdict(strategy)
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def render_markdown(
    forecast: MatchForecast,
    *,
    generated_at: datetime | None = None,
    strategy: BettingStrategy | None = None,
) -> str:
    """Render a forecast as a multi-section Markdown report."""
    fixture = forecast.fixture
    home, away = fixture.home_team, fixture.away_team
    home_p, draw_p, away_p = forecast.correct_score.home_draw_away()
    corners = forecast.corners
    cards = forecast.cards
    per_half = forecast.per_half
    first_home, first_away = per_half.first_half_home_expected, per_half.first_half_away_expected
    second_home, second_away = per_half.second_half_home_expected, per_half.second_half_away_expected
    half_result = per_half.half_time_result.selection if per_half.half_time_result else "n/a"
    corner_lines = " ".join(f"O{line:g} {prob:.0%};" for line, prob in sorted(corners.total_over_lines.items()))
    lines = [
        f"## {home} vs {away}",
        f"*Model: {forecast.model_name} &middot; Generated: {_stamp(generated_at)}*",
        "",
        "### Match result (1X2)",
        "| Outcome | Probability |",
        "| --- | ---: |",
        f"| {home} win | {home_p:.1%} |",
        f"| Draw | {draw_p:.1%} |",
        f"| {away} win | {away_p:.1%} |",
        "",
        *model_analysis_markdown(forecast),
        *_context_md(forecast),
        *_knockout_md(forecast),
        "### Goals",
        f"- Over 2.5 goals: {forecast.over_under.probability:.1%}",
        f"- Both teams to score: {forecast.btts.probability:.1%}",
        "",
        "### Corners",
        f"- {home}: {corners.home_expected:.2f} expected (minimum {corners.home_minimum})",
        f"- {away}: {corners.away_expected:.2f} expected (minimum {corners.away_minimum})",
        f"- Total: {corners.total_expected:.2f} corners &mdash; {corner_lines}",
        "",
        "### Cards",
        f"- Yellows {cards.yellows_expected:.2f}, reds {cards.reds_expected:.2f}, total {cards.total_expected:.2f}",
        "",
        "### Per-half scoring",
        f"- 1st-half expected goals: {first_home:.2f} - {first_away:.2f}",
        f"- 2nd-half expected goals: {second_home:.2f} - {second_away:.2f}",
        f"- Likeliest half-time result: {half_result}",
        "",
        *_scorers_table_md(forecast),
        "",
        *_history_table_md(forecast),
    ]
    if strategy is not None:
        lines.extend(["", strategy_markdown(strategy)])
    return "\n".join(lines)


def example_usage() -> None:
    """Render a sample forecast."""
    from soccer_prediction.public import forecast_fixture

    print(render_text(forecast_fixture("Brazil", "Argentina")))


def main() -> None:
    """Module entry point."""
    example_usage()
