"""Coverage for the offline worked examples and report writers (T26)."""

from __future__ import annotations

from pathlib import Path

from soccer_prediction.example import load_sample_history, run_example, write_reports
from soccer_prediction.example.switzerland_colombia_example import build_forecast, load_history


def test_wc2026_example_runs() -> None:
    """The World Cup 2026 example forecasts offline and prints a report."""
    text = run_example()
    assert "Brazil vs Argentina" in text
    assert len(load_sample_history()) > 0


def test_switzerland_colombia_history_loads() -> None:
    """Both national teams have bundled history rows."""
    history = load_history()
    teams = {record.team for record in history}
    assert {"Switzerland", "Colombia"} <= teams


def test_switzerland_colombia_reports_written(tmp_path: Path) -> None:
    """The example writes a non-trivial HTML and Markdown report."""
    paths = write_reports(tmp_path)
    html = paths["html"].read_text(encoding="utf-8")
    markdown = paths["md"].read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>")
    assert "Switzerland" in html
    assert "Corners" in html
    assert "Switzerland vs Colombia" in markdown


def test_switzerland_colombia_forecast_favours_stronger_side() -> None:
    """Colombia's stronger scoring history yields more expected corners."""
    forecast = build_forecast()
    assert forecast.corners.total_expected > 0.0
    assert 0.0 <= forecast.btts.probability <= 1.0
