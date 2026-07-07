"""T22 acceptance: the CLI exposes commands and exits cleanly."""

from __future__ import annotations

from typer.testing import CliRunner

from soccer_prediction.cli.main import app

runner = CliRunner()


def test_predict_exit_code() -> None:
    """`predict` returns exit code 0 and prints a forecast."""
    result = runner.invoke(app, ["predict", "--home", "Brazil", "--away", "Argentina", "--source", "bundled_wc2026"])
    assert result.exit_code == 0
    assert "Brazil" in result.stdout


def test_help_lists_commands() -> None:
    """`--help` exits 0 and lists the three commands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("predict", "fetch", "backtest"):
        assert command in result.stdout
