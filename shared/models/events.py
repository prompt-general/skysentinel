from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class CloudProvider(str, Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class Principal(BaseModel):
    id: str
    type: str
    arn: Optional[str] = None
    name: Optional[str] = None


class ResourceReference(BaseModel):
    id: str
    type: str
    region: Optional[str] = None
    account: Optional[str] = None
    name: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)


class NormalizedEvent(BaseModel):
    id: str
    cloud: CloudProvider
    event_type: str
    event_time: datetime
    operation: str
    principal: Principal
    resource: ResourceReference
    request_parameters: Dict[str, Any]
    response_elements: Dict[str, Any]
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    raw_event: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EventCollectorConfig(BaseModel):
    """Configuration for event collectors"""
    cloud_provider: CloudProvider
    region: str
    credentials: Dict[str, Any]
    event_sources: List[str]
    batch_size: int = 100
    poll_interval: int = 30
    retry_attempts: int = 3
    enable_compression: bool = True
