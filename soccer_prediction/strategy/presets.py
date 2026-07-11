"""Named bankroll reserves and live-exit fractions."""

from __future__ import annotations

from decimal import Decimal

from soccer_prediction.models import StrategyRequest

__all__ = ["exit_fractions", "reserve_percentage"]

_RESERVES = {
    "conservative": Decimal("0.30"),
    "balanced": Decimal("0.20"),
    "aggressive": Decimal("0.10"),
}
_FRACTIONS = {
    "conservative": (Decimal("0.60"), Decimal("0.30"), Decimal("0.10")),
    "balanced": (Decimal("0.40"), Decimal("0.35"), Decimal("0.25")),
    "aggressive": (Decimal("0.20"), Decimal("0.30"), Decimal("0.50")),
}


def reserve_percentage(name: str, request: StrategyRequest) -> Decimal:
    """Return a preset reserve, honoring an override for the selected plan."""
    if name == request.plan and request.reserve_pct is not None:
        return request.reserve_pct
    return _RESERVES[name]


def exit_fractions(name: str) -> tuple[Decimal, Decimal, Decimal]:
    """Return first, second, and final live sell fractions."""
    return _FRACTIONS[name]

