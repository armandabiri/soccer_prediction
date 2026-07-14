"""Typed contracts for price-aware bankroll and live-exit reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal

__all__ = [
    "Allocation",
    "BettingStrategy",
    "ContractEvaluation",
    "ContractQuote",
    "ExitStage",
    "LiveMatchContext",
    "LiveScorePlan",
    "PathLedgerRow",
    "PresetSummary",
    "QuoteSnapshot",
    "StrategyRequest",
]

ZERO = Decimal("0")
ONE = Decimal("1")
CENT = Decimal("0.01")


def _unit(value: Decimal, name: str) -> None:
    if not ZERO <= value <= ONE:
        raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class ContractQuote:
    """One executable binary-contract quote and its market identity."""

    market: str
    selection: str
    ask: Decimal
    bid: Decimal | None = None
    available_at_ask: Decimal = Decimal("1000000")
    available_at_bid: Decimal = Decimal("1000000")
    tick_size: Decimal = CENT
    quantity_step: Decimal = ONE
    buy_fee_rate: Decimal = ZERO
    sell_fee_rate: Decimal = ZERO
    settlement: str = "unspecified"

    def __post_init__(self) -> None:
        _unit(self.ask, "ask")
        if self.bid is not None:
            _unit(self.bid, "bid")
            if self.bid > self.ask:
                raise ValueError("bid cannot exceed ask")
        if min(self.available_at_ask, self.available_at_bid) < ZERO:
            raise ValueError("available size cannot be negative")
        if self.tick_size <= ZERO or self.quantity_step <= ZERO:
            raise ValueError("tick_size and quantity_step must be positive")
        _unit(self.buy_fee_rate, "buy_fee_rate")
        _unit(self.sell_fee_rate, "sell_fee_rate")

    @property
    def key(self) -> str:
        """Return the canonical quote key."""
        return f"{self.market}:{self.selection}"


@dataclass(frozen=True, slots=True)
class QuoteSnapshot:
    """Versioned immutable collection of executable quotes."""

    schema_version: int
    venue: str
    observed_at: datetime
    contracts: tuple[ContractQuote, ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("unsupported quote schema_version")
        if not self.venue.strip():
            raise ValueError("venue is required")
        keys = [quote.key for quote in self.contracts]
        if len(keys) != len(set(keys)):
            raise ValueError("quote snapshot contains duplicate market keys")


@dataclass(frozen=True, slots=True)
class StrategyRequest:
    """User risk and execution assumptions for one report."""

    bankroll: Decimal = Decimal("10.00")
    plan: Literal["conservative", "balanced", "aggressive"] = "balanced"
    safety_margin: Decimal = Decimal("0.03")
    slippage: Decimal = Decimal("0.005")
    reserve_pct: Decimal | None = None
    max_quote_age_seconds: int | None = 3600

    def __post_init__(self) -> None:
        if self.bankroll <= ZERO:
            raise ValueError("bankroll must be positive")
        _unit(self.safety_margin, "safety_margin")
        _unit(self.slippage, "slippage")
        if self.reserve_pct is not None and not Decimal("0.10") <= self.reserve_pct <= Decimal("0.30"):
            raise ValueError("reserve_pct must be between 0.10 and 0.30")
        if self.max_quote_age_seconds is not None and self.max_quote_age_seconds <= 0:
            raise ValueError("max_quote_age_seconds must be positive or None")


@dataclass(frozen=True, slots=True)
class ContractEvaluation:
    """Model value compared with one executable contract quote."""

    quote: ContractQuote
    model_probability: Decimal | None
    conservative_probability: Decimal | None
    fair_price: Decimal | None
    raw_edge: Decimal | None
    net_edge: Decimal | None
    all_in_cost: Decimal | None
    max_buy_price: Decimal | None
    eligible: bool
    reason: str
    intent: str


@dataclass(frozen=True, slots=True)
class Allocation:
    """One purchased position and its settlement economics."""

    evaluation: ContractEvaluation
    amount: Decimal
    contracts: Decimal
    maximum_loss: Decimal
    gross_payout: Decimal
    net_profit_if_win: Decimal


@dataclass(frozen=True, slots=True)
class ExitStage:
    """One planned live sale stage."""

    label: str
    minute_range: str
    minute: int
    fair_value: Decimal
    current_bid: Decimal | None
    bid_depth: Decimal
    target_price: Decimal
    executable_now: bool
    fraction: Decimal
    contracts: Decimal
    cash_received: Decimal
    profit_locked: Decimal
    cumulative_cash: Decimal = ZERO
    recovery_target: Decimal = ZERO
    safe_to_sell: bool = False


@dataclass(frozen=True, slots=True)
class LiveMatchContext:
    """Explicit caller-supplied live scoring-rate adjustments."""

    home_rate_multiplier: Decimal = ONE
    away_rate_multiplier: Decimal = ONE
    home_red_cards: int = 0
    away_red_cards: int = 0
    leading_team_defending: bool = False
    trailing_team_pressure: bool = False
    injury_multiplier: Decimal = ONE
    substitution_multiplier: Decimal = ONE
    pressure_multiplier: Decimal = ONE
    added_minutes: int = 0
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value in (self.home_rate_multiplier, self.away_rate_multiplier):
            if not Decimal("0.25") <= value <= Decimal("3.0"):
                raise ValueError("live rate multipliers must be between 0.25 and 3.0")
        if not 0 <= self.home_red_cards <= 2 or not 0 <= self.away_red_cards <= 2:
            raise ValueError("red-card counts must be between 0 and 2")
        for value in (self.injury_multiplier, self.substitution_multiplier, self.pressure_multiplier):
            if not Decimal("0.50") <= value <= Decimal("1.50"):
                raise ValueError("context multipliers must be between 0.50 and 1.50")
        if not 0 <= self.added_minutes <= 20:
            raise ValueError("added_minutes must be between 0 and 20")


@dataclass(frozen=True, slots=True)
class LiveScorePlan:
    """Conditional value and staged exits for one current score."""

    score: str
    model_probability: Decimal
    position_active: bool
    allocated_contracts: Decimal
    position_cost: Decimal
    stages: tuple[ExitStage, ...]
    next_home_score: str
    next_away_score: str
    goal_before_fill: str
    assumptions: str
    impossible_cost_now: Decimal = ZERO
    next_home_goal_loss: Decimal = ZERO
    next_away_goal_loss: Decimal = ZERO
    safe_recovery_target: Decimal = ZERO
    safe_sell_price: Decimal | None = None


@dataclass(frozen=True, slots=True)
class PathLedgerRow:
    """Cumulative cash and recovery state at one score-path event."""

    path: str
    score: str
    stage_cash: Decimal
    cumulative_cash: Decimal
    active_position_costs: Decimal
    realized_profit: Decimal
    individual_recovered: bool
    active_positions_recovered: bool
    full_bankroll_recovered: bool
    fixed_profit_025: bool
    fixed_profit_050: bool
    fixed_profit_100: bool


@dataclass(frozen=True, slots=True)
class PresetSummary:
    """Exact allocation and loss summary for one risk preset."""

    name: str
    reserve: Decimal
    deployed: Decimal
    uninvested_cash: Decimal
    maximum_loss: Decimal
    exit_fractions: tuple[Decimal, Decimal, Decimal]
    allocations: tuple[Allocation, ...] = ()


@dataclass(frozen=True, slots=True)
class BettingStrategy:
    """Complete price-aware strategy artifact consumed by report renderers."""

    schema_version: int
    venue: str
    quote_observed_at: datetime
    request: StrategyRequest
    evaluations: tuple[ContractEvaluation, ...]
    allocations: tuple[Allocation, ...]
    uninvested_cash: Decimal
    live_scores: tuple[LiveScorePlan, ...]
    path_ledger: tuple[PathLedgerRow, ...]
    presets: tuple[PresetSummary, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)
