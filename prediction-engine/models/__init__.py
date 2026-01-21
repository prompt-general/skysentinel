"""
SkySentinel Prediction Engine Models

Specialized ML model implementations for violation prediction.
"""

from .xgboost_predictor import XGBoostPredictor

__all__ = [
    "XGBoostPredictor"
]
