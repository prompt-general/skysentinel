"""
CI/CD Prevention API Package

This package provides API endpoints for CI/CD integration,
including webhooks and evaluation result retrieval.
"""

from .webhook import router as webhook_router

__all__ = [
    'webhook_router',
]
