"""Team rate computation from normalized history."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from soccer_prediction.models import TeamMatchStats, TeamRates

__all__ = ["RateBook", "compute_rates", "example_usage", "main"]


@dataclass(frozen=True, slots=True)
class RateBook:
    """Computed rates plus global priors."""

    team_rates: dict[str, TeamRates]
    global_rates: TeamRates

    def for_team(self, team: str) -> TeamRates:
        """Return rates for a team or the global prior for unseen teams."""
        return self.team_rates.get(team, self.global_rates)


def compute_rates(history: Sequence[TeamMatchStats], *, today: date | None = None) -> RateBook:
    """Compute shrinkage-adjusted team rates with exponential recency weights."""
    if not history:
        prior = _rates_from_totals(_empty_totals(), 1.0)
        return RateBook(team_rates={}, global_rates=prior)
    totals_by_team: dict[str, dict[str, float]] = {}
    global_totals = _empty_totals()
    anchor = max(record.date for record in history) if today is None else today
    for record in history:
        weight = _recency_weight((anchor - record.date).days)
        team_totals = totals_by_team.setdefault(record.team, _empty_totals())
        _add_record(team_totals, record, weight)
        _add_record(global_totals, record, weight)
    global_rates = _rates_from_totals(global_totals, max(global_totals["weight"], 1.0))
    team_rates = {
        team: _shrink(_rates_from_totals(totals, max(totals["weight"], 1.0)), global_rates, totals["matches"])
        for team, totals in totals_by_team.items()
    }
    return RateBook(team_rates=team_rates, global_rates=global_rates)


def _empty_totals() -> dict[str, float]:
    return {
        "weight": 0.0,
        "matches": 0.0,
        "goals_for": 0.0,
        "goals_against": 0.0,
        "ht_goals_for": 0.0,
        "ht_goals_against": 0.0,
        "corners_for": 0.0,
        "corners_against": 0.0,
        "yellows": 0.0,
        "reds": 0.0,
    }


def _recency_weight(age_days: int) -> float:
    return math.pow(0.5, max(age_days, 0) / 730.0)


def _add_record(totals: dict[str, float], record: TeamMatchStats, weight: float) -> None:
    totals["weight"] += weight
    totals["matches"] += 1.0
    totals["goals_for"] += record.goals_for * weight
    totals["goals_against"] += record.goals_against * weight
    totals["ht_goals_for"] += record.ht_goals_for * weight
    totals["ht_goals_against"] += record.ht_goals_against * weight
    totals["corners_for"] += record.corners_for * weight
    totals["corners_against"] += record.corners_against * weight
    totals["yellows"] += record.yellows * weight
    totals["reds"] += record.reds * weight


def _rates_from_totals(totals: dict[str, float], weight: float) -> TeamRates:
    return TeamRates(
        goals_for=totals["goals_for"] / weight,
        goals_against=totals["goals_against"] / weight,
        ht_goals_for=totals["ht_goals_for"] / weight,
        ht_goals_against=totals["ht_goals_against"] / weight,
        corners_for=totals["corners_for"] / weight,
        corners_against=totals["corners_against"] / weight,
        yellows=totals["yellows"] / weight,
        reds=totals["reds"] / weight,
        sample_size=int(totals["matches"]),
    )


def _shrink(raw: TeamRates, prior: TeamRates, sample_size: float, prior_weight: float = 6.0) -> TeamRates:
    raw_weight = sample_size / (sample_size + prior_weight)
    prior_share = 1.0 - raw_weight
    return TeamRates(
        goals_for=raw.goals_for * raw_weight + prior.goals_for * prior_share,
        goals_against=raw.goals_against * raw_weight + prior.goals_against * prior_share,
        ht_goals_for=raw.ht_goals_for * raw_weight + prior.ht_goals_for * prior_share,
        ht_goals_against=raw.ht_goals_against * raw_weight + prior.ht_goals_against * prior_share,
        corners_for=raw.corners_for * raw_weight + prior.corners_for * prior_share,
        corners_against=raw.corners_against * raw_weight + prior.corners_against * prior_share,
        yellows=raw.yellows * raw_weight + prior.yellows * prior_share,
        reds=raw.reds * raw_weight + prior.reds * prior_share,
        sample_size=raw.sample_size,
    )


def example_usage() -> None:
    """Print an empty rate book."""
    print(compute_rates([]))


def main() -> None:
    """Module entry point."""
    example_usage()
