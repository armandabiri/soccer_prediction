"""T04 acceptance: the data-source registry round-trips and ships built-in adapters."""

from __future__ import annotations

from soccer_prediction.datasources import get_source, list_sources, register_source
from soccer_prediction.datasources.base import DataSource
from soccer_prediction.models import Fixture, TeamMatchStats


class _DummySource:
    def fetch_team_history(self, team: str, competition: str | None = None) -> list[TeamMatchStats]:
        return []

    def fetch_fixtures(self, competition: str) -> list[Fixture]:
        return []


def test_registry_roundtrip() -> None:
    """A registered factory is retrievable by its normalized name."""

    @register_source("dummy-registry-test")
    def _factory() -> _DummySource:
        return _DummySource()

    source: DataSource = get_source("Dummy_Registry_Test")
    assert isinstance(source, _DummySource)


def test_builtin_sources_registered() -> None:
    """The four free adapters register at import time."""
    names = set(list_sources())
    assert {"api_football", "football_data_csv", "worldcup_open", "statsbomb"} <= names
