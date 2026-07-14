"""Weighted opponent-dependency SVG for the HTML forecast report."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from html import escape
from math import cos, pi, sin

from soccer_prediction.config import load_config
from soccer_prediction.features.rates import RateBook, compute_rates
from soccer_prediction.models import MatchForecast, MatchupContext, TeamMatchStats

__all__ = ["matchup_network_section"]

_RECENT_LIMIT = 6
_MAX_BRIDGES = 6
_MAX_SATELLITES = 5


@dataclass(frozen=True, slots=True)
class _EdgeStats:
    """Recency-weighted link between one side and an opponent."""

    opponent: str
    meetings: int
    weight: float
    goals_for: float
    goals_against: float
    latest: date


def matchup_network_section(forecast: MatchForecast) -> str:
    """Latest-game strips plus a weighted opponent-dependency SVG."""
    home = forecast.fixture.home_team
    away = forecast.fixture.away_team
    home_recent = _recent_matches(forecast, home)
    away_recent = _recent_matches(forecast, away)
    rates = compute_rates(forecast.history)
    config = load_config().model
    timeline = (
        "<h3>Latest games &amp; opponent dependencies</h3>"
        '<div class="form-timeline">'
        f"{_form_lane(home, home_recent, 'var(--home)')}"
        f"{_form_lane(away, away_recent, 'var(--away)')}"
        "</div>"
    )
    params = (
        '<p class="net-params">Model inputs on this graph: '
        f"time decay xi={config.time_decay_xi:.4f}, "
        f"morale decay xi={config.morale_decay_xi:.4f}, "
        f"network depth={config.opponent_network_depth}, "
        f"max teams={config.opponent_network_max_teams}, "
        f"recency window={config.recency_window_days}d. "
        "Edge width proportional to sum(exp(-xi*age)) effective meetings. "
        "Node badges: Atk / Def weakness / morale / n_eff.</p>"
    )
    network = _dependency_svg(forecast, rates, home_recent, away_recent)
    legend = (
        '<div class="net-legend">'
        '<span><i class="nl win"></i> Win</span>'
        '<span><i class="nl draw"></i> Draw</span>'
        '<span><i class="nl loss"></i> Loss</span>'
        '<span><i class="nl path"></i> Shared bridge (thicker = heavier weight)</span>'
        '<span><i class="nl recent"></i> Recent opponent edge</span>'
        '<span><i class="nl h2h"></i> Direct H2H</span>'
        "</div>"
    )
    return f"{timeline}{params}{network}{legend}"


def _form_lane(team: str, matches: list[TeamMatchStats], color: str) -> str:
    chips = "".join(_form_chip(record) for record in matches) or (
        '<span class="fgame empty">No recent matches</span>'
    )
    return (
        f'<div class="form-lane">'
        f'<div class="form-lane-label"><span class="dot" style="background:{color}"></span>'
        f"{escape(team)}</div>"
        f'<div class="form-lane-games">{chips}</div></div>'
    )


def _form_chip(record: TeamMatchStats) -> str:
    if record.goals_for > record.goals_against:
        letter, kind = "W", "win"
    elif record.goals_for < record.goals_against:
        letter, kind = "L", "loss"
    else:
        letter, kind = "D", "draw"
    date_label = record.date.strftime("%b %d").replace(" 0", " ")
    venue = "vs" if record.is_home else "@"
    title = (
        f"{record.date.isoformat()}: {record.team} {record.goals_for}-{record.goals_against} "
        f"{venue} {record.opponent}"
    )
    return (
        f'<div class="fgame {kind}" title="{escape(title)}">'
        f'<span class="fgame-res">{letter}</span>'
        f'<span class="fgame-score">{record.goals_for}-{record.goals_against}</span>'
        f'<span class="fgame-opp">{escape(venue)} {escape(_short(record.opponent))}</span>'
        f'<span class="fgame-date">{escape(date_label)}</span></div>'
    )


def _dependency_svg(
    forecast: MatchForecast,
    rates: RateBook,
    home_recent: list[TeamMatchStats],
    away_recent: list[TeamMatchStats],
) -> str:
    home = forecast.fixture.home_team
    away = forecast.fixture.away_team
    context = forecast.matchup_context
    assert context is not None
    xi = load_config().model.time_decay_xi
    home_edges = _edge_stats(forecast.history, home, xi)
    away_edges = _edge_stats(forecast.history, away, xi)
    path_bridges = _bridge_teams(context.connection_paths, home, away)
    bridges = _ranked_bridges(home_edges, away_edges, path_bridges, home, away)
    bridge_keys = {name.casefold() for name in bridges}
    ends = {home.casefold(), away.casefold()}
    home_ops = [e for e in home_edges if e.opponent.casefold() not in ends | bridge_keys][:_MAX_SATELLITES]
    away_ops = [e for e in away_edges if e.opponent.casefold() not in ends | bridge_keys][:_MAX_SATELLITES]
    width, height = 900, 420
    home_xy, away_xy = (200.0, 210.0), (700.0, 210.0)
    bridge_xy = _spread_vertical(bridges, x=450.0, y0=55.0, y1=365.0)
    home_sat = _arc_positions([e.opponent for e in home_ops], cx=70.0, cy=210.0, radius=125.0, start=-0.95, end=0.95)
    away_sat = _arc_positions(
        [e.opponent for e in away_ops], cx=830.0, cy=210.0, radius=125.0, start=pi - 0.95, end=pi + 0.95
    )
    home_by_opp = {e.opponent.casefold(): e for e in home_edges}
    away_by_opp = {e.opponent.casefold(): e for e in away_edges}
    weights = [e.weight for e in home_ops + away_ops]
    for key in bridge_keys:
        if key in home_by_opp and key in away_by_opp:
            weights.append(home_by_opp[key].weight + away_by_opp[key].weight)
    max_w = max(weights) if weights else 1.0
    parts = [
        f'<svg class="net-graph" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Weighted opponent dependency network for {escape(home)} versus {escape(away)}">'
    ]
    for edge in home_ops:
        x, y = home_sat[edge.opponent]
        parts.append(_weighted_edge(x, y, *home_xy, edge.weight, max_w, "net-edge recent", _edge_label(edge)))
    for edge in away_ops:
        x, y = away_sat[edge.opponent]
        parts.append(_weighted_edge(x, y, *away_xy, edge.weight, max_w, "net-edge recent", _edge_label(edge)))
    if bridges:
        for name, (x, y) in bridge_xy.items():
            he = home_by_opp.get(name.casefold())
            ae = away_by_opp.get(name.casefold())
            parts.append(
                _weighted_edge(*home_xy, x, y, he.weight if he else 0.0, max_w, "net-edge path", _edge_label(he))
            )
            parts.append(
                _weighted_edge(x, y, *away_xy, ae.weight if ae else 0.0, max_w, "net-edge path", _edge_label(ae))
            )
    elif context.head_to_head_matches:
        h2h = home_by_opp.get(away.casefold()) or away_by_opp.get(home.casefold())
        parts.append(
            _weighted_edge(
                *home_xy, *away_xy, h2h.weight if h2h else 1.0, max_w, "net-edge path direct", _edge_label(h2h) or "H2H"
            )
        )
    else:
        parts.append(
            '<text x="450" y="28" text-anchor="middle" class="net-empty">'
            "No shared-opponent bridge within four links</text>"
        )
    if bridges and context.head_to_head_matches:
        h2h = home_by_opp.get(away.casefold()) or away_by_opp.get(home.casefold())
        parts.append(
            _weighted_edge(*home_xy, *away_xy, h2h.weight if h2h else 1.0, max_w, "net-edge h2h", _h2h_label(context, h2h))
        )
    recent_keys = {r.opponent.casefold() for r in home_recent} | {r.opponent.casefold() for r in away_recent}
    for edge in home_ops:
        x, y = home_sat[edge.opponent]
        parts.append(_sat_node(edge, x, y, side="home"))
    for edge in away_ops:
        x, y = away_sat[edge.opponent]
        parts.append(_sat_node(edge, x, y, side="away"))
    for name, (x, y) in bridge_xy.items():
        highlight = " recent-bridge" if name.casefold() in recent_keys else ""
        parts.append(
            _bridge_node(
                name, x, y, home_by_opp.get(name.casefold()), away_by_opp.get(name.casefold()), rates, highlight
            )
        )
    parts.append(_hub_node(home, *home_xy, rates, context.home_form.effective_matches, "home"))
    parts.append(_hub_node(away, *away_xy, rates, context.away_form.effective_matches, "away"))
    parts.append("</svg>")
    return "".join(parts)


def _hub_node(team: str, x: float, y: float, rates: RateBook, neff: float, side: str) -> str:
    atk = rates.attack_for(team)
    defence = rates.defence_weakness_for(team)
    morale = rates.morale_for(team)
    team_rates = rates.for_team(team)
    title = (
        f"{team}: attack {atk:.2f}, defence weakness {defence:.2f}, morale {morale:+.2f}, "
        f"n_eff {neff:.1f}, GF/GA {team_rates.goals_for:.2f}/{team_rates.goals_against:.2f}"
    )
    return (
        f'<g class="net-node {side}" transform="translate({x:.1f},{y:.1f})">'
        f"<title>{escape(title)}</title><circle r=\"34\"/>"
        f'<text class="net-hub-name" text-anchor="middle" y="-8">{escape(_short(team, 12))}</text>'
        f'<text class="net-hub-meta" text-anchor="middle" y="8">Atk {atk:.2f} Def {defence:.2f}</text>'
        f'<text class="net-hub-meta" text-anchor="middle" y="22">Mor {morale:+.2f} neff {neff:.1f}</text></g>'
    )


def _bridge_node(
    name: str,
    x: float,
    y: float,
    home_edge: _EdgeStats | None,
    away_edge: _EdgeStats | None,
    rates: RateBook,
    highlight: str,
) -> str:
    atk = rates.attack_for(name)
    defence = rates.defence_weakness_for(name)
    hw = home_edge.weight if home_edge else 0.0
    aw = away_edge.weight if away_edge else 0.0
    hm = home_edge.meetings if home_edge else 0
    am = away_edge.meetings if away_edge else 0
    title = (
        f"{name}: Atk {atk:.2f}, Def {defence:.2f}; "
        f"home-side w={hw:.2f} ({hm} mtgs), away-side w={aw:.2f} ({am} mtgs)"
    )
    return (
        f'<g class="net-node bridge{highlight}" transform="translate({x:.1f},{y:.1f})">'
        f"<title>{escape(title)}</title><circle r=\"26\"/>"
        f'<text class="net-bridge-name" text-anchor="middle" y="-6">{escape(_short(name, 10))}</text>'
        f'<text class="net-bridge-meta" text-anchor="middle" y="8">Sw {hw + aw:.2f}</text>'
        f'<text class="net-bridge-meta" text-anchor="middle" y="20">A{atk:.2f} D{defence:.2f}</text></g>'
    )


def _sat_node(edge: _EdgeStats, x: float, y: float, *, side: str) -> str:
    title = (
        f"{edge.opponent}: {edge.meetings} meetings, weight {edge.weight:.2f}, "
        f"GF/GA {edge.goals_for:.1f}/{edge.goals_against:.1f}, latest {edge.latest.isoformat()}"
    )
    return (
        f'<g class="net-node sat {side}-sat" transform="translate({x:.1f},{y:.1f})">'
        f"<title>{escape(title)}</title><circle r=\"20\"/>"
        f'<text class="net-sat-name" text-anchor="middle" y="-3">{escape(_short(edge.opponent, 8))}</text>'
        f'<text class="net-sat-meta" text-anchor="middle" y="10">w{edge.weight:.2f}</text></g>'
    )


def _weighted_edge(
    x1: float, y1: float, x2: float, y2: float, weight: float, max_w: float, cls: str, label: str
) -> str:
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    cx, cy = mx + (y1 - y2) * 0.08, my + (x2 - x1) * 0.08
    width = 1.0 + 4.5 * min(1.0, weight / max(max_w, 1e-6))
    path = (
        f'<path class="{cls}" d="M{x1:.1f},{y1:.1f} Q{cx:.1f},{cy:.1f} {x2:.1f},{y2:.1f}" '
        f'fill="none" stroke-width="{width:.2f}"/>'
    )
    if not label:
        return path
    lx, ly = (x1 + 2 * cx + x2) / 4, (y1 + 2 * cy + y2) / 4
    return (
        f'{path}<text class="net-edge-label" x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle">'
        f"{escape(label)}</text>"
    )


def _edge_label(edge: _EdgeStats | None) -> str:
    if edge is None:
        return ""
    gf = edge.goals_for / max(edge.meetings, 1)
    ga = edge.goals_against / max(edge.meetings, 1)
    return f"w{edge.weight:.2f} {edge.meetings}n {gf:.1f}-{ga:.1f}"


def _h2h_label(context: MatchupContext, edge: _EdgeStats | None) -> str:
    prefix = f"w{edge.weight:.2f} " if edge else ""
    return f"{prefix}H2H {context.head_to_head_matches} {context.head_to_head_average_goals:.1f}g"


def _edge_stats(history: tuple[TeamMatchStats, ...] | list[TeamMatchStats], team: str, xi: float) -> list[_EdgeStats]:
    rows = [record for record in history if record.team.casefold() == team.casefold()]
    return sorted(_edges_from_records(rows, xi), key=lambda edge: (-edge.weight, -edge.meetings))


def _edges_from_records(records: list[TeamMatchStats], xi: float) -> list[_EdgeStats]:
    if not records:
        return []
    anchor = max(record.date for record in records)
    buckets: dict[str, list[TeamMatchStats]] = defaultdict(list)
    labels: dict[str, str] = {}
    for record in records:
        key = record.opponent.casefold()
        buckets[key].append(record)
        labels[key] = record.opponent
    edges: list[_EdgeStats] = []
    for key, rows in buckets.items():
        weight = sum(math.exp(-max(xi, 0.0) * max((anchor - row.date).days, 0)) for row in rows)
        edges.append(
            _EdgeStats(
                opponent=labels[key],
                meetings=len(rows),
                weight=weight,
                goals_for=float(sum(row.goals_for for row in rows)),
                goals_against=float(sum(row.goals_against for row in rows)),
                latest=max(row.date for row in rows),
            )
        )
    return edges


def _ranked_bridges(
    home_edges: list[_EdgeStats],
    away_edges: list[_EdgeStats],
    path_bridges: list[str],
    home: str,
    away: str,
) -> list[str]:
    """Prefer shortest-path bridges, then fill with heaviest shared opponents."""
    ends = {home.casefold(), away.casefold()}
    home_w = {edge.opponent.casefold(): edge for edge in home_edges}
    away_w = {edge.opponent.casefold(): edge for edge in away_edges}
    shared = set(home_w) & set(away_w) - ends
    ordered: list[str] = []
    seen: set[str] = set()
    for name in path_bridges:
        key = name.casefold()
        if key in shared and key not in seen:
            seen.add(key)
            ordered.append(name)
    extras = sorted(shared - seen, key=lambda key: -(home_w[key].weight + away_w[key].weight))
    for key in extras:
        if len(ordered) >= _MAX_BRIDGES:
            break
        ordered.append(home_w[key].opponent)
    return ordered[:_MAX_BRIDGES]


def _bridge_teams(paths: tuple[tuple[str, ...], ...], home: str, away: str) -> list[str]:
    ends = {home.casefold(), away.casefold()}
    ordered: list[str] = []
    seen: set[str] = set()
    for path in paths:
        for team in path[1:-1]:
            key = team.casefold()
            if key in ends or key in seen:
                continue
            seen.add(key)
            ordered.append(team)
    return ordered


def _recent_matches(forecast: MatchForecast, team: str) -> list[TeamMatchStats]:
    return sorted(
        (record for record in forecast.history if record.team.casefold() == team.casefold()),
        key=lambda item: item.date,
        reverse=True,
    )[:_RECENT_LIMIT]


def _spread_vertical(names: list[str], *, x: float, y0: float, y1: float) -> dict[str, tuple[float, float]]:
    if not names:
        return {}
    if len(names) == 1:
        return {names[0]: (x, (y0 + y1) / 2)}
    step = (y1 - y0) / (len(names) - 1)
    return {name: (x, y0 + index * step) for index, name in enumerate(names)}


def _arc_positions(
    names: list[str], *, cx: float, cy: float, radius: float, start: float, end: float
) -> dict[str, tuple[float, float]]:
    if not names:
        return {}
    span, denom = end - start, max(len(names) - 1, 1)
    return {
        name: (cx + radius * cos(start + span * index / denom), cy + radius * sin(start + span * index / denom))
        for index, name in enumerate(names)
    }


def _short(name: str, limit: int = 10) -> str:
    text = name.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."
