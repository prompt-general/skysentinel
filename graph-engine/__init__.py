"""
Graph Engine Module

This module provides the core graph database functionality for SkySentinel:
- Neo4j integration for security graph management
- Temporal versioning for audit trails
- Relationship mapping and analysis
- Attack path detection and anomaly analysis
- Resource dependency tracking

Main Components:
- GraphEngine: Main graph database service class
"""

from .service import GraphEngine

__version__ = "1.0.0"
__all__ = ["GraphEngine"]
