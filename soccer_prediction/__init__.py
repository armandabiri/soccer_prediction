"""Top-level package facade for soccer_prediction."""

from __future__ import annotations

from soccer_prediction.public import forecast_fixture, predict_match
from soccer_prediction.strategy import build_betting_strategy, load_quote_snapshot

from .version import __version__

__all__ = [
    "__version__",
    "build_betting_strategy",
    "example_usage",
    "forecast_fixture",
    "load_quote_snapshot",
    "main",
    "predict_match",
]


def example_usage() -> None:
    """Print a lightweight scaffold message."""
    forecast = forecast_fixture("Brazil", "Argentina")
    print(f"soccer_prediction {__version__}: {forecast.result.selection} {forecast.result.probability:.1%}")


def main() -> None:
    """Run the package entry point."""
    from soccer_prediction.cli.main import main as cli_main

    cli_main()
