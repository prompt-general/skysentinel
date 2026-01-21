import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ModelTrainer:
    """Orchestrates model training and evaluation"""
    
    def __init__(self, neo4j_driver, model_storage_path: str = "./models"):
        self.driver = neo4j_driver
        self.model_storage_path = Path(model_storage_path)
        self.model_storage_path.mkdir(exist_ok=True)
        
        # Initialize predictors
        from ..models.xgboost_predictor import XGBoostPredictor
        from ..models.lightgbm_predictor import LightGBMPredictor
        from ..engine import ModelMetrics
        
        self.predictors = {
            'xgboost': XGBoostPredictor(),
            'lightgbm': LightGBMPredictor()
        }
        self.active_predictor = 'xgboost'
        
    async def train_all_models(self, tenant_id: str) -> Dict[str, Any]:
        """Train all models for a tenant"""
        logger.info(f"Starting model training for tenant: {tenant_id}")
        
        # Collect training data
        from .data_collector import TrainingDataCollector
        data_collector = TrainingDataCollector(self.driver)
        features, labels = data_collector.collect_training_data(lookback_days=90)
        
        if features.empty or labels.empty:
            logger.error("No training data available")
            return {'status': 'error', 'message': 'No training data'}
        
        # Train each model
        results = {}
        for model_name, predictor in self.predictors.items():
            try:
                logger.info(f"Training {model_name} model...")
                
                # Train model
                metrics = predictor.train(features, labels)
                
                # Save model
                model_path = self.model_storage_path / f"{tenant_id}_{model_name}.joblib"
                predictor.save(str(model_path))
                
                # Store results
                results[model_name] = {
                    'status': 'success',
                    'metrics': self._serialize_metrics(metrics),
                    'model_path': str(model_path),
                    'training_samples': len(features)
                }
                
                logger.info(f"{model_name} training completed: F1={metrics.f1_score:.3f}")
                
            except Exception as e:
                logger.error(f"Error training {model_name}: {e}")
                results[model_name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Select best model
        best_model = self._select_best_model(results)
        self.active_predictor = best_model
        
        # Update model registry
        await self._update_model_registry(tenant_id, best_model, results)
        
        return {
            'status': 'success',
            'best_model': best_model,
            'results': results,
            'training_summary': {
                'total_samples': len(features),
                'positive_samples': int(labels.sum()),
                'negative_samples': int(len(labels) - labels.sum()),
                'training_time': datetime.utcnow().isoformat()
            }
        }
    
    def _select_best_model(self, results: Dict) -> str:
        """Select best model based on F1 score"""
        best_model = 'xgboost'  # Default
        best_f1 = 0
        
        for model_name, result in results.items():
            if result['status'] == 'success':
                f1_score = result['metrics'].get('f1_score', 0)
                if f1_score > best_f1:
                    best_f1 = f1_score
                    best_model = model_name
        
        return best_model
    
    def _serialize_metrics(self, metrics) -> Dict[str, Any]:
        """Serialize metrics for storage"""
        return {
            'accuracy': metrics.accuracy,
            'precision': metrics.precision,
            'recall': metrics.recall,
            'f1_score': metrics.f1_score,
            'auc_roc': metrics.auc_roc,
            'log_loss': metrics.log_loss,
            'training_time_seconds': metrics.training_time_seconds,
            'last_trained': metrics.last_trained,
            'feature_importance': metrics.feature_importance
        }
    
    async def _update_model_registry(self, 
                                   tenant_id: str, 
                                   best_model: str,
                                   results: Dict):
        """Update model registry in Neo4j"""
        query = """
        MERGE (m:Model {tenant_id: $tenant_id, type: $model_type})
        SET m.metrics = $metrics,
            m.model_path = $model_path,
            m.is_active = $is_active,
            m.last_trained = datetime(),
            m.training_samples = $training_samples,
            m.status = 'trained'
        """
        
        for model_name, result in results.items():
            if result['status'] == 'success':
                with self.driver.session() as session:
                    session.run(query,
                        tenant_id=tenant_id,
                        model_type=model_name,
                        metrics=json.dumps(result['metrics']),
                        model_path=result['model_path'],
                        is_active=(model_name == best_model),
                        training_samples=result['training_samples']
                    )
    
    async def incremental_train(self, 
                              tenant_id: str,
                              new_violations: List[Dict]) -> Dict[str, Any]:
        """Incrementally train model with new violations"""
        logger.info(f"Incremental training for tenant {tenant_id}")
        
        # Load current model
        model_path = self.model_storage_path / f"{tenant_id}_{self.active_predictor}.joblib"
        if not model_path.exists():
            logger.warning("No existing model found, performing full training")
            return await self.train_all_models(tenant_id)
        
        # Load predictor
        predictor = self.predictors[self.active_predictor]
        predictor.load(str(model_path))
        
        # Extract features from new violations
        from ..features import FeatureEngineer
        feature_engineer = FeatureEngineer(self.driver)
        new_features = []
        new_labels = []
        
        for violation in new_violations:
            resource = violation.get('resource', {})
            if resource:
                features = feature_engineer._extract_resource_features(resource)
                features['resource_id'] = resource.get('id', '')
                new_features.append(features)
                new_labels.append(1)  # Positive samples
        
        if not new_features:
            return {'status': 'skipped', 'message': 'No new violation data'}
        
        # Get historical data for negative samples
        from .data_collector import TrainingDataCollector
        data_collector = TrainingDataCollector(self.driver)
        historical_features, historical_labels = data_collector.collect_training_data(
            lookback_days=30
        )
        
        if not historical_features.empty:
            # Combine with new data
            all_features = pd.concat([historical_features, pd.DataFrame(new_features)])
            all_labels = pd.concat([
                historical_labels, 
                pd.Series(new_labels, index=range(len(new_labels)))
            ])
            
            # Retrain model
            metrics = predictor.train(all_features, all_labels)
            
            # Save updated model
            predictor.save(str(model_path))
            
            return {
                'status': 'success',
                'samples_added': len(new_features),
                'total_samples': len(all_features),
                'metrics': self._serialize_metrics(metrics)
            }
        
        return {'status': 'skipped', 'message': 'Insufficient historical data'}
    
    def get_model_info(self, tenant_id: str) -> Dict[str, Any]:
        """Get information about trained models"""
        model_info = {}
        
        for model_name in self.predictors.keys():
            model_path = self.model_storage_path / f"{tenant_id}_{model_name}.joblib"
            if model_path.exists():
                try:
                    # Load model to get info
                    predictor = self.predictors[model_name]
                    predictor.load(str(model_path))
                    
                    model_info[model_name] = {
                        'exists': True,
                        'path': str(model_path),
                        'size_mb': model_path.stat().st_size / (1024 * 1024),
                        'last_modified': datetime.fromtimestamp(
                            model_path.stat().st_mtime
                        ).isoformat(),
                        'is_active': model_name == self.active_predictor
                    }
                except Exception as e:
                    model_info[model_name] = {
                        'exists': True,
                        'error': str(e)
                    }
            else:
                model_info[model_name] = {'exists': False}
        
        return model_info
    
    async def evaluate_model(self, tenant_id: str, test_data: List[Dict]) -> Dict[str, Any]:
        """Evaluate model performance on test data"""
        logger.info(f"Evaluating model for tenant {tenant_id}")
        
        # Load active model
        model_path = self.model_storage_path / f"{tenant_id}_{self.active_predictor}.joblib"
        if not model_path.exists():
            return {'status': 'error', 'message': 'No trained model found'}
        
        predictor = self.predictors[self.active_predictor]
        predictor.load(str(model_path))
        
        # Extract features from test data
        from ..features import FeatureEngineer
        feature_engineer = FeatureEngineer(self.driver)
        test_features = []
        test_labels = []
        
        for item in test_data:
            resource = item.get('resource', {})
            label = item.get('label', 0)
            
            if resource:
                features = feature_engineer._extract_resource_features(resource)
                features['resource_id'] = resource.get('id', '')
                test_features.append(features)
                test_labels.append(label)
        
        if not test_features:
            return {'status': 'error', 'message': 'No test data available'}
        
        # Make predictions
        features_df = pd.DataFrame(test_features)
        predictions = predictor.predict(features_df)
        
        # Calculate metrics
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        
        y_pred = [1 if p.violation_probability > 0.5 else 0 for p in predictions]
        y_pred_proba = [p.violation_probability for p in predictions]
        
        metrics = {
            'accuracy': float(accuracy_score(test_labels, y_pred)),
            'precision': float(precision_score(test_labels, y_pred, zero_division=0)),
            'recall': float(recall_score(test_labels, y_pred, zero_division=0)),
            'f1_score': float(f1_score(test_labels, y_pred, zero_division=0)),
            'auc_roc': float(roc_auc_score(test_labels, y_pred_proba))
        }
        
        # Store evaluation results
        await self._store_evaluation_results(tenant_id, metrics, len(test_data))
        
        return {
            'status': 'success',
            'metrics': metrics,
            'test_samples': len(test_data),
            'model_type': self.active_predictor,
            'evaluation_time': datetime.utcnow().isoformat()
        }
    
    async def _store_evaluation_results(self, tenant_id: str, metrics: Dict, sample_count: int):
        """Store evaluation results in Neo4j"""
        query = """
        MATCH (m:Model {tenant_id: $tenant_id, type: $model_type, is_active: true})
        CREATE (e:Evaluation {
            tenant_id: $tenant_id,
            model_type: $model_type,
            metrics: $metrics,
            sample_count: $sample_count,
            evaluation_time: datetime()
        })
        CREATE (m)-[:EVALUATED_ON]->(e)
        """
        
        with self.driver.session() as session:
            session.run(query,
                tenant_id=tenant_id,
                model_type=self.active_predictor,
                metrics=json.dumps(metrics),
                sample_count=sample_count
            )
    
    async def schedule_training(self, tenant_id: str, schedule: str = "daily") -> Dict[str, Any]:
        """Schedule periodic model training"""
        logger.info(f"Scheduling {schedule} training for tenant {tenant_id}")
        
        # Store training schedule
        query = """
        MERGE (s:TrainingSchedule {tenant_id: $tenant_id})
        SET s.schedule = $schedule,
            s.last_scheduled = datetime(),
            s.next_training = $next_training,
            s.is_active = true
        """
        
        # Calculate next training time
        if schedule == "daily":
            next_training = datetime.now() + timedelta(days=1)
        elif schedule == "weekly":
            next_training = datetime.now() + timedelta(weeks=1)
        elif schedule == "monthly":
            next_training = datetime.now() + timedelta(days=30)
        else:
            next_training = datetime.now() + timedelta(days=1)
        
        with self.driver.session() as session:
            session.run(query,
                tenant_id=tenant_id,
                schedule=schedule,
                next_training=next_training
            )
        
        return {
            'status': 'success',
            'schedule': schedule,
            'next_training': next_training.isoformat()
        }
    
    async def get_training_history(self, tenant_id: str, limit: int = 10) -> List[Dict]:
        """Get training history for a tenant"""
        query = """
        MATCH (m:Model {tenant_id: $tenant_id})
        OPTIONAL MATCH (m)-[:EVALUATED_ON]->(e:Evaluation)
        RETURN m.type as model_type,
               m.last_trained as last_trained,
               m.training_samples as training_samples,
               m.status as status,
               e.evaluation_time as evaluation_time,
               e.metrics as evaluation_metrics
        ORDER BY m.last_trained DESC
        LIMIT $limit
        """
        
        with self.driver.session() as session:
            result = session.run(query, tenant_id=tenant_id, limit=limit)
            records = []
            
            for record in result:
                record_dict = dict(record)
                if record_dict['evaluation_metrics']:
                    record_dict['evaluation_metrics'] = json.loads(record_dict['evaluation_metrics'])
                records.append(record_dict)
            
            return records
    
    async def cleanup_old_models(self, tenant_id: str, keep_count: int = 3) -> Dict[str, Any]:
        """Clean up old model versions, keeping only the most recent ones"""
        logger.info(f"Cleaning up old models for tenant {tenant_id}, keeping {keep_count}")
        
        # Get all model files for tenant
        model_files = {}
        for model_name in self.predictors.keys():
            pattern = f"{tenant_id}_{model_name}_*.joblib"
            files = list(self.model_storage_path.glob(pattern))
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            model_files[model_name] = files
        
        removed_files = []
        
        for model_name, files in model_files.items():
            # Keep only the most recent files
            files_to_remove = files[keep_count:]
            
            for file_path in files_to_remove:
                try:
                    file_path.unlink()
                    removed_files.append(str(file_path))
                except Exception as e:
                    logger.error(f"Error removing {file_path}: {e}")
        
        return {
            'status': 'success',
            'removed_files': removed_files,
            'files_removed': len(removed_files)
        }
