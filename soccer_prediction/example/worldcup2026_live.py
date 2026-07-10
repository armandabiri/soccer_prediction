"""Live World Cup 2026 example (real results, no API key).

Fetches the current, real World Cup 2026 results from the public-domain
openfootball dataset via the registered ``worldcup_2026`` source and forecasts a
fixture from actual tournament data. **Requires network access.**

openfootball ships goals and half-time scores, so the scoreline, 1X2, BTTS,
over/under, and per-half markets are grounded in real results. It does NOT
include corners or cards, so those fall back to model priors (use
``source='api_football'`` with a free key for real corner/card markets).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from soccer_prediction.models import MatchForecast
from soccer_prediction.public import forecast_fixture
from soccer_prediction.reporting import render_html, render_markdown, render_text

__all__ = ["forecast_wc2026", "write_wc2026_report", "example_usage", "main"]

_SOURCE = "worldcup_2026"


def forecast_wc2026(home: str = "Switzerland", away: str = "Colombia", *, model: str = "dixon_coles") -> MatchForecast:
    """Forecast a World Cup 2026 fixture from real openfootball results (network)."""
    return forecast_fixture(home, away, model=model, source=_SOURCE)


def write_wc2026_report(
    home: str = "Switzerland",
    away: str = "Colombia",
    output_dir: str | Path | None = None,
) -> dict[str, Path]:
    """Write HTML and Markdown reports for a real World Cup 2026 fixture."""
    forecast = forecast_wc2026(home, away)
    generated_at = datetime.now(UTC)
    stamp = generated_at.strftime("%Y-%m-%d_%H-%M-%S")
    out = Path("reports") if output_dir is None else Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    slug = f"wc2026_{home}_{away}".lower().replace(" ", "_")
    title = f"{home} vs {away} - World Cup 2026 (real results)"
    html_path = out / f"{slug}_{stamp}.html"
    md_path = out / f"{slug}_{stamp}.md"
    html_path.write_text(render_html(forecast, title=title, generated_at=generated_at), encoding="utf-8")
    md_path.write_text(f"# {title}\n\n{render_markdown(forecast, generated_at=generated_at)}\n", encoding="utf-8")
    return {"html": html_path, "md": md_path}


def example_usage() -> None:
    """Print a real World Cup 2026 forecast for Switzerland vs Colombia."""
    print(render_text(forecast_wc2026()))


def main() -> None:
    """Forecast a real World Cup 2026 fixture and write reports."""
    example_usage()
    for kind, path in write_wc2026_report().items():
        print(f"wrote {kind} report: {path}")


if __name__ == "__main__":
    main()
