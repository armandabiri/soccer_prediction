"""T23 acceptance: forecast rendering round-trips through JSON, with timestamp + history."""

from __future__ import annotations

import json
import re

from soccer_prediction.public import forecast_fixture
from soccer_prediction.reporting import render_html, render_json, render_markdown, render_text

_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}")


def test_json_roundtrip() -> None:
    """JSON export re-parses to the same headline market values and lists history."""
    forecast = forecast_fixture("Brazil", "Argentina", source="bundled_wc2026")
    parsed = json.loads(render_json(forecast))
    assert parsed["model_name"] == "ensemble"
    assert abs(parsed["result"]["probability"] - forecast.result.probability) < 1e-9
    assert abs(parsed["corners"]["total_expected"] - forecast.corners.total_expected) < 1e-9
    assert len(parsed["history"]) == len(forecast.history) > 0
    assert parsed["scenario_analysis"]["model_estimates"]


def test_text_and_markdown_render() -> None:
    """Text and Markdown renderers include the requested markets."""
    forecast = forecast_fixture("Brazil", "Argentina", source="bundled_wc2026")
    text = render_text(forecast)
    assert "Minimum corners" in text
    markdown = render_markdown(forecast)
    assert "### Match result (1X2)" in markdown
    assert "### Corners" in markdown
    assert "### Ensemble conclusion, robustness & random scenarios" in markdown
    assert "All goal algorithms" in markdown
    assert "Form, head-to-head & opponent network" in markdown
    html = render_html(forecast)
    assert "Latest games &amp; opponent dependencies" in html
    assert 'class="net-graph"' in html
    assert 'class="form-timeline"' in html
    assert 'class="fgame' in html
    assert 'class="net-edge-label"' in html
    assert "Atk" in html
    assert "neff" in html
    assert "time decay xi=" in html


def test_timestamp_and_history_section() -> None:
    """Every format carries a YYYY-MM-DD_HH-MM-SS timestamp and a history section."""
    forecast = forecast_fixture("Brazil", "Argentina", source="bundled_wc2026")
    text = render_text(forecast)
    markdown = render_markdown(forecast)
    html = render_html(forecast)
    for rendered in (text, markdown, html):
        assert _STAMP.search(rendered) is not None
        assert "Historical data used" in rendered
        assert "random scenarios" in rendered.lower() or "Simulated 80% goal range" in rendered
    # the history table lists the actual teams used
    assert "Brazil" in html
    assert "| Team | Date | Opponent" in markdown


def test_html_exposes_all_model_decision_visuals() -> None:
    """The standalone report lets readers compare algorithms and inspect the ensemble distribution."""
    forecast = forecast_fixture("Brazil", "Argentina", source="bundled_wc2026")
    html = render_html(forecast)
    for name in ("Poisson", "Dixon Coles", "Negative Binomial", "Bivariate Poisson", "Monte Carlo", "Ensemble"):
        assert name in html
    assert "1X2 predictions by algorithm" in html
    assert "Approximate 80% uncertainty ranges" in html
    assert "Goals-market sensitivity" in html
    assert "Ensemble score distribution" in html
    assert "Tail scenario probabilities" in html
    assert "Scoreless draw" in html
    assert "--home:#2563eb" in html
    assert "--away:#dc2626" in html
    assert "heat-gradient" in html
    assert "leads · red" in html
    assert "leads · blue" in html
    assert 'class="heat home' in html
    assert 'class="heat away' in html
    assert 'class="heat draw' in html
    assert 'class="sidenav"' in html
    assert 'class="sidenav-link"' in html
    assert 'id="match-result-1x2"' in html or 'id="match-result' in html
    assert "Most confident markets" in html
    shares = [
        float(value)
        for value in re.findall(r'\$\d+\.\d+</td><td class="n">(\d+\.\d+)%</td>', html)
    ]
    assert shares
    assert shares == sorted(shares, reverse=True)
