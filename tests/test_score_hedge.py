"""Correct-score grid staking: risk blend, live reachability, and report squares."""

from __future__ import annotations

import re

import pytest

from soccer_prediction.example.fixture_example import build_forecast
from soccer_prediction.reporting.html_score_hedge import _live_split, score_hedge_section
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


def test_flat_risk_returns_the_same_for_every_covered_score() -> None:
    """At risk 0 the stakes are price-proportional, so every payout is identical."""
    quotes = _grid({(0, 0): 0.25, (1, 0): 0.25, (0, 1): 0.10})
    plan = build_grid_hedge(quotes, bankroll=100.0, max_goals=1, risk=0.0)
    payouts = {round(stake.payout_if_hit, 6) for stake in plan.stakes}
    assert len(payouts) == 1  # one identical payout across all covered scores
    assert plan.guaranteed_return == pytest.approx(plan.max_return)
    assert sum(stake.stake for stake in plan.stakes) == pytest.approx(100.0)
    # Cheaper scores take a smaller slice of the bankroll.
    by_score = {stake.label: stake.stake for stake in plan.stakes}
    assert by_score["0-1"] < by_score["0-0"]


def test_full_risk_biases_stakes_toward_the_model() -> None:
    """At risk 1 stakes follow probability, so payouts spread and the mode pays more."""
    quotes = [
        ScoreQuote(0, 0, price=0.25, probability=0.10),
        ScoreQuote(1, 0, price=0.25, probability=0.10),
        ScoreQuote(0, 1, price=0.10, probability=0.30),  # cheap but likely
    ]
    flat = build_grid_hedge(quotes, bankroll=100.0, max_goals=1, risk=0.0)
    biased = build_grid_hedge(quotes, bankroll=100.0, max_goals=1, risk=1.0)
    # Flat pays the same everywhere; biased fans the payouts out.
    assert flat.max_return == pytest.approx(flat.guaranteed_return)
    assert biased.max_return > biased.guaranteed_return
    # Leaning on the model lifts expected value (the model sees value the price misses).
    assert biased.expected_profit > flat.expected_profit
    # The likeliest score is staked more heavily under full risk than flat.
    flat_01 = next(s for s in flat.stakes if s.label == "0-1").stake
    biased_01 = next(s for s in biased.stakes if s.label == "0-1").stake
    assert biased_01 > flat_01


def test_risk_default_is_between_the_extremes() -> None:
    """The default plan sits between flat and full-model on every headline number."""
    grid = load_packaged_score_grid("correct_score_argentina_england.yaml")
    flat = build_grid_hedges(grid, caps=(2,), risk=0.0)[0]
    mid = build_grid_hedges(grid, caps=(2,))[0]  # default risk
    full = build_grid_hedges(grid, caps=(2,), risk=1.0)[0]
    assert flat.max_return <= mid.max_return <= full.max_return
    assert flat.guaranteed_return >= mid.guaranteed_return >= full.guaranteed_return
    assert flat.expected_profit <= mid.expected_profit <= full.expected_profit


def test_arbitrage_needs_every_covered_score_to_clear_the_stake() -> None:
    """Prices summing under 1.0 are an arbitrage only while the payout stays flat."""
    quotes = _grid({(0, 0): 0.2, (1, 0): 0.2, (0, 1): 0.2})  # sum 0.6
    flat = build_grid_hedge(quotes, bankroll=300.0, max_goals=1, risk=0.0)
    assert flat.is_true_arbitrage
    assert flat.guaranteed_return == pytest.approx(500.0)  # 300 / 0.6
    # Biasing the money can drop the worst covered score below the stake, killing
    # the guarantee even though the prices still sum under 1.0.
    biased = build_grid_hedge(
        [
            ScoreQuote(0, 0, price=0.2, probability=0.02),
            ScoreQuote(1, 0, price=0.2, probability=0.02),
            ScoreQuote(0, 1, price=0.2, probability=0.50),
        ],
        bankroll=300.0,
        max_goals=1,
        risk=1.0,
    )
    assert not biased.is_true_arbitrage
    assert biased.guaranteed_profit < 0.0


def test_no_arbitrage_when_prices_sum_above_one() -> None:
    """An overpriced book returns less than stake even on a covered win."""
    quotes = _grid({(0, 0): 0.5, (1, 0): 0.5, (0, 1): 0.3})  # sum 1.3
    plan = build_grid_hedge(quotes, bankroll=100.0, max_goals=1, risk=0.0)
    assert not plan.is_true_arbitrage
    assert plan.guaranteed_profit < 0.0


def test_expected_profit_uses_outcome_probabilities() -> None:
    """A grid that rarely contains the real score has negative expected profit."""
    quotes = [
        ScoreQuote(0, 0, price=0.2, probability=0.05),
        ScoreQuote(1, 0, price=0.2, probability=0.05),
        ScoreQuote(0, 1, price=0.2, probability=0.05),
    ]
    plan = build_grid_hedge(quotes, bankroll=300.0, max_goals=1, risk=0.0)
    assert plan.is_true_arbitrage  # price-wise
    assert plan.covered_probability == pytest.approx(0.15)
    assert plan.expected_profit < 0.0  # but a losing bet once outcomes are weighted


def test_goal_cap_selects_the_grid() -> None:
    """A tighter cap covers fewer scores and pays more per covered hit (flat risk)."""
    quotes = _grid({(0, 0): 0.2, (2, 2): 0.1, (3, 0): 0.05})
    wide = build_grid_hedge(quotes, bankroll=100.0, max_goals=3, risk=0.0)
    tight = build_grid_hedge(quotes, bankroll=100.0, max_goals=2, risk=0.0)
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
    """The packaged ENG/ARG grid yields the flat 0-3 and 0-2 plans."""
    grid = load_packaged_score_grid("correct_score_argentina_england.yaml")
    assert grid.home == "England" and grid.away == "Argentina"
    assert len(grid.quotes) == 25  # the full 0-4 grid
    plan_three, plan_two = build_grid_hedges(grid, caps=(3, 2), risk=0.0)
    assert len(plan_three.stakes) == 16
    assert len(plan_two.stakes) == 9
    assert plan_two.guaranteed_return > plan_three.guaranteed_return
    # Every score inside the 0-3 grid was read off a screenshot; only the six
    # never-visible 4-goal scores are assumed.
    assert not any(stake.estimated_price for stake in plan_three.stakes)
    plan_four = build_grid_hedges(grid, caps=(4,), risk=0.0)[0]
    assumed = {stake.label for stake in plan_four.stakes if stake.estimated_price}
    assert assumed == {"4-0", "4-1", "4-3", "4-4", "0-4", "3-4"}
    # At the displayed prices the flat 0-3 grid is just past break-even while the
    # tighter 0-2 grid still clears it.
    assert plan_three.total_price > 1.0
    assert not plan_three.is_true_arbitrage
    assert plan_three.guaranteed_profit < 0.0
    assert plan_two.is_true_arbitrage
    assert 0.0 < plan_two.guaranteed_profit < 30.0  # a sliver, not the $184 my bad estimates implied
    assert plan_three.expected_profit < 0.0
    assert plan_two.expected_profit < 0.0


def test_report_section_renders_all_grids_and_sliders() -> None:
    """The section renders for ENG/ARG with a risk slider per grid."""
    section = score_hedge_section(build_forecast(key="argentina_england", live=False))
    assert "Score-grid staking plans" in section
    for cap in (1, 2, 3, 4):
        assert f"0-{cap} grid" in section
        assert f'data-cap="{cap}"' in section  # slider + live-recompute hooks
    assert section.count('class="risk-slider"') == 4
    assert "All grids at a glance" in section
    assert "Most you can lose" in section
    assert "Worst net (covered)" in section
    assert "Best net (covered)" in section


def test_unpriced_fixture_explains_itself_instead_of_vanishing() -> None:
    """A fixture with no bundled quotes says so, and names the file it would need."""
    section = score_hedge_section(build_forecast(key="spain_france", live=False))
    assert "Score-grid staking plans" in section  # the heading still appears
    assert "No market prices are bundled" in section
    assert "correct_score_spain_france.yaml" in section
    # It must not invent a plan or a slider out of model probabilities.
    assert "sc-score" not in section
    assert "risk-slider" not in section


def test_each_grid_renders_as_a_square_matrix() -> None:
    """Every plan is laid out as a (cap+1) x (cap+1) score square with both axes."""
    section = score_hedge_section(build_forecast(key="argentina_england", live=False))
    for cap in (1, 2, 3, 4):
        block = section.split(f"0-{cap} grid")[1].split("hedge-summary")[0]
        assert len(re.findall(r'class="scell prob', block)) == (cap + 1) ** 2
        assert len(re.findall(r'class="scell axis"', block)) == 2 * (cap + 1)
    assert "England goals" in section and "Argentina goals" in section


def test_each_tile_matches_its_rendered_plan() -> None:
    """Every tile's bet and win equal the default-risk plan's own numbers."""
    section = score_hedge_section(build_forecast(key="argentina_england", live=False))
    grid = load_packaged_score_grid("correct_score_argentina_england.yaml")
    plans = {plan.max_goals: plan for plan in build_grid_hedges(grid, caps=(1, 2, 3, 4))}
    tile_re = re.compile(
        r'class="sc-score">(\d-\d)<.*?class="sc-bet">bet \$([\d.]+)<'
        r'.*?class="sc-win">win \$([\d.]+)<.*?class="sc-loss">this -\$([\d.]+)<',
        re.DOTALL,
    )
    for cap, plan in plans.items():
        block = section.split(f"0-{cap} grid")[1].split("hedge-summary")[0]
        tiles = tile_re.findall(block)
        assert len(tiles) == (cap + 1) ** 2
        by_label = {stake.label: stake for stake in plan.stakes}
        for label, bet, win, own_loss in tiles:
            stake = by_label[label]
            assert float(bet) == pytest.approx(stake.stake, abs=0.01)
            assert float(win) == pytest.approx(stake.payout_if_hit, abs=0.01)
            assert float(own_loss) == pytest.approx(stake.stake, abs=0.01)


def test_live_split_reports_dead_stake_and_reachable_net_range() -> None:
    """From 2-0, 0-x/1-x cells are dead; POSSIBLE is the (min, max) reachable net."""
    grid = load_packaged_score_grid("correct_score_argentina_england.yaml")
    plan = build_grid_hedges(grid, caps=(2,))[0]  # default risk
    stakes = {(s.home_goals, s.away_goals): s for s in plan.stakes}
    dead, net_range = _live_split(stakes, 2, 0)
    expected_dead = sum(stakes[c].stake for c in [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)])
    reachable = [stakes[c].profit_if_hit for c in [(2, 1), (2, 2)]]
    assert dead == pytest.approx(expected_dead, abs=0.01)
    assert net_range is not None
    assert net_range[0] == pytest.approx(min(reachable), abs=0.01)
    assert net_range[1] == pytest.approx(max(reachable), abs=0.01)
    # At 0-0 nothing is dead yet; at the far corner no other score can follow.
    assert _live_split(stakes, 0, 0)[0] == pytest.approx(0.0)
    assert _live_split(stakes, 2, 2)[1] is None


def test_flat_risk_makes_the_reachable_range_a_single_point() -> None:
    """At risk 0 every reachable net is equal, so min == max (the user's +$16.28 case)."""
    grid = load_packaged_score_grid("correct_score_argentina_england.yaml")
    plan = build_grid_hedges(grid, caps=(2,), risk=0.0)[0]
    stakes = {(s.home_goals, s.away_goals): s for s in plan.stakes}
    _dead, net_range = _live_split(stakes, 1, 1)
    assert net_range is not None
    lo, hi = net_range
    assert lo == pytest.approx(hi, abs=0.01)  # flat: one number, not a spread
    assert lo == pytest.approx(plan.guaranteed_profit, abs=0.01)


def test_dead_plus_reachable_stakes_reconstruct_the_bankroll() -> None:
    """LOST stake + this cell's stake + reachable stakes always sum to the bankroll."""
    grid = load_packaged_score_grid("correct_score_argentina_england.yaml")
    plan = build_grid_hedges(grid, caps=(3,))[0]
    stakes = {(s.home_goals, s.away_goals): s for s in plan.stakes}
    for (home, away), stake in stakes.items():
        dead, _best = _live_split(stakes, home, away)
        reachable = sum(
            other.stake
            for (oh, oa), other in stakes.items()
            if (oh, oa) != (home, away) and oh >= home and oa >= away
        )
        assert dead + stake.stake + reachable == pytest.approx(plan.bankroll, abs=0.02)


def test_far_corner_tile_shows_possible_none() -> None:
    """The top-corner score has nothing left to play for, shown as POSSIBLE none."""
    section = score_hedge_section(build_forecast(key="argentina_england", live=False))
    block = section.split("0-2 grid")[1].split("hedge-summary")[0]
    corner = block.split('data-h="2" data-a="2"')[1].split("</div>")
    joined = "".join(corner[:8])
    assert "POSSIBLE none" in joined


def test_cells_are_shaded_by_probability() -> None:
    """The likeliest score is the most saturated cell; longshots fade toward white."""
    section = score_hedge_section(build_forecast(key="argentina_england", live=False))
    block = section.split("0-4 grid")[1].split("hedge-summary")[0]
    shaded = [
        (int(strength), float(probability))
        for strength, probability in re.findall(
            r'--strength:(\d+)%" title="\d-\d[^(]*\(probability ([\d.]+)%', block
        )
    ]
    assert len(shaded) == 25
    by_probability = [item[0] for item in sorted(shaded, key=lambda item: -item[1])]
    assert by_probability == sorted(by_probability, reverse=True)
    assert max(by_probability) > 80  # peak score is solidly blue
    assert min(by_probability) < 15  # rarest score is nearly white
    assert "sgrid-gradient" in section  # colour legend accompanies the squares
