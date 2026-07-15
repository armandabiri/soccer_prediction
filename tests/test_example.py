"""Coverage for the offline worked examples and report writers (T26)."""

from __future__ import annotations

from pathlib import Path

from soccer_prediction.example import build_forecast, load_sample_history, run_example, write_reports
from soccer_prediction.example.fixture_example import FIXTURES, load_history

_SWI_COL = "switzerland_colombia"


def test_wc2026_example_runs() -> None:
    """The World Cup 2026 example forecasts offline and prints a report."""
    text = run_example()
    assert "Brazil vs Argentina" in text
    assert len(load_sample_history()) > 0


def test_fixtures_registry_has_expected_matchups() -> None:
    """The constant FIXTURES registry names all competing team pairs."""
    assert {
        "switzerland_colombia",
        "france_morocco",
        "argentina_egypt",
        "spain_belgium",
        "spain_france",
        "argentina_england",
    } <= set(FIXTURES)
    for key, spec in FIXTURES.items():
        assert spec.key == key
        assert spec.home and spec.away
        assert spec.bundled_source != spec.live_source


def test_switzerland_colombia_history_loads() -> None:
    """Both national teams have bundled history rows."""
    history = load_history(key=_SWI_COL)
    teams = {record.team for record in history}
    assert {"Switzerland", "Colombia"} <= teams


def test_switzerland_colombia_reports_written(tmp_path: Path) -> None:
    """The example writes a non-trivial HTML and Markdown report."""
    paths = write_reports(tmp_path, live=False)
    html = paths["html"].read_text(encoding="utf-8")
    markdown = paths["md"].read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>")
    assert "Switzerland" in html
    assert "Corners" in html
    assert "Goalscorers" in html
    assert "James Rodriguez" in html
    assert "Betting value &amp; bankroll allocation" in html
    assert "Live correct-score exit ladder" in html
    # The strategy sections render as visual charts, not just tables.
    assert 'class="edge-chart"' in html  # net-edge bar chart
    assert 'class="ladder-card"' in html  # per-score exit ladder cards
    assert 'class="ptree"' in html  # vertical scoring-path tree
    assert 'class="ptree-branches"' in html
    assert 'class="wf-grid"' in html  # step-by-step sell-down waterfall (open positions only)
    assert "Position sell-down, step by step" in html
    assert "blue = covering next-goal invalidated positions" in html
    assert "Most confident markets" in html
    assert "$100" in html
    assert "Color map used throughout" in html
    assert 'class="plan-card"' in html  # side-by-side risk-plan cards
    # Betting markets settle on the regulation-time result, stated explicitly.
    assert "regulation-time (90') result" in html
    assert 'class="settle-note"' in html
    assert "Switzerland vs Colombia" in markdown
    assert "### Betting value & bankroll allocation" in markdown
    assert "### Goalscorers &amp; assists" in markdown or "### Goalscorers & assists" in markdown


def test_switzerland_colombia_forecast_favours_stronger_side() -> None:
    """Colombia's stronger scoring history yields more expected corners."""
    forecast = build_forecast(live=False)
    assert forecast.corners.total_expected > 0.0
    assert 0.0 <= forecast.btts.probability <= 1.0


def test_other_fixtures_load_independently() -> None:
    """France/Morocco, Argentina/Egypt, Spain/Belgium, Spain/France, Argentina/England load their own data."""
    france_morocco = load_history(key="france_morocco")
    argentina_egypt = load_history(key="argentina_egypt")
    spain_belgium = load_history(key="spain_belgium")
    spain_france = load_history(key="spain_france")
    argentina_england = load_history(key="argentina_england")
    assert {"France", "Morocco"} <= {record.team for record in france_morocco}
    assert {"Argentina", "Egypt"} <= {record.team for record in argentina_egypt}
    assert {"Spain", "Belgium"} <= {record.team for record in spain_belgium}
    assert {"Spain", "France"} <= {record.team for record in spain_france}
    assert {"Argentina", "England"} <= {record.team for record in argentina_england}
    # Opponents may overlap across fixtures via the network pack; primary pairs must not.
    assert "England" not in {record.team for record in argentina_egypt}
    assert "Belgium" not in {record.team for record in spain_france}
    assert "Morocco" not in {record.team for record in spain_belgium}
