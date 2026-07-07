"""Backtest CLI handlers."""

from __future__ import annotations

from typing import Annotated

import typer

__all__ = ["cmd_backtest"]


def cmd_backtest(
    competition: Annotated[str, typer.Option("--competition")] = "world-cup",
    metric: Annotated[str, typer.Option("--metric")] = "rps",
) -> None:
    """Placeholder backtest command until calibration tasks are available."""
    typer.echo(f"backtest requested for {competition} using {metric}")
