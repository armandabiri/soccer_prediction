"""Smoke tests for the scaffolded package."""

from __future__ import annotations

import math

import soccer_prediction
from soccer_prediction.calibration import metrics_report, ranked_probability_score, walk_forward
from soccer_prediction.models import TeamMatchStats
from soccer_prediction.predictors import get_model


def test_import_and_example_usage() -> None:
    soccer_prediction.example_usage()


def test_predictor_and_backtest_smoke(sample_history: list[TeamMatchStats]) -> None:
    model = get_model("dixon_coles")
    model.fit(sample_history)
    grid = model.predict_scoreline("Brazil", "Argentina")
    assert round(grid.total_probability(), 6) == 1.0

    result = walk_forward(sample_history, "poisson")
    report = metrics_report(result)
    assert report.count == result.count
    assert math.isclose(ranked_probability_score((0.2, 0.5, 0.3), 1), 0.065)
