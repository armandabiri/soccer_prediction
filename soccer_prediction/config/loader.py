"""Configuration loading and environment overrides."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "AppConfig",
    "ApiFootballConfig",
    "CacheConfig",
    "ModelConfig",
    "example_usage",
    "load_config",
    "main",
]


@dataclass(frozen=True, slots=True)
class ApiFootballConfig:
    """API-Football settings."""

    api_key: str = ""
    host: str = "v3.football.api-sports.io"


@dataclass(frozen=True, slots=True)
class CacheConfig:
    """Cache settings."""

    dir: Path = Path(".cache/soccer_prediction")
    ttl_hours: int = 24


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """Model tuning knobs."""

    time_decay_xi: float = 0.0039
    recency_window_days: int = 730
    max_goals: int = 8
    scenario_simulations: int = 20_000
    random_seed: int = 2026
    opponent_network_depth: int = 1
    opponent_network_max_teams: int = 12
    morale_decay_xi: float = 0.0077
    morale_max_effect: float = 0.08
    rate_prior_weight: float = 4.0
    elite_defence_exponent: float = 0.85
    elite_tempo_strength: float = 0.08
    # Attack/defence rating estimator: "mle" (regularized Poisson maximum
    # likelihood) or "heuristic" (the legacy per-match-ratio fixed point).
    network_rating_method: str = "mle"
    # Shrink each team's network attack/defence factor toward neutral (1.0) by
    # its effective match weight; higher values distrust thinly-connected teams.
    network_confidence_prior: float = 2.0
    # Max blend weight of the shared-opponent (transitive) margin into goal
    # expectations; scales with connection evidence, fades out for rich data.
    shared_opponent_weight: float = 0.15
    # Per-extra-hop discount applied to indirect connection chains (0..1).
    shared_opponent_hop_decay: float = 0.5
    # Longest connection chain (edges) searched between the two teams.
    shared_opponent_max_hops: int = 3


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Top-level application configuration."""

    api_football: ApiFootballConfig = field(default_factory=ApiFootballConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    rate_limits: dict[str, int] = field(
        default_factory=lambda: {
            "api_football": 100,
            "football_data_csv": 0,
            "worldcup_open": 0,
            "statsbomb": 0,
        }
    )
    model: ModelConfig = field(default_factory=ModelConfig)


def _read_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {} if payload is None else dict(payload)


def _package_defaults() -> dict[str, Any]:
    defaults_path = resources.files(__package__).joinpath("defaults.yaml")
    payload = yaml.safe_load(defaults_path.read_text(encoding="utf-8"))
    return {} if payload is None else dict(payload)


def _merge(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), dict):
            merged[key] = _merge(dict(merged[key]), value)
        else:
            merged[key] = value
    return merged


def _apply_env(config: dict[str, Any]) -> dict[str, Any]:
    env_overrides = {
        ("api_football", "api_key"): os.getenv("SOCCER_PREDICTION_API_FOOTBALL_KEY"),
        ("api_football", "host"): os.getenv("SOCCER_PREDICTION_API_FOOTBALL_HOST"),
        ("cache", "dir"): os.getenv("SOCCER_PREDICTION_CACHE_DIR"),
        ("cache", "ttl_hours"): os.getenv("SOCCER_PREDICTION_CACHE_TTL_HOURS"),
        ("model", "time_decay_xi"): os.getenv("SOCCER_PREDICTION_MODEL_TIME_DECAY_XI"),
        ("model", "recency_window_days"): os.getenv("SOCCER_PREDICTION_MODEL_RECENCY_WINDOW_DAYS"),
        ("model", "max_goals"): os.getenv("SOCCER_PREDICTION_MODEL_MAX_GOALS"),
        ("model", "scenario_simulations"): os.getenv("SOCCER_PREDICTION_MODEL_SCENARIO_SIMULATIONS"),
        ("model", "random_seed"): os.getenv("SOCCER_PREDICTION_MODEL_RANDOM_SEED"),
        ("model", "opponent_network_depth"): os.getenv("SOCCER_PREDICTION_MODEL_OPPONENT_NETWORK_DEPTH"),
        ("model", "opponent_network_max_teams"): os.getenv("SOCCER_PREDICTION_MODEL_OPPONENT_NETWORK_MAX_TEAMS"),
        ("model", "morale_decay_xi"): os.getenv("SOCCER_PREDICTION_MODEL_MORALE_DECAY_XI"),
        ("model", "morale_max_effect"): os.getenv("SOCCER_PREDICTION_MODEL_MORALE_MAX_EFFECT"),
        ("model", "rate_prior_weight"): os.getenv("SOCCER_PREDICTION_MODEL_RATE_PRIOR_WEIGHT"),
        ("model", "elite_defence_exponent"): os.getenv("SOCCER_PREDICTION_MODEL_ELITE_DEFENCE_EXPONENT"),
        ("model", "elite_tempo_strength"): os.getenv("SOCCER_PREDICTION_MODEL_ELITE_TEMPO_STRENGTH"),
        ("model", "network_rating_method"): os.getenv("SOCCER_PREDICTION_MODEL_NETWORK_RATING_METHOD"),
        ("model", "network_confidence_prior"): os.getenv("SOCCER_PREDICTION_MODEL_NETWORK_CONFIDENCE_PRIOR"),
        ("model", "shared_opponent_weight"): os.getenv("SOCCER_PREDICTION_MODEL_SHARED_OPPONENT_WEIGHT"),
        ("model", "shared_opponent_hop_decay"): os.getenv("SOCCER_PREDICTION_MODEL_SHARED_OPPONENT_HOP_DECAY"),
        ("model", "shared_opponent_max_hops"): os.getenv("SOCCER_PREDICTION_MODEL_SHARED_OPPONENT_MAX_HOPS"),
        ("rate_limits", "api_football"): os.getenv("SOCCER_PREDICTION_RATE_LIMITS_API_FOOTBALL"),
    }
    updated = dict(config)
    for (section, key), raw_value in env_overrides.items():
        if raw_value is None:
            continue
        section_data = dict(updated.get(section, {}))
        if key == "dir":
            section_data[key] = str(Path(raw_value).expanduser())
        elif key in {
            "ttl_hours",
            "recency_window_days",
            "max_goals",
            "scenario_simulations",
            "random_seed",
            "opponent_network_depth",
            "opponent_network_max_teams",
            "shared_opponent_max_hops",
            "api_football",
        }:
            section_data[key] = int(raw_value)
        elif key in {
            "time_decay_xi",
            "morale_decay_xi",
            "morale_max_effect",
            "rate_prior_weight",
            "elite_defence_exponent",
            "elite_tempo_strength",
            "network_confidence_prior",
            "shared_opponent_weight",
            "shared_opponent_hop_decay",
        }:
            section_data[key] = float(raw_value)
        else:
            section_data[key] = raw_value
        updated[section] = section_data
    return updated


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load defaults, merge an optional YAML file, then apply env overrides."""
    config_data = _package_defaults()
    if path is not None:
        config_data = _merge(config_data, _read_yaml(Path(path)))
    config_data = _apply_env(config_data)

    api_football_data = dict(config_data.get("api_football", {}))
    cache_data = dict(config_data.get("cache", {}))
    rate_limits_data = dict(config_data.get("rate_limits", {}))
    model_data = dict(config_data.get("model", {}))

    return AppConfig(
        api_football=ApiFootballConfig(
            api_key=str(api_football_data.get("api_key", "")),
            host=str(api_football_data.get("host", "v3.football.api-sports.io")),
        ),
        cache=CacheConfig(
            dir=Path(str(cache_data.get("dir", ".cache/soccer_prediction"))).expanduser(),
            ttl_hours=int(cache_data.get("ttl_hours", 24)),
        ),
        rate_limits={str(key): int(value) for key, value in rate_limits_data.items()},
        model=ModelConfig(
            time_decay_xi=float(model_data.get("time_decay_xi", 0.0039)),
            recency_window_days=int(model_data.get("recency_window_days", 730)),
            max_goals=int(model_data.get("max_goals", 8)),
            scenario_simulations=int(model_data.get("scenario_simulations", 20_000)),
            random_seed=int(model_data.get("random_seed", 2026)),
            opponent_network_depth=int(model_data.get("opponent_network_depth", 1)),
            opponent_network_max_teams=int(model_data.get("opponent_network_max_teams", 12)),
            morale_decay_xi=float(model_data.get("morale_decay_xi", 0.0077)),
            morale_max_effect=float(model_data.get("morale_max_effect", 0.08)),
            rate_prior_weight=float(model_data.get("rate_prior_weight", 4.0)),
            elite_defence_exponent=min(1.0, max(0.35, float(model_data.get("elite_defence_exponent", 0.85)))),
            elite_tempo_strength=min(1.0, max(0.0, float(model_data.get("elite_tempo_strength", 0.08)))),
            network_rating_method=_rating_method(model_data.get("network_rating_method", "mle")),
            network_confidence_prior=max(0.0, float(model_data.get("network_confidence_prior", 2.0))),
            shared_opponent_weight=min(0.6, max(0.0, float(model_data.get("shared_opponent_weight", 0.15)))),
            shared_opponent_hop_decay=min(1.0, max(0.0, float(model_data.get("shared_opponent_hop_decay", 0.5)))),
            shared_opponent_max_hops=min(6, max(2, int(model_data.get("shared_opponent_max_hops", 3)))),
        ),
    )


def _rating_method(value: Any) -> str:
    """Normalize the network rating selector to a supported estimator name."""
    method = str(value).strip().casefold()
    return method if method in {"mle", "heuristic"} else "mle"


def example_usage() -> None:
    """Print the resolved default configuration."""
    print(load_config())


def main() -> None:
    """Module entry point."""
    example_usage()
