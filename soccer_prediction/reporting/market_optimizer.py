"""Load fixture market prices and build a risk-adjusted $100 allocation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from soccer_prediction.models import MatchForecast

__all__ = ["MarketAllocation", "MarketPlan", "optimize_fixture_markets"]


@dataclass(frozen=True, slots=True)
class MarketAllocation:
    category: str
    market: str
    selection: str
    side: str
    model_probability: float
    ask: float
    edge: float
    win_profit: float
    win_roi: float
    loss_probability: float
    utility: float
    stake: float
    expected_profit: float


@dataclass(frozen=True, slots=True)
class MarketPlan:
    source: str
    bankroll: float
    profit_weight: float
    risk_weight: float
    allocations: tuple[MarketAllocation, ...]
    rejected: int


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot load market prices {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"market prices {path} must contain a YAML mapping")
    return payload


def _settings(forecast: MatchForecast) -> tuple[dict[str, Any], dict[str, Any], str] | None:
    data = resources.files("soccer_prediction.example").joinpath("data")
    with resources.as_file(data.joinpath("market_prices_default.yaml")) as defaults_path:
        defaults = _load_yaml(Path(defaults_path))
    home = forecast.fixture.home_team.casefold().replace(" ", "_")
    away = forecast.fixture.away_team.casefold().replace(" ", "_")
    keys = (f"{home}_{away}", f"{away}_{home}")
    for key in keys:
        resource = data.joinpath(f"market_prices_{key}.yaml")
        if resource.is_file():
            with resources.as_file(resource) as path:
                return defaults, _load_yaml(Path(path)), resource.name
    return None


def _optimizer_settings(defaults: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Merge default optimizer knobs with any per-fixture override block."""
    merged = dict(defaults.get("optimizer") or {})
    override = payload.get("optimizer")
    if isinstance(override, dict):
        merged.update(override)
    return merged


def _poisson_at_least(mean: float, goals: int) -> float:
    if goals <= 0:
        return 1.0
    cumulative = sum(math.exp(-mean) * mean**value / math.factorial(value) for value in range(goals))
    return max(0.0, min(1.0, 1.0 - cumulative))


def _goal_means(forecast: MatchForecast) -> tuple[float, float]:
    grid = forecast.correct_score
    home = sum(i * probability for i, row in enumerate(grid.probabilities) for probability in row)
    away = sum(j * probability for row in grid.probabilities for j, probability in enumerate(row))
    return home, away


def _team_side(forecast: MatchForecast, team: str) -> str:
    return "home" if team.casefold() == forecast.fixture.home_team.casefold() else "away"


def _team_name(payload: dict[str, Any], token: str) -> str:
    fixture = payload.get("fixture", {})
    if token not in ("team1", "team2") or not isinstance(fixture, dict):
        return token
    return str(fixture.get(token, token))


def _player(forecast: MatchForecast, name: str) -> Any | None:
    if forecast.scorers is None:
        return None
    wanted = name.casefold()
    return next((item for item in forecast.scorers.players if item.player.casefold() == wanted), None)


def _correct_score_probability(
    forecast: MatchForecast, payload: dict[str, Any], selection: str
) -> tuple[float, str, str] | None:
    parts = selection.split()
    if len(parts) != 2 or "-" not in parts[1]:
        return None
    team = _team_name(payload, parts[0])
    winner_goals, loser_goals = (int(value) for value in parts[1].split("-", 1))
    if _team_side(forecast, team) == "home":
        home_goals, away_goals, side = winner_goals, loser_goals, "home"
    else:
        home_goals, away_goals, side = loser_goals, winner_goals, "away"
    grid = forecast.correct_score
    if home_goals >= grid.home_goals_max or away_goals >= grid.away_goals_max:
        return None
    label = f"{team} {winner_goals}-{loser_goals}" if winner_goals != loser_goals else f"Draw {parts[1]}"
    return grid.cell_probability(home_goals, away_goals), label, side if winner_goals != loser_goals else "draw"


def _probability(
    forecast: MatchForecast, payload: dict[str, Any], offer: dict[str, Any]
) -> tuple[float, str, str] | None:
    market = str(offer.get("market", ""))
    selection = str(offer.get("selection", ""))
    team = _team_name(payload, selection)
    home_mean, away_mean = _goal_means(forecast)
    if market == "to_advance" and forecast.knockout is not None:
        side = _team_side(forecast, team)
        return (forecast.knockout.home_advance if side == "home" else forecast.knockout.away_advance), team, side
    if market == "btts":
        return forecast.correct_score.both_teams_to_score(), "Yes", "draw"
    if market == "second_half_btts":
        return forecast.per_half.second_half_grid.both_teams_to_score(), "Yes", "draw"
    if market == "first_team_to_score":
        if selection == "no_goal":
            return forecast.correct_score.cell_probability(0, 0), "No goal", "draw"
        side = _team_side(forecast, team)
        own, other = (home_mean, away_mean) if side == "home" else (away_mean, home_mean)
        probability = own / max(own + other, 1e-9) * (1.0 - math.exp(-(own + other)))
        return probability, team, side
    if market == "correct_score":
        return _correct_score_probability(forecast, payload, selection)
    if market == "total_corners":
        threshold = int(selection.removesuffix("+"))
        return _poisson_at_least(forecast.corners.total_expected, threshold), f"{threshold}+ corners", "draw"
    if market == "team_corners":
        token, raw = selection.split(":", 1)
        team = _team_name(payload, token)
        side = _team_side(forecast, team)
        mean = forecast.corners.home_expected if side == "home" else forecast.corners.away_expected
        threshold = int(raw.removesuffix("+"))
        return _poisson_at_least(mean, threshold), f"{team} {threshold}+ corners", side
    if market == "player_first_goal" and selection == "no_goal":
        return forecast.correct_score.cell_probability(0, 0), "No goal", "draw"
    if ":" not in selection:
        return None
    name, raw = selection.rsplit(":", 1)
    player = _player(forecast, name)
    if player is None:
        return None
    side = _team_side(forecast, player.team)
    if market in ("player_goals", "player_assists"):
        base = player.score_probability if market == "player_goals" else player.assist_probability
        count = int(raw.removesuffix("+"))
        mean = -math.log(max(1e-9, 1.0 - base))
        return _poisson_at_least(mean, count), f"{name} {count}+", side
    if market == "player_first_goal":
        player_mean = -math.log(max(1e-9, 1.0 - player.score_probability))
        probability = player_mean / max(home_mean + away_mean, 1e-9) * (1.0 - math.exp(-(home_mean + away_mean)))
        return probability, name, side
    if market == "player_score_or_assist":
        probability = 1.0 - (1.0 - player.score_probability) * (1.0 - player.assist_probability)
        return probability, name, side
    return None


def _exposure_key(offer: dict[str, Any]) -> str:
    """Collapse overlapping ladders so one outcome is not funded repeatedly."""
    market = str(offer.get("market", ""))
    selection = str(offer.get("selection", ""))
    if selection == "no_goal" and market in ("first_team_to_score", "player_first_goal"):
        return "match:no_goal"
    if market == "total_corners":
        return market
    if market == "team_corners":
        return f"{market}:{selection.split(':', 1)[0]}"
    if market in ("player_goals", "player_assists"):
        return f"{market}:{selection.rsplit(':', 1)[0].casefold()}"
    return f"{market}:{selection.casefold()}"


@dataclass(frozen=True, slots=True)
class _Candidate:
    """One eligible offer with the two competing quality signals."""

    offer: dict[str, Any]
    probability: float
    label: str
    side: str
    cost: float
    edge: float
    kelly: float  # growth-optimal bet fraction: edge / (1 - cost)


def _collect_candidates(
    forecast: MatchForecast,
    payload: dict[str, Any],
    *,
    fee_rate: float,
    min_edge: float,
    min_probability: float,
) -> tuple[list[_Candidate], int]:
    """Turn configured offers into eligible candidates and count rejections."""
    candidates: list[_Candidate] = []
    rejected = 0
    for raw in payload.get("markets", []):
        if not isinstance(raw, dict):
            continue
        modeled = _probability(forecast, payload, raw)
        ask = float(raw.get("ask", 0))
        if modeled is None or not 0 < ask < 1:
            rejected += 1
            continue
        probability, label, side = modeled
        cost = min(0.99, ask * (1.0 + fee_rate))
        edge = probability - cost
        if edge <= min_edge or probability < min_probability:
            rejected += 1
            continue
        candidates.append(
            _Candidate(raw, probability, label, side, cost, edge, edge / (1.0 - cost))
        )
    return candidates, rejected


def _dedupe_exposures(candidates: list[_Candidate]) -> tuple[list[_Candidate], int]:
    """Keep only the highest-Kelly offer per overlapping outcome (e.g. one corner line)."""
    best: dict[str, _Candidate] = {}
    dropped = 0
    for candidate in candidates:
        key = _exposure_key(candidate.offer)
        incumbent = best.get(key)
        if incumbent is None:
            best[key] = candidate
        elif candidate.kelly > incumbent.kelly:
            best[key] = candidate
            dropped += 1
        else:
            dropped += 1
    return list(best.values()), dropped


def optimize_fixture_markets(forecast: MatchForecast) -> MarketPlan | None:
    """Allocate configured fixture offers by blending expected return and safety.

    The two YAML weights are normalized to sum to one and mixed as a convex
    combination of two per-offer signals, each rescaled to ``[0, 1]`` against the
    strongest candidate so the weights alone decide the tilt:

    * profit signal  = fractional Kelly ``edge / (1 - price)`` (growth-optimal size);
    * safety signal  = model win probability.
    """
    loaded = _settings(forecast)
    if loaded is None:
        return None
    defaults, payload, source = loaded
    optimizer = _optimizer_settings(defaults, payload)
    bankroll = float(optimizer.get("bankroll", 100))
    raw_profit = max(0.0, float(optimizer.get("profit_weight", 0.5)))
    raw_risk = max(0.0, float(optimizer.get("risk_weight", 0.5)))
    total = raw_profit + raw_risk or 1.0
    profit_weight, risk_weight = raw_profit / total, raw_risk / total
    fee_rate = float(optimizer.get("fee_rate", 0))
    min_edge = float(optimizer.get("minimum_edge", 0))
    min_probability = float(optimizer.get("minimum_probability", 0.0))
    max_positions = int(optimizer.get("max_positions", 6))
    max_position = bankroll * float(optimizer.get("max_position_pct", 0.28))
    reserve = bankroll * float(optimizer.get("reserve_pct", 0.05))

    candidates, rejected = _collect_candidates(
        forecast, payload, fee_rate=fee_rate, min_edge=min_edge, min_probability=min_probability
    )
    candidates, dropped = _dedupe_exposures(candidates)
    rejected += dropped
    return build_plan(
        candidates,
        source,
        bankroll=bankroll,
        profit_weight=profit_weight,
        risk_weight=risk_weight,
        max_positions=max_positions,
        max_position=max_position,
        reserve=reserve,
        rejected=rejected,
    )


def _blended_weight(candidate: _Candidate, profit_weight: float, risk_weight: float,
                    best_kelly: float, best_probability: float) -> float:
    """Convex blend of the rescaled profit (Kelly) and safety (probability) signals."""
    return profit_weight * (candidate.kelly / best_kelly) + risk_weight * (candidate.probability / best_probability)


def build_plan(
    candidates: list[_Candidate],
    source: str,
    *,
    bankroll: float,
    profit_weight: float,
    risk_weight: float,
    max_positions: int,
    max_position: float,
    reserve: float,
    rejected: int = 0,
) -> MarketPlan:
    """Rank candidates by the weighted blend, cap the count, and water-fill stakes."""
    if not candidates:
        return MarketPlan(source, bankroll, profit_weight, risk_weight, (), rejected)
    best_kelly = max(candidate.kelly for candidate in candidates) or 1.0
    best_probability = max(candidate.probability for candidate in candidates) or 1.0
    scored = sorted(
        candidates,
        key=lambda c: _blended_weight(c, profit_weight, risk_weight, best_kelly, best_probability),
        reverse=True,
    )
    if len(scored) > max(1, max_positions):
        rejected += len(scored) - max_positions
        scored = scored[:max_positions]

    best_kelly = max(candidate.kelly for candidate in scored) or 1.0
    best_probability = max(candidate.probability for candidate in scored) or 1.0
    weights = [
        _blended_weight(candidate, profit_weight, risk_weight, best_kelly, best_probability)
        for candidate in scored
    ]
    stakes = _water_fill(weights, bankroll - reserve, max_position)

    allocations = [
        MarketAllocation(
            category=str(candidate.offer.get("category", market_label(str(candidate.offer.get("market", ""))))),
            market=market_label(str(candidate.offer.get("market", ""))),
            selection=candidate.label,
            side=candidate.side,
            model_probability=candidate.probability,
            ask=candidate.cost,
            edge=candidate.edge,
            win_profit=1.0 - candidate.cost,
            win_roi=(1.0 - candidate.cost) / candidate.cost,
            loss_probability=1.0 - candidate.probability,
            utility=weight,
            stake=round(stake, 2),
            expected_profit=round(stake * candidate.edge / candidate.cost, 2),
        )
        for candidate, weight, stake in zip(scored, weights, stakes, strict=True)
    ]
    allocations.sort(key=lambda item: (-item.stake, -item.utility, item.selection))
    return MarketPlan(source, bankroll, profit_weight, risk_weight, tuple(allocations), rejected)


def _water_fill(weights: list[float], deployable: float, cap: float) -> list[float]:
    """Split ``deployable`` proportionally to weights, respecting a per-position cap."""
    if deployable <= 0 or not weights:
        return [0.0 for _ in weights]
    stakes = [0.0 for _ in weights]
    open_indexes = list(range(len(weights)))
    remaining = deployable
    while remaining > 0.005 and open_indexes:
        open_weight = sum(weights[index] for index in open_indexes) or 1.0
        newly_capped: list[int] = []
        distributed = 0.0
        for index in open_indexes:
            target = stakes[index] + remaining * weights[index] / open_weight
            if target >= cap:
                distributed += cap - stakes[index]
                stakes[index] = cap
                newly_capped.append(index)
            else:
                distributed += target - stakes[index]
                stakes[index] = target
        remaining -= distributed
        if newly_capped:
            open_indexes = [index for index in open_indexes if index not in newly_capped]
        elif distributed <= 0.005:
            break
    return stakes


def market_label(value: str) -> str:
    return value.replace("_", " ").title()
