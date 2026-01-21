"""
SkySentinel Prediction Engine

A comprehensive ML-based prediction engine for cloud security policy violations.
Supports multiple model types including XGBoost, LightGBM, Isolation Forest, and Random Forest.
"""

from .engine import BasePredictor, Prediction, ModelMetrics, ModelType
from .predictors import (
    XGBoostPredictor, 
    LightGBMPredictor, 
    IsolationForestPredictor, 
    RandomForestPredictor
)
from .service import PredictionEngine

__version__ = "1.0.0"
__author__ = "SkySentinel Team"

__all__ = [
    "BasePredictor",
    "Prediction", 
    "ModelMetrics",
    "ModelType",
    "XGBoostPredictor",
    "LightGBMPredictor", 
    "IsolationForestPredictor",
    "RandomForestPredictor",
    "PredictionEngine"
]
