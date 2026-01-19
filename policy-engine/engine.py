from typing import Dict, List, Any, Optional, Union
from neo4j import GraphDatabase
import yaml
import json
import re
from datetime import datetime, timedelta
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .schemas.policy import (
    Policy, ActionType, Condition, GraphCondition, 
    ConditionField, ConditionOperator, EnforcementMode
)
from shared.metrics import get_metrics, MetricsTimer

logger = logging.getLogger(__name__)


class PolicyEngine:
    """Core policy evaluation engine for SkySentinel"""
    
    def __init__(self, neo4j_driver, cloud_clients: Dict[str, Any]):
        self.driver = neo4j_driver
        self.cloud_clients = cloud_clients
        self.policies: Dict[str, Policy] = {}
        self.policy_sets: Dict[str, List[str]] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.metrics = get_metrics()
        
        # Cache for frequently accessed data
        self._resource_cache = {}
        self._policy_cache_ttl = timedelta(minutes=5)
        self._last_cache_update = {}
        
    def load_policy(self, policy_yaml: str) -> Policy:
        """Load and validate a policy from YAML"""
        try:
            policy_dict = yaml.safe_load(policy_yaml)
            if 'policy' in policy_dict:
                policy_dict = policy_dict['policy']
            
            policy = Policy(**policy_dict)
            self.policies[policy.id] = policy
            
            logger.info(f"Loaded policy: {policy.name} (ID: {policy.id})")
            self.metrics.record_policy_evaluation(
                policy_type="load", 
                result="success", 
                duration=0.1
            )
            
            return policy
            
        except Exception as e:
            logger.error(f"Failed to load policy: {e}")
            self.metrics.record_error("policy_load", "engine")
            raise
    
    def load_policy_from_file(self, file_path: str) -> Policy:
        """Load policy from YAML file"""
        with open(file_path, 'r') as f:
            content = f.read()
        return self.load_policy(content)
    
    def evaluate_event(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate policies against an event"""
        with MetricsTimer(self.metrics.event_processing_duration):
            violations = []
            
            try:
                # Get applicable policies
                applicable_policies = self._get_applicable_policies(event)
                
                # Evaluate each applicable policy
                for policy_id, policy in applicable_policies.items():
                    if not policy.enabled or policy.is_expired():
                        continue
                    
                    try:
                        # Evaluate condition
                        if self._evaluate_condition(policy, event):
                            violation = self._create_violation(policy, event)
                            violations.append(violation)
                            
                            # Record metrics
                            self.metrics.record_alert_generated(
                                severity=policy.severity,
                                alert_type="policy_violation"
                            )
                            
                            # Execute actions based on enforcement mode
                            self._execute_actions(policy, violation)
                            
                    except Exception as e:
                        logger.error(f"Error evaluating policy {policy.name}: {e}")
                        self.metrics.record_error("policy_evaluation", "engine")
                
                # Update metrics
                self.metrics.record_event_processed(
                    cloud=event.get('cloud', 'unknown'),
                    event_type=event.get('event_type', 'unknown'),
                    duration=0.1  # Timer will provide actual duration
                )
                
            except Exception as e:
                logger.error(f"Error in event evaluation: {e}")
                self.metrics.record_error("event_evaluation", "engine")
            
            return violations
    
    def evaluate_resource(self, resource_id: str, context: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Evaluate policies against a specific resource"""
        violations = []
        
        try:
            # Get resource data from graph
            resource_data = self._get_resource_data(resource_id)
            if not resource_data:
                logger.warning(f"Resource not found: {resource_id}")
                return violations
            
            # Create synthetic event for resource evaluation
            event = {
                'resource': resource_data,
                'cloud': resource_data.get('cloud'),
                'event_type': 'resource_evaluation',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            if context:
                event.update(context)
            
            return self.evaluate_event(event)
            
        except Exception as e:
            logger.error(f"Error evaluating resource {resource_id}: {e}")
            self.metrics.record_error("resource_evaluation", "engine")
            return violations
    
    def _get_applicable_policies(self, event: Dict) -> Dict[str, Policy]:
        """Get policies that apply to the given event"""
        applicable = {}
        
        for policy_id, policy in self.policies.items():
            if self._policy_applies_to_event(policy, event):
                applicable[policy_id] = policy
        
        return applicable
    
    def _policy_applies_to_event(self, policy: Policy, event: Dict) -> bool:
        """Check if policy applies to the given event"""
        try:
            resource = event.get('resource', {})
            resource_type = resource.get('type', '')
            resource_cloud = event.get('cloud', resource.get('cloud', ''))
            resource_tags = resource.get('tags', {})
            resource_region = resource.get('region', '')
            resource_account = resource.get('account', '')
            
            # Check cloud filter
            if policy.resources.cloud and policy.resources.cloud != 'all':
                if resource_cloud != policy.resources.cloud:
                    return False
            
            # Check resource types (with wildcards)
            if policy.resources.resource_types:
                if not self._matches_resource_type(resource_type, policy.resources.resource_types):
                    return False
            
            # Check excluded resource types
            if policy.resources.exclude_resource_types:
                if self._matches_resource_type(resource_type, policy.resources.exclude_resource_types):
                    return False
            
            # Check tags
            if policy.resources.tags:
                for key, value in policy.resources.tags.items():
                    if '|' in str(value):
                        # Handle OR logic in tag values
                        values = [v.strip() for v in str(value).split('|')]
                        if resource_tags.get(key) not in values:
                            return False
                    else:
                        if resource_tags.get(key) != value:
                            return False
            
            # Check excluded tags
            if policy.resources.exclude_tags:
                for key, value in policy.resources.exclude_tags.items():
                    if resource_tags.get(key) == value:
                        return False
            
            # Check region
            if policy.resources.region:
                if resource_region != policy.resources.region:
                    return False
            
            # Check account IDs
            if policy.resources.account_ids:
                if resource_account not in policy.resources.account_ids:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking policy applicability: {e}")
            return False
    
    def _matches_resource_type(self, actual_type: str, allowed_types: List[str]) -> bool:
        """Check if resource type matches any allowed type (with wildcards)"""
        for allowed in allowed_types:
            if '*' in allowed:
                # Convert wildcard pattern to regex
                pattern = allowed.replace('.', r'\.').replace('*', '.*')
                if re.match(f'^{pattern}$', actual_type):
                    return True
            elif actual_type == allowed:
                return True
        return False
    
    def _evaluate_condition(self, policy: Policy, event: Dict) -> bool:
        """Evaluate policy condition against event"""
        try:
            condition = policy.condition
            
            if isinstance(condition, GraphCondition):
                return self._evaluate_graph_condition(condition, event)
            elif isinstance(condition, Condition):
                return self._evaluate_logical_condition(condition, event)
            elif isinstance(condition, dict):
                # Handle legacy format
                if 'graph' in condition:
                    return self._evaluate_graph_condition(
                        GraphCondition(**condition['graph']), event
                    )
                else:
                    return self._evaluate_simple_condition(condition, event)
            else:
                logger.warning(f"Unknown condition type: {type(condition)}")
                return False
                
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    def _evaluate_graph_condition(self, graph_condition: GraphCondition, event: Dict) -> bool:
        """Evaluate graph-based condition using Neo4j"""
        with MetricsTimer(self.metrics.graph_query_duration):
            try:
                resource_id = event.get('resource', {}).get('id')
                
                if not resource_id:
                    return False
                
                query = self._build_graph_query(graph_condition, resource_id)
                
                with self.driver.session() as session:
                    result = session.run(query, resource_id=resource_id)
                    record = result.single()
                    return record['exists'] if record else False
                    
            except Exception as e:
                logger.error(f"Graph query failed: {e}")
                self.metrics.record_error("graph_query", "engine")
                return False
    
    def _build_graph_query(self, condition: GraphCondition, resource_id: str) -> str:
        """Build Cypher query from graph condition"""
        path_config = condition.path
        where_condition = condition.where
        max_depth = condition.max_depth
        
        # Convert path configuration to Cypher pattern
        path_pattern = self._build_path_pattern(path_config)
        
        # Build WHERE clause
        where_clause = ""
        if where_condition:
            if isinstance(where_condition, Condition):
                where_clause = f"WHERE {self._build_logical_cypher(where_condition)}"
            else:
                where_clause = f"WHERE {self._build_simple_cypher(where_condition)}"
        
        # Build final query
        query = f"""
        MATCH {path_pattern}
        {where_clause}
        RETURN count(*) > 0 as exists
        LIMIT 1
        """
        
        return query
    
    def _build_path_pattern(self, path_config) -> str:
        """Convert path configuration to Cypher pattern"""
        if not path_config:
            return "(r:Resource {id: $resource_id})"
        
        from_node = path_config.from_ or 'internet'
        to_node = path_config.to or 'resource'
        via = path_config.via or []
        direction = path_config.direction
        
        # Build relationship pattern
        if via:
            # Multi-hop path
            pattern = f"({from_node})"
            for hop in via:
                if direction == 'incoming':
                    pattern += f"<-[:CONNECTED_TO*..{path_config.max_depth}]-(:{hop})"
                elif direction == 'both':
                    pattern += f"-[:CONNECTED_TO*..{path_config.max_depth}]-(:{hop})"
                else:  # outgoing
                    pattern += f"-[:CONNECTED_TO*..{path_config.max_depth}]->(:{hop})"
            pattern += f"->({to_node})"
        else:
            # Direct path
            if direction == 'incoming':
                pattern = f"({from_node})<-[:CONNECTED_TO*..{path_config.max_depth}]-({to_node})"
            elif direction == 'both':
                pattern = f"({from_node})-[:CONNECTED_TO*..{path_config.max_depth}]-({to_node})"
            else:  # outgoing
                pattern = f"({from_node})-[:CONNECTED_TO*..{path_config.max_depth}]->({to_node})"
        
        return pattern
    
    def _build_logical_cypher(self, condition: Condition) -> str:
        """Build Cypher WHERE clause from logical condition"""
        if condition.any:
            clauses = [self._build_logical_cypher(sub) for sub in condition.any]
            return f"({' OR '.join(clauses)})"
        elif condition.all:
            clauses = [self._build_logical_cypher(sub) for sub in condition.all]
            return f"({' AND '.join(clauses)})"
        elif condition.not_:
            clause = self._build_logical_cypher(condition.not_)
            return f"NOT ({clause})"
        elif condition.field:
            return self._build_field_cypher(condition.field)
        else:
            return "true"
    
    def _build_simple_cypher(self, condition: Dict) -> str:
        """Build Cypher WHERE clause from simple condition dict"""
        clauses = []
        for key, value in condition.items():
            if isinstance(value, dict) and 'operator' in value:
                clauses.append(self._build_operator_cypher(key, value))
            else:
                clauses.append(f"{key} = '{value}'")
        return " AND ".join(clauses)
    
    def _build_field_cypher(self, field: ConditionField) -> str:
        """Build Cypher clause for field condition"""
        field_path = field.field
        operator = field.operator
        value = field.value
        
        return self._build_operator_cypher(field_path, {
            'operator': operator,
            'value': value
        })
    
    def _build_operator_cypher(self, field: str, condition: Dict) -> str:
        """Build Cypher clause for operator condition"""
        operator = condition['operator']
        value = condition['value']
        
        operators = {
            'eq': f"{field} = '{value}'",
            'ne': f"{field} <> '{value}'",
            'gt': f"{field} > {value}",
            'gte': f"{field} >= {value}",
            'lt': f"{field} < {value}",
            'lte': f"{field} <= {value}",
            'contains': f"{field} CONTAINS '{value}'",
            'starts_with': f"{field} STARTS WITH '{value}'",
            'ends_with': f"{field} ENDS WITH '{value}'",
            'exists': f"{field} IS NOT NULL",
            'not_exists': f"{field} IS NULL",
            'in': f"{field} IN {json.dumps(value)}",
            'not_in': f"{field} NOT IN {json.dumps(value)}",
            'regex': f"{field} =~ '{value}'"
        }
        
        return operators.get(operator, f"{field} = '{value}'")
    
    def _evaluate_logical_condition(self, condition: Condition, event: Dict) -> bool:
        """Evaluate logical condition tree"""
        if condition.any:
            return any(self._evaluate_logical_condition(sub, event) for sub in condition.any)
        elif condition.all:
            return all(self._evaluate_logical_condition(sub, event) for sub in condition.all)
        elif condition.not_:
            return not self._evaluate_logical_condition(condition.not_, event)
        elif condition.field:
            return self._evaluate_field_condition(condition.field, event)
        else:
            return True
    
    def _evaluate_simple_condition(self, condition: Dict, event: Dict) -> bool:
        """Evaluate simple logical conditions (legacy format)"""
        if 'and' in condition:
            return all(self._evaluate_simple_condition(sub, event) 
                      for sub in condition['and'])
        elif 'or' in condition:
            return any(self._evaluate_simple_condition(sub, event)
                      for sub in condition['or'])
        elif 'not' in condition:
            return not self._evaluate_simple_condition(condition['not'], event)
        else:
            # Evaluate field condition
            field = condition.get('field')
            operator = condition.get('operator', 'eq')
            value = condition.get('value')
            
            actual_value = self._get_nested_value(event, field)
            
            return self._apply_operator(operator, actual_value, value)
    
    def _evaluate_field_condition(self, field: ConditionField, event: Dict) -> bool:
        """Evaluate a single field condition"""
        actual_value = self._get_nested_value(event, field.field)
        return self._apply_operator(field.operator, actual_value, field.value)
    
    def _get_nested_value(self, obj: Dict, path: str) -> Any:
        """Get value from nested dictionary using dot notation"""
        if not obj or not path:
            return None
            
        keys = path.split('.')
        current = obj
        
        try:
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                elif isinstance(current, list) and key.isdigit():
                    idx = int(key)
                    if 0 <= idx < len(current):
                        current = current[idx]
                    else:
                        return None
                else:
                    return None
            return current
        except (KeyError, TypeError, IndexError):
            return None
    
    def _apply_operator(self, operator: str, actual: Any, expected: Any) -> bool:
        """Apply comparison operator"""
        try:
            operators = {
                ConditionOperator.EQUALS: lambda a, e: a == e,
                ConditionOperator.NOT_EQUALS: lambda a, e: a != e,
                ConditionOperator.CONTAINS: lambda a, e: isinstance(a, str) and e in a,
                ConditionOperator.STARTS_WITH: lambda a, e: isinstance(a, str) and a.startswith(e),
                ConditionOperator.ENDS_WITH: lambda a, e: isinstance(a, str) and a.endswith(e),
                ConditionOperator.GREATER_THAN: lambda a, e: float(a) > float(e) if a and e else False,
                ConditionOperator.GREATER_EQUAL: lambda a, e: float(a) >= float(e) if a and e else False,
                ConditionOperator.LESS_THAN: lambda a, e: float(a) < float(e) if a and e else False,
                ConditionOperator.LESS_EQUAL: lambda a, e: float(a) <= float(e) if a and e else False,
                ConditionOperator.EXISTS: lambda a, e: a is not None,
                ConditionOperator.NOT_EXISTS: lambda a, e: a is None,
                ConditionOperator.IN: lambda a, e: a in e if isinstance(e, list) else False,
                ConditionOperator.NOT_IN: lambda a, e: a not in e if isinstance(e, list) else False,
                ConditionOperator.REGEX: lambda a, e: bool(re.search(e, str(a))) if a else False,
            }
            
            if operator not in operators:
                logger.warning(f"Unknown operator: {operator}")
                return False
            
            return operators[operator](actual, expected)
            
        except Exception as e:
            logger.error(f"Error applying operator {operator}: {e}")
            return False
    
    def _create_violation(self, policy: Policy, event: Dict) -> Dict:
        """Create violation record"""
        return {
            "id": f"violation-{int(datetime.utcnow().timestamp())}",
            "policy_id": policy.id,
            "policy_name": policy.name,
            "policy_version": policy.version,
            "severity": policy.severity,
            "timestamp": datetime.utcnow().isoformat(),
            "resource": event.get('resource'),
            "event": event,
            "description": f"Violation of policy: {policy.name}",
            "status": "open",
            "remediation_actions": [action.dict() for action in policy.actions],
            "enforcement_mode": policy.enforcement.get('runtime', {}).get('mode', 'post-event')
        }
    
    def _execute_actions(self, policy: Policy, violation: Dict):
        """Execute policy actions based on enforcement mode"""
        try:
            enforcement_mode = policy.enforcement.get('runtime', {}).get('mode', EnforcementMode.POST_EVENT)
            
            if enforcement_mode == EnforcementMode.INLINE_DENY:
                self._perform_inline_deny(policy, violation)
            elif enforcement_mode == EnforcementMode.POST_EVENT:
                self._perform_post_event_actions(policy, violation)
            elif enforcement_mode == EnforcementMode.SCHEDULED:
                self._schedule_actions(policy, violation)
            elif enforcement_mode == EnforcementMode.AUDIT_ONLY:
                logger.info(f"Audit-only mode: Would execute actions for {policy.name}")
            
            # Store violation in graph
            self._store_violation(violation)
            
        except Exception as e:
            logger.error(f"Error executing actions for policy {policy.name}: {e}")
            self.metrics.record_error("action_execution", "engine")
    
    def _perform_inline_deny(self, policy: Policy, violation: Dict):
        """Attempt to deny the action inline (if supported by cloud provider)"""
        event = violation['event']
        cloud = event.get('cloud')
        
        logger.warning(f"Inline deny triggered for policy: {policy.name}")
        
        if cloud == 'aws':
            self._inline_deny_aws(event)
        elif cloud == 'azure':
            self._inline_deny_azure(event)
        elif cloud == 'gcp':
            self._inline_deny_gcp(event)
    
    def _inline_deny_aws(self, event: Dict):
        """Implement AWS inline denial using SCPs or EventBridge"""
        try:
            eventbridge = self.cloud_clients.get('aws', {}).get('eventbridge')
            if eventbridge:
                # Put event back with deny decision
                eventbridge.put_events(
                    Entries=[{
                        'Source': 'sky-sentinel',
                        'DetailType': 'PolicyDenial',
                        'Detail': json.dumps({
                            'original_event': event,
                            'decision': 'DENY',
                            'timestamp': datetime.utcnow().isoformat()
                        }),
                        'EventBusName': 'default'
                    }]
                )
                logger.info("AWS inline deny event sent")
            else:
                logger.warning("EventBridge client not available for inline deny")
                
        except Exception as e:
            logger.error(f"Failed to send AWS denial event: {e}")
    
    def _inline_deny_azure(self, event: Dict):
        """Implement Azure inline denial using Azure Policy"""
        logger.info("Azure inline deny would be implemented here")
    
    def _inline_deny_gcp(self, event: Dict):
        """Implement GCP inline denial using Organization Policy"""
        logger.info("GCP inline deny would be implemented here")
    
    def _perform_post_event_actions(self, policy: Policy, violation: Dict):
        """Execute post-event remediation actions"""
        for action in policy.actions:
            try:
                if action.type == ActionType.NOTIFY:
                    self._execute_notify_action(action, violation)
                elif action.type == ActionType.TAG:
                    self._execute_tag_action(action, violation)
                elif action.type == ActionType.STOP:
                    self._execute_stop_action(action, violation)
                elif action.type == ActionType.DISABLE:
                    self._execute_disable_action(action, violation)
                elif action.type == ActionType.QUARANTINE:
                    self._execute_quarantine_action(action, violation)
                elif action.type == ActionType.ESCALATE:
                    self._execute_escalate_action(action, violation)
                    
            except Exception as e:
                logger.error(f"Error executing action {action.type}: {e}")
    
    def _execute_notify_action(self, action, violation: Dict):
        """Execute notification action"""
        logger.info(f"Notification action executed for violation {violation['id']}")
        # Implementation would integrate with notification channels
    
    def _execute_tag_action(self, action, violation: Dict):
        """Execute tagging action"""
        logger.info(f"Tag action executed for violation {violation['id']}")
        # Implementation would tag resources in respective cloud
    
    def _execute_stop_action(self, action, violation: Dict):
        """Execute stop action"""
        logger.info(f"Stop action executed for violation {violation['id']}")
        # Implementation would stop resources
    
    def _execute_disable_action(self, action, violation: Dict):
        """Execute disable action"""
        logger.info(f"Disable action executed for violation {violation['id']}")
        # Implementation would disable resources
    
    def _execute_quarantine_action(self, action, violation: Dict):
        """Execute quarantine action"""
        logger.info(f"Quarantine action executed for violation {violation['id']}")
        # Implementation would quarantine resources
    
    def _execute_escalate_action(self, action, violation: Dict):
        """Execute escalation action"""
        logger.info(f"Escalation action executed for violation {violation['id']}")
        # Implementation would escalate to higher-level systems
    
    def _schedule_actions(self, policy: Policy, violation: Dict):
        """Schedule actions for later execution"""
        logger.info(f"Actions scheduled for violation {violation['id']}")
        # Implementation would use task scheduler
    
    def _store_violation(self, violation: Dict):
        """Store violation in Neo4j graph"""
        query = """
        MERGE (v:Violation {id: $id})
        SET v += $properties,
            v.created_at = datetime(),
            v.updated_at = datetime()
        
        WITH v
        MATCH (r:Resource {id: $resource_id})
        WHERE r.valid_to IS NULL
        MERGE (v)-[:DETECTED_ON]->(r)
        
        WITH v
        MATCH (p:Policy {id: $policy_id})
        MERGE (p)-[:VIOLATED_BY]->(v)
        
        RETURN v
        """
        
        try:
            with self.driver.session() as session:
                session.run(query, 
                    id=violation['id'],
                    properties=violation,
                    resource_id=violation['resource']['id'],
                    policy_id=violation['policy_id']
                )
        except Exception as e:
            logger.error(f"Failed to store violation: {e}")
            self.metrics.record_error("violation_storage", "engine")
    
    def _get_resource_data(self, resource_id: str) -> Optional[Dict]:
        """Get resource data from graph"""
        query = """
        MATCH (r:Resource {id: $id})
        WHERE r.valid_to IS NULL
        OPTIONAL MATCH (r)-[:HAS_TAG]->(t:Tag)
        RETURN r, collect(t) as tags
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, id=resource_id)
                record = result.single()
                
                if record:
                    resource = dict(record['r'])
                    tags = {tag['key']: tag['value'] for tag in record['tags']}
                    resource['tags'] = tags
                    return resource
                    
        except Exception as e:
            logger.error(f"Failed to get resource data: {e}")
        
        return None
    
    def get_policy_stats(self) -> Dict[str, Any]:
        """Get policy engine statistics"""
        return {
            'total_policies': len(self.policies),
            'enabled_policies': len([p for p in self.policies.values() if p.enabled]),
            'expired_policies': len([p for p in self.policies.values() if p.is_expired()]),
            'policies_by_severity': {
                severity: len([p for p in self.policies.values() if p.severity == severity])
                for severity in ['critical', 'high', 'medium', 'low', 'info']
            }
        }
    
    def shutdown(self):
        """Shutdown the policy engine"""
        self.executor.shutdown(wait=True)
        logger.info("Policy engine shutdown complete")
