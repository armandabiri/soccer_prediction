"""Forecast-to-quote mapping and uncertainty-adjusted value screening."""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from soccer_prediction.models import ContractEvaluation, ContractQuote, MatchForecast, StrategyRequest

__all__ = ["evaluate_contracts"]


def _d(value: float) -> Decimal:
    return Decimal(str(value))


def _score_probability(forecast: MatchForecast, selection: str) -> Decimal | None:
    try:
        home, away = (int(value) for value in selection.split("-", 1))
    except (ValueError, TypeError):
        return None
    grid = forecast.correct_score
    if home >= grid.home_goals_max or away >= grid.away_goals_max or min(home, away) < 0:
        return None
    return _d(grid.cell_probability(home, away))


def _player_probability(forecast: MatchForecast, selection: str) -> Decimal | None:
    if forecast.scorers is None:
        return None
    wanted = selection.casefold()
    for player in forecast.scorers.players:
        if player.player.casefold() == wanted:
            return _d(player.score_probability)
    return None


def _probability(forecast: MatchForecast, quote: ContractQuote) -> Decimal | None:
    selection = quote.selection.casefold().replace(" ", "_")
    if quote.market == "correct_score":
        return _score_probability(forecast, quote.selection)
    if quote.market == "match_result":
        values = forecast.correct_score.home_draw_away()
        return dict(zip(("home", "draw", "away"), map(_d, values), strict=True)).get(selection)
    if quote.market == "btts":
        yes = _d(forecast.correct_score.both_teams_to_score())
        return {"yes": yes, "no": Decimal(1) - yes}.get(selection)
    if quote.market == "total_goals":
        under, over = map(_d, forecast.correct_score.over_under(2.5))
        return {"over": over, "over_2.5": over, "under": under, "under_2.5": under}.get(selection)
    if quote.market == "second_half_result":
        values = forecast.per_half.second_half_grid.home_draw_away()
        return dict(zip(("home", "draw", "away"), map(_d, values), strict=True)).get(selection)
    if quote.market == "player_to_score":
        return _player_probability(forecast, quote.selection)
    return None


def _conservative(forecast: MatchForecast, quote: ContractQuote, probability: Decimal, margin: Decimal) -> Decimal:
    analysis = forecast.scenario_analysis
    if quote.market == "match_result" and analysis is not None:
        bounds = {
            "home": analysis.home_win_interval[0],
            "draw": analysis.draw_interval[0],
            "away": analysis.away_win_interval[0],
        }
        lower = bounds.get(quote.selection.casefold())
        if lower is not None:
            return max(Decimal(0), min(probability, _d(lower)))
    return max(Decimal(0), probability - margin)


def _round_tick(value: Decimal, tick: Decimal) -> Decimal:
    return (value / tick).to_integral_value(rounding=ROUND_DOWN) * tick


def _evaluate(forecast: MatchForecast, quote: ContractQuote, request: StrategyRequest) -> ContractEvaluation:
    probability = _probability(forecast, quote)
    if probability is None:
        return ContractEvaluation(quote, None, None, None, None, None, None, None, False,
                                  "No matching model probability is available.", "excluded")
    conservative = _conservative(forecast, quote, probability, request.safety_margin)
    all_in = quote.ask + quote.ask * quote.buy_fee_rate + request.slippage
    raw_edge = probability - quote.ask
    net_edge = conservative - all_in
    value_limit = max(Decimal(0), conservative - quote.ask * quote.buy_fee_rate - request.slippage)
    max_buy = _round_tick(value_limit, quote.tick_size)
    enough_size = quote.available_at_ask >= quote.quantity_step
    eligible = net_edge > 0 and enough_size and max_buy >= quote.ask
    if not enough_size:
        reason = "Excluded: ask-side liquidity is below the minimum quantity step."
    elif net_edge <= 0:
        reason = "Excluded: uncertainty-adjusted edge is not positive after costs."
    elif max_buy < quote.ask:
        reason = "Excluded: executable ask exceeds the maximum limit-buy price."
    else:
        reason = "Included: executable ask is below conservative fair value after costs."
    intent = "live trading" if quote.market == "correct_score" else "final settlement"
    return ContractEvaluation(
        quote, probability, conservative, probability, raw_edge, net_edge, all_in, max_buy, eligible, reason, intent
    )


def evaluate_contracts(
    forecast: MatchForecast,
    quotes: tuple[ContractQuote, ...],
    request: StrategyRequest,
) -> tuple[ContractEvaluation, ...]:
    """Compare every quote with the matching forecast probability."""
    return tuple(_evaluate(forecast, quote, request) for quote in quotes)
