"""Typed strategy contract validation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from soccer_prediction.models import ContractQuote, StrategyRequest


def test_quote_rejects_invalid_price_and_crossed_book() -> None:
    with pytest.raises(ValueError, match="ask"):
        ContractQuote("match_result", "home", Decimal("1.01"))
    with pytest.raises(ValueError, match="bid cannot exceed ask"):
        ContractQuote("match_result", "home", Decimal("0.4"), bid=Decimal("0.5"))


def test_request_validates_risk_inputs_and_is_immutable() -> None:
    with pytest.raises(ValueError, match="bankroll"):
        StrategyRequest(bankroll=Decimal("0"))
    request = StrategyRequest()
    with pytest.raises(FrozenInstanceError):
        request.bankroll = Decimal("20")  # type: ignore[misc]

