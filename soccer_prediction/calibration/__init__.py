"""Calibration, backtesting, and evaluation metrics."""

from __future__ import annotations

from soccer_prediction.calibration.backtest import BacktestPrediction, BacktestResult, walk_forward
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
    "MetricsReport",
    "brier_score",
    "calibration_curve",
    "log_loss",
    "metrics_report",
    "ranked_probability_score",
    "walk_forward",
]
