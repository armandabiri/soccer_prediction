"""Runnable, offline worked examples for soccer_prediction.

Importing this package registers the bundled offline data sources for every
fixture in ``fixture_example.FIXTURES`` (including ``bundled_swi_col``) plus
``bundled_wc2026``, used by the examples.
"""

from __future__ import annotations

from functools import partial

from soccer_prediction.example.fixture_example import FIXTURES
from soccer_prediction.example.fixture_example import build_forecast as _build_forecast
from soccer_prediction.example.fixture_example import run_example as _run_example
from soccer_prediction.example.fixture_example import write_reports as _write_reports
from soccer_prediction.example.wc2026_example import BundledWorldCupSource, load_sample_history, run_example
from soccer_prediction.example.worldcup2026_live import forecast_wc2026, write_wc2026_report

__all__ = [
    "FIXTURES",
    "BundledWorldCupSource",
    "build_forecast",
    "forecast_wc2026",
    "load_sample_history",
    "run_example",
    "run_switzerland_colombia",
    "write_reports",
    "write_wc2026_report",
]

# Pinned to "switzerland_colombia" regardless of fixture_example.DEFAULT_FIXTURE,
# since these names and the README's "Example: Switzerland vs Colombia" section
# promise that specific fixture rather than whichever one is currently default.
build_forecast = partial(_build_forecast, key="switzerland_colombia")
write_reports = partial(_write_reports, key="switzerland_colombia")
run_switzerland_colombia = partial(_run_example, key="switzerland_colombia")
