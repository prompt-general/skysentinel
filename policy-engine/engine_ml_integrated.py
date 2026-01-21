from typing import Dict, List, Any, Optional
import asyncio
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MLEnhancedPolicyEngine:
    """Policy engine enhanced with ML predictions"""
    
    def __init__(self, neo4j_driver, cloud_clients, prediction_engine):
        self.driver = neo4j_driver
        self.cloud_clients = cloud_clients
        self.prediction_engine = prediction_engine
        
        # Initialize base policy engine
        from .engine import PolicyEngine
        self.base_engine = PolicyEngine(neo4j_driver, cloud_clients)
        
    async def evaluate_event_with_ml(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate event with ML predictions"""
        
        # Step 1: Traditional policy evaluation
        policy_violations = self.base_engine.evaluate_event(event)
        
        # Step 2: ML prediction
        ml_prediction = await self._get_ml_prediction(event)
        
        # Step 3: Combine results
        combined_result = self._combine_results(policy_violations, ml_prediction)
        
        # Step 4: Store combined evaluation
        await self._store_combined_evaluation(event, combined_result)
        
        return combined_result
    
    async def evaluate_iac_with_ml(self, 
                                 iac_plan: Dict[str, Any],
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate IaC plan with ML predictions"""
        
        # Step 1: Traditional policy evaluation
        from cicd_prevention.service import CICDService
        cicd_service = CICDService(self.base_engine, self.prediction_engine, self.driver)
        
        policy_result = await cicd_service.evaluate_plan(
            iac_type=context.get('iac_type', 'terraform'),
            iac_content=iac_plan,
            context=context
        )
        
        # Step 2: Enhanced ML prediction
        ml_result = await self.prediction_engine.predict_iac(iac_plan, context)
        
        # Step 3: Combine and enhance
        enhanced_result = self._enhance_with_ml(policy_result, ml_result)
        
        return enhanced_result
    
    async def _get_ml_prediction(self, event: Dict) -> Dict[str, Any]:
        """Get ML prediction for an event"""
        try:
            # Extract resource information
            resource = event.get('resource', {})
            
            # Create prediction request
            prediction_request = {
                'resource': resource,
                'operation': event.get('operation'),
                'context': {
                    'stage': 'runtime',
                    'principal': event.get('principal', {}),
                    'timestamp': event.get('timestamp')
                }
            }
            
            # Get prediction
            prediction = await self.prediction_engine.predict_single(
                prediction_request
            )
            
            return {
                'violation_probability': prediction.get('violation_probability', 0),
                'confidence': prediction.get('confidence', 0),
                'predicted_violations': prediction.get('predicted_violations', []),
                'explanation': prediction.get('explanation', {})
            }
            
        except Exception as e:
            logger.error(f"Error getting ML prediction: {e}")
            return {
                'violation_probability': 0,
                'confidence': 0,
                'error': str(e)
            }
    
    def _combine_results(self, 
                        policy_violations: List[Dict], 
                        ml_prediction: Dict) -> Dict[str, Any]:
        """Combine policy and ML results"""
        
        # Calculate combined risk score
        policy_risk = len(policy_violations) * 0.3  # Weight policy violations
        ml_risk = ml_prediction.get('violation_probability', 0) * 0.7  # Weight ML prediction
        
        combined_risk = policy_risk + ml_risk
        
        # Determine action
        if combined_risk > 0.8:
            action = 'block'
        elif combined_risk > 0.5:
            action = 'warn'
        else:
            action = 'allow'
        
        # Generate explanation
        explanation = {
            'policy_violation_count': len(policy_violations),
            'ml_violation_probability': ml_prediction.get('violation_probability', 0),
            'ml_confidence': ml_prediction.get('confidence', 0),
            'combined_risk_score': combined_risk,
            'ml_explanation': ml_prediction.get('explanation', {}),
            'policy_violations': [
                {
                    'policy': v.get('policy_name'),
                    'severity': v.get('severity'),
                    'description': v.get('description')
                }
                for v in policy_violations[:5]  # Limit to top 5
            ]
        }
        
        return {
            'action': action,
            'combined_risk_score': combined_risk,
            'policy_violations': policy_violations,
            'ml_prediction': ml_prediction,
            'explanation': explanation,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _enhance_with_ml(self, 
                        policy_result: Dict, 
                        ml_result: Dict) -> Dict[str, Any]:
        """Enhance policy result with ML insights"""
        
        enhanced = policy_result.copy()
        
        # Add ML predictions
        enhanced['ml_predictions'] = ml_result
        
        # Enhance recommendations
        enhanced_recommendations = enhanced.get('recommendations', [])
        
        # Add ML-based recommendations
        high_risk_resources = ml_result.get('high_risk_resources', [])
        for resource in high_risk_resources[:3]:  # Top 3 high-risk
            if resource.get('violation_probability', 0) > 0.7:
                enhanced_recommendations.append({
                    'type': 'ml_high_risk',
                    'severity': 'high',
                    'resource': resource.get('resource_id'),
                    'message': f"ML predicts high violation risk ({resource.get('violation_probability', 0):.1%})",
                    'top_risk_factors': resource.get('top_features', [])
                })
        
        # Update overall result based on ML
        if ml_result.get('violation_probability', 0) > 0.8:
            if enhanced['result'] == 'pass':
                enhanced['result'] = 'warn'
                enhanced['result_reason'] = 'High ML-predicted violation probability'
        
        enhanced['recommendations'] = enhanced_recommendations
        
        return enhanced
    
    async def _store_combined_evaluation(self, 
                                       event: Dict, 
                                       result: Dict):
        """Store combined evaluation in Neo4j"""
        
        query = """
        MERGE (e:Evaluation {id: $eval_id})
        SET e.event = $event,
            e.result = $result,
            e.timestamp = datetime(),
            e.type = 'combined_ml_policy'
        
        WITH e
        MATCH (r:Resource {id: $resource_id})
        WHERE r.valid_to IS NULL
        MERGE (e)-[:EVALUATES]->(r)
        
        // Link ML prediction
        MERGE (p:Prediction {id: $prediction_id})
        SET p.violation_probability = $violation_probability,
            p.confidence = $confidence,
            p.explanation = $explanation
        
        MERGE (e)-[:USES_PREDICTION]->(p)
        """
        
        try:
            eval_id = f"eval-{datetime.utcnow().timestamp()}"
            prediction_id = f"pred-{datetime.utcnow().timestamp()}"
            
            with self.driver.session() as session:
                session.run(query,
                    eval_id=eval_id,
                    event=json.dumps(event),
                    result=json.dumps(result),
                    resource_id=event.get('resource', {}).get('id', 'unknown'),
                    prediction_id=prediction_id,
                    violation_probability=result.get('ml_prediction', {}).get('violation_probability', 0),
                    confidence=result.get('ml_prediction', {}).get('confidence', 0),
                    explanation=json.dumps(result.get('ml_prediction', {}).get('explanation', {}))
                )
        except Exception as e:
            logger.error(f"Error storing combined evaluation: {e}")
    
    async def evaluate_batch_with_ml(self, events: List[Dict]) -> List[Dict]:
        """Evaluate multiple events with ML predictions"""
        
        results = []
        
        # Get ML predictions for all events
        ml_predictions = await self._get_batch_ml_predictions(events)
        
        # Evaluate each event
        for i, event in enumerate(events):
            # Traditional policy evaluation
            policy_violations = self.base_engine.evaluate_event(event)
            
            # Get corresponding ML prediction
            ml_prediction = ml_predictions[i] if i < len(ml_predictions) else {}
            
            # Combine results
            combined_result = self._combine_results(policy_violations, ml_prediction)
            results.append(combined_result)
        
        return results
    
    async def _get_batch_ml_predictions(self, events: List[Dict]) -> List[Dict]:
        """Get ML predictions for multiple events"""
        
        try:
            # Create batch prediction request
            prediction_requests = []
            for event in events:
                resource = event.get('resource', {})
                prediction_requests.append({
                    'resource': resource,
                    'operation': event.get('operation'),
                    'context': {
                        'stage': 'runtime',
                        'principal': event.get('principal', {}),
                        'timestamp': event.get('timestamp')
                    }
                })
            
            # Get batch predictions
            predictions = await self.prediction_engine.predict_batch(prediction_requests)
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error getting batch ML predictions: {e}")
            # Return empty predictions for all events
            return [{'violation_probability': 0, 'confidence': 0, 'error': str(e)}] * len(events)
    
    async def get_ml_enhanced_insights(self, tenant_id: str) -> Dict[str, Any]:
        """Get ML-enhanced insights for a tenant"""
        
        try:
            # Get recent evaluations
            query = """
            MATCH (e:Evaluation {type: 'combined_ml_policy'})
            WHERE e.timestamp > datetime() - duration('P7D')
            RETURN e.result as result, e.timestamp as timestamp
            ORDER BY e.timestamp DESC
            LIMIT 100
            """
            
            with self.driver.session() as session:
                result = session.run(query)
                evaluations = []
                
                for record in result:
                    result_data = json.loads(record['result'])
                    evaluations.append({
                        'result': result_data,
                        'timestamp': record['timestamp']
                    })
            
            # Analyze ML impact
            ml_impact = self._analyze_ml_impact(evaluations)
            
            # Get top ML-predicted violations
            top_ml_violations = self._get_top_ml_violations(evaluations)
            
            return {
                'tenant_id': tenant_id,
                'ml_impact': ml_impact,
                'top_ml_violations': top_ml_violations,
                'evaluation_count': len(evaluations),
                'insights_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting ML-enhanced insights: {e}")
            return {'error': str(e)}
    
    def _analyze_ml_impact(self, evaluations: List[Dict]) -> Dict[str, Any]:
        """Analyze the impact of ML predictions"""
        
        if not evaluations:
            return {}
        
        # Calculate statistics
        total_evaluations = len(evaluations)
        ml_blocked = 0
        policy_blocked = 0
        ml_enhanced_warnings = 0
        
        for eval_data in evaluations:
            result = eval_data['result']
            action = result.get('action', 'allow')
            ml_prob = result.get('ml_prediction', {}).get('violation_probability', 0)
            policy_violations = result.get('policy_violations', [])
            
            if action == 'block':
                if ml_prob > 0.7:
                    ml_blocked += 1
                elif len(policy_violations) > 0:
                    policy_blocked += 1
            elif action == 'warn' and ml_prob > 0.5:
                ml_enhanced_warnings += 1
        
        return {
            'total_evaluations': total_evaluations,
            'ml_triggered_blocks': ml_blocked,
            'policy_triggered_blocks': policy_blocked,
            'ml_enhanced_warnings': ml_enhanced_warnings,
            'ml_block_rate': ml_blocked / total_evaluations if total_evaluations > 0 else 0,
            'policy_block_rate': policy_blocked / total_evaluations if total_evaluations > 0 else 0,
            'ml_enhancement_rate': (ml_blocked + ml_enhanced_warnings) / total_evaluations if total_evaluations > 0 else 0
        }
    
    def _get_top_ml_violations(self, evaluations: List[Dict]) -> List[Dict]:
        """Get top ML-predicted violations"""
        
        ml_violations = []
        
        for eval_data in evaluations:
            result = eval_data['result']
            ml_prediction = result.get('ml_prediction', {})
            policy_violations = result.get('policy_violations', [])
            
            if ml_prediction.get('violation_probability', 0) > 0.7:
                ml_violations.append({
                    'violation_probability': ml_prediction.get('violation_probability', 0),
                    'confidence': ml_prediction.get('confidence', 0),
                    'predicted_violations': ml_prediction.get('predicted_violations', []),
                    'policy_violations': len(policy_violations),
                    'explanation': ml_prediction.get('explanation', {}),
                    'timestamp': eval_data['timestamp']
                })
        
        # Sort by violation probability
        ml_violations.sort(key=lambda x: x['violation_probability'], reverse=True)
        
        return ml_violations[:10]  # Top 10
    
    async def update_ml_weights(self, tenant_id: str, weights: Dict[str, float]) -> Dict[str, Any]:
        """Update ML integration weights"""
        
        try:
            # Validate weights
            total_weight = sum(weights.values())
            if abs(total_weight - 1.0) > 0.01:
                raise ValueError("Weights must sum to 1.0")
            
            # Store weights in Neo4j
            query = """
            MERGE (w:MLWeights {tenant_id: $tenant_id})
            SET w.policy_weight = $policy_weight,
                w.ml_weight = $ml_weight,
                w.updated_at = datetime()
            """
            
            with self.driver.session() as session:
                session.run(query,
                    tenant_id=tenant_id,
                    policy_weight=weights.get('policy', 0.3),
                    ml_weight=weights.get('ml', 0.7)
                )
            
            return {
                'status': 'success',
                'weights': weights,
                'updated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating ML weights: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def get_ml_weights(self, tenant_id: str) -> Dict[str, Any]:
        """Get current ML integration weights"""
        
        try:
            query = """
            MATCH (w:MLWeights {tenant_id: $tenant_id})
            RETURN w.policy_weight as policy_weight,
                   w.ml_weight as ml_weight,
                   w.updated_at as updated_at
            """
            
            with self.driver.session() as session:
                result = session.run(query, tenant_id=tenant_id)
                record = result.single()
                
                if record:
                    return {
                        'policy_weight': record['policy_weight'],
                        'ml_weight': record['ml_weight'],
                        'updated_at': record['updated_at']
                    }
                else:
                    # Return default weights
                    return {
                        'policy_weight': 0.3,
                        'ml_weight': 0.7,
                        'updated_at': None
                    }
                    
        except Exception as e:
            logger.error(f"Error getting ML weights: {e}")
            return {'error': str(e)}
