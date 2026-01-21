import xgboost as xgb
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple
import joblib
import logging
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, 
    f1_score, roc_auc_score, log_loss
)
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from imblearn.over_sampling import SMOTE

from ..engine import BasePredictor, Prediction, ModelMetrics

logger = logging.getLogger(__name__)

class XGBoostPredictor(BasePredictor):
    """XGBoost-based predictor for violation probability"""
    
    def __init__(self, model_type: str = "xgboost"):
        self.model = None
        self.preprocessor = None
        self.feature_names = None
        self.model_type = model_type
        self.scaler = StandardScaler()
        self.categorical_features = []
        self.numerical_features = []
        
    def train(self, features: pd.DataFrame, labels: pd.Series) -> ModelMetrics:
        """Train XGBoost model with feature engineering"""
        import time
        start_time = time.time()
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features, labels, test_size=0.2, random_state=42, stratify=labels
        )
        
        # Handle class imbalance with SMOTE
        smote = SMOTE(random_state=42)
        X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
        
        # Identify feature types
        self._identify_feature_types(X_train_resampled)
        
        # Preprocess features
        X_train_processed = self._preprocess_features(X_train_resampled, fit=True)
        X_test_processed = self._preprocess_features(X_test, fit=False)
        
        # Train model
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss',
            use_label_encoder=False
        )
        
        self.model.fit(
            X_train_processed, 
            y_train_resampled,
            eval_set=[(X_test_processed, y_test)],
            verbose=False
        )
        
        # Make predictions
        y_pred = self.model.predict(X_test_processed)
        y_pred_proba = self.model.predict_proba(X_test_processed)[:, 1]
        
        # Calculate metrics
        metrics = self._calculate_metrics(y_test, y_pred, y_pred_proba)
        metrics.training_time_seconds = time.time() - start_time
        metrics.last_trained = datetime.utcnow().isoformat()
        
        # Get feature importance
        metrics.feature_importance = self._get_feature_importance(X_train_processed)
        
        return metrics
    
    def predict(self, features: pd.DataFrame) -> List[Prediction]:
        """Make predictions for new data"""
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # Preprocess features
        features_processed = self._preprocess_features(features, fit=False)
        
        # Get probabilities
        probabilities = self.model.predict_proba(features_processed)[:, 1]
        
        # Get prediction confidence (using probability calibration)
        confidences = self._calculate_confidence(probabilities)
        
        # Create predictions
        predictions = []
        for idx, (_, row) in enumerate(features.iterrows()):
            # Get SHAP values for explanation
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
        
        # Check for attack paths
        attack_path_warnings = self._detect_attack_paths(iac_plan, predictions)
        warnings.extend(attack_path_warnings)
        
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
    
    def _identify_feature_types(self, df: pd.DataFrame):
        """Identify categorical and numerical features"""
        self.categorical_features = df.select_dtypes(include=['object', 'category']).columns.tolist()
        self.numerical_features = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
        
        # Remove target column if present
        if 'violation_label' in self.categorical_features:
            self.categorical_features.remove('violation_label')
        if 'violation_label' in self.numerical_features:
            self.numerical_features.remove('violation_label')
    
    def _preprocess_features(self, df: pd.DataFrame, fit: bool = False) -> np.ndarray:
        """Preprocess features for model training/prediction"""
        if fit:
            # Fit preprocessor
            categorical_transformer = OneHotEncoder(
                handle_unknown='ignore', 
                sparse_output=False
            )
            numerical_transformer = StandardScaler()
            
            # Create column transformer
            self.preprocessor = ColumnTransformer(
                transformers=[
                    ('num', numerical_transformer, self.numerical_features),
                    ('cat', categorical_transformer, self.categorical_features)
                ],
                remainder='drop'
            )
            
            # Fit and transform
            return self.preprocessor.fit_transform(df)
        else:
            # Transform using fitted preprocessor
            if self.preprocessor is None:
                raise ValueError("Preprocessor not fitted. Call with fit=True first.")
            return self.preprocessor.transform(df)
    
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
    
    def _get_feature_importance(self, X_processed: np.ndarray) -> Dict[str, float]:
        """Get feature importance from model"""
        if self.model is None:
            return {}
        
        # Get feature names from preprocessor
        feature_names = []
        for name, transformer, features in self.preprocessor.transformers_:
            if name == 'num':
                feature_names.extend(features)
            elif name == 'cat':
                # Get categories from one-hot encoder
                encoder = transformer
                for i, feature in enumerate(features):
                    categories = encoder.categories_[i]
                    for category in categories:
                        feature_names.append(f"{feature}_{category}")
        
        # Get importance scores
        importances = self.model.feature_importances_
        
        # Sort by importance
        importance_dict = dict(zip(feature_names, importances))
        sorted_importance = dict(
            sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[:20]
        )
        
        return sorted_importance
    
    def _calculate_confidence(self, probabilities: np.ndarray) -> np.ndarray:
        """Calculate confidence scores for predictions"""
        # Use probability calibration to estimate confidence
        # High confidence when probability is near 0 or 1
        # Low confidence when probability is near 0.5
        
        confidences = 1 - 2 * np.abs(probabilities - 0.5)
        return np.clip(confidences, 0, 1)
    
    def _explain_prediction(self, features: np.ndarray) -> Dict[str, Any]:
        """Generate explanation for prediction using SHAP"""
        try:
            import shap
            
            # Create SHAP explainer
            explainer = shap.TreeExplainer(self.model)
            
            # Calculate SHAP values
            shap_values = explainer.shap_values(features)
            
            # Get feature names
            feature_names = self._get_feature_names()
            
            # Get top contributing features
            if len(features.shape) == 1:
                features = features.reshape(1, -1)
            
            shap_array = shap_values[0] if isinstance(shap_values, list) else shap_values
            shap_for_instance = shap_array[0]
            
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
            logger.warning("SHAP not installed, falling back to feature importance")
            return {
                'top_features': self._get_feature_importance_for_instance(features),
                'shap_values_available': False
            }
    
    def _get_feature_names(self) -> List[str]:
        """Get feature names from preprocessor"""
        feature_names = []
        for name, transformer, features in self.preprocessor.transformers_:
            if name == 'num':
                feature_names.extend(features)
            elif name == 'cat':
                encoder = transformer
                for i, feature in enumerate(features):
                    categories = encoder.categories_[i]
                    for category in categories:
                        feature_names.append(f"{feature}_{category}")
        return feature_names
    
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
    
    def _detect_attack_paths(self, iac_plan: Dict, predictions: List[Prediction]) -> List[str]:
        """Detect potential attack paths in IaC plan"""
        warnings = []
        
        # Look for internet-facing resources with database connections
        public_resources = [
            p for p in predictions 
            if p.violation_probability > 0.6 and 'public_access' in p.predicted_violations
        ]
        
        database_resources = [
            p for p in predictions 
            if any(db in p.resource_type for db in ['rds', 'database', 'sql', 'dynamodb'])
        ]
        
        if public_resources and database_resources:
            warnings.append(
                f"Potential attack path: {len(public_resources)} public resources "
                f"with {len(database_resources)} database resources"
            )
        
        return warnings
    
    def save(self, path: str):
        """Save model and preprocessor to disk"""
        model_data = {
            'model': self.model,
            'preprocessor': self.preprocessor,
            'categorical_features': self.categorical_features,
            'numerical_features': self.numerical_features,
            'feature_names': self.feature_names,
            'model_type': self.model_type
        }
        joblib.dump(model_data, path)
    
    def load(self, path: str):
        """Load model and preprocessor from disk"""
        model_data = joblib.load(path)
        self.model = model_data['model']
        self.preprocessor = model_data['preprocessor']
        self.categorical_features = model_data['categorical_features']
        self.numerical_features = model_data['numerical_features']
        self.feature_names = model_data['feature_names']
        self.model_type = model_data['model_type']
