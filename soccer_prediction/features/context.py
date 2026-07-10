"""Recent form, head-to-head, opponent-network, and game-style context."""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Sequence
from datetime import date

from soccer_prediction.config import load_config
from soccer_prediction.models import (
    CardsPrediction,
    CornersPrediction,
    MatchupContext,
    ScorelineGrid,
    TeamForm,
    TeamMatchStats,
)

__all__ = ["build_matchup_context"]


def build_matchup_context(
    history: Sequence[TeamMatchStats],
    home: str,
    away: str,
    grid: ScorelineGrid,
    corners: CornersPrediction,
    cards: CardsPrediction,
) -> MatchupContext:
    """Summarize the evidence that explains a fixture forecast."""
    home_form = _team_form(history, home)
    away_form = _team_form(history, away)
    h2h = _head_to_head(history, home, away)
    paths = _connection_paths(history, home, away)
    teams = {
        name.casefold()
        for record in history
        for name in (record.team, record.opponent)
    }
    matches = {
        (tuple(sorted((record.team.casefold(), record.opponent.casefold()))), record.date)
        for record in history
    }
    style_label, style_description = _game_style(grid, corners, cards)
    return MatchupContext(
        home_form=home_form,
        away_form=away_form,
        head_to_head_matches=h2h[0],
        home_head_to_head_wins=h2h[1],
        head_to_head_draws=h2h[2],
        away_head_to_head_wins=h2h[3],
        head_to_head_average_goals=h2h[4],
        head_to_head_average_corners=h2h[5],
        network_team_count=len(teams),
        network_match_count=len(matches),
        connection_paths=paths,
        style_label=style_label,
        style_description=style_description,
    )


def _team_form(history: Sequence[TeamMatchStats], team: str) -> TeamForm:
    records = sorted(
        (record for record in history if record.team.casefold() == team.casefold()),
        key=lambda item: item.date,
        reverse=True,
    )
    if not records:
        return TeamForm(team, 0, 0.0, 0.0, 0.0, 0.0, 0.0)
    xi = max(load_config().model.time_decay_xi, 0.0)
    today = date.today()
    weighted_points = 0.0
    weighted_goals_for = 0.0
    weighted_goals_against = 0.0
    weighted_corners = 0.0
    effective_matches = 0.0
    for record in records:
        weight = math.exp(-xi * max((today - record.date).days, 0))
        if record.goals_for > record.goals_against:
            points = 3.0
        elif record.goals_for == record.goals_against:
            points = 1.0
        else:
            points = 0.0
        effective_matches += weight
        weighted_points += points * weight
        weighted_goals_for += record.goals_for * weight
        weighted_goals_against += record.goals_against * weight
        weighted_corners += record.corners_for * weight
    denominator = max(effective_matches, 1e-9)
    recent_results = tuple(
        f"{_result_letter(record)} {record.goals_for}-{record.goals_against} vs {record.opponent}"
        for record in records[:5]
    )
    return TeamForm(
        team=team,
        matches=len(records),
        effective_matches=effective_matches,
        points_per_match=weighted_points / denominator,
        goals_for_per_match=weighted_goals_for / denominator,
        goals_against_per_match=weighted_goals_against / denominator,
        corners_for_per_match=weighted_corners / denominator,
        recent_results=recent_results,
    )


def _result_letter(record: TeamMatchStats) -> str:
    if record.goals_for > record.goals_against:
        return "W"
    if record.goals_for < record.goals_against:
        return "L"
    return "D"


def _head_to_head(
    history: Sequence[TeamMatchStats],
    home: str,
    away: str,
) -> tuple[int, int, int, int, float, float]:
    home_rows = [
        record
        for record in history
        if record.team.casefold() == home.casefold() and record.opponent.casefold() == away.casefold()
    ]
    perspective_home = True
    rows = home_rows
    if not rows:
        perspective_home = False
        rows = [
            record
            for record in history
            if record.team.casefold() == away.casefold() and record.opponent.casefold() == home.casefold()
        ]
    if not rows:
        return 0, 0, 0, 0, 0.0, 0.0
    home_wins = sum(
        (record.goals_for > record.goals_against) == perspective_home and record.goals_for != record.goals_against
        for record in rows
    )
    draws = sum(record.goals_for == record.goals_against for record in rows)
    away_wins = len(rows) - home_wins - draws
    xi = max(load_config().model.time_decay_xi, 0.0)
    anchor = date.today()
    weights = [math.exp(-xi * max((anchor - record.date).days, 0)) for record in rows]
    total_weight = max(sum(weights), 1e-9)
    average_goals = sum(
        weight * (record.goals_for + record.goals_against) for record, weight in zip(rows, weights, strict=True)
    ) / total_weight
    average_corners = sum(
        weight * (record.corners_for + record.corners_against) for record, weight in zip(rows, weights, strict=True)
    ) / total_weight
    return len(rows), home_wins, draws, away_wins, average_goals, average_corners


def _connection_paths(
    history: Sequence[TeamMatchStats],
    home: str,
    away: str,
    max_edges: int = 4,
) -> tuple[tuple[str, ...], ...]:
    adjacency: dict[str, set[str]] = {}
    labels: dict[str, str] = {home.casefold(): home, away.casefold(): away}
    for record in history:
        team = record.team.casefold()
        opponent = record.opponent.casefold()
        labels.setdefault(team, record.team)
        labels.setdefault(opponent, record.opponent)
        adjacency.setdefault(team, set()).add(opponent)
        adjacency.setdefault(opponent, set()).add(team)
    start, target = home.casefold(), away.casefold()
    queue: deque[tuple[str, ...]] = deque([(start,)])
    found: list[tuple[str, ...]] = []
    explored = 0
    while queue and len(found) < 3 and explored < 5_000:
        path = queue.popleft()
        explored += 1
        if len(path) - 1 >= max_edges:
            continue
        for neighbour in sorted(adjacency.get(path[-1], set())):
            if neighbour in path:
                continue
            candidate = (*path, neighbour)
            if neighbour == target:
                if len(candidate) > 2:
                    found.append(candidate)
                continue
            queue.append(candidate)
    return tuple(tuple(labels[name] for name in path) for path in found)


def _game_style(
    grid: ScorelineGrid,
    corners: CornersPrediction,
    cards: CardsPrediction,
) -> tuple[str, str]:
    expected_goals = sum(
        (home_goals + away_goals) * probability
        for home_goals, row in enumerate(grid.probabilities)
        for away_goals, probability in enumerate(row)
    )
    tempo = "cagey" if expected_goals < 2.2 else "open" if expected_goals > 3.0 else "balanced"
    if corners.total_expected > 11.0:
        width = "wide/high-corner"
    elif corners.total_expected < 8.5:
        width = "low-corner"
    else:
        width = "mixed-width"
    if cards.total_expected > 5.0:
        physicality = "physical"
    elif cards.total_expected < 3.0:
        physicality = "controlled"
    else:
        physicality = "competitive"
    label = f"{tempo}, {width}, {physicality}"
    description = (
        f"The score model implies {expected_goals:.2f} total goals; the corner model implies "
        f"{corners.total_expected:.2f} corners and the discipline model {cards.total_expected:.2f} cards."
    )
    return label, description
