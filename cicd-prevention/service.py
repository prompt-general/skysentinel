"""
Core CI/CD Prevention Service

This module provides the main service for evaluating IaC plans against
policies and ML predictions to prevent security issues in CI/CD pipelines.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Union

from policy_engine.engine import PolicyEngine
from prediction_engine.predictor import Predictor
from .parsers import IaCPlan, IaCResource, IaCParserFactory

# Configure logging
logger = logging.getLogger(__name__)


class EvaluationResult(Enum):
    """Evaluation result types"""
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"
    ERROR = "error"


class CICDService:
    """Core CI/CD Prevention Service"""
    
    def __init__(self, policy_engine: PolicyEngine, predictor: Predictor, neo4j_driver):
        """Initialize CI/CD service with dependencies"""
        self.policy_engine = policy_engine
        self.predictor = predictor
        self.driver = neo4j_driver
        
        # Initialize parsers factory
        self.parser_factory = IaCParserFactory()
        
        # Cache for evaluation results
        self._evaluation_cache = {}
        
        logger.info("CI/CD Prevention Service initialized")
    
    async def evaluate_plan(self, 
                          iac_type: str, 
                          iac_content: Union[str, Dict],
                          context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate an IaC plan against policies and predictions
        Returns: Evaluation result with violations and recommendations
        """
        try:
            logger.info(f"Starting evaluation for IaC type: {iac_type}")
            
            # Step 1: Parse IaC content
            parser = self.parser_factory.create_parser(iac_type)
            if not parser:
                return self._error_result(f"Unsupported IaC type: {iac_type}")
            
            plan = parser.parse(iac_content)
            logger.info(f"Parsed {len(plan.resources)} resources from {iac_type} plan")
            
            # Step 2: Store IaC resources in graph
            await self._store_iac_resources(plan, context)
            
            # Step 3: Evaluate policies against each resource
            policy_violations = await self._evaluate_iac_resources(plan, context)
            logger.info(f"Found {len(policy_violations)} policy violations")
            
            # Step 4: Get ML predictions
            ml_predictions = await self._get_predictions(plan, context)
            logger.info(f"ML predictions: {ml_predictions}")
            
            # Step 5: Determine overall result
            result, reasons = self._determine_result(policy_violations, ml_predictions)
            logger.info(f"Evaluation result: {result.value} - {reasons}")
            
            # Step 6: Generate report
            report = self._generate_report(
                plan=plan,
                policy_violations=policy_violations,
                ml_predictions=ml_predictions,
                result=result,
                context=context,
                reasons=reasons
            )
            
            # Step 7: Store evaluation result
            await self._store_evaluation_result(report, context)
            
            logger.info(f"Evaluation completed: {report['evaluation_id']}")
            return report
            
        except Exception as e:
            logger.error(f"Error evaluating IaC plan: {e}", exc_info=True)
            return self._error_result(str(e))
    
    async def evaluate_pr(self,
                        iac_files: List[Dict[str, Any]],
                        context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate multiple IaC files in a pull request
        """
        try:
            logger.info(f"Starting PR evaluation for {len(iac_files)} files")
            
            all_reports = []
            all_violations = []
            total_resources = 0
            
            # Evaluate each file
            for file_info in iac_files:
                file_path = file_info.get('path', '')
                iac_type = file_info.get('type', '')
                iac_content = file_info.get('content', '')
                
                if not iac_type or not iac_content:
                    continue
                
                # Add file context
                file_context = {
                    **context,
                    'file_path': file_path,
                    'pr_evaluation': True
                }
                
                file_report = await self.evaluate_plan(iac_type, iac_content, file_context)
                all_reports.append(file_report)
                
                # Aggregate violations
                all_violations.extend(file_report.get('policy_evaluation', {}).get('violations_by_severity', {}).get('critical', []))
                all_violations.extend(file_report.get('policy_evaluation', {}).get('violations_by_severity', {}).get('high', []))
                
                total_resources += file_report.get('plan_summary', {}).get('total_resources', 0)
            
            # Generate PR summary
            pr_report = self._generate_pr_summary(all_reports, all_violations, total_resources, context)
            
            logger.info(f"PR evaluation completed: {pr_report['pr_id']}")
            return pr_report
            
        except Exception as e:
            logger.error(f"Error evaluating PR: {e}", exc_info=True)
            return self._error_result(f"PR evaluation failed: {str(e)}")
    
    async def _store_iac_resources(self, plan: IaCPlan, context: Dict):
        """Store IaC resources in Neo4j graph"""
        query = """
        MERGE (p:IaCPlan {id: $plan_id})
        SET p += $plan_props,
            p.created_at = datetime(),
            p.context = $context
        
        WITH p
        UNWIND $resources as resource
        MERGE (r:IaCResource {id: resource.iac_id})
        SET r += resource.properties,
            r.type = resource.resource_type,
            r.cloud = resource.cloud_provider,
            r.tags = resource.tags,
            r.change_type = resource.change_type,
            r.valid_from = datetime(),
            r.metadata = resource.metadata
        
        MERGE (p)-[:CONTAINS]->(r)
        
        // Link to existing resources if possible
        WITH r
        MATCH (existing:Resource {cloud: r.cloud})
        WHERE existing.type = r.type
        AND (
            existing.name = r.name OR
            (r.properties.arn IS NOT NULL AND existing.arn = r.properties.arn)
        )
        MERGE (r)-[:WILL_AFFECT]->(existing)
        """
        
        resources_data = []
        for resource in plan.resources:
            resource_data = {
                "iac_id": resource.iac_id,
                "resource_type": resource.resource_type,
                "cloud_provider": resource.cloud_provider.value if hasattr(resource.cloud_provider, 'value') else str(resource.cloud_provider),
                "properties": resource.properties,
                "tags": resource.tags,
                "change_type": resource.change_type.value if hasattr(resource.change_type, 'value') else str(resource.change_type),
                "name": resource.metadata.get('name', ''),
                "metadata": resource.metadata
            }
            resources_data.append(resource_data)
        
        plan_props = {
            "source_type": plan.source_type,
            "resource_count": len(plan.resources),
            "timestamp": plan.timestamp,
            "metadata": plan.metadata
        }
        
        try:
            with self.driver.session() as session:
                session.run(query,
                    plan_id=plan.id,
                    plan_props=plan_props,
                    resources=resources_data,
                    context=context
                )
            logger.info(f"Stored {len(resources_data)} IaC resources in graph")
        except Exception as e:
            logger.error(f"Failed to store IaC resources: {e}")
            raise
    
    async def _evaluate_iac_resources(self, plan: IaCPlan, context: Dict) -> List[Dict]:
        """Evaluate IaC resources against policies"""
        violations = []
        
        for resource in plan.resources:
            # Skip no-change resources
            if resource.change_type.value == "no-change":
                continue
            
            # Create evaluation event
            event = {
                "cloud": resource.cloud_provider.value if hasattr(resource.cloud_provider, 'value') else str(resource.cloud_provider),
                "resource": {
                    "id": f"iac:{resource.iac_id}",
                    "type": resource.resource_type,
                    "properties": resource.properties,
                    "tags": resource.tags,
                    "change_type": resource.change_type.value if hasattr(resource.change_type, 'value') else str(resource.change_type)
                },
                "operation": f"{resource.change_type.value if hasattr(resource.change_type, 'value') else str(resource.change_type)}_resource",
                "principal": context.get('principal', 'ci-cd-system'),
                "source_ip": context.get('source_ip', '0.0.0.0'),
                "timestamp": datetime.utcnow().isoformat(),
                "context": {
                    "iac_plan": plan.id,
                    "source_type": plan.source_type,
                    "stage": "pre_deployment",
                    "file_path": context.get('file_path', '')
                }
            }
            
            try:
                # Evaluate against policies
                resource_violations = self.policy_engine.evaluate_event(event)
                
                # Add resource context to violations
                for violation in resource_violations:
                    violation['iac_context'] = {
                        'resource_id': resource.iac_id,
                        'change_type': resource.change_type.value if hasattr(resource.change_type, 'value') else str(resource.change_type),
                        'plan_id': plan.id,
                        'resource_type': resource.resource_type,
                        'cloud_provider': resource.cloud_provider.value if hasattr(resource.cloud_provider, 'value') else str(resource.cloud_provider)
                    }
                    violations.append(violation)
                    
            except Exception as e:
                logger.error(f"Error evaluating resource {resource.iac_id}: {e}")
                # Add error as violation
                violations.append({
                    'id': f"eval-error-{hashlib.md5(resource.iac_id.encode()).hexdigest()[:8]}",
                    'severity': 'error',
                    'policy_name': 'evaluation_error',
                    'description': f"Failed to evaluate resource: {str(e)}",
                    'iac_context': {
                        'resource_id': resource.iac_id,
                        'change_type': resource.change_type.value if hasattr(resource.change_type, 'value') else str(resource.change_type),
                        'plan_id': plan.id
                    }
                })
        
        return violations
    
    async def _get_predictions(self, plan: IaCPlan, context: Dict) -> Dict[str, Any]:
        """Get ML predictions for the IaC plan"""
        try:
            # Prepare features for prediction
            features = self._prepare_prediction_features(plan, context)
            
            # Get predictions from ML engine
            predictions = await self.predictor.predict_iac(features)
            
            return predictions
            
        except Exception as e:
            logger.error(f"Failed to get predictions: {e}")
            return {
                "violation_probability": 0.0,
                "confidence": 0.0,
                "high_risk_resources": [],
                "warnings": [],
                "error": str(e)
            }
    
    def _prepare_prediction_features(self, plan: IaCPlan, context: Dict) -> Dict:
        """Prepare features for ML prediction"""
        features = {
            "plan_id": plan.id,
            "source_type": plan.source_type,
            "resource_count": len(plan.resources),
            "resource_types": list(set(r.resource_type for r in plan.resources)),
            "change_types": {
                "create": sum(1 for r in plan.resources if r.change_type.value == "create"),
                "update": sum(1 for r in plan.resources if r.change_type.value == "update"),
                "delete": sum(1 for r in plan.resources if r.change_type.value == "delete"),
                "no_change": sum(1 for r in plan.resources if r.change_type.value == "no-change")
            },
            "cloud_providers": list(set(r.cloud_provider.value if hasattr(r.cloud_provider, 'value') else str(r.cloud_provider) for r in plan.resources)),
            "context": context
        }
        
        # Add resource-specific features
        resource_features = []
        for resource in plan.resources:
            resource_feature = {
                "type": resource.resource_type,
                "change_type": resource.change_type.value if hasattr(resource.change_type, 'value') else str(resource.change_type),
                "has_sensitive_tags": self._has_sensitive_tags(resource.tags),
                "properties_count": len(resource.properties),
                "is_public": self._is_public_resource(resource),
                "tags_count": len(resource.tags),
                "metadata_count": len(resource.metadata)
            }
            resource_features.append(resource_feature)
        
        features["resources"] = resource_features
        return features
    
    def _determine_result(self, 
                         policy_violations: List[Dict], 
                         ml_predictions: Dict) -> Tuple[EvaluationResult, List[str]]:
        """Determine overall evaluation result"""
        reasons = []
        
        # Check for critical policy violations
        critical_violations = [
            v for v in policy_violations 
            if v.get('severity') == 'critical'
        ]
        
        if critical_violations:
            reasons.append(f"{len(critical_violations)} critical policy violations")
            return EvaluationResult.BLOCK, reasons
        
        # Check for high severity violations
        high_violations = [
            v for v in policy_violations 
            if v.get('severity') == 'high'
        ]
        
        if high_violations:
            reasons.append(f"{len(high_violations)} high severity policy violations")
            return EvaluationResult.BLOCK, reasons
        
        # Check ML predictions
        violation_prob = ml_predictions.get('violation_probability', 0.0)
        confidence = ml_predictions.get('confidence', 0.0)
        
        if violation_prob > 0.8 and confidence > 0.7:
            reasons.append(f"High predicted violation probability: {violation_prob:.2f}")
            return EvaluationResult.BLOCK, reasons
        elif violation_prob > 0.6:
            reasons.append(f"Moderate predicted violation probability: {violation_prob:.2f}")
            return EvaluationResult.WARN, reasons
        
        # Check for medium severity violations
        medium_violations = [
            v for v in policy_violations 
            if v.get('severity') == 'medium'
        ]
        
        if medium_violations:
            reasons.append(f"{len(medium_violations)} medium severity policy violations")
            return EvaluationResult.WARN, reasons
        
        # Check for low severity violations
        low_violations = [
            v for v in policy_violations 
            if v.get('severity') == 'low'
        ]
        
        if low_violations:
            reasons.append(f"{len(low_violations)} low severity policy violations")
        
        return EvaluationResult.PASS, reasons or ["No violations detected"]
    
    def _generate_report(self, 
                        plan: IaCPlan,
                        policy_violations: List[Dict],
                        ml_predictions: Dict,
                        result: EvaluationResult,
                        context: Dict,
                        reasons: List[str]) -> Dict[str, Any]:
        """Generate comprehensive evaluation report"""
        
        # Group violations by severity
        violations_by_severity = {}
        for violation in policy_violations:
            severity = violation.get('severity', 'unknown')
            if severity not in violations_by_severity:
                violations_by_severity[severity] = []
            violations_by_severity[severity].append(violation)
        
        # Calculate statistics
        total_resources = len(plan.resources)
        resources_with_violations = len(set(
            v['iac_context']['resource_id'] for v in policy_violations
        ))
        
        return {
            "evaluation_id": f"eval-{hashlib.md5(json.dumps(plan.dict()).encode()).hexdigest()[:8]}",
            "timestamp": datetime.utcnow().isoformat(),
            "result": result.value,
            "reasons": reasons,
            "plan_summary": {
                "id": plan.id,
                "source_type": plan.source_type,
                "total_resources": total_resources,
                "resources_by_change_type": {
                    "create": sum(1 for r in plan.resources if r.change_type.value == "create"),
                    "update": sum(1 for r in plan.resources if r.change_type.value == "update"),
                    "delete": sum(1 for r in plan.resources if r.change_type.value == "delete"),
                    "no_change": sum(1 for r in plan.resources if r.change_type.value == "no-change")
                },
                "cloud_providers": list(set(r.cloud_provider.value if hasattr(r.cloud_provider, 'value') else str(r.cloud_provider) for r in plan.resources))
            },
            "policy_evaluation": {
                "total_violations": len(policy_violations),
                "violations_by_severity": violations_by_severity,
                "resources_with_violations": resources_with_violations,
                "violation_rate": (resources_with_violations / total_resources) if total_resources > 0 else 0
            },
            "ml_predictions": ml_predictions,
            "recommendations": self._generate_recommendations(policy_violations, ml_predictions),
            "context": context,
            "next_steps": self._get_next_steps(result)
        }
    
    def _generate_pr_summary(self, 
                           all_reports: List[Dict],
                           all_violations: List[Dict],
                           total_resources: int,
                           context: Dict) -> Dict[str, Any]:
        """Generate PR evaluation summary"""
        
        # Determine overall result
        has_critical = any(r.get('result') == 'block' for r in all_reports)
        has_warnings = any(r.get('result') == 'warn' for r in all_reports)
        
        if has_critical:
            overall_result = EvaluationResult.BLOCK
        elif has_warnings:
            overall_result = EvaluationResult.WARN
        else:
            overall_result = EvaluationResult.PASS
        
        # Aggregate violations
        all_violations_by_severity = {}
        for report in all_reports:
            report_violations = report.get('policy_evaluation', {}).get('violations_by_severity', {})
            for severity, violations in report_violations.items():
                if severity not in all_violations_by_severity:
                    all_violations_by_severity[severity] = []
                all_violations_by_severity[severity].extend(violations)
        
        return {
            "pr_id": context.get('pr_id', 'unknown'),
            "evaluation_id": f"pr-eval-{hashlib.md5(json.dumps(context).encode()).hexdigest()[:8]}",
            "timestamp": datetime.utcnow().isoformat(),
            "result": overall_result.value,
            "files_evaluated": len(all_reports),
            "total_resources": total_resources,
            "summary": {
                "total_violations": len(all_violations),
                "violations_by_severity": all_violations_by_severity,
                "files_with_issues": len([r for r in all_reports if r.get('policy_evaluation', {}).get('total_violations', 0) > 0])
            },
            "file_reports": all_reports,
            "recommendations": self._generate_pr_recommendations(all_reports, overall_result),
            "context": context,
            "next_steps": self._get_next_steps(overall_result)
        }
    
    def _generate_recommendations(self, 
                                 violations: List[Dict], 
                                 predictions: Dict) -> List[Dict]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Recommendations from policy violations
        for violation in violations[:10]:  # Limit to top 10
            recommendation = {
                "type": "policy_violation",
                "severity": violation.get('severity'),
                "resource": violation.get('iac_context', {}).get('resource_id'),
                "message": violation.get('description', 'Policy violation detected'),
                "remediation": violation.get('remediation_actions', []),
                "policy": violation.get('policy_name'),
                "rule_id": violation.get('rule_id')
            }
            recommendations.append(recommendation)
        
        # Recommendations from ML predictions
        high_risk_resources = predictions.get('high_risk_resources', [])
        for resource in high_risk_resources[:5]:  # Limit to top 5
            recommendation = {
                "type": "ml_prediction",
                "severity": "warning",
                "resource": resource.get('resource_id'),
                "message": f"High risk of violation predicted ({resource.get('probability', 0):.2%})",
                "remediation": ["Review resource configuration", "Check similar historical violations"],
                "confidence": predictions.get('confidence', 0)
            }
            recommendations.append(recommendation)
        
        # General recommendations
        if predictions.get('violation_probability', 0) > 0.5:
            recommendations.append({
                "type": "general",
                "severity": "info",
                "message": "Consider adding more specific security policies",
                "remediation": ["Review security policy coverage", "Add missing security rules"]
            })
        
        return recommendations
    
    def _generate_pr_recommendations(self, 
                                  reports: List[Dict], 
                                  result: EvaluationResult) -> List[Dict]:
        """Generate PR-specific recommendations"""
        recommendations = []
        
        # Aggregate recommendations from all reports
        all_recommendations = []
        for report in reports:
            all_recommendations.extend(report.get('recommendations', []))
        
        # Remove duplicates and prioritize
        seen = set()
        unique_recommendations = []
        
        for rec in all_recommendations:
            key = (rec.get('type'), rec.get('message'))
            if key not in seen:
                seen.add(key)
                unique_recommendations.append(rec)
        
        # Sort by severity
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'warning': 4, 'info': 5}
        unique_recommendations.sort(key=lambda x: severity_order.get(x.get('severity', 'info'), 5))
        
        return unique_recommendations[:20]  # Limit to top 20
    
    def _get_next_steps(self, result: EvaluationResult) -> List[str]:
        """Get next steps based on evaluation result"""
        if result == EvaluationResult.BLOCK:
            return [
                "Fix policy violations before proceeding",
                "Review ML predictions and high-risk resources",
                "Update IaC configuration to comply with policies",
                "Request exception if needed (contact security team)",
                "Re-run evaluation after making changes"
            ]
        elif result == EvaluationResult.WARN:
            return [
                "Review warnings and recommendations",
                "Consider fixing violations before production deployment",
                "Document any accepted risks",
                "Proceed with caution",
                "Monitor runtime for any policy violations"
            ]
        else:
            return [
                "Proceed with deployment",
                "Monitor runtime for any policy violations",
                "Review ML predictions for improvement opportunities",
                "Consider implementing additional security policies"
            ]
    
    async def _store_evaluation_result(self, report: Dict, context: Dict):
        """Store evaluation result in Neo4j"""
        query = """
        MERGE (e:Evaluation {id: $evaluation_id})
        SET e += $report,
            e.context = $context,
            e.created_at = datetime()
        
        WITH e
        MATCH (p:IaCPlan {id: $plan_id})
        MERGE (p)-[:EVALUATED_BY]->(e)
        
        // Link violations
        UNWIND $violations as violation
        MERGE (v:Violation {id: violation.id})
        SET v += violation
        
        MERGE (e)-[:DETECTED]->(v)
        """
        
        try:
            # Extract violations for storage
            all_violations = []
            violations_by_severity = report.get('policy_evaluation', {}).get('violations_by_severity', {})
            for severity, violations in violations_by_severity.items():
                all_violations.extend(violations)
            
            with self.driver.session() as session:
                session.run(query,
                    evaluation_id=report['evaluation_id'],
                    report=report,
                    context=context,
                    plan_id=report.get('plan_summary', {}).get('id', ''),
                    violations=all_violations
                )
            logger.info(f"Stored evaluation result: {report['evaluation_id']}")
        except Exception as e:
            logger.error(f"Failed to store evaluation result: {e}")
    
    def _error_result(self, error_message: str) -> Dict[str, Any]:
        """Generate error result"""
        return {
            "evaluation_id": f"error-{hashlib.md5(error_message.encode()).hexdigest()[:8]}",
            "timestamp": datetime.utcnow().isoformat(),
            "result": EvaluationResult.ERROR.value,
            "error": error_message,
            "reasons": [f"Evaluation error: {error_message}"],
            "plan_summary": {},
            "policy_evaluation": {
                "total_violations": 0,
                "violations_by_severity": {},
                "resources_with_violations": 0,
                "violation_rate": 0
            },
            "ml_predictions": {},
            "recommendations": [],
            "context": {},
            "next_steps": ["Fix parsing error and resubmit"]
        }
    
    # Helper methods
    @staticmethod
    def _has_sensitive_tags(tags: Dict[str, str]) -> bool:
        """Check if resource has sensitive tags"""
        sensitive_patterns = ['pii', 'confidential', 'secret', 'password', 'key', 'token', 'credential']
        for tag_value in tags.values():
            if isinstance(tag_value, str) and any(pattern in tag_value.lower() for pattern in sensitive_patterns):
                return True
        return False
    
    @staticmethod
    def _is_public_resource(resource: IaCResource) -> bool:
        """Check if resource is configured for public access"""
        properties = resource.properties
        
        if 'aws:s3:bucket' in resource.resource_type:
            acl = properties.get('acl', 'private')
            policy = properties.get('policy', '')
            public_read = properties.get('public_read', False)
            public_write = properties.get('public_write', False)
            
            return (acl == 'public-read' or 
                   acl == 'public-read-write' or 
                   'PublicAccess' in str(policy) or
                   public_read or
                   public_write)
        
        elif 'aws:ec2:security-group' in resource.resource_type:
            rules = properties.get('ingress', [])
            for rule in rules:
                cidr_blocks = rule.get('cidr_blocks', [])
                if '0.0.0.0/0' in cidr_blocks:
                    return True
        
        elif 'azure:storage:storageaccount' in resource.resource_type:
            # Check for public blob access
            network_rules = properties.get('networkAcls', {}).get('bypass', [])
            allow_public_access = properties.get('allowBlobPublicAccess', False)
            
            return allow_public_access or 'AzureServices' in network_rules
        
        return False
    
    async def get_evaluation_history(self, 
                                 limit: int = 100,
                                 context_filter: Optional[Dict] = None) -> List[Dict]:
        """Get evaluation history"""
        query = """
        MATCH (e:Evaluation)
        WHERE $context_filter IS NULL OR e.context CONTAINS $context_filter
        RETURN e
        ORDER BY e.created_at DESC
        LIMIT $limit
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query,
                    context_filter=context_filter,
                    limit=limit)
                return [record['e'] for record in result]
        except Exception as e:
            logger.error(f"Failed to get evaluation history: {e}")
            return []
    
    async def get_evaluation_by_id(self, evaluation_id: str) -> Optional[Dict]:
        """Get specific evaluation by ID"""
        query = """
        MATCH (e:Evaluation {id: $evaluation_id})
        OPTIONAL MATCH (e)-[:DETECTED]->(v:Violation)
        RETURN e, collect(v) as violations
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, evaluation_id=evaluation_id)
                records = list(result)
                if records:
                    return records[0]['e']
                return None
        except Exception as e:
            logger.error(f"Failed to get evaluation {evaluation_id}: {e}")
            return None
