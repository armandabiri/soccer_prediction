"""API-Football data-source adapter."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime
from typing import Any

from soccer_prediction.config import load_config
from soccer_prediction.datasources.base import register_source
from soccer_prediction.datasources.cache import CachedFetcher, JsonPayload
from soccer_prediction.datasources.errors import DataSourceError
from soccer_prediction.models import Fixture, TeamMatchStats

__all__ = ["ApiFootballSource", "example_usage", "main"]

logger = logging.getLogger(__name__)


class ApiFootballSource:
    """Fetch fixtures and team histories from API-Football."""

    def __init__(
        self,
        api_key: str | None = None,
        host: str | None = None,
        fetcher: Callable[[str, Mapping[str, str], Mapping[str, str]], JsonPayload] | None = None,
    ) -> None:
        config = load_config()
        self.api_key = config.api_football.api_key if api_key is None else api_key
        self.host = config.api_football.host if host is None else host
        cached = CachedFetcher(
            config.cache.dir / "api_football",
            config.cache.ttl_hours,
            config.rate_limits["api_football"],
        )
        self._fetcher = (
            (lambda url, headers, params: cached.fetch(url, headers=headers, params=params))
            if fetcher is None
            else fetcher
        )

    def fetch_team_history(self, team: str, competition: str | None = None) -> list[TeamMatchStats]:
        """Return historical API-Football fixture statistics for a team."""
        if not self.api_key:
            raise DataSourceError("SOCCER_PREDICTION_API_FOOTBALL_KEY is required")
        params = {"team": team}
        if competition is not None:
            params["league"] = competition
        payload = self._request("/fixtures", params)
        records = [record for fixture in _items(payload) for record in self._records_from_fixture(fixture, team)]
        logger.info("loaded %d API-Football records for %s", len(records), team)
        return records

    def fetch_fixtures(self, competition: str) -> list[Fixture]:
        """Return fixtures for a competition code or API league id."""
        payload = self._request("/fixtures", {"league": competition})
        fixtures = [_fixture_from_api(item) for item in _items(payload)]
        logger.info("loaded %d API-Football fixtures for %s", len(fixtures), competition)
        return fixtures

    def _request(self, path: str, params: Mapping[str, str]) -> JsonPayload:
        if not self.api_key:
            raise DataSourceError("SOCCER_PREDICTION_API_FOOTBALL_KEY is required")
        url = f"https://{self.host}{path}"
        headers = {"x-apisports-key": self.api_key}
        payload = self._fetcher(url, headers, params)
        if isinstance(payload, dict) and payload.get("errors"):
            raise DataSourceError(f"API-Football returned errors: {payload['errors']}")
        return payload

    def _records_from_fixture(self, item: Mapping[str, Any], team: str) -> list[TeamMatchStats]:
        fixture = _nested(item, "fixture")
        teams = _nested(item, "teams")
        goals = _nested(item, "goals")
        score = _nested(item, "score")
        home = _nested(teams, "home")
        away = _nested(teams, "away")
        home_name = str(home.get("name", ""))
        away_name = str(away.get("name", ""))
        if team.casefold() not in {home_name.casefold(), away_name.casefold()}:
            return []
        fixture_date = _parse_date(str(fixture.get("date", "")))
        fetched_at = datetime.now(UTC)
        stats = _statistics(item)
        home_stats = stats.get(home_name, {"corners": 0, "yellows": 0, "reds": 0})
        away_stats = stats.get(away_name, {"corners": 0, "yellows": 0, "reds": 0})
        ht = _nested(score, "halftime")
        home_record = TeamMatchStats(
            team=home_name,
            opponent=away_name,
            date=fixture_date,
            is_home=True,
            goals_for=_int(goals.get("home")),
            goals_against=_int(goals.get("away")),
            ht_goals_for=_int(ht.get("home")),
            ht_goals_against=_int(ht.get("away")),
            corners_for=home_stats["corners"],
            corners_against=away_stats["corners"],
            yellows=home_stats["yellows"],
            reds=home_stats["reds"],
            source="api_football",
            fetched_at=fetched_at,
        )
        away_record = TeamMatchStats(
            team=away_name,
            opponent=home_name,
            date=fixture_date,
            is_home=False,
            goals_for=_int(goals.get("away")),
            goals_against=_int(goals.get("home")),
            ht_goals_for=_int(ht.get("away")),
            ht_goals_against=_int(ht.get("home")),
            corners_for=away_stats["corners"],
            corners_against=home_stats["corners"],
            yellows=away_stats["yellows"],
            reds=away_stats["reds"],
            source="api_football",
            fetched_at=fetched_at,
        )
        return [record for record in (home_record, away_record) if record.team.casefold() == team.casefold()]


def _items(payload: JsonPayload) -> list[Mapping[str, Any]]:
    raw_items = payload.get("response", []) if isinstance(payload, dict) else payload
    return [item for item in raw_items if isinstance(item, Mapping)]


def _nested(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key, {})
    return value if isinstance(value, Mapping) else {}


def _parse_date(raw: str) -> date:
    if not raw:
        return datetime.now(UTC).date()
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()


def _int(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float | str):
        return int(float(value))
    return 0


def _statistics(item: Mapping[str, Any]) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    for team_stats in item.get("statistics", []):
        if not isinstance(team_stats, Mapping):
            continue
        team_name = str(_nested(team_stats, "team").get("name", ""))
        values = {"corners": 0, "yellows": 0, "reds": 0}
        for stat in team_stats.get("statistics", []):
            if not isinstance(stat, Mapping):
                continue
            stat_name = str(stat.get("type", "")).casefold()
            if stat_name == "corner kicks":
                values["corners"] = _int(stat.get("value"))
            elif stat_name == "yellow cards":
                values["yellows"] = _int(stat.get("value"))
            elif stat_name == "red cards":
                values["reds"] = _int(stat.get("value"))
        stats[team_name] = values
    return stats


def _fixture_from_api(item: Mapping[str, Any]) -> Fixture:
    fixture = _nested(item, "fixture")
    teams = _nested(item, "teams")
    return Fixture(
        home_team=str(_nested(teams, "home").get("name", "")),
        away_team=str(_nested(teams, "away").get("name", "")),
        kickoff=datetime.fromisoformat(str(fixture.get("date", "")).replace("Z", "+00:00"))
        if fixture.get("date")
        else None,
        competition=str(_nested(item, "league").get("name", "")) or None,
        venue=str(_nested(fixture, "venue").get("name", "")) or None,
        round_name=str(_nested(item, "league").get("round", "")) or None,
    )


@register_source("api_football")
def _factory() -> ApiFootballSource:
    return ApiFootballSource()


def example_usage() -> None:
    """Print the configured source host."""
    print(ApiFootballSource(api_key="example").host)


def main() -> None:
    """Module entry point."""
    example_usage()
