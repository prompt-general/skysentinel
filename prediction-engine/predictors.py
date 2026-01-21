import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
import joblib
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, log_loss
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import xgboost as xgb
import lightgbm as lgb
import shap
from scipy import stats

from .engine import BasePredictor, Prediction, ModelMetrics, ModelType

class XGBoostPredictor(BasePredictor):
    """XGBoost-based violation predictor"""
    
    def __init__(self, **kwargs):
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            **kwargs
        )
        self.preprocessor = None
        self.feature_names = None
        self.explainer = None
        
    def train(self, features: pd.DataFrame, labels: pd.Series) -> ModelMetrics:
        """Train XGBoost model"""
        start_time = datetime.now()
        
        # Identify categorical and numerical columns
        categorical_cols = features.select_dtypes(include=['object', 'category']).columns
        numerical_cols = features.select_dtypes(include=['number']).columns
        
        # Create preprocessor
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), numerical_cols),
                ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_cols)
            ]
        )
        
        # Create pipeline
        pipeline = Pipeline([
            ('preprocessor', preprocessor),
            ('classifier', self.model)
        ])
        
        # Train model
        pipeline.fit(features, labels)
        
        # Store components
        self.preprocessor = preprocessor
        self.feature_names = self._get_feature_names(pipeline)
        
        # Setup SHAP explainer
        self.explainer = shap.TreeExplainer(pipeline.named_steps['classifier'])
        
        # Calculate metrics
        predictions = pipeline.predict(features)
        pred_proba = pipeline.predict_proba(features)[:, 1]
        
        training_time = (datetime.now() - start_time).total_seconds()
        
        metrics = ModelMetrics(
            accuracy=accuracy_score(labels, predictions),
            precision=precision_score(labels, predictions, average='weighted', zero_division=0),
            recall=recall_score(labels, predictions, average='weighted', zero_division=0),
            f1_score=f1_score(labels, predictions, average='weighted', zero_division=0),
            auc_roc=roc_auc_score(labels, pred_proba),
            log_loss=log_loss(labels, pred_proba),
            training_time_seconds=training_time,
            last_trained=datetime.now().isoformat(),
            feature_importance=self._get_feature_importance(pipeline)
        )
        
        # Store the full pipeline
        self.model = pipeline
        return metrics
    
    def predict(self, features: pd.DataFrame) -> List[Prediction]:
        """Make predictions with XGBoost"""
        predictions = []
        
        # Make predictions
        pred_proba = self.model.predict_proba(features)[:, 1]
        pred_classes = self.model.predict(features)
        
        # Generate explanations
        if self.explainer:
            # Get SHAP values
            processed_features = self.preprocessor.transform(features)
            shap_values = self.explainer.shap_values(processed_features)
        else:
            shap_values = None
        
        for i, (idx, row) in enumerate(features.iterrows()):
            probability = float(pred_proba[i])
            confidence = self._calculate_confidence(probability)
            
            prediction = Prediction(
                resource_id=str(idx),
                resource_type=row.get('resource_type', 'unknown'),
                violation_probability=probability,
                confidence=confidence,
                predicted_violations=self._get_predicted_violations(probability, pred_classes[i]),
                features=row.to_dict(),
                explanation=self._create_explanation(shap_values[i] if shap_values is not None else None, i),
                timestamp=datetime.now().isoformat()
            )
            predictions.append(prediction)
        
        return predictions
    
    def save(self, path: str):
        """Save XGBoost model"""
        model_data = {
            'model': self.model,
            'preprocessor': self.preprocessor,
            'feature_names': self.feature_names,
            'explainer': self.explainer
        }
        joblib.dump(model_data, path)
    
    def load(self, path: str):
        """Load XGBoost model"""
        model_data = joblib.load(path)
        self.model = model_data['model']
        self.preprocessor = model_data['preprocessor']
        self.feature_names = model_data['feature_names']
        self.explainer = model_data['explainer']
    
    def _get_feature_names(self, pipeline):
        """Get feature names after preprocessing"""
        feature_names = []
        
        # Numerical features
        num_features = pipeline.named_steps['preprocessor'].named_transformers_['num'].get_feature_names_out()
        feature_names.extend(num_features)
        
        # Categorical features
        cat_features = pipeline.named_steps['preprocessor'].named_transformers_['cat'].get_feature_names_out()
        feature_names.extend(cat_features)
        
        return feature_names
    
    def _get_feature_importance(self, pipeline):
        """Get feature importance from trained model"""
        importance = pipeline.named_steps['classifier'].feature_importances_
        return dict(zip(self.feature_names, importance))
    
    def _calculate_confidence(self, probability):
        """Calculate prediction confidence"""
        # Simple confidence calculation based on distance from 0.5
        return abs(probability - 0.5) * 2
    
    def _get_predicted_violations(self, probability, pred_class):
        """Get predicted violation types"""
        if probability > 0.7:
            return ['security', 'compliance', 'cost']
        elif probability > 0.5:
            return ['security', 'compliance']
        elif probability > 0.3:
            return ['security']
        else:
            return []
    
    def _create_explanation(self, shap_values, index):
        """Create explanation from SHAP values"""
        if shap_values is None:
            return {}
        
        # Get top contributing features
        feature_importance = dict(zip(self.feature_names, shap_values))
        top_features = sorted(feature_importance.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
        
        return {
            'top_features': top_features,
            'base_value': float(self.explainer.expected_value),
            'method': 'shap'
        }

class LightGBMPredictor(BasePredictor):
    """LightGBM-based violation predictor"""
    
    def __init__(self, **kwargs):
        self.model = lgb.LGBMClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            **kwargs
        )
        self.preprocessor = None
        self.feature_names = None
        self.explainer = None
        
    def train(self, features: pd.DataFrame, labels: pd.Series) -> ModelMetrics:
        """Train LightGBM model"""
        start_time = datetime.now()
        
        # Identify categorical and numerical columns
        categorical_cols = features.select_dtypes(include=['object', 'category']).columns
        numerical_cols = features.select_dtypes(include=['number']).columns
        
        # Create preprocessor
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), numerical_cols),
                ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_cols)
            ]
        )
        
        # Create pipeline
        pipeline = Pipeline([
            ('preprocessor', preprocessor),
            ('classifier', self.model)
        ])
        
        # Train model
        pipeline.fit(features, labels)
        
        # Store components
        self.preprocessor = preprocessor
        self.feature_names = self._get_feature_names(pipeline)
        
        # Setup SHAP explainer
        self.explainer = shap.TreeExplainer(pipeline.named_steps['classifier'])
        
        # Calculate metrics
        predictions = pipeline.predict(features)
        pred_proba = pipeline.predict_proba(features)[:, 1]
        
        training_time = (datetime.now() - start_time).total_seconds()
        
        metrics = ModelMetrics(
            accuracy=accuracy_score(labels, predictions),
            precision=precision_score(labels, predictions, average='weighted', zero_division=0),
            recall=recall_score(labels, predictions, average='weighted', zero_division=0),
            f1_score=f1_score(labels, predictions, average='weighted', zero_division=0),
            auc_roc=roc_auc_score(labels, pred_proba),
            log_loss=log_loss(labels, pred_proba),
            training_time_seconds=training_time,
            last_trained=datetime.now().isoformat(),
            feature_importance=self._get_feature_importance(pipeline)
        )
        
        # Store the full pipeline
        self.model = pipeline
        return metrics
    
    def predict(self, features: pd.DataFrame) -> List[Prediction]:
        """Make predictions with LightGBM"""
        predictions = []
        
        # Make predictions
        pred_proba = self.model.predict_proba(features)[:, 1]
        pred_classes = self.model.predict(features)
        
        # Generate explanations
        if self.explainer:
            processed_features = self.preprocessor.transform(features)
            shap_values = self.explainer.shap_values(processed_features)
        else:
            shap_values = None
        
        for i, (idx, row) in enumerate(features.iterrows()):
            probability = float(pred_proba[i])
            confidence = self._calculate_confidence(probability)
            
            prediction = Prediction(
                resource_id=str(idx),
                resource_type=row.get('resource_type', 'unknown'),
                violation_probability=probability,
                confidence=confidence,
                predicted_violations=self._get_predicted_violations(probability, pred_classes[i]),
                features=row.to_dict(),
                explanation=self._create_explanation(shap_values[i] if shap_values is not None else None, i),
                timestamp=datetime.now().isoformat()
            )
            predictions.append(prediction)
        
        return predictions
    
    def save(self, path: str):
        """Save LightGBM model"""
        model_data = {
            'model': self.model,
            'preprocessor': self.preprocessor,
            'feature_names': self.feature_names,
            'explainer': self.explainer
        }
        joblib.dump(model_data, path)
    
    def load(self, path: str):
        """Load LightGBM model"""
        model_data = joblib.load(path)
        self.model = model_data['model']
        self.preprocessor = model_data['preprocessor']
        self.feature_names = model_data['feature_names']
        self.explainer = model_data['explainer']
    
    def _get_feature_names(self, pipeline):
        """Get feature names after preprocessing"""
        feature_names = []
        
        # Numerical features
        num_features = pipeline.named_steps['preprocessor'].named_transformers_['num'].get_feature_names_out()
        feature_names.extend(num_features)
        
        # Categorical features
        cat_features = pipeline.named_steps['preprocessor'].named_transformers_['cat'].get_feature_names_out()
        feature_names.extend(cat_features)
        
        return feature_names
    
    def _get_feature_importance(self, pipeline):
        """Get feature importance from trained model"""
        importance = pipeline.named_steps['classifier'].feature_importances_
        return dict(zip(self.feature_names, importance))
    
    def _calculate_confidence(self, probability):
        """Calculate prediction confidence"""
        return abs(probability - 0.5) * 2
    
    def _get_predicted_violations(self, probability, pred_class):
        """Get predicted violation types"""
        if probability > 0.7:
            return ['security', 'compliance', 'cost']
        elif probability > 0.5:
            return ['security', 'compliance']
        elif probability > 0.3:
            return ['security']
        else:
            return []
    
    def _create_explanation(self, shap_values, index):
        """Create explanation from SHAP values"""
        if shap_values is None:
            return {}
        
        feature_importance = dict(zip(self.feature_names, shap_values))
        top_features = sorted(feature_importance.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
        
        return {
            'top_features': top_features,
            'base_value': float(self.explainer.expected_value),
            'method': 'shap'
        }

class IsolationForestPredictor(BasePredictor):
    """Isolation Forest anomaly detector"""
    
    def __init__(self, contamination=0.1, **kwargs):
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            **kwargs
        )
        self.preprocessor = None
        self.feature_names = None
        
    def train(self, features: pd.DataFrame, labels: pd.Series) -> ModelMetrics:
        """Train Isolation Forest"""
        start_time = datetime.now()
        
        # Identify categorical and numerical columns
        categorical_cols = features.select_dtypes(include=['object', 'category']).columns
        numerical_cols = features.select_dtypes(include=['number']).columns
        
        # Create preprocessor
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), numerical_cols),
                ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_cols)
            ]
        )
        
        # Create pipeline
        pipeline = Pipeline([
            ('preprocessor', preprocessor),
            ('detector', self.model)
        ])
        
        # Train model
        pipeline.fit(features)
        
        # Store components
        self.preprocessor = preprocessor
        self.feature_names = self._get_feature_names(pipeline)
        
        # Calculate metrics (convert anomaly scores to binary)
        anomaly_scores = pipeline.decision_function(features)
        predictions = pipeline.predict(features)
        
        # Convert to binary (1 for normal, -1 for anomaly)
        binary_predictions = [1 if p == 1 else 0 for p in predictions]
        
        training_time = (datetime.now() - start_time).total_seconds()
        
        # For isolation forest, we use different metrics
        metrics = ModelMetrics(
            accuracy=accuracy_score(labels, binary_predictions),
            precision=precision_score(labels, binary_predictions, average='weighted', zero_division=0),
            recall=recall_score(labels, binary_predictions, average='weighted', zero_division=0),
            f1_score=f1_score(labels, binary_predictions, average='weighted', zero_division=0),
            auc_roc=roc_auc_score(labels, anomaly_scores),
            log_loss=log_loss(labels, anomaly_scores),
            training_time_seconds=training_time,
            last_trained=datetime.now().isoformat(),
            feature_importance={}
        )
        
        # Store the full pipeline
        self.model = pipeline
        return metrics
    
    def predict(self, features: pd.DataFrame) -> List[Prediction]:
        """Make predictions with Isolation Forest"""
        predictions = []
        
        # Make predictions
        anomaly_scores = self.model.decision_function(features)
        pred_classes = self.model.predict(features)
        
        for i, (idx, row) in enumerate(features.iterrows()):
            # Convert anomaly score to probability
            probability = self._anomaly_score_to_probability(anomaly_scores[i])
            confidence = self._calculate_confidence(probability)
            
            prediction = Prediction(
                resource_id=str(idx),
                resource_type=row.get('resource_type', 'unknown'),
                violation_probability=probability,
                confidence=confidence,
                predicted_violations=self._get_predicted_violations(probability, pred_classes[i]),
                features=row.to_dict(),
                explanation={'anomaly_score': float(anomaly_scores[i]), 'method': 'isolation_forest'},
                timestamp=datetime.now().isoformat()
            )
            predictions.append(prediction)
        
        return predictions
    
    def save(self, path: str):
        """Save Isolation Forest model"""
        model_data = {
            'model': self.model,
            'preprocessor': self.preprocessor,
            'feature_names': self.feature_names
        }
        joblib.dump(model_data, path)
    
    def load(self, path: str):
        """Load Isolation Forest model"""
        model_data = joblib.load(path)
        self.model = model_data['model']
        self.preprocessor = model_data['preprocessor']
        self.feature_names = model_data['feature_names']
    
    def _get_feature_names(self, pipeline):
        """Get feature names after preprocessing"""
        feature_names = []
        
        # Numerical features
        num_features = pipeline.named_steps['preprocessor'].named_transformers_['num'].get_feature_names_out()
        feature_names.extend(num_features)
        
        # Categorical features
        cat_features = pipeline.named_steps['preprocessor'].named_transformers_['cat'].get_feature_names_out()
        feature_names.extend(cat_features)
        
        return feature_names
    
    def _anomaly_score_to_probability(self, anomaly_score):
        """Convert anomaly score to probability"""
        # Normalize score to 0-1 range
        return 1 / (1 + np.exp(-anomaly_score))
    
    def _calculate_confidence(self, probability):
        """Calculate prediction confidence"""
        return abs(probability - 0.5) * 2
    
    def _get_predicted_violations(self, probability, pred_class):
        """Get predicted violation types"""
        if pred_class == -1:  # Anomaly detected
            return ['anomaly', 'security']
        else:
            return []

class RandomForestPredictor(BasePredictor):
    """Random Forest classifier"""
    
    def __init__(self, **kwargs):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            **kwargs
        )
        self.preprocessor = None
        self.feature_names = None
        
    def train(self, features: pd.DataFrame, labels: pd.Series) -> ModelMetrics:
        """Train Random Forest"""
        start_time = datetime.now()
        
        # Identify categorical and numerical columns
        categorical_cols = features.select_dtypes(include=['object', 'category']).columns
        numerical_cols = features.select_dtypes(include=['number']).columns
        
        # Create preprocessor
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), numerical_cols),
                ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_cols)
            ]
        )
        
        # Create pipeline
        pipeline = Pipeline([
            ('preprocessor', preprocessor),
            ('classifier', self.model)
        ])
        
        # Train model
        pipeline.fit(features, labels)
        
        # Store components
        self.preprocessor = preprocessor
        self.feature_names = self._get_feature_names(pipeline)
        
        # Calculate metrics
        predictions = pipeline.predict(features)
        pred_proba = pipeline.predict_proba(features)[:, 1]
        
        training_time = (datetime.now() - start_time).total_seconds()
        
        metrics = ModelMetrics(
            accuracy=accuracy_score(labels, predictions),
            precision=precision_score(labels, predictions, average='weighted', zero_division=0),
            recall=recall_score(labels, predictions, average='weighted', zero_division=0),
            f1_score=f1_score(labels, predictions, average='weighted', zero_division=0),
            auc_roc=roc_auc_score(labels, pred_proba),
            log_loss=log_loss(labels, pred_proba),
            training_time_seconds=training_time,
            last_trained=datetime.now().isoformat(),
            feature_importance=self._get_feature_importance(pipeline)
        )
        
        # Store the full pipeline
        self.model = pipeline
        return metrics
    
    def predict(self, features: pd.DataFrame) -> List[Prediction]:
        """Make predictions with Random Forest"""
        predictions = []
        
        # Make predictions
        pred_proba = self.model.predict_proba(features)[:, 1]
        pred_classes = self.model.predict(features)
        
        for i, (idx, row) in enumerate(features.iterrows()):
            probability = float(pred_proba[i])
            confidence = self._calculate_confidence(probability)
            
            prediction = Prediction(
                resource_id=str(idx),
                resource_type=row.get('resource_type', 'unknown'),
                violation_probability=probability,
                confidence=confidence,
                predicted_violations=self._get_predicted_violations(probability, pred_classes[i]),
                features=row.to_dict(),
                explanation={'method': 'random_forest'},
                timestamp=datetime.now().isoformat()
            )
            predictions.append(prediction)
        
        return predictions
    
    def save(self, path: str):
        """Save Random Forest model"""
        model_data = {
            'model': self.model,
            'preprocessor': self.preprocessor,
            'feature_names': self.feature_names
        }
        joblib.dump(model_data, path)
    
    def load(self, path: str):
        """Load Random Forest model"""
        model_data = joblib.load(path)
        self.model = model_data['model']
        self.preprocessor = model_data['preprocessor']
        self.feature_names = model_data['feature_names']
    
    def _get_feature_names(self, pipeline):
        """Get feature names after preprocessing"""
        feature_names = []
        
        # Numerical features
        num_features = pipeline.named_steps['preprocessor'].named_transformers_['num'].get_feature_names_out()
        feature_names.extend(num_features)
        
        # Categorical features
        cat_features = pipeline.named_steps['preprocessor'].named_transformers_['cat'].get_feature_names_out()
        feature_names.extend(cat_features)
        
        return feature_names
    
    def _get_feature_importance(self, pipeline):
        """Get feature importance from trained model"""
        importance = pipeline.named_steps['classifier'].feature_importances_
        return dict(zip(self.feature_names, importance))
    
    def _calculate_confidence(self, probability):
        """Calculate prediction confidence"""
        return abs(probability - 0.5) * 2
    
    def _get_predicted_violations(self, probability, pred_class):
        """Get predicted violation types"""
        if probability > 0.7:
            return ['security', 'compliance', 'cost']
        elif probability > 0.5:
            return ['security', 'compliance']
        elif probability > 0.3:
            return ['security']
        else:
            return []
