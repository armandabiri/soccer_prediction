"""Public forecasting facade."""

from __future__ import annotations

import logging

from soccer_prediction.config import load_config
from soccer_prediction.datasources import DataSource, DataSourceError, PlayerSource, get_source
from soccer_prediction.features import build_matchup_context
from soccer_prediction.models import (
    Fixture,
    MarketPrediction,
    MatchForecast,
    ScorelineGrid,
    ScorerPrediction,
    TeamMatchStats,
)
from soccer_prediction.predictors import (
    CardsPredictor,
    CornersPredictor,
    HalfTimePredictor,
    build_scenario_analysis,
    derive_markets,
    get_model,
    predict_knockout,
    predict_scorers,
)

__all__ = ["forecast_fixture", "predict_match"]

logger = logging.getLogger(__name__)


def forecast_fixture(
    home: str,
    away: str,
    *,
    model: str = "ensemble",
    source: str = "auto",
) -> MatchForecast:
    """Forecast a fixture across scoreline, totals, BTTS, corners, cards, and per-half markets."""
    history, notes = _load_history(home, away, source)
    goal_model = get_model(model)
    goal_model.fit(history)
    correct_score = goal_model.predict_scoreline(home, away)
    markets = derive_markets(correct_score)
    result = _best_result(markets)

    half_time = HalfTimePredictor()
    half_time.fit(history)
    corners = CornersPredictor()
    corners.fit(history)
    cards = CardsPredictor()
    cards.fit(history)
    per_half_prediction = half_time.predict(home, away)
    corners_prediction = corners.predict(home, away)
    cards_prediction = cards.predict(home, away)
    scenario_analysis = build_scenario_analysis(history, home, away, correct_score)

    return MatchForecast(
        fixture=Fixture(home_team=home, away_team=away),
        result=result,
        correct_score=correct_score,
        over_under=markets["over_2_5"],
        btts=markets["btts_yes"],
        per_half=per_half_prediction,
        corners=corners_prediction,
        cards=cards_prediction,
        model_name=model,
        generated_notes=tuple(notes),
        history=tuple(history),
        scorers=_load_scorers(source, home, away, correct_score),
        knockout=predict_knockout(correct_score),
        scenario_analysis=scenario_analysis,
        matchup_context=build_matchup_context(
            history,
            home,
            away,
            correct_score,
            corners_prediction,
            cards_prediction,
        ),
    )


def predict_match(
    home: str,
    away: str,
    market: str,
    *,
    model: str = "ensemble",
    source: str = "auto",
) -> MarketPrediction:
    """Forecast a single market for a fixture."""
    forecast = forecast_fixture(home, away, model=model, source=source)
    if market == "result":
        return forecast.result
    if market == "over_under":
        return forecast.over_under
    if market == "btts":
        return forecast.btts
    return derive_markets(forecast.correct_score)[market]


def _load_history(home: str, away: str, source: str) -> tuple[list[TeamMatchStats], list[str]]:
    if source == "auto":
        return [], ["source=auto used model priors; no live data source was queried"]
    try:
        data_source = get_source(source)
    except KeyError as exc:
        logger.warning("history load failed for %s v %s from %s: %s", home, away, source, exc)
        return [], [f"history unavailable from {source}: {exc}"]
    history, teams, failures = _load_opponent_network(data_source, home, away)
    depth = max(0, load_config().model.opponent_network_depth)
    notes = [
        f"loaded {len(history)} history records for {teams} team histories from {source} "
        f"(opponent-network depth {depth})"
    ]
    notes.extend(failures)
    return history, notes


def _load_opponent_network(
    data_source: DataSource,
    home: str,
    away: str,
) -> tuple[list[TeamMatchStats], int, list[str]]:
    """Load target histories plus a bounded, recent opponent graph."""
    config = load_config().model
    depth = max(0, config.opponent_network_depth)
    max_teams = max(2, config.opponent_network_max_teams)
    fetched: set[str] = set()
    successful: set[str] = set()
    frontier = [home, away]
    history: list[TeamMatchStats] = []
    failures: list[str] = []
    for _level in range(depth + 1):
        frontier_records: list[TeamMatchStats] = []
        for team in frontier:
            key = team.casefold()
            if key in fetched or len(fetched) >= max_teams:
                continue
            fetched.add(key)
            try:
                records = data_source.fetch_team_history(team)
            except (DataSourceError, OSError) as exc:
                logger.warning("opponent-network history failed for %s: %s", team, exc)
                failures.append(f"history unavailable for connected team {team}: {exc}")
                continue
            if records:
                successful.add(key)
            history.extend(records)
            frontier_records.extend(records)
        slots = max_teams - len(fetched)
        if slots <= 0:
            break
        next_frontier: list[str] = []
        queued: set[str] = set()
        for record in sorted(frontier_records, key=lambda item: item.date, reverse=True):
            opponent_key = record.opponent.casefold()
            if opponent_key in fetched or opponent_key in queued:
                continue
            queued.add(opponent_key)
            next_frontier.append(record.opponent)
            if len(next_frontier) >= slots:
                break
        frontier = next_frontier
        if not frontier:
            break
    return _deduplicate_history(history), len(successful), failures


def _deduplicate_history(history: list[TeamMatchStats]) -> list[TeamMatchStats]:
    unique: dict[tuple[object, ...], TeamMatchStats] = {}
    for record in history:
        key = (
            record.team.casefold(),
            record.opponent.casefold(),
            record.date,
            record.is_home,
            record.goals_for,
            record.goals_against,
            record.ht_goals_for,
            record.ht_goals_against,
            record.corners_for,
            record.corners_against,
            record.yellows,
            record.reds,
        )
        unique[key] = record
    return sorted(unique.values(), key=lambda item: item.date, reverse=True)


def _load_scorers(source: str, home: str, away: str, grid: ScorelineGrid) -> ScorerPrediction | None:
    if source == "auto":
        return None
    try:
        data_source = get_source(source)
    except KeyError:
        return None
    if not isinstance(data_source, PlayerSource):
        return None
    home_players = data_source.fetch_players(home)
    away_players = data_source.fetch_players(away)
    if not home_players and not away_players:
        return None
    return predict_scorers(grid, home_players, away_players)


def _best_result(markets: dict[str, MarketPrediction]) -> MarketPrediction:
    return max((markets["home_win"], markets["draw"], markets["away_win"]), key=lambda item: item.probability)
