"""
SkySentinel Prediction Engine API

FastAPI endpoints for ML predictions and training.
"""

from .prediction_api import router

__all__ = ["router"]
