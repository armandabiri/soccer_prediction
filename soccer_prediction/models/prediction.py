"""Prediction dataclasses and scoreline helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from .match import Fixture, TeamMatchStats
from .player import ScorerPrediction

__all__ = [
    "CardsPrediction",
    "CornersPrediction",
    "KnockoutPrediction",
    "MarketPrediction",
    "MatchForecast",
    "MatchupContext",
    "ModelEstimate",
    "PerHalfPrediction",
    "ScorelineGrid",
    "ScenarioAnalysis",
    "TeamForm",
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
class KnockoutPrediction:
    """Extra-time and penalty-shootout outcomes for a knockout fixture."""

    goes_to_extra_time: float
    goes_to_penalties: float
    home_advance: float
    away_advance: float
    home_shootout_win: float
    away_shootout_win: float
    home_penalty_conversion: float = 0.75
    away_penalty_conversion: float = 0.75
    decided_in_normal_time: float = 0.0
    decided_in_extra_time: float = 0.0


@dataclass(frozen=True, slots=True)
class ModelEstimate:
    """Headline probabilities produced by one goal-model family."""

    model_name: str
    home_win: float
    draw: float
    away_win: float
    home_expected_goals: float
    away_expected_goals: float
    ensemble_weight: float = 0.0
    is_ensemble: bool = False
    description: str = ""
    over_2_5: float = 0.0
    btts_yes: float = 0.0
    most_likely_score: str = "0-0"
    most_likely_score_probability: float = 0.0
    home_win_interval: tuple[float, float] = (0.0, 1.0)
    draw_interval: tuple[float, float] = (0.0, 1.0)
    away_win_interval: tuple[float, float] = (0.0, 1.0)
    is_selected: bool = False
    role: str = "component"
    validation_log_loss: float | None = None
    validation_matches: int = 0


@dataclass(frozen=True, slots=True)
class ScenarioAnalysis:
    """Uncertainty diagnostics from latent match-scenario simulation."""

    simulations: int
    home_goals_interval: tuple[int, int]
    away_goals_interval: tuple[int, int]
    total_goals_interval: tuple[int, int]
    home_clean_sheet: float
    away_clean_sheet: float
    scoreless_draw: float
    five_plus_goals: float
    three_plus_goal_margin: float
    model_disagreement: float
    outcome_uncertainty: float
    agreement_label: str
    model_estimates: tuple[ModelEstimate, ...] = ()
    data_uncertainty: float = 1.0
    data_quality_label: str = "low"
    confidence_level: float = 0.80
    home_win_interval: tuple[float, float] = (0.0, 1.0)
    draw_interval: tuple[float, float] = (0.0, 1.0)
    away_win_interval: tuple[float, float] = (0.0, 1.0)
    conclusion_model_name: str = "ensemble"
    ensemble_weights: dict[str, float] = field(default_factory=dict)
    ensemble_validation_log_losses: dict[str, float] = field(default_factory=dict)
    ensemble_validation_matches: int = 0
    ensemble_validation_from: str | None = None
    ensemble_validation_to: str | None = None
    ensemble_weight_method: str = "static_prior"
    selected_model_name: str = "ensemble"
    interval_method: str = "effective-sample sensitivity range"


@dataclass(frozen=True, slots=True)
class TeamForm:
    """Recency-weighted form for one team."""

    team: str
    matches: int
    effective_matches: float
    points_per_match: float
    goals_for_per_match: float
    goals_against_per_match: float
    corners_for_per_match: float
    recent_results: tuple[str, ...] = ()
    morale_index: float = 0.0
    morale_label: str = "neutral"
    result_streak: int = 0


@dataclass(frozen=True, slots=True)
class MatchupContext:
    """Direct meetings, opponent-network connections, and inferred game style."""

    home_form: TeamForm
    away_form: TeamForm
    head_to_head_matches: int
    home_head_to_head_wins: int
    head_to_head_draws: int
    away_head_to_head_wins: int
    head_to_head_average_goals: float
    head_to_head_average_corners: float
    network_team_count: int
    network_match_count: int
    connection_paths: tuple[tuple[str, ...], ...]
    style_label: str
    style_description: str


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
    knockout: KnockoutPrediction | None = None
    scenario_analysis: ScenarioAnalysis | None = None
    matchup_context: MatchupContext | None = None


def example_usage() -> None:
    """Print a compact sample forecast shell."""
    grid = ScorelineGrid(home_goals_max=1, away_goals_max=1, probabilities=((0.4, 0.1), (0.2, 0.3)))
    print(grid.home_draw_away())


def main() -> None:
    """Module entry point."""
    example_usage()
