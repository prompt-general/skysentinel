import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from scipy import stats
import json
import logging

logger = logging.getLogger(__name__)

class ModelMonitor:
    """Monitor model performance and detect drift"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        
    async def monitor_model_performance(self, tenant_id: str) -> Dict[str, Any]:
        """Monitor model performance metrics"""
        
        # Get recent predictions and actual outcomes
        query = """
        MATCH (p:Prediction {tenant_id: $tenant_id})
        WHERE p.timestamp > datetime() - duration('P7D')
        OPTIONAL MATCH (p)-[:RELATES_TO]->(v:Violation)
        WITH p, 
             count(v) as actual_violations,
             CASE WHEN count(v) > 0 THEN 1 ELSE 0 END as actual_label
        RETURN p.predicted_probability as predicted_prob,
               actual_label,
               p.confidence as confidence,
               p.resource_type as resource_type
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, tenant_id=tenant_id)
                records = [dict(record) for record in result]
                
                if len(records) < 50:  # Minimum samples for meaningful metrics
                    return {
                        'status': 'insufficient_data',
                        'sample_size': len(records)
                    }
                
                # Calculate metrics
                df = pd.DataFrame(records)
                metrics = self._calculate_performance_metrics(df)
                
                # Check for drift
                drift_detected = await self._detect_concept_drift(tenant_id, df)
                
                # Check data quality
                data_quality = self._check_data_quality(df)
                
                return {
                    'status': 'success',
                    'metrics': metrics,
                    'drift_detected': drift_detected,
                    'data_quality': data_quality,
                    'sample_size': len(records),
                    'monitoring_window': '7d'
                }
                
        except Exception as e:
            logger.error(f"Error monitoring model: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _calculate_performance_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate performance metrics from predictions"""
        
        # Binary predictions (threshold = 0.5)
        df['predicted_label'] = (df['predicted_prob'] > 0.5).astype(int)
        
        # Calculate metrics
        from sklearn.metrics import (
            accuracy_score, precision_score, recall_score,
            f1_score, roc_auc_score, confusion_matrix
        )
        
        try:
            accuracy = accuracy_score(df['actual_label'], df['predicted_label'])
            precision = precision_score(df['actual_label'], df['predicted_label'], zero_division=0)
            recall = recall_score(df['actual_label'], df['predicted_label'], zero_division=0)
            f1 = f1_score(df['actual_label'], df['predicted_label'], zero_division=0)
            auc = roc_auc_score(df['actual_label'], df['predicted_prob'])
            
            # Calibration metrics
            calibration_error = self._calculate_calibration_error(
                df['predicted_prob'], df['actual_label']
            )
            
            # Confidence metrics
            avg_confidence = df['confidence'].mean()
            confidence_variance = df['confidence'].var()
            
            return {
                'accuracy': float(accuracy),
                'precision': float(precision),
                'recall': float(recall),
                'f1_score': float(f1),
                'auc_roc': float(auc),
                'calibration_error': float(calibration_error),
                'average_confidence': float(avg_confidence),
                'confidence_variance': float(confidence_variance),
                'sample_size': len(df)
            }
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {'error': str(e)}
    
    def _calculate_calibration_error(self, probabilities: pd.Series, labels: pd.Series) -> float:
        """Calculate calibration error (ECE)"""
        n_bins = 10
        bins = np.linspace(0, 1, n_bins + 1)
        bin_indices = np.digitize(probabilities, bins) - 1
        
        ece = 0
        for i in range(n_bins):
            mask = bin_indices == i
            if mask.sum() > 0:
                bin_prob = probabilities[mask].mean()
                bin_acc = labels[mask].mean()
                ece += mask.sum() * abs(bin_prob - bin_acc)
        
        return ece / len(probabilities)
    
    async def _detect_concept_drift(self, tenant_id: str, recent_data: pd.DataFrame) -> Dict[str, Any]:
        """Detect concept drift in model performance"""
        
        # Get historical performance for comparison
        query = """
        MATCH (m:ModelMetrics {tenant_id: $tenant_id})
        WHERE m.timestamp > datetime() - duration('P30D')
        RETURN m.metrics as metrics, m.timestamp as timestamp
        ORDER BY m.timestamp
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, tenant_id=tenant_id)
                historical_metrics = []
                
                for record in result:
                    metrics = json.loads(record['metrics'])
                    historical_metrics.append({
                        'timestamp': record['timestamp'],
                        'f1_score': metrics.get('f1_score', 0)
                    })
                
                if len(historical_metrics) < 2:
                    return {'detected': False, 'reason': 'Insufficient historical data'}
                
                # Calculate current F1 score
                current_f1 = self._calculate_performance_metrics(recent_data).get('f1_score', 0)
                
                # Get historical F1 scores
                historical_f1 = [m['f1_score'] for m in historical_metrics[-10:]]  # Last 10 readings
                
                if len(historical_f1) >= 5:
                    # Perform statistical test for drift
                    drift_detected, p_value = self._perform_drift_test(
                        historical_f1, current_f1
                    )
                    
                    return {
                        'detected': drift_detected,
                        'p_value': float(p_value),
                        'current_f1': float(current_f1),
                        'historical_mean_f1': float(np.mean(historical_f1)),
                        'threshold': 0.05
                    }
                
                return {'detected': False, 'reason': 'Insufficient historical samples'}
                
        except Exception as e:
            logger.error(f"Error detecting drift: {e}")
            return {'detected': False, 'error': str(e)}
    
    def _perform_drift_test(self, historical: List[float], current: float) -> Tuple[bool, float]:
        """Perform statistical test for concept drift"""
        # Use Mann-Whitney U test for distribution comparison
        # Compare current performance against historical distribution
        
        # Create synthetic current distribution based on confidence
        current_samples = np.random.normal(
            loc=current, 
            scale=0.05,  # Assume some variance
            size=len(historical)
        )
        
        # Perform Mann-Whitney U test
        statistic, p_value = stats.mannwhitneyu(historical, current_samples)
        
        return p_value < 0.05, p_value  # Drift if p < 0.05
    
    def _check_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Check quality of prediction data"""
        
        quality_issues = []
        
        # Check for missing values
        missing_values = df.isnull().sum().sum()
        if missing_values > 0:
            quality_issues.append(f"Missing values: {missing_values}")
        
        # Check class balance
        class_balance = df['actual_label'].value_counts(normalize=True)
        if len(class_balance) > 1 and abs(class_balance[0] - class_balance[1]) > 0.8:
            quality_issues.append(f"Severe class imbalance: {class_balance.to_dict()}")
        
        # Check prediction distribution
        pred_dist = df['predicted_prob'].describe()
        if pred_dist['std'] < 0.05:  # Very low variance
            quality_issues.append("Low variance in predictions")
        
        # Check confidence distribution
        conf_dist = df['confidence'].describe()
        if conf_dist['mean'] < 0.6:  # Low average confidence
            quality_issues.append(f"Low average confidence: {conf_dist['mean']:.2f}")
        
        return {
            'issues': quality_issues,
            'issue_count': len(quality_issues),
            'sample_size': len(df),
            'class_distribution': df['actual_label'].value_counts().to_dict(),
            'prediction_stats': {
                'mean': float(pred_dist['mean']),
                'std': float(pred_dist['std']),
                'min': float(pred_dist['min']),
                'max': float(pred_dist['max'])
            }
        }
    
    async def generate_monitoring_report(self, tenant_id: str) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        
        # Get performance metrics
        performance = await self.monitor_model_performance(tenant_id)
        
        # Get model info
        query = """
        MATCH (m:Model {tenant_id: $tenant_id, is_active: true})
        RETURN m.type as model_type,
               m.last_trained as last_trained,
               m.training_samples as training_samples
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, tenant_id=tenant_id)
                model_info = result.single()
                
                # Get prediction volume
                volume_query = """
                MATCH (p:Prediction {tenant_id: $tenant_id})
                WHERE p.timestamp > datetime() - duration('P1D')
                RETURN count(p) as daily_predictions
                """
                volume_result = session.run(volume_query, tenant_id=tenant_id)
                daily_volume = volume_result.single()['daily_predictions']
                
                report = {
                    'tenant_id': tenant_id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'model_info': dict(model_info) if model_info else {},
                    'performance': performance,
                    'prediction_volume': {
                        'daily': daily_volume,
                        'estimated_monthly': daily_volume * 30
                    },
                    'recommendations': self._generate_recommendations(performance)
                }
                
                # Store report
                await self._store_monitoring_report(report)
                
                return report
                
        except Exception as e:
            logger.error(f"Error generating monitoring report: {e}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, performance: Dict) -> List[Dict[str, Any]]:
        """Generate recommendations based on monitoring results"""
        
        recommendations = []
        
        if performance.get('status') != 'success':
            return [{'type': 'error', 'message': 'Unable to assess performance'}]
        
        metrics = performance.get('metrics', {})
        drift = performance.get('drift_detected', {})
        quality = performance.get('data_quality', {})
        
        # Performance-based recommendations
        if metrics.get('f1_score', 0) < 0.7:
            recommendations.append({
                'type': 'performance',
                'severity': 'high',
                'message': f"Low F1 score: {metrics.get('f1_score', 0):.3f}. Consider retraining model.",
                'action': 'retrain_model'
            })
        
        if metrics.get('calibration_error', 0) > 0.1:
            recommendations.append({
                'type': 'calibration',
                'severity': 'medium',
                'message': f"High calibration error: {metrics.get('calibration_error', 0):.3f}",
                'action': 'recalibrate_model'
            })
        
        # Drift-based recommendations
        if drift.get('detected', False):
            recommendations.append({
                'type': 'drift',
                'severity': 'high',
                'message': f"Concept drift detected (p={drift.get('p_value', 0):.3f})",
                'action': 'retrain_model'
            })
        
        # Data quality recommendations
        if quality.get('issue_count', 0) > 0:
            recommendations.append({
                'type': 'data_quality',
                'severity': 'medium',
                'message': f"Data quality issues detected: {quality.get('issue_count', 0)}",
                'action': 'review_data_quality',
                'issues': quality.get('issues', [])
            })
        
        # Confidence-based recommendations
        if metrics.get('average_confidence', 0) < 0.6:
            recommendations.append({
                'type': 'confidence',
                'severity': 'low',
                'message': f"Low average confidence: {metrics.get('average_confidence', 0):.3f}",
                'action': 'review_model_thresholds'
            })
        
        return recommendations if recommendations else [
            {'type': 'info', 'message': 'Model performance is satisfactory'}
        ]
    
    async def _store_monitoring_report(self, report: Dict):
        """Store monitoring report in Neo4j"""
        
        query = """
        MERGE (r:MonitoringReport {tenant_id: $tenant_id, timestamp: $timestamp})
        SET r.report = $report,
            r.created_at = datetime()
        """
        
        try:
            with self.driver.session() as session:
                session.run(query,
                    tenant_id=report['tenant_id'],
                    timestamp=report['timestamp'],
                    report=json.dumps(report)
                )
        except Exception as e:
            logger.error(f"Error storing monitoring report: {e}")
    
    async def detect_data_drift(self, tenant_id: str) -> Dict[str, Any]:
        """Detect data drift in feature distributions"""
        
        # Get recent feature distributions
        query = """
        MATCH (f:FeatureDistribution {tenant_id: $tenant_id})
        WHERE f.timestamp > datetime() - duration('P7D')
        RETURN f.features as features, f.timestamp as timestamp
        ORDER BY f.timestamp
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, tenant_id=tenant_id)
                recent_distributions = []
                
                for record in result:
                    recent_distributions.append({
                        'features': json.loads(record['features']),
                        'timestamp': record['timestamp']
                    })
                
                if len(recent_distributions) < 2:
                    return {'detected': False, 'reason': 'Insufficient data for comparison'}
                
                # Compare with baseline (oldest distribution)
                baseline = recent_distributions[0]['features']
                current = recent_distributions[-1]['features']
                
                # Calculate KL divergence for each feature
                drift_scores = {}
                for feature_name in baseline.keys():
                    if feature_name in current:
                        baseline_dist = np.array(baseline[feature_name])
                        current_dist = np.array(current[feature_name])
                        
                        # Calculate KL divergence
                        kl_div = self._calculate_kl_divergence(baseline_dist, current_dist)
                        drift_scores[feature_name] = kl_div
                
                # Determine if drift is significant
                max_drift = max(drift_scores.values()) if drift_scores else 0
                avg_drift = np.mean(list(drift_scores.values())) if drift_scores else 0
                
                drift_detected = max_drift > 0.1 or avg_drift > 0.05
                
                return {
                    'detected': drift_detected,
                    'max_drift_score': float(max_drift),
                    'avg_drift_score': float(avg_drift),
                    'feature_drift_scores': drift_scores,
                    'baseline_date': recent_distributions[0]['timestamp'],
                    'current_date': recent_distributions[-1]['timestamp']
                }
                
        except Exception as e:
            logger.error(f"Error detecting data drift: {e}")
            return {'detected': False, 'error': str(e)}
    
    def _calculate_kl_divergence(self, p: np.ndarray, q: np.ndarray) -> float:
        """Calculate Kullback-Leibler divergence between two distributions"""
        # Add small epsilon to avoid division by zero
        epsilon = 1e-10
        p = p + epsilon
        q = q + epsilon
        
        # Normalize
        p = p / p.sum()
        q = q / q.sum()
        
        # Calculate KL divergence
        kl_div = np.sum(p * np.log(p / q))
        
        return float(kl_div)
    
    async def get_monitoring_dashboard(self, tenant_id: str) -> Dict[str, Any]:
        """Get monitoring dashboard data"""
        
        try:
            # Get latest monitoring report
            report = await self.generate_monitoring_report(tenant_id)
            
            # Get historical metrics
            query = """
            MATCH (r:MonitoringReport {tenant_id: $tenant_id})
            WHERE r.timestamp > datetime() - duration('P30D')
            RETURN r.report as report, r.timestamp as timestamp
            ORDER BY r.timestamp
            """
            
            with self.driver.session() as session:
                result = session.run(query, tenant_id=tenant_id)
                historical_reports = []
                
                for record in result:
                    report_data = json.loads(record['report'])
                    historical_reports.append({
                        'timestamp': record['timestamp'],
                        'f1_score': report_data.get('performance', {}).get('metrics', {}).get('f1_score', 0),
                        'accuracy': report_data.get('performance', {}).get('metrics', {}).get('accuracy', 0),
                        'drift_detected': report_data.get('performance', {}).get('drift_detected', {}).get('detected', False)
                    })
            
            # Get data drift information
            data_drift = await self.detect_data_drift(tenant_id)
            
            return {
                'current_report': report,
                'historical_metrics': historical_reports,
                'data_drift': data_drift,
                'dashboard_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting monitoring dashboard: {e}")
            return {'error': str(e)}
