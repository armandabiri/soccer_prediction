"""All-format betting strategy report coverage."""

from __future__ import annotations

import json

from soccer_prediction.models import BettingStrategy, MatchForecast
from soccer_prediction.reporting import render_html, render_json, render_markdown, render_text


def test_strategy_appears_in_all_report_formats(
    strategy_forecast: MatchForecast, betting_strategy: BettingStrategy
) -> None:
    markdown = render_markdown(strategy_forecast, strategy=betting_strategy)
    html = render_html(strategy_forecast, strategy=betting_strategy)
    text = render_text(strategy_forecast, strategy=betting_strategy)
    assert "### Betting value & bankroll allocation" in markdown
    assert "### Live correct-score exit ladder" in markdown
    assert "Major scoring paths & capital recovery" in markdown
    assert "Conservative, balanced &amp; aggressive plans" in html
    assert "Betting strategy (price-aware)" in text


def test_strategy_json_is_additive(strategy_forecast: MatchForecast, betting_strategy: BettingStrategy) -> None:
    plain = json.loads(render_json(strategy_forecast))
    enriched = json.loads(render_json(strategy_forecast, strategy=betting_strategy))
    assert "betting_strategy" not in plain
    assert enriched["betting_strategy"]["schema_version"] == 1
    assert enriched["betting_strategy"]["uninvested_cash"] == str(betting_strategy.uninvested_cash)
