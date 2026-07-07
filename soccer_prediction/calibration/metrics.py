"""Evaluation metrics for probabilistic forecasts."""

from __future__ import annotations

import math
from dataclasses import dataclass

from soccer_prediction.calibration.backtest import BacktestResult

__all__ = [
    "MetricsReport",
    "brier_score",
    "calibration_curve",
    "log_loss",
    "ranked_probability_score",
]


@dataclass(frozen=True, slots=True)
class MetricsReport:
    """Summary metrics for a backtest result."""

    rps: float
    log_loss: float
    brier: float
    count: int


def ranked_probability_score(probabilities: tuple[float, ...], actual_index: int) -> float:
    """Return ranked probability score for ordered outcomes."""
    _validate_probabilities(probabilities, actual_index)
    total = 0.0
    cumulative_prob = 0.0
    for index, probability in enumerate(probabilities[:-1]):
        cumulative_prob += probability
        cumulative_actual = 1.0 if actual_index <= index else 0.0
        total += (cumulative_prob - cumulative_actual) ** 2
    return total / (len(probabilities) - 1)


def log_loss(probabilities: tuple[float, ...], actual_index: int) -> float:
    """Return multiclass log loss for one prediction."""
    _validate_probabilities(probabilities, actual_index)
    return -math.log(max(probabilities[actual_index], 1e-15))


def brier_score(probabilities: tuple[float, ...], actual_index: int) -> float:
    """Return multiclass Brier score for one prediction."""
    _validate_probabilities(probabilities, actual_index)
    return sum(
        (probability - (1.0 if index == actual_index else 0.0)) ** 2 for index, probability in enumerate(probabilities)
    )


def metrics_report(result: BacktestResult) -> MetricsReport:
    """Aggregate metrics across a backtest result."""
    if not result.predictions:
        return MetricsReport(rps=0.0, log_loss=0.0, brier=0.0, count=0)
    count = len(result.predictions)
    return MetricsReport(
        rps=sum(ranked_probability_score(item.probabilities, item.actual_index) for item in result.predictions) / count,
        log_loss=sum(log_loss(item.probabilities, item.actual_index) for item in result.predictions) / count,
        brier=sum(brier_score(item.probabilities, item.actual_index) for item in result.predictions) / count,
        count=count,
    )


def calibration_curve(result: BacktestResult, bins: int = 10) -> tuple[tuple[float, float, int], ...]:
    """Return mean confidence, empirical accuracy, and count per bin."""
    if bins <= 0:
        raise ValueError("bins must be positive")
    bucket_values: list[list[tuple[float, float]]] = [[] for _ in range(bins)]
    for prediction in result.predictions:
        confidence = max(prediction.probabilities)
        predicted_index = prediction.probabilities.index(confidence)
        bucket_index = min(int(confidence * bins), bins - 1)
        bucket_values[bucket_index].append((confidence, 1.0 if predicted_index == prediction.actual_index else 0.0))
    curve: list[tuple[float, float, int]] = []
    for bucket in bucket_values:
        if not bucket:
            curve.append((0.0, 0.0, 0))
            continue
        curve.append(
            (
                sum(item[0] for item in bucket) / len(bucket),
                sum(item[1] for item in bucket) / len(bucket),
                len(bucket),
            )
        )
    return tuple(curve)


def _validate_probabilities(probabilities: tuple[float, ...], actual_index: int) -> None:
    if not probabilities:
        raise ValueError("probabilities cannot be empty")
    if actual_index < 0 or actual_index >= len(probabilities):
        raise ValueError("actual_index is out of range")
    if any(probability < 0.0 or probability > 1.0 for probability in probabilities):
        raise ValueError("probabilities must be between 0 and 1")
    if not math.isclose(sum(probabilities), 1.0, abs_tol=1e-6):
        raise ValueError("probabilities must sum to 1")
