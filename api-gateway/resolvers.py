"""
SkySentinel GraphQL Resolvers

This module contains the resolver functions for the GraphQL API schema.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from graph_engine.neo4j_client import Neo4jClient
from policy_engine.engine import PolicyEngine
from shared.metrics import MetricsCollector

logger = logging.getLogger(__name__)


class GraphQLResolvers:
    """GraphQL resolver implementations"""
    
    def __init__(self, neo4j_client: Neo4jClient, policy_engine: PolicyEngine, 
                 metrics: MetricsCollector):
        self.neo4j_client = neo4j_client
        self.policy_engine = policy_engine
        self.metrics = metrics
    
    # Resource Resolvers
    async def resolve_resource(self, info, id: str) -> Optional[Dict[str, Any]]:
        """Resolve a single resource by ID"""
        try:
            # Query Neo4j for resource
            query = """
            MATCH (r:Resource {id: $id})
            OPTIONAL MATCH (r)-[:HAS_VIOLATION]->(v:Violation)
            OPTIONAL MATCH (r)-[:DEPENDS_ON]->(dep:Resource)
            OPTIONAL MATCH (dep)-[:DEPENDS_ON]->(r)
            RETURN r, collect(v) as violations, collect(dep) as dependencies
            """
            
            result = await self.neo4j_client.run_query(query, {"id": id})
            
            if not result:
                return None
            
            # Transform to GraphQL format
            resource_data = result[0]["r"]
            return self._format_resource(resource_data, result[0])
            
        except Exception as e:
            logger.error(f"Error resolving resource {id}: {e}")
            raise
    
    async def resolve_resources(self, info, filter: Dict = None, limit: int = 100, 
                              offset: int = 0, sortBy: str = "name", 
                              sortOrder: str = "ASC") -> List[Dict[str, Any]]:
        """Resolve resources with filtering and pagination"""
        try:
            # Build Neo4j query
            where_clauses = []
            params = {"limit": limit, "offset": offset}
            
            if filter:
                if filter.get("type"):
                    where_clauses.append("r.type = $type")
                    params["type"] = filter["type"]
                
                if filter.get("cloud"):
                    where_clauses.append("r.cloud = $cloud")
                    params["cloud"] = filter["cloud"]
                
                if filter.get("region"):
                    where_clauses.append("r.region = $region")
                    params["region"] = filter["region"]
                
                if filter.get("tags"):
                    # Handle tag filtering
                    tag_conditions = []
                    for i, tag_filter in enumerate(filter["tags"]):
                        tag_key = f"tag_key_{i}"
                        tag_value = f"tag_value_{i}"
                        tag_conditions.append(f"r.tags.{tag_filter['key']} = ${tag_value}")
                        params[tag_key] = tag_filter["key"]
                        params[tag_value] = tag_filter["value"]
                    
                    if tag_conditions:
                        where_clauses.append(f"({' AND '.join(tag_conditions)})")
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = f"""
            MATCH (r:Resource)
            WHERE {where_clause}
            OPTIONAL MATCH (r)-[:HAS_VIOLATION]->(v:Violation)
            RETURN r, collect(v) as violations
            ORDER BY r.{sortBy} {sortOrder}
            SKIP $offset LIMIT $limit
            """
            
            results = await self.neo4j_client.run_query(query, params)
            
            # Format results
            resources = []
            for result in results:
                resource_data = result["r"]
                formatted_resource = self._format_resource(resource_data, result)
                resources.append(formatted_resource)
            
            return resources
            
        except Exception as e:
            logger.error(f"Error resolving resources: {e}")
            raise
    
    async def resolve_search_resources(self, info, query: str, limit: int = 50, 
                                     filters: Dict = None) -> Dict[str, Any]:
        """Search resources by text query"""
        try:
            # Build search query
            where_clauses = [
                "(toLower(r.name) CONTAINS toLower($query) OR toLower(r.type) CONTAINS toLower($query))"
            ]
            params = {"query": query, "limit": limit}
            
            if filters:
                if filters.get("cloud"):
                    where_clauses.append("r.cloud = $cloud")
                    params["cloud"] = filters["cloud"]
                
                if filters.get("type"):
                    where_clauses.append("r.type = $type")
                    params["type"] = filters["type"]
            
            where_clause = " AND ".join(where_clauses)
            
            # Search resources, policies, and violations
            resource_query = f"""
            MATCH (r:Resource)
            WHERE {where_clause}
            OPTIONAL MATCH (r)-[:HAS_VIOLATION]->(v:Violation)
            RETURN 'resource' as type, r as item, collect(v) as violations
            LIMIT $limit
            """
            
            policy_query = f"""
            MATCH (p:Policy)
            WHERE toLower(p.name) CONTAINS toLower($query) OR toLower(p.description) CONTAINS toLower($query)
            RETURN 'policy' as type, p as item, [] as violations
            LIMIT $limit
            """
            
            violation_query = f"""
            MATCH (v:Violation)
            WHERE toLower(v.title) CONTAINS toLower($query) OR toLower(v.description) CONTAINS toLower($query)
            RETURN 'violation' as type, v as item, [] as violations
            LIMIT $limit
            """
            
            # Execute queries in parallel
            resource_results, policy_results, violation_results = await asyncio.gather(
                self.neo4j_client.run_query(resource_query, params),
                self.neo4j_client.run_query(policy_query, params),
                self.neo4j_client.run_query(violation_query, params)
            )
            
            # Format results
            resources = []
            policies = []
            violations = []
            
            for result in resource_results:
                resource_data = result["item"]
                formatted_resource = self._format_resource(resource_data, result)
                resources.append(formatted_resource)
            
            for result in policy_results:
                policy_data = result["item"]
                formatted_policy = self._format_policy(policy_data)
                policies.append(formatted_policy)
            
            for result in violation_results:
                violation_data = result["item"]
                formatted_violation = self._format_violation(violation_data)
                violations.append(formatted_violation)
            
            total = len(resources) + len(policies) + len(violations)
            has_more = total >= limit
            
            return {
                "resources": resources,
                "policies": policies,
                "violations": violations,
                "total": total,
                "hasMore": has_more
            }
            
        except Exception as e:
            logger.error(f"Error searching resources: {e}")
            raise
    
    # Policy Resolvers
    async def resolve_policy(self, info, id: str) -> Optional[Dict[str, Any]]:
        """Resolve a single policy by ID"""
        try:
            # Query policy from database
            policy = await self.policy_engine.get_policy(id)
            if not policy:
                return None
            
            return self._format_policy(policy)
            
        except Exception as e:
            logger.error(f"Error resolving policy {id}: {e}")
            raise
    
    async def resolve_policies(self, info, category: str = None, severity: str = None,
                             status: str = None, tags: List[str] = None,
                             limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Resolve policies with filtering"""
        try:
            # Build filter criteria
            filters = {}
            if category:
                filters["category"] = category
            if severity:
                filters["severity"] = severity
            if status:
                filters["status"] = status
            if tags:
                filters["tags"] = tags
            
            # Query policies
            policies = await self.policy_engine.list_policies(
                filters=filters, limit=limit, offset=offset
            )
            
            # Format results
            formatted_policies = []
            for policy in policies:
                formatted_policy = self._format_policy(policy)
                formatted_policies.append(formatted_policy)
            
            return formatted_policies
            
        except Exception as e:
            logger.error(f"Error resolving policies: {e}")
            raise
    
    # Violation Resolvers
    async def resolve_violation(self, info, id: str) -> Optional[Dict[str, Any]]:
        """Resolve a single violation by ID"""
        try:
            # Query violation from database
            query = """
            MATCH (v:Violation {id: $id})
            OPTIONAL MATCH (v)-[:VIOLATES_POLICY]->(p:Policy)
            OPTIONAL MATCH (v)-[:AFFECTS_RESOURCE]->(r:Resource)
            RETURN v, p, r
            """
            
            result = await self.neo4j_client.run_query(query, {"id": id})
            
            if not result:
                return None
            
            violation_data = result[0]["v"]
            policy_data = result[0]["p"]
            resource_data = result[0]["r"]
            
            return self._format_violation(violation_data, policy_data, resource_data)
            
        except Exception as e:
            logger.error(f"Error resolving violation {id}: {e}")
            raise
    
    async def resolve_violations(self, info, filter: Dict = None, limit: int = 100,
                                offset: int = 0, sortBy: str = "detectedAt",
                                sortOrder: str = "DESC") -> List[Dict[str, Any]]:
        """Resolve violations with filtering"""
        try:
            # Build query
            where_clauses = []
            params = {"limit": limit, "offset": offset}
            
            if filter:
                if filter.get("severity"):
                    where_clauses.append("v.severity = $severity")
                    params["severity"] = filter["severity"]
                
                if filter.get("status"):
                    where_clauses.append("v.status = $status")
                    params["status"] = filter["status"]
                
                if filter.get("resourceId"):
                    where_clauses.append("v.resourceId = $resourceId")
                    params["resourceId"] = filter["resourceId"]
                
                if filter.get("policyId"):
                    where_clauses.append("v.policyId = $policyId")
                    params["policyId"] = filter["policyId"]
                
                if filter.get("from"):
                    where_clauses.append("v.detectedAt >= $from")
                    params["from"] = filter["from"]
                
                if filter.get("to"):
                    where_clauses.append("v.detectedAt <= $to")
                    params["to"] = filter["to"]
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = f"""
            MATCH (v:Violation)
            WHERE {where_clause}
            OPTIONAL MATCH (v)-[:VIOLATES_POLICY]->(p:Policy)
            OPTIONAL MATCH (v)-[:AFFECTS_RESOURCE]->(r:Resource)
            RETURN v, p, r
            ORDER BY v.{sortBy} {sortOrder}
            SKIP $offset LIMIT $limit
            """
            
            results = await self.neo4j_client.run_query(query, params)
            
            # Format results
            violations = []
            for result in results:
                violation_data = result["v"]
                policy_data = result["p"]
                resource_data = result["r"]
                
                formatted_violation = self._format_violation(violation_data, policy_data, resource_data)
                violations.append(formatted_violation)
            
            return violations
            
        except Exception as e:
            logger.error(f"Error resolving violations: {e}")
            raise
    
    # Graph Analysis Resolvers
    async def resolve_attack_paths(self, info, from_id: str, to_id: str = None,
                                  maxDepth: int = 10, minRiskScore: float = 0.0) -> List[Dict[str, Any]]:
        """Resolve attack paths between resources"""
        try:
            # Build path query
            target_clause = ""
            params = {"from": from_id, "maxDepth": maxDepth, "minRiskScore": minRiskScore}
            
            if to_id:
                target_clause = "AND r.id = $to"
                params["to"] = to_id
            
            query = f"""
            MATCH path = shortestPath((start:Resource {id: $from})-[:DEPENDS_ON*1..{maxDepth}]->(end:Resource))
            WHERE end.exposed = true {target_clause}
            WITH path, start, end,
                 [node in nodes(path) | node] as pathNodes,
                 [rel in relationships(path) | rel] as pathRels
            
            OPTIONAL MATCH (n:Resource)-[:HAS_VIOLATION]->(v:Violation)
            WHERE n IN pathNodes AND v.severity IN ['HIGH', 'CRITICAL']
            
            RETURN pathNodes as path, 
                   length(path) as length,
                   collect(v) as vulnerabilities,
                   start as source,
                   end as target
            """
            
            results = await self.neo4j_client.run_query(query, params)
            
            # Format attack paths
            attack_paths = []
            for result in results:
                path_data = {
                    "id": f"attack-path-{from_id}-{to_id or 'exposed'}",
                    "source": self._format_resource(result["source"]),
                    "target": self._format_resource(result["target"]),
                    "path": [self._format_resource(node) for node in result["path"]],
                    "length": result["length"],
                    "vulnerabilities": [self._format_violation(v) for v in result["vulnerabilities"]],
                    "riskScore": self._calculate_path_risk(result["vulnerabilities"]),
                    "description": f"Attack path from {result['source']['name']} to {result['target']['name']}",
                    "discoveredAt": datetime.utcnow().isoformat()
                }
                attack_paths.append(path_data)
            
            return attack_paths
            
        except Exception as e:
            logger.error(f"Error resolving attack paths: {e}")
            raise
    
    async def resolve_resource_dependencies(self, info, resource_id: str, depth: int = 3,
                                          direction: str = "BOTH") -> List[Dict[str, Any]]:
        """Resolve resource dependencies"""
        try:
            # Build dependency query based on direction
            if direction == "INCOMING":
                query = f"""
                MATCH (r:Resource {id: $resourceId})<-[:DEPENDS_ON*1..{depth}]-(dep:Resource)
                RETURN DISTINCT dep
                """
            elif direction == "OUTGOING":
                query = f"""
                MATCH (r:Resource {id: $resourceId})-[:DEPENDS_ON*1..{depth}]->(dep:Resource)
                RETURN DISTINCT dep
                """
            else:  # BOTH
                query = f"""
                MATCH (r:Resource {id: $resourceId})-[:DEPENDS_ON*1..{depth}]-(dep:Resource)
                RETURN DISTINCT dep
                """
            
            results = await self.neo4j_client.run_query(query, {"resourceId": resource_id})
            
            # Format dependencies
            dependencies = []
            for result in results:
                dep_data = result["dep"]
                formatted_dep = self._format_resource(dep_data)
                dependencies.append(formatted_dep)
            
            return dependencies
            
        except Exception as e:
            logger.error(f"Error resolving resource dependencies: {e}")
            raise
    
    # Compliance Resolvers
    async def resolve_compliance_report(self, info, policyId: str = None, resourceId: str = None,
                                       from_date: datetime = None, to_date: datetime = None) -> Dict[str, Any]:
        """Generate compliance report"""
        try:
            # Set default date range if not provided
            if not to_date:
                to_date = datetime.utcnow()
            if not from_date:
                from_date = to_date - timedelta(days=30)
            
            # Generate report data
            report_data = {
                "id": f"compliance-report-{datetime.utcnow().timestamp()}",
                "generatedAt": datetime.utcnow().isoformat(),
                "period": {
                    "from": from_date.isoformat(),
                    "to": to_date.isoformat()
                },
                "overallScore": 0.0,
                "status": "UNKNOWN",
                "summary": await self._generate_compliance_summary(policyId, resourceId, from_date, to_date),
                "policyBreakdown": await self._generate_policy_breakdown(policyId, from_date, to_date),
                "resourceBreakdown": await self._generate_resource_breakdown(resourceId, from_date, to_date),
                "violationBreakdown": await self._generate_violation_breakdown(from_date, to_date),
                "trends": await self._generate_compliance_trends(from_date, to_date),
                "recommendations": await self._generate_recommendations(policyId, resourceId)
            }
            
            # Calculate overall score and status
            report_data["overallScore"] = report_data["summary"]["overallComplianceRate"]
            report_data["status"] = self._determine_compliance_status(report_data["overallScore"])
            
            return report_data
            
        except Exception as e:
            logger.error(f"Error generating compliance report: {e}")
            raise
    
    # Mutation Resolvers
    async def resolve_create_policy(self, info, policy: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new policy"""
        try:
            # Validate and create policy
            created_policy = await self.policy_engine.create_policy(policy)
            
            # Record metrics
            self.metrics.counter('graphql_policies_created_total').inc()
            
            return self._format_policy(created_policy)
            
        except Exception as e:
            logger.error(f"Error creating policy: {e}")
            raise
    
    async def resolve_update_policy(self, info, id: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing policy"""
        try:
            updated_policy = await self.policy_engine.update_policy(id, policy)
            
            # Record metrics
            self.metrics.counter('graphql_policies_updated_total').inc()
            
            return self._format_policy(updated_policy)
            
        except Exception as e:
            logger.error(f"Error updating policy {id}: {e}")
            raise
    
    async def resolve_delete_policy(self, info, id: str) -> bool:
        """Delete a policy"""
        try:
            success = await self.policy_engine.delete_policy(id)
            
            # Record metrics
            self.metrics.counter('graphql_policies_deleted_total').inc()
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting policy {id}: {e}")
            raise
    
    async def resolve_resolve_violation(self, info, id: str, notes: str) -> Dict[str, Any]:
        """Resolve a violation"""
        try:
            # Update violation status
            updated_violation = await self._update_violation_status(id, "RESOLVED", notes)
            
            # Record metrics
            self.metrics.counter('graphql_violations_resolved_total').inc()
            
            return updated_violation
            
        except Exception as e:
            logger.error(f"Error resolving violation {id}: {e}")
            raise
    
    # Helper Methods
    def _format_resource(self, resource_data: Dict[str, Any], additional_data: Dict = None) -> Dict[str, Any]:
        """Format resource data for GraphQL"""
        formatted = {
            "id": resource_data.get("id"),
            "type": resource_data.get("type"),
            "name": resource_data.get("name"),
            "cloud": resource_data.get("cloud"),
            "region": resource_data.get("region"),
            "account": resource_data.get("account"),
            "tags": resource_data.get("tags", []),
            "properties": resource_data.get("properties", {}),
            "metadata": resource_data.get("metadata", {}),
            "createdAt": resource_data.get("createdAt"),
            "updatedAt": resource_data.get("updatedAt"),
            "violations": [],
            "dependencies": [],
            "dependents": [],
            "compliance": {
                "status": "UNKNOWN",
                "score": 0.0,
                "lastAssessed": datetime.utcnow().isoformat(),
                "violations": [],
                "policies": []
            }
        }
        
        # Add additional data if provided
        if additional_data:
            if "violations" in additional_data:
                formatted["violations"] = [self._format_violation(v) for v in additional_data["violations"]]
            if "dependencies" in additional_data:
                formatted["dependencies"] = [self._format_resource(d) for d in additional_data["dependencies"]]
        
        return formatted
    
    def _format_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format policy data for GraphQL"""
        return {
            "id": policy_data.get("id"),
            "name": policy_data.get("name"),
            "description": policy_data.get("description"),
            "category": policy_data.get("category"),
            "severity": policy_data.get("severity"),
            "status": policy_data.get("status"),
            "conditions": policy_data.get("conditions", {}),
            "actions": policy_data.get("actions", {}),
            "metadata": policy_data.get("metadata", {}),
            "tags": policy_data.get("tags", []),
            "createdAt": policy_data.get("createdAt"),
            "updatedAt": policy_data.get("updatedAt"),
            "violations": [],
            "complianceStats": {
                "totalResources": 0,
                "compliantResources": 0,
                "nonCompliantResources": 0,
                "complianceRate": 0.0,
                "violationsBySeverity": [],
                "lastUpdated": datetime.utcnow().isoformat()
            }
        }
    
    def _format_violation(self, violation_data: Dict[str, Any], policy_data: Dict = None, 
                         resource_data: Dict = None) -> Dict[str, Any]:
        """Format violation data for GraphQL"""
        return {
            "id": violation_data.get("id"),
            "policyId": violation_data.get("policyId"),
            "resourceId": violation_data.get("resourceId"),
            "severity": violation_data.get("severity"),
            "status": violation_data.get("status"),
            "title": violation_data.get("title"),
            "description": violation_data.get("description"),
            "recommendation": violation_data.get("recommendation"),
            "detectedAt": violation_data.get("detectedAt"),
            "resolvedAt": violation_data.get("resolvedAt"),
            "assignee": violation_data.get("assignee"),
            "notes": violation_data.get("notes"),
            "falsePositive": violation_data.get("falsePositive", False),
            "riskScore": violation_data.get("riskScore", 0.0),
            "policy": self._format_policy(policy_data) if policy_data else None,
            "resource": self._format_resource(resource_data) if resource_data else None,
            "remediation": {
                "status": "PENDING",
                "action": None,
                "scheduledAt": None,
                "completedAt": None,
                "result": {},
                "error": None
            },
            "evidence": violation_data.get("evidence", {}),
            "context": violation_data.get("context", {})
        }
    
    def _calculate_path_risk(self, vulnerabilities: List[Dict]) -> float:
        """Calculate risk score for attack path"""
        if not vulnerabilities:
            return 0.0
        
        # Simple risk calculation based on vulnerability severity
        severity_weights = {"LOW": 1.0, "MEDIUM": 2.0, "HIGH": 3.0, "CRITICAL": 4.0}
        total_risk = 0.0
        
        for vuln in vulnerabilities:
            severity = vuln.get("severity", "LOW")
            weight = severity_weights.get(severity, 1.0)
            total_risk += weight
        
        # Normalize to 0-100 scale
        max_possible_risk = len(vulnerabilities) * 4.0
        return min((total_risk / max_possible_risk) * 100, 100.0)
    
    def _determine_compliance_status(self, score: float) -> str:
        """Determine compliance status from score"""
        if score >= 95:
            return "COMPLIANT"
        elif score >= 80:
            return "NON_COMPLIANT"
        else:
            return "PENDING"
    
    # Additional helper methods for compliance report generation
    async def _generate_compliance_summary(self, policyId: str, resourceId: str, 
                                         from_date: datetime, to_date: datetime) -> Dict[str, Any]:
        """Generate compliance summary"""
        # Implementation would query database for summary statistics
        return {
            "totalPolicies": 0,
            "activePolicies": 0,
            "totalResources": 0,
            "compliantResources": 0,
            "overallComplianceRate": 0.0,
            "criticalViolations": 0,
            "highViolations": 0
        }
    
    async def _generate_policy_breakdown(self, policyId: str, from_date: datetime, 
                                       to_date: datetime) -> List[Dict[str, Any]]:
        """Generate policy compliance breakdown"""
        # Implementation would query database for policy-specific compliance
        return []
    
    async def _generate_resource_breakdown(self, resourceId: str, from_date: datetime, 
                                         to_date: datetime) -> List[Dict[str, Any]]:
        """Generate resource compliance breakdown"""
        # Implementation would query database for resource-specific compliance
        return []
    
    async def _generate_violation_breakdown(self, from_date: datetime, 
                                          to_date: datetime) -> List[Dict[str, Any]]:
        """Generate violation trend breakdown"""
        # Implementation would query database for violation trends
        return []
    
    async def _generate_compliance_trends(self, from_date: datetime, 
                                         to_date: datetime) -> Dict[str, Any]:
        """Generate compliance trends"""
        # Implementation would query database for trend data
        return {
            "complianceRate": [],
            "violationCount": [],
            "riskScore": []
        }
    
    async def _generate_recommendations(self, policyId: str, resourceId: str) -> List[Dict[str, Any]]:
        """Generate compliance recommendations"""
        # Implementation would generate recommendations based on analysis
        return []
    
    async def _update_violation_status(self, id: str, status: str, notes: str) -> Dict[str, Any]:
        """Update violation status"""
        # Implementation would update violation in database
        return {}
