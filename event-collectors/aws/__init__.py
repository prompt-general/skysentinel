"""
AWS Event Collector Module

This module provides event collection capabilities for AWS services including:
- CloudTrail API events
- EventBridge events
- Real-time event streaming
- Normalized event schema conversion

Main Components:
- AWSEventCollector: Main collector class
- NormalizedEvent: Standardized event format
- Configuration management
"""

from .collector import AWSEventCollector

__version__ = "1.0.0"
__all__ = ["AWSEventCollector"]
