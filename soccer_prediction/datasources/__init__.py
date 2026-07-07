"""Data-source adapters and registry."""

from __future__ import annotations

from soccer_prediction.datasources.api_football import ApiFootballSource
from soccer_prediction.datasources.base import DataSource, get_source, list_sources, register_source
from soccer_prediction.datasources.cache import CachedFetcher, TokenBucketRateLimiter
from soccer_prediction.datasources.errors import DataSourceError, InsufficientHistoryError
from soccer_prediction.datasources.football_data_csv import FootballDataCsvSource
from soccer_prediction.datasources.statsbomb import StatsbombSource
from soccer_prediction.datasources.worldcup_open import WorldCupOpenSource

__all__ = [
    "ApiFootballSource",
    "CachedFetcher",
    "DataSource",
    "DataSourceError",
    "FootballDataCsvSource",
    "InsufficientHistoryError",
    "StatsbombSource",
    "TokenBucketRateLimiter",
    "WorldCupOpenSource",
    "get_source",
    "list_sources",
    "register_source",
]
