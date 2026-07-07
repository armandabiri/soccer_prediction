"""Cached JSON fetcher with rate limiting and retry backoff."""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from soccer_prediction.datasources.errors import DataSourceError

__all__ = ["CachedFetcher", "JsonPayload", "TokenBucketRateLimiter", "example_usage", "main"]

JsonPayload = dict[str, Any] | list[Any]
logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """Simple per-process token bucket."""

    def __init__(self, rate_limit: int, window_seconds: float = 86_400.0) -> None:
        self._capacity = max(rate_limit, 0)
        self._tokens = float(self._capacity)
        self._window_seconds = window_seconds
        self._updated_at = time.monotonic()

    def wait(self) -> None:
        """Block until one request token is available."""
        if self._capacity <= 0:
            return
        now = time.monotonic()
        refill = (now - self._updated_at) * (self._capacity / self._window_seconds)
        self._tokens = min(float(self._capacity), self._tokens + refill)
        self._updated_at = now
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return
        sleep_for = (1.0 - self._tokens) * (self._window_seconds / self._capacity)
        logger.debug("rate limit sleeping %.2f seconds", sleep_for)
        time.sleep(sleep_for)
        self._tokens = 0.0
        self._updated_at = time.monotonic()


def _default_get(url: str, headers: Mapping[str, str], params: Mapping[str, str]) -> JsonPayload:
    query = urlencode(params)
    request_url = f"{url}?{query}" if query else url
    request = Request(request_url, headers=dict(headers), method="GET")
    with urlopen(request, timeout=30) as response:  # noqa: S310 - user-provided data source URL by design.
        payload = response.read().decode("utf-8")
    parsed = json.loads(payload)
    if not isinstance(parsed, dict | list):
        raise DataSourceError("response JSON must be an object or array")
    return parsed


@dataclass(slots=True)
class CachedFetcher:
    """Fetch JSON with TTL caching, atomic writes, rate limiting, and bounded retry."""

    cache_dir: Path
    ttl_hours: int
    rate_limit: int = 0
    get: Callable[[str, Mapping[str, str], Mapping[str, str]], JsonPayload] = _default_get
    retries: int = 3
    _limiter: TokenBucketRateLimiter = field(init=False)

    def __post_init__(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._limiter = TokenBucketRateLimiter(self.rate_limit)

    def fetch(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        refresh: bool = False,
    ) -> JsonPayload:
        """Return cached JSON or fetch and cache a fresh response."""
        safe_headers = {} if headers is None else dict(headers)
        safe_params = {} if params is None else dict(params)
        cache_path = self._cache_path(url, safe_params)
        if not refresh and self._is_fresh(cache_path):
            logger.debug("cache hit for %s", url)
            return self._read(cache_path)
        payload = self._fetch_with_retry(url, safe_headers, safe_params)
        self._write_atomic(cache_path, payload)
        return payload

    def _cache_path(self, url: str, params: Mapping[str, str]) -> Path:
        key = json.dumps({"url": url, "params": sorted(params.items())}, sort_keys=True)
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def _is_fresh(self, path: Path) -> bool:
        if not path.exists():
            return False
        age_seconds = time.time() - path.stat().st_mtime
        return age_seconds <= self.ttl_hours * 3600

    def _read(self, path: Path) -> JsonPayload:
        parsed = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(parsed, dict | list):
            raise DataSourceError(f"cached JSON at {path} is not an object or array")
        return parsed

    def _write_atomic(self, path: Path, payload: JsonPayload) -> None:
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        temp_path.replace(path)

    def _fetch_with_retry(self, url: str, headers: Mapping[str, str], params: Mapping[str, str]) -> JsonPayload:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            self._limiter.wait()
            try:
                logger.debug("fetching %s attempt %d", url, attempt + 1)
                return self.get(url, headers, params)
            except HTTPError as exc:
                last_error = exc
                if exc.code not in {429, 500, 502, 503, 504} or attempt >= self.retries:
                    break
            except URLError as exc:
                last_error = exc
                if attempt >= self.retries:
                    break
            sleep_for = min(2.0**attempt + random.uniform(0.0, 0.25), 10.0)
            logger.warning("retrying %s after %.2f seconds", url, sleep_for)
            time.sleep(sleep_for)
        raise DataSourceError(f"failed to fetch {url}") from last_error


def example_usage() -> None:
    """Print a cache key example."""
    fetcher = CachedFetcher(Path(".cache/soccer_prediction"), ttl_hours=24)
    print(fetcher._cache_path("https://example.invalid", {}))


def main() -> None:
    """Module entry point."""
    example_usage()
