"""Self-contained HTML match-forecast report renderer."""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape

from soccer_prediction.models import MatchForecast, ScorelineGrid
from soccer_prediction.reporting.html_analysis import confidence_interval_section, scenario_section
from soccer_prediction.reporting.html_components import (
    _CSS,
    _dot,
    _history_section,
    _pct,
    _scorers_section,
    _team_color,
    _team_legend,
)
from soccer_prediction.reporting.html_context import context_section
from soccer_prediction.reporting.html_model_comparison import ensemble_heatmap_section, model_comparison_section

__all__ = ["render_html", "example_usage", "main"]

def render_html(forecast: MatchForecast, *, title: str | None = None, generated_at: datetime | None = None) -> str:
    """Render a MatchForecast as a styled, self-contained HTML document."""
    home = escape(forecast.fixture.home_team)
    away = escape(forecast.fixture.away_team)
    heading = escape(title) if title else f"{home} vs {away}"
    stamp = (generated_at or datetime.now(UTC)).strftime("%Y-%m-%d_%H-%M-%S")
    home_p, draw_p, away_p = forecast.correct_score.home_draw_away()
    sections = [
        _tiles(forecast, home, away, home_p, draw_p, away_p),
        _result_section(home, away, home_p, draw_p, away_p),
        confidence_interval_section(forecast),
        model_comparison_section(forecast),
        ensemble_heatmap_section(forecast),
        scenario_section(forecast),
        context_section(forecast),
        _knockout_section(forecast, home, away),
        _goals_section(forecast),
        _score_section(forecast.correct_score),
        _half_section(forecast, home, away),
        _corners_section(forecast, home, away),
        _cards_section(forecast),
        _scorers_section(forecast),
        _history_section(forecast),
    ]
    notes = "; ".join(escape(note) for note in forecast.generated_notes) or "model priors"
    body = "\n".join(sections)
    return (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{heading}</title><style>{_CSS}</style></head><body><div class="wrap">'
        f"<h1>{heading}</h1>"
        f'<p class="sub">Selected model: <span class="pill">{escape(forecast.model_name)}</span> '
        f"&nbsp; Generated: {stamp} &nbsp; Data: {notes}</p>"
        f"{_team_legend([forecast.fixture.home_team, forecast.fixture.away_team])}"
        f"{body}"
        f'<p class="foot">Generated {stamp}. Probabilities are model estimates from the historical '
        f"team stats listed above; per-half and minimum-corner figures are illustrative outputs, "
        f"not guaranteed outcomes.</p>"
        f"</div></body></html>"
    )


def _row(label: str, probability: float, color: str | None = None) -> str:
    width = max(0.0, min(100.0, probability * 100))
    style = f' style="background:{color}22"' if color else ""
    return (
        f"<tr{style}><td>{label}</td>"
        f'<td><div class="bar"><span style="width:{width:.1f}%"></span></div></td>'
        f'<td class="n">{_pct(probability)}</td></tr>'
    )


def _top_score(grid: ScorelineGrid) -> str:
    best_label = "0-0"
    best = -1.0
    for home_goals, grid_row in enumerate(grid.probabilities):
        for away_goals, probability in enumerate(grid_row):
            if probability > best:
                best = probability
                home_label = f"{home_goals}{'+' if home_goals == grid.home_goals_max else ''}"
                away_label = f"{away_goals}{'+' if away_goals == grid.away_goals_max else ''}"
                best_label = f"{home_label}-{away_label}"
    return best_label


def _tiles(
    forecast: MatchForecast,
    home: str,
    away: str,
    home_p: float,
    draw_p: float,
    away_p: float,
) -> str:
    result = max(((home, home_p), ("Draw", draw_p), (away, away_p)), key=lambda item: item[1])[0]
    tiles = [
        ("Most likely result", escape(result)),
        ("Likeliest score", _top_score(forecast.correct_score)),
        ("Both teams to score", _pct(forecast.btts.probability)),
        ("Over 2.5 goals", _pct(forecast.over_under.probability)),
    ]
    if forecast.scorers and forecast.scorers.players:
        top_scorer = forecast.scorers.players[0]
        tiles.append(("Top anytime scorer", f"{escape(top_scorer.player)} {_pct(top_scorer.anytime_scorer)}"))
    cells = "".join(f'<div class="tile"><div class="k">{k}</div><div class="v">{v}</div></div>' for k, v in tiles)
    return f'<div class="tiles">{cells}</div>'


def _result_section(home: str, away: str, home_p: float, draw_p: float, away_p: float) -> str:
    home_color = _team_color(home)
    away_color = _team_color(away)
    rows = (
        _row(f"{_dot(home_color)}{home} win", home_p, home_color)
        + _row("Draw", draw_p)
        + _row(f"{_dot(away_color)}{away} win", away_p, away_color)
    )
    return _table("Match result (1X2)", "Outcome", rows)


def _knockout_section(forecast: MatchForecast, home: str, away: str) -> str:
    knockout = forecast.knockout
    if knockout is None:
        return ""
    home_color = _team_color(home)
    away_color = _team_color(away)
    rows = (
        _row(f"{_dot(home_color)}{home} to advance", knockout.home_advance, home_color)
        + _row(f"{_dot(away_color)}{away} to advance", knockout.away_advance, away_color)
        + _row("Goes to extra time", knockout.goes_to_extra_time)
        + _row("Goes to penalties", knockout.goes_to_penalties)
    )
    header = '<thead><tr><th>Outcome</th><th>Likelihood</th><th class="n">Probability</th></tr></thead>'
    settled = (
        f"Settled in normal time {_pct(knockout.decided_in_normal_time)}, "
        f"extra time {_pct(knockout.decided_in_extra_time)}, penalties {_pct(knockout.goes_to_penalties)}."
    )
    shootout = (
        f"Shootout: {home} {_pct(knockout.home_shootout_win)} vs {away} {_pct(knockout.away_shootout_win)} "
        f"(penalty conversion {_pct(knockout.home_penalty_conversion)} / "
        f"{_pct(knockout.away_penalty_conversion)}; best-of-five plus sudden death)."
    )
    note = f'<p class="foot">{settled} {shootout}</p>'
    return (
        f'<h2>Extra time &amp; penalties</h2><div class="card"><table>{header}<tbody>{rows}</tbody></table>{note}</div>'
    )


def _goals_section(forecast: MatchForecast) -> str:
    over = forecast.over_under.probability
    rows = (
        _row("Over 2.5 goals", over)
        + _row("Under 2.5 goals", 1.0 - over)
        + _row("Both teams to score - yes", forecast.btts.probability)
        + _row("Both teams to score - no", 1.0 - forecast.btts.probability)
    )
    return _table("Goals markets", "Market", rows)


def _score_section(grid: ScorelineGrid) -> str:
    scored: list[tuple[str, float]] = []
    for home_goals, grid_row in enumerate(grid.probabilities):
        for away_goals, probability in enumerate(grid_row):
            home_label = f"{home_goals}{'+' if home_goals == grid.home_goals_max else ''}"
            away_label = f"{away_goals}{'+' if away_goals == grid.away_goals_max else ''}"
            scored.append((f"{home_label}-{away_label}", probability))
    scored.sort(key=lambda item: item[1], reverse=True)
    rows = "".join(_row(label, probability) for label, probability in scored[:6])
    return _table("Most likely correct scores", "Score", rows)


def _p_team_scores(grid: ScorelineGrid) -> tuple[float, float]:
    home_scores = 1.0 - sum(grid.probabilities[0])
    away_scores = 1.0 - sum(row[0] for row in grid.probabilities)
    return home_scores, away_scores


def _half_section(forecast: MatchForecast, home: str, away: str) -> str:
    per_half = forecast.per_half
    first_home, first_away = _p_team_scores(per_half.first_half_grid)
    second_home, second_away = _p_team_scores(per_half.second_half_grid)
    ht = per_half.half_time_result.selection if per_half.half_time_result else "n/a"
    rows = (
        f'<tr><td>1st half - {home} scores</td><td class="n">'
        f'{per_half.first_half_home_expected:.2f} model goals</td><td class="n">{_pct(first_home)}</td></tr>'
        f'<tr><td>1st half - {away} scores</td><td class="n">'
        f'{per_half.first_half_away_expected:.2f} model goals</td><td class="n">{_pct(first_away)}</td></tr>'
        f'<tr><td>2nd half - {home} scores</td><td class="n">'
        f'{per_half.second_half_home_expected:.2f} model goals</td><td class="n">{_pct(second_home)}</td></tr>'
        f'<tr><td>2nd half - {away} scores</td><td class="n">'
        f'{per_half.second_half_away_expected:.2f} model goals</td><td class="n">{_pct(second_away)}</td></tr>'
        f'<tr><td>Half-time result (likeliest)</td><td class="n">{escape(ht)}</td><td class="n">-</td></tr>'
    )
    header = '<thead><tr><th>Segment</th><th class="n">Expected</th><th class="n">Probability</th></tr></thead>'
    return f'<h2>Per-half scoring</h2><div class="card"><table>{header}<tbody>{rows}</tbody></table></div>'


def _corners_section(forecast: MatchForecast, home: str, away: str) -> str:
    corners = forecast.corners
    lines = "".join(
        f'<tr><td>Over {line:g} corners</td><td class="n">-</td><td class="n">{_pct(prob)}</td></tr>'
        for line, prob in sorted(corners.total_over_lines.items())
    )
    body = (
        f'<tr><td>{home} corners (expected / min)</td><td class="n">{corners.home_expected:.2f}</td>'
        f'<td class="n">min {corners.home_minimum}</td></tr>'
        f'<tr><td>{away} corners (expected / min)</td><td class="n">{corners.away_expected:.2f}</td>'
        f'<td class="n">min {corners.away_minimum}</td></tr>'
        f'<tr><td>Total corners (expected)</td><td class="n">{corners.total_expected:.2f}</td>'
        f'<td class="n">-</td></tr>{lines}'
    )
    header = '<thead><tr><th>Corners market</th><th class="n">Expected</th><th class="n">Value</th></tr></thead>'
    note = _prior_note(forecast, "corners", "corner")
    return f'<h2>Corners</h2><div class="card"><table>{header}<tbody>{body}</tbody></table>{note}</div>'


def _cards_section(forecast: MatchForecast) -> str:
    cards = forecast.cards
    lines = "".join(
        f'<tr><td>Over {line:g} cards</td><td class="n">{_pct(prob)}</td></tr>'
        for line, prob in sorted(cards.over_under_lines.items())
    )
    booking = cards.booking_points_expected or 0.0
    body = (
        f'<tr><td>Yellow cards (expected)</td><td class="n">{cards.yellows_expected:.2f}</td></tr>'
        f'<tr><td>Red cards (expected)</td><td class="n">{cards.reds_expected:.2f}</td></tr>'
        f'<tr><td>Total cards (expected)</td><td class="n">{cards.total_expected:.2f}</td></tr>'
        f'<tr><td>Booking points (expected)</td><td class="n">{booking:.0f}</td></tr>{lines}'
    )
    header = '<thead><tr><th>Cards market</th><th class="n">Value</th></tr></thead>'
    note = _prior_note(forecast, "cards", "card")
    return f'<h2>Cards</h2><div class="card"><table>{header}<tbody>{body}</tbody></table>{note}</div>'


def _prior_note(forecast: MatchForecast, kind: str, label: str) -> str:
    if not forecast.history:
        return ""
    if kind == "corners":
        empty = all(record.corners_for == 0 and record.corners_against == 0 for record in forecast.history)
    else:
        empty = all(record.yellows == 0 and record.reds == 0 for record in forecast.history)
    if not empty:
        return ""
    return (
        f'<p class="foot">The data source carries no {label} data, so league-average priors are '
        f'shown here (not team-specific). Use source="api_football" (free key) for real {label} markets.</p>'
    )


def _table(heading: str, first_column: str, rows: str) -> str:
    header = f'<thead><tr><th>{first_column}</th><th>Likelihood</th><th class="n">Probability</th></tr></thead>'
    return f'<h2>{heading}</h2><div class="card"><table>{header}<tbody>{rows}</tbody></table></div>'


def example_usage() -> None:
    """Render a sample forecast to HTML."""
    from soccer_prediction.public import forecast_fixture

    print(len(render_html(forecast_fixture("Brazil", "Argentina"))))


def main() -> None:
    """Module entry point."""
    example_usage()
