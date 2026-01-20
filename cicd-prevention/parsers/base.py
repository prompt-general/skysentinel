"""
Unified IaC Parser Interface

This module provides a unified interface for parsing different IaC formats
and converting them to a standardized representation.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field, validator
import json
import yaml
from enum import Enum


class CloudProvider(str, Enum):
    """Supported cloud providers"""
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    KUBERNETES = "kubernetes"
    MULTI_CLOUD = "multi-cloud"


class ChangeType(str, Enum):
    """Types of resource changes"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    NO_CHANGE = "no-change"


class IaCResource(BaseModel):
    """Unified IaC resource model"""
    iac_id: str = Field(..., description="Resource address/identifier in IaC")
    resource_type: str = Field(..., description="Normalized resource type (aws:s3:bucket)")
    cloud_provider: CloudProvider = Field(..., description="Cloud provider")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Resource properties")
    tags: Dict[str, str] = Field(default_factory=dict, description="Resource tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    change_type: ChangeType = Field(ChangeType.CREATE, description="Type of change")
    source_file: Optional[str] = Field(None, description="Source file where resource was defined")
    line_number: Optional[int] = Field(None, description="Line number in source file")
    
    @validator('resource_type')
    def normalize_resource_type(cls, v):
        """Validate resource type format"""
        if not v or ':' not in v:
            raise ValueError("Resource type must be in format 'provider:service:resource'")
        return v
    
    @validator('cloud_provider')
    def validate_cloud_provider(cls, v):
        """Validate cloud provider"""
        if v not in CloudProvider.__members__.values():
            raise ValueError(f"Unsupported cloud provider: {v}")
        return v


class IaCDependency(BaseModel):
    """Unified IaC dependency model"""
    source_id: str = Field(..., description="Source resource ID")
    target_id: str = Field(..., description="Target resource ID")
    dependency_type: str = Field(..., description="Type of dependency")
    property_path: Optional[str] = Field(None, description="Property path reference")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IaCPlan(BaseModel):
    """Complete IaC plan representation"""
    id: str = Field(..., description="Plan identifier")
    source_type: str = Field(..., description="Source IaC type (terraform/cloudformation/arm/...)")
    source_content: Dict[str, Any] = Field(..., description="Original IaC content")
    resources: List[IaCResource] = Field(default_factory=list, description="Parsed resources")
    dependencies: List[IaCDependency] = Field(default_factory=list, description="Resource dependencies")
    timestamp: str = Field(..., description="Plan creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_encoders = {
            # Handle datetime serialization
            datetime: lambda v: v.isoformat()
        }


class IaCParser(ABC):
    """Base class for IaC parsers"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._get_logger()
    
    @abstractmethod
    def parse(self, content: Union[str, Dict]) -> IaCPlan:
        """Parse IaC content and return unified plan"""
        pass
    
    @abstractmethod
    def extract_resources(self, content: Dict) -> List[IaCResource]:
        """Extract resources from parsed content"""
        pass
    
    @abstractmethod
    def extract_dependencies(self, content: Dict) -> List[IaCDependency]:
        """Extract dependencies from parsed content"""
        pass
    
    @abstractmethod
    def detect_format(self, content: Union[str, Dict]) -> bool:
        """Detect if content matches this parser's format"""
        pass
    
    @staticmethod
    def normalize_resource_type(raw_type: str, provider: CloudProvider) -> str:
        """Normalize resource type to unified format"""
        type_normalizers = {
            CloudProvider.AWS: IaCParser._normalize_aws_type,
            CloudProvider.AZURE: IaCParser._normalize_azure_type,
            CloudProvider.GCP: IaCParser._normalize_gcp_type,
            CloudProvider.KUBERNETES: IaCParser._normalize_kubernetes_type
        }
        
        normalizer = type_normalizers.get(provider)
        if normalizer:
            return normalizer(raw_type)
        
        # Default normalization
        return raw_type.lower().replace('::', ':').replace('_', '').replace('-', '')
    
    @staticmethod
    def _normalize_aws_type(raw_type: str) -> str:
        """Normalize AWS resource type"""
        # Handle CloudFormation format: AWS::S3::Bucket
        if '::' in raw_type:
            parts = raw_type.split('::')
            if len(parts) >= 3 and parts[0] == 'AWS':
                return f"aws:{parts[1].lower()}:{parts[2].lower()}"
        
        # Handle Terraform format: aws_s3_bucket
        if '_' in raw_type:
            parts = raw_type.split('_')
            if len(parts) >= 3 and parts[0] == 'aws':
                return f"aws:{parts[1]}:{parts[2]}"
        
        return raw_type.lower()
    
    @staticmethod
    def _normalize_azure_type(raw_type: str) -> str:
        """Normalize Azure resource type"""
        # Handle ARM format: Microsoft.Storage/storageAccounts
        if '/' in raw_type:
            parts = raw_type.split('/')
            if len(parts) >= 2 and parts[0].startswith('Microsoft.'):
                service = parts[0].split('.')[1].lower()
                resource = parts[1].lower()
                return f"azure:{service}:{resource}"
        
        return raw_type.lower()
    
    @staticmethod
    def _normalize_gcp_type(raw_type: str) -> str:
        """Normalize GCP resource type"""
        # Handle GCP format: compute.googleapis.com/Instance
        if '/' in raw_type:
            parts = raw_type.split('/')
            if len(parts) >= 2:
                service = parts[0].split('.')[0].lower()
                resource = parts[1].lower()
                return f"gcp:{service}:{resource}"
        
        return raw_type.lower()
    
    @staticmethod
    def _normalize_kubernetes_type(raw_type: str) -> str:
        """Normalize Kubernetes resource type"""
        # Handle Kubernetes format: apps/v1/Deployment
        if '/' in raw_type:
            parts = raw_type.split('/')
            if len(parts) >= 2:
                group = parts[0].lower()
                resource = parts[1].lower()
                return f"kubernetes:{group}:{resource}"
        
        return raw_type.lower()
    
    def _get_logger(self):
        """Get parser-specific logger"""
        import logging
        return logging.getLogger(f"{self.__class__.__name__}")
    
    def _parse_content(self, content: Union[str, Dict]) -> Dict[str, Any]:
        """Parse content to dictionary"""
        if isinstance(content, dict):
            return content
        
        try:
            # Try JSON first
            return json.loads(content)
        except json.JSONDecodeError:
            try:
                # Try YAML
                return yaml.safe_load(content)
            except yaml.YAMLError:
                raise ValueError("Content is not valid JSON or YAML")
    
    def _generate_plan_id(self, source_type: str) -> str:
        """Generate unique plan ID"""
        import uuid
        import datetime
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{source_type}_plan_{timestamp}_{unique_id}"
    
    def _extract_tags(self, properties: Dict[str, Any]) -> Dict[str, str]:
        """Extract tags from resource properties"""
        tags = {}
        
        # Handle different tag formats
        if 'Tags' in properties:
            tag_list = properties['Tags']
            if isinstance(tag_list, list):
                for tag in tag_list:
                    if isinstance(tag, dict):
                        key = tag.get('Key', tag.get('key', ''))
                        value = tag.get('Value', tag.get('value', ''))
                        if key and value:
                            tags[key] = value
            elif isinstance(tag_list, dict):
                tags.update(tag_list)
        
        elif 'tags' in properties:
            tags.update(properties['tags'])
        
        return tags
    
    def _determine_change_type(self, resource_data: Dict[str, Any]) -> ChangeType:
        """Determine the type of change for a resource"""
        # Check for explicit change indicators
        if 'change_type' in resource_data:
            change_type = resource_data['change_type'].lower()
            if change_type in ChangeType.__members__.values():
                return ChangeType(change_type)
        
        # Infer from resource data
        if 'delete' in str(resource_data).lower():
            return ChangeType.DELETE
        elif 'update' in str(resource_data).lower():
            return ChangeType.UPDATE
        elif 'create' in str(resource_data).lower():
            return ChangeType.CREATE
        else:
            return ChangeType.NO_CHANGE


class IaCParserFactory:
    """Factory for creating IaC parsers"""
    
    _parsers = {}
    
    @classmethod
    def register_parser(cls, iac_type: str, parser_class):
        """Register a parser for an IaC type"""
        cls._parsers[iac_type.lower()] = parser_class
    
    @classmethod
    def create_parser(cls, iac_type: str, config: Optional[Dict[str, Any]] = None) -> IaCParser:
        """Create parser instance for IaC type"""
        parser_class = cls._parsers.get(iac_type.lower())
        if not parser_class:
            raise ValueError(f"No parser registered for IaC type: {iac_type}")
        
        return parser_class(config)
    
    @classmethod
    def detect_iac_type(cls, content: Union[str, Dict]) -> Optional[str]:
        """Auto-detect IaC type from content"""
        if isinstance(content, str):
            # Convert to dict for detection
            try:
                content_dict = json.loads(content)
            except json.JSONDecodeError:
                try:
                    content_dict = yaml.safe_load(content)
                except yaml.YAMLError:
                    return None
        else:
            content_dict = content
        
        # Try each registered parser
        for iac_type, parser_class in cls._parsers.items():
            parser = parser_class()
            if parser.detect_format(content_dict):
                return iac_type
        
        return None
    
    @classmethod
    def get_supported_types(cls) -> List[str]:
        """Get list of supported IaC types"""
        return list(cls._parsers.keys())


# Utility functions
def create_unified_plan(iac_content: Union[str, Dict], 
                      iac_type: Optional[str] = None,
                      config: Optional[Dict[str, Any]] = None) -> IaCPlan:
    """Create unified IaC plan from content"""
    
    # Auto-detect IaC type if not provided
    if not iac_type:
        iac_type = IaCParserFactory.detect_iac_type(iac_content)
        if not iac_type:
            raise ValueError("Could not detect IaC type from content")
    
    # Create parser and parse
    parser = IaCParserFactory.create_parser(iac_type, config)
    plan = parser.parse(iac_content)
    
    return plan


def normalize_all_resources(plans: List[IaCPlan]) -> List[IaCResource]:
    """Normalize resources from multiple plans"""
    all_resources = []
    
    for plan in plans:
        all_resources.extend(plan.resources)
    
    return all_resources


def extract_dependencies(plans: List[IaCPlan]) -> List[IaCDependency]:
    """Extract all dependencies from multiple plans"""
    all_dependencies = []
    
    for plan in plans:
        all_dependencies.extend(plan.dependencies)
    
    return all_dependencies
