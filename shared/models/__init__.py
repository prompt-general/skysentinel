"""
Shared Models Module

This module contains shared data models used across SkySentinel components:
- NormalizedEvent: Standardized event format
- ResourceInfo: Resource information model
- PrincipalInfo: Principal/identity information model
- EventCollectorConfig: Configuration model for collectors
"""

from .events import NormalizedEvent, ResourceInfo, PrincipalInfo, EventCollectorConfig

__all__ = ["NormalizedEvent", "ResourceInfo", "PrincipalInfo", "EventCollectorConfig"]
