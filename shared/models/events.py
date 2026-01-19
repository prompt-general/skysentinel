from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class ResourceInfo:
    """Normalized resource information"""
    id: str
    type: str
    region: Optional[str] = None
    account: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


@dataclass
class PrincipalInfo:
    """Normalized principal information"""
    id: str
    type: str
    name: Optional[str] = None
    session_context: Optional[Dict[str, Any]] = None


@dataclass
class NormalizedEvent:
    """Normalized event schema across all cloud providers"""
    id: str
    cloud: str
    event_type: str
    event_time: datetime
    operation: str
    principal: PrincipalInfo
    resource: ResourceInfo
    request_parameters: Dict[str, Any]
    response_elements: Dict[str, Any]
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    error: Optional[str] = None
    status: str = "SUCCESS"
    raw_event: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'cloud': self.cloud,
            'event_type': self.event_type,
            'event_time': self.event_time.isoformat(),
            'operation': self.operation,
            'principal': {
                'id': self.principal.id,
                'type': self.principal.type,
                'name': self.principal.name,
                'session_context': self.principal.session_context
            },
            'resource': {
                'id': self.resource.id,
                'type': self.resource.type,
                'region': self.resource.region,
                'account': self.resource.account,
                'properties': self.resource.properties
            },
            'request_parameters': self.request_parameters,
            'response_elements': self.response_elements,
            'source_ip': self.source_ip,
            'user_agent': self.user_agent,
            'error': self.error,
            'status': self.status,
            'raw_event': self.raw_event
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NormalizedEvent':
        """Create from dictionary"""
        principal = PrincipalInfo(
            id=data['principal']['id'],
            type=data['principal']['type'],
            name=data['principal'].get('name'),
            session_context=data['principal'].get('session_context')
        )
        
        resource = ResourceInfo(
            id=data['resource']['id'],
            type=data['resource']['type'],
            region=data['resource'].get('region'),
            account=data['resource'].get('account'),
            properties=data['resource'].get('properties')
        )
        
        return cls(
            id=data['id'],
            cloud=data['cloud'],
            event_type=data['event_type'],
            event_time=datetime.fromisoformat(data['event_time']),
            operation=data['operation'],
            principal=principal,
            resource=resource,
            request_parameters=data['request_parameters'],
            response_elements=data['response_elements'],
            source_ip=data.get('source_ip'),
            user_agent=data.get('user_agent'),
            error=data.get('error'),
            status=data.get('status', 'SUCCESS'),
            raw_event=data.get('raw_event')
        )


@dataclass
class EventCollectorConfig:
    """Configuration for event collectors"""
    cloud_provider: str
    region: str
    credentials: Dict[str, Any]
    event_sources: list[str]
    batch_size: int = 100
    poll_interval: int = 30
    retry_attempts: int = 3
    enable_compression: bool = True
