"""
GraphQL Server for SkySentinel
FastAPI-based GraphQL server with subscriptions support
"""

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
import asyncio
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Import schema and resolvers
from .resolvers import create_schema
from .schema import DateTime, JSON

class GraphQLServer:
    """GraphQL Server with FastAPI"""
    
    def __init__(self, neo4j_driver, prediction_engine, policy_engine):
        self.app = FastAPI(title="SkySentinel GraphQL API")
        self.neo4j_driver = neo4j_driver
        self.prediction_engine = prediction_engine
        self.policy_engine = policy_engine
        
        # Create GraphQL schema
        self.schema = create_schema(neo4j_driver, prediction_engine, policy_engine)
        
        # WebSocket connections for subscriptions
        self.websockets: Dict[str, WebSocket] = {}
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def graphql_playground():
            """GraphQL Playground"""
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>SkySentinel GraphQL Playground</title>
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/css/index.css" />
            </head>
            <body>
                <div id="root">
                    <style>
                        body { margin: 0; font-family: Arial, sans-serif; }
                        .header { 
                            background: #2c3e50; 
                            color: white; 
                            padding: 1rem; 
                            text-align: center; 
                        }
                        .playground-container { 
                            height: calc(100vh - 60px); 
                        }
                    </style>
                    <div class="header">
                        <h1>SkySentinel GraphQL API</h1>
                        <p>Cloud Security Policy Management & ML-Powered Threat Detection</p>
                    </div>
                    <div class="playground-container" id="playground"></div>
                </div>
                <script crossorigin src="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/js/index.js"></script>
                <script>
                    window.addEventListener('load', () => {
                        GraphQLPlayground.init(document.getElementById('playground'), {
                            endpoint: '/graphql',
                            subscriptionEndpoint: '/ws',
                            headers: {
                                'X-Tenant-ID': 'demo-tenant'
                            }
                        });
                    });
                </script>
            </body>
            </html>
            """
        
        @self.app.post("/graphql")
        async def graphql_endpoint(request: Request):
            """GraphQL endpoint"""
            try:
                # Parse request
                data = await request.json()
                query = data.get("query")
                variables = data.get("variables", {})
                operation_name = data.get("operationName")
                
                # Extract tenant ID from headers
                tenant_id = request.headers.get("X-Tenant-ID", "default")
                
                # Execute query
                result = await self.schema.execute(
                    query,
                    variable_values=variables,
                    operation_name=operation_name,
                    context_value={
                        "tenant_id": tenant_id,
                        "neo4j_driver": self.neo4j_driver,
                        "prediction_engine": self.prediction_engine,
                        "policy_engine": self.policy_engine
                    }
                )
                
                return result
                
            except Exception as e:
                logger.error(f"GraphQL error: {e}")
                return {
                    "errors": [{"message": str(e)}]
                }
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for subscriptions"""
            await websocket.accept()
            
            # Generate connection ID
            connection_id = f"conn-{id(websocket)}"
            self.websockets[connection_id] = websocket
            
            try:
                # Handle subscription messages
                while True:
                    message = await websocket.receive_text()
                    data = json.loads(message)
                    
                    # Handle subscription
                    if data.get("type") == "start":
                        subscription_name = data.get("subscriptionName")
                        tenant_id = data.get("tenantId", "default")
                        
                        # Start subscription
                        await self._handle_subscription(
                            websocket, connection_id, subscription_name, tenant_id
                        )
                    elif data.get("type") == "stop":
                        # Stop subscription
                        break
                        
            except WebSocketDisconnect:
                pass
            finally:
                # Clean up connection
                if connection_id in self.websockets:
                    del self.websockets[connection_id]
    
    async def _handle_subscription(self, websocket, connection_id, subscription_name, tenant_id):
        """Handle GraphQL subscription"""
        
        # Mock subscription data - in real implementation, this would
        # listen to database events or message queues
        subscription_data = {
            "violationCreated": self._mock_violation_created,
            "violationUpdated": self._mock_violation_updated,
            "evaluationCompleted": self._mock_evaluation_completed
        }
        
        if subscription_name in subscription_data:
            # Get subscription generator
            generator = subscription_data[subscription_name](tenant_id)
            
            # Send subscription data
            try:
                async for data in generator:
                    await websocket.send_text(json.dumps({
                        "type": "data",
                        "subscription": subscription_name,
                        "data": data
                    }))
                    # Small delay to prevent overwhelming the client
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Subscription error: {e}")
    
    async def _mock_violation_created(self, tenant_id):
        """Mock violation created subscription"""
        # In real implementation, this would listen to violation creation events
        for i in range(5):  # Send 5 mock events
            yield {
                "id": f"violation-{i}",
                "policyId": "policy-1",
                "severity": "HIGH",
                "description": f"Mock violation {i}",
                "detectedAt": "2024-01-15T10:30:00Z",
                "tenantId": tenant_id
            }
            await asyncio.sleep(2)
    
    async def _mock_violation_updated(self, tenant_id):
        """Mock violation updated subscription"""
        for i in range(3):
            yield {
                "id": f"violation-{i}",
                "status": "RESOLVED",
                "updatedAt": "2024-01-15T11:00:00Z",
                "tenantId": tenant_id
            }
            await asyncio.sleep(3)
    
    async def _mock_evaluation_completed(self, tenant_id):
        """Mock evaluation completed subscription"""
        for i in range(2):
            yield {
                "id": f"eval-{i}",
                "status": "COMPLETED",
                "result": "WARN",
                "completedAt": "2024-01-15T09:05:00Z",
                "tenantId": tenant_id
            }
            await asyncio.sleep(5)
    
    async def broadcast_to_subscribers(self, subscription_type: str, data: Dict, tenant_id: str = None):
        """Broadcast data to all subscribers of a specific subscription"""
        
        for connection_id, websocket in self.websockets.items():
            try:
                await websocket.send_text(json.dumps({
                    "type": "data",
                    "subscription": subscription_type,
                    "data": data
                }))
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_id}: {e}")
                # Remove broken connection
                if connection_id in self.websockets:
                    del self.websockets[connection_id]
    
    def get_app(self):
        """Get the FastAPI app instance"""
        return self.app


# Custom scalar types
class DateTime:
    @staticmethod
    def serialize(value):
        return value.isoformat() if hasattr(value, 'isoformat') else value

class JSON:
    @staticmethod
    def serialize(value):
        return value


# Factory function
def create_graphql_server(neo4j_driver, prediction_engine, policy_engine):
    """Create and configure GraphQL server"""
    server = GraphQLServer(neo4j_driver, prediction_engine, policy_engine)
    return server.get_app()
