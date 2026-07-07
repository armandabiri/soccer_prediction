"""T09 acceptance: cache hits skip refetch; 429s back off then succeed."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

import pytest

from soccer_prediction.datasources.cache import CachedFetcher


def test_hit_skips_fetch(tmp_path: Path) -> None:
    """A second fetch of the same key does not call the underlying getter."""
    calls = {"n": 0}

    def counting_get(url: str, headers: Mapping[str, str], params: Mapping[str, str]) -> dict[str, Any]:
        calls["n"] += 1
        return {"value": calls["n"]}

    fetcher = CachedFetcher(tmp_path, ttl_hours=24, get=counting_get)
    first = fetcher.fetch("https://example.invalid/data", params={"team": "Brazil"})
    second = fetcher.fetch("https://example.invalid/data", params={"team": "Brazil"})
    assert calls["n"] == 1
    assert first == second


def test_backoff_on_429(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A 429 is retried after backoff and then succeeds."""
    monkeypatch.setattr("time.sleep", lambda _seconds: None)
    calls = {"n": 0}

    def flaky_get(url: str, headers: Mapping[str, str], params: Mapping[str, str]) -> dict[str, Any]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise HTTPError(url, 429, "Too Many Requests", {}, None)  # type: ignore[arg-type]
        return {"ok": True}

    fetcher = CachedFetcher(tmp_path, ttl_hours=24, get=flaky_get, retries=3)
    result = fetcher.fetch("https://example.invalid/data")
    assert result == {"ok": True}
    assert calls["n"] == 2
