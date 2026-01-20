"""
Unified IaC Parsers Package

This package provides parsers for different Infrastructure as Code formats
and converts them to a unified representation for SkySentinel.
"""

from .base import (
    IaCParser,
    IaCPlan,
    IaCResource,
    IaCDependency,
    IaCParserFactory,
    CloudProvider,
    ChangeType,
    create_unified_plan,
    normalize_all_resources,
    extract_dependencies
)

from .terraform import TerraformParser
from .cloudformation import CloudFormationParser
from .arm import ARMParser

# Auto-register parsers
IaCParserFactory.register_parser('terraform', TerraformParser)
IaCParserFactory.register_parser('cloudformation', CloudFormationParser)
IaCParserFactory.register_parser('arm', ARMParser)

__all__ = [
    # Base classes
    'IaCParser',
    'IaCPlan',
    'IaCResource',
    'IaCDependency',
    'IaCParserFactory',
    'CloudProvider',
    'ChangeType',
    
    # Utility functions
    'create_unified_plan',
    'normalize_all_resources',
    'extract_dependencies',
    
    # Parser implementations
    'TerraformParser',
    'CloudFormationParser',
]
