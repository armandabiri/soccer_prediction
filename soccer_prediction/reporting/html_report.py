"""Self-contained HTML match-forecast report renderer."""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape

from soccer_prediction.models import MatchForecast, ScorelineGrid

__all__ = ["render_html", "example_usage", "main"]

_CSS = """
:root { color-scheme: light dark; --bg:#f5f7f4; --card:#ffffff; --ink:#12160f; --muted:#586152;
  --line:#e4e8e0; --accent:#1a7f4b; --accent2:#2563eb; --bar:#e0e5db; }
:root[data-theme="light"] { --bg:#f5f7f4; --card:#ffffff; --ink:#12160f; --muted:#586152;
  --line:#e4e8e0; --accent:#1a7f4b; --accent2:#2563eb; --bar:#e0e5db; }
@media (prefers-color-scheme: dark) { :root { --bg:#0e120d; --card:#161b13; --ink:#e9ede4;
  --muted:#98a48c; --line:#242b1f; --accent:#3ddc84; --accent2:#7cb0ff; --bar:#28301f; } }
:root[data-theme="dark"] { --bg:#0e120d; --card:#161b13; --ink:#e9ede4; --muted:#98a48c;
  --line:#242b1f; --accent:#3ddc84; --accent2:#7cb0ff; --bar:#28301f; }
* { box-sizing: border-box; }
body { margin:0; padding:32px 16px; background:var(--bg); color:var(--ink);
  font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }
.wrap { max-width: 900px; margin: 0 auto; }
h1 { font-size: 1.7rem; margin:0 0 4px; }
h2 { font-size: 1.05rem; margin: 26px 0 10px; letter-spacing:.02em; }
.sub { color: var(--muted); margin:0 0 20px; }
.tiles { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin-bottom:8px; }
.tile { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:14px 16px; }
.tile .k { color:var(--muted); font-size:.78rem; text-transform:uppercase; letter-spacing:.05em; }
.tile .v { font-size:1.35rem; font-weight:700; margin-top:4px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:6px 16px 14px; }
table { width:100%; border-collapse:collapse; }
th,td { text-align:left; padding:9px 6px; border-bottom:1px solid var(--line); }
th { color:var(--muted); font-weight:600; font-size:.82rem; }
td.n, th.n { text-align:right; font-variant-numeric:tabular-nums; }
.bar { position:relative; height:8px; border-radius:6px; background:var(--bar); overflow:hidden; min-width:80px; }
.bar > span { position:absolute; inset:0 auto 0 0; background:var(--accent2); border-radius:6px; }
.foot { color:var(--muted); font-size:.82rem; margin-top:24px; }
.pill { display:inline-block; background:var(--bar); border-radius:999px; padding:2px 10px; font-size:.8rem; }
.dot { display:inline-block; width:10px; height:10px; border-radius:3px; margin-right:7px;
  vertical-align:middle; border:1px solid rgba(128,128,128,.35); }
.legend { display:flex; flex-wrap:wrap; gap:16px; margin:-8px 0 18px; font-size:.85rem; }
.chip { display:inline-flex; align-items:center; }
"""

_FALLBACK_COLORS = (
    "#2563eb",
    "#dc2626",
    "#059669",
    "#d97706",
    "#7c3aed",
    "#0891b2",
    "#db2777",
    "#65a30d",
)
_TEAM_COLORS = {
    "switzerland": "#d52b1e",
    "colombia": "#fcd116",
    "brazil": "#009c3b",
    "argentina": "#6cabdd",
    "france": "#274796",
    "england": "#0a3d91",
    "germany": "#3a3a3a",
    "spain": "#c60b1e",
    "italy": "#1c6fb3",
    "portugal": "#006847",
    "netherlands": "#f36c21",
    "belgium": "#c8102e",
    "mexico": "#006341",
    "usa": "#1a3a6b",
    "united states": "#1a3a6b",
    "uruguay": "#5b9bd5",
    "croatia": "#b81b2c",
    "morocco": "#c1272d",
    "japan": "#1b2a6b",
    "canada": "#d80621",
}


def _team_color(team: str) -> str:
    """Return a stable display colour for a team (curated, else hashed)."""
    key = team.strip().casefold()
    if key in _TEAM_COLORS:
        return _TEAM_COLORS[key]
    digest = 0
    for char in key:
        digest = (digest * 31 + ord(char)) & 0xFFFFFFFF
    return _FALLBACK_COLORS[digest % len(_FALLBACK_COLORS)]


def _dot(color: str) -> str:
    return f'<span class="dot" style="background:{color}"></span>'


def _team_legend(teams: list[str]) -> str:
    chips = "".join(f'<span class="chip">{_dot(_team_color(team))}{escape(team)}</span>' for team in teams)
    return f'<p class="legend">{chips}</p>'


def render_html(forecast: MatchForecast, *, title: str | None = None, generated_at: datetime | None = None) -> str:
    """Render a MatchForecast as a styled, self-contained HTML document."""
    home = escape(forecast.fixture.home_team)
    away = escape(forecast.fixture.away_team)
    heading = escape(title) if title else f"{home} vs {away}"
    stamp = (generated_at or datetime.now(UTC)).strftime("%Y-%m-%d_%H-%M-%S")
    home_p, draw_p, away_p = forecast.correct_score.home_draw_away()
    sections = [
        _tiles(forecast, home, away, home_p, away_p),
        _result_section(home, away, home_p, draw_p, away_p),
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
        f'<p class="sub">Model: <span class="pill">{escape(forecast.model_name)}</span> '
        f"&nbsp; Generated: {stamp} &nbsp; Data: {notes}</p>"
        f"{_team_legend([forecast.fixture.home_team, forecast.fixture.away_team])}"
        f"{body}"
        f'<p class="foot">Generated {stamp}. Probabilities are model estimates from the historical '
        f"team stats listed above; per-half and minimum-corner figures are illustrative outputs, "
        f"not guaranteed outcomes.</p>"
        f"</div></body></html>"
    )


def _scorers_section(forecast: MatchForecast) -> str:
    scorers = forecast.scorers
    if scorers is None or not scorers.players:
        return ""
    rows: list[str] = []
    for player in scorers.players[:12]:
        color = _team_color(player.team)
        rows.append(
            f'<tr style="background:{color}22"><td>{escape(player.player)}</td>'
            f"<td>{_dot(color)}{escape(player.team)}</td>"
            f'<td class="n">{escape(player.position)}</td>'
            f'<td class="n">{_pct(player.anytime_scorer)}</td>'
            f'<td class="n">{_pct(player.to_score_or_assist)}</td>'
            f'<td class="n">{_pct(player.first_scorer)}</td></tr>'
        )
    header = (
        '<thead><tr><th>Player</th><th>Team</th><th class="n">Pos</th><th class="n">Anytime</th>'
        '<th class="n">Score/assist</th><th class="n">First</th></tr></thead>'
    )
    return (
        f'<h2>Goalscorers &amp; assists</h2><div class="card">'
        f'<div style="overflow-x:auto"><table>{header}<tbody>{"".join(rows)}</tbody></table></div>'
        f'<p class="foot">Anytime = to score anytime; Score/assist = to score or assist; '
        f"First = to open the scoring. Share-based estimates from historical goal/assist involvement.</p></div>"
    )


def _history_section(forecast: MatchForecast) -> str:
    if not forecast.history:
        return (
            '<h2>Historical data used</h2><div class="card">'
            '<p class="sub">No historical data was available; model priors were used.</p></div>'
        )
    rows: list[str] = []
    for record in sorted(forecast.history, key=lambda item: (item.team, item.date)):
        venue = "H" if record.is_home else "A"
        color = _team_color(record.team)
        rows.append(
            f'<tr style="background:{color}22"><td>{_dot(color)}{escape(record.team)}</td>'
            f'<td class="n">{record.date.isoformat()}</td>'
            f"<td>{escape(record.opponent)}</td>"
            f'<td class="n">{venue}</td>'
            f'<td class="n">{record.goals_for}-{record.goals_against}</td>'
            f'<td class="n">{record.ht_goals_for}-{record.ht_goals_against}</td>'
            f'<td class="n">{record.corners_for}-{record.corners_against}</td>'
            f'<td class="n">{record.yellows}/{record.reds}</td></tr>'
        )
    header = (
        '<thead><tr><th>Team</th><th class="n">Date</th><th>Opponent</th><th class="n">H/A</th>'
        '<th class="n">Score</th><th class="n">HT</th><th class="n">Corners</th><th class="n">Y/R</th></tr></thead>'
    )
    sources = ", ".join(sorted({record.source for record in forecast.history}))
    return (
        f'<h2>Historical data used</h2><div class="card">'
        f'<div style="overflow-x:auto"><table>{header}<tbody>{"".join(rows)}</tbody></table></div>'
        f'<p class="foot">{len(forecast.history)} matches from: {escape(sources)}. '
        f"Score = full-time goals for-against; HT = half-time; Corners = for-against; Y/R = yellow/red cards.</p></div>"
    )


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


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
                best_label = f"{home_goals}-{away_goals}"
    return best_label


def _tiles(forecast: MatchForecast, home: str, away: str, home_p: float, away_p: float) -> str:
    result = home if home_p >= away_p else away
    tiles = [
        ("Most likely result", escape(result)),
        ("Likeliest score", _top_score(forecast.correct_score)),
        ("Both teams to score", _pct(forecast.btts.probability)),
        ("Over 2.5 goals", _pct(forecast.over_under.probability)),
    ]
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
            scored.append((f"{home_goals}-{away_goals}", probability))
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
        f'{per_half.first_half_home_expected:.2f} xG</td><td class="n">{_pct(first_home)}</td></tr>'
        f'<tr><td>1st half - {away} scores</td><td class="n">'
        f'{per_half.first_half_away_expected:.2f} xG</td><td class="n">{_pct(first_away)}</td></tr>'
        f'<tr><td>2nd half - {home} scores</td><td class="n">'
        f'{per_half.second_half_home_expected:.2f} xG</td><td class="n">{_pct(second_home)}</td></tr>'
        f'<tr><td>2nd half - {away} scores</td><td class="n">'
        f'{per_half.second_half_away_expected:.2f} xG</td><td class="n">{_pct(second_away)}</td></tr>'
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
