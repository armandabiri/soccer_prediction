"""Ingest normalization and validation."""

from __future__ import annotations

from soccer_prediction.ingest.normalize import NormalizedHistory, normalize_records
from soccer_prediction.ingest.validate import validate_record

__all__ = ["NormalizedHistory", "normalize_records", "validate_record"]
