"""Runnable, offline worked examples for soccer_prediction.

Importing this package registers the bundled offline data sources
(``bundled_wc2026`` and ``bundled_swi_col``) used by the examples.
"""

from __future__ import annotations

from soccer_prediction.example.switzerland_colombia_example import (
    build_forecast,
    write_reports,
)
from soccer_prediction.example.switzerland_colombia_example import (
    run_example as run_switzerland_colombia,
)
from soccer_prediction.example.wc2026_example import BundledWorldCupSource, load_sample_history, run_example
from soccer_prediction.example.worldcup2026_live import forecast_wc2026, write_wc2026_report

__all__ = [
    "BundledWorldCupSource",
    "build_forecast",
    "forecast_wc2026",
    "load_sample_history",
    "run_example",
    "run_switzerland_colombia",
    "write_reports",
    "write_wc2026_report",
]
