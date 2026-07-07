"""T11 acceptance: the predictor registry resolves models and rejects unknowns."""

from __future__ import annotations

import pytest

from soccer_prediction.predictors import get_model, list_models


def test_registry() -> None:
    """Built-in models resolve and unknown names raise a helpful error."""
    names = set(list_models())
    assert {"poisson", "dixon_coles"} <= names
    model = get_model("Dixon-Coles")
    assert hasattr(model, "predict_scoreline")
    with pytest.raises(KeyError):
        get_model("no_such_model")
