import schedule
import time
import threading
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor
import json

from neo4j import GraphDatabase
from shared.metrics import get_metrics, MetricsTimer

logger = logging.getLogger(__name__)


class EvaluationType(str, Enum):
    """Types of scheduled evaluations"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class EvaluationStatus(str, Enum):
    """Evaluation status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class EvaluationResult:
    """Result of scheduled evaluation"""
    evaluation_id: str
    evaluation_type: EvaluationType
    status: EvaluationStatus
    start_time: datetime
    end_time: Optional[datetime]
    resources_evaluated: int
    violations_found: int
    error: Optional[str] = None
    details: Optional[Dict] = None


class ScheduledEvaluator:
    """Scheduled evaluation service for drift detection and compliance monitoring"""
    
    def __init__(self, 
                 policy_engine, 
                 neo4j_driver,
                 max_workers: int = 5,
                 batch_size: int = 1000):
        self.policy_engine = policy_engine
        self.driver = neo4j_driver
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # State management
        self.running = False
        self.scheduler_thread = None
        self.current_evaluations = {}
        self.evaluation_history = []
        
        # Metrics
        self.metrics = get_metrics()
        
        # Evaluation callbacks
        self.evaluation_callbacks = {
            'started': [],
            'completed': [],
            'failed': []
        }
        
        # Schedule configuration
        self.schedule_config = {
            'hourly_evaluation': True,
            'daily_drift_check': True,
            'weekly_compliance': True,
            'monthly_report': True
        }
    
    def start(self):
        """Start scheduled evaluation service"""
        if self.running:
            logger.warning("Scheduled evaluator is already running")
            return
        
        self.running = True
        
        # Configure schedule
        self._configure_schedule()
        
        # Start scheduler in background thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        logger.info("Scheduled evaluator started")
    
    def stop(self):
        """Stop scheduled evaluation service"""
        self.running = False
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        self.executor.shutdown(wait=True)
        logger.info("Scheduled evaluator stopped")
    
    def _configure_schedule(self):
        """Configure evaluation schedules"""
        # Clear existing schedule
        schedule.clear()
        
        if self.schedule_config['hourly_evaluation']:
            schedule.every().hour.do(self._run_hourly_evaluation)
        
        if self.schedule_config['daily_drift_check']:
            schedule.every().day.at("02:00").do(self._run_drift_detection)
        
        if self.schedule_config['weekly_compliance']:
            schedule.every().sunday.at("03:00").do(self._run_compliance_evaluation)
        
        if self.schedule_config['monthly_report']:
            schedule.every().month.do(self._run_monthly_report)
        
        logger.info("Schedule configured")
    
    def _run_scheduler(self):
        """Run scheduler in background thread"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                time.sleep(60)
    
    def _run_hourly_evaluation(self):
        """Run hourly evaluation of all resources"""
        evaluation_id = f"hourly-{int(datetime.utcnow().timestamp())}"
        
        try:
            result = self._evaluate_all_resources(
                evaluation_id, 
                EvaluationType.HOURLY
            )
            self._handle_evaluation_completion(result)
            
        except Exception as e:
            logger.error(f"Error in hourly evaluation: {e}")
            self._handle_evaluation_failure(evaluation_id, EvaluationType.HOURLY, str(e))
    
    def _run_drift_detection(self):
        """Run daily drift detection"""
        evaluation_id = f"drift-{int(datetime.utcnow().timestamp())}"
        
        try:
            result = self._evaluate_drift(evaluation_id)
            self._handle_evaluation_completion(result)
            
        except Exception as e:
            logger.error(f"Error in drift detection: {e}")
            self._handle_evaluation_failure(evaluation_id, EvaluationType.DAILY, str(e))
    
    def _run_compliance_evaluation(self):
        """Run weekly compliance evaluation"""
        evaluation_id = f"compliance-{int(datetime.utcnow().timestamp())}"
        
        try:
            result = self._evaluate_compliance(evaluation_id)
            self._handle_evaluation_completion(result)
            
        except Exception as e:
            logger.error(f"Error in compliance evaluation: {e}")
            self._handle_evaluation_failure(evaluation_id, EvaluationType.WEEKLY, str(e))
    
    def _run_monthly_report(self):
        """Run monthly comprehensive report"""
        evaluation_id = f"monthly-{int(datetime.utcnow().timestamp())}"
        
        try:
            result = self._generate_monthly_report(evaluation_id)
            self._handle_evaluation_completion(result)
            
        except Exception as e:
            logger.error(f"Error in monthly report: {e}")
            self._handle_evaluation_failure(evaluation_id, EvaluationType.MONTHLY, str(e))
    
    def _evaluate_all_resources(self, evaluation_id: str, eval_type: EvaluationType) -> EvaluationResult:
        """Evaluate all resources against all policies"""
        start_time = datetime.utcnow()
        
        # Create evaluation result
        result = EvaluationResult(
            evaluation_id=evaluation_id,
            evaluation_type=eval_type,
            status=EvaluationStatus.RUNNING,
            start_time=start_time,
            end_time=None,
            resources_evaluated=0,
            violations_found=0
        )
        
        self.current_evaluations[evaluation_id] = result
        self._notify_callbacks('started', result)
        
        logger.info(f"Starting {eval_type.value} evaluation: {evaluation_id}")
        
        try:
            with MetricsTimer(self.metrics.graph_query_duration):
                with self.driver.session() as session:
                    # Get all active resources in batches
                    query = """
                    MATCH (r:Resource)
                    WHERE r.valid_to IS NULL 
                    AND r.state IN ['ACTIVE', 'RUNNING']
                    RETURN r.id as id, r as properties
                    ORDER BY r.last_modified DESC
                    LIMIT $batch_size
                    """
                    
                    total_violations = []
                    total_resources = 0
                    offset = 0
                    
                    while True:
                        batch_result = session.run(query, batch_size=self.batch_size, offset=offset)
                        batch_resources = list(batch_result)
                        
                        if not batch_resources:
                            break
                        
                        # Process batch
                        batch_violations = self._process_resource_batch(
                            [record["properties"] for record in batch_resources]
                        )
                        
                        total_violations.extend(batch_violations)
                        total_resources += len(batch_resources)
                        offset += self.batch_size
                        
                        logger.debug(f"Processed batch of {len(batch_resources)} resources")
                        
                        # Prevent overwhelming the system
                        time.sleep(0.1)
            
            # Update result
            result.status = EvaluationStatus.COMPLETED
            result.end_time = datetime.utcnow()
            result.resources_evaluated = total_resources
            result.violations_found = len(total_violations)
            result.details = {
                'violations_by_severity': self._group_violations_by_severity(total_violations),
                'processing_time': (result.end_time - start_time).total_seconds()
            }
            
            # Store evaluation results
            self._store_evaluation_results(result, total_violations)
            
            logger.info(f"Completed {eval_type.value} evaluation: {total_resources} resources, {len(total_violations)} violations")
            
            return result
            
        except Exception as e:
            result.status = EvaluationStatus.FAILED
            result.end_time = datetime.utcnow()
            result.error = str(e)
            raise
    
    def _evaluate_drift(self, evaluation_id: str) -> EvaluationResult:
        """Detect configuration drift"""
        start_time = datetime.utcnow()
        
        result = EvaluationResult(
            evaluation_id=evaluation_id,
            evaluation_type=EvaluationType.DAILY,
            status=EvaluationStatus.RUNNING,
            start_time=start_time,
            end_time=None,
            resources_evaluated=0,
            violations_found=0
        )
        
        self.current_evaluations[evaluation_id] = result
        self._notify_callbacks('started', result)
        
        logger.info(f"Starting drift detection: {evaluation_id}")
        
        try:
            with self.driver.session() as session:
                # Find resources that have changed since last evaluation
                query = """
                MATCH (r:Resource)
                WHERE r.valid_to IS NULL
                AND r.last_modified > datetime() - duration('P1D')
                RETURN r.id as id, r as properties
                ORDER BY r.last_modified DESC
                """
                
                result_set = session.run(query)
                drifted_resources = [record["properties"] for record in result_set]
                
                # Check if drifted resources violate any policies
                violations = []
                for resource in drifted_resources:
                    resource_event = {
                        "resource": resource,
                        "cloud": resource.get("cloud"),
                        "operation": "drift_detection",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    resource_violations = self.policy_engine.evaluate_event(resource_event)
                    violations.extend(resource_violations)
                
                # Tag drifted resources
                self._tag_drifted_resources(drifted_resources)
                
                # Update result
                result.status = EvaluationStatus.COMPLETED
                result.end_time = datetime.utcnow()
                result.resources_evaluated = len(drifted_resources)
                result.violations_found = len(violations)
                result.details = {
                    'drifted_resources': len(drifted_resources),
                    'violations_by_severity': self._group_violations_by_severity(violations),
                    'drift_types': self._analyze_drift_types(drifted_resources)
                }
                
                # Store results
                self._store_evaluation_results(result, violations)
                
                logger.info(f"Drift detection complete: {len(drifted_resources)} drifted resources, {len(violations)} violations")
                
                return result
                
        except Exception as e:
            result.status = EvaluationStatus.FAILED
            result.end_time = datetime.utcnow()
            result.error = str(e)
            raise
    
    def _evaluate_compliance(self, evaluation_id: str) -> EvaluationResult:
        """Weekly compliance evaluation"""
        start_time = datetime.utcnow()
        
        result = EvaluationResult(
            evaluation_id=evaluation_id,
            evaluation_type=EvaluationType.WEEKLY,
            status=EvaluationStatus.RUNNING,
            start_time=start_time,
            end_time=None,
            resources_evaluated=0,
            violations_found=0
        )
        
        self.current_evaluations[evaluation_id] = result
        self._notify_callbacks('started', result)
        
        logger.info(f"Starting compliance evaluation: {evaluation_id}")
        
        try:
            # Get all policies
            policies = list(self.policy_engine.policies.values())
            active_policies = [p for p in policies if p.enabled and not p.is_expired()]
            
            compliance_report = {
                "timestamp": datetime.utcnow().isoformat(),
                "policies_evaluated": len(active_policies),
                "compliance_by_policy": {},
                "compliance_by_severity": {},
                "overall_compliance": 0.0,
                "total_resources": 0,
                "compliant_resources": 0
            }
            
            total_resources = 0
            compliant_resources = 0
            
            for policy in active_policies:
                # Count resources matching policy
                resource_count = self._count_resources_for_policy(policy)
                total_resources += resource_count
                
                # Count compliant resources
                compliant_count = self._count_compliant_resources(policy)
                compliant_resources += compliant_count
                
                policy_compliance = (compliant_count / resource_count * 100) if resource_count > 0 else 100
                
                compliance_report["compliance_by_policy"][policy.name] = {
                    "total_resources": resource_count,
                    "compliant_resources": compliant_count,
                    "compliance_percentage": round(policy_compliance, 2),
                    "policy_severity": policy.severity
                }
                
                # Track by severity
                severity = policy.severity
                if severity not in compliance_report["compliance_by_severity"]:
                    compliance_report["compliance_by_severity"][severity] = {
                        "total_resources": 0,
                        "compliant_resources": 0
                    }
                
                compliance_report["compliance_by_severity"][severity]["total_resources"] += resource_count
                compliance_report["compliance_by_severity"][severity]["compliant_resources"] += compliant_count
            
            if total_resources > 0:
                compliance_report["overall_compliance"] = round((compliant_resources / total_resources) * 100, 2)
            
            compliance_report["total_resources"] = total_resources
            compliance_report["compliant_resources"] = compliant_resources
            
            # Update result
            result.status = EvaluationStatus.COMPLETED
            result.end_time = datetime.utcnow()
            result.resources_evaluated = total_resources
            result.violations_found = total_resources - compliant_resources
            result.details = compliance_report
            
            # Store compliance report
            self._store_compliance_report(compliance_report)
            
            logger.info(f"Compliance evaluation complete: {compliance_report['overall_compliance']}% overall compliance")
            
            return result
            
        except Exception as e:
            result.status = EvaluationStatus.FAILED
            result.end_time = datetime.utcnow()
            result.error = str(e)
            raise
    
    def _generate_monthly_report(self, evaluation_id: str) -> EvaluationResult:
        """Generate monthly comprehensive report"""
        start_time = datetime.utcnow()
        
        result = EvaluationResult(
            evaluation_id=evaluation_id,
            evaluation_type=EvaluationType.MONTHLY,
            status=EvaluationStatus.RUNNING,
            start_time=start_time,
            end_time=None,
            resources_evaluated=0,
            violations_found=0
        )
        
        self.current_evaluations[evaluation_id] = result
        self._notify_callbacks('started', result)
        
        try:
            # Generate comprehensive monthly report
            monthly_report = {
                "report_period": {
                    "start": (start_time - timedelta(days=30)).isoformat(),
                    "end": start_time.isoformat()
                },
                "summary": self._generate_monthly_summary(),
                "trends": self._analyze_trends(),
                "top_violations": self._get_top_violations(),
                "recommendations": self._generate_recommendations()
            }
            
            # Update result
            result.status = EvaluationStatus.COMPLETED
            result.end_time = datetime.utcnow()
            result.details = monthly_report
            
            # Store monthly report
            self._store_monthly_report(monthly_report)
            
            logger.info(f"Monthly report generated: {evaluation_id}")
            
            return result
            
        except Exception as e:
            result.status = EvaluationStatus.FAILED
            result.end_time = datetime.utcnow()
            result.error = str(e)
            raise
    
    def _process_resource_batch(self, resources: List[Dict]) -> List[Dict]:
        """Process a batch of resources for evaluation"""
        violations = []
        
        for resource in resources:
            try:
                resource_event = {
                    "resource": resource,
                    "cloud": resource.get("cloud"),
                    "operation": "scheduled_evaluation",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                resource_violations = self.policy_engine.evaluate_event(resource_event)
                violations.extend(resource_violations)
                
            except Exception as e:
                logger.error(f"Error evaluating resource {resource.get('id')}: {e}")
        
        return violations
    
    def _count_resources_for_policy(self, policy) -> int:
        """Count resources that match policy selector"""
        try:
            with self.driver.session() as session:
                conditions = []
                
                if policy.resources.cloud and policy.resources.cloud != 'all':
                    conditions.append(f"r.cloud = '{policy.resources.cloud}'")
                
                if policy.resources.resource_types:
                    type_conditions = []
                    for rtype in policy.resources.resource_types:
                        if '*' in rtype:
                            pattern = rtype.replace('*', '.*')
                            type_conditions.append(f"r.type =~ '{pattern}'")
                        else:
                            type_conditions.append(f"r.type = '{rtype}'")
                    
                    if type_conditions:
                        conditions.append(f"({' OR '.join(type_conditions)})")
                
                where_clause = " AND ".join(conditions) if conditions else "true"
                
                query = f"""
                MATCH (r:Resource)
                WHERE r.valid_to IS NULL AND {where_clause}
                RETURN count(r) as count
                """
                
                result = session.run(query)
                return result.single()["count"]
                
        except Exception as e:
            logger.error(f"Error counting resources for policy {policy.name}: {e}")
            return 0
    
    def _count_compliant_resources(self, policy) -> int:
        """Count resources that are compliant with policy"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (r:Resource)
                WHERE r.valid_to IS NULL
                AND NOT EXISTS {
                    MATCH (p:Policy {id: $policy_id})-[:VIOLATED_BY]->(v:Violation)-[:DETECTED_ON]->(r)
                    WHERE v.created_at > datetime() - duration('P7D')
                }
                RETURN count(r) as count
                """
                
                result = session.run(query, policy_id=policy.id)
                return result.single()["count"]
                
        except Exception as e:
            logger.error(f"Error counting compliant resources for policy {policy.name}: {e}")
            return 0
    
    def _group_violations_by_severity(self, violations: List[Dict]) -> Dict:
        """Group violations by severity"""
        severity_counts = {}
        for violation in violations:
            severity = violation.get('severity', 'medium')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        return severity_counts
    
    def _analyze_drift_types(self, drifted_resources: List[Dict]) -> Dict:
        """Analyze types of drift detected"""
        drift_types = {
            'configuration_changes': 0,
            'tag_changes': 0,
            'state_changes': 0,
            'new_resources': 0
        }
        
        for resource in drifted_resources:
            # Analyze what changed (simplified)
            if resource.get('last_modified'):
                drift_types['configuration_changes'] += 1
        
        return drift_types
    
    def _tag_drifted_resources(self, resources: List[Dict]):
        """Tag resources that have drifted"""
        try:
            with self.driver.session() as session:
                for resource in resources:
                    session.run("""
                    MATCH (r:Resource {id: $id})
                    WHERE r.valid_to IS NULL
                    SET r.tags.last_drift_check = $timestamp,
                        r.tags.drift_status = 'detected'
                    """, 
                    id=resource['id'],
                    timestamp=datetime.utcnow().isoformat()
                    )
                    
        except Exception as e:
            logger.error(f"Error tagging drifted resources: {e}")
    
    def _store_evaluation_results(self, result: EvaluationResult, violations: List[Dict]):
        """Store evaluation results in Neo4j"""
        try:
            with self.driver.session() as session:
                # Store evaluation record
                session.run("""
                CREATE (e:Evaluation {
                    id: $evaluation_id,
                    type: $evaluation_type,
                    status: $status,
                    start_time: datetime($start_time),
                    end_time: datetime($end_time),
                    resources_evaluated: $resources_evaluated,
                    violations_found: $violations_found,
                    details: $details,
                    created_at: datetime()
                })
                """, 
                evaluation_id=result.evaluation_id,
                evaluation_type=result.evaluation_type.value,
                status=result.status.value,
                start_time=result.start_time.isoformat(),
                end_time=result.end_time.isoformat() if result.end_time else None,
                resources_evaluated=result.resources_evaluated,
                violations_found=result.violations_found,
                details=json.dumps(result.details) if result.details else None
                )
                
        except Exception as e:
            logger.error(f"Error storing evaluation results: {e}")
    
    def _store_compliance_report(self, report: Dict):
        """Store compliance report"""
        try:
            with self.driver.session() as session:
                session.run("""
                CREATE (c:ComplianceReport {
                    timestamp: datetime($timestamp),
                    overall_compliance: $overall_compliance,
                    total_resources: $total_resources,
                    compliant_resources: $compliant_resources,
                    policies_evaluated: $policies_evaluated,
                    details: $details,
                    created_at: datetime()
                })
                """, 
                timestamp=report["timestamp"],
                overall_compliance=report["overall_compliance"],
                total_resources=report["total_resources"],
                compliant_resources=report["compliant_resources"],
                policies_evaluated=report["policies_evaluated"],
                details=json.dumps(report)
                )
                
        except Exception as e:
            logger.error(f"Error storing compliance report: {e}")
    
    def _store_monthly_report(self, report: Dict):
        """Store monthly report"""
        try:
            with self.driver.session() as session:
                session.run("""
                CREATE (m:MonthlyReport {
                    report_id: $report_id,
                    report_period: $report_period,
                    summary: $summary,
                    trends: $trends,
                    top_violations: $top_violations,
                    recommendations: $recommendations,
                    created_at: datetime()
                })
                """, 
                report_id=f"monthly-{int(datetime.utcnow().timestamp())}",
                report_period=report["report_period"],
                summary=json.dumps(report["summary"]),
                trends=json.dumps(report["trends"]),
                top_violations=json.dumps(report["top_violations"]),
                recommendations=json.dumps(report["recommendations"])
                )
                
        except Exception as e:
            logger.error(f"Error storing monthly report: {e}")
    
    def _generate_monthly_summary(self) -> Dict:
        """Generate monthly summary statistics"""
        # Simplified implementation
        return {
            "total_evaluations": 0,
            "total_violations": 0,
            "compliance_trend": "stable"
        }
    
    def _analyze_trends(self) -> Dict:
        """Analyze compliance trends"""
        # Simplified implementation
        return {
            "compliance_trend": "improving",
            "violation_trend": "decreasing"
        }
    
    def _get_top_violations(self) -> List[Dict]:
        """Get top violations for the period"""
        # Simplified implementation
        return []
    
    def _generate_recommendations(self) -> List[str]:
        """Generate improvement recommendations"""
        return [
            "Review and update outdated policies",
            "Focus on high-severity violations",
            "Implement automated remediation"
        ]
    
    def _handle_evaluation_completion(self, result: EvaluationResult):
        """Handle evaluation completion"""
        if result.evaluation_id in self.current_evaluations:
            del self.current_evaluations[result.evaluation_id]
        
        self.evaluation_history.append(result)
        
        # Keep only last 100 evaluations
        if len(self.evaluation_history) > 100:
            self.evaluation_history = self.evaluation_history[-100:]
        
        self._notify_callbacks('completed', result)
        
        # Update metrics
        self.metrics.record_policy_evaluation(
            policy_type=result.evaluation_type.value,
            result="success",
            duration=(result.end_time - result.start_time).total_seconds()
        )
    
    def _handle_evaluation_failure(self, evaluation_id: str, eval_type: EvaluationType, error: str):
        """Handle evaluation failure"""
        result = EvaluationResult(
            evaluation_id=evaluation_id,
            evaluation_type=eval_type,
            status=EvaluationStatus.FAILED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            resources_evaluated=0,
            violations_found=0,
            error=error
        )
        
        if evaluation_id in self.current_evaluations:
            del self.current_evaluations[evaluation_id]
        
        self.evaluation_history.append(result)
        self._notify_callbacks('failed', result)
        
        # Update metrics
        self.metrics.record_error("scheduled_evaluation", "evaluator")
    
    def _notify_callbacks(self, event_type: str, result: EvaluationResult):
        """Notify registered callbacks"""
        for callback in self.evaluation_callbacks.get(event_type, []):
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in evaluation callback: {e}")
    
    def add_evaluation_callback(self, event_type: str, callback: Callable):
        """Add callback for evaluation events"""
        if event_type not in self.evaluation_callbacks:
            self.evaluation_callbacks[event_type] = []
        self.evaluation_callbacks[event_type].append(callback)
    
    def get_evaluation_status(self, evaluation_id: str) -> Optional[EvaluationResult]:
        """Get status of a specific evaluation"""
        return self.current_evaluations.get(evaluation_id)
    
    def get_evaluation_history(self, limit: int = 50) -> List[EvaluationResult]:
        """Get evaluation history"""
        return self.evaluation_history[-limit:]
    
    def get_current_evaluations(self) -> Dict[str, EvaluationResult]:
        """Get currently running evaluations"""
        return self.current_evaluations.copy()
    
    def configure_schedule(self, config: Dict[str, bool]):
        """Configure evaluation schedule"""
        self.schedule_config.update(config)
        if self.running:
            self._configure_schedule()  # Reconfigure with new settings
