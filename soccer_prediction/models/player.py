"""Player-level stats and goalscorer/assist market dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "PlayerGame",
    "PlayerMarketPrediction",
    "PlayerStats",
    "ScorerPrediction",
    "example_usage",
    "main",
]


@dataclass(frozen=True, slots=True)
class PlayerGame:
    """One recent match for a player: whether they featured and their involvements.

    ``played`` is ``False`` for a game the player missed entirely (injury,
    suspension, or left out of the squad); such a game contributes no goals or
    assists. Sequences of these are ordered oldest-to-newest, so the last
    entry is the most recent match and ``games[-5:]`` is the latest five.
    """

    played: bool
    goals: int = 0
    assists: int = 0

    def __post_init__(self) -> None:
        if self.goals < 0 or self.assists < 0:
            raise ValueError("player-game goals and assists cannot be negative")
        if not self.played and (self.goals or self.assists):
            raise ValueError("a game the player did not play cannot record goals or assists")

    @property
    def involvements(self) -> int:
        """Goal involvements (goals plus assists) recorded in this game."""
        return self.goals + self.assists


@dataclass(frozen=True, slots=True)
class PlayerStats:
    """Historical scoring involvement for one player.

    When ``recent_games`` is supplied and the aggregate ``recent_*`` fields are
    not, the aggregates are derived from the games the player actually featured
    in, so match-level form and the availability signal stay consistent.
    """

    name: str
    team: str
    position: str
    appearances: int
    goals: int
    assists: int
    recent_appearances: int | None = None
    recent_goals: int | None = None
    recent_assists: int | None = None
    recent_games: tuple[PlayerGame, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        values = (self.appearances, self.goals, self.assists)
        if any(value < 0 for value in values):
            raise ValueError("player appearances, goals, and assists cannot be negative")
        self._derive_recent_from_games()
        recent = (self.recent_appearances, self.recent_goals, self.recent_assists)
        if any(value is not None for value in recent) and not all(value is not None for value in recent):
            raise ValueError("recent player form requires appearances, goals, and assists together")
        if any(value is not None and value < 0 for value in recent):
            raise ValueError("recent player form cannot be negative")
        if self.recent_appearances is not None and self.recent_appearances > 20:
            raise ValueError("recent player form is limited to the latest 20 appearances")

    def _derive_recent_from_games(self) -> None:
        """Fill the aggregate recent_* fields from recent_games when not given."""
        if not self.recent_games or self.recent_appearances is not None:
            return
        played = [game for game in self.recent_games if game.played]
        object.__setattr__(self, "recent_appearances", len(played))
        object.__setattr__(self, "recent_goals", sum(game.goals for game in played))
        object.__setattr__(self, "recent_assists", sum(game.assists for game in played))

    def played_in_last(self, window: int) -> int:
        """Count games featured in over the most recent ``window`` matches."""
        if window <= 0 or not self.recent_games:
            return 0
        return sum(1 for game in self.recent_games[-window:] if game.played)


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
    recent_games: tuple[PlayerGame, ...] = field(default_factory=tuple)
    recent_availability: float = 1.0
    played_last_five: int = 0

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
