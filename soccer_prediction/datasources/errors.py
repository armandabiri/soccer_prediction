"""Data-source exception types."""

from __future__ import annotations

__all__ = ["DataSourceError", "InsufficientHistoryError"]


class DataSourceError(RuntimeError):
    """Raised when a source cannot fetch or parse soccer data."""


class InsufficientHistoryError(DataSourceError):
    """Raised when no usable historical match records remain."""
