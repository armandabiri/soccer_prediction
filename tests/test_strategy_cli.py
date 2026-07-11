"""Opt-in quote-aware CLI workflow tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from soccer_prediction.cli.main import app

runner = CliRunner()


def test_cli_generates_strategy_markdown(tmp_path: Path) -> None:
    quote_path = tmp_path / "quotes.json"
    quote_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "venue": "test",
                "observed_at": datetime.now(UTC).isoformat(),
                "contracts": [
                    {"market": "match_result", "selection": "home", "ask": "0.01", "bid": "0.01"}
                ],
            }
        ),
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        [
            "predict", "--home", "Norway", "--away", "England", "--source", "bundled_nor_eng",
            "--format", "md", "--quotes", str(quote_path),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "Betting value & bankroll allocation" in result.stdout


def test_cli_rejects_bad_strategy_decimal(tmp_path: Path) -> None:
    quote_path = tmp_path / "bad.json"
    quote_path.write_text("{}", encoding="utf-8")
    result = runner.invoke(app, ["predict", "--home", "A", "--away", "B", "--quotes", str(quote_path)])
    assert result.exit_code != 0

