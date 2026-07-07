"""Cards predictor."""

from __future__ import annotations

from collections.abc import Sequence

from soccer_prediction.features import compute_rates
from soccer_prediction.models import CardsPrediction, TeamMatchStats
from soccer_prediction.predictors.poisson import poisson_tail_at_least

__all__ = ["CardsPredictor"]


class CardsPredictor:
    """Poisson card model; COM-Poisson is a future under-dispersion upgrade."""

    def __init__(self, referee_multiplier: float = 1.0) -> None:
        self.referee_multiplier = referee_multiplier
        self._rates = compute_rates([])

    def fit(self, history: Sequence[TeamMatchStats]) -> None:
        """Fit yellow/red card rates."""
        self._rates = compute_rates(history)

    def predict(self, home: str, away: str) -> CardsPrediction:
        """Return card expectations and line probabilities."""
        home_rates = self._rates.for_team(home)
        away_rates = self._rates.for_team(away)
        yellows = (home_rates.yellows * 0.88 + away_rates.yellows) * self.referee_multiplier
        reds = (home_rates.reds * 0.88 + away_rates.reds) * self.referee_multiplier
        total = max(0.0, yellows + reds)
        lines = {line: poisson_tail_at_least(total, int(line + 0.5)) for line in (2.5, 3.5, 4.5, 5.5)}
        return CardsPrediction(yellows, reds, total, lines, yellows * 10.0 + reds * 25.0)
