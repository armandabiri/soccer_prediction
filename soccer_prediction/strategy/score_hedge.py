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

# How far to lean on the model by default: half flat (price-proportional, equal
# payout), half opinionated (probability-proportional). Matches the report's
# risk slider, which starts at 50%.
DEFAULT_RISK = 0.5


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
    """A staking plan over every score within a goal cap.

    ``risk`` slides the money between two shapes. At 0 the stakes are
    price-proportional, so every covered score returns exactly the same -- the
    flat, equal-payout hedge. At 1 they follow the model's probabilities, paying
    far more on the scores the model likes and less on the rest. In between the
    payouts spread out, so ``guaranteed_*`` become the *worst* covered case and
    ``max_*`` the best; only at ``risk == 0`` are they equal.
    """

    label: str
    max_goals: int
    bankroll: float
    risk: float
    stakes: tuple[ScoreStake, ...]
    total_price: float
    covered_probability: float
    guaranteed_return: float
    guaranteed_profit: float
    guaranteed_roi: float
    max_return: float
    max_profit: float
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
    risk: float = DEFAULT_RISK,
) -> GridHedgePlan:
    """Distribute ``bankroll`` across every score within ``max_goals``.

    ``risk`` picks the shape of the money, from flat to opinionated:

    * ``0.0`` -- stakes proportional to price. Every covered score buys the same
      number of contracts, so every covered score returns the identical
      ``bankroll / sum(prices)``. Safe and shapeless: it is an arbitrage exactly
      when the covered prices sum below 1.00.
    * ``1.0`` -- stakes proportional to the model's probabilities. The scores the
      model likes get the money and pay big; the rest pay under the stake. This
      wins more when the model is right and less when it is wrong.
    * in between -- a linear blend, so payouts spread around the flat line.

    Above ``risk == 0`` the payout is no longer uniform, so ``guaranteed_*``
    describe the *worst* covered score and ``max_*`` the best.
    """
    if bankroll <= 0.0:
        raise ValueError("bankroll must be positive")
    if max_goals < 0:
        raise ValueError("max_goals must be non-negative")
    risk = min(1.0, max(0.0, risk))
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
    total_probability = sum(quote.probability for quote in covered)
    covered_probability = min(1.0, total_probability)
    stakes = tuple(
        _stake_for(quote, bankroll=bankroll, risk=risk, price_sum=total_price, prob_sum=total_probability)
        for quote in sorted(covered, key=lambda item: -item.price)
    )
    payouts = [item.payout_if_hit for item in stakes]
    worst_return, best_return = min(payouts), max(payouts)
    expected_value = sum(item.probability * item.payout_if_hit for item in stakes)
    return GridHedgePlan(
        label=label or f"0-{max_goals} goals",
        max_goals=max_goals,
        bankroll=bankroll,
        risk=risk,
        stakes=stakes,
        total_price=total_price,
        covered_probability=covered_probability,
        guaranteed_return=worst_return,
        guaranteed_profit=worst_return - bankroll,
        guaranteed_roi=(worst_return - bankroll) / bankroll,
        max_return=best_return,
        max_profit=best_return - bankroll,
        worst_case_loss=-bankroll,
        expected_value=expected_value,
        expected_profit=expected_value - bankroll,
        # An arbitrage means *every* covered score profits, i.e. even the worst
        # one clears the stake. At risk 0 that reduces to sum(prices) < 1.
        is_true_arbitrage=worst_return > bankroll,
    )


def _stake_for(
    quote: ScoreQuote,
    *,
    bankroll: float,
    risk: float,
    price_sum: float,
    prob_sum: float,
) -> ScoreStake:
    """Size one score: blend its price share with its probability share by ``risk``."""
    price_share = quote.price / price_sum if price_sum > 0 else 0.0
    prob_share = quote.probability / prob_sum if prob_sum > 0 else 0.0
    stake = bankroll * ((1.0 - risk) * price_share + risk * prob_share)
    contracts = stake / quote.price
    return ScoreStake(
        home_goals=quote.home_goals,
        away_goals=quote.away_goals,
        price=quote.price,
        probability=quote.probability,
        stake=stake,
        contracts=contracts,
        payout_if_hit=contracts,  # each contract settles at 1.00
        profit_if_hit=contracts - bankroll,
        value_edge=quote.probability - quote.price,
        estimated_price=quote.estimated_price,
    )


def build_grid_hedges(
    grid: ScoreGrid,
    *,
    caps: Sequence[int] = (3, 2),
    bankroll: float | None = None,
    risk: float = DEFAULT_RISK,
) -> tuple[GridHedgePlan, ...]:
    """Build one staking plan per goal cap (default: the 0-3 and 0-2 grids)."""
    stake_bankroll = grid.bankroll if bankroll is None else bankroll
    return tuple(
        build_grid_hedge(
            grid.quotes,
            bankroll=stake_bankroll,
            max_goals=cap,
            label=f"0-{cap} goals ({cap}-goal cap)",
            risk=risk,
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
