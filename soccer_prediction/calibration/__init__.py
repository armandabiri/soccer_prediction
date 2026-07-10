"""Calibration, backtesting, and evaluation metrics."""

from __future__ import annotations

from soccer_prediction.calibration.backtest import (
    BacktestPrediction,
    BacktestResult,
    CanonicalMatch,
    canonical_matches,
    walk_forward,
)
from soccer_prediction.calibration.metrics import (
    MetricsReport,
    brier_score,
    calibration_curve,
    log_loss,
    metrics_report,
    ranked_probability_score,
)

__all__ = [
    "BacktestPrediction",
    "BacktestResult",
    "CanonicalMatch",
    "MetricsReport",
    "brier_score",
    "calibration_curve",
    "canonical_matches",
    "log_loss",
    "metrics_report",
    "ranked_probability_score",
    "walk_forward",
]
