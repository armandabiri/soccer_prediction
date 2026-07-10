"""Shared style and supplementary sections for the HTML report."""

from __future__ import annotations

from html import escape

from soccer_prediction.models import MatchForecast

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
h3 { font-size:.92rem; margin:18px 0 8px; color:var(--muted); }
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
.formbar { position:relative; height:7px; min-width:120px; border-radius:6px; background:var(--bar); overflow:hidden; }
.formbar > span { position:absolute; inset:0 auto 0 0; border-radius:6px; }
.formlabel { display:block; margin-top:4px; color:var(--muted); font-size:.75rem; white-space:nowrap; }
.player-form-chart { display:grid; gap:7px; padding:10px 0 2px; }
.player-form-row { display:grid; grid-template-columns:minmax(135px,1.15fr) minmax(180px,3fr) 100px;
  gap:10px; align-items:center; }
.player-form-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.player-form-track { height:12px; border-radius:7px; background:var(--bar); overflow:hidden; }
.player-form-fill { height:100%; border-radius:7px; }
.player-form-value { text-align:right; color:var(--muted); font-size:.8rem; font-variant-numeric:tabular-nums; }
.ci-chart { display:grid; gap:12px; padding:12px 0 4px; }
.ci-row { display:grid; grid-template-columns:minmax(120px,1fr) minmax(220px,3fr) 145px; gap:12px; align-items:center; }
.ci-track { position:relative; height:14px; border-radius:8px; background:var(--bar); }
.ci-range { position:absolute; top:3px; height:8px; border-radius:5px; background:var(--accent2); opacity:.42; }
.ci-point { position:absolute; top:-3px; width:4px; height:14px; margin-left:-2px;
  border-radius:3px; background:var(--accent2); }
.ci-value { text-align:right; color:var(--muted); font-size:.82rem; font-variant-numeric:tabular-nums; }
@media (max-width:600px) { .player-form-row { grid-template-columns:minmax(105px,1fr) minmax(100px,2fr) 76px; } }
@media (max-width:600px) { .ci-row { grid-template-columns:90px minmax(100px,2fr) 112px; } }
.foot { color:var(--muted); font-size:.82rem; margin-top:24px; }
.pill { display:inline-block; background:var(--bar); border-radius:999px; padding:2px 10px; font-size:.8rem; }
.dot { display:inline-block; width:10px; height:10px; border-radius:3px; margin-right:7px;
  vertical-align:middle; border:1px solid rgba(128,128,128,.35); }
.legend { display:flex; flex-wrap:wrap; gap:16px; margin:-8px 0 18px; font-size:.85rem; }
.chip { display:inline-flex; align-items:center; }
"""

_FALLBACK_COLORS = ("#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed", "#0891b2", "#db2777", "#65a30d")
_TEAM_COLORS = {
    "switzerland": "#d52b1e", "colombia": "#fcd116", "brazil": "#009c3b", "argentina": "#6cabdd",
    "france": "#274796", "england": "#0a3d91", "germany": "#3a3a3a", "spain": "#c60b1e",
    "italy": "#1c6fb3", "portugal": "#006847", "netherlands": "#f36c21", "belgium": "#c8102e",
    "mexico": "#006341", "usa": "#1a3a6b", "united states": "#1a3a6b", "uruguay": "#5b9bd5",
    "croatia": "#b81b2c", "morocco": "#c1272d", "japan": "#1b2a6b", "canada": "#d80621",
}


def _team_color(team: str) -> str:
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


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _count(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _scorers_section(forecast: MatchForecast) -> str:
    scorers = forecast.scorers
    if scorers is None or not scorers.players:
        return ""
    chart_players = sorted(scorers.players, key=lambda item: item.recent_goals, reverse=True)
    maximum_goals = max((player.recent_goals for player in chart_players), default=1.0) or 1.0
    chart_rows: list[str] = []
    for player in chart_players:
        color = _team_color(player.team)
        width = min(100.0, player.recent_goals / maximum_goals * 100.0)
        marker = "*" if player.recent_form_estimated else ""
        sample = f"{player.recent_appearances} apps{marker}" if player.recent_appearances else "no sample"
        label = f"{_count(player.recent_goals)} goals / {sample}"
        chart_rows.append(
            f'<div class="player-form-row"><div class="player-form-name" title="{escape(player.player, quote=True)}">'
            f"{_dot(color)}{escape(player.player)}</div>"
            f'<div class="player-form-track" role="img" aria-label="{escape(label, quote=True)}">'
            f'<div class="player-form-fill" style="width:{width:.1f}%;background:{color}"></div></div>'
            f'<div class="player-form-value">{escape(label)}</div></div>'
        )
    chart = (
        f'<h3>Recent scoring comparison — all {len(chart_players)} listed players</h3><div class="card">'
        f'<div class="player-form-chart">{"".join(chart_rows)}</div>'
        f'<p class="foot">Each bar compares goals over the latest available sample of up to 20 appearances. '
        f"Bars are scaled to the leading player. * marks an aggregate-rate estimate.</p></div>"
    )
    rows: list[str] = []
    for player in scorers.players[:12]:
        color = _team_color(player.team)
        appearances = player.recent_appearances
        goal_rate = player.recent_goals / appearances if appearances else 0.0
        form_width = min(100.0, goal_rate * 100.0)
        estimate_marker = "*" if player.recent_form_estimated else ""
        form_label = (
            f"{_count(player.recent_goals)}G · {_count(player.recent_assists)}A / {appearances}{estimate_marker}"
            if appearances
            else "n/a"
        )
        rows.append(
            f'<tr style="background:{color}22"><td>{escape(player.player)}</td>'
            f"<td>{_dot(color)}{escape(player.team)}</td>"
            f'<td class="n">{escape(player.position)}</td>'
            f'<td><div class="formbar" title="Goals per appearance over the latest available sample">'
            f'<span style="width:{form_width:.1f}%;background:{color}"></span></div>'
            f'<span class="formlabel">{form_label}</span></td>'
            f'<td class="n">{_pct(player.score_probability)}</td>'
            f'<td class="n">{_pct(player.assist_probability)}</td>'
            f'<td class="n">{_pct(player.to_score_or_assist)}</td>'
            f'<td class="n">{_pct(player.first_scorer)}</td></tr>'
        )
    header = (
        '<thead><tr><th>Player</th><th>Team</th><th class="n">Pos</th><th>Recent scoring (max 20)</th>'
        '<th class="n">Score</th><th class="n">Assist</th><th class="n">Score/assist</th>'
        '<th class="n">First</th></tr></thead>'
    )
    return (
        f'<h2>Goalscorers &amp; assists</h2>{chart}<h3>Fixture probabilities</h3>'
        f'<div class="card"><div style="overflow-x:auto">'
        f'<table>{header}<tbody>{"".join(rows)}</tbody></table></div><p class="foot">'
        f"Score and Assist are separate anytime probabilities; Score/assist is either event; First is to open "
        f"the scoring. The bar is goals per appearance over up to 20 recent games. * means an up-to-20 equivalent "
        f"estimated from aggregate career totals because the source has no match-level recent form. Probabilities "
        f"use position-shrunk per-appearance rates and assume the player participates.</p></div>"
    )


def _history_section(forecast: MatchForecast) -> str:
    if not forecast.history:
        return (
            '<h2>Historical data used</h2><div class="card">'
            '<p class="sub">No historical data was available; model priors were used.</p></div>'
        )
    rows: list[str] = []
    displayed = sorted(forecast.history, key=lambda item: item.date, reverse=True)[:80]
    for record in displayed:
        venue = "H" if record.is_home else "A"
        color = _team_color(record.team)
        rows.append(
            f'<tr style="background:{color}22"><td>{_dot(color)}{escape(record.team)}</td>'
            f'<td class="n">{record.date.isoformat()}</td><td>{escape(record.opponent)}</td>'
            f'<td class="n">{venue}</td><td class="n">{record.goals_for}-{record.goals_against}</td>'
            f'<td class="n">{record.ht_goals_for}-{record.ht_goals_against}</td>'
            f'<td class="n">{record.corners_for}-{record.corners_against}</td>'
            f'<td class="n">{record.yellows}/{record.reds}</td></tr>'
        )
    header = (
        '<thead><tr><th>Team</th><th class="n">Date</th><th>Opponent</th><th class="n">H/A</th>'
        '<th class="n">Score</th><th class="n">HT</th><th class="n">Corners</th>'
        '<th class="n">Y/R</th></tr></thead>'
    )
    sources = ", ".join(sorted({record.source for record in forecast.history}))
    display_note = (
        f" Showing the newest {len(displayed)} records."
        if len(displayed) < len(forecast.history)
        else ""
    )
    return (
        f'<h2>Historical data used</h2><div class="card"><div style="overflow-x:auto"><table>{header}'
        f'<tbody>{"".join(rows)}</tbody></table></div><p class="foot">{len(forecast.history)} matches from: '
        f"{escape(sources)}. Score = full-time goals for-against; HT = half-time; Corners = for-against; "
        f"Y/R = yellow/red cards.{display_note}</p></div>"
    )
