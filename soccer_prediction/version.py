"""Version helpers for soccer_prediction."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as metadata_version

__all__ = ["__version__", "get_version"]


def get_version() -> str:
    """Return the installed distribution version, or a local fallback."""
    try:
        return metadata_version("soccer-prediction")
    except PackageNotFoundError:
        return "0.1.0"


__version__ = get_version()
