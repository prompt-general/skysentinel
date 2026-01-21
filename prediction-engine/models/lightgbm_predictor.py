import lightgbm as lgb
import numpy as np
import pandas as pd
from typing import Dict, List, Any
import joblib
import logging
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, 
    f1_score, roc_auc_score, log_loss
)
from sklearn.preprocessing import LabelEncoder
from imblearn.over_sampling import SMOTE

from ..engine import BasePredictor, Prediction, ModelMetrics

logger = logging.getLogger(__name__)

class LightGBMPredictor(BasePredictor):
    """LightGBM-based predictor with gradient boosting"""
    
    def __init__(self):
        super().__init__()
        self.model = None
        self.categorical_features = []
        self.numerical_features = []
        self.label_encoders = {}
        self.feature_names = None
        self.params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'random_state': 42,
            'min_child_samples': 20,
            'reg_alpha': 0.1,
            'reg_lambda': 0.1
        }
    
    def train(self, features: pd.DataFrame, labels: pd.Series) -> ModelMetrics:
        """Train LightGBM model"""
        import time
        start_time = time.time()
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features, labels, test_size=0.2, random_state=42, stratify=labels
        )
        
        # Handle class imbalance with SMOTE
        smote = SMOTE(random_state=42)
        X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
        
        # Preprocess features
        X_train_processed = self._preprocess_features(X_train_resampled, fit=True)
        X_test_processed = self._preprocess_features(X_test, fit=False)
        
        # Create LightGBM datasets
        train_data = lgb.Dataset(
            X_train_processed, 
            label=y_train_resampled,
            categorical_feature=self.categorical_features
        )
        test_data = lgb.Dataset(
            X_test_processed, 
            label=y_test,
            reference=train_data
        )
        
        # Train model with early stopping
        self.model = lgb.train(
            self.params,
            train_data,
            valid_sets=[test_data],
            num_boost_round=1000,
            callbacks=[lgb.early_stopping(10), lgb.log_evaluation(0)]
        )
        
        # Make predictions
        y_pred_proba = self.model.predict(X_test_processed, num_iteration=self.model.best_iteration)
        y_pred = (y_pred_proba > 0.5).astype(int)
        
        # Calculate metrics
        metrics = self._calculate_metrics(y_test, y_pred, y_pred_proba)
        metrics.training_time_seconds = time.time() - start_time
        metrics.last_trained = datetime.utcnow().isoformat()
        metrics.feature_importance = self._get_feature_importance()
        
        return metrics
    
    def predict(self, features: pd.DataFrame) -> List[Prediction]:
        """Make predictions for new data"""
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # Preprocess features
        features_processed = self._preprocess_features(features, fit=False)
        
        # Get probabilities
        probabilities = self.model.predict(features_processed, num_iteration=self.model.best_iteration)
        
        # Get prediction confidence
        confidences = self._calculate_confidence(probabilities)
        
        # Create predictions
        predictions = []
        for idx, (_, row) in enumerate(features.iterrows()):
            # Get explanation
            explanation = self._explain_prediction(features_processed[idx:idx+1])
            
            # Determine predicted violation types
            predicted_violations = self._predict_violation_types(
                row, probabilities[idx]
            )
            
            prediction = Prediction(
                resource_id=row.get('resource_id', f'resource_{idx}'),
                resource_type=row.get('resource_type', 'unknown'),
                violation_probability=float(probabilities[idx]),
                confidence=float(confidences[idx]),
                predicted_violations=predicted_violations,
                features=row.to_dict(),
                explanation=explanation,
                timestamp=datetime.utcnow().isoformat()
            )
            predictions.append(prediction)
        
        return predictions
    
    def predict_batch(self, iac_plan: Dict, driver=None) -> Dict[str, Any]:
        """Predict violations for entire IaC plan"""
        # Extract features
        if driver:
            from ..features import FeatureEngineer
            feature_engineer = FeatureEngineer(driver)
            features_df = feature_engineer.extract_iac_features(iac_plan)
        else:
            # Simple feature extraction fallback
            features_df = pd.DataFrame([{
                'resource_id': r.get('iac_id', f'resource_{i}'),
                'resource_type': r.get('resource_type', 'unknown'),
                'cloud_provider': r.get('cloud_provider', 'unknown'),
                'change_type': r.get('change_type', 'create'),
                'property_count': len(r.get('properties', {})),
                'tag_count': len(r.get('tags', {}))
            } for i, r in enumerate(iac_plan.get('resources', []))])
        
        if features_df.empty:
            return {
                'violation_probability': 0.0,
                'confidence': 0.0,
                'high_risk_resources': [],
                'warnings': []
            }
        
        # Make predictions
        predictions = self.predict(features_df)
        
        # Aggregate results
        violation_probs = [p.violation_probability for p in predictions]
        avg_violation_prob = np.mean(violation_probs) if violation_probs else 0.0
        
        # Identify high-risk resources
        high_risk_resources = [
            {
                'resource_id': p.resource_id,
                'resource_type': p.resource_type,
                'violation_probability': p.violation_probability,
                'confidence': p.confidence,
                'top_features': list(p.explanation.get('top_features', {}).keys())[:3]
            }
            for p in predictions if p.violation_probability > 0.7
        ]
        
        # Generate warnings
        warnings = []
        if avg_violation_prob > 0.8:
            warnings.append(f"High overall violation probability: {avg_violation_prob:.2%}")
        
        if len(high_risk_resources) > 3:
            warnings.append(f"Multiple high-risk resources: {len(high_risk_resources)}")
        
        return {
            'violation_probability': float(avg_violation_prob),
            'confidence': float(np.mean([p.confidence for p in predictions])),
            'high_risk_resources': high_risk_resources,
            'warnings': warnings,
            'resource_predictions': [
                {
                    'resource_id': p.resource_id,
                    'probability': p.violation_probability,
                    'confidence': p.confidence
                }
                for p in predictions
            ]
        }
    
    def _preprocess_features(self, df: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
        """Preprocess features for LightGBM"""
        df_processed = df.copy()
        
        if fit:
            # Identify feature types
            self._identify_feature_types(df)
            
            # Encode categorical features
            for col in self.categorical_features:
                if col in df_processed.columns:
                    encoder = LabelEncoder()
                    # Handle unseen categories by fitting on all unique values
                    df_processed[col] = df_processed[col].astype(str)
                    encoder.fit(df_processed[col])
                    df_processed[col] = encoder.transform(df_processed[col])
                    self.label_encoders[col] = encoder
            
            # Store feature names
            self.feature_names = df_processed.columns.tolist()
        else:
            # Transform categorical features using fitted encoders
            for col in self.categorical_features:
                if col in df_processed.columns and col in self.label_encoders:
                    encoder = self.label_encoders[col]
                    # Handle unseen categories
                    df_processed[col] = df_processed[col].astype(str)
                    unseen_mask = ~df_processed[col].isin(encoder.classes_)
                    if unseen_mask.any():
                        # Assign unseen categories to a special value
                        df_processed.loc[unseen_mask, col] = encoder.classes_[0]
                    df_processed[col] = encoder.transform(df_processed[col])
        
        return df_processed
    
    def _identify_feature_types(self, df: pd.DataFrame):
        """Identify categorical and numerical features"""
        self.categorical_features = []
        self.numerical_features = []
        
        for col in df.columns:
            if df[col].dtype == 'object' or df[col].dtype == 'category':
                # Only include categorical features with reasonable cardinality
                if df[col].nunique() <= 100:  # Limit to 100 unique values
                    self.categorical_features.append(col)
                else:
                    # Treat high-cardinality categorical as numerical after encoding
                    self.numerical_features.append(col)
            elif pd.api.types.is_numeric_dtype(df[col]):
                self.numerical_features.append(col)
        
        logger.info(f"LightGBM: {len(self.categorical_features)} categorical, "
                   f"{len(self.numerical_features)} numerical features")
    
    def _calculate_metrics(self, y_true, y_pred, y_pred_proba) -> ModelMetrics:
        """Calculate model performance metrics"""
        return ModelMetrics(
            accuracy=float(accuracy_score(y_true, y_pred)),
            precision=float(precision_score(y_true, y_pred, zero_division=0)),
            recall=float(recall_score(y_true, y_pred, zero_division=0)),
            f1_score=float(f1_score(y_true, y_pred, zero_division=0)),
            auc_roc=float(roc_auc_score(y_true, y_pred_proba)),
            log_loss=float(log_loss(y_true, y_pred_proba)),
            training_time_seconds=0.0,
            last_trained='',
            feature_importance={}
        )
    
    def _get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from LightGBM model"""
        if self.model is None:
            return {}
        
        # Get feature importance using gain
        importance = self.model.feature_importance(importance_type='gain')
        feature_names = self.model.feature_name()
        
        importance_dict = dict(zip(feature_names, importance))
        sorted_importance = dict(
            sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[:20]
        )
        
        return sorted_importance
    
    def _calculate_confidence(self, probabilities: np.ndarray) -> np.ndarray:
        """Calculate confidence scores for predictions"""
        # Use probability calibration to estimate confidence
        confidences = 1 - 2 * np.abs(probabilities - 0.5)
        return np.clip(confidences, 0, 1)
    
    def _explain_prediction(self, features: np.ndarray) -> Dict[str, Any]:
        """Generate explanation for prediction"""
        try:
            import shap
            
            # Create SHAP explainer
            explainer = shap.TreeExplainer(self.model)
            
            # Calculate SHAP values
            shap_values = explainer.shap_values(features)
            
            # Get top contributing features
            shap_array = shap_values[0] if isinstance(shap_values, list) else shap_values
            shap_for_instance = shap_array[0]
            
            feature_names = self.model.feature_name()
            
            # Sort features by absolute SHAP value
            feature_contributions = {}
            for i, value in enumerate(shap_for_instance):
                feature_name = feature_names[i] if i < len(feature_names) else f"feature_{i}"
                feature_contributions[feature_name] = float(value)
            
            sorted_contributions = dict(
                sorted(feature_contributions.items(), 
                       key=lambda x: abs(x[1]), 
                       reverse=True)[:5]
            )
            
            return {
                'top_features': sorted_contributions,
                'base_value': float(explainer.expected_value[0] if isinstance(explainer.expected_value, list) 
                                   else explainer.expected_value),
                'shap_values_available': True
            }
            
        except ImportError:
            logger.warning("SHAP not installed, using feature importance")
            return {
                'top_features': self._get_feature_importance(),
                'shap_values_available': False
            }
    
    def _predict_violation_types(self, features: pd.Series, probability: float) -> List[str]:
        """Predict specific violation types based on features"""
        violations = []
        
        if probability > 0.5:
            # Check for specific violation patterns
            if features.get('is_public_resource', False):
                violations.append('public_access')
            
            if features.get('has_sensitive_tags', False):
                violations.append('sensitive_data_exposure')
            
            if features.get('historical_violation_count', 0) > 2:
                violations.append('repeated_violations')
            
            if features.get('base_risk_score', 0) > 7:
                violations.append('high_risk_configuration')
        
        return violations if violations else ['generic_violation']
    
    def save(self, path: str):
        """Save model and encoders to disk"""
        model_data = {
            'model': self.model,
            'categorical_features': self.categorical_features,
            'numerical_features': self.numerical_features,
            'label_encoders': self.label_encoders,
            'feature_names': self.feature_names,
            'params': self.params
        }
        joblib.dump(model_data, path)
        logger.info(f"LightGBM model saved to {path}")
    
    def load(self, path: str):
        """Load model and encoders from disk"""
        model_data = joblib.load(path)
        self.model = model_data['model']
        self.categorical_features = model_data['categorical_features']
        self.numerical_features = model_data['numerical_features']
        self.label_encoders = model_data['label_encoders']
        self.feature_names = model_data['feature_names']
        self.params = model_data['params']
        logger.info(f"LightGBM model loaded from {path}")
    
    def get_feature_importance_plot(self) -> Any:
        """Get feature importance plot for visualization"""
        if self.model is None:
            return None
        
        import matplotlib.pyplot as plt
        
        # Create feature importance plot
        importance = self.model.feature_importance(importance_type='gain')
        feature_names = self.model.feature_name()
        
        # Sort by importance
        indices = np.argsort(importance)[::-1][:20]  # Top 20 features
        
        plt.figure(figsize=(10, 8))
        plt.title('LightGBM Feature Importance (Gain)')
        plt.bar(range(len(indices)), importance[indices])
        plt.xticks(range(len(indices)), [feature_names[i] for i in indices], rotation=45, ha='right')
        plt.tight_layout()
        
        return plt
    
    def optimize_hyperparameters(self, features: pd.DataFrame, labels: pd.Series) -> Dict[str, Any]:
        """Optimize hyperparameters using cross-validation"""
        from sklearn.model_selection import StratifiedKFold
        import optuna
        
        def objective(trial):
            # Define hyperparameter search space
            params = {
                'objective': 'binary',
                'metric': 'binary_logloss',
                'boosting_type': 'gbdt',
                'num_leaves': trial.suggest_int('num_leaves', 10, 300),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
                'feature_fraction': trial.suggest_float('feature_fraction', 0.6, 1.0),
                'bagging_fraction': trial.suggest_float('bagging_fraction', 0.6, 1.0),
                'bagging_freq': trial.suggest_int('bagging_freq', 1, 10),
                'min_child_samples': trial.suggest_int('min_child_samples', 5, 100),
                'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 1.0),
                'reg_lambda': trial.suggest_float('reg_lambda', 0.0, 1.0),
                'verbose': -1,
                'random_state': 42
            }
            
            # Cross-validation
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
            scores = []
            
            for train_idx, val_idx in cv.split(features, labels):
                X_train, X_val = features.iloc[train_idx], features.iloc[val_idx]
                y_train, y_val = labels.iloc[train_idx], labels.iloc[val_idx]
                
                # Preprocess
                X_train_proc = self._preprocess_features(X_train, fit=True)
                X_val_proc = self._preprocess_features(X_val, fit=False)
                
                # Train
                train_data = lgb.Dataset(X_train_proc, label=y_train)
                val_data = lgb.Dataset(X_val_proc, label=y_val, reference=train_data)
                
                model = lgb.train(
                    params,
                    train_data,
                    valid_sets=[val_data],
                    num_boost_round=1000,
                    callbacks=[lgb.early_stopping(10), lgb.log_evaluation(0)]
                )
                
                # Evaluate
                y_pred_proba = model.predict(X_val_proc, num_iteration=model.best_iteration)
                score = roc_auc_score(y_val, y_pred_proba)
                scores.append(score)
            
            return np.mean(scores)
        
        # Optimize
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=50)
        
        # Update params with best ones
        self.params.update(study.best_params)
        
        return {
            'best_params': study.best_params,
            'best_score': study.best_value,
            'n_trials': len(study.trials)
        }
