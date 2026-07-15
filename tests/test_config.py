"""T03 acceptance: env variables override YAML defaults; no secrets in source."""

from __future__ import annotations

import pytest

from soccer_prediction.config import load_config


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """An env var overrides the packaged YAML default."""
    monkeypatch.setenv("SOCCER_PREDICTION_MODEL_MAX_GOALS", "5")
    monkeypatch.setenv("SOCCER_PREDICTION_MODEL_SCENARIO_SIMULATIONS", "2500")
    monkeypatch.setenv("SOCCER_PREDICTION_MODEL_OPPONENT_NETWORK_DEPTH", "2")
    monkeypatch.setenv("SOCCER_PREDICTION_MODEL_MORALE_MAX_EFFECT", "0.05")
    monkeypatch.setenv("SOCCER_PREDICTION_API_FOOTBALL_KEY", "secret-from-env")
    config = load_config()
    assert config.model.max_goals == 5
    assert config.model.scenario_simulations == 2500
    assert config.model.opponent_network_depth == 2
    assert config.model.morale_max_effect == 0.05
    assert config.api_football.api_key == "secret-from-env"


def test_defaults_have_no_secret() -> None:
    """The default API key is empty, never a hard-coded secret."""
    monkeypatch_free = load_config()
    assert monkeypatch_free.api_football.api_key == ""
    assert monkeypatch_free.model.max_goals == 8


def test_network_rating_defaults() -> None:
    """The graph-strength knobs load with sane, bounded defaults."""
    model = load_config().model
    assert model.network_rating_method == "mle"
    assert model.network_confidence_prior >= 0.0
    assert 0.0 <= model.shared_opponent_weight <= 0.6
    assert 0.0 <= model.shared_opponent_hop_decay <= 1.0
    assert model.shared_opponent_max_hops >= 2


def test_network_rating_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env variables override the graph-strength knobs and unknown methods fall back."""
    monkeypatch.setenv("SOCCER_PREDICTION_MODEL_NETWORK_RATING_METHOD", "heuristic")
    monkeypatch.setenv("SOCCER_PREDICTION_MODEL_SHARED_OPPONENT_WEIGHT", "0.25")
    monkeypatch.setenv("SOCCER_PREDICTION_MODEL_SHARED_OPPONENT_MAX_HOPS", "4")
    model = load_config().model
    assert model.network_rating_method == "heuristic"
    assert model.shared_opponent_weight == 0.25
    assert model.shared_opponent_max_hops == 4

    monkeypatch.setenv("SOCCER_PREDICTION_MODEL_NETWORK_RATING_METHOD", "nonsense")
    assert load_config().model.network_rating_method == "mle"
