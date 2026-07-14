"""Fixture-YAML market optimization coverage."""

from __future__ import annotations

from soccer_prediction.example.fixture_example import build_forecast
from soccer_prediction.reporting.html_confident_bets import confident_bets_section
from soccer_prediction.reporting.market_optimizer import optimize_fixture_markets


def test_spain_france_uses_price_aware_plan() -> None:
    forecast = build_forecast(key="spain_france", live=False)
    plan = optimize_fixture_markets(forecast)
    assert plan is not None
    assert plan.source == "market_prices_spain_france.yaml"
    assert abs(plan.profit_weight + plan.risk_weight - 1.0) < 1e-9
    assert plan.profit_weight > plan.risk_weight  # default file favours return
    assert plan.allocations
    assert len(plan.allocations) <= 6
    assert all(item.edge > 0.01 for item in plan.allocations)
    assert all(item.model_probability >= 0.20 for item in plan.allocations)
    assert all(item.stake <= 28.00 + 1e-6 for item in plan.allocations)
    assert abs(sum(item.stake for item in plan.allocations) - 95.00) <= 0.05
    assert [item.stake for item in plan.allocations] == sorted(
        (item.stake for item in plan.allocations), reverse=True
    )
    assert any(item.selection == "Spain" and item.category == "Advance" for item in plan.allocations)
    assert not any(item.selection == "France" and item.category == "Advance" for item in plan.allocations)
    assert sum(item.expected_profit for item in plan.allocations) > 5.0


def test_weights_shift_allocation_toward_safety() -> None:
    """Raising risk_weight moves stake toward higher win-probability picks."""
    import soccer_prediction.reporting.market_optimizer as optimizer

    forecast = build_forecast(key="spain_france", live=False)
    _defaults, payload, source = optimizer._settings(forecast)
    candidates, _ = optimizer._collect_candidates(
        forecast, payload, fee_rate=0.0, min_edge=0.01, min_probability=0.20
    )
    candidates, _ = optimizer._dedupe_exposures(candidates)

    def _stake_weighted_win_prob(profit: float, risk: float) -> float:
        plan = optimizer.build_plan(
            candidates,
            source,
            bankroll=100.0,
            profit_weight=profit,
            risk_weight=risk,
            max_positions=6,
            max_position=28.0,
            reserve=5.0,
        )
        staked = sum(item.stake for item in plan.allocations)
        return sum(item.stake * item.model_probability for item in plan.allocations) / staked

    safety_first = _stake_weighted_win_prob(0.2, 0.8)
    profit_first = _stake_weighted_win_prob(0.8, 0.2)
    assert safety_first > profit_first


def test_price_aware_html_explains_contract_return() -> None:
    forecast = build_forecast(key="spain_france", live=False)
    html = confident_bets_section(forecast)
    assert "$100 price-aware bankroll" in html
    assert "market_prices_spain_france.yaml" in html
    assert "69.5% ROI" in html
    assert "Expected profit" in html
