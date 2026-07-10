"""Prediction CLI handlers."""

from __future__ import annotations

from pathlib import Path
from datetime import date
from typing import Annotated, Literal

import typer

from soccer_prediction.public import forecast_fixture
from soccer_prediction.reporting import render_html, render_json, render_markdown, render_text

__all__ = ["cmd_fetch", "cmd_predict"]

OutputFormat = Literal["text", "json", "md", "html"]


def cmd_predict(
    home: Annotated[str, typer.Option("--home")],
    away: Annotated[str, typer.Option("--away")],
    model: Annotated[
        str,
        typer.Option(
            "--model",
            help="Goal model: ensemble, dixon_coles, poisson, negative_binomial, bivariate_poisson, or monte_carlo",
        ),
    ] = "ensemble",
    source: Annotated[str, typer.Option("--source")] = "auto",
    as_of: Annotated[date | None, typer.Option("--as-of", help="Forecast date (YYYY-MM-DD)")] = None,
    neutral_venue: Annotated[bool, typer.Option("--neutral-venue", help="Remove home-field effects")] = False,
    output_format: Annotated[OutputFormat, typer.Option("--format")] = "text",
    output: Annotated[Path | None, typer.Option("--output", help="Write the report to a file")] = None,
) -> None:
    """Forecast a fixture and print or write a report in the chosen format."""
    forecast = forecast_fixture(
        home,
        away,
        model=model,
        source=source,
        as_of=as_of,
        neutral_venue=neutral_venue,
    )
    if output_format == "json":
        content = render_json(forecast)
    elif output_format == "md":
        content = render_markdown(forecast)
    elif output_format == "html":
        content = render_html(forecast, title=f"{home} vs {away} - Match Forecast")
    else:
        content = render_text(forecast)
    if output is not None:
        output.write_text(content, encoding="utf-8")
        typer.echo(f"wrote {output_format} report to {output}")
    else:
        typer.echo(content)


def cmd_fetch(
    team: Annotated[str, typer.Option("--team")],
    competition: Annotated[str | None, typer.Option("--competition")] = None,
) -> None:
    """Placeholder fetch command until source-specific persistence lands."""
    suffix = f" for {competition}" if competition else ""
    typer.echo(f"fetch requested for {team}{suffix}")
