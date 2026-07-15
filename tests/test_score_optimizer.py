"""Log-optimal (Kelly) staking: threshold math, blending, tail, and edge cases."""

from __future__ import annotations

import math

import pytest

from soccer_prediction.strategy.score_optimizer import (
    ASK_SPREAD,
    ScoreOutcome,
    blend_probabilities,
    build_outcomes,
    load_packaged_market,
    optimize_market,
    optimize_stakes,
)


def _outcome(label: str, ask: float, probability: float, *, tradeable: bool = True) -> ScoreOutcome:
    return ScoreOutcome(
        label=label,
        ask=ask,
        model_probability=probability,
        market_probability=probability,
        probability=probability,
        tradeable=tradeable,
    )


def test_matches_closed_form_kelly_for_an_even_money_bet() -> None:
    """A 60/40 even-money edge stakes exactly the Kelly fraction 2p-1 = 20%."""
    outcomes = [_outcome("win", 0.5, 0.6), _outcome("lose", 0.5, 0.4, tradeable=False)]
    plan = optimize_stakes(outcomes, bankroll=1000.0)
    assert plan.staked == pytest.approx(200.0, abs=1e-6)
    assert plan.cash_reserve == pytest.approx(800.0, abs=1e-6)


def test_holds_all_cash_when_nothing_is_positive_edge() -> None:
    """With no +EV outcome anywhere, lambda stays at 1 and nothing is staked."""
    outcomes = [
        _outcome("a", 0.50, 0.40),
        _outcome("b", 0.50, 0.30),
        _outcome("tail", 1.0, 0.30, tradeable=False),
    ]
    plan = optimize_stakes(outcomes, bankroll=1000.0)
    assert plan.allocations == ()
    assert plan.staked == 0.0
    assert plan.cash_reserve == pytest.approx(1000.0)
    assert plan.expected_profit == pytest.approx(0.0)


def test_pure_arbitrage_is_fully_staked() -> None:
    """Two complementary outcomes priced at 0.40 each are a guaranteed 25% gain."""
    outcomes = [_outcome("a", 0.4, 0.5), _outcome("b", 0.4, 0.5)]
    plan = optimize_stakes(outcomes, bankroll=1000.0)
    assert plan.staked == pytest.approx(1000.0)
    assert plan.cash_reserve == pytest.approx(0.0, abs=1e-9)
    for allocation in plan.allocations:
        assert allocation.wealth_if_hit == pytest.approx(1250.0)  # same payout either way


def test_fraction_scales_toward_cash() -> None:
    """Half-Kelly stakes half as much and keeps the rest in cash."""
    outcomes = [_outcome("win", 0.5, 0.6), _outcome("lose", 0.5, 0.4, tradeable=False)]
    full = optimize_stakes(outcomes, bankroll=1000.0, fraction=1.0)
    half = optimize_stakes(outcomes, bankroll=1000.0, fraction=0.5)
    assert half.staked == pytest.approx(full.staked / 2.0)
    assert half.cash_reserve > full.cash_reserve


def test_growth_is_positive_for_an_edge_and_zero_when_flat() -> None:
    """Expected log growth is positive with an edge and exactly zero with no bet."""
    edge = optimize_stakes(
        [_outcome("win", 0.5, 0.6), _outcome("lose", 0.5, 0.4, tradeable=False)], bankroll=1000.0
    )
    assert edge.expected_log_growth > 0.0
    # 0.6*log(1.2) + 0.4*log(0.8) is the textbook growth rate for this bet.
    assert edge.expected_log_growth == pytest.approx(
        0.6 * math.log(1.2) + 0.4 * math.log(0.8), abs=1e-9
    )
    flat = optimize_stakes(
        [_outcome("a", 0.5, 0.4), _outcome("t", 1.0, 0.6, tradeable=False)], bankroll=1000.0
    )
    assert flat.expected_log_growth == pytest.approx(0.0)


def test_blending_moves_between_model_and_market() -> None:
    """model_trust=1 keeps the model; 0 hands the estimate to the market prices."""
    model = [0.5, 0.3]
    asks = [0.2, 0.6]
    pure_model = blend_probabilities(model, asks, model_trust=1.0, listed_mass=0.8)
    pure_market = blend_probabilities(model, asks, model_trust=0.0, listed_mass=0.8)
    assert pure_model == pytest.approx(model)
    # Market view is asks normalized to the same mass: 0.2/0.8*0.8 and 0.6/0.8*0.8.
    assert pure_market == pytest.approx([0.2, 0.6])
    mixed = blend_probabilities(model, asks, model_trust=0.5, listed_mass=0.8)
    assert mixed == pytest.approx([0.35, 0.45])


def test_trusting_the_market_finds_no_edge() -> None:
    """At model_trust=0 probabilities track prices, so nothing is worth staking."""
    market = load_packaged_market("correct_score_argentina_england.yaml")
    plan = optimize_market(market, model_trust=0.0)
    assert plan.allocations == ()
    assert plan.cash_reserve == pytest.approx(plan.bankroll)


def test_residual_tail_is_always_present_and_untradeable() -> None:
    """Unlisted scores become a residual outcome, so nothing is assumed impossible."""
    market = load_packaged_market("correct_score_argentina_england.yaml")
    outcomes = build_outcomes(market, model_trust=0.5)
    residual = [outcome for outcome in outcomes if not outcome.tradeable]
    assert len(residual) == 1
    assert residual[0].probability > 0.0  # the tail is real, never zero
    assert sum(outcome.probability for outcome in outcomes) == pytest.approx(1.0, abs=1e-6)
    # Every listed outcome keeps a non-zero probability and price.
    assert all(outcome.probability > 0.0 and outcome.ask > 0.0 for outcome in outcomes)


def test_prices_default_to_the_displayed_market_percentage() -> None:
    """By default every score is priced at the figure actually shown in the app."""
    market = load_packaged_market("correct_score_argentina_england.yaml")
    outcomes = {item.label: item for item in build_outcomes(market, model_trust=1.0)}
    assert outcomes["1-1"].ask == pytest.approx(0.16)  # displayed, not marked up
    assert outcomes["0-3"].ask == pytest.approx(0.02)
    assert outcomes["3-3"].ask == pytest.approx(0.01)


def test_spread_is_an_opt_in_sensitivity() -> None:
    """Passing a spread switches to quoted asks / marked-up fills for a worst case."""
    market = load_packaged_market("correct_score_argentina_england.yaml")
    outcomes = {
        item.label: item for item in build_outcomes(market, model_trust=1.0, spread=ASK_SPREAD)
    }
    assert outcomes["0-3"].ask == pytest.approx(0.031)  # payout-quoted ($20 -> $645)
    assert outcomes["3-3"].ask == pytest.approx(0.0205)  # payout-quoted ($100 -> $4,879)
    assert outcomes["1-1"].ask == pytest.approx(0.16 + ASK_SPREAD)  # displayed + spread
    # Pessimistic fills can only shrink the staked edge, never grow it.
    optimistic = optimize_market(market, model_trust=1.0)
    pessimistic = optimize_market(market, model_trust=1.0, spread=ASK_SPREAD)
    assert pessimistic.staked < optimistic.staked


def test_real_market_stakes_little_and_keeps_most_in_cash() -> None:
    """Fully trusting the model still backs only a small slice, never a grid cover."""
    market = load_packaged_market("correct_score_argentina_england.yaml")
    plan = optimize_market(market, model_trust=1.0)
    assert 0.0 < plan.staked < 0.20 * plan.bankroll  # ~$12 of $100, not a grid cover
    assert plan.expected_profit > 0.0
    # The heaviest edges are the Argentina blowouts the market underprices.
    best = max(plan.allocations, key=lambda item: item.ratio)
    assert best.label in {"1-4", "0-3", "1-3"}


def test_marginal_outcomes_are_admitted_only_as_hedges_below_lambda() -> None:
    """Every stake beats the cash rate lambda, which is what Kelly actually requires.

    Admission is ``p/ask > lambda`` (cash held), not ``p/ask > 1``: once the plan
    holds +EV positions lambda falls under 1, so a slightly -EV score can earn a
    small hedging stake. Nothing below lambda is ever funded.
    """
    market = load_packaged_market("correct_score_argentina_england.yaml")
    plan = optimize_market(market, model_trust=1.0)
    lam = plan.cash_reserve / plan.bankroll
    assert lam < 1.0  # positions exist, so the bar sits below break-even
    assert all(item.ratio > lam for item in plan.allocations)
    assert all(item.ratio <= lam for item in plan.skipped if item.tradeable)
    # Some funded cells are genuinely below break-even -- held purely as hedges.
    assert any(item.ratio < 1.0 for item in plan.allocations)


def test_less_trust_in_the_model_means_less_money_at_risk() -> None:
    """Staking shrinks monotonically as the market is given more of the say."""
    market = load_packaged_market("correct_score_argentina_england.yaml")
    staked = [
        optimize_market(market, model_trust=trust).staked for trust in (1.0, 0.75, 0.5, 0.25, 0.0)
    ]
    assert staked == sorted(staked, reverse=True)
    assert staked[-1] == 0.0  # trusting the market entirely finds no edge at all


def test_bad_inputs_raise() -> None:
    """A non-positive bankroll or an all-untradeable space is rejected."""
    with pytest.raises(ValueError):
        optimize_stakes([_outcome("a", 0.5, 0.6)], bankroll=0.0)
    with pytest.raises(ValueError):
        optimize_stakes([_outcome("t", 1.0, 1.0, tradeable=False)], bankroll=100.0)
