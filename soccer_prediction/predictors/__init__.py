"""Prediction model implementations."""

from __future__ import annotations

from soccer_prediction.predictors.analysis import build_scenario_analysis
from soccer_prediction.predictors.base import Predictor, get_model, list_models, register_model
from soccer_prediction.predictors.bivariate_poisson import BivariatePoissonPredictor
from soccer_prediction.predictors.cards import CardsPredictor
from soccer_prediction.predictors.corners import CornersPredictor
from soccer_prediction.predictors.dixon_coles import DixonColesPredictor
from soccer_prediction.predictors.ensemble import EnsemblePredictor
from soccer_prediction.predictors.half_time import HalfTimePredictor
from soccer_prediction.predictors.knockout import predict_knockout, shootout_win_probability
from soccer_prediction.predictors.markets import derive_markets
from soccer_prediction.predictors.monte_carlo import MonteCarloPredictor
from soccer_prediction.predictors.negative_binomial import NegativeBinomialPredictor
from soccer_prediction.predictors.poisson import PoissonPredictor
from soccer_prediction.predictors.scorers import predict_scorers

__all__ = [
    "CardsPredictor",
    "BivariatePoissonPredictor",
    "CornersPredictor",
    "DixonColesPredictor",
    "EnsemblePredictor",
    "HalfTimePredictor",
    "PoissonPredictor",
    "MonteCarloPredictor",
    "NegativeBinomialPredictor",
    "Predictor",
    "derive_markets",
    "build_scenario_analysis",
    "get_model",
    "list_models",
    "predict_knockout",
    "predict_scorers",
    "register_model",
    "shootout_win_probability",
]
