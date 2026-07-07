"""Validation for normalized match records."""

from __future__ import annotations

from soccer_prediction.models import TeamMatchStats

__all__ = ["validate_record"]


def validate_record(record: TeamMatchStats) -> list[str]:
    """Return validation errors for a team match record."""
    errors: list[str] = []
    if not record.team:
        errors.append("team is required")
    if not record.opponent:
        errors.append("opponent is required")
    numeric_fields = {
        "goals_for": record.goals_for,
        "goals_against": record.goals_against,
        "ht_goals_for": record.ht_goals_for,
        "ht_goals_against": record.ht_goals_against,
        "corners_for": record.corners_for,
        "corners_against": record.corners_against,
        "yellows": record.yellows,
        "reds": record.reds,
    }
    errors.extend(f"{name} must be non-negative" for name, value in numeric_fields.items() if value < 0)
    if record.ht_goals_for > record.goals_for:
        errors.append("half-time goals for cannot exceed full-time goals for")
    if record.ht_goals_against > record.goals_against:
        errors.append("half-time goals against cannot exceed full-time goals against")
    return errors
