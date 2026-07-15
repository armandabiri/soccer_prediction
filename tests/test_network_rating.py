"""Graph-based team strength: MLE rating, confidence shrinkage, shared opponents."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from soccer_prediction.features import compute_rates
from soccer_prediction.features.rates import (
    _mle_network_strengths,
    _recency_weight,
    _shrink_network_factors,
)
from soccer_prediction.models import TeamMatchStats
from soccer_prediction.predictors.poisson import expected_goals

_FETCHED_AT = datetime.now(UTC)


def _record(
    team: str,
    opponent: str,
    goals_for: int,
    goals_against: int,
    *,
    is_home: bool = True,
    match_date: date = date(2025, 1, 1),
) -> TeamMatchStats:
    return TeamMatchStats(
        team, opponent, match_date, is_home, goals_for, goals_against, 0, 0, 5, 5, 2, 0, "rating_test", _FETCHED_AT
    )


def _mirror(team: str, opponent: str, goals_for: int, goals_against: int, **kwargs: object) -> list[TeamMatchStats]:
    """Return both directed records for one match so the graph stays symmetric."""
    home = _record(team, opponent, goals_for, goals_against, **kwargs)  # type: ignore[arg-type]
    away = _record(opponent, team, goals_against, goals_for, is_home=False, match_date=home.date)
    return [home, away]


# A beat strong D (who thrashed F); Z only beat weak F. A should outrank Z.
_CHAIN_HISTORY = (
    *_mirror("A", "D", 1, 0),
    *_mirror("D", "F", 4, 0),
    *_mirror("Z", "F", 1, 0),
)


def test_mle_rating_propagates_opponent_strength() -> None:
    """Beating a strong side lifts attack more than beating a weak one."""
    rates = compute_rates(_CHAIN_HISTORY)
    assert rates.attack_for("A") > rates.attack_for("Z")
    assert rates.defence_weakness_for("F") > rates.defence_weakness_for("D")


def test_mle_rating_converges_and_centers_on_one() -> None:
    """The estimator anchors unseen strength at the neutral factor 1.0."""
    weighted = [(record, _recency_weight((date(2025, 1, 1) - record.date).days)) for record in _CHAIN_HISTORY]
    attack, defence = _mle_network_strengths(weighted, league_rate=1.2, prior_weight=4.0)
    # Geometric mean of attack is canonicalized to 1.0 (scale is identifiable).
    product = 1.0
    for value in attack.values():
        product *= value
    assert round(product ** (1.0 / len(attack)), 6) == 1.0
    assert all(0.35 <= value <= 2.5 for value in {**attack, **defence}.values())


def test_confidence_shrinkage_pulls_thin_teams_toward_neutral() -> None:
    """The same raw factor is trusted less for a team with fewer matches."""
    attack = {"rich": 1.6, "thin": 1.6}
    defence = {"rich": 1.0, "thin": 1.0}
    confidence = {"rich": 20.0, "thin": 1.0}
    shrunk_attack, _ = _shrink_network_factors(attack, defence, confidence, confidence_prior=4.0)
    assert shrunk_attack["rich"] > shrunk_attack["thin"]
    assert shrunk_attack["thin"] < 1.6  # pulled toward 1.0
    # Disabling the prior leaves factors untouched.
    same_attack, _ = _shrink_network_factors(attack, defence, confidence, confidence_prior=0.0)
    assert same_attack == attack


def test_shared_opponent_signal_reads_transitive_edge() -> None:
    """A common opponent that home beat and away lost to favours home."""
    # Home drew nobody directly with Away; both met bridge B.
    history = (
        *_mirror("Home", "B", 3, 0),  # Home smashed B
        *_mirror("Away", "B", 0, 2),  # Away lost to B
    )
    rates = compute_rates(history)
    signal = rates.shared_opponent_signal("Home", "Away")
    assert signal is not None
    implied_home, implied_away, evidence = signal
    assert implied_home > implied_away
    assert evidence > 0.0
    # No connection at all -> no signal.
    assert rates.shared_opponent_signal("Home", "Ghost") is None


def test_shared_opponent_signal_discounts_longer_chains() -> None:
    """A two-edge bridge carries more evidence than a three-edge chain."""
    direct = compute_rates((*_mirror("H", "B", 2, 0), *_mirror("A", "B", 0, 2)))
    longer = compute_rates(
        (*_mirror("H", "B", 2, 0), *_mirror("B", "C", 1, 1), *_mirror("A", "C", 0, 2))
    )
    near = direct.shared_opponent_signal("H", "A")
    far = longer.shared_opponent_signal("H", "A", hop_decay=0.5)
    assert near is not None and far is not None
    assert near[2] > far[2]  # closer bridge is stronger evidence


def test_shared_opponents_shift_goal_expectations() -> None:
    """The transitive hint nudges lambdas when the two sides never met directly."""
    history = (
        *_mirror("Home", "Bridge", 3, 0),
        *_mirror("Away", "Bridge", 0, 3),
    )
    rates = compute_rates(history)
    home_lambda, away_lambda = expected_goals(rates, "Home", "Away", neutral_venue=True)
    assert home_lambda > away_lambda


def test_shared_opponent_blend_is_config_gated(monkeypatch: pytest.MonkeyPatch) -> None:
    """Setting the weight to zero removes the shared-opponent influence."""
    history = (
        *_mirror("Home", "Bridge", 3, 0),
        *_mirror("Away", "Bridge", 0, 3),
    )
    monkeypatch.setenv("SOCCER_PREDICTION_MODEL_SHARED_OPPONENT_WEIGHT", "0.0")
    rates = compute_rates(history)
    with_gate_off = expected_goals(rates, "Home", "Away", neutral_venue=True)
    monkeypatch.setenv("SOCCER_PREDICTION_MODEL_SHARED_OPPONENT_WEIGHT", "0.4")
    rates_on = compute_rates(history)
    with_gate_on = expected_goals(rates_on, "Home", "Away", neutral_venue=True)
    assert with_gate_on[0] - with_gate_on[1] > with_gate_off[0] - with_gate_off[1]


def test_heuristic_method_still_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """The legacy estimator remains selectable and keeps the ordering."""
    monkeypatch.setenv("SOCCER_PREDICTION_MODEL_NETWORK_RATING_METHOD", "heuristic")
    rates = compute_rates(_CHAIN_HISTORY)
    assert rates.attack_for("A") > rates.attack_for("Z")


def test_recency_weight_discounts_old_chains() -> None:
    """Old matches contribute less confidence than recent ones."""
    old = date(2025, 1, 1) - timedelta(days=400)
    history = (*_mirror("A", "D", 1, 0), *_mirror("A", "E", 1, 0, match_date=old))
    rates = compute_rates(history, today=date(2025, 1, 1))
    assert rates.confidence_for("A") < 2.0  # two matches, but one heavily decayed
