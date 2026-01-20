"""
CI/CD Prevention Package

This package provides comprehensive IaC evaluation and prevention
capabilities for CI/CD pipelines, including policy evaluation,
ML predictions, and security analysis.
"""

from .service import CICDService, EvaluationResult
from .parsers import (
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

__all__ = [
    # Core service
    'CICDService',
    'EvaluationResult',
    
    # Parsers
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
]
