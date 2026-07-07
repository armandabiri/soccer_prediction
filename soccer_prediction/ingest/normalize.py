"""Normalization helpers for source records."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass

from soccer_prediction.datasources.errors import InsufficientHistoryError
from soccer_prediction.ingest.validate import validate_record
from soccer_prediction.models import TeamMatchStats

__all__ = ["NormalizedHistory", "normalize_records"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class NormalizedHistory:
    """Clean records and quarantine count."""

    records: list[TeamMatchStats]
    quarantined: int


def normalize_records(records: Iterable[TeamMatchStats]) -> NormalizedHistory:
    """Validate records and quarantine malformed rows."""
    clean: list[TeamMatchStats] = []
    quarantined = 0
    for record in records:
        errors = validate_record(record)
        if errors:
            quarantined += 1
            logger.warning("quarantined %s vs %s: %s", record.team, record.opponent, "; ".join(errors))
            continue
        clean.append(record)
    if not clean:
        raise InsufficientHistoryError("no valid history records remain after normalization")
    logger.info("normalized %d records; quarantined %d", len(clean), quarantined)
    return NormalizedHistory(records=clean, quarantined=quarantined)
