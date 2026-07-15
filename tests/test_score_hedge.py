"""Correct-score grid hedging: equal payout, probability-weighted EV, zero-safety."""

from __future__ import annotations

import pytest

from soccer_prediction.example.fixture_example import build_forecast
from soccer_prediction.reporting.html_score_hedge import score_hedge_section
from soccer_prediction.strategy import (
    ScoreQuote,
    build_grid_hedge,
    build_grid_hedges,
    load_packaged_score_grid,
)


def _grid(prices: dict[tuple[int, int], float], prob: float = 0.05) -> list[ScoreQuote]:
    return [
        ScoreQuote(home_goals=h, away_goals=a, price=price, probability=prob)
        for (h, a), price in prices.items()
    ]


def test_equal_payout_returns_same_for_every_covered_score() -> None:
    """Stakes are set so any covered score returns the identical payout."""
    quotes = _grid({(0, 0): 0.25, (1, 0): 0.25, (0, 1): 0.10})
    plan = build_grid_hedge(quotes, bankroll=100.0, max_goals=1)
    payouts = {round(stake.payout_if_hit, 6) for stake in plan.stakes}
    assert len(payouts) == 1  # one identical payout across all covered scores
    assert abs(sum(stake.stake for stake in plan.stakes) - 100.0) < 1e-6
    # Cheaper scores take a smaller slice of the bankroll.
    by_score = {stake.label: stake.stake for stake in plan.stakes}
    assert by_score["0-1"] < by_score["0-0"]


def test_true_arbitrage_when_prices_sum_below_one() -> None:
    """Prices summing under 1.0 guarantee a profit on any covered score."""
    quotes = _grid({(0, 0): 0.2, (1, 0): 0.2, (0, 1): 0.2})  # sum 0.6
    plan = build_grid_hedge(quotes, bankroll=300.0, max_goals=1)
    assert plan.is_true_arbitrage
    assert plan.guaranteed_profit > 0.0
    assert plan.guaranteed_return == pytest.approx(500.0)  # 300 / 0.6


def test_no_arbitrage_when_prices_sum_above_one() -> None:
    """An overpriced book returns less than stake even on a covered win."""
    quotes = _grid({(0, 0): 0.5, (1, 0): 0.5, (0, 1): 0.3})  # sum 1.3
    plan = build_grid_hedge(quotes, bankroll=100.0, max_goals=1)
    assert not plan.is_true_arbitrage
    assert plan.guaranteed_profit < 0.0


def test_expected_profit_uses_outcome_probabilities() -> None:
    """A grid that rarely contains the real score has negative expected profit."""
    # Prices sum < 1 (looks like a guaranteed win) but the covered scores are unlikely.
    quotes = [
        ScoreQuote(0, 0, price=0.2, probability=0.05),
        ScoreQuote(1, 0, price=0.2, probability=0.05),
        ScoreQuote(0, 1, price=0.2, probability=0.05),
    ]
    plan = build_grid_hedge(quotes, bankroll=300.0, max_goals=1)
    assert plan.is_true_arbitrage  # price-wise
    assert plan.covered_probability == pytest.approx(0.15)
    assert plan.expected_profit < 0.0  # but a losing bet once outcomes are weighted


def test_goal_cap_selects_the_grid() -> None:
    """A tighter cap covers fewer scores and pays more per covered hit."""
    quotes = _grid({(0, 0): 0.2, (2, 2): 0.1, (3, 0): 0.05})
    wide = build_grid_hedge(quotes, bankroll=100.0, max_goals=3)
    tight = build_grid_hedge(quotes, bankroll=100.0, max_goals=2)
    assert len(tight.stakes) < len(wide.stakes)
    assert tight.guaranteed_return > wide.guaranteed_return  # fewer scores => bigger payout


def test_nothing_is_treated_as_zero() -> None:
    """A zero price or probability is floored, never dropped or divided-by-zero."""
    quotes = [ScoreQuote(0, 0, price=0.0, probability=0.0)]
    plan = build_grid_hedge(quotes, bankroll=50.0, max_goals=0)
    assert plan.stakes[0].price > 0.0
    assert plan.stakes[0].probability > 0.0
    assert plan.guaranteed_return > 0.0


def test_bad_inputs_raise() -> None:
    """Non-positive bankroll or an empty grid is rejected."""
    quotes = _grid({(0, 0): 0.2})
    with pytest.raises(ValueError):
        build_grid_hedge(quotes, bankroll=0.0, max_goals=0)
    with pytest.raises(ValueError):
        build_grid_hedge([], bankroll=100.0, max_goals=3)


def test_bundled_argentina_england_grid_loads_and_plans() -> None:
    """The packaged ENG/ARG grid yields the 0-3 and 0-2 plans over $500."""
    grid = load_packaged_score_grid("correct_score_argentina_england.yaml")
    assert grid.home == "England" and grid.away == "Argentina"
    assert len(grid.quotes) == 16
    plan_three, plan_two = build_grid_hedges(grid, caps=(3, 2))
    assert len(plan_three.stakes) == 16
    assert len(plan_two.stakes) == 9
    assert plan_two.guaranteed_return > plan_three.guaranteed_return
    # Every price is now a real market quote; none are model-filled.
    assert not any(stake.estimated_price for stake in plan_three.stakes)
    # At the real 11% prices for 0-0/1-0/0-1 the full 0-3 grid is priced out of
    # arbitrage (sum > 1.00) while the tighter 0-2 grid still clears it.
    assert plan_three.total_price > 1.0
    assert not plan_three.is_true_arbitrage
    assert plan_three.guaranteed_profit < 0.0
    assert plan_two.is_true_arbitrage
    assert plan_two.guaranteed_profit > 0.0
    # Both are still negative once the chance of an uncovered score is priced in.
    assert plan_three.expected_profit < 0.0
    assert plan_two.expected_profit < 0.0


def test_report_section_appears_only_with_a_price_grid() -> None:
    """The hedge section renders for ENG/ARG and is absent for fixtures without a grid."""
    forecast = build_forecast(key="argentina_england", live=False)
    section = score_hedge_section(forecast)
    assert "Guaranteed-win score hedge" in section
    assert "0-2 goals" in section
    assert "Expected profit" in section
    other = build_forecast(key="spain_france", live=False)
    assert score_hedge_section(other) == ""
