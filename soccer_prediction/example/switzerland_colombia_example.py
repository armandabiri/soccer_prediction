"""Switzerland vs Colombia worked example.

Loads bundled offline history for both national teams, registers it as the
``bundled_swi_col`` data source, forecasts every supported market through the
public facade, and writes a styled HTML report plus a Markdown report.

The bundled history is *illustrative sample data* for an offline demo. In
production the same models run on real data fetched from the free sources
(API-Football, StatsBomb open-data, football-data.co.uk, openfootball).
"""

from __future__ import annotations

from pathlib import Path

from soccer_prediction.datasources.base import register_source
from soccer_prediction.example._data import load_packaged_history
from soccer_prediction.models import Fixture, MatchForecast, TeamMatchStats
from soccer_prediction.public import forecast_fixture
from soccer_prediction.reporting import render_html, render_markdown, render_text

__all__ = [
    "SwissColombiaSource",
    "build_forecast",
    "example_usage",
    "load_history",
    "main",
    "run_example",
    "write_reports",
]

_HOME = "Switzerland"
_AWAY = "Colombia"
_SOURCE = "bundled_swi_col"
_TITLE = "Switzerland vs Colombia - Match Forecast"


def load_history() -> list[TeamMatchStats]:
    """Load the bundled Switzerland/Colombia sample history."""
    return load_packaged_history("data/switzerland_colombia_history.json", _SOURCE)


class SwissColombiaSource:
    """Offline data source backed by the bundled Switzerland/Colombia history."""

    def __init__(self) -> None:
        self._history = load_history()

    def fetch_team_history(self, team: str, competition: str | None = None) -> list[TeamMatchStats]:
        """Return bundled history rows for one team."""
        return [record for record in self._history if record.team.casefold() == team.casefold()]

    def fetch_fixtures(self, competition: str) -> list[Fixture]:
        """Return the single Switzerland vs Colombia sample fixture."""
        return [Fixture(home_team=_HOME, away_team=_AWAY, competition=competition)]


@register_source(_SOURCE)
def _factory() -> SwissColombiaSource:
    return SwissColombiaSource()


def build_forecast(model: str = "dixon_coles") -> MatchForecast:
    """Forecast Switzerland vs Colombia from the bundled history."""
    return forecast_fixture(_HOME, _AWAY, model=model, source=_SOURCE)


def write_reports(output_dir: str | Path | None = None, *, model: str = "dixon_coles") -> dict[str, Path]:
    """Write HTML and Markdown reports for the fixture and return their paths."""
    forecast = build_forecast(model)
    out = Path("reports") if output_dir is None else Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    html_path = out / "switzerland_colombia.html"
    md_path = out / "switzerland_colombia.md"
    html_path.write_text(render_html(forecast, title=_TITLE), encoding="utf-8")
    md_path.write_text(f"# {_TITLE}\n\n{render_markdown(forecast)}\n", encoding="utf-8")
    return {"html": html_path, "md": md_path}


def run_example(output_dir: str | Path | None = None) -> dict[str, Path]:
    """Print a text forecast and write the HTML and Markdown reports."""
    print(render_text(build_forecast()))
    paths = write_reports(output_dir)
    for kind, path in paths.items():
        print(f"wrote {kind} report: {path}")
    return paths


def example_usage() -> None:
    """Run the Switzerland vs Colombia example."""
    run_example()


def main() -> None:
    """Module entry point."""
    example_usage()


if __name__ == "__main__":
    main()
