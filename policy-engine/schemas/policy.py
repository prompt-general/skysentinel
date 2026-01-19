from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime
import re


class Severity(str, Enum):
    """Policy severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class CloudProvider(str, Enum):
    """Supported cloud providers"""
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    ALL = "all"


class EnforcementMode(str, Enum):
    """Policy enforcement modes"""
    INLINE_DENY = "inline-deny"
    POST_EVENT = "post-event"
    SCHEDULED = "scheduled"
    PRE_DEPLOYMENT = "pre-deployment"
    AUDIT_ONLY = "audit-only"


class ActionType(str, Enum):
    """Available policy actions"""
    NOTIFY = "notify"
    BLOCK = "block"
    TAG = "tag"
    DISABLE = "disable"
    DELETE = "delete"
    STOP = "stop"
    QUARANTINE = "quarantine"
    ESCALATE = "escalate"


class ConditionOperator(str, Enum):
    """Condition operators"""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_EQUAL = "ge"
    LESS_THAN = "lt"
    LESS_EQUAL = "le"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    NOT_IN = "not_in"
    REGEX = "regex"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class ResourceSelector(BaseModel):
    """Selector for resources to evaluate"""
    cloud: Optional[Union[CloudProvider, str]] = None
    resource_types: List[str] = Field(default_factory=list)
    tags: Optional[Dict[str, str]] = None
    region: Optional[str] = None
    account_ids: Optional[List[str]] = None
    subscription_ids: Optional[List[str]] = None
    project_ids: Optional[List[str]] = None
    exclude_resource_types: List[str] = Field(default_factory=list)
    exclude_tags: Optional[Dict[str, str]] = None
    
    @validator('resource_types', pre=True)
    def normalize_resource_types(cls, v):
        """Normalize resource type formats"""
        if isinstance(v, str):
            return [v]
        return v
    
    @validator('cloud', pre=True)
    def normalize_cloud(cls, v):
        """Normalize cloud provider values"""
        if isinstance(v, str):
            return v.lower()
        return v
    
    @validator('account_ids', pre=True)
    def normalize_account_ids(cls, v):
        """Normalize account IDs"""
        if isinstance(v, str):
            return [v]
        return v


class ConditionField(BaseModel):
    """Individual condition field"""
    field: str
    operator: ConditionOperator
    value: Optional[Any] = None
    case_sensitive: bool = True
    
    @validator('value')
    def validate_condition_value(cls, v, values):
        """Validate condition value based on operator"""
        operator = values.get('operator')
        
        if operator in [ConditionOperator.IN, ConditionOperator.NOT_IN]:
            if not isinstance(v, (list, tuple)):
                raise ValueError(f"Operator {operator} requires a list value")
        elif operator in [ConditionOperator.EXISTS, ConditionOperator.NOT_EXISTS]:
            if v is not None:
                raise ValueError(f"Operator {operator} should not have a value")
        elif v is None:
            raise ValueError(f"Operator {operator} requires a value")
        
        return v


class LogicalOperator(str, Enum):
    """Logical operators for combining conditions"""
    AND = "and"
    OR = "or"
    NOT = "not"


class Condition(BaseModel):
    """Policy condition definition"""
    any: Optional[List['Condition']] = None  # OR logic
    all: Optional[List['Condition']] = None  # AND logic
    not_: Optional['Condition'] = Field(None, alias="not")
    field: Optional[ConditionField] = None
    
    class Config:
        allow_population_by_field_name = True


# Resolve forward references
Condition.update_forward_refs()


class GraphPath(BaseModel):
    """Graph traversal path definition"""
    from_: Optional[str] = Field(None, alias="from")
    to: Optional[str] = None
    via: Optional[List[str]] = None
    direction: str = Field(default="outgoing", regex="^(incoming|outgoing|both)$")
    
    class Config:
        allow_population_by_field_name = True


class GraphCondition(BaseModel):
    """Graph traversal condition"""
    path: Optional[GraphPath] = None
    where: Optional[Union[Condition, Dict[str, Any]]] = None
    max_depth: int = Field(default=10, ge=1, le=50)
    timeout: Optional[int] = Field(default=30, ge=1, le=300)  # seconds
    
    @validator('where', pre=True)
    def normalize_where_condition(cls, v):
        """Convert dict to Condition object if needed"""
        if isinstance(v, dict) and 'field' not in v and 'any' not in v and 'all' not in v:
            # Simple field condition format
            return Condition(field=ConditionField(**v))
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "path": {
                    "from": "internet",
                    "to": "resource",
                    "via": ["load_balancer", "security_group"]
                },
                "where": {
                    "all": [
                        {
                            "field": {
                                "field": "resource.tags.env",
                                "operator": "eq",
                                "value": "prod"
                            }
                        },
                        {
                            "field": {
                                "field": "resource.type",
                                "operator": "contains",
                                "value": "aws:rds:"
                            }
                        }
                    ]
                },
                "max_depth": 5
            }
        }


class NotificationChannel(BaseModel):
    """Notification channel configuration"""
    type: str = Field(regex="^(slack|email|webhook|teams|pagerduty)$")
    target: str
    template: Optional[str] = None
    severity_threshold: Optional[Severity] = None
    
    @validator('target')
    def validate_target(cls, v, values):
        """Validate target based on channel type"""
        channel_type = values.get('type')
        
        if channel_type == 'email':
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
                raise ValueError("Invalid email address")
        elif channel_type == 'webhook':
            if not v.startswith(('http://', 'https://')):
                raise ValueError("Webhook URL must start with http:// or https://")
        
        return v


class Action(BaseModel):
    """Action to take on policy violation"""
    type: ActionType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    delay: Optional[int] = Field(None, ge=0, le=86400)  # seconds
    retry_count: int = Field(default=0, ge=0, le=10)
    timeout: Optional[int] = Field(None, ge=1, le=3600)  # seconds
    
    @validator('parameters')
    def validate_action_params(cls, v, values):
        """Validate action-specific parameters"""
        action_type = values.get('type')
        
        if action_type == ActionType.NOTIFY:
            if 'channels' not in v and 'channel' not in v:
                raise ValueError("Notify action requires channels or channel parameter")
        elif action_type == ActionType.TAG:
            if 'tags' not in v or not isinstance(v['tags'], dict):
                raise ValueError("Tag action requires tags dictionary")
        elif action_type == ActionType.BLOCK:
            if 'message' not in v:
                raise ValueError("Block action requires message parameter")
        elif action_type == ActionType.QUARANTINE:
            if 'duration' not in v:
                raise ValueError("Quarantine action requires duration parameter")
        
        return v


class EnforcementConfig(BaseModel):
    """Enforcement configuration for different contexts"""
    mode: EnforcementMode
    dry_run: bool = False
    timeout: Optional[int] = Field(None, ge=1, le=3600)
    retry_count: int = Field(default=3, ge=0, le=10)
    escalation: Optional[Dict[str, Any]] = None


class PolicyMetadata(BaseModel):
    """Policy metadata"""
    category: Optional[str] = None
    compliance_framework: Optional[List[str]] = None
    tags: Optional[Dict[str, str]] = None
    owner: Optional[str] = None
    team: Optional[str] = None
    review_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None


class Policy(BaseModel):
    """Main policy definition"""
    id: str = Field(default_factory=lambda: f"policy-{int(datetime.utcnow().timestamp())}")
    name: str = Field(..., min_length=1, max_length=200)
    version: str = Field(default="1.0", regex=r'^\d+\.\d+(\.\d+)?$')
    description: Optional[str] = Field(None, max_length=1000)
    severity: Severity = Severity.MEDIUM
    
    # Resource selection
    resources: ResourceSelector
    
    # Conditions
    condition: Union[Condition, GraphCondition, Dict[str, Any]]
    
    # Enforcement settings
    enforcement: Dict[str, EnforcementConfig] = Field(
        default_factory=lambda: {
            "runtime": EnforcementConfig(mode=EnforcementMode.POST_EVENT),
            "cicd": EnforcementConfig(mode=EnforcementMode.BLOCK)
        }
    )
    
    # Actions
    actions: List[Action] = Field(default_factory=list)
    
    # Metadata
    enabled: bool = True
    metadata: Optional[PolicyMetadata] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    class Config:
        validate_assignment = True
        use_enum_values = True
        schema_extra = {
            "example": {
                "name": "Block Public S3 Buckets",
                "description": "Prevent creation of publicly accessible S3 buckets",
                "severity": "high",
                "resources": {
                    "cloud": "aws",
                    "resource_types": ["aws:s3:bucket"]
                },
                "condition": {
                    "all": [
                        {
                            "field": {
                                "field": "resource.public_read",
                                "operator": "eq",
                                "value": True
                            }
                        }
                    ]
                },
                "enforcement": {
                    "runtime": {
                        "mode": "post-event",
                        "dry_run": False
                    },
                    "cicd": {
                        "mode": "block"
                    }
                },
                "actions": [
                    {
                        "type": "notify",
                        "parameters": {
                            "channels": [
                                {
                                    "type": "slack",
                                    "target": "#security-alerts"
                                }
                            ]
                        }
                    },
                    {
                        "type": "tag",
                        "parameters": {
                            "tags": {
                                "compliance": "violation",
                                "policy": "public-s3-block"
                            }
                        }
                    }
                ]
            }
        }
    
    @validator('condition', pre=True)
    def normalize_condition(cls, v):
        """Convert dict to appropriate condition type"""
        if isinstance(v, dict):
            if 'path' in v or 'max_depth' in v:
                return GraphCondition(**v)
            elif 'field' in v or 'any' in v or 'all' in v or 'not' in v:
                return Condition(**v)
        
        return v
    
    @validator('enforcement')
    def validate_enforcement(cls, v):
        """Validate enforcement configuration"""
        allowed_modes = [mode.value for mode in EnforcementMode]
        
        for context, config in v.items():
            if not isinstance(config, EnforcementConfig):
                if isinstance(config, dict):
                    mode = config.get('mode')
                    if mode not in allowed_modes:
                        raise ValueError(f"Invalid enforcement mode: {mode}")
                else:
                    raise ValueError(f"Invalid enforcement config for {context}")
        
        return v
    
    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.utcnow()
    
    def is_expired(self) -> bool:
        """Check if policy has expired"""
        if self.metadata and self.metadata.expiration_date:
            return datetime.utcnow() > self.metadata.expiration_date
        return False
    
    def needs_review(self) -> bool:
        """Check if policy needs review"""
        if self.metadata and self.metadata.review_date:
            return datetime.utcnow() > self.metadata.review_date
        return False


class PolicySet(BaseModel):
    """Collection of related policies"""
    id: str = Field(default_factory=lambda: f"policyset-{int(datetime.utcnow().timestamp())}")
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    policies: List[str] = Field(default_factory=list)  # Policy IDs
    priority: int = Field(default=100, ge=1, le=1000)
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "name": "CIS AWS Foundations",
                "description": "CIS AWS Foundations Benchmark policies",
                "policies": ["policy-1", "policy-2", "policy-3"],
                "priority": 100
            }
        }
    
    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.utcnow()
