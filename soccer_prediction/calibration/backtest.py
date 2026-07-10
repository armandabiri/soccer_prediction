"""Walk-forward backtesting."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from soccer_prediction.models import TeamMatchStats
from soccer_prediction.predictors import get_model

__all__ = ["BacktestPrediction", "BacktestResult", "CanonicalMatch", "canonical_matches", "walk_forward"]


@dataclass(frozen=True, slots=True)
class CanonicalMatch:
    """One real fixture in home/away orientation, deduplicated across team perspectives."""

    match_date: date
    home_team: str
    away_team: str
    home_score: int
    away_score: int


@dataclass(frozen=True, slots=True)
class BacktestPrediction:
    """One walk-forward prediction and realized outcome."""

    match_date: date
    home_team: str
    away_team: str
    probabilities: tuple[float, float, float]
    actual_index: int


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Walk-forward predictions plus model metadata."""

    model_name: str
    predictions: tuple[BacktestPrediction, ...]

    @property
    def count(self) -> int:
        """Return number of evaluated matches."""
        return len(self.predictions)


def walk_forward(
    history: Sequence[TeamMatchStats],
    model_name: str = "poisson",
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> BacktestResult:
    """Fit only on matches before each test date and predict home/draw/away."""
    matches = canonical_matches(history)
    predictions: list[BacktestPrediction] = []
    for match in matches:
        if from_date is not None and match.match_date < from_date:
            continue
        if to_date is not None and match.match_date > to_date:
            continue
        train = [record for record in history if record.date < match.match_date]
        if not train:
            continue
        assert max(record.date for record in train) < match.match_date
        model = get_model(model_name)
        model.fit(train, as_of=match.match_date)
        probabilities = model.predict_scoreline(match.home_team, match.away_team).home_draw_away()
        predictions.append(
            BacktestPrediction(
                match_date=match.match_date,
                home_team=match.home_team,
                away_team=match.away_team,
                probabilities=probabilities,
                actual_index=_actual_index(match.home_score, match.away_score),
            )
        )
    return BacktestResult(model_name=model_name, predictions=tuple(predictions))


def canonical_matches(history: Sequence[TeamMatchStats]) -> tuple[CanonicalMatch, ...]:
    """Return each fixture once, including sources that expose only an away-team perspective."""
    unique: dict[tuple[date, str, str], CanonicalMatch] = {}
    for record in history:
        if record.is_home:
            home, away = record.team, record.opponent
            home_score, away_score = record.goals_for, record.goals_against
        else:
            home, away = record.opponent, record.team
            home_score, away_score = record.goals_against, record.goals_for
        key = (record.date, home.casefold(), away.casefold())
        unique[key] = CanonicalMatch(record.date, home, away, home_score, away_score)
    return tuple(sorted(unique.values(), key=lambda item: (item.match_date, item.home_team, item.away_team)))


def _actual_index(home_score: int, away_score: int) -> int:
    if home_score > away_score:
        return 0
    if home_score == away_score:
        return 1
    return 2
