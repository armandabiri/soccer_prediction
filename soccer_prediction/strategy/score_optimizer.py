"""Log-optimal (Kelly) staking across mutually exclusive scorelines.

This replaces "cover the whole grid and hope" with an actual constrained
optimization:

    maximize   sum_i  p_i * log(W_i)
    subject to W_i = cash + stake_i / ask_i,  sum_i stake_i + cash = bankroll,
               stake_i >= 0,  cash >= 0

over *every* outcome -- including a residual bucket holding every scoreline the
market does not list, so no possibility is ever treated as impossible. Maximizing
expected log wealth is the growth-optimal criterion (Kelly), which is exactly the
discipline a flat "dutch the grid" plan lacks.

Note the admission rule is ``p_i / ask_i > lambda``, where ``lambda`` is the cash
the plan would otherwise hold -- *not* ``> 1``. When nothing is +EV, ``lambda``
stays at 1 and the optimizer stakes nothing at all. But once it holds positions
``lambda`` falls below 1, and a marginally negative-edge score can then earn a
small stake as a hedge: it pays more than idle cash in a case the other legs miss.

Two deliberate guards against over-trusting the model:

* ``model_trust`` blends the model's probabilities with the market's own
  de-vigged implied probabilities. At ``model_trust=0`` the market is taken as
  truth and the optimizer finds no edge anywhere (it stakes nothing) -- the
  honest answer when you have no view. The default only partially trusts the
  model.
* ``ask`` prices are what you actually pay, not the optimistic displayed
  percentage; see ``ASK_SPREAD``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import yaml

__all__ = [
    "ASK_SPREAD",
    "OptimizedPlan",
    "ScoreOutcome",
    "StakeAllocation",
    "blend_probabilities",
    "build_outcomes",
    "example_usage",
    "load_market",
    "main",
    "optimize_stakes",
]

# Observed gap between the displayed market % and the real ask, from two payout
# quotes on this book: 0-3 showed 2% but cost 3.10% ($20 -> $645); 3-3 showed 1%
# but cost 2.05% ($100 -> $4,879). Both imply ~+1.1pp, so an unquoted price is
# assumed to cost this much more than the screen says.
ASK_SPREAD = 0.011

# Nothing is ever zero: probabilities and prices are floored here.
_EPSILON = 1e-6

_RESIDUAL_LABEL = "other"


@dataclass(frozen=True, slots=True)
class ScoreOutcome:
    """One mutually exclusive outcome: a scoreline, or the residual tail."""

    label: str
    ask: float
    model_probability: float
    market_probability: float
    probability: float
    tradeable: bool = True
    quoted_ask: bool = False

    @property
    def edge(self) -> float:
        """Blended probability minus the price paid; positive means value."""
        return self.probability - self.ask if self.tradeable else 0.0

    @property
    def ratio(self) -> float:
        """Expected value per dollar staked (``p/ask``); above 1.0 is +EV."""
        return self.probability / self.ask if self.tradeable else 0.0


@dataclass(frozen=True, slots=True)
class StakeAllocation:
    """A funded position produced by the optimizer."""

    label: str
    ask: float
    probability: float
    stake: float
    contracts: float
    payout_if_hit: float
    wealth_if_hit: float
    profit_if_hit: float
    edge: float
    ratio: float


@dataclass(frozen=True, slots=True)
class OptimizedPlan:
    """A log-optimal allocation plus its risk/return profile."""

    bankroll: float
    model_trust: float
    allocations: tuple[StakeAllocation, ...]
    cash_reserve: float
    staked: float
    expected_profit: float
    expected_log_growth: float
    win_probability: float
    loss_probability: float
    worst_case_wealth: float
    residual_probability: float
    skipped: tuple[ScoreOutcome, ...]


@dataclass(frozen=True, slots=True)
class ScoreMarket:
    """A loaded market: fixture identity plus every quoted scoreline."""

    home: str
    away: str
    bankroll: float
    rows: tuple[dict[str, float], ...]


def load_market(path: str | Path) -> ScoreMarket:
    """Load a schema-2 correct-score market (displayed/ask/probability) from YAML."""
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    fixture = payload.get("fixture") or {}
    rows = payload.get("scores") or []
    if not rows:
        raise ValueError("market YAML must contain a non-empty 'scores' list")
    return ScoreMarket(
        home=str(fixture.get("home", "Home")),
        away=str(fixture.get("away", "Away")),
        bankroll=float(payload.get("bankroll", 500.0)),
        rows=tuple(dict(row) for row in rows),
    )


def load_packaged_market(resource: str) -> ScoreMarket:
    """Load a market bundled under ``soccer_prediction.example.data``."""
    handle = resources.files("soccer_prediction.example").joinpath(f"data/{resource}")
    with resources.as_file(handle) as path:
        return load_market(path)


def _ask_for(row: dict[str, float], spread: float = 0.0) -> tuple[float, bool]:
    """Return the price to trade against and whether a payout quote pinned it.

    With ``spread <= 0`` (the default) the displayed market percentage is used
    verbatim -- it is the only figure actually observed for every score. Passing
    a positive ``spread`` (e.g. ``ASK_SPREAD``) switches to the pessimistic view:
    payout-quoted rows use their true ask and the rest are marked up, which
    stress-tests how much of the edge survives real fills.
    """
    displayed = max(_EPSILON, float(row.get("displayed", 0.0)))
    quoted = row.get("ask")
    if spread <= 0.0:
        return displayed, quoted is not None
    if quoted is not None:
        return max(_EPSILON, float(quoted)), True
    return displayed + spread, False


def blend_probabilities(
    model: Sequence[float],
    asks: Sequence[float],
    *,
    model_trust: float,
    listed_mass: float,
) -> list[float]:
    """Blend model probabilities with the market's de-vigged implied probabilities.

    The market's asks are normalized to the same total mass as the model assigns
    to the listed scores, so both views are directly comparable, then mixed by
    ``model_trust`` (1.0 = model only, 0.0 = market only). Anything below 1.0
    means the optimizer is not taking the model's word as truth.
    """
    trust = min(1.0, max(0.0, model_trust))
    ask_total = sum(asks) or 1.0
    blended: list[float] = []
    for model_p, ask in zip(model, asks, strict=True):
        market_p = (ask / ask_total) * listed_mass
        blended.append(max(_EPSILON, trust * model_p + (1.0 - trust) * market_p))
    return blended


def build_outcomes(
    market: ScoreMarket, *, model_trust: float = 0.5, spread: float = 0.0
) -> tuple[ScoreOutcome, ...]:
    """Build the complete outcome space: every listed score plus the residual tail.

    The residual holds all probability the listed scores do not account for, so
    the unlisted tail (5-1, 6-0, ...) is represented rather than assumed away. It
    is not tradeable, so the optimizer can never "cover everything".

    ``spread`` defaults to 0, pricing against the displayed market percentages;
    pass ``ASK_SPREAD`` to re-run the same optimization on pessimistic fills.
    """
    model_probs = [max(_EPSILON, float(row.get("probability", 0.0))) for row in market.rows]
    asks_quoted = [_ask_for(row, spread) for row in market.rows]
    asks = [ask for ask, _quoted in asks_quoted]
    listed_mass = min(1.0 - _EPSILON, sum(model_probs))
    blended = blend_probabilities(model_probs, asks, model_trust=model_trust, listed_mass=listed_mass)
    ask_total = sum(asks) or 1.0
    outcomes = [
        ScoreOutcome(
            label=f"{int(row['home'])}-{int(row['away'])}",
            ask=ask,
            model_probability=model_p,
            market_probability=(ask / ask_total) * listed_mass,
            probability=blend_p,
            tradeable=True,
            quoted_ask=quoted,
        )
        for row, (ask, quoted), model_p, blend_p in zip(
            market.rows, asks_quoted, model_probs, blended, strict=True
        )
    ]
    residual = max(_EPSILON, 1.0 - sum(outcome.probability for outcome in outcomes))
    outcomes.append(
        ScoreOutcome(
            label=_RESIDUAL_LABEL,
            ask=1.0,  # unreachable: not tradeable
            model_probability=max(_EPSILON, 1.0 - sum(model_probs)),
            market_probability=residual,
            probability=residual,
            tradeable=False,
        )
    )
    return tuple(outcomes)


def optimize_stakes(
    outcomes: Sequence[ScoreOutcome],
    *,
    bankroll: float,
    fraction: float = 1.0,
) -> OptimizedPlan:
    """Maximize expected log wealth over mutually exclusive outcomes.

    Uses the exact Kelly threshold solution: sort outcomes by ``p/ask``, admit
    them while the ratio beats ``lambda = (1 - P_S) / (1 - Q_S)``, then stake
    ``p_i - lambda * ask_i`` on each admitted outcome and hold ``lambda`` as
    cash. ``lambda`` is the cash rate the stake must beat, so with no +EV outcome
    anywhere it stays at 1 and nothing is staked; once positions exist it drops
    below 1 and a slightly -EV score can be admitted as a hedge. The untradeable
    residual keeps ``lambda`` honest -- it is why full coverage is not optimal.

    ``fraction`` scales the stakes toward cash (0.5 = "half Kelly"), the usual
    hedge against the probabilities themselves being wrong.
    """
    if bankroll <= 0.0:
        raise ValueError("bankroll must be positive")
    tradeable = [outcome for outcome in outcomes if outcome.tradeable]
    if not tradeable:
        raise ValueError("no tradeable outcomes")
    ranked = sorted(tradeable, key=lambda item: -item.ratio)
    chosen: list[ScoreOutcome] = []
    probability_sum = 0.0
    ask_sum = 0.0
    for outcome in ranked:
        # Threshold from the set admitted SO FAR (never including the candidate):
        # with an empty set lambda is 1.0, so the first outcome is admitted only
        # if p/ask > 1 -- i.e. a genuinely +EV price. Lambda is non-increasing as
        # +EV outcomes are added, which makes this greedy pass exact.
        threshold = (1.0 - probability_sum) / (1.0 - ask_sum)
        if outcome.ratio <= threshold:
            break
        if ask_sum + outcome.ask >= 1.0:
            break
        chosen.append(outcome)
        probability_sum += outcome.probability
        ask_sum += outcome.ask
    lam = (1.0 - probability_sum) / (1.0 - ask_sum) if ask_sum < 1.0 else 1.0
    scale = min(1.0, max(0.0, fraction))
    allocations: list[StakeAllocation] = []
    for outcome in chosen:
        weight = max(0.0, outcome.probability - lam * outcome.ask) * scale
        stake = bankroll * weight
        if stake <= 0.0:
            continue
        contracts = stake / outcome.ask
        allocations.append(
            StakeAllocation(
                label=outcome.label,
                ask=outcome.ask,
                probability=outcome.probability,
                stake=stake,
                contracts=contracts,
                payout_if_hit=contracts,
                wealth_if_hit=0.0,  # filled below once cash is known
                profit_if_hit=0.0,
                edge=outcome.edge,
                ratio=outcome.ratio,
            )
        )
    staked = sum(item.stake for item in allocations)
    cash = bankroll - staked
    allocations = [
        StakeAllocation(
            label=item.label,
            ask=item.ask,
            probability=item.probability,
            stake=item.stake,
            contracts=item.contracts,
            payout_if_hit=item.payout_if_hit,
            wealth_if_hit=cash + item.payout_if_hit,
            profit_if_hit=cash + item.payout_if_hit - bankroll,
            edge=item.edge,
            ratio=item.ratio,
        )
        for item in allocations
    ]
    allocations.sort(key=lambda item: -item.stake)
    staked_labels = {item.label for item in allocations}
    win_probability = sum(item.probability for item in allocations)
    expected_profit = sum(item.probability * item.wealth_if_hit for item in allocations)
    expected_profit += (1.0 - win_probability) * cash
    expected_profit -= bankroll
    growth = sum(
        item.probability * math.log(max(item.wealth_if_hit, _EPSILON)) for item in allocations
    )
    growth += (1.0 - win_probability) * math.log(max(cash, _EPSILON))
    growth -= math.log(bankroll)
    residual = next(
        (item.probability for item in outcomes if not item.tradeable),
        0.0,
    )
    return OptimizedPlan(
        bankroll=bankroll,
        model_trust=0.0,
        allocations=tuple(allocations),
        cash_reserve=cash,
        staked=staked,
        expected_profit=expected_profit,
        expected_log_growth=growth,
        win_probability=win_probability,
        loss_probability=1.0 - win_probability,
        worst_case_wealth=cash,
        residual_probability=residual,
        skipped=tuple(
            outcome
            for outcome in outcomes
            if outcome.tradeable and outcome.label not in staked_labels
        ),
    )


def optimize_market(
    market: ScoreMarket,
    *,
    model_trust: float = 0.5,
    fraction: float = 1.0,
    bankroll: float | None = None,
    spread: float = 0.0,
) -> OptimizedPlan:
    """Build the outcome space from a market and return its log-optimal plan."""
    outcomes = build_outcomes(market, model_trust=model_trust, spread=spread)
    plan = optimize_stakes(
        outcomes,
        bankroll=market.bankroll if bankroll is None else bankroll,
        fraction=fraction,
    )
    return OptimizedPlan(
        bankroll=plan.bankroll,
        model_trust=model_trust,
        allocations=plan.allocations,
        cash_reserve=plan.cash_reserve,
        staked=plan.staked,
        expected_profit=plan.expected_profit,
        expected_log_growth=plan.expected_log_growth,
        win_probability=plan.win_probability,
        loss_probability=plan.loss_probability,
        worst_case_wealth=plan.worst_case_wealth,
        residual_probability=plan.residual_probability,
        skipped=plan.skipped,
    )


def example_usage() -> None:
    """Print the log-optimal plan for the bundled Argentina/England market."""
    market = load_packaged_market("correct_score_argentina_england.yaml")
    plan = optimize_market(market, model_trust=0.5)
    print(
        f"stake ${plan.staked:.2f} of ${plan.bankroll:.0f} across {len(plan.allocations)} scores; "
        f"cash ${plan.cash_reserve:.2f}; expected profit ${plan.expected_profit:+.2f}"
    )
    for item in plan.allocations:
        print(f"  {item.label}: ${item.stake:.2f} @ {item.ask * 100:.1f}% -> ${item.payout_if_hit:.2f}")


def main() -> None:
    """Module entry point."""
    example_usage()


if __name__ == "__main__":
    main()
