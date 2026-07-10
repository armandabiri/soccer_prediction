"""Player goalscorer/assist market predictions (who might score, score or assist)."""

from __future__ import annotations

import pytest

from soccer_prediction.models import PlayerGame, PlayerStats, ScorelineGrid
from soccer_prediction.predictors import predict_scorers
from soccer_prediction.predictors.scorers import expected_goals_from_grid
from soccer_prediction.public import forecast_fixture
from soccer_prediction.reporting import render_html


def _grid() -> ScorelineGrid:
    return ScorelineGrid(2, 2, ((0.20, 0.10, 0.05), (0.15, 0.12, 0.03), (0.10, 0.05, 0.20)))


def test_expected_goals_from_grid() -> None:
    """Expected goals derived from a grid are positive and finite."""
    home_xg, away_xg = expected_goals_from_grid(_grid())
    assert home_xg > 0.0
    assert away_xg > 0.0


def test_predict_scorers_ranks_and_bounds() -> None:
    """Players rank by anytime probability; score-or-assist dominates anytime."""
    grid = _grid()
    home = [PlayerStats("A", "H", "FW", 50, 20, 5), PlayerStats("B", "H", "MF", 50, 5, 15)]
    away = [PlayerStats("C", "A", "FW", 50, 15, 3)]
    prediction = predict_scorers(grid, home, away)
    assert len(prediction.players) == 3
    anytime = [player.anytime_scorer for player in prediction.players]
    assert anytime == sorted(anytime, reverse=True)
    for player in prediction.players:
        assert 0.0 <= player.anytime_scorer <= 1.0
        assert player.score_probability == player.anytime_scorer
        assert 0.0 <= player.assist_probability <= 1.0
        assert player.to_score_or_assist >= player.anytime_scorer - 1e-9
        assert player.to_score_or_assist >= player.assist_probability - 1e-9
    # first-goalscorer probabilities cannot exceed P(at least one goal) <= 1.
    assert sum(player.first_scorer for player in prediction.players) <= 1.0 + 1e-9


def test_empty_squads_yield_no_players() -> None:
    """No squad data means no player markets, not an error."""
    assert predict_scorers(_grid(), [], []).players == ()


def test_recent_form_is_used_and_fallback_is_marked() -> None:
    """Real recent production affects ranking; aggregate fallback stays explicit."""
    players = [
        PlayerStats("Hot", "H", "FW", 50, 10, 5, 10, 8, 3),
        PlayerStats("Cold", "H", "FW", 50, 10, 5, 10, 0, 1),
        PlayerStats("Estimated", "H", "MF", 40, 8, 12),
    ]
    predictions = predict_scorers(_grid(), players, []).players
    by_name = {player.player: player for player in predictions}
    assert by_name["Hot"].score_probability > by_name["Cold"].score_probability
    assert by_name["Hot"].recent_goals == 8
    assert by_name["Hot"].recent_form_estimated is False
    assert by_name["Estimated"].recent_appearances == 20
    assert by_name["Estimated"].recent_form_estimated is True


def test_recent_form_requires_a_complete_max_20_sample() -> None:
    """Partial or oversized recent-form payloads are rejected."""
    with pytest.raises(ValueError):
        PlayerStats("A", "H", "FW", 10, 2, 1, recent_appearances=10)
    with pytest.raises(ValueError):
        PlayerStats("A", "H", "FW", 30, 3, 2, 21, 3, 2)


def test_forecast_includes_scorers() -> None:
    """A source that exposes squads attaches ranked scorer markets to the forecast."""
    forecast = forecast_fixture("Switzerland", "Colombia", source="bundled_swi_col")
    assert forecast.scorers is not None
    assert len(forecast.scorers.players) == 20
    assert all(0.0 <= player.to_score_or_assist <= 1.0 for player in forecast.scorers.players)
    html = render_html(forecast)
    assert "Recent scoring (max 20)" in html
    assert 'class="formbar"' in html
    assert html.count('class="player-form-row"') == 20
    assert "Recent scoring comparison — all 20 listed players" in html
    assert ">Score</th>" in html
    assert ">Assist</th>" in html


def test_recent_games_derive_aggregate_recent_form() -> None:
    """A recent_games timeline fills the recent_* aggregates from featured games."""
    player = PlayerStats(
        "X",
        "H",
        "FW",
        50,
        10,
        5,
        recent_games=(PlayerGame(True, 1, 1), PlayerGame(False), PlayerGame(True, 0, 1)),
    )
    assert player.recent_appearances == 2
    assert player.recent_goals == 1
    assert player.recent_assists == 2
    assert player.played_in_last(2) == 1  # oldest-to-newest: last two are DNP then a start


def test_player_game_rejects_involvement_without_playing() -> None:
    """A game the player missed cannot record goals or assists."""
    with pytest.raises(ValueError):
        PlayerGame(played=False, goals=1)


def test_recent_absence_damps_markets_and_redistributes_share() -> None:
    """Missing the last five games damps a player's markets below an ever-present twin."""
    ever_present = tuple(PlayerGame(True, 1, 0) for _ in range(10))
    recent_absentee = (*[PlayerGame(True, 1, 0)] * 5, *[PlayerGame(False)] * 5)
    players = [
        PlayerStats("Present", "H", "FW", 50, 10, 5, recent_games=ever_present),
        PlayerStats("Absent", "H", "FW", 50, 10, 5, recent_games=recent_absentee),
    ]
    by_name = {p.player: p for p in predict_scorers(_grid(), players, []).players}
    assert by_name["Absent"].played_last_five == 0
    assert by_name["Present"].played_last_five == 5
    assert by_name["Absent"].recent_availability < by_name["Present"].recent_availability
    assert by_name["Absent"].score_probability < by_name["Present"].score_probability


def test_report_renders_per_game_circles_and_availability() -> None:
    """The bundled squad exposes per-game circles, absences, and availability notes."""
    forecast = forecast_fixture("Spain", "Belgium", source="bundled_esp_bel")
    assert forecast.scorers is not None
    names = {player.player for player in forecast.scorers.players}
    assert {"Mikel Oyarzabal", "Charles De Ketelaere"} <= names  # recent scorers now in the squad
    de_bruyne = next(p for p in forecast.scorers.players if p.player == "Kevin De Bruyne")
    assert de_bruyne.played_last_five <= 1
    assert de_bruyne.recent_availability < 1.0
    html = render_html(forecast)
    assert 'class="form-dots"' in html
    assert "gdot dnp" in html  # at least one did-not-play circle is rendered
    assert "played 1/5 recent" in html


def test_forecast_without_players_has_no_scorers() -> None:
    """The auto source (priors only) produces no player markets."""
    assert forecast_fixture("Switzerland", "Colombia", source="auto").scorers is None
