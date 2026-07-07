"""Switzerland vs Colombia worked example.

By default this uses **all real international results from 2024-01-01 to today**
for both teams, fetched from the public-domain martj42 ``international_results``
dataset (registered source ``swi_col_2024``), and forecasts the fixture. When
the network is unavailable it falls back to a small bundled offline sample
(``bundled_swi_col``). Player (goalscorer) markets use bundled illustrative
squads.

martj42 provides goals only, so scoreline, 1X2, BTTS, over/under, and per-half
markets are grounded in real results; corners and cards fall back to model
priors (use ``source='api_football'`` with a free key for real corner/card data).
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from soccer_prediction.datasources.base import register_source
from soccer_prediction.datasources.errors import DataSourceError
from soccer_prediction.datasources.international_results import InternationalResultsSource
from soccer_prediction.example._data import load_packaged_history, load_packaged_players
from soccer_prediction.models import Fixture, MatchForecast, PlayerStats, TeamMatchStats
from soccer_prediction.public import forecast_fixture
from soccer_prediction.reporting import render_html, render_markdown, render_text

__all__ = [
    "SwissColombiaSource",
    "build_forecast",
    "example_usage",
    "load_history",
    "load_players",
    "main",
    "run_example",
    "write_reports",
]

logger = logging.getLogger(__name__)

_HOME = "Switzerland"
_AWAY = "Colombia"
_SINCE = date(2024, 1, 1)
_TITLE = "Switzerland vs Colombia - Match Forecast (2024 to date)"


def load_history() -> list[TeamMatchStats]:
    """Load the bundled Switzerland/Colombia offline fallback history."""
    return load_packaged_history("data/switzerland_colombia_history.json", "bundled_swi_col")


def load_players() -> list[PlayerStats]:
    """Load the bundled Switzerland/Colombia illustrative squads."""
    return load_packaged_players("data/switzerland_colombia_players.json")


class SwissColombiaSource:
    """Data source for the fixture: real 2024-to-date results (live) or bundled."""

    def __init__(self, *, live: bool = False) -> None:
        self.live = live
        self._players = load_players()
        self._bundled = load_history()

    def fetch_team_history(self, team: str, competition: str | None = None) -> list[TeamMatchStats]:
        """Return a team's real 2024-to-date results, else the bundled sample."""
        if self.live:
            live_records = self._live_history(team)
            if live_records:
                return live_records
        return [record for record in self._bundled if record.team.casefold() == team.casefold()]

    def _live_history(self, team: str) -> list[TeamMatchStats]:
        try:
            return InternationalResultsSource(since=_SINCE).fetch_team_history(team)
        except (DataSourceError, OSError) as exc:
            logger.warning("live international results unavailable (%s); using bundled sample", exc)
            return []

    def fetch_fixtures(self, competition: str) -> list[Fixture]:
        """Return the single Switzerland vs Colombia fixture."""
        return [Fixture(home_team=_HOME, away_team=_AWAY, competition=competition)]

    def fetch_players(self, team: str) -> list[PlayerStats]:
        """Return bundled squad rows for one team."""
        return [player for player in self._players if player.team.casefold() == team.casefold()]


@register_source("bundled_swi_col")
def _factory_bundled() -> SwissColombiaSource:
    return SwissColombiaSource(live=False)


@register_source("swi_col_2024")
def _factory_live() -> SwissColombiaSource:
    return SwissColombiaSource(live=True)


def build_forecast(model: str = "dixon_coles", *, live: bool = True) -> MatchForecast:
    """Forecast Switzerland vs Colombia (live real 2024-to-date data by default)."""
    return forecast_fixture(_HOME, _AWAY, model=model, source="swi_col_2024" if live else "bundled_swi_col")


def write_reports(
    output_dir: str | Path | None = None,
    *,
    model: str = "dixon_coles",
    live: bool = True,
) -> dict[str, Path]:
    """Write HTML and Markdown reports for the fixture and return their paths."""
    forecast = build_forecast(model, live=live)
    out = Path("reports") if output_dir is None else Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    html_path = out / "switzerland_colombia.html"
    md_path = out / "switzerland_colombia.md"
    html_path.write_text(render_html(forecast, title=_TITLE), encoding="utf-8")
    md_path.write_text(f"# {_TITLE}\n\n{render_markdown(forecast)}\n", encoding="utf-8")
    return {"html": html_path, "md": md_path}


def run_example(output_dir: str | Path | None = None, *, live: bool = True) -> dict[str, Path]:
    """Print a text forecast and write the HTML and Markdown reports."""
    print(render_text(build_forecast(live=live)))
    paths = write_reports(output_dir, live=live)
    for kind, path in paths.items():
        print(f"wrote {kind} report: {path}")
    return paths


def example_usage() -> None:
    """Run the Switzerland vs Colombia example (real 2024-to-date data)."""
    run_example()


def main() -> None:
    """Module entry point."""
    example_usage()


if __name__ == "__main__":
    main()
