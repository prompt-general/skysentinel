"""
Cloud Integration Layer

This module provides cloud-specific integrations for the SkySentinel policy engine.
"""

from .azure_integration import AzureIntegration

__all__ = [
    "AzureIntegration"
]
