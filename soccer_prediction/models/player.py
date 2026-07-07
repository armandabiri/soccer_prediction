"""Player-level stats and goalscorer/assist market dataclasses."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "PlayerMarketPrediction",
    "PlayerStats",
    "ScorerPrediction",
    "example_usage",
    "main",
]


@dataclass(frozen=True, slots=True)
class PlayerStats:
    """Historical scoring involvement for one player."""

    name: str
    team: str
    position: str
    appearances: int
    goals: int
    assists: int


@dataclass(frozen=True, slots=True)
class PlayerMarketPrediction:
    """Per-player goal and assist market estimates for a fixture."""

    player: str
    team: str
    position: str
    expected_goals: float
    expected_assists: float
    anytime_scorer: float
    to_score_or_assist: float
    first_scorer: float


@dataclass(frozen=True, slots=True)
class ScorerPrediction:
    """Goalscorer and assist markets across both squads, ranked by likelihood."""

    players: tuple[PlayerMarketPrediction, ...] = ()


def example_usage() -> None:
    """Print a sample player record."""
    print(PlayerStats("Breel Embolo", "Switzerland", "FW", 70, 12, 8))


def main() -> None:
    """Module entry point."""
    example_usage()
