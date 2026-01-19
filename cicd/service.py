import asyncio
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
import logging

from iac_adapters import IaCProcessor, IaCType, create_iac_adapter
from policy_engine.engine import PolicyEngine
from shared.models.events import CloudProvider, ResourceReference
from shared.metrics import MetricsCollector


class CIStatus(Enum):
    """CI/CD pipeline status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    BLOCKED = "blocked"
    WARNING = "warning"


class EvaluationResult:
    """Result of IaC evaluation"""
    
    def __init__(self, status: CIStatus, violations: List[Dict], 
                 prediction: Dict, resources_count: int, metadata: Dict = None):
        self.status = status
        self.violations = violations
        self.prediction = prediction
        self.resources_count = resources_count
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'status': self.status.value,
            'violations': self.violations,
            'prediction': self.prediction,
            'resources_evaluated': self.resources_count,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


class CICDService:
    """CI/CD service for IaC evaluation and policy enforcement"""
    
    def __init__(self, policy_engine: PolicyEngine, predictor=None, 
                 metrics_collector: Optional[MetricsCollector] = None):
        self.policy_engine = policy_engine
        self.predictor = predictor
        self.metrics = metrics_collector or MetricsCollector("cicd_service")
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # Initialize IaC processor
        self.iac_processor = IaCProcessor()
        
        # Cache for adapters
        self._adapter_cache = {}
    
    async def evaluate_iac(self, iac_type: str, iac_content: Union[str, Dict], 
                         context: Dict[str, Any]) -> EvaluationResult:
        """Evaluate an IaC plan and return violations and predictions."""
        start_time = datetime.utcnow()
        
        try:
            # Parse the IaC plan
            plan = await self._parse_iac_plan(iac_type, iac_content, context)
            
            # Evaluate each resource against policies
            violations = await self._evaluate_resources(plan, context)
            
            # Get ML predictions for the entire plan
            prediction = await self._get_predictions(plan, context)
            
            # Determine overall status
            status = self._determine_status(violations, prediction)
            
            # Create evaluation result
            result = EvaluationResult(
                status=status,
                violations=violations,
                prediction=prediction,
                resources_count=len(plan.resources),
                metadata={
                    'iac_type': iac_type,
                    'plan_id': plan.id,
                    'evaluation_time': (datetime.utcnow() - start_time).total_seconds(),
                    'context': context
                }
            )
            
            # Record metrics
            await self._record_metrics(result, plan)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error evaluating IaC: {e}")
            return EvaluationResult(
                status=CIStatus.FAILURE,
                violations=[],
                prediction={},
                resources_count=0,
                metadata={'error': str(e)}
            )
    
    async def evaluate_pull_request(self, pr_data: Dict, iac_changes: List[Dict]) -> Dict[str, Any]:
        """Evaluate IaC changes in a pull request"""
        results = []
        
        for change in iac_changes:
            iac_type = change.get('type', 'terraform')
            iac_content = change.get('content', {})
            
            # Context for PR evaluation
            context = {
                'principal': f"pr-author-{pr_data.get('author', 'unknown')}",
                'source_ip': 'github-action',
                'pull_request': pr_data,
                'repository': pr_data.get('repository', ''),
                'branch': pr_data.get('branch', ''),
                'commit_sha': pr_data.get('commit_sha', '')
            }
            
            result = await self.evaluate_iac(iac_type, iac_content, context)
            results.append({
                'file_path': change.get('file_path', ''),
                'result': result.to_dict()
            })
        
        # Overall PR status
        overall_status = self._determine_pr_status(results)
        
        return {
            'pull_request': pr_data,
            'overall_status': overall_status.value,
            'file_results': results,
            'summary': {
                'total_files': len(results),
                'passed': sum(1 for r in results if r['result']['status'] == 'pass'),
                'blocked': sum(1 for r in results if r['result']['status'] == 'block'),
                'warnings': sum(1 for r in results if r['result']['status'] == 'warn'),
                'failed': sum(1 for r in results if r['result']['status'] == 'failure')
            }
        }
    
    async def evaluate_deployment(self, deployment_config: Dict) -> Dict[str, Any]:
        """Evaluate a deployment configuration"""
        iac_type = deployment_config.get('iac_type', 'terraform')
        iac_content = deployment_config.get('iac_content', {})
        
        # Context for deployment evaluation
        context = {
            'principal': f"deployment-user-{deployment_config.get('user', 'unknown')}",
            'source_ip': deployment_config.get('source_ip', '0.0.0.0'),
            'deployment': {
                'environment': deployment_config.get('environment', 'unknown'),
                'pipeline': deployment_config.get('pipeline', 'unknown'),
                'stage': deployment_config.get('stage', 'unknown'),
                'deployment_id': deployment_config.get('deployment_id', '')
            }
        }
        
        result = await self.evaluate_iac(iac_type, iac_content, context)
        
        return {
            'deployment': deployment_config,
            'evaluation': result.to_dict(),
            'recommendations': await self._generate_recommendations(result, deployment_config)
        }
    
    async def _parse_iac_plan(self, iac_type: str, iac_content: Union[str, Dict], 
                              context: Dict[str, Any]) -> Any:
        """Parse IaC plan using appropriate adapter"""
        try:
            # Auto-detect IaC type if not provided
            if iac_type.lower() == 'auto':
                detected_type = IaCProcessor.auto_detect_iac_type(iac_content)
                if detected_type:
                    iac_type = detected_type.value
                else:
                    raise ValueError("Could not auto-detect IaC type")
            
            # Parse plan
            plan = self.iac_processor.process_plan(iac_content, IaCType(iac_type.lower()))
            
            self.logger.info(f"Parsed {len(plan.resources)} resources from {iac_type} plan")
            return plan
            
        except Exception as e:
            self.logger.error(f"Error parsing IaC plan: {e}")
            raise
    
    async def _evaluate_resources(self, plan, context: Dict[str, Any]) -> List[Dict]:
        """Evaluate resources against policies"""
        violations = []
        
        for resource in plan.resources:
            try:
                # Create event for resource evaluation
                event = self._create_resource_event(resource, context)
                
                # Evaluate against policies
                resource_violations = self.policy_engine.evaluate_event(event)
                violations.extend(resource_violations)
                
            except Exception as e:
                self.logger.warning(f"Error evaluating resource {resource.id}: {e}")
                violations.append({
                    'resource_id': resource.id,
                    'policy_name': 'evaluation_error',
                    'severity': 'medium',
                    'message': f"Error evaluating resource: {str(e)}",
                    'category': 'system'
                })
        
        return violations
    
    async def _get_predictions(self, plan, context: Dict[str, Any]) -> Dict:
        """Get ML predictions for the plan"""
        if not self.predictor:
            return {}
        
        try:
            # Convert plan to dict for prediction
            plan_dict = {
                'iac_type': plan.iac_type.value,
                'resources': [r.__dict__ for r in plan.resources],
                'metadata': plan.metadata
            }
            
            prediction = self.predictor.predict(plan_dict, context)
            return prediction
            
        except Exception as e:
            self.logger.warning(f"Error getting predictions: {e}")
            return {}
    
    def _determine_status(self, violations: List[Dict], prediction: Dict) -> CIStatus:
        """Determine overall CI/CD status"""
        # Check for critical violations
        if any(v.get('severity') == 'critical' for v in violations):
            return CIStatus.BLOCKED
        
        # Check for high violations
        if any(v.get('severity') == 'high' for v in violations):
            return CIStatus.WARNING
        
        # Check prediction risk
        if prediction.get('risk_level') == 'high':
            return CIStatus.WARNING
        elif prediction.get('risk_level') == 'critical':
            return CIStatus.BLOCKED
        
        return CIStatus.SUCCESS
    
    def _determine_pr_status(self, results: List[Dict]) -> CIStatus:
        """Determine overall PR status"""
        if any(r['result']['status'] == 'block' for r in results):
            return CIStatus.BLOCKED
        elif any(r['result']['status'] == 'failure' for r in results):
            return CIStatus.FAILURE
        elif any(r['result']['status'] == 'warn' for r in results):
            return CIStatus.WARNING
        else:
            return CIStatus.SUCCESS
    
    def _create_resource_event(self, resource, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create evaluation event for a resource"""
        return {
            'cloud': resource.provider.value if hasattr(resource, 'provider') else 'aws',
            'resource': {
                'type': resource.type,
                'id': resource.id,
                'name': resource.name,
                'region': resource.properties.get('region'),
                'account': resource.properties.get('account'),
                'tags': resource.properties.get('tags', {}),
                'properties': resource.properties
            },
            'operation': resource.change_type or 'Create',
            'principal': context.get('principal', 'ci-cd-system'),
            'source_ip': context.get('source_ip', '0.0.0.0'),
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': {
                'iac_type': context.get('iac_type', 'unknown'),
                'evaluation_context': context
            }
        }
    
    async def _generate_recommendations(self, result: EvaluationResult, 
                                  deployment_config: Dict) -> List[Dict]:
        """Generate recommendations based on evaluation results"""
        recommendations = []
        
        # Security recommendations
        critical_violations = [v for v in result.violations if v.get('severity') == 'critical']
        if critical_violations:
            recommendations.append({
                'type': 'security',
                'priority': 'high',
                'title': 'Critical Security Violations Found',
                'description': f"Found {len(critical_violations)} critical security violations that must be addressed before deployment.",
                'actions': [
                    'Review and fix all critical violations',
                    'Consider security review before deployment',
                    'Implement least privilege access patterns'
                ]
            })
        
        # Cost optimization recommendations
        if result.prediction.get('cost_impact', {}).get('level') == 'high':
            recommendations.append({
                'type': 'cost',
                'priority': 'medium',
                'title': 'High Cost Impact Detected',
                'description': 'The deployment may have significant cost implications.',
                'actions': [
                    'Review resource sizing',
                    'Consider cost optimization strategies',
                    'Set up cost alerts'
                ]
            })
        
        # Performance recommendations
        if result.prediction.get('performance_risk', {}).get('level') == 'high':
            recommendations.append({
                'type': 'performance',
                'priority': 'medium',
                'title': 'Performance Risk Detected',
                'description': 'The deployment may impact system performance.',
                'actions': [
                    'Conduct performance testing',
                    'Monitor resource utilization',
                    'Consider gradual rollout'
                ]
            })
        
        return recommendations
    
    async def _record_metrics(self, result: EvaluationResult, plan):
        """Record evaluation metrics"""
        try:
            # Count violations by severity
            severity_counts = {}
            for violation in result.violations:
                severity = violation.get('severity', 'unknown')
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Record metrics
            self.metrics.counter('cicd_evaluations_total').inc()
            self.metrics.counter('cicd_resources_evaluated_total').inc(len(plan.resources))
            self.metrics.counter('cicd_violations_total').inc(len(result.violations))
            
            for severity, count in severity_counts.items():
                self.metrics.counter('cicd_violations_by_severity').inc(count, labels={'severity': severity})
            
            self.metrics.histogram('cicd_evaluation_duration_seconds').observe(
                result.metadata.get('evaluation_time', 0)
            )
            
            self.metrics.gauge('cicd_last_evaluation_timestamp').set(
                result.timestamp.timestamp()
            )
            
        except Exception as e:
            self.logger.warning(f"Error recording metrics: {e}")
    
    def get_supported_iac_types(self) -> List[str]:
        """Get list of supported IaC types"""
        return [iac_type.value for iac_type in IaCType]
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for CI/CD service"""
        try:
            # Test policy engine
            test_event = {
                'cloud': 'aws',
                'resource': {'type': 'test', 'id': 'test'},
                'operation': 'test'
            }
            self.policy_engine.evaluate_event(test_event)
            
            # Test IaC processor
            test_content = {'test': 'content'}
            IaCProcessor.auto_detect_iac_type(test_content)
            
            return {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'components': {
                    'policy_engine': 'healthy',
                    'iac_processor': 'healthy',
                    'predictor': 'healthy' if self.predictor else 'disabled'
                }
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }


# Utility functions
async def create_cicd_service(policy_engine: PolicyEngine, predictor=None, 
                            metrics_collector: Optional[MetricsCollector] = None) -> CICDService:
    """Create and initialize CI/CD service"""
    service = CICDService(policy_engine, predictor, metrics_collector)
    return service
