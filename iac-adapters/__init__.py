"""
SkySentinel IaC Adapters

This package provides adapters for various Infrastructure as Code (IaC) tools,
enabling unified parsing and analysis of cloud infrastructure configurations.

Supported IaC Tools:
- Terraform
- AWS CloudFormation
- Azure ARM Templates
- Kubernetes YAML/JSON
- Helm Charts
- Pulumi
- Ansible

Usage:
    from iac_adapters import IaCProcessor, IaCType
    
    processor = IaCProcessor()
    plan = processor.process_plan(terraform_plan_json, IaCType.TERRAFORM)
    
    # Auto-detect IaC type
    plan = processor.process_plan(iac_content)
"""

from .base import (
    IaCAdapter,
    IaCType,
    IaCPlan,
    IaCResource,
    IaCDependency,
    IaCValidationResult,
    ResourceType,
    CloudProvider,
    IaCAdapterFactory,
    IaCProcessor,
    create_iac_adapter
)

from .terraform import TerraformAdapter
from .cloudformation import CloudFormationAdapter
from .kubernetes import KubernetesAdapter
from .arm import ARMAdapter

__version__ = "1.0.0"
__author__ = "SkySentinel Team"

# Export main classes
__all__ = [
    # Core classes
    'IaCAdapter',
    'IaCType',
    'IaCPlan',
    'IaCResource',
    'IaCDependency',
    'IaCValidationResult',
    'ResourceType',
    'CloudProvider',
    'IaCAdapterFactory',
    'IaCProcessor',
    'create_iac_adapter',
    
    # Adapters
    'TerraformAdapter',
    'CloudFormationAdapter',
    'KubernetesAdapter',
    'ARMAdapter',
    
    # Enums
    'IaCType',
    'ResourceType',
    'CloudProvider',
]

# Auto-register all adapters
def _register_all_adapters():
    """Auto-register all available adapters"""
    from .base import IaCAdapterFactory
    from .terraform import TerraformAdapter
    from .cloudformation import CloudFormationAdapter
    from .kubernetes import KubernetesAdapter
    from .arm import ARMAdapter
    
    IaCAdapterFactory.register_adapter(IaCType.TERRAFORM, TerraformAdapter)
    IaCAdapterFactory.register_adapter(IaCType.CLOUDFORMATION, CloudFormationAdapter)
    IaCAdapterFactory.register_adapter(IaCType.KUBERNETES, KubernetesAdapter)
    IaCAdapterFactory.register_adapter(IaCType.ARM_TEMPLATE, ARMAdapter)

# Register adapters on import
_register_all_adapters()
