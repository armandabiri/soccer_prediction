"""Market derivation from scoreline grids."""

from __future__ import annotations

from soccer_prediction.models import MarketPrediction, ScorelineGrid

__all__ = ["derive_markets", "example_usage", "main"]


def derive_markets(grid: ScorelineGrid) -> dict[str, MarketPrediction]:
    """Derive mutually consistent markets from one scoreline grid."""
    home, draw, away = grid.home_draw_away()
    btts = grid.both_teams_to_score()
    under_25, over_25 = grid.over_under(2.5)
    best_score = _best_score(grid)
    return {
        "home_win": MarketPrediction("1x2", "home", home),
        "draw": MarketPrediction("1x2", "draw", draw),
        "away_win": MarketPrediction("1x2", "away", away),
        "btts_yes": MarketPrediction("btts", "yes", btts),
        "btts_no": MarketPrediction("btts", "no", 1.0 - btts),
        "over_2_5": MarketPrediction("total_goals", "over", over_25, 2.5),
        "under_2_5": MarketPrediction("total_goals", "under", under_25, 2.5),
        "correct_score": MarketPrediction("correct_score", best_score[0], best_score[1]),
    }


def _best_score(grid: ScorelineGrid) -> tuple[str, float]:
    best_label = "0-0"
    best_prob = 0.0
    for home_goals, row in enumerate(grid.probabilities):
        for away_goals, probability in enumerate(row):
            if probability > best_prob:
                best_label = f"{home_goals}-{away_goals}"
                best_prob = probability
    return best_label, best_prob


def example_usage() -> None:
    """Print derived markets for a tiny grid."""
    grid = ScorelineGrid(1, 1, ((0.25, 0.25), (0.25, 0.25)))
    print(derive_markets(grid)["home_win"])


def main() -> None:
    """Module entry point."""
    example_usage()
