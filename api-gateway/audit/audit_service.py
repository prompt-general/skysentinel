import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from neo4j import GraphDatabase
from pydantic import BaseModel
from fastapi import Request, Response

logger = logging.getLogger(__name__)

class AuditEvent(BaseModel):
    id: str
    timestamp: datetime
    event_type: str
    tenant_id: str
    user_id: Optional[str]
    user_email: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Dict[str, Any]
    source_ip: Optional[str]
    user_agent: Optional[str]
    status: str  # success, failure
    error_message: Optional[str]

class User(BaseModel):
    id: str
    email: str

class AuditService:
    """Service for logging audit events to Neo4j"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
    
    def log_event(self, event: AuditEvent):
        """Log audit event to Neo4j"""
        query = """
        CREATE (a:AuditEvent {
            id: $id,
            timestamp: datetime($timestamp),
            event_type: $event_type,
            tenant_id: $tenant_id,
            user_id: $user_id,
            user_email: $user_email,
            action: $action,
            resource_type: $resource_type,
            resource_id: $resource_id,
            details: $details,
            source_ip: $source_ip,
            user_agent: $user_agent,
            status: $status,
            error_message: $error_message
        })
        WITH a
        MATCH (t:Tenant {id: $tenant_id})
        MERGE (t)-[:HAS_AUDIT_EVENT]->(a)
        
        WITH a, $user_id as user_id
        WHERE user_id IS NOT NULL
        MATCH (u:User {id: user_id})
        MERGE (u)-[:PERFORMED]->(a)
        
        RETURN a
        """
        
        try:
            with self.driver.session() as session:
                session.run(query, **event.dict())
        except Exception as e:
            # Fallback to file logging if Neo4j fails
            self._fallback_log(event, str(e))
    
    def get_events(self, tenant_id: str, filters: Dict = None, limit: int = 100) -> List[AuditEvent]:
        """Get audit events for a tenant"""
        query = """
        MATCH (a:AuditEvent {tenant_id: $tenant_id})
        WHERE 1=1
        """
        
        parameters = {"tenant_id": tenant_id, "limit": limit}
        
        # Add filters
        conditions = []
        if filters:
            if filters.get("user_id"):
                conditions.append("a.user_id = $user_id")
                parameters["user_id"] = filters["user_id"]
            
            if filters.get("event_type"):
                conditions.append("a.event_type = $event_type")
                parameters["event_type"] = filters["event_type"]
            
            if filters.get("start_date"):
                conditions.append("a.timestamp >= datetime($start_date)")
                parameters["start_date"] = filters["start_date"]
            
            if filters.get("end_date"):
                conditions.append("a.timestamp <= datetime($end_date)")
                parameters["end_date"] = filters["end_date"]
            
            if filters.get("action"):
                conditions.append("a.action = $action")
                parameters["action"] = filters["action"]
        
        if conditions:
            query += " AND " + " AND ".join(conditions)
        
        query += """
        RETURN a
        ORDER BY a.timestamp DESC
        LIMIT $limit
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters)
                events = []
                for record in result:
                    event_data = record["a"]
                    # Convert Neo4j datetime to Python datetime
                    if isinstance(event_data.get("timestamp"), dict):
                        from datetime import datetime
                        event_data["timestamp"] = datetime.fromisoformat(event_data["timestamp"].replace("Z", "+00:00"))
                    events.append(AuditEvent(**event_data))
                return events
        except Exception as e:
            logger.error(f"Failed to get audit events: {e}")
            return []
    
    def log_api_call(self, request: Request, response: Response, user: Optional[User] = None):
        """Log API call as audit event"""
        event = AuditEvent(
            id=f"audit_{datetime.utcnow().timestamp()}",
            timestamp=datetime.utcnow(),
            event_type="api_call",
            tenant_id=getattr(request.state, 'tenant_id', 'unknown'),
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            action=f"{request.method} {request.url.path}",
            resource_type="api_endpoint",
            resource_id=request.url.path,
            details={
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "status_code": response.status_code,
                "response_time": float(response.headers.get("X-Process-Time", 0))
            },
            source_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            status="success" if response.status_code < 400 else "failure",
            error_message=None if response.status_code < 400 else "API call failed"
        )
        
        self.log_event(event)
    
    def log_policy_violation(self, violation: Dict, user: Optional[User] = None):
        """Log policy violation"""
        event = AuditEvent(
            id=f"audit_{datetime.utcnow().timestamp()}",
            timestamp=datetime.utcnow(),
            event_type="policy_violation",
            tenant_id=violation.get("tenant_id", "unknown"),
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            action="violation_detected",
            resource_type=violation.get("resource_type"),
            resource_id=violation.get("resource_id"),
            details={
                "policy_name": violation.get("policy_name"),
                "severity": violation.get("severity"),
                "description": violation.get("description"),
                "remediation": violation.get("remediation_actions", [])
            },
            source_ip=None,
            user_agent=None,
            status="success",
            error_message=None
        )
        
        self.log_event(event)
    
    def log_security_event(self, event_type: str, details: Dict, user: Optional[User] = None):
        """Log security-related event"""
        event = AuditEvent(
            id=f"audit_{datetime.utcnow().timestamp()}",
            timestamp=datetime.utcnow(),
            event_type=event_type,
            tenant_id=details.get("tenant_id", "unknown"),
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            action=event_type,
            resource_type=details.get("resource_type", "system"),
            resource_id=details.get("resource_id"),
            details=details,
            source_ip=details.get("source_ip"),
            user_agent=details.get("user_agent"),
            status="success",
            error_message=None
        )
        
        self.log_event(event)
    
    def _fallback_log(self, event: AuditEvent, error: str):
        """Fallback logging to file"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "ERROR",
            "service": "audit_service",
            "message": "Failed to log to Neo4j",
            "error": error,
            "event": event.dict()
        }
        
        # Write to file (use cross-platform path)
        import os
        log_dir = os.path.join(os.path.expanduser("~"), "logs", "skysentinel")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "audit_fallback.log")
        
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as file_error:
            logger.error(f"Failed to write fallback log: {file_error}")
        
        logger.error(f"Failed to log audit event: {error}")
