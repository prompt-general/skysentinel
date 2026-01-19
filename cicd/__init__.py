"""
SkySentinel CI/CD Service

This module provides CI/CD integration for SkySentinel, enabling automated
policy evaluation and security checks in CI/CD pipelines.

Features:
- IaC plan evaluation (Terraform, CloudFormation, ARM, Kubernetes)
- Policy violation detection and blocking
- ML-based risk prediction
- Pull request evaluation
- Deployment gatekeeping
- Comprehensive metrics and logging

Usage:
    from cicd.service import CICDService
    
    service = CICDService(policy_engine, predictor)
    result = await service.evaluate_iac('terraform', plan_content, context)
"""

from .service import CICDService, CIStatus, EvaluationResult, create_cicd_service

__version__ = "1.0.0"
__author__ = "SkySentinel Team"

# Export main classes
__all__ = [
    'CICDService',
    'CIStatus', 
    'EvaluationResult',
    'create_cicd_service',
]
