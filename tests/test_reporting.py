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
    assert parsed["model_name"] == "dixon_coles"
    assert abs(parsed["result"]["probability"] - forecast.result.probability) < 1e-9
    assert abs(parsed["corners"]["total_expected"] - forecast.corners.total_expected) < 1e-9
    assert len(parsed["history"]) == len(forecast.history) > 0


def test_text_and_markdown_render() -> None:
    """Text and Markdown renderers include the requested markets."""
    forecast = forecast_fixture("Brazil", "Argentina", source="bundled_wc2026")
    text = render_text(forecast)
    assert "Minimum corners" in text
    markdown = render_markdown(forecast)
    assert "### Match result (1X2)" in markdown
    assert "### Corners" in markdown


def test_timestamp_and_history_section() -> None:
    """Every format carries a YYYY-MM-DD_HH-MM-SS timestamp and a history section."""
    forecast = forecast_fixture("Brazil", "Argentina", source="bundled_wc2026")
    text = render_text(forecast)
    markdown = render_markdown(forecast)
    html = render_html(forecast)
    for rendered in (text, markdown, html):
        assert _STAMP.search(rendered) is not None
        assert "Historical data used" in rendered
    # the history table lists the actual teams used
    assert "Brazil" in html
    assert "| Team | Date | Opponent" in markdown
