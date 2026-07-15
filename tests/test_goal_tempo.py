"""Regression checks for Spain/France 2-0 feedback and elite-match tempo."""

from __future__ import annotations

from datetime import date

from soccer_prediction.example.fixture_example import load_history
from soccer_prediction.features import compute_rates
from soccer_prediction.predictors import get_model
from soccer_prediction.predictors.poisson import expected_goals


def test_spain_france_prematch_favours_spain_and_keeps_sensible_totals() -> None:
    """Spain beat France 2-0; pre-match forecast should lean Spain without over-scoring."""
    history = [record for record in load_history("spain_france") if record.date < date(2026, 7, 14)]
    rates = compute_rates(history, today=date(2026, 7, 13))
    home_lambda, away_lambda = expected_goals(rates, "Spain", "France", neutral_venue=True)
    # Actual total was 2; avoid the earlier ~3.8 open-game overshoot.
    assert 2.2 <= home_lambda + away_lambda <= 3.4
    assert home_lambda >= away_lambda

    model = get_model("ensemble")
    model.fit(history, as_of=date(2026, 7, 13))
    grid = model.predict_scoreline("Spain", "France", neutral_venue=True)
    home_p, _draw_p, away_p = grid.home_draw_away()
    assert home_p > away_p
    assert grid.cell_probability(2, 0) >= grid.cell_probability(0, 2)
    ranked = sorted(
        ((f"{i}-{j}", probability) for i, row in enumerate(grid.probabilities) for j, probability in enumerate(row)),
        key=lambda item: -item[1],
    )
    top_labels = {label for label, _probability in ranked[:8]}
    assert "2-0" in top_labels or "1-0" in top_labels or "2-1" in top_labels


def test_bundled_history_records_spain_france_2_0() -> None:
    """Bundled Spain/France history stores the corrected 2-0 result."""
    rows = [
        record
        for record in load_history("spain_france")
        if record.date == date(2026, 7, 14) and {record.team, record.opponent} == {"Spain", "France"}
    ]
    assert len(rows) == 2
    spain = next(record for record in rows if record.team == "Spain")
    france = next(record for record in rows if record.team == "France")
    assert (spain.goals_for, spain.goals_against) == (2, 0)
    assert (france.goals_for, france.goals_against) == (0, 2)


def test_mismatch_still_produces_usable_totals() -> None:
    """A mismatch forecast stays in a sane goal range."""
    history = load_history("argentina_egypt")
    rates = compute_rates(history)
    home_lambda, away_lambda = expected_goals(rates, "Argentina", "Egypt", neutral_venue=True)
    assert 1.5 <= home_lambda + away_lambda <= 6.0
