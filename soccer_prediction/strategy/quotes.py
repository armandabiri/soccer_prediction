"""Versioned JSON quote loading and venue-neutral normalization."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from soccer_prediction.models import ContractQuote, QuoteSnapshot

__all__ = ["load_quote_snapshot"]


def _decimal(value: object, name: str, *, optional: bool = False) -> Decimal | None:
    if value is None and optional:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be a decimal value") from exc


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("observed_at must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("observed_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("observed_at must include a timezone")
    return parsed.astimezone(UTC)


def _normalized_prices(item: dict[str, Any]) -> tuple[Decimal, Decimal | None]:
    ask = _decimal(item.get("ask"), "ask", optional=True)
    bid = _decimal(item.get("bid"), "bid", optional=True)
    yes_bid = _decimal(item.get("yes_bid"), "yes_bid", optional=True)
    no_bid = _decimal(item.get("no_bid"), "no_bid", optional=True)
    if bid is None and yes_bid is not None:
        bid = yes_bid
    if ask is None and no_bid is not None:
        ask = Decimal("1") - no_bid
    if ask is None:
        raise ValueError("each contract requires ask or reciprocal no_bid")
    return ask, bid


def _contract(item: object, index: int) -> ContractQuote:
    if not isinstance(item, dict):
        raise ValueError(f"contracts[{index}] must be an object")
    ask, bid = _normalized_prices(item)
    market = str(item.get("market", "")).strip().lower()
    selection = str(item.get("selection", "")).strip()
    if not market or not selection:
        raise ValueError(f"contracts[{index}] requires market and selection")
    return ContractQuote(
        market=market,
        selection=selection,
        ask=ask,
        bid=bid,
        available_at_ask=_decimal(item.get("available_at_ask", "1000000"), "available_at_ask") or Decimal(0),
        available_at_bid=_decimal(item.get("available_at_bid", "1000000"), "available_at_bid") or Decimal(0),
        tick_size=_decimal(item.get("tick_size", "0.01"), "tick_size") or Decimal("0.01"),
        quantity_step=_decimal(item.get("quantity_step", "1"), "quantity_step") or Decimal(1),
        buy_fee_rate=_decimal(item.get("buy_fee_rate", "0"), "buy_fee_rate") or Decimal(0),
        sell_fee_rate=_decimal(item.get("sell_fee_rate", "0"), "sell_fee_rate") or Decimal(0),
        settlement=str(item.get("settlement", "unspecified")).strip(),
    )


def load_quote_snapshot(path: str | Path) -> QuoteSnapshot:
    """Load and validate a version-1 executable quote snapshot from JSON."""
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load quote snapshot {source}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("quote snapshot must be a JSON object")
    raw_contracts = payload.get("contracts")
    if not isinstance(raw_contracts, list) or not raw_contracts:
        raise ValueError("quote snapshot requires a non-empty contracts list")
    return QuoteSnapshot(
        schema_version=int(payload.get("schema_version", 0)),
        venue=str(payload.get("venue", "")).strip(),
        observed_at=_timestamp(payload.get("observed_at")),
        contracts=tuple(_contract(item, index) for index, item in enumerate(raw_contracts)),
        notes=tuple(str(note) for note in payload.get("notes", [])),
    )

