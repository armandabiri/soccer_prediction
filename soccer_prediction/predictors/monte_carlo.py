"""Reproducible Monte Carlo model with latent match-state uncertainty."""

from __future__ import annotations

import hashlib
import math
import random
from collections.abc import Sequence

from soccer_prediction.config import load_config
from soccer_prediction.features import compute_rates
from soccer_prediction.models import MarketPrediction, ScorelineGrid, TeamMatchStats
from soccer_prediction.predictors.base import register_model
from soccer_prediction.predictors.markets import derive_markets
from soccer_prediction.predictors.poisson import expected_goals

__all__ = ["MonteCarloPredictor"]


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

    def fit(self, history: Sequence[TeamMatchStats]) -> None:
        """Fit baseline goal rates; match-state variation is simulated at prediction time."""
        self._rates = compute_rates(history)

    def predict_scoreline(self, home: str, away: str) -> ScorelineGrid:
        """Simulate and aggregate a deterministic scoreline grid for this fixture."""
        home_mean, away_mean = expected_goals(self._rates, home, away)
        rng = random.Random(_fixture_seed(self.seed, home, away, home_mean, away_mean))
        counts = [[0 for _ in range(self.max_goals + 1)] for _ in range(self.max_goals + 1)]
        for _ in range(self.simulations):
            home_rate, away_rate = _scenario_rates(rng, home_mean, away_mean)
            home_goals = min(self.max_goals, _sample_poisson(rng, home_rate))
            away_goals = min(self.max_goals, _sample_poisson(rng, away_rate))
            counts[home_goals][away_goals] += 1
        rows = tuple(tuple(value / self.simulations for value in row) for row in counts)
        return ScorelineGrid(self.max_goals, self.max_goals, rows)

    def predict_market(self, home: str, away: str, market: str) -> MarketPrediction:
        """Predict a market derived from simulated scorelines."""
        return derive_markets(self.predict_scoreline(home, away))[market]


def _scenario_rates(rng: random.Random, home_mean: float, away_mean: float) -> tuple[float, float]:
    # A shared log-normal tempo shock preserves the baseline mean while widening tails.
    volatility = 0.22
    tempo = rng.lognormvariate(-(volatility**2) / 2.0, volatility)
    roll = rng.random()
    if roll < 0.10:  # Cagey tactical state.
        tempo *= rng.uniform(0.48, 0.75)
    elif roll < 0.20:  # Open/end-to-end state.
        tempo *= rng.uniform(1.35, 1.85)
    elif roll < 0.26:  # Home-side momentum or an early away red card.
        return home_mean * tempo * 1.55, away_mean * tempo * 0.78
    elif roll < 0.32:  # Away-side momentum or an early home red card.
        return home_mean * tempo * 0.78, away_mean * tempo * 1.55
    return home_mean * tempo, away_mean * tempo


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
