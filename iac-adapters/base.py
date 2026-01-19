from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime

from shared.models.events import ResourceReference, CloudProvider


class IaCType(Enum):
    """Supported IaC tool types"""
    TERRAFORM = "terraform"
    CLOUDFORMATION = "cloudformation"
    ARM_TEMPLATE = "arm_template"
    PULUMI = "pulumi"
    ANSIBLE = "ansible"
    KUBERNETES = "kubernetes"
    HELM = "helm"


class ResourceType(Enum):
    """Standardized resource types across clouds"""
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    DATABASE = "database"
    SECURITY = "security"
    MONITORING = "monitoring"
    IDENTITY = "identity"
    CONTAINER = "container"
    SERVERLESS = "serverless"
    MESSAGING = "messaging"
    ANALYTICS = "analytics"
    AI_ML = "ai_ml"
    IOT = "iot"
    BLOCKCHAIN = "blockchain"
    OTHER = "other"


@dataclass
class IaCResource:
    """Unified IaC resource representation"""
    id: str
    type: str
    name: str
    provider: CloudProvider
    resource_category: ResourceType
    properties: Dict[str, Any] = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    change_type: str = "create"  # create, update, delete, read
    plan_id: Optional[str] = None


@dataclass
class IaCPlan:
    """Unified IaC plan representation"""
    id: str
    iac_type: IaCType
    version: str
    created_at: datetime
    resources: List[IaCResource] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_files: List[str] = field(default_factory=list)
    workspace: Optional[str] = None
    environment: Optional[str] = None


@dataclass
class IaCDependency:
    """Resource dependency representation"""
    source_id: str
    target_id: str
    dependency_type: str  # explicit, implicit, reference
    property_path: Optional[str] = None
    condition: Optional[str] = None


@dataclass
class IaCValidationResult:
    """Validation result for IaC content"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class IaCAdapter(ABC):
    """Abstract base class for IaC adapters"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._resource_type_mapping = self._get_resource_type_mapping()
        self._provider_mapping = self._get_provider_mapping()
    
    @abstractmethod
    def get_iac_type(self) -> IaCType:
        """Return the IaC type this adapter supports"""
        pass
    
    @abstractmethod
    def parse_plan(self, plan_content: Union[str, Dict]) -> IaCPlan:
        """Parse IaC plan and return unified representation"""
        pass
    
    @abstractmethod
    def parse_configuration(self, config_content: Union[str, Dict]) -> IaCPlan:
        """Parse IaC configuration and return unified representation"""
        pass
    
    @abstractmethod
    def normalize_resource(self, raw_resource: Dict) -> IaCResource:
        """Normalize a resource from IaC to unified model"""
        pass
    
    @abstractmethod
    def extract_dependencies(self, iac_content: Dict) -> List[IaCDependency]:
        """Extract dependencies between resources"""
        pass
    
    @abstractmethod
    def validate_syntax(self, content: Union[str, Dict]) -> IaCValidationResult:
        """Validate IaC syntax and structure"""
        pass
    
    def parse(self, iac_content: Dict) -> List[ResourceReference]:
        """Legacy method for backward compatibility"""
        plan = self.parse_plan(iac_content)
        return [self._to_resource_reference(resource) for resource in plan.resources]
    
    def _to_resource_reference(self, iac_resource: IaCResource) -> ResourceReference:
        """Convert IaCResource to ResourceReference"""
        return ResourceReference(
            id=iac_resource.id,
            type=iac_resource.type,
            region=iac_resource.properties.get('region'),
            account=iac_resource.properties.get('account'),
            name=iac_resource.name,
            properties=iac_resource.properties,
            tags=iac_resource.properties.get('tags', {}),
            metadata={
                'iac_type': self.get_iac_type().value,
                'resource_category': iac_resource.resource_category.value,
                'change_type': iac_resource.change_type,
                'dependencies': list(iac_resource.dependencies),
                'source_file': iac_resource.source_file,
                'line_number': iac_resource.line_number,
                **iac_resource.metadata
            }
        )
    
    def _get_resource_type_mapping(self) -> Dict[str, ResourceType]:
        """Get mapping from IaC-specific resource types to standardized types"""
        return {}
    
    def _get_provider_mapping(self) -> Dict[str, CloudProvider]:
        """Get mapping from IaC-specific providers to CloudProvider enum"""
        return {}
    
    def _normalize_resource_type(self, resource_type: str) -> ResourceType:
        """Normalize resource type to standardized enum"""
        return self._resource_type_mapping.get(resource_type, ResourceType.OTHER)
    
    def _normalize_provider(self, provider: str) -> CloudProvider:
        """Normalize provider to CloudProvider enum"""
        return self._provider_mapping.get(provider, CloudProvider.AWS)
    
    def _extract_cloud_provider(self, resource: Dict) -> CloudProvider:
        """Extract cloud provider from resource"""
        # Check provider field
        if 'provider' in resource:
            provider_name = resource['provider']
            if isinstance(provider_name, dict):
                provider_name = provider_name.get('name', '')
            return self._normalize_provider(provider_name)
        
        # Check resource type prefix
        resource_type = resource.get('type', '')
        if resource_type.startswith('aws:'):
            return CloudProvider.AWS
        elif resource_type.startswith('azure:'):
            return CloudProvider.AZURE
        elif resource_type.startswith('gcp:'):
            return CloudProvider.GCP
        elif resource_type.startswith('kubernetes:'):
            return CloudProvider.KUBERNETES
        
        # Default to AWS
        return CloudProvider.AWS
    
    def _extract_resource_id(self, resource: Dict) -> str:
        """Extract resource ID from IaC resource"""
        # Try common ID fields
        for id_field in ['id', 'resource_id', 'arn', 'name', 'full_name']:
            if id_field in resource and resource[id_field]:
                return str(resource[id_field])
        
        # Generate ID from type and name
        resource_type = resource.get('type', 'unknown')
        resource_name = resource.get('name', 'unknown')
        return f"{resource_type}:{resource_name}"
    
    def _extract_resource_name(self, resource: Dict) -> str:
        """Extract resource name from IaC resource"""
        for name_field in ['name', 'display_name', 'title', 'resource_name']:
            if name_field in resource and resource[name_field]:
                return str(resource[name_field])
        
        return self._extract_resource_id(resource)
    
    def _get_change_type(self, resource: Dict) -> str:
        """Extract change type from resource"""
        # Check for change indicators
        if resource.get('delete', False):
            return "delete"
        elif resource.get('create', False) or resource.get('new', False):
            return "create"
        elif resource.get('update', False) or resource.get('modified', False):
            return "update"
        elif resource.get('read', False) or resource.get('no_change', False):
            return "read"
        
        return "create"  # Default
    
    def _validate_required_fields(self, resource: Dict) -> List[str]:
        """Validate required fields for resource"""
        errors = []
        
        if not resource.get('type'):
            errors.append("Resource type is required")
        
        if not resource.get('name') and not resource.get('id'):
            errors.append("Resource name or ID is required")
        
        return errors
    
    def _sanitize_properties(self, properties: Dict) -> Dict[str, Any]:
        """Sanitize resource properties for security and size"""
        if not isinstance(properties, dict):
            return {}
        
        sanitized = {}
        sensitive_keys = {
            'password', 'secret', 'key', 'token', 'credential',
            'private_key', 'certificate', 'api_key'
        }
        
        for key, value in properties.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, (str, int, float, bool, list, dict)):
                # Limit size of large values
                if isinstance(value, str) and len(value) > 1000:
                    sanitized[key] = value[:1000] + '...[TRUNCATED]'
                else:
                    sanitized[key] = value
            else:
                sanitized[key] = str(value)
        
        return sanitized


class IaCAdapterFactory:
    """Factory for creating IaC adapters"""
    
    _adapters: Dict[IaCType, type] = {}
    
    @classmethod
    def register_adapter(cls, iac_type: IaCType, adapter_class: type):
        """Register an adapter for a specific IaC type"""
        cls._adapters[iac_type] = adapter_class
    
    @classmethod
    def create_adapter(cls, iac_type: IaCType, config: Optional[Dict[str, Any]] = None) -> IaCAdapter:
        """Create an adapter for the specified IaC type"""
        if iac_type not in cls._adapters:
            raise ValueError(f"No adapter registered for IaC type: {iac_type}")
        
        adapter_class = cls._adapters[iac_type]
        return adapter_class(config)
    
    @classmethod
    def get_supported_types(cls) -> List[IaCType]:
        """Get list of supported IaC types"""
        return list(cls._adapters.keys())
    
    @classmethod
    def auto_detect_iac_type(cls, content: Union[str, Dict]) -> Optional[IaCType]:
        """Auto-detect IaC type from content"""
        if isinstance(content, str):
            # Check for file patterns
            if 'resource "' in content and 'provider "' in content:
                return IaCType.TERRAFORM
            elif 'AWSTemplateFormatVersion' in content or 'Resources:' in content:
                return IaCType.CLOUDFORMATION
            elif '$schema' in content and 'https://schema.management.azure.com' in content:
                return IaCType.ARM_TEMPLATE
            elif 'apiVersion' in content and 'kind:' in content:
                return IaCType.KUBERNETES
            elif 'apiVersion' in content and 'runtime:' in content:
                return IaCType.HELM
        elif isinstance(content, dict):
            # Check for structure patterns
            if 'resource' in content and 'provider' in content:
                return IaCType.TERRAFORM
            elif 'Resources' in content and 'AWSTemplateFormatVersion' in content:
                return IaCType.CLOUDFORMATION
            elif '$schema' in content and 'resources' in content:
                return IaCType.ARM_TEMPLATE
            elif 'apiVersion' in content and 'kind' in content:
                return IaCType.KUBERNETES
        
        return None


class IaCProcessor:
    """High-level processor for IaC content"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def process_plan(self, content: Union[str, Dict], iac_type: Optional[IaCType] = None) -> IaCPlan:
        """Process IaC plan and return unified representation"""
        # Auto-detect IaC type if not provided
        if iac_type is None:
            iac_type = IaCAdapterFactory.auto_detect_iac_type(content)
            if iac_type is None:
                raise ValueError("Could not auto-detect IaC type")
        
        # Create adapter
        adapter = IaCAdapterFactory.create_adapter(iac_type, self.config)
        
        # Parse plan
        plan = adapter.parse_plan(content)
        
        # Post-process plan
        self._post_process_plan(plan)
        
        return plan
    
    def _post_process_plan(self, plan: IaCPlan):
        """Post-process plan to add additional metadata and validation"""
        # Add resource count by type
        resource_counts = {}
        for resource in plan.resources:
            category = resource.resource_category
            resource_counts[category] = resource_counts.get(category, 0) + 1
        
        plan.metadata['resource_counts'] = {
            category.value: count for category, count in resource_counts.items()
        }
        
        # Add dependency graph metrics
        total_dependencies = sum(len(resource.dependencies) for resource in plan.resources)
        plan.metadata['total_dependencies'] = total_dependencies
        plan.metadata['avg_dependencies_per_resource'] = (
            total_dependencies / len(plan.resources) if plan.resources else 0
        )
        
        # Validate resources
        validation_errors = []
        for resource in plan.resources:
            if not resource.id:
                validation_errors.append(f"Resource missing ID: {resource.name}")
            if not resource.type:
                validation_errors.append(f"Resource missing type: {resource.name}")
        
        if validation_errors:
            plan.metadata['validation_errors'] = validation_errors
            self.logger.warning(f"Plan validation errors: {validation_errors}")


# Utility functions
def create_iac_adapter(iac_type: str, config: Optional[Dict[str, Any]] = None) -> IaCAdapter:
    """Utility function to create IaC adapter from string"""
    try:
        iac_enum = IaCType(iac_type.lower())
        return IaCAdapterFactory.create_adapter(iac_enum, config)
    except ValueError:
        raise ValueError(f"Unsupported IaC type: {iac_type}. Supported types: {[t.value for t in IaCType.get_supported_types()]}")
