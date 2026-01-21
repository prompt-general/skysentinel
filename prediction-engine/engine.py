from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum
import joblib
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import xgboost as xgb
import lightgbm as lgb
from scipy import stats

class ModelType(Enum):
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    ISOLATION_FOREST = "isolation_forest"
    RANDOM_FOREST = "random_forest"

@dataclass
class Prediction:
    """Prediction result"""
    resource_id: str
    resource_type: str
    violation_probability: float
    confidence: float
    predicted_violations: List[str]
    features: Dict[str, Any]
    explanation: Dict[str, Any]
    timestamp: str

@dataclass
class ModelMetrics:
    """Model performance metrics"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: float
    log_loss: float
    training_time_seconds: float
    last_trained: str
    feature_importance: Dict[str, float]

class BasePredictor(ABC):
    """Base class for all predictors"""
    
    @abstractmethod
    def train(self, features: pd.DataFrame, labels: pd.Series) -> ModelMetrics:
        """Train the model"""
        pass
    
    @abstractmethod
    def predict(self, features: pd.DataFrame) -> List[Prediction]:
        """Make predictions"""
        pass
    
    @abstractmethod
    def save(self, path: str):
        """Save model to disk"""
        pass
    
    @abstractmethod
    def load(self, path: str):
        """Load model from disk"""
        pass
