"""Reproducible Monte Carlo model with data-calibrated match-state uncertainty."""

from __future__ import annotations

import hashlib
import math
import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from soccer_prediction.config import load_config
from soccer_prediction.features import RateBook, compute_rates
from soccer_prediction.models import MarketPrediction, ScorelineGrid, TeamMatchStats
from soccer_prediction.predictors.base import register_model
from soccer_prediction.predictors.markets import derive_markets
from soccer_prediction.predictors.poisson import expected_goals

__all__ = ["MonteCarloPredictor"]


@dataclass(frozen=True, slots=True)
class _ScenarioMix:
    """Mixture weights and volatility fitted from residual goal variance."""

    volatility: float
    cagey: float
    open: float
    home_momentum: float
    away_momentum: float
    mean_factor: float


_DEFAULT_MIX = _ScenarioMix(
    volatility=0.22,
    cagey=0.10,
    open=0.10,
    home_momentum=0.06,
    away_momentum=0.06,
    mean_factor=1.0413,
)


class MonteCarloPredictor:
    """Simulate cagey, open, and one-sided momentum match states."""

    def __init__(
        self,
        max_goals: int | None = None,
        simulations: int | None = None,
        seed: int | None = None,
    ) -> None:
        config = load_config().model
        self.max_goals = config.max_goals if max_goals is None else max_goals
        self.simulations = config.scenario_simulations if simulations is None else simulations
        self.seed = config.random_seed if seed is None else seed
        if self.simulations <= 0:
            raise ValueError("simulations must be positive")
        self._rates = compute_rates([])
        self._mix = _DEFAULT_MIX

    def fit(self, history: Sequence[TeamMatchStats], *, as_of: date | None = None) -> None:
        """Fit baseline rates and calibrate the latent match-state mixture."""
        visible = tuple(record for record in history if as_of is None or record.date <= as_of)
        self._rates = compute_rates(visible, today=as_of)
        self._mix = _estimate_scenario_mix(visible, self._rates, as_of=as_of)

    def predict_scoreline(self, home: str, away: str, *, neutral_venue: bool = False) -> ScorelineGrid:
        """Simulate and aggregate a deterministic scoreline grid for this fixture."""
        home_mean, away_mean = expected_goals(self._rates, home, away, neutral_venue=neutral_venue)
        rng = random.Random(_fixture_seed(self.seed, home, away, home_mean, away_mean))
        counts = [[0 for _ in range(self.max_goals + 1)] for _ in range(self.max_goals + 1)]
        for _ in range(self.simulations):
            home_rate, away_rate = _scenario_rates(rng, home_mean, away_mean, self._mix)
            home_goals = min(self.max_goals, _sample_poisson(rng, home_rate))
            away_goals = min(self.max_goals, _sample_poisson(rng, away_rate))
            counts[home_goals][away_goals] += 1
        rows = tuple(tuple(value / self.simulations for value in row) for row in counts)
        return ScorelineGrid(self.max_goals, self.max_goals, rows)

    def predict_market(
        self, home: str, away: str, market: str, *, neutral_venue: bool = False
    ) -> MarketPrediction:
        """Predict a market derived from simulated scorelines."""
        return derive_markets(self.predict_scoreline(home, away, neutral_venue=neutral_venue))[market]


def _estimate_scenario_mix(
    history: Sequence[TeamMatchStats],
    rates: RateBook,
    *,
    as_of: date | None,
) -> _ScenarioMix:
    """Widen cagey/open share when observed totals are more dispersed than Poisson."""
    if len(history) < 16:
        return _DEFAULT_MIX
    residuals: list[float] = []
    for record in history:
        if as_of is not None and record.date > as_of:
            continue
        if not record.is_home:
            continue
        home_mean, away_mean = expected_goals(rates, record.team, record.opponent, neutral_venue=False)
        expected_total = home_mean + away_mean
        observed_total = float(record.goals_for + record.goals_against)
        residuals.append(observed_total - expected_total)
    if len(residuals) < 10:
        return _DEFAULT_MIX
    mean_residual = sum(residuals) / len(residuals)
    variance = sum((value - mean_residual) ** 2 for value in residuals) / (len(residuals) - 1)
    poisson_scale = max(2.2, abs(mean_residual) + 2.2)
    excess = max(0.0, variance / poisson_scale - 1.0)
    volatility = min(0.38, max(0.16, 0.18 + 0.10 * excess))
    cagey = min(0.18, max(0.06, 0.08 + 0.06 * excess))
    open_share = min(0.18, max(0.06, 0.08 + 0.06 * excess))
    momentum = min(0.10, max(0.04, 0.05 + 0.03 * excess))
    draft = _ScenarioMix(
        volatility=volatility,
        cagey=cagey,
        open=open_share,
        home_momentum=momentum,
        away_momentum=momentum,
        mean_factor=1.0,
    )
    return _ScenarioMix(
        volatility=draft.volatility,
        cagey=draft.cagey,
        open=draft.open,
        home_momentum=draft.home_momentum,
        away_momentum=draft.away_momentum,
        mean_factor=_empirical_mean_factor(draft),
    )


def _empirical_mean_factor(mix: _ScenarioMix) -> float:
    """Estimate multiplicative bias of the scenario mix so expected goals stay centered."""
    rng = random.Random(2026)
    home_mean = away_mean = 1.3
    total = 0.0
    trials = 8_000
    centered = _ScenarioMix(
        volatility=mix.volatility,
        cagey=mix.cagey,
        open=mix.open,
        home_momentum=mix.home_momentum,
        away_momentum=mix.away_momentum,
        mean_factor=1.0,
    )
    for _ in range(trials):
        home_rate, away_rate = _scenario_rates(rng, home_mean, away_mean, centered)
        total += home_rate + away_rate
    return max(0.95, min(1.12, total / (trials * (home_mean + away_mean))))


def _scenario_rates(
    rng: random.Random, home_mean: float, away_mean: float, mix: _ScenarioMix
) -> tuple[float, float]:
    volatility = mix.volatility
    tempo = rng.lognormvariate(-(volatility**2) / 2.0, volatility)
    roll = rng.random()
    cagey_end = mix.cagey
    open_end = cagey_end + mix.open
    home_end = open_end + mix.home_momentum
    away_end = home_end + mix.away_momentum
    factor = max(mix.mean_factor, 1e-6)
    if roll < cagey_end:
        tempo *= rng.uniform(0.48, 0.75)
    elif roll < open_end:
        tempo *= rng.uniform(1.35, 1.85)
    elif roll < home_end:
        return home_mean * tempo * 1.55 / factor, away_mean * tempo * 0.78 / factor
    elif roll < away_end:
        return home_mean * tempo * 0.78 / factor, away_mean * tempo * 1.55 / factor
    return home_mean * tempo / factor, away_mean * tempo / factor


def _sample_poisson(rng: random.Random, rate: float) -> int:
    threshold = math.exp(-rate)
    product = 1.0
    count = 0
    while product > threshold:
        count += 1
        product *= rng.random()
    return count - 1


def _fixture_seed(seed: int, home: str, away: str, home_mean: float, away_mean: float) -> int:
    payload = f"{seed}|{home.casefold()}|{away.casefold()}|{home_mean:.8f}|{away_mean:.8f}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


@register_model("monte_carlo")
def _factory() -> MonteCarloPredictor:
    return MonteCarloPredictor()
