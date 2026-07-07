"""Data-source adapters and registry."""

from __future__ import annotations

from soccer_prediction.datasources.api_football import ApiFootballSource
from soccer_prediction.datasources.base import DataSource, PlayerSource, get_source, list_sources, register_source
from soccer_prediction.datasources.cache import CachedFetcher, TokenBucketRateLimiter
from soccer_prediction.datasources.errors import DataSourceError, InsufficientHistoryError
from soccer_prediction.datasources.football_data_csv import FootballDataCsvSource
from soccer_prediction.datasources.international_results import INTERNATIONAL_RESULTS_URL, InternationalResultsSource
from soccer_prediction.datasources.statsbomb import StatsbombSource
from soccer_prediction.datasources.worldcup_open import WC2026_URL, WorldCupOpenSource

__all__ = [
    "INTERNATIONAL_RESULTS_URL",
    "WC2026_URL",
    "ApiFootballSource",
    "CachedFetcher",
    "DataSource",
    "DataSourceError",
    "FootballDataCsvSource",
    "InsufficientHistoryError",
    "InternationalResultsSource",
    "PlayerSource",
    "StatsbombSource",
    "TokenBucketRateLimiter",
    "WorldCupOpenSource",
    "get_source",
    "list_sources",
    "register_source",
]
