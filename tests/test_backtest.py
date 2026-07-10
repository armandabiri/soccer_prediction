"""T18 acceptance: walk-forward backtesting trains only on prior matches."""

from __future__ import annotations

from datetime import UTC, date, datetime

from soccer_prediction.calibration import canonical_matches, walk_forward
from soccer_prediction.models import TeamMatchStats


def test_no_leakage(sample_history: list[TeamMatchStats]) -> None:
    """Walk-forward completes (its internal leakage guard holds) and predicts."""
    result = walk_forward(sample_history, "poisson")
    assert result.count >= 1
    home_matches = sum(1 for record in sample_history if record.is_home)
    # The earliest match has no prior training data and is skipped.
    assert result.count < home_matches
    for prediction in result.predictions:
        assert round(sum(prediction.probabilities), 6) == 1.0
        assert 0 <= prediction.actual_index <= 2


def test_away_only_source_record_is_canonicalized() -> None:
    """Sources exposing only an away-team perspective still contribute one real fixture."""
    record = TeamMatchStats(
        "Away", "Home", date(2025, 2, 1), False, 1, 2, 0, 1, 3, 5, 2, 0, "test", datetime.now(UTC)
    )
    matches = canonical_matches([record])
    assert len(matches) == 1
    assert (matches[0].home_team, matches[0].away_team) == ("Home", "Away")
    assert (matches[0].home_score, matches[0].away_score) == (2, 1)
