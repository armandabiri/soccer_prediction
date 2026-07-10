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
    recent_appearances: int | None = None
    recent_goals: int | None = None
    recent_assists: int | None = None

    def __post_init__(self) -> None:
        values = (self.appearances, self.goals, self.assists)
        if any(value < 0 for value in values):
            raise ValueError("player appearances, goals, and assists cannot be negative")
        recent = (self.recent_appearances, self.recent_goals, self.recent_assists)
        if any(value is not None for value in recent) and not all(value is not None for value in recent):
            raise ValueError("recent player form requires appearances, goals, and assists together")
        if any(value is not None and value < 0 for value in recent):
            raise ValueError("recent player form cannot be negative")
        if self.recent_appearances is not None and self.recent_appearances > 20:
            raise ValueError("recent player form is limited to the latest 20 appearances")


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
    score_probability: float = 0.0
    assist_probability: float = 0.0
    recent_appearances: int = 0
    recent_goals: float = 0.0
    recent_assists: float = 0.0
    recent_form_estimated: bool = True

    def __post_init__(self) -> None:
        if self.score_probability == 0.0 and self.anytime_scorer > 0.0:
            object.__setattr__(self, "score_probability", self.anytime_scorer)


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
