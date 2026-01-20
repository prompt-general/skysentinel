"""
SkySentinel GraphQL Server

FastAPI-based GraphQL server for SkySentinel API.
"""

import asyncio
from typing import Dict, Any
import logging
from datetime import datetime

import strawberry
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from .resolvers import GraphQLResolvers
from graph_engine.neo4j_client import Neo4jClient
from policy_engine.engine import PolicyEngine
from shared.metrics import MetricsCollector

logger = logging.getLogger(__name__)

# Initialize services
neo4j_client = Neo4jClient()
policy_engine = PolicyEngine()
metrics = MetricsCollector("graphql_api")
resolvers = GraphQLResolvers(neo4j_client, policy_engine, metrics)

# Create FastAPI app
app = FastAPI(title="SkySentinel GraphQL API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GraphQL Schema Definition
@strawberry.type
class Query:
    """Root Query type"""
    
    @strawberry.field
    async def resource(self, id: str) -> Dict[str, Any]:
        return await resolvers.resolve_resource(None, id)
    
    @strawberry.field
    async def resources(self, filter: Dict = None, limit: int = 100, 
                     offset: int = 0, sortBy: str = "name", 
                     sortOrder: str = "ASC") -> list[Dict[str, Any]]:
        return await resolvers.resolve_resources(None, filter, limit, offset, sortBy, sortOrder)
    
    @strawberry.field
    async def policy(self, id: str) -> Dict[str, Any]:
        return await resolvers.resolve_policy(None, id)
    
    @strawberry.field
    async def policies(self, category: str = None, severity: str = None,
                     status: str = None, tags: list[str] = None,
                     limit: int = 100, offset: int = 0) -> list[Dict[str, Any]]:
        return await resolvers.resolve_policies(None, category, severity, status, tags, limit, offset)
    
    @strawberry.field
    async def violation(self, id: str) -> Dict[str, Any]:
        return await resolvers.resolve_violation(None, id)
    
    @strawberry.field
    async def violations(self, filter: Dict = None, limit: int = 100,
                       offset: int = 0, sortBy: str = "detectedAt",
                       sortOrder: str = "DESC") -> list[Dict[str, Any]]:
        return await resolvers.resolve_violations(None, filter, limit, offset, sortBy, sortOrder)

@strawberry.type
class Mutation:
    """Root Mutation type"""
    
    @strawberry.mutation
    async def create_policy(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        return await resolvers.resolve_create_policy(None, policy)
    
    @strawberry.mutation
    async def update_policy(self, id: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        return await resolvers.resolve_update_policy(None, id, policy)
    
    @strawberry.mutation
    async def delete_policy(self, id: str) -> bool:
        return await resolvers.resolve_delete_policy(None, id)
    
    @strawberry.mutation
    async def resolve_violation(self, id: str, notes: str) -> Dict[str, Any]:
        return await resolvers.resolve_resolve_violation(None, id, notes)

@strawberry.type
class Subscription:
    """Root Subscription type"""
    
    @strawberry.subscription
    async def violation_created(self) -> Dict[str, Any]:
        """Subscribe to new violations"""
        # Implementation would use WebSocket or similar
        pass

# Create GraphQL schema
schema = strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)

# Create GraphQL router
graphql_router = GraphQLRouter(schema)

# Include GraphQL router
app.include_router(graphql_router, prefix="/graphql")

# Health check endpoint
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "graphql-api"
    }

# Metrics endpoint
@app.get("/metrics")
async def metrics_endpoint():
    return metrics.get_metrics()

# Start server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
