"""Feature computation helpers."""

from __future__ import annotations

from soccer_prediction.features.context import build_matchup_context
from soccer_prediction.features.morale import morale_label, morale_signal, morale_signals
from soccer_prediction.features.rates import RateBook, compute_rates

__all__ = [
    "RateBook",
    "build_matchup_context",
    "compute_rates",
    "morale_label",
    "morale_signal",
    "morale_signals",
]
