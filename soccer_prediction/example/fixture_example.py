"""Illustrative international fixture examples, driven by one constant registry.

``FIXTURES`` names every competing team pair this module can forecast. Each
entry owns its own bundled offline sample (history + squad) and its own
registered data-source names, so adding a fixture never collides with another
one's registration. By default every function operates on ``DEFAULT_FIXTURE``
(Switzerland vs Colombia), matching the package's original example behaviour.

By default (``live=True``) each fixture uses **all real international results
from 2024-01-01 to today** for both teams, fetched from the public-domain
martj42 ``international_results`` dataset. When the network is unavailable it
falls back to the fixture's small bundled offline sample. Player (goalscorer)
markets use the bundled illustrative squads.

martj42 provides goals only, so scoreline, 1X2, BTTS, over/under, and per-half
markets are grounded in real results; corners and cards fall back to model
priors (use ``source='api_football'`` with a free key for real corner/card data).
"""

from __future__ import annotations

import logging
import webbrowser
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from soccer_prediction.datasources.base import DataSourceFactory, register_source
from soccer_prediction.datasources.errors import DataSourceError
from soccer_prediction.datasources.international_results import InternationalResultsSource
from soccer_prediction.example._data import load_packaged_history, load_packaged_players
from soccer_prediction.models import Fixture, MatchForecast, PlayerStats, TeamMatchStats
from soccer_prediction.public import forecast_fixture
from soccer_prediction.reporting import render_html, render_markdown, render_text

__all__ = [
    "DEFAULT_FIXTURE",
    "FIXTURES",
    "FixtureDataSource",
    "FixtureSpec",
    "build_forecast",
    "example_usage",
    "load_history",
    "load_players",
    "main",
    "run_example",
    "write_reports",
]

logger = logging.getLogger(__name__)

_SINCE = date(2024, 1, 1)


@dataclass(frozen=True, slots=True)
class FixtureSpec:
    """Static definition of one illustrative, competing international fixture."""

    key: str
    home: str
    away: str
    history_file: str
    players_file: str
    bundled_source: str
    live_source: str
    title: str


FIXTURES: dict[str, FixtureSpec] = {
    "switzerland_colombia": FixtureSpec(
        key="switzerland_colombia",
        home="Switzerland",
        away="Colombia",
        history_file="data/switzerland_colombia_history.json",
        players_file="data/switzerland_colombia_players.json",
        bundled_source="bundled_swi_col",
        live_source="swi_col_2024",
        title="Switzerland vs Colombia - Match Forecast (2024 to date)",
    ),
    "france_morocco": FixtureSpec(
        key="france_morocco",
        home="France",
        away="Morocco",
        history_file="data/france_morocco_history.json",
        players_file="data/france_morocco_players.json",
        bundled_source="bundled_fra_mar",
        live_source="fra_mar_2024",
        title="France vs Morocco - Match Forecast (2024 to date)",
    ),
    "argentina_egypt": FixtureSpec(
        key="argentina_egypt",
        home="Argentina",
        away="Egypt",
        history_file="data/argentina_egypt_history.json",
        players_file="data/argentina_egypt_players.json",
        bundled_source="bundled_arg_egy",
        live_source="arg_egy_2024",
        title="Argentina vs Egypt - Match Forecast (2024 to date)",
    ),
    "spain_belgium": FixtureSpec(
        key="spain_belgium",
        home="Spain",
        away="Belgium",
        history_file="data/spain_belgium_history.json",
        players_file="data/spain_belgium_players.json",
        bundled_source="bundled_esp_bel",
        live_source="esp_bel_2024",
        title="Spain vs Belgium - Match Forecast (2024 to date)",
    ),
}

DEFAULT_FIXTURE = "spain_belgium"


class FixtureDataSource:
    """Data source for one fixture: real 2024-to-date results (live) or bundled."""

    def __init__(self, spec: FixtureSpec, *, live: bool) -> None:
        self.spec = spec
        self.live = live
        self._players = load_packaged_players(spec.players_file)
        self._bundled = load_packaged_history(spec.history_file, spec.bundled_source)

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
        """Return the single fixture this data source was built for."""
        return [Fixture(home_team=self.spec.home, away_team=self.spec.away, competition=competition)]

    def fetch_players(self, team: str) -> list[PlayerStats]:
        """Return bundled squad rows for one team."""
        return [player for player in self._players if player.team.casefold() == team.casefold()]


def _make_factory(spec: FixtureSpec, *, live: bool) -> DataSourceFactory:
    def factory() -> FixtureDataSource:
        return FixtureDataSource(spec, live=live)

    return factory


def _register_fixture_sources() -> None:
    for spec in FIXTURES.values():
        register_source(spec.bundled_source)(_make_factory(spec, live=False))
        register_source(spec.live_source)(_make_factory(spec, live=True))


_register_fixture_sources()


def _spec(key: str) -> FixtureSpec:
    try:
        return FIXTURES[key]
    except KeyError as exc:
        available = ", ".join(sorted(FIXTURES))
        raise KeyError(f"unknown fixture {key!r}; available: {available}") from exc


def load_history(key: str = DEFAULT_FIXTURE) -> list[TeamMatchStats]:
    """Load a fixture's bundled offline fallback history."""
    spec = _spec(key)
    return load_packaged_history(spec.history_file, spec.bundled_source)


def load_players(key: str = DEFAULT_FIXTURE) -> list[PlayerStats]:
    """Load a fixture's bundled illustrative squads."""
    return load_packaged_players(_spec(key).players_file)


def build_forecast(model: str = "dixon_coles", *, key: str = DEFAULT_FIXTURE, live: bool = True) -> MatchForecast:
    """Forecast a fixture (live real 2024-to-date data by default)."""
    spec = _spec(key)
    source = spec.live_source if live else spec.bundled_source
    return forecast_fixture(spec.home, spec.away, model=model, source=source)


def write_reports(
    output_dir: str | Path | None = None,
    *,
    key: str = DEFAULT_FIXTURE,
    model: str = "dixon_coles",
    live: bool = True,
) -> dict[str, Path]:
    """Write timestamped HTML and Markdown reports for a fixture and return their paths."""
    spec = _spec(key)
    forecast = build_forecast(model, key=key, live=live)
    generated_at = datetime.now(UTC)
    stamp = generated_at.strftime("%Y-%m-%d_%H-%M-%S")
    out = Path("reports") if output_dir is None else Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    html_path = out / f"{spec.key}_{stamp}.html"
    md_path = out / f"{spec.key}_{stamp}.md"
    html_path.write_text(render_html(forecast, title=spec.title, generated_at=generated_at), encoding="utf-8")
    md_path.write_text(f"# {spec.title}\n\n{render_markdown(forecast, generated_at=generated_at)}\n", encoding="utf-8")
    return {"html": html_path, "md": md_path}


def _open_in_browser(path: Path) -> None:
    """Open a report in the default browser, or print its path if none is available."""
    try:
        opened = webbrowser.open(path.resolve().as_uri())
    except webbrowser.Error:
        opened = False
    print(f"opened {path.name} in your browser" if opened else f"open the report manually: {path.resolve()}")


def run_example(
    output_dir: str | Path | None = None,
    *,
    key: str = DEFAULT_FIXTURE,
    live: bool = True,
    open_browser: bool = False,
) -> dict[str, Path]:
    """Print a text forecast, write the HTML and Markdown reports, optionally open the HTML."""
    print(render_text(build_forecast(key=key, live=live)))
    paths = write_reports(output_dir, key=key, live=live)
    for kind, path in paths.items():
        print(f"wrote {kind} report: {path}")
    if open_browser:
        _open_in_browser(paths["html"])
    return paths


def example_usage() -> None:
    """Run the default fixture example and open the HTML report in the default browser."""
    run_example(open_browser=True)


def main() -> None:
    """Module entry point."""
    example_usage()


if __name__ == "__main__":
    main()
