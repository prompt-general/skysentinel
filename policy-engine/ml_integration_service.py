from typing import Dict, List, Any, Optional
import asyncio
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class MLIntegrationService:
    """Service for integrating ML predictions with policy engine"""
    
    def __init__(self, neo4j_driver, prediction_engine):
        self.driver = neo4j_driver
        self.prediction_engine = prediction_engine
        
    async def create_ml_enhanced_policy(self, 
                                      policy_id: str,
                                      ml_threshold: float = 0.7,
                                      ml_weight: float = 0.7) -> Dict[str, Any]:
        """Create an ML-enhanced policy"""
        
        try:
            # Store ML-enhanced policy configuration
            query = """
            MERGE (p:Policy {id: $policy_id})
            SET p.ml_enabled = true,
                p.ml_threshold = $ml_threshold,
                p.ml_weight = $ml_weight,
                p.type = 'ml_enhanced',
                p.created_at = datetime(),
                p.updated_at = datetime()
            """
            
            with self.driver.session() as session:
                session.run(query,
                    policy_id=policy_id,
                    ml_threshold=ml_threshold,
                    ml_weight=ml_weight
                )
            
            return {
                'status': 'success',
                'policy_id': policy_id,
                'ml_threshold': ml_threshold,
                'ml_weight': ml_weight,
                'created_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating ML-enhanced policy: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def evaluate_with_ml_policy(self, 
                                   policy_id: str,
                                   resource: Dict[str, Any],
                                   context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate resource with ML-enhanced policy"""
        
        try:
            # Get policy configuration
            policy_config = await self._get_ml_policy_config(policy_id)
            
            if not policy_config:
                return {'status': 'error', 'message': 'Policy not found'}
            
            # Get ML prediction
            ml_prediction = await self.prediction_engine.predict_single({
                'resource': resource,
                'context': context
            })
            
            # Get traditional policy evaluation
            traditional_result = await self._evaluate_traditional_policy(
                policy_id, resource, context
            )
            
            # Combine results
            combined_result = self._combine_ml_policy_results(
                traditional_result, ml_prediction, policy_config
            )
            
            # Store evaluation
            await self._store_ml_policy_evaluation(
                policy_id, resource, context, combined_result
            )
            
            return combined_result
            
        except Exception as e:
            logger.error(f"Error evaluating with ML policy: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def _get_ml_policy_config(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Get ML-enhanced policy configuration"""
        
        query = """
        MATCH (p:Policy {id: $policy_id, ml_enabled: true})
        RETURN p.ml_threshold as ml_threshold,
               p.ml_weight as ml_weight,
               p.rules as rules
        """
        
        with self.driver.session() as session:
            result = session.run(query, policy_id=policy_id)
            record = result.single()
            
            if record:
                return {
                    'ml_threshold': record['ml_threshold'],
                    'ml_weight': record['ml_weight'],
                    'rules': json.loads(record['rules']) if record['rules'] else []
                }
        
        return None
    
    async def _evaluate_traditional_policy(self, 
                                         policy_id: str,
                                         resource: Dict[str, Any],
                                         context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate resource with traditional policy rules"""
        
        # This would integrate with the existing policy engine
        # For now, return a mock result
        return {
            'violations': [],
            'risk_score': 0.2,
            'recommendations': []
        }
    
    def _combine_ml_policy_results(self, 
                                 traditional_result: Dict,
                                 ml_prediction: Dict,
                                 policy_config: Dict) -> Dict[str, Any]:
        """Combine traditional and ML policy results"""
        
        ml_threshold = policy_config.get('ml_threshold', 0.7)
        ml_weight = policy_config.get('ml_weight', 0.7)
        policy_weight = 1 - ml_weight
        
        # Calculate combined risk
        traditional_risk = traditional_result.get('risk_score', 0)
        ml_risk = ml_prediction.get('violation_probability', 0)
        
        combined_risk = (traditional_risk * policy_weight) + (ml_risk * ml_weight)
        
        # Determine violations
        violations = traditional_result.get('violations', [])
        
        # Add ML-predicted violations if above threshold
        if ml_risk > ml_threshold:
            ml_violations = ml_prediction.get('predicted_violations', [])
            for violation in ml_violations:
                violations.append({
                    'type': 'ml_predicted',
                    'description': violation,
                    'severity': 'high' if ml_risk > 0.8 else 'medium',
                    'confidence': ml_prediction.get('confidence', 0)
                })
        
        # Generate recommendations
        recommendations = traditional_result.get('recommendations', [])
        
        if ml_risk > ml_threshold:
            recommendations.append({
                'type': 'ml_warning',
                'message': f"ML predicts high violation risk ({ml_risk:.1%})",
                'action': 'review',
                'priority': 'high'
            })
        
        return {
            'violations': violations,
            'combined_risk_score': combined_risk,
            'traditional_risk_score': traditional_risk,
            'ml_risk_score': ml_risk,
            'recommendations': recommendations,
            'ml_prediction': ml_prediction,
            'policy_config': policy_config,
            'evaluation_timestamp': datetime.utcnow().isoformat()
        }
    
    async def _store_ml_policy_evaluation(self, 
                                        policy_id: str,
                                        resource: Dict[str, Any],
                                        context: Dict[str, Any],
                                        result: Dict[str, Any]):
        """Store ML policy evaluation result"""
        
        query = """
        MERGE (e:Evaluation {id: $eval_id})
        SET e.policy_id = $policy_id,
            e.resource = $resource,
            e.context = $context,
            e.result = $result,
            e.timestamp = datetime(),
            e.type = 'ml_policy_evaluation'
        
        WITH e
        MATCH (p:Policy {id: $policy_id})
        MERGE (e)-[:EVALUATED_WITH]->(p)
        """
        
        try:
            eval_id = f"ml-eval-{datetime.utcnow().timestamp()}"
            
            with self.driver.session() as session:
                session.run(query,
                    eval_id=eval_id,
                    policy_id=policy_id,
                    resource=json.dumps(resource),
                    context=json.dumps(context),
                    result=json.dumps(result)
                )
        except Exception as e:
            logger.error(f"Error storing ML policy evaluation: {e}")
    
    async def get_ml_policy_analytics(self, policy_id: str) -> Dict[str, Any]:
        """Get analytics for ML-enhanced policy"""
        
        try:
            # Get evaluation statistics
            query = """
            MATCH (e:Evaluation {policy_id: $policy_id, type: 'ml_policy_evaluation'})
            WHERE e.timestamp > datetime() - duration('P30D')
            RETURN e.result as result, e.timestamp as timestamp
            ORDER BY e.timestamp DESC
            """
            
            with self.driver.session() as session:
                result = session.run(query, policy_id=policy_id)
                evaluations = []
                
                for record in result:
                    result_data = json.loads(record['result'])
                    evaluations.append({
                        'result': result_data,
                        'timestamp': record['timestamp']
                    })
            
            if not evaluations:
                return {
                    'policy_id': policy_id,
                    'total_evaluations': 0,
                    'analytics': {}
                }
            
            # Calculate analytics
            analytics = self._calculate_ml_policy_analytics(evaluations)
            
            return {
                'policy_id': policy_id,
                'total_evaluations': len(evaluations),
                'analytics': analytics,
                'analytics_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting ML policy analytics: {e}")
            return {'error': str(e)}
    
    def _calculate_ml_policy_analytics(self, evaluations: List[Dict]) -> Dict[str, Any]:
        """Calculate analytics for ML policy evaluations"""
        
        total_evals = len(evaluations)
        ml_triggered = 0
        policy_triggered = 0
        combined_triggered = 0
        
        ml_risk_scores = []
        traditional_risk_scores = []
        combined_risk_scores = []
        
        for eval_data in evaluations:
            result = eval_data['result']
            
            ml_risk = result.get('ml_risk_score', 0)
            traditional_risk = result.get('traditional_risk_score', 0)
            combined_risk = result.get('combined_risk_score', 0)
            
            ml_risk_scores.append(ml_risk)
            traditional_risk_scores.append(traditional_risk)
            combined_risk_scores.append(combined_risk)
            
            # Count triggers
            violations = result.get('violations', [])
            ml_violations = [v for v in violations if v.get('type') == 'ml_predicted']
            traditional_violations = [v for v in violations if v.get('type') != 'ml_predicted']
            
            if ml_violations:
                ml_triggered += 1
            if traditional_violations:
                policy_triggered += 1
            if violations:
                combined_triggered += 1
        
        return {
            'trigger_rates': {
                'ml_triggered_rate': ml_triggered / total_evals if total_evals > 0 else 0,
                'policy_triggered_rate': policy_triggered / total_evals if total_evals > 0 else 0,
                'combined_triggered_rate': combined_triggered / total_evals if total_evals > 0 else 0
            },
            'risk_statistics': {
                'ml_risk': {
                    'mean': sum(ml_risk_scores) / len(ml_risk_scores) if ml_risk_scores else 0,
                    'max': max(ml_risk_scores) if ml_risk_scores else 0,
                    'min': min(ml_risk_scores) if ml_risk_scores else 0
                },
                'traditional_risk': {
                    'mean': sum(traditional_risk_scores) / len(traditional_risk_scores) if traditional_risk_scores else 0,
                    'max': max(traditional_risk_scores) if traditional_risk_scores else 0,
                    'min': min(traditional_risk_scores) if traditional_risk_scores else 0
                },
                'combined_risk': {
                    'mean': sum(combined_risk_scores) / len(combined_risk_scores) if combined_risk_scores else 0,
                    'max': max(combined_risk_scores) if combined_risk_scores else 0,
                    'min': min(combined_risk_scores) if combined_risk_scores else 0
                }
            },
            'evaluation_count': total_evals
        }
    
    async def update_ml_policy_config(self, 
                                    policy_id: str,
                                    updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update ML-enhanced policy configuration"""
        
        try:
            # Build update query
            set_clauses = []
            parameters = {'policy_id': policy_id}
            
            if 'ml_threshold' in updates:
                set_clauses.append('p.ml_threshold = $ml_threshold')
                parameters['ml_threshold'] = updates['ml_threshold']
            
            if 'ml_weight' in updates:
                set_clauses.append('p.ml_weight = $ml_weight')
                parameters['ml_weight'] = updates['ml_weight']
            
            if 'enabled' in updates:
                set_clauses.append('p.ml_enabled = $enabled')
                parameters['enabled'] = updates['enabled']
            
            if not set_clauses:
                return {'status': 'error', 'message': 'No valid updates provided'}
            
            set_clauses.append('p.updated_at = datetime()')
            
            query = f"""
            MATCH (p:Policy {{id: $policy_id}})
            SET {', '.join(set_clauses)}
            RETURN p.id as policy_id
            """
            
            with self.driver.session() as session:
                result = session.run(query, **parameters)
                record = result.single()
                
                if record:
                    return {
                        'status': 'success',
                        'policy_id': record['policy_id'],
                        'updates': updates,
                        'updated_at': datetime.utcnow().isoformat()
                    }
                else:
                    return {'status': 'error', 'message': 'Policy not found'}
                    
        except Exception as e:
            logger.error(f"Error updating ML policy config: {e}")
            return {'status': 'error', 'error': str(e)}
