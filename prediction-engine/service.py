from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime, timedelta
import logging
from pathlib import Path

from .engine import BasePredictor, ModelType, Prediction, ModelMetrics
from .predictors import XGBoostPredictor, LightGBMPredictor, IsolationForestPredictor, RandomForestPredictor

logger = logging.getLogger(__name__)

class PredictionEngine:
    """Main prediction engine service"""
    
    def __init__(self, model_dir: str = "models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        
        self.predictors = {
            ModelType.XGBOOST: XGBoostPredictor(),
            ModelType.LIGHTGBM: LightGBMPredictor(),
            ModelType.ISOLATION_FOREST: IsolationForestPredictor(),
            ModelType.RANDOM_FOREST: RandomForestPredictor()
        }
        
        self.active_predictor = None
        self.model_metrics = {}
        
    def set_predictor(self, model_type: ModelType):
        """Set the active predictor"""
        self.active_predictor = self.predictors[model_type]
        logger.info(f"Set active predictor to {model_type.value}")
    
    def train_model(self, model_type: ModelType, features: pd.DataFrame, labels: pd.Series) -> ModelMetrics:
        """Train a specific model"""
        predictor = self.predictors[model_type]
        
        logger.info(f"Training {model_type.value} model with {len(features)} samples")
        
        try:
            metrics = predictor.train(features, labels)
            self.model_metrics[model_type.value] = metrics
            
            # Save the trained model
            model_path = self.model_dir / f"{model_type.value}_model.joblib"
            predictor.save(str(model_path))
            
            logger.info(f"Successfully trained {model_type.value} model")
            return metrics
            
        except Exception as e:
            logger.error(f"Error training {model_type.value} model: {e}")
            raise
    
    def predict_violations(self, features: pd.DataFrame, model_type: Optional[ModelType] = None) -> List[Prediction]:
        """Make predictions using specified or active model"""
        if model_type:
            predictor = self.predictors[model_type]
        elif self.active_predictor:
            predictor = self.active_predictor
        else:
            raise ValueError("No predictor specified or active")
        
        logger.info(f"Making predictions for {len(features)} resources")
        
        try:
            predictions = predictor.predict(features)
            logger.info(f"Generated {len(predictions)} predictions")
            return predictions
            
        except Exception as e:
            logger.error(f"Error making predictions: {e}")
            raise
    
    def load_model(self, model_type: ModelType, model_path: str):
        """Load a trained model"""
        predictor = self.predictors[model_type]
        
        try:
            predictor.load(model_path)
            logger.info(f"Loaded {model_type.value} model from {model_path}")
            
        except Exception as e:
            logger.error(f"Error loading {model_type.value} model: {e}")
            raise
    
    def get_model_metrics(self, model_type: ModelType) -> Optional[ModelMetrics]:
        """Get metrics for a trained model"""
        return self.model_metrics.get(model_type.value)
    
    def compare_models(self, features: pd.DataFrame, labels: pd.Series) -> Dict[str, ModelMetrics]:
        """Compare all models on the same dataset"""
        results = {}
        
        for model_type in ModelType:
            logger.info(f"Evaluating {model_type.value} model")
            
            try:
                metrics = self.train_model(model_type, features, labels)
                results[model_type.value] = metrics
                
            except Exception as e:
                logger.error(f"Error evaluating {model_type.value} model: {e}")
                continue
        
        return results
    
    def get_best_model(self, metrics: Dict[str, ModelMetrics], metric: str = 'f1_score') -> ModelType:
        """Get the best performing model based on a metric"""
        best_model = None
        best_score = -1
        
        for model_name, model_metrics in metrics.items():
            score = getattr(model_metrics, metric)
            if score > best_score:
                best_score = score
                best_model = ModelType(model_name)
        
        return best_model
    
    def predict_batch(self, resource_data: List[Dict[str, Any]], model_type: Optional[ModelType] = None) -> List[Prediction]:
        """Predict violations for a batch of resources"""
        # Convert to DataFrame
        df = pd.DataFrame(resource_data)
        
        # Make predictions
        return self.predict_violations(df, model_type)
    
    def get_feature_importance(self, model_type: ModelType) -> Dict[str, float]:
        """Get feature importance for a trained model"""
        metrics = self.get_model_metrics(model_type)
        if metrics:
            return metrics.feature_importance
        return {}
    
    def evaluate_model_performance(self, features: pd.DataFrame, labels: pd.Series, model_type: ModelType) -> ModelMetrics:
        """Evaluate a model on test data"""
        predictor = self.predictors[model_type]
        
        # Load model if not already trained
        model_path = self.model_dir / f"{model_type.value}_model.joblib"
        if model_path.exists():
            predictor.load(str(model_path))
        else:
            raise ValueError(f"Model {model_type.value} not found. Train it first.")
        
        # Make predictions
        predictions = predictor.predict(features)
        
        # Calculate metrics
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, log_loss
        
        pred_classes = [1 if p.violation_probability > 0.5 else 0 for p in predictions]
        pred_proba = [p.violation_probability for p in predictions]
        
        metrics = ModelMetrics(
            accuracy=accuracy_score(labels, pred_classes),
            precision=precision_score(labels, pred_classes, average='weighted', zero_division=0),
            recall=recall_score(labels, pred_classes, average='weighted', zero_division=0),
            f1_score=f1_score(labels, pred_classes, average='weighted', zero_division=0),
            auc_roc=roc_auc_score(labels, pred_proba),
            log_loss=log_loss(labels, pred_proba),
            training_time_seconds=0,
            last_trained=datetime.now().isoformat(),
            feature_importance=self.get_feature_importance(model_type)
        )
        
        return metrics
    
    def auto_retrain_if_needed(self, model_type: ModelType, features: pd.DataFrame, labels: pd.Series, 
                              retrain_threshold_days: int = 30) -> bool:
        """Automatically retrain model if it's old or performance degraded"""
        metrics = self.get_model_metrics(model_type)
        
        if not metrics:
            logger.info(f"No existing metrics for {model_type.value}, training new model")
            self.train_model(model_type, features, labels)
            return True
        
        # Check if model is old
        last_trained = datetime.fromisoformat(metrics.last_trained)
        days_since_training = (datetime.now() - last_trained).days
        
        if days_since_training > retrain_threshold_days:
            logger.info(f"Model {model_type.value} is {days_since_training} days old, retraining")
            self.train_model(model_type, features, labels)
            return True
        
        # Check performance degradation (simplified)
        current_metrics = self.evaluate_model_performance(features, labels, model_type)
        
        if current_metrics.f1_score < metrics.f1_score * 0.9:  # 10% degradation
            logger.info(f"Model {model_type.value} performance degraded, retraining")
            self.train_model(model_type, features, labels)
            return True
        
        return False
