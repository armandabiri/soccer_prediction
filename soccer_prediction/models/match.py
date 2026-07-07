"""Match and history dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

__all__ = ["Fixture", "Match", "TeamMatchStats", "example_usage", "main"]


@dataclass(frozen=True, slots=True)
class TeamMatchStats:
    """Historical team-level statistics for one match."""

    team: str
    opponent: str
    date: date
    is_home: bool
    goals_for: int
    goals_against: int
    ht_goals_for: int
    ht_goals_against: int
    corners_for: int
    corners_against: int
    yellows: int
    reds: int
    source: str
    fetched_at: datetime


@dataclass(frozen=True, slots=True)
class Match:
    """Concrete match record with optional scoreline."""

    home_team: str
    away_team: str
    kickoff: datetime | None = None
    competition: str | None = None
    home_score: int | None = None
    away_score: int | None = None


@dataclass(frozen=True, slots=True)
class Fixture:
    """Future fixture metadata for forecasting."""

    home_team: str
    away_team: str
    kickoff: datetime | None = None
    competition: str | None = None
    venue: str | None = None
    round_name: str | None = None


def example_usage() -> None:
    """Print a compact sample record."""
    sample = Fixture(home_team="Brazil", away_team="Argentina")
    print(sample)


def main() -> None:
    """Module entry point."""
    example_usage()
