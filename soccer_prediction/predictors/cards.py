"""Cards predictor."""

from __future__ import annotations

from collections.abc import Sequence

from soccer_prediction.features import compute_rates
from soccer_prediction.models import CardsPrediction, TeamMatchStats, TeamRates
from soccer_prediction.predictors.poisson import poisson_tail_at_least

__all__ = ["CardsPredictor"]

# League-average per-team card rates, used when the data source carries no card
# data (e.g. martj42 international results, which provide goals only).
_PRIOR_YELLOWS = 1.9
_PRIOR_REDS = 0.07


def _team_cards(rates: TeamRates) -> tuple[float, float]:
    """Observed yellow/red rates, or league-average priors when cards are absent."""
    if rates.yellows > 0.2:
        return rates.yellows, rates.reds
    return _PRIOR_YELLOWS, _PRIOR_REDS


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
        home_yellows, home_reds = _team_cards(self._rates.for_team(home))
        away_yellows, away_reds = _team_cards(self._rates.for_team(away))
        yellows = (home_yellows * 0.88 + away_yellows) * self.referee_multiplier
        reds = (home_reds * 0.88 + away_reds) * self.referee_multiplier
        total = max(0.0, yellows + reds)
        lines = {line: poisson_tail_at_least(total, int(line + 0.5)) for line in (2.5, 3.5, 4.5, 5.5)}
        return CardsPrediction(yellows, reds, total, lines, yellows * 10.0 + reds * 25.0)
