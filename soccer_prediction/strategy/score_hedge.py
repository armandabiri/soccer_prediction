"""Correct-score grid hedging: spread a bankroll to win on any covered score.

Given market "Yes" prices for exact scorelines (each contract pays 1.00 if that
score occurs) plus the model's probability for each score, this builds an
*equal-payout* hedge over a bounded grid (e.g. every score with no side above 2
or 3 goals). Stakes are proportional to price, so **every covered score returns
the same amount** -- that is the "guarantee a win if any of them happen" plan.

Because a guarantee that ignores how often the real score lands *outside* the
grid is misleading, every plan also carries the model-weighted expectation:
``P(score in grid)`` (the true chance the hedge pays at all) and the resulting
expected profit. No scoreline is ever treated as zero -- a missing price falls
back to the model probability, floored at a small epsilon.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import yaml

__all__ = [
    "GridHedgePlan",
    "ScoreGrid",
    "ScoreQuote",
    "ScoreStake",
    "build_grid_hedge",
    "build_grid_hedges",
    "example_usage",
    "load_packaged_score_grid",
    "load_score_grid",
    "main",
]

# Nothing is zero: prices and probabilities are floored here so a cell always
# takes a positive stake and contributes positive risk.
_EPSILON = 1e-4


@dataclass(frozen=True, slots=True)
class ScoreQuote:
    """One exact-score contract: market price and model probability."""

    home_goals: int
    away_goals: int
    price: float
    probability: float
    estimated_price: bool = False

    @property
    def label(self) -> str:
        """Return the ``home-away`` scoreline label."""
        return f"{self.home_goals}-{self.away_goals}"


@dataclass(frozen=True, slots=True)
class ScoreStake:
    """A funded position on one scoreline within a hedge plan."""

    home_goals: int
    away_goals: int
    price: float
    probability: float
    stake: float
    contracts: float
    payout_if_hit: float
    profit_if_hit: float
    value_edge: float
    estimated_price: bool

    @property
    def label(self) -> str:
        """Return the ``home-away`` scoreline label."""
        return f"{self.home_goals}-{self.away_goals}"


@dataclass(frozen=True, slots=True)
class GridHedgePlan:
    """An equal-payout hedge over every score within a goal cap."""

    label: str
    max_goals: int
    bankroll: float
    stakes: tuple[ScoreStake, ...]
    total_price: float
    covered_probability: float
    guaranteed_return: float
    guaranteed_profit: float
    guaranteed_roi: float
    worst_case_loss: float
    expected_value: float
    expected_profit: float
    is_true_arbitrage: bool


@dataclass(frozen=True, slots=True)
class ScoreGrid:
    """Loaded market grid: fixture identity plus one quote per scoreline."""

    home: str
    away: str
    bankroll: float
    quotes: tuple[ScoreQuote, ...]
    source: str = ""


def load_score_grid(path: str | Path) -> ScoreGrid:
    """Load a correct-score market grid (prices + model probabilities) from YAML."""
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return _grid_from_payload(payload)


def load_packaged_score_grid(resource: str) -> ScoreGrid:
    """Load a correct-score grid bundled under ``soccer_prediction.example.data``."""
    handle = resources.files("soccer_prediction.example").joinpath(f"data/{resource}")
    with resources.as_file(handle) as path:
        return load_score_grid(path)


def _grid_from_payload(payload: dict[str, object]) -> ScoreGrid:
    fixture = dict(payload.get("fixture", {})) if isinstance(payload.get("fixture"), dict) else {}
    rows = payload.get("scores", [])
    if not isinstance(rows, list) or not rows:
        raise ValueError("score grid YAML must contain a non-empty 'scores' list")
    quotes = tuple(_quote_from_row(row) for row in rows)
    return ScoreGrid(
        home=str(fixture.get("home", "Home")),
        away=str(fixture.get("away", "Away")),
        bankroll=float(payload.get("bankroll", 500.0)),
        quotes=quotes,
        source=str(payload.get("source", "")),
    )


def _quote_from_row(row: object) -> ScoreQuote:
    if not isinstance(row, dict):
        raise ValueError(f"score row must be a mapping, got {type(row).__name__}")
    price, quoted = _row_price(row)
    return ScoreQuote(
        home_goals=int(row["home"]),
        away_goals=int(row["away"]),
        price=price,
        probability=max(_EPSILON, float(row.get("probability", 0.0)) or _EPSILON),
        estimated_price=bool(row.get("estimated", False)) or not quoted,
    )


def _row_price(row: dict[str, object]) -> tuple[float, bool]:
    """Resolve a scoreline's price from the market percentage on screen.

    ``displayed`` is the real, observed market number for every score, so it is
    what the plans price against. (Two payout quotes on this book imply real
    fills cost ~1.1pp more than the screen; that is a genuine cost, but it was
    only ever measured on two 1-2% longshots and does not generalize to a 16%
    line. ``score_optimizer`` can apply it as an explicit sensitivity instead of
    baking a guess into the headline.) Schema 1 rows still carry flat ``price``.

    The second return value is False only when the displayed number itself was
    assumed rather than read off a screenshot.
    """
    displayed = row.get("displayed")
    if displayed is not None:
        return max(_EPSILON, float(displayed)), not bool(row.get("estimated", False))  # type: ignore[arg-type]
    legacy = float(row.get("price", 0.0) or 0.0)  # type: ignore[arg-type]
    return max(_EPSILON, legacy or _EPSILON), not bool(row.get("estimated", False))


def build_grid_hedge(
    quotes: Iterable[ScoreQuote],
    *,
    bankroll: float,
    max_goals: int,
    label: str | None = None,
) -> GridHedgePlan:
    """Distribute ``bankroll`` for an equal payout across every score within ``max_goals``.

    Stakes are set proportional to each price so the number of contracts is the
    same on every covered score; whichever covered score lands returns
    ``bankroll / sum(prices)``. The plan is a genuine arbitrage only when the
    covered prices sum to under 1.00 -- otherwise even a covered score returns
    less than the stake. The model probabilities give ``covered_probability``
    (the real chance any covered score occurs) and the expected profit.
    """
    if bankroll <= 0.0:
        raise ValueError("bankroll must be positive")
    if max_goals < 0:
        raise ValueError("max_goals must be non-negative")
    # Floor every price and probability so no scoreline is ever treated as zero
    # (no zero stake, no divide-by-zero, no silently dropped outcome).
    covered = tuple(
        ScoreQuote(
            home_goals=quote.home_goals,
            away_goals=quote.away_goals,
            price=max(_EPSILON, quote.price),
            probability=max(_EPSILON, quote.probability),
            estimated_price=quote.estimated_price,
        )
        for quote in quotes
        if quote.home_goals <= max_goals and quote.away_goals <= max_goals
    )
    if not covered:
        raise ValueError(f"no scorelines within a {max_goals}-goal cap")
    total_price = sum(quote.price for quote in covered)
    contracts = bankroll / total_price  # equal contract count on every covered score
    guaranteed_return = contracts  # each covered contract settles at 1.00
    covered_probability = min(1.0, sum(quote.probability for quote in covered))
    expected_value = covered_probability * guaranteed_return
    stakes = tuple(
        ScoreStake(
            home_goals=quote.home_goals,
            away_goals=quote.away_goals,
            price=quote.price,
            probability=quote.probability,
            stake=contracts * quote.price,
            contracts=contracts,
            payout_if_hit=guaranteed_return,
            profit_if_hit=guaranteed_return - bankroll,
            value_edge=quote.probability - quote.price,
            estimated_price=quote.estimated_price,
        )
        for quote in sorted(covered, key=lambda item: -item.price)
    )
    return GridHedgePlan(
        label=label or f"0-{max_goals} goals",
        max_goals=max_goals,
        bankroll=bankroll,
        stakes=stakes,
        total_price=total_price,
        covered_probability=covered_probability,
        guaranteed_return=guaranteed_return,
        guaranteed_profit=guaranteed_return - bankroll,
        guaranteed_roi=(guaranteed_return - bankroll) / bankroll,
        worst_case_loss=-bankroll,
        expected_value=expected_value,
        expected_profit=expected_value - bankroll,
        is_true_arbitrage=total_price < 1.0,
    )


def build_grid_hedges(
    grid: ScoreGrid,
    *,
    caps: Sequence[int] = (3, 2),
    bankroll: float | None = None,
) -> tuple[GridHedgePlan, ...]:
    """Build one equal-payout plan per goal cap (default: the 0-3 and 0-2 grids)."""
    stake_bankroll = grid.bankroll if bankroll is None else bankroll
    return tuple(
        build_grid_hedge(
            grid.quotes,
            bankroll=stake_bankroll,
            max_goals=cap,
            label=f"0-{cap} goals ({cap}-goal cap)",
        )
        for cap in caps
    )


def example_usage() -> None:
    """Print the 0-3 and 0-2 hedge plans for the bundled Argentina/England grid."""
    grid = load_packaged_score_grid("correct_score_argentina_england.yaml")
    for plan in build_grid_hedges(grid):
        print(
            f"{plan.label}: stake ${plan.bankroll:.0f} over {len(plan.stakes)} scores | "
            f"guaranteed return ${plan.guaranteed_return:.2f} "
            f"(profit ${plan.guaranteed_profit:+.2f}, {plan.guaranteed_roi * 100:+.1f}%) | "
            f"P(win)={plan.covered_probability * 100:.1f}% | "
            f"expected profit ${plan.expected_profit:+.2f}"
        )


def main() -> None:
    """Module entry point."""
    example_usage()


if __name__ == "__main__":
    main()
