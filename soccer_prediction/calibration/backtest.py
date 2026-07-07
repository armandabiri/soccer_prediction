"""Walk-forward backtesting."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from soccer_prediction.models import TeamMatchStats
from soccer_prediction.predictors import get_model

__all__ = ["BacktestPrediction", "BacktestResult", "walk_forward"]


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
    matches = sorted((record for record in history if record.is_home), key=lambda record: record.date)
    predictions: list[BacktestPrediction] = []
    for match in matches:
        if from_date is not None and match.date < from_date:
            continue
        if to_date is not None and match.date > to_date:
            continue
        train = [record for record in history if record.date < match.date]
        if not train:
            continue
        assert max(record.date for record in train) < match.date
        model = get_model(model_name)
        model.fit(train)
        probabilities = model.predict_scoreline(match.team, match.opponent).home_draw_away()
        predictions.append(
            BacktestPrediction(
                match_date=match.date,
                home_team=match.team,
                away_team=match.opponent,
                probabilities=probabilities,
                actual_index=_actual_index(match),
            )
        )
    return BacktestResult(model_name=model_name, predictions=tuple(predictions))


def _actual_index(record: TeamMatchStats) -> int:
    if record.goals_for > record.goals_against:
        return 0
    if record.goals_for == record.goals_against:
        return 1
    return 2
