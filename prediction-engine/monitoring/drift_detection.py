import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from scipy import stats
from scipy.spatial.distance import jensenshannon
import json
import logging

logger = logging.getLogger(__name__)

class DriftDetector:
    """Advanced drift detection for ML models"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        self.drift_thresholds = {
            'kl_divergence': 0.1,
            'jensen_shannon': 0.1,
            'wasserstein': 0.1,
            'ks_test': 0.05,
            'psi': 0.2
        }
    
    async def detect_comprehensive_drift(self, tenant_id: str) -> Dict[str, Any]:
        """Comprehensive drift detection using multiple methods"""
        
        try:
            # Get feature distributions
            feature_drift = await self._detect_feature_drift(tenant_id)
            
            # Get performance drift
            performance_drift = await self._detect_performance_drift(tenant_id)
            
            # Get prediction drift
            prediction_drift = await self._detect_prediction_drift(tenant_id)
            
            # Get concept drift
            concept_drift = await self._detect_concept_drift_advanced(tenant_id)
            
            # Aggregate results
            overall_drift = self._aggregate_drift_results([
                feature_drift, performance_drift, prediction_drift, concept_drift
            ])
            
            return {
                'overall_drift': overall_drift,
                'feature_drift': feature_drift,
                'performance_drift': performance_drift,
                'prediction_drift': prediction_drift,
                'concept_drift': concept_drift,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in comprehensive drift detection: {e}")
            return {'error': str(e)}
    
    async def _detect_feature_drift(self, tenant_id: str) -> Dict[str, Any]:
        """Detect drift in feature distributions"""
        
        query = """
        MATCH (f:FeatureDistribution {tenant_id: $tenant_id})
        WHERE f.timestamp > datetime() - duration('P30D')
        RETURN f.features as features, f.timestamp as timestamp
        ORDER BY f.timestamp
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, tenant_id=tenant_id)
                distributions = []
                
                for record in result:
                    distributions.append({
                        'features': json.loads(record['features']),
                        'timestamp': record['timestamp']
                    })
                
                if len(distributions) < 2:
                    return {'detected': False, 'reason': 'Insufficient data'}
                
                # Compare baseline vs current
                baseline = distributions[0]['features']
                current = distributions[-1]['features']
                
                drift_results = {}
                for feature_name, baseline_values in baseline.items():
                    if feature_name in current:
                        current_values = current[feature_name]
                        
                        # Convert to numpy arrays
                        baseline_array = np.array(baseline_values)
                        current_array = np.array(current_values)
                        
                        # Multiple drift detection methods
                        drift_scores = self._calculate_feature_drift_scores(
                            baseline_array, current_array
                        )
                        
                        drift_results[feature_name] = drift_scores
                
                # Determine overall feature drift
                max_drift_scores = {}
                for method in self.drift_thresholds.keys():
                    max_score = max([
                        result.get(method, 0) for result in drift_results.values()
                    ])
                    max_drift_scores[method] = max_score
                
                drift_detected = any(
                    max_drift_scores[method] > self.drift_thresholds[method]
                    for method in self.drift_thresholds
                )
                
                return {
                    'detected': drift_detected,
                    'max_drift_scores': max_drift_scores,
                    'feature_drift_scores': drift_results,
                    'baseline_date': distributions[0]['timestamp'],
                    'current_date': distributions[-1]['timestamp']
                }
                
        except Exception as e:
            logger.error(f"Error detecting feature drift: {e}")
            return {'detected': False, 'error': str(e)}
    
    def _calculate_feature_drift_scores(self, baseline: np.ndarray, current: np.ndarray) -> Dict[str, float]:
        """Calculate drift scores using multiple methods"""
        
        scores = {}
        
        try:
            # KL Divergence
            scores['kl_divergence'] = self._calculate_kl_divergence(baseline, current)
            
            # Jensen-Shannon Distance
            scores['jensen_shannon'] = self._calculate_jensen_shannon(baseline, current)
            
            # Wasserstein Distance
            scores['wasserstein'] = self._calculate_wasserstein(baseline, current)
            
            # Kolmogorov-Smirnov Test
            ks_stat, ks_pvalue = stats.ks_2samp(baseline, current)
            scores['ks_test'] = ks_pvalue  # Lower p-value indicates drift
            
            # Population Stability Index (PSI)
            scores['psi'] = self._calculate_psi(baseline, current)
            
        except Exception as e:
            logger.error(f"Error calculating drift scores: {e}")
            # Return default values
            scores = {method: 0.0 for method in self.drift_thresholds.keys()}
        
        return scores
    
    def _calculate_kl_divergence(self, p: np.ndarray, q: np.ndarray) -> float:
        """Calculate Kullback-Leibler divergence"""
        epsilon = 1e-10
        p = p + epsilon
        q = q + epsilon
        
        # Normalize to probability distributions
        p = p / p.sum()
        q = q / q.sum()
        
        # Calculate KL divergence
        kl_div = np.sum(p * np.log(p / q))
        
        return float(kl_div)
    
    def _calculate_jensen_shannon(self, p: np.ndarray, q: np.ndarray) -> float:
        """Calculate Jensen-Shannon distance"""
        epsilon = 1e-10
        p = p + epsilon
        q = q + epsilon
        
        # Normalize
        p = p / p.sum()
        q = q / q.sum()
        
        # Calculate Jensen-Shannon distance
        m = 0.5 * (p + q)
        js_div = 0.5 * (self._calculate_kl_divergence(p, m) + self._calculate_kl_divergence(q, m))
        
        return float(np.sqrt(js_div))
    
    def _calculate_wasserstein(self, p: np.ndarray, q: np.ndarray) -> float:
        """Calculate Wasserstein distance"""
        try:
            from scipy.stats import wasserstein_distance
            return float(wasserstein_distance(p, q))
        except ImportError:
            # Fallback to simple distance calculation
            return float(np.mean(np.abs(p - q)))
    
    def _calculate_psi(self, expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
        """Calculate Population Stability Index (PSI)"""
        try:
            # Create bins
            min_val = min(expected.min(), actual.min())
            max_val = max(expected.max(), actual.max())
            
            if max_val == min_val:
                return 0.0
            
            bin_edges = np.linspace(min_val, max_val, bins + 1)
            
            # Calculate frequencies
            expected_freq, _ = np.histogram(expected, bins=bin_edges)
            actual_freq, _ = np.histogram(actual, bins=bin_edges)
            
            # Avoid division by zero
            expected_freq = expected_freq + epsilon
            actual_freq = actual_freq + epsilon
            
            # Convert to percentages
            expected_pct = expected_freq / expected_freq.sum()
            actual_pct = actual_freq / actual_freq.sum()
            
            # Calculate PSI
            psi = np.sum((expected_pct - actual_pct) * np.log(expected_pct / actual_pct))
            
            return float(psi)
            
        except Exception as e:
            logger.error(f"Error calculating PSI: {e}")
            return 0.0
    
    async def _detect_performance_drift(self, tenant_id: str) -> Dict[str, Any]:
        """Detect drift in model performance metrics"""
        
        query = """
        MATCH (m:ModelMetrics {tenant_id: $tenant_id})
        WHERE m.timestamp > datetime() - duration('P30D')
        RETURN m.metrics as metrics, m.timestamp as timestamp
        ORDER BY m.timestamp
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, tenant_id=tenant_id)
                metrics_history = []
                
                for record in result:
                    metrics_data = json.loads(record['metrics'])
                    metrics_history.append({
                        'timestamp': record['timestamp'],
                        'f1_score': metrics_data.get('f1_score', 0),
                        'accuracy': metrics_data.get('accuracy', 0),
                        'precision': metrics_data.get('precision', 0),
                        'recall': metrics_data.get('recall', 0),
                        'auc_roc': metrics_data.get('auc_roc', 0)
                    })
                
                if len(metrics_history) < 5:
                    return {'detected': False, 'reason': 'Insufficient performance history'}
                
                # Split into baseline and recent
                baseline_metrics = metrics_history[:len(metrics_history)//2]
                recent_metrics = metrics_history[len(metrics_history)//2:]
                
                # Compare distributions
                drift_results = {}
                for metric in ['f1_score', 'accuracy', 'precision', 'recall', 'auc_roc']:
                    baseline_values = [m[metric] for m in baseline_metrics]
                    recent_values = [m[metric] for m in recent_metrics]
                    
                    # Perform statistical test
                    if len(baseline_values) >= 3 and len(recent_values) >= 3:
                        stat, p_value = stats.mannwhitneyu(baseline_values, recent_values)
                        drift_results[metric] = {
                            'p_value': float(p_value),
                            'drift_detected': p_value < 0.05,
                            'baseline_mean': float(np.mean(baseline_values)),
                            'recent_mean': float(np.mean(recent_values))
                        }
                
                # Overall performance drift
                drift_detected = any(
                    result['drift_detected'] for result in drift_results.values()
                )
                
                return {
                    'detected': drift_detected,
                    'metric_drift': drift_results,
                    'baseline_period': f"{baseline_metrics[0]['timestamp']} to {baseline_metrics[-1]['timestamp']}",
                    'recent_period': f"{recent_metrics[0]['timestamp']} to {recent_metrics[-1]['timestamp']}"
                }
                
        except Exception as e:
            logger.error(f"Error detecting performance drift: {e}")
            return {'detected': False, 'error': str(e)}
    
    async def _detect_prediction_drift(self, tenant_id: str) -> Dict[str, Any]:
        """Detect drift in prediction patterns"""
        
        query = """
        MATCH (p:Prediction {tenant_id: $tenant_id})
        WHERE p.timestamp > datetime() - duration('P30D')
        RETURN p.predicted_probability as predicted_prob,
               p.confidence as confidence,
               p.timestamp as timestamp
        ORDER BY p.timestamp
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, tenant_id=tenant_id)
                predictions = []
                
                for record in result:
                    predictions.append({
                        'predicted_prob': record['predicted_prob'],
                        'confidence': record['confidence'],
                        'timestamp': record['timestamp']
                    })
                
                if len(predictions) < 100:
                    return {'detected': False, 'reason': 'Insufficient prediction data'}
                
                # Split into baseline and recent
                split_point = len(predictions) // 2
                baseline_predictions = predictions[:split_point]
                recent_predictions = predictions[split_point:]
                
                # Extract probability distributions
                baseline_probs = [p['predicted_prob'] for p in baseline_predictions]
                recent_probs = [p['predicted_prob'] for p in recent_predictions]
                
                # Calculate drift scores
                drift_scores = self._calculate_feature_drift_scores(
                    np.array(baseline_probs), np.array(recent_probs)
                )
                
                drift_detected = any(
                    drift_scores[method] > self.drift_thresholds[method]
                    for method in self.drift_thresholds
                )
                
                return {
                    'detected': drift_detected,
                    'drift_scores': drift_scores,
                    'baseline_count': len(baseline_predictions),
                    'recent_count': len(recent_predictions),
                    'baseline_mean': float(np.mean(baseline_probs)),
                    'recent_mean': float(np.mean(recent_probs))
                }
                
        except Exception as e:
            logger.error(f"Error detecting prediction drift: {e}")
            return {'detected': False, 'error': str(e)}
    
    async def _detect_concept_drift_advanced(self, tenant_id: str) -> Dict[str, Any]:
        """Advanced concept drift detection"""
        
        # Get feature importance changes
        query = """
        MATCH (m:Model {tenant_id: $tenant_id, is_active: true})
        RETURN m.feature_importance as importance, m.last_trained as trained_at
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, tenant_id=tenant_id)
                record = result.single()
                
                if not record:
                    return {'detected': False, 'reason': 'No model found'}
                
                current_importance = json.loads(record['importance'])
                trained_at = record['trained_at']
                
                # Get recent feature importance from predictions
                recent_importance = await self._get_recent_feature_importance(tenant_id)
                
                if recent_importance:
                    # Compare importance distributions
                    importance_drift = self._compare_feature_importance(
                        current_importance, recent_importance
                    )
                    
                    # Check for significant changes
                    max_change = max(
                        abs(change) for change in importance_drift.values()
                    )
                    
                    return {
                        'detected': max_change > 0.2,  # 20% change threshold
                        'max_importance_change': float(max_change),
                        'importance_changes': importance_drift,
                        'model_trained_at': trained_at
                    }
                
                return {'detected': False, 'reason': 'No recent importance data'}
                
        except Exception as e:
            logger.error(f"Error detecting concept drift: {e}")
            return {'detected': False, 'error': str(e)}
    
    async def _get_recent_feature_importance(self, tenant_id: str) -> Optional[Dict[str, float]]:
        """Get recent feature importance from prediction explanations"""
        
        query = """
        MATCH (p:Prediction {tenant_id: $tenant_id})
        WHERE p.timestamp > datetime() - duration('P7D')
        RETURN p.explanation as explanation
        LIMIT 100
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, tenant_id=tenant_id)
                explanations = []
                
                for record in result:
                    explanation_data = json.loads(record['explanation'])
                    top_features = explanation_data.get('top_features', {})
                    explanations.append(top_features)
                
                if not explanations:
                    return None
                
                # Aggregate feature importance across explanations
                aggregated_importance = {}
                for explanation in explanations:
                    for feature, importance in explanation.items():
                        if feature not in aggregated_importance:
                            aggregated_importance[feature] = []
                        aggregated_importance[feature].append(abs(importance))
                
                # Calculate average importance
                avg_importance = {
                    feature: float(np.mean(importances))
                    for feature, importances in aggregated_importance.items()
                }
                
                return avg_importance
                
        except Exception as e:
            logger.error(f"Error getting recent feature importance: {e}")
            return None
    
    def _compare_feature_importance(self, baseline: Dict[str, float], recent: Dict[str, float]) -> Dict[str, float]:
        """Compare feature importance distributions"""
        
        changes = {}
        
        # Get common features
        common_features = set(baseline.keys()) & set(recent.keys())
        
        for feature in common_features:
            baseline_imp = baseline[feature]
            recent_imp = recent[feature]
            
            # Calculate relative change
            if baseline_imp > 0:
                change = (recent_imp - baseline_imp) / baseline_imp
                changes[feature] = change
        
        return changes
    
    def _aggregate_drift_results(self, drift_results: List[Dict]) -> Dict[str, Any]:
        """Aggregate drift results from multiple detectors"""
        
        detected_count = sum(1 for result in drift_results if result.get('detected', False))
        total_count = len(drift_results)
        
        overall_drift = {
            'detected': detected_count > total_count // 2,  # Majority vote
            'detection_rate': detected_count / total_count,
            'summary': {
                'feature_drift': drift_results[0].get('detected', False) if len(drift_results) > 0 else False,
                'performance_drift': drift_results[1].get('detected', False) if len(drift_results) > 1 else False,
                'prediction_drift': drift_results[2].get('detected', False) if len(drift_results) > 2 else False,
                'concept_drift': drift_results[3].get('detected', False) if len(drift_results) > 3 else False
            }
        }
        
        return overall_drift
