"""Forecast rendering helpers."""

from __future__ import annotations

import json
from dataclasses import asdict

from soccer_prediction.models import MatchForecast

__all__ = ["render_json", "render_markdown", "render_text", "example_usage", "main"]


def render_text(forecast: MatchForecast) -> str:
    """Render a forecast as readable text."""
    fixture = forecast.fixture
    lines = [
        f"{fixture.home_team} vs {fixture.away_team}",
        f"Model: {forecast.model_name}",
        f"1X2: {forecast.result.selection} {forecast.result.probability:.1%}",
        f"BTTS yes: {forecast.btts.probability:.1%}",
        f"Over 2.5: {forecast.over_under.probability:.1%}",
        f"Corners: {forecast.corners.home_expected:.2f} + {forecast.corners.away_expected:.2f}"
        f" = {forecast.corners.total_expected:.2f}",
        f"Minimum corners: {forecast.corners.home_minimum}-{forecast.corners.away_minimum}",
        f"Cards: yellows {forecast.cards.yellows_expected:.2f}, reds {forecast.cards.reds_expected:.2f}",
        f"Half-time: {forecast.per_half.half_time_result.selection if forecast.per_half.half_time_result else 'n/a'}",
    ]
    if forecast.generated_notes:
        lines.append("Notes: " + "; ".join(forecast.generated_notes))
    return "\n".join(lines)


def render_json(forecast: MatchForecast) -> str:
    """Render a forecast as JSON."""
    return json.dumps(asdict(forecast), indent=2, sort_keys=True, default=str)


def render_markdown(forecast: MatchForecast) -> str:
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
        f"*Model: {forecast.model_name}*",
        "",
        "### Match result (1X2)",
        "| Outcome | Probability |",
        "| --- | ---: |",
        f"| {home} win | {home_p:.1%} |",
        f"| Draw | {draw_p:.1%} |",
        f"| {away} win | {away_p:.1%} |",
        "",
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
    ]
    return "\n".join(lines)


def example_usage() -> None:
    """Render a sample forecast."""
    from soccer_prediction.public import forecast_fixture

    print(render_text(forecast_fixture("Brazil", "Argentina")))


def main() -> None:
    """Module entry point."""
    example_usage()
