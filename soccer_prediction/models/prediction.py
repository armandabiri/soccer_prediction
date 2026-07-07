"""Prediction dataclasses and scoreline helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from .match import Fixture, TeamMatchStats
from .player import ScorerPrediction

__all__ = [
    "CardsPrediction",
    "CornersPrediction",
    "MarketPrediction",
    "MatchForecast",
    "PerHalfPrediction",
    "ScorelineGrid",
    "example_usage",
    "main",
]


def _sum_probability(items: Iterable[float]) -> float:
    return sum(items)


@dataclass(frozen=True, slots=True)
class ScorelineGrid:
    """A bounded grid of score probabilities."""

    home_goals_max: int
    away_goals_max: int
    probabilities: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        if len(self.probabilities) != self.home_goals_max + 1:
            raise ValueError("probabilities rows do not match home_goals_max")
        for row in self.probabilities:
            if len(row) != self.away_goals_max + 1:
                raise ValueError("probabilities columns do not match away_goals_max")

    def cell_probability(self, home_goals: int, away_goals: int) -> float:
        """Return one grid cell probability."""
        return self.probabilities[home_goals][away_goals]

    def total_probability(self) -> float:
        """Return the total probability mass in the grid."""
        return _sum_probability(value for row in self.probabilities for value in row)

    def home_draw_away(self) -> tuple[float, float, float]:
        """Return 1X2 probabilities as home, draw, away."""
        home = 0.0
        draw = 0.0
        away = 0.0
        for home_goals, row in enumerate(self.probabilities):
            for away_goals, probability in enumerate(row):
                if home_goals > away_goals:
                    home += probability
                elif home_goals == away_goals:
                    draw += probability
                else:
                    away += probability
        return home, draw, away

    def both_teams_to_score(self) -> float:
        """Return the BTTS probability."""
        blank_home = sum(row[0] for row in self.probabilities)
        blank_away = sum(self.probabilities[0])
        return 1.0 - blank_home - blank_away + self.probabilities[0][0]

    def over_under(self, line: float) -> tuple[float, float]:
        """Return under/over probabilities for the supplied goal line."""
        under = 0.0
        over = 0.0
        for home_goals, row in enumerate(self.probabilities):
            for away_goals, probability in enumerate(row):
                total_goals = home_goals + away_goals
                if total_goals <= line:
                    under += probability
                else:
                    over += probability
        return under, over


@dataclass(frozen=True, slots=True)
class MarketPrediction:
    """Single-market probability estimate."""

    market: str
    selection: str
    probability: float
    line: float | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class PerHalfPrediction:
    """Per-half score and result probabilities."""

    first_half_grid: ScorelineGrid
    second_half_grid: ScorelineGrid
    first_half_home_expected: float
    first_half_away_expected: float
    second_half_home_expected: float
    second_half_away_expected: float
    half_time_result: MarketPrediction | None = None
    second_half_result: MarketPrediction | None = None


@dataclass(frozen=True, slots=True)
class CornersPrediction:
    """Corners forecast summary."""

    home_expected: float
    away_expected: float
    total_expected: float
    total_over_lines: dict[float, float] = field(default_factory=dict)
    home_minimum: int = 0
    away_minimum: int = 0
    prob_at_least: dict[int, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CardsPrediction:
    """Cards forecast summary."""

    yellows_expected: float
    reds_expected: float
    total_expected: float
    over_under_lines: dict[float, float] = field(default_factory=dict)
    booking_points_expected: float | None = None


@dataclass(frozen=True, slots=True)
class MatchForecast:
    """Combined fixture forecast across the supported markets."""

    fixture: Fixture
    result: MarketPrediction
    correct_score: ScorelineGrid
    over_under: MarketPrediction
    btts: MarketPrediction
    per_half: PerHalfPrediction
    corners: CornersPrediction
    cards: CardsPrediction
    model_name: str
    generated_notes: tuple[str, ...] = ()
    history: tuple[TeamMatchStats, ...] = ()
    scorers: ScorerPrediction | None = None


def example_usage() -> None:
    """Print a compact sample forecast shell."""
    grid = ScorelineGrid(home_goals_max=1, away_goals_max=1, probabilities=((0.4, 0.1), (0.2, 0.3)))
    print(grid.home_draw_away())


def main() -> None:
    """Module entry point."""
    example_usage()
