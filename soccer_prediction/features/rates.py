"""Team rate computation from normalized history."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date

from soccer_prediction.config import load_config
from soccer_prediction.features.morale import morale_signals
from soccer_prediction.models import TeamMatchStats, TeamRates

__all__ = ["RateBook", "compute_rates", "example_usage", "main"]


@dataclass(frozen=True, slots=True)
class RateBook:
    """Computed rates plus global priors."""

    team_rates: dict[str, TeamRates]
    global_rates: TeamRates
    attack_factors: dict[str, float] = field(default_factory=dict)
    defence_weakness_factors: dict[str, float] = field(default_factory=dict)
    matchup_rates: dict[tuple[str, str], TeamRates] = field(default_factory=dict)
    matchup_effective_samples: dict[tuple[str, str], float] = field(default_factory=dict)
    corner_attack_factors: dict[str, float] = field(default_factory=dict)
    corner_concession_factors: dict[str, float] = field(default_factory=dict)
    morale_factors: dict[str, float] = field(default_factory=dict)

    def for_team(self, team: str) -> TeamRates:
        """Return rates for a team or the global prior for unseen teams."""
        direct = self.team_rates.get(team)
        if direct is not None:
            return direct
        normalized = team.casefold()
        return next(
            (rates for name, rates in self.team_rates.items() if name.casefold() == normalized),
            self.global_rates,
        )

    def attack_for(self, team: str) -> float:
        """Return schedule-adjusted attack strength relative to the history average."""
        return self.attack_factors.get(team.casefold(), 1.0)

    def defence_weakness_for(self, team: str) -> float:
        """Return schedule-adjusted concession tendency; above one is weaker."""
        return self.defence_weakness_factors.get(team.casefold(), 1.0)

    def for_matchup(self, team: str, opponent: str) -> TeamRates | None:
        """Return direct head-to-head rates when those teams previously met."""
        return self.matchup_rates.get((team.casefold(), opponent.casefold()))

    def matchup_effective_sample(self, team: str, opponent: str) -> float:
        """Return the recency-discounted number of direct meetings."""
        return self.matchup_effective_samples.get((team.casefold(), opponent.casefold()), 0.0)

    def corner_attack_for(self, team: str) -> float:
        """Return schedule-adjusted corner production relative to average."""
        return self.corner_attack_factors.get(team.casefold(), 1.0)

    def corner_concession_for(self, team: str) -> float:
        """Return schedule-adjusted corners conceded relative to average."""
        return self.corner_concession_factors.get(team.casefold(), 1.0)

    def morale_for(self, team: str) -> float:
        """Return the bounded recent-results morale proxy for a team."""
        return self.morale_factors.get(team.casefold(), 0.0)


def compute_rates(history: Sequence[TeamMatchStats], *, today: date | None = None) -> RateBook:
    """Compute shrinkage-adjusted team rates with exponential recency weights."""
    if not history:
        prior = _default_prior()
        return RateBook(team_rates={}, global_rates=prior)
    model_config = load_config().model
    totals_by_team: dict[str, dict[str, float]] = {}
    totals_by_matchup: dict[tuple[str, str], dict[str, float]] = {}
    global_totals = _empty_totals()
    weighted_records: list[tuple[TeamMatchStats, float]] = []
    anchor = max(record.date for record in history) if today is None else today
    for record in history:
        if record.date > anchor:
            continue
        age_days = (anchor - record.date).days
        if age_days > model_config.recency_window_days:
            continue
        weight = _recency_weight(age_days, model_config.time_decay_xi)
        weighted_records.append((record, weight))
        team_totals = totals_by_team.setdefault(record.team, _empty_totals())
        matchup_key = (record.team.casefold(), record.opponent.casefold())
        matchup_totals = totals_by_matchup.setdefault(matchup_key, _empty_totals())
        _add_record(team_totals, record, weight)
        _add_record(matchup_totals, record, weight)
        _add_record(global_totals, record, weight)
    if global_totals["matches"] == 0:
        prior = _default_prior()
        return RateBook(team_rates={}, global_rates=prior)
    global_rates = _rates_from_totals(global_totals, max(global_totals["weight"], 1e-9))
    team_rates = {
        team: _shrink(_rates_from_totals(totals, max(totals["weight"], 1e-9)), global_rates, totals["weight"])
        for team, totals in totals_by_team.items()
    }
    matchup_rates = {
        teams: _rates_from_totals(totals, max(totals["weight"], 1e-9))
        for teams, totals in totals_by_matchup.items()
    }
    attack, defence = _network_strengths(weighted_records, max(global_rates.goals_for, 0.8))
    corner_attack, corner_concession = _network_corner_strengths(
        weighted_records,
        max(global_rates.corners_for, 4.0),
    )
    morale = {
        team: signal[0]
        for team, signal in morale_signals(
            tuple(record for record, _weight in weighted_records),
            model_config.morale_decay_xi,
            anchor=anchor,
        ).items()
    }
    return RateBook(
        team_rates=team_rates,
        global_rates=global_rates,
        attack_factors=attack,
        defence_weakness_factors=defence,
        matchup_rates=matchup_rates,
        matchup_effective_samples={teams: totals["weight"] for teams, totals in totals_by_matchup.items()},
        corner_attack_factors=corner_attack,
        corner_concession_factors=corner_concession,
        morale_factors=morale,
    )


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


def _recency_weight(age_days: int, time_decay_xi: float = 0.0039) -> float:
    return math.exp(-max(time_decay_xi, 0.0) * max(age_days, 0))


def _default_prior() -> TeamRates:
    """Return realistic per-team priors for forecasts with sparse or absent data."""
    return TeamRates(
        goals_for=1.35,
        goals_against=1.35,
        ht_goals_for=0.55,
        ht_goals_against=0.55,
        corners_for=5.2,
        corners_against=5.2,
        yellows=2.1,
        reds=0.08,
        sample_size=0,
    )


def _network_strengths(
    weighted_records: Sequence[tuple[TeamMatchStats, float]],
    league_rate: float,
    prior_weight: float = 6.0,
) -> tuple[dict[str, float], dict[str, float]]:
    """Iteratively adjust attack and defence for the strength of connected opponents."""
    names = {
        name.casefold()
        for record, _weight in weighted_records
        for name in (record.team, record.opponent)
    }
    attack = {name: 1.0 for name in names}
    defence = {name: 1.0 for name in names}
    for _ in range(8):
        attack_sum = {name: 0.0 for name in names}
        defence_sum = {name: 0.0 for name in names}
        weights = {name: 0.0 for name in names}
        for record, weight in weighted_records:
            team = record.team.casefold()
            opponent = record.opponent.casefold()
            venue_factor = 1.08 if record.is_home else 0.92
            opponent_venue_factor = 0.92 if record.is_home else 1.08
            attack_sum[team] += weight * record.goals_for / max(
                league_rate * venue_factor * defence[opponent],
                0.1,
            )
            defence_sum[team] += weight * record.goals_against / max(
                league_rate * opponent_venue_factor * attack[opponent],
                0.1,
            )
            weights[team] += weight
        attack = {
            name: min(2.5, max(0.35, (attack_sum[name] + prior_weight) / (weights[name] + prior_weight)))
            for name in names
        }
        defence = {
            name: min(2.5, max(0.35, (defence_sum[name] + prior_weight) / (weights[name] + prior_weight)))
            for name in names
        }
    return attack, defence


def _network_corner_strengths(
    weighted_records: Sequence[tuple[TeamMatchStats, float]],
    league_rate: float,
    prior_weight: float = 6.0,
) -> tuple[dict[str, float], dict[str, float]]:
    """Adjust corner production for the corner strength of connected opponents."""
    usable = tuple(
        (record, weight)
        for record, weight in weighted_records
        if record.corners_for > 0 or record.corners_against > 0
    )
    if not usable:
        return {}, {}
    names = {name.casefold() for record, _weight in usable for name in (record.team, record.opponent)}
    attack = {name: 1.0 for name in names}
    concession = {name: 1.0 for name in names}
    for _ in range(6):
        attack_sum = {name: 0.0 for name in names}
        concession_sum = {name: 0.0 for name in names}
        weights = {name: 0.0 for name in names}
        for record, weight in usable:
            team = record.team.casefold()
            opponent = record.opponent.casefold()
            attack_sum[team] += weight * record.corners_for / max(league_rate * concession[opponent], 0.5)
            concession_sum[team] += weight * record.corners_against / max(league_rate * attack[opponent], 0.5)
            weights[team] += weight
        attack = {
            name: min(2.5, max(0.35, (attack_sum[name] + prior_weight) / (weights[name] + prior_weight)))
            for name in names
        }
        concession = {
            name: min(2.5, max(0.35, (concession_sum[name] + prior_weight) / (weights[name] + prior_weight)))
            for name in names
        }
    return attack, concession


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
