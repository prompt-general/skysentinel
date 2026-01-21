from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from pathlib import Path
import json

from .data_collector import TrainingDataCollector
from ..preprocessing import FeaturePreprocessor, FeatureSelector
from ..models.xgboost_predictor import XGBoostPredictor
from ..models.lightgbm_predictor import LightGBMPredictor
from ..service import PredictionEngine, ModelType

logger = logging.getLogger(__name__)

class TrainingPipeline:
    """Complete training pipeline for ML models"""
    
    def __init__(self, neo4j_driver, model_dir: str = "models"):
        self.driver = neo4j_driver
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        
        self.data_collector = TrainingDataCollector(neo4j_driver)
        self.preprocessor = FeaturePreprocessor()
        self.feature_selector = FeatureSelector()
        
        self.training_history = []
        
    def run_full_training(self, 
                         model_types: List[ModelType] = None,
                         lookback_days: int = 90,
                         min_samples: int = 1000,
                         test_size: float = 0.2) -> Dict[str, Any]:
        """Run complete training pipeline"""
        
        if model_types is None:
            model_types = [ModelType.XGBOOST, ModelType.LIGHTGBM]
        
        logger.info(f"Starting full training pipeline for {model_types}")
        
        # Step 1: Collect training data
        features_df, labels_series = self.data_collector.collect_training_data(
            lookback_days=lookback_days,
            min_samples=min_samples
        )
        
        if features_df.empty:
            raise ValueError("No training data available")
        
        # Validate data quality
        quality_report = self.data_collector.validate_data_quality(features_df, labels_series)
        logger.info(f"Data quality score: {quality_report['data_quality_score']}")
        
        # Step 2: Preprocess features
        features_processed = self.preprocessor.fit_transform(features_df)
        
        # Step 3: Feature selection
        features_selected = self.feature_selector.fit_transform(features_processed, labels_series)
        
        # Step 4: Split data
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(
            features_selected, labels_series, 
            test_size=test_size, random_state=42, stratify=labels_series
        )
        
        # Step 5: Train models
        training_results = {}
        
        for model_type in model_types:
            logger.info(f"Training {model_type.value} model")
            
            try:
                # Get predictor
                predictor = self._get_predictor(model_type)
                
                # Train model
                metrics = predictor.train(X_train, y_train)
                
                # Evaluate on test set
                test_predictions = predictor.predict(X_test)
                test_metrics = self._evaluate_predictions(y_test, test_predictions)
                
                # Save model
                model_path = self.model_dir / f"{model_type.value}_model.joblib"
                predictor.save(str(model_path))
                
                # Store results
                training_results[model_type.value] = {
                    'training_metrics': metrics.__dict__,
                    'test_metrics': test_metrics,
                    'model_path': str(model_path),
                    'training_samples': len(X_train),
                    'test_samples': len(X_test),
                    'features_used': self.feature_selector.get_selected_features(),
                    'data_quality': quality_report
                }
                
                logger.info(f"Successfully trained {model_type.value} model")
                
            except Exception as e:
                logger.error(f"Error training {model_type.value} model: {e}")
                training_results[model_type.value] = {'error': str(e)}
        
        # Step 6: Select best model
        best_model = self._select_best_model(training_results)
        
        # Step 7: Save training metadata
        training_metadata = {
            'timestamp': datetime.now().isoformat(),
            'lookback_days': lookback_days,
            'min_samples': min_samples,
            'data_quality': quality_report,
            'model_results': training_results,
            'best_model': best_model,
            'feature_importance': self._get_feature_importance(training_results),
            'training_history': self.training_history[-10:]  # Last 10 trainings
        }
        
        metadata_path = self.model_dir / "training_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(training_metadata, f, indent=2, default=str)
        
        # Update training history
        self.training_history.append(training_metadata)
        
        return training_metadata
    
    def run_incremental_training(self, 
                               model_type: ModelType,
                               last_training_date: datetime,
                               new_samples: int = 100) -> Dict[str, Any]:
        """Run incremental training for existing model"""
        
        logger.info(f"Starting incremental training for {model_type.value}")
        
        # Collect new data
        features_df, labels_series = self.data_collector.collect_incremental_data(
            last_training_date=last_training_date,
            new_samples=new_samples
        )
        
        if features_df.empty:
            logger.info("No new data for incremental training")
            return {'status': 'no_new_data'}
        
        # Load existing model
        model_path = self.model_dir / f"{model_type.value}_model.joblib"
        if not model_path.exists():
            raise ValueError(f"No existing model found for {model_type.value}")
        
        predictor = self._get_predictor(model_type)
        predictor.load(str(model_path))
        
        # Preprocess new data using existing preprocessor
        preprocessor_path = self.model_dir / f"{model_type.value}_preprocessor.joblib"
        if preprocessor_path.exists():
            self.preprocessor.load(str(preprocessor_path))
        
        features_processed = self.preprocessor.transform(features_df)
        
        # Feature selection
        selector_path = self.model_dir / f"{model_type.value}_feature_selector.joblib"
        if selector_path.exists():
            self.feature_selector.load(str(selector_path))
        
        features_selected = self.feature_selector.transform(features_processed)
        
        # Retrain model with new data
        old_metrics = predictor.get_model_metrics()
        new_metrics = predictor.train(features_selected, labels_series)
        
        # Save updated model
        predictor.save(str(model_path))
        
        # Compare performance
        performance_change = {
            'accuracy_change': new_metrics.accuracy - old_metrics.accuracy,
            'f1_change': new_metrics.f1_score - old_metrics.f1_score,
            'auc_change': new_metrics.auc_roc - old_metrics.auc_roc
        }
        
        incremental_result = {
            'status': 'completed',
            'new_samples': len(features_df),
            'old_metrics': old_metrics.__dict__,
            'new_metrics': new_metrics.__dict__,
            'performance_change': performance_change,
            'training_date': datetime.now().isoformat()
        }
        
        logger.info(f"Incremental training completed: {len(features_df)} new samples")
        return incremental_result
    
    def run_cross_validation(self, 
                           model_type: ModelType,
                           lookback_days: int = 90,
                           cv_folds: int = 5) -> Dict[str, Any]:
        """Run cross-validation training"""
        
        logger.info(f"Starting {cv_folds}-fold cross-validation for {model_type.value}")
        
        # Collect CV data
        cv_data = self.data_collector.collect_cross_validation_data(
            lookback_days=lookback_days,
            cv_folds=cv_folds
        )
        
        if len(cv_data) < cv_folds:
            raise ValueError(f"Insufficient data for {cv_folds}-fold CV")
        
        cv_results = []
        
        for fold, (X_fold, y_fold) in enumerate(cv_data):
            logger.info(f"Training fold {fold + 1}/{cv_folds}")
            
            try:
                # Preprocess
                X_fold_processed = self.preprocessor.fit_transform(X_fold)
                X_fold_selected = self.feature_selector.fit_transform(X_fold_processed, y_fold)
                
                # Train model
                predictor = self._get_predictor(model_type)
                metrics = predictor.train(X_fold_selected, y_fold)
                
                cv_results.append({
                    'fold': fold + 1,
                    'samples': len(X_fold),
                    'metrics': metrics.__dict__
                })
                
            except Exception as e:
                logger.error(f"Error in fold {fold + 1}: {e}")
                cv_results.append({
                    'fold': fold + 1,
                    'error': str(e)
                })
        
        # Aggregate CV results
        successful_folds = [r for r in cv_results if 'error' not in r]
        
        if successful_folds:
            avg_metrics = {
                'accuracy': np.mean([r['metrics']['accuracy'] for r in successful_folds]),
                'precision': np.mean([r['metrics']['precision'] for r in successful_folds]),
                'recall': np.mean([r['metrics']['recall'] for r in successful_folds]),
                'f1_score': np.mean([r['metrics']['f1_score'] for r in successful_folds]),
                'auc_roc': np.mean([r['metrics']['auc_roc'] for r in successful_folds]),
                'std_accuracy': np.std([r['metrics']['accuracy'] for r in successful_folds]),
                'std_f1_score': np.std([r['metrics']['f1_score'] for r in successful_folds])
            }
        else:
            avg_metrics = {}
        
        cv_summary = {
            'model_type': model_type.value,
            'cv_folds': cv_folds,
            'successful_folds': len(successful_folds),
            'avg_metrics': avg_metrics,
            'fold_results': cv_results,
            'cv_date': datetime.now().isoformat()
        }
        
        # Save CV results
        cv_path = self.model_dir / f"{model_type.value}_cv_results.json"
        with open(cv_path, 'w') as f:
            json.dump(cv_summary, f, indent=2, default=str)
        
        return cv_summary
    
    def _get_predictor(self, model_type: ModelType):
        """Get predictor instance for model type"""
        if model_type == ModelType.XGBOOST:
            return XGBoostPredictor()
        elif model_type == ModelType.LIGHTGBM:
            return LightGBMPredictor()
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
    
    def _evaluate_predictions(self, y_true, predictions) -> Dict[str, float]:
        """Evaluate predictions on test set"""
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        
        # Convert predictions to binary
        y_pred = [1 if p.violation_probability > 0.5 else 0 for p in predictions]
        y_pred_proba = [p.violation_probability for p in predictions]
        
        return {
            'accuracy': float(accuracy_score(y_true, y_pred)),
            'precision': float(precision_score(y_true, y_pred, zero_division=0)),
            'recall': float(recall_score(y_true, y_pred, zero_division=0)),
            'f1_score': float(f1_score(y_true, y_pred, zero_division=0)),
            'auc_roc': float(roc_auc_score(y_true, y_pred_proba))
        }
    
    def _select_best_model(self, training_results: Dict[str, Any]) -> Optional[str]:
        """Select best model based on test metrics"""
        best_model = None
        best_score = -1
        
        for model_name, result in training_results.items():
            if 'error' in result:
                continue
            
            test_metrics = result.get('test_metrics', {})
            f1_score = test_metrics.get('f1_score', 0)
            
            if f1_score > best_score:
                best_score = f1_score
                best_model = model_name
        
        return best_model
    
    def _get_feature_importance(self, training_results: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate feature importance from all models"""
        all_importance = {}
        
        for model_name, result in training_results.items():
            if 'error' in result:
                continue
            
            training_metrics = result.get('training_metrics', {})
            feature_importance = training_metrics.get('feature_importance', {})
            
            for feature, importance in feature_importance.items():
                if feature not in all_importance:
                    all_importance[feature] = []
                all_importance[feature].append(importance)
        
        # Calculate average importance
        avg_importance = {}
        for feature, scores in all_importance.items():
            avg_importance[feature] = np.mean(scores)
        
        # Sort by importance
        sorted_importance = dict(
            sorted(avg_importance.items(), key=lambda x: x[1], reverse=True)[:20]
        )
        
        return sorted_importance
    
    def get_training_status(self) -> Dict[str, Any]:
        """Get current training status and model information"""
        
        model_files = list(self.model_dir.glob("*_model.joblib"))
        
        models = {}
        for model_file in model_files:
            model_name = model_file.stem.replace("_model", "")
            models[model_name] = {
                'file_path': str(model_file),
                'file_size': model_file.stat().st_size,
                'last_modified': datetime.fromtimestamp(model_file.stat().st_mtime).isoformat()
            }
        
        # Load latest training metadata
        metadata_path = self.model_dir / "training_metadata.json"
        latest_metadata = None
        
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                latest_metadata = json.load(f)
        
        return {
            'models': models,
            'latest_training': latest_metadata,
            'training_history_count': len(self.training_history),
            'model_directory': str(self.model_dir)
        }
