"""Data-source protocol and registry."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol

from soccer_prediction.models import Fixture, TeamMatchStats

__all__ = [
    "DataSource",
    "DataSourceFactory",
    "get_source",
    "list_sources",
    "register_source",
]


class DataSource(Protocol):
    """Stable interface for historical data providers."""

    def fetch_team_history(self, team: str, competition: str | None = None) -> list[TeamMatchStats]:
        """Return historical team-level match records."""

    def fetch_fixtures(self, competition: str) -> list[Fixture]:
        """Return fixtures for a competition."""


DataSourceFactory = Callable[[], DataSource]
_SOURCE_REGISTRY: dict[str, DataSourceFactory] = {}


def register_source(name: str) -> Callable[[DataSourceFactory], DataSourceFactory]:
    """Register a data-source factory by name."""

    def decorator(factory: DataSourceFactory) -> DataSourceFactory:
        normalized = name.strip().lower().replace("-", "_")
        if not normalized:
            raise ValueError("source name cannot be empty")
        _SOURCE_REGISTRY[normalized] = factory
        return factory

    return decorator


def get_source(name: str) -> DataSource:
    """Create a registered source by name."""
    normalized = name.strip().lower().replace("-", "_")
    try:
        return _SOURCE_REGISTRY[normalized]()
    except KeyError as exc:
        available = ", ".join(list_sources()) or "none"
        raise KeyError(f"unknown data source {name!r}; available: {available}") from exc


def list_sources() -> Sequence[str]:
    """Return registered source names."""
    return tuple(sorted(_SOURCE_REGISTRY))
