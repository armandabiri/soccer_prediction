"""Shared style and supplementary sections for the HTML report."""

from __future__ import annotations

from html import escape

from soccer_prediction.models import MatchForecast, PlayerMarketPrediction

_CSS = """
:root { color-scheme: light dark; --bg:#f5f7f4; --card:#ffffff; --ink:#12160f; --muted:#586152;
  --line:#e4e8e0; --accent:#1a7f4b; --home:#2563eb; --away:#dc2626; --draw:#7c8595;
  --accent2:var(--home); --bar:#e0e5db; }
:root[data-theme="light"] { --bg:#f5f7f4; --card:#ffffff; --ink:#12160f; --muted:#586152;
  --line:#e4e8e0; --accent:#1a7f4b; --home:#2563eb; --away:#dc2626; --draw:#7c8595;
  --accent2:var(--home); --bar:#e0e5db; }
@media (prefers-color-scheme: dark) { :root { --bg:#0e120d; --card:#161b13; --ink:#e9ede4;
  --muted:#98a48c; --line:#242b1f; --accent:#3ddc84; --home:#60a5fa; --away:#f87171;
  --draw:#9ca3af; --accent2:var(--home); --bar:#28301f; } }
:root[data-theme="dark"] { --bg:#0e120d; --card:#161b13; --ink:#e9ede4; --muted:#98a48c;
  --line:#242b1f; --accent:#3ddc84; --home:#60a5fa; --away:#f87171; --draw:#9ca3af;
  --accent2:var(--home); --bar:#28301f; }
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
.tile .v .v-sub { font-size:.85rem; font-weight:600; color:var(--muted); }
.tile .v .runners { display:block; margin-top:3px; font-size:.72rem; font-weight:400; color:var(--muted);
  font-variant-numeric:tabular-nums; }
.prior-badge { font-size:.62rem; font-weight:600; text-transform:uppercase; letter-spacing:.04em;
  vertical-align:middle; color:var(--muted); background:var(--bar); border:1px solid var(--line);
  border-radius:999px; padding:2px 8px; }
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
.player-form-chart { display:grid; gap:7px; padding:10px 0 2px; overflow-x:auto; }
.player-form-row { display:grid;
  grid-template-columns:minmax(120px,1.1fr) auto minmax(120px,2.2fr) 92px;
  gap:10px; align-items:center; }
.player-form-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.player-form-track { height:12px; border-radius:7px; background:var(--bar); overflow:hidden; }
.player-form-fill { height:100%; border-radius:7px; }
.player-form-value { text-align:right; color:var(--muted); font-size:.8rem; font-variant-numeric:tabular-nums; }
.player-form-value .avail { display:block; font-size:.7rem; }
.player-form-value .avail.low { color:#d97706; font-weight:600; }
.form-dots { display:inline-flex; gap:3px; }
.gdot { display:inline-flex; align-items:center; justify-content:center; flex:0 0 auto;
  width:17px; height:17px; border-radius:50%; border:1.5px solid var(--line); color:transparent;
  font-size:.6rem; font-weight:700; font-variant-numeric:tabular-nums; }
.gdot.dnp { background:var(--muted); border-color:var(--muted); opacity:.45; }
.gdot.blank { background:transparent; }
.gdot.goal { background:var(--c); border-color:var(--c); color:#fff; }
.gdot.assist { background:color-mix(in srgb,var(--c) 25%,transparent); border-color:var(--c); color:var(--ink); }
.dot-legend { display:flex; flex-wrap:wrap; gap:14px; align-items:center; margin:2px 0 0;
  color:var(--muted); font-size:.75rem; }
.dot-legend .gdot { color:inherit; }
.dot-legend span { display:inline-flex; align-items:center; gap:5px; }
.ci-chart { display:grid; gap:12px; padding:12px 0 4px; }
.ci-row { display:grid; grid-template-columns:minmax(120px,1fr) minmax(220px,3fr) 145px; gap:12px; align-items:center; }
.ci-track { position:relative; height:14px; border-radius:8px; background:var(--bar); }
.ci-range { position:absolute; top:3px; height:8px; border-radius:5px; background:var(--accent2); opacity:.42; }
.ci-point { position:absolute; top:-3px; width:4px; height:14px; margin-left:-2px;
  border-radius:3px; background:var(--accent2); }
.ci-row[data-outcome="home"] .ci-range,.ci-row[data-outcome="home"] .ci-point { background:var(--home); }
.ci-row[data-outcome="draw"] .ci-range,.ci-row[data-outcome="draw"] .ci-point { background:var(--draw); }
.ci-row[data-outcome="away"] .ci-range,.ci-row[data-outcome="away"] .ci-point { background:var(--away); }
.ci-value { text-align:right; color:var(--muted); font-size:.82rem; font-variant-numeric:tabular-nums; }
.model-card { padding-top:14px; }
.conclusion-line { margin:0 0 16px; padding:10px 12px; border-left:4px solid var(--accent); background:var(--bar); }
.model-chart { display:grid; gap:9px; }
.model-row { display:grid; grid-template-columns:180px minmax(260px,1fr); gap:10px; align-items:center; }
.model-label { font-size:.83rem; }
.model-badge { display:inline-block; margin-left:5px; padding:1px 5px; border-radius:8px; background:var(--bar);
  color:var(--muted); font-size:.65rem; text-transform:uppercase; }
.model-badge.conclusion { background:var(--accent); color:white; }
.stacked { display:flex; height:25px; overflow:hidden; border-radius:7px; background:var(--bar); }
.seg { display:flex; align-items:center; justify-content:center; min-width:25px; color:white; font-size:.68rem;
  font-variant-numeric:tabular-nums; overflow:hidden; }
.seg.home { background:var(--home); } .seg.draw { background:var(--draw); } .seg.away { background:var(--away); }
.stack-legend { display:flex; justify-content:flex-end; gap:16px; color:var(--muted); font-size:.75rem; }
.stack-legend span:nth-child(1) { color:var(--home); } .stack-legend span:nth-child(2) { color:var(--draw); }
.stack-legend span:nth-child(3) { color:var(--away); }
.forest-grid { display:grid; grid-template-columns:repeat(3,minmax(235px,1fr)); gap:12px; overflow-x:auto; }
.forest-panel { min-width:235px; border:1px solid var(--line); border-radius:10px; padding:4px 9px 10px; }
.forest-panel h4 { margin:5px 0 8px; font-size:.78rem; color:var(--muted); }
.forest-row { display:grid; grid-template-columns:82px 1fr 30px; gap:6px; align-items:center;
  margin:6px 0; font-size:.68rem; }
.forest-track { position:relative; height:10px; border-radius:5px; background:var(--bar); }
.forest-track i { position:absolute; top:3px; height:4px; border-radius:3px; background:var(--accent2); opacity:.45; }
.forest-track b { position:absolute; top:0; width:3px; height:10px; margin-left:-1px; background:var(--accent2); }
.forest-panel.home .forest-track i,.forest-panel.home .forest-track b { background:var(--home); }
.forest-panel.draw .forest-track i,.forest-panel.draw .forest-track b { background:var(--draw); }
.forest-panel.away .forest-track i,.forest-panel.away .forest-track b { background:var(--away); }
.forest-row small { text-align:right; color:var(--muted); }
.market-head,.market-row { display:grid; grid-template-columns:150px minmax(100px,1fr) 34px minmax(100px,1fr) 34px;
  gap:7px; align-items:center; }
.market-head { color:var(--muted); font-size:.72rem; margin-bottom:4px; }
.market-row { margin:6px 0; font-size:.76rem; }
.mini-track,.tail-track { display:block; height:8px; overflow:hidden; border-radius:5px; background:var(--bar); }
.mini-track i,.tail-track i { display:block; height:100%; background:var(--accent2); }
.mini-track.btts i { background:var(--accent); }
.tail-row.home .tail-track i { background:var(--home); }
.tail-row.draw .tail-track i { background:var(--draw); }
.tail-row.away .tail-track i { background:var(--away); }
.market-row small,.tail-row small { text-align:right; color:var(--muted); font-variant-numeric:tabular-nums; }
.table-scroll { overflow-x:auto; }
.table-scroll table { min-width:880px; }
.tail-chart { display:grid; gap:7px; margin:8px 0 16px; }
.tail-row { display:grid; grid-template-columns:150px minmax(180px,1fr) 50px; gap:8px;
  align-items:center; font-size:.78rem; }
.heatmap { display:grid; grid-template-columns:45px repeat(6,minmax(50px,1fr)); gap:3px; max-width:610px; }
.heat { min-height:46px; display:flex; align-items:center; justify-content:center; border-radius:4px; color:var(--ink);
  font-size:.72rem; font-variant-numeric:tabular-nums; }
.heat.home { background:color-mix(in srgb,var(--home) var(--strength),var(--card)); }
.heat.away { background:color-mix(in srgb,var(--away) var(--strength),var(--card)); }
.heat.draw { background:color-mix(in srgb,var(--draw) var(--strength),var(--card)); }
.heat.strong { color:white; text-shadow:0 1px 1px rgba(0,0,0,.35); }
.heat.axis { min-height:28px; color:var(--muted); background:transparent; font-weight:600; }
.heat.blank { min-height:28px; background:transparent; }
.heat-legend { max-width:610px; margin:12px 0 4px; }
.heat-gradient { height:10px; border-radius:6px;
  background:linear-gradient(90deg,var(--away),var(--draw),var(--home)); }
.heat-labels { display:flex; justify-content:space-between; color:var(--muted); font-size:.72rem; margin-top:3px; }
@media (max-width:600px) {
  .player-form-row { grid-template-columns:minmax(96px,1fr) auto minmax(70px,1.4fr) 66px; }
  .gdot { width:14px; height:14px; font-size:.5rem; border-width:1px; } }
@media (max-width:600px) { .ci-row { grid-template-columns:90px minmax(100px,2fr) 112px; } }
@media (max-width:600px) { .model-row { grid-template-columns:105px minmax(210px,1fr); }
  .model-chart { overflow-x:auto; }
  .market-head,.market-row { grid-template-columns:105px minmax(90px,1fr) 32px minmax(90px,1fr) 32px; }
  .heatmap { grid-template-columns:38px repeat(6,minmax(43px,1fr)); overflow-x:auto; } }
.foot { color:var(--muted); font-size:.82rem; margin-top:24px; }
.pill { display:inline-block; background:var(--bar); border-radius:999px; padding:2px 10px; font-size:.8rem; }
.dot { display:inline-block; width:10px; height:10px; border-radius:3px; margin-right:7px;
  vertical-align:middle; border:1px solid rgba(128,128,128,.35); }
.legend { display:flex; flex-wrap:wrap; gap:16px; margin:-8px 0 18px; font-size:.85rem; }
.chip { display:inline-flex; align-items:center; }
.settle-note { margin:2px 0 12px; padding:9px 12px; border-left:4px solid var(--accent); background:var(--bar);
  border-radius:0 8px 8px 0; font-size:.86rem; }
:root { --profit:#1a7f4b; --loss:#b91c1c; }
:root[data-theme="dark"] { --profit:#3ddc84; --loss:#f87171; }
@media (prefers-color-scheme: dark) { :root { --profit:#3ddc84; --loss:#f87171; } }
.edge-chart { display:grid; gap:9px; padding:10px 0 4px; }
.edge-row { display:grid; grid-template-columns:minmax(150px,1.3fr) minmax(160px,2.4fr) 92px; gap:10px;
  align-items:center; }
.edge-name { font-size:.82rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.edge-name .tag { display:inline-block; margin-left:6px; padding:1px 6px; border-radius:8px; font-size:.62rem;
  font-weight:600; text-transform:uppercase; letter-spacing:.03em; background:var(--bar); color:var(--muted); }
.edge-name .tag.buy { background:color-mix(in srgb,var(--profit) 20%,transparent); color:var(--profit); }
.edge-track { position:relative; height:14px; border-radius:7px; background:var(--bar); }
.edge-track .zero { position:absolute; top:-2px; bottom:-2px; width:1px; background:var(--line); }
.edge-track .fill { position:absolute; top:1px; bottom:1px; border-radius:5px; }
.edge-value { text-align:right; font-size:.78rem; color:var(--muted); font-variant-numeric:tabular-nums; }
.edge-value b { display:block; color:var(--ink); font-size:.85rem; }
.edge-value .pctv { display:block; color:var(--ink); font-weight:700; font-size:.82rem; }
.edge-value .sub3 { display:block; color:var(--muted); font-size:.68rem; }
.split-bar { display:flex; gap:2px; height:20px; border-radius:7px; overflow:hidden; background:var(--bar);
  margin:2px 0 4px; }
.split-bar span { display:flex; align-items:center; justify-content:center; font-size:.66rem; font-weight:600;
  font-variant-numeric:tabular-nums; overflow:hidden; white-space:nowrap; }
.split-bar .dep { background:var(--accent); color:#fff; }
.split-bar .csh { background:var(--bar); color:var(--muted); }
.ladder-cost { margin:-4px 0 8px; font-size:.7rem; color:var(--muted); font-variant-numeric:tabular-nums; }
.details-toggle { margin:10px 0 2px; }
.details-toggle summary { cursor:pointer; color:var(--muted); font-size:.8rem; padding:4px 0; }
.details-toggle summary:hover { color:var(--ink); }
.ladder-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:12px; padding:6px 0; }
.ladder-card { border:1px solid var(--line); border-radius:12px; padding:10px 12px 12px; background:var(--card); }
.ladder-card.inactive { opacity:.55; }
.ladder-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:8px; }
.ladder-score { font-weight:700; font-size:.95rem; font-variant-numeric:tabular-nums; }
.ladder-badge { font-size:.62rem; font-weight:600; text-transform:uppercase; letter-spacing:.03em;
  padding:2px 7px; border-radius:999px; background:var(--bar); color:var(--muted); }
.ladder-badge.active { background:color-mix(in srgb,var(--profit) 22%,transparent); color:var(--profit); }
.ladder-steps { display:grid; gap:7px; }
.ladder-step { display:grid; grid-template-columns:54px 1fr 66px; gap:7px; align-items:center; font-size:.72rem; }
.ladder-step .lbl { color:var(--muted); }
.ladder-step .track { position:relative; height:10px; border-radius:5px; background:var(--bar); overflow:hidden; }
.ladder-step .track b { position:absolute; left:0; top:0; bottom:0; border-radius:5px;
  background:color-mix(in srgb,var(--profit) 45%,transparent); }
.ladder-step.now .track b { background:var(--profit); }
.ladder-step .amt { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; line-height:1.15; }
.ladder-step .amt .pctv { font-weight:700; font-size:.82rem; }
.ladder-step .amt .sub3 { display:block; color:var(--muted); font-size:.64rem; font-weight:400; }
.ladder-step.now .amt .pctv { color:var(--profit); }
.ladder-foot { margin:8px 0 0; font-size:.7rem; color:var(--muted); }
.wf-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:14px; padding:8px 0 2px; }
.wf-card { border:1px solid var(--line); border-radius:12px; padding:12px 14px 13px; background:var(--card); }
.wf-head { display:flex; align-items:baseline; justify-content:space-between; margin-bottom:12px; }
.wf-score { font-weight:700; font-size:1.15rem; font-variant-numeric:tabular-nums; }
.wf-sub { color:var(--muted); font-size:.74rem; }
.wf-bar { position:relative; display:flex; gap:2px; height:30px; border-radius:8px; background:var(--bar);
  overflow:hidden; }
.wf-seg { position:relative; display:flex; align-items:center; justify-content:center; min-width:2px;
  overflow:hidden; }
.wf-seg.stake { background:color-mix(in srgb,var(--profit) 35%,var(--card)); }
.wf-seg.profit { background:var(--profit); }
.wf-seglab { font-size:.66rem; font-weight:600; color:var(--ink); white-space:nowrap; opacity:.85; }
.wf-seg.profit .wf-seglab { color:#fff; }
.wf-breakeven { position:absolute; top:-3px; bottom:-3px; width:2px; background:var(--ink); z-index:3; }
.wf-scale { display:flex; justify-content:space-between; gap:8px; margin-top:9px; color:var(--muted);
  font-size:.66rem; font-variant-numeric:tabular-nums; }
.wf-scale span:nth-child(2) { text-align:center; }
.wf-result { margin-top:10px; padding-top:9px; border-top:1px solid var(--line); font-size:.78rem;
  color:var(--muted); }
.wf-result strong { font-size:.95rem; }
.wf-result.profit strong { color:var(--profit); }
.wf-result.loss strong { color:var(--loss); }
.wf-belegend { background:var(--ink) !important; border-radius:1px !important; width:3px !important; }
.ptree { display:flex; flex-direction:column; align-items:center; gap:0; padding:14px 0 4px; overflow-x:auto; }
.ptree-root { display:inline-flex; flex-direction:column; align-items:center; }
.ptree-node { min-width:108px; border:1px solid var(--line); border-radius:10px; padding:7px 10px;
  text-align:center; background:var(--card); position:relative; }
.ptree-node .sc { font-weight:700; font-variant-numeric:tabular-nums; font-size:.86rem; }
.ptree-node .pl { font-size:.72rem; font-variant-numeric:tabular-nums; margin-top:2px; color:var(--muted); }
.ptree-node.profit .pl { color:var(--profit); font-weight:700; }
.ptree-node.loss .pl { color:var(--loss); font-weight:700; }
.ptree-node .marks { display:flex; gap:3px; justify-content:center; margin-top:4px; }
.ptree-node .marks span { width:6px; height:6px; border-radius:50%; background:var(--bar);
  border:1px solid var(--line); }
.ptree-node .marks span.hit { background:var(--accent); border-color:var(--accent); }
.ptree-stem { width:2px; height:16px; background:var(--line); }
.ptree-branches { display:flex; gap:18px; align-items:flex-start; }
.ptree-branch { display:flex; flex-direction:column; align-items:center; }
.ptree-branch-label { font-size:.66rem; color:var(--muted); text-transform:uppercase; letter-spacing:.03em;
  margin-bottom:2px; }
.ptree-legend { display:flex; flex-wrap:wrap; gap:14px; align-items:center; margin:4px 0 0; color:var(--muted);
  font-size:.72rem; }
.ptree-legend .sw { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:5px;
  vertical-align:middle; }
.plan-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:12px; padding:6px 0; }
.plan-card { border:1px solid var(--line); border-radius:12px; padding:12px 14px 14px; background:var(--card); }
.plan-card h4 { margin:0 0 2px; font-size:.92rem; text-transform:capitalize; }
.plan-card .sub2 { color:var(--muted); font-size:.75rem; margin:0 0 10px; }
.plan-bar { display:flex; gap:2px; height:22px; border-radius:7px; overflow:hidden; background:var(--bar);
  margin-bottom:8px; }
.plan-bar span { display:flex; align-items:center; justify-content:center; color:#fff; font-size:.62rem;
  font-variant-numeric:tabular-nums; overflow:hidden; white-space:nowrap; }
.plan-bar .cash { background:var(--bar); color:var(--muted); }
.plan-stats { display:grid; grid-template-columns:1fr 1fr; gap:5px 10px; font-size:.75rem; color:var(--muted);
  margin-bottom:8px; }
.plan-stats b { display:block; color:var(--ink); font-size:.86rem; font-variant-numeric:tabular-nums; }
.plan-positions { list-style:none; margin:0; padding:8px 0 0; border-top:1px solid var(--line); font-size:.76rem; }
.plan-positions li { display:flex; justify-content:space-between; gap:8px; padding:3px 0; }
.plan-positions li .nm { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--ink); }
.plan-positions li .amt { color:var(--muted); font-variant-numeric:tabular-nums; white-space:nowrap; }
@media (max-width:600px) {
  .edge-row { grid-template-columns:1fr; }
  .edge-value { text-align:left; }
  .ptree-branches { gap:10px; } }
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


def _fixture_color(forecast: MatchForecast, team: str) -> str:
    """Use semantic blue/red colors for the two forecast teams."""
    if team.casefold() == forecast.fixture.home_team.casefold():
        return "var(--home)"
    if team.casefold() == forecast.fixture.away_team.casefold():
        return "var(--away)"
    return _team_color(team)


def _dot(color: str) -> str:
    return f'<span class="dot" style="background:{color}"></span>'


def _team_legend(home: str, away: str) -> str:
    chips = (
        f'<span class="chip">{_dot("var(--home)")}{escape(home)} (home)</span>'
        f'<span class="chip">{_dot("var(--away)")}{escape(away)} (away)</span>'
    )
    return f'<p class="legend">{chips}</p>'


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _count(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _form_dots(player: PlayerMarketPrediction, color: str) -> str:
    """Ten circles, one per recent game (oldest first): solid grey means the
    player did not feature; a filled colour circle shows goals+assists that game."""
    cells: list[str] = []
    for game in player.recent_games:
        if not game.played:
            cells.append('<span class="gdot dnp" title="Did not play"></span>')
            continue
        involvements = game.goals + game.assists
        if involvements == 0:
            cells.append('<span class="gdot blank" title="Played — no goal or assist"></span>')
            continue
        kind = "goal" if game.goals else "assist"
        title = f"{game.goals}G · {game.assists}A"
        cells.append(f'<span class="gdot {kind}" style="--c:{color}" title="{title}">{involvements}</span>')
    if not cells:
        return '<div class="form-dots"></div>'
    aria = f"Last {len(player.recent_games)} games oldest to newest; played {player.played_last_five} of the last 5"
    return f'<div class="form-dots" role="img" aria-label="{escape(aria, quote=True)}">{"".join(cells)}</div>'


def _availability_note(player: PlayerMarketPrediction) -> str:
    """A "played N/5 recent" tag, highlighted when the player is barely featuring."""
    if not player.recent_games:
        return ""
    played = player.played_last_five
    cls = " low" if played <= 2 else ""
    return f'<span class="avail{cls}">played {played}/5 recent</span>'


def _scorers_section(forecast: MatchForecast) -> str:
    scorers = forecast.scorers
    if scorers is None or not scorers.players:
        return ""
    chart_players = sorted(scorers.players, key=lambda item: item.recent_goals, reverse=True)
    maximum_goals = max((player.recent_goals for player in chart_players), default=1.0) or 1.0
    chart_rows: list[str] = []
    for player in chart_players:
        color = _fixture_color(forecast, player.team)
        width = min(100.0, player.recent_goals / maximum_goals * 100.0)
        marker = "*" if player.recent_form_estimated else ""
        sample = f"{player.recent_appearances} apps{marker}" if player.recent_appearances else "no sample"
        label = f"{_count(player.recent_goals)} goals / {sample}"
        chart_rows.append(
            f'<div class="player-form-row"><div class="player-form-name" title="{escape(player.player, quote=True)}">'
            f"{_dot(color)}{escape(player.player)}</div>"
            f"{_form_dots(player, color)}"
            f'<div class="player-form-track" role="img" aria-label="{escape(label, quote=True)}">'
            f'<div class="player-form-fill" style="width:{width:.1f}%;background:{color}"></div></div>'
            f'<div class="player-form-value">{escape(label)}{_availability_note(player)}</div></div>'
        )
    dot_legend = (
        '<div class="dot-legend">'
        '<span><span class="gdot goal" style="--c:var(--accent)"></span>goal</span>'
        '<span><span class="gdot assist" style="--c:var(--accent)"></span>assist only</span>'
        '<span><span class="gdot blank"></span>played, blank</span>'
        '<span><span class="gdot dnp"></span>did not play</span>'
        "</div>"
    )
    chart = (
        f'<h3>Recent scoring comparison — all {len(chart_players)} listed players</h3><div class="card">'
        f'<div class="player-form-chart">{"".join(chart_rows)}</div>{dot_legend}'
        f'<p class="foot">The ten circles left of each bar are that player’s last ten games, oldest first; '
        f"the number is goals+assists that game and a solid grey circle marks a game they did not play. "
        f'Bars compare goals over the latest available sample of up to 20 appearances, scaled to the leader. '
        f"A thin recent presence (see “played N/5”) damps the player’s predicted markets below; "
        f"* marks an aggregate-rate estimate.</p></div>"
    )
    rows: list[str] = []
    for player in scorers.players[:12]:
        color = _fixture_color(forecast, player.team)
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
            f'<tr style="background:color-mix(in srgb,{color} 14%,transparent)"><td>{escape(player.player)}</td>'
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
        f"use position-shrunk per-appearance rates, then weight each player by how many of the last five games "
        f"they featured in, so someone absent from recent squads is damped and cedes share to teammates who "
        f"are playing.</p></div>"
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
        color = _fixture_color(forecast, record.team)
        rows.append(
            f'<tr style="background:color-mix(in srgb,{color} 14%,transparent)">'
            f'<td>{_dot(color)}{escape(record.team)}</td>'
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
