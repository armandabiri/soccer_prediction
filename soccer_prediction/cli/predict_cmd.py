"""Prediction CLI handlers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated, Literal

import typer

from soccer_prediction.models import StrategyRequest
from soccer_prediction.public import forecast_fixture
from soccer_prediction.reporting import render_html, render_json, render_markdown, render_text
from soccer_prediction.strategy import build_betting_strategy, load_quote_snapshot

__all__ = ["cmd_fetch", "cmd_predict"]

OutputFormat = Literal["text", "json", "md", "html"]
StrategyPlan = Literal["conservative", "balanced", "aggressive"]


def _decimal_option(value: str, name: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as error:
        raise typer.BadParameter("must be a decimal value", param_hint=name) from error


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
    as_of: Annotated[str | None, typer.Option("--as-of", help="Forecast date (YYYY-MM-DD)")] = None,
    neutral_venue: Annotated[bool, typer.Option("--neutral-venue", help="Remove home-field effects")] = False,
    output_format: Annotated[OutputFormat, typer.Option("--format")] = "text",
    output: Annotated[Path | None, typer.Option("--output", help="Write the report to a file")] = None,
    quotes: Annotated[Path | None, typer.Option("--quotes", help="Executable quote snapshot JSON")] = None,
    bankroll: Annotated[str, typer.Option("--bankroll", help="Strategy bankroll in dollars")] = "10.00",
    strategy_plan: Annotated[StrategyPlan, typer.Option("--strategy-plan")] = "balanced",
    safety_margin: Annotated[str, typer.Option("--safety-margin")] = "0.03",
    slippage: Annotated[str, typer.Option("--slippage", help="Per-contract slippage in dollars")] = "0.005",
    reserve_pct: Annotated[str | None, typer.Option("--reserve-pct")] = None,
    max_quote_age: Annotated[int, typer.Option("--max-quote-age", help="Maximum quote age in seconds")] = 3600,
) -> None:
    """Forecast a fixture and print or write a report in the chosen format."""
    try:
        forecast_date = date.fromisoformat(as_of) if as_of else None
    except ValueError as error:
        raise typer.BadParameter("must use YYYY-MM-DD", param_hint="--as-of") from error
    forecast = forecast_fixture(
        home,
        away,
        model=model,
        source=source,
        as_of=forecast_date,
        neutral_venue=neutral_venue,
    )
    strategy = None
    if quotes is not None:
        try:
            request = StrategyRequest(
                bankroll=_decimal_option(bankroll, "--bankroll"),
                plan=strategy_plan,
                safety_margin=_decimal_option(safety_margin, "--safety-margin"),
                slippage=_decimal_option(slippage, "--slippage"),
                reserve_pct=_decimal_option(reserve_pct, "--reserve-pct") if reserve_pct else None,
                max_quote_age_seconds=max_quote_age,
            )
            strategy = build_betting_strategy(forecast, load_quote_snapshot(quotes), request=request)
        except ValueError as error:
            raise typer.BadParameter(str(error), param_hint="--quotes/strategy") from error
    if output_format == "json":
        content = render_json(forecast, strategy=strategy)
    elif output_format == "md":
        content = render_markdown(forecast, strategy=strategy)
    elif output_format == "html":
        content = render_html(forecast, title=f"{home} vs {away} - Match Forecast", strategy=strategy)
    else:
        content = render_text(forecast, strategy=strategy)
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
