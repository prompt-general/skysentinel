"""
Shared Models Module

This module contains shared data models used across SkySentinel components:
- NormalizedEvent: Standardized event format using Pydantic
- ResourceReference: Resource information model
- Principal: Principal/identity information model
- EventCollectorConfig: Configuration model for collectors
"""

from .events import NormalizedEvent, ResourceReference, Principal, EventCollectorConfig, CloudProvider

__all__ = ["NormalizedEvent", "ResourceReference", "Principal", "EventCollectorConfig", "CloudProvider"]
