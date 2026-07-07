"""T03 acceptance: env variables override YAML defaults; no secrets in source."""

from __future__ import annotations

import pytest

from soccer_prediction.config import load_config


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """An env var overrides the packaged YAML default."""
    monkeypatch.setenv("SOCCER_PREDICTION_MODEL_MAX_GOALS", "5")
    monkeypatch.setenv("SOCCER_PREDICTION_API_FOOTBALL_KEY", "secret-from-env")
    config = load_config()
    assert config.model.max_goals == 5
    assert config.api_football.api_key == "secret-from-env"


def test_defaults_have_no_secret() -> None:
    """The default API key is empty, never a hard-coded secret."""
    monkeypatch_free = load_config()
    assert monkeypatch_free.api_football.api_key == ""
    assert monkeypatch_free.model.max_goals == 8
