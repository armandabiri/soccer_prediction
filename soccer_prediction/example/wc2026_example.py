"""Offline World Cup 2026 worked example.

Loads a small packaged history (no network), registers it as the
``bundled_wc2026`` data source, and forecasts a sample fixture end to end
through the public facade (Dixon-Coles goals, per-half, corners, cards).
"""

from __future__ import annotations

from soccer_prediction.datasources.base import register_source
from soccer_prediction.example._data import load_packaged_history
from soccer_prediction.models import Fixture, TeamMatchStats
from soccer_prediction.public import forecast_fixture
from soccer_prediction.reporting import render_text

__all__ = ["BundledWorldCupSource", "example_usage", "load_sample_history", "main", "run_example"]

_SAMPLE_HOME = "Brazil"
_SAMPLE_AWAY = "Argentina"
_SOURCE = "bundled_wc2026"


def load_sample_history() -> list[TeamMatchStats]:
    """Load the packaged offline sample history as typed records."""
    return load_packaged_history("data/sample_history.json", _SOURCE)


class BundledWorldCupSource:
    """In-package data source backed by the offline sample history."""

    def __init__(self) -> None:
        self._history = load_sample_history()

    def fetch_team_history(self, team: str, competition: str | None = None) -> list[TeamMatchStats]:
        """Return packaged history rows for one team."""
        return [record for record in self._history if record.team.casefold() == team.casefold()]

    def fetch_fixtures(self, competition: str) -> list[Fixture]:
        """Return the single sample World Cup 2026 fixture."""
        return [Fixture(home_team=_SAMPLE_HOME, away_team=_SAMPLE_AWAY, competition=competition)]


@register_source(_SOURCE)
def _factory() -> BundledWorldCupSource:
    return BundledWorldCupSource()


def run_example() -> str:
    """Forecast the sample fixture from bundled data and print the report."""
    forecast = forecast_fixture(_SAMPLE_HOME, _SAMPLE_AWAY, model="dixon_coles", source=_SOURCE)
    text = render_text(forecast)
    print(text)
    return text


def example_usage() -> None:
    """Run the offline worked example."""
    run_example()


def main() -> None:
    """Module entry point."""
    example_usage()


if __name__ == "__main__":
    main()
