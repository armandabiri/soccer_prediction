"""Team morale proxy and result-confidence interval coverage."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from soccer_prediction.features import RateBook, compute_rates, morale_label, morale_signal
from soccer_prediction.models import TeamMatchStats
from soccer_prediction.predictors.poisson import expected_goals
from soccer_prediction.public import forecast_fixture
from soccer_prediction.reporting import render_html


def _form_history(team: str, *, wins: bool) -> list[TeamMatchStats]:
    today = date.today()
    records: list[TeamMatchStats] = []
    for index in range(5):
        goals_for, goals_against = (2, 0) if wins else (0, 2)
        records.append(
            TeamMatchStats(
                team,
                f"Opponent {index}",
                today - timedelta(days=index * 12),
                index % 2 == 0,
                goals_for,
                goals_against,
                0,
                0,
                5,
                5,
                2,
                0,
                "morale_test",
                datetime.now(UTC),
            )
        )
    return records


def test_winning_and_losing_streaks_create_bounded_morale() -> None:
    """Repeated recent wins and losses move the signal in opposite directions."""
    wins, win_streak = morale_signal(_form_history("A", wins=True), "A", 0.0077)
    losses, loss_streak = morale_signal(_form_history("B", wins=False), "B", 0.0077)
    assert 0.45 < wins <= 1.0
    assert -1.0 <= losses < -0.45
    assert win_streak == 5
    assert loss_streak == -5
    assert morale_label(wins) == "very confident"
    assert morale_label(losses) == "fragile"


def test_morale_changes_expected_goals_without_overriding_strength() -> None:
    """The configured morale edge nudges, rather than replaces, baseline rates."""
    prior = compute_rates([]).global_rates
    neutral = RateBook({}, prior, attack_factors={"a": 1.0, "b": 1.0}, defence_weakness_factors={"a": 1.0, "b": 1.0})
    polarized = RateBook(
        {},
        prior,
        attack_factors={"a": 1.0, "b": 1.0},
        defence_weakness_factors={"a": 1.0, "b": 1.0},
        morale_factors={"a": 1.0, "b": -1.0},
    )
    neutral_home, neutral_away = expected_goals(neutral, "A", "B")
    morale_home, morale_away = expected_goals(polarized, "A", "B")
    assert neutral_home < morale_home <= neutral_home * 1.081
    assert neutral_away > morale_away >= neutral_away * 0.919


def test_result_intervals_and_morale_are_reported() -> None:
    """Every 1X2 point estimate is contained by its displayed interval."""
    forecast = forecast_fixture("Switzerland", "Colombia", source="bundled_swi_col")
    assert forecast.scenario_analysis is not None
    analysis = forecast.scenario_analysis
    probabilities = forecast.correct_score.home_draw_away()
    intervals = (analysis.home_win_interval, analysis.draw_interval, analysis.away_win_interval)
    for probability, (lower, upper) in zip(probabilities, intervals, strict=True):
        assert 0.0 <= lower <= probability <= upper <= 1.0
    html = render_html(forecast)
    assert html.count('class="ci-row"') == 3
    assert "Morale proxy" in html
