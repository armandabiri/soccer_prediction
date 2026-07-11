"""Shared test fixtures."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

# Importing the example package registers the bundled offline data sources
# (`bundled_wc2026`, `bundled_swi_col`) that several tests forecast against.
import soccer_prediction.example  # noqa: F401
from soccer_prediction.example.fixture_example import build_forecast, build_strategy
from soccer_prediction.models import BettingStrategy, MatchForecast, TeamMatchStats


@pytest.fixture(scope="session")
def strategy_forecast() -> MatchForecast:
    """Return the bundled Norway/England forecast used by strategy tests."""
    return build_forecast(key="norway_england", live=False)


@pytest.fixture(scope="session")
def betting_strategy(strategy_forecast: MatchForecast) -> BettingStrategy:
    """Return a complete strategy using the clearly labeled demo quotes."""
    return build_strategy(strategy_forecast)


@pytest.fixture
def sample_history() -> list[TeamMatchStats]:
    """Return a compact home/away duplicated history."""
    fetched_at = datetime.now(UTC)
    rows = [
        ("Brazil", "Argentina", date(2024, 1, 1), 2, 1, 1, 0, 6, 4, 2, 3),
        ("Argentina", "Brazil", date(2024, 2, 1), 1, 1, 0, 0, 5, 5, 3, 2),
        ("Brazil", "Argentina", date(2024, 3, 1), 3, 0, 1, 0, 7, 3, 1, 4),
    ]
    records: list[TeamMatchStats] = []
    for home, away, match_date, hg, ag, hth, hta, hc, ac, hy, ay in rows:
        records.append(
            TeamMatchStats(home, away, match_date, True, hg, ag, hth, hta, hc, ac, hy, 0, "fixture", fetched_at)
        )
        records.append(
            TeamMatchStats(away, home, match_date, False, ag, hg, hta, hth, ac, hc, ay, 0, "fixture", fetched_at)
        )
    return records
