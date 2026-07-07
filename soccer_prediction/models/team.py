"""Team and team-rate dataclasses."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Team", "TeamRates", "example_usage", "main"]


@dataclass(frozen=True, slots=True)
class Team:
    """Team identity and optional metadata."""

    name: str
    country_code: str | None = None
    confederation: str | None = None


@dataclass(frozen=True, slots=True)
class TeamRates:
    """Aggregate rate estimates used by the prediction models."""

    goals_for: float
    goals_against: float
    ht_goals_for: float
    ht_goals_against: float
    corners_for: float
    corners_against: float
    yellows: float
    reds: float
    sample_size: int = 0


def example_usage() -> None:
    """Print a compact sample team."""
    print(Team(name="Brazil"))


def main() -> None:
    """Module entry point."""
    example_usage()
