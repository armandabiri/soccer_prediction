"""T14 acceptance: markets derived from a grid are consistent with it."""

from __future__ import annotations

from soccer_prediction.models import ScorelineGrid
from soccer_prediction.predictors import derive_markets


def _grid() -> ScorelineGrid:
    return ScorelineGrid(2, 2, ((0.20, 0.10, 0.05), (0.15, 0.12, 0.03), (0.10, 0.05, 0.20)))


def test_1x2_sums_to_one() -> None:
    """Home, draw, and away market probabilities sum to one."""
    markets = derive_markets(_grid())
    total = markets["home_win"].probability + markets["draw"].probability + markets["away_win"].probability
    assert round(total, 6) == 1.0


def test_btts_matches_grid() -> None:
    """The BTTS market matches the grid's both-teams-to-score mass."""
    grid = _grid()
    markets = derive_markets(grid)
    assert abs(markets["btts_yes"].probability - grid.both_teams_to_score()) < 1e-9
