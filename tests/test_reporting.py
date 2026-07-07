"""T23 acceptance: forecast rendering round-trips through JSON."""

from __future__ import annotations

import json

from soccer_prediction.public import forecast_fixture
from soccer_prediction.reporting import render_json, render_markdown, render_text


def test_json_roundtrip() -> None:
    """JSON export re-parses to the same headline market values."""
    forecast = forecast_fixture("Brazil", "Argentina", source="bundled_wc2026")
    parsed = json.loads(render_json(forecast))
    assert parsed["model_name"] == "dixon_coles"
    assert abs(parsed["result"]["probability"] - forecast.result.probability) < 1e-9
    assert abs(parsed["corners"]["total_expected"] - forecast.corners.total_expected) < 1e-9


def test_text_and_markdown_render() -> None:
    """Text and Markdown renderers include the requested markets."""
    forecast = forecast_fixture("Brazil", "Argentina", source="bundled_wc2026")
    text = render_text(forecast)
    assert "Minimum corners" in text
    markdown = render_markdown(forecast)
    assert "### Match result (1X2)" in markdown
    assert "### Corners" in markdown
