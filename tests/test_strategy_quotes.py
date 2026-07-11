"""Quote schema, normalization, and provenance tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from soccer_prediction.strategy import load_quote_snapshot


def _write(path: Path, contracts: list[dict[str, str]]) -> Path:
    payload = {
        "schema_version": 1,
        "venue": "test",
        "observed_at": datetime.now(UTC).isoformat(),
        "contracts": contracts,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_reciprocal_no_bid_produces_executable_ask(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "quotes.json",
        [{"market": "match_result", "selection": "home", "yes_bid": "0.40", "no_bid": "0.55"}],
    )
    quote = load_quote_snapshot(path).contracts[0]
    assert str(quote.bid) == "0.40"
    assert str(quote.ask) == "0.45"


def test_duplicate_market_keys_are_rejected(tmp_path: Path) -> None:
    item = {"market": "btts", "selection": "yes", "ask": "0.40"}
    with pytest.raises(ValueError, match="duplicate"):
        load_quote_snapshot(_write(tmp_path / "duplicates.json", [item, item]))

