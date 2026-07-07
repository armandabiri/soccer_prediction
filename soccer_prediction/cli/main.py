"""Typer CLI entry point."""

from __future__ import annotations

import typer

from soccer_prediction.cli.backtest_cmd import cmd_backtest
from soccer_prediction.cli.predict_cmd import cmd_fetch, cmd_predict

__all__ = ["app", "main"]

app = typer.Typer(help="Soccer prediction command line interface.")
app.command("predict")(cmd_predict)
app.command("fetch")(cmd_fetch)
app.command("backtest")(cmd_backtest)


def main() -> None:
    """Run the CLI app."""
    app()
