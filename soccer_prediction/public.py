"""Public forecasting facade."""

from __future__ import annotations

import logging

from soccer_prediction.datasources import DataSourceError, get_source
from soccer_prediction.models import Fixture, MarketPrediction, MatchForecast, TeamMatchStats
from soccer_prediction.predictors import CardsPredictor, CornersPredictor, HalfTimePredictor, derive_markets, get_model

__all__ = ["forecast_fixture", "predict_match"]

logger = logging.getLogger(__name__)


def forecast_fixture(
    home: str,
    away: str,
    *,
    model: str = "dixon_coles",
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

    return MatchForecast(
        fixture=Fixture(home_team=home, away_team=away),
        result=result,
        correct_score=correct_score,
        over_under=markets["over_2_5"],
        btts=markets["btts_yes"],
        per_half=half_time.predict(home, away),
        corners=corners.predict(home, away),
        cards=cards.predict(home, away),
        model_name=model,
        generated_notes=tuple(notes),
    )


def predict_match(
    home: str,
    away: str,
    market: str,
    *,
    model: str = "dixon_coles",
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
        history = data_source.fetch_team_history(home) + data_source.fetch_team_history(away)
    except (DataSourceError, KeyError) as exc:
        logger.warning("history load failed for %s v %s from %s: %s", home, away, source, exc)
        return [], [f"history unavailable from {source}: {exc}"]
    return history, [f"loaded {len(history)} history records from {source}"]


def _best_result(markets: dict[str, MarketPrediction]) -> MarketPrediction:
    return max((markets["home_win"], markets["draw"], markets["away_win"]), key=lambda item: item.probability)
