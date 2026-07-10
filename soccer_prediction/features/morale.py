"""Short-lived team morale and momentum signals from recent results."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date

from soccer_prediction.models import TeamMatchStats

__all__ = ["morale_label", "morale_signal", "morale_signals"]


def morale_signals(
    history: Sequence[TeamMatchStats],
    decay_xi: float,
    *,
    anchor: date | None = None,
) -> dict[str, tuple[float, int]]:
    """Return a [-1, 1] morale proxy and signed current streak per team."""
    if not history:
        return {}
    reference = max(record.date for record in history) if anchor is None else anchor
    teams = {record.team.casefold() for record in history}
    return {
        team: morale_signal(history, team, decay_xi, anchor=reference)
        for team in teams
    }


def morale_signal(
    history: Sequence[TeamMatchStats],
    team: str,
    decay_xi: float,
    *,
    anchor: date | None = None,
) -> tuple[float, int]:
    """Summarize recent results, margins, and a consecutive win/loss streak."""
    records = sorted(
        (record for record in history if record.team.casefold() == team.casefold()),
        key=lambda item: item.date,
        reverse=True,
    )
    if not records:
        return 0.0, 0
    reference = records[0].date if anchor is None else anchor
    weighted_result = 0.0
    total_weight = 0.0
    for record in records:
        age_days = max((reference - record.date).days, 0)
        weight = math.exp(-max(decay_xi, 0.0) * age_days)
        margin = record.goals_for - record.goals_against
        if margin == 0:
            outcome = 0.0
        else:
            outcome = math.copysign(1.0 + 0.12 * (min(abs(margin), 3) - 1), margin)
        weighted_result += outcome * weight
        total_weight += weight
    base = weighted_result / max(total_weight, 1e-9) / 1.24
    streak = _current_streak(records)
    streak_component = math.copysign(min(abs(streak), 5) / 5.0, streak) if streak else 0.0
    score = 0.78 * base + 0.22 * streak_component
    return min(1.0, max(-1.0, score)), streak


def morale_label(score: float) -> str:
    """Convert a morale score into restrained user-facing language."""
    if score >= 0.45:
        return "very confident"
    if score >= 0.15:
        return "confident"
    if score <= -0.45:
        return "fragile"
    if score <= -0.15:
        return "low confidence"
    return "neutral"


def _current_streak(records: Sequence[TeamMatchStats]) -> int:
    first = _outcome_sign(records[0])
    if first == 0:
        return 0
    length = 0
    for record in records:
        if _outcome_sign(record) != first:
            break
        length += 1
    return length * first


def _outcome_sign(record: TeamMatchStats) -> int:
    if record.goals_for > record.goals_against:
        return 1
    if record.goals_for < record.goals_against:
        return -1
    return 0
