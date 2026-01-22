"""
SkySentinel API Gateway

FastAPI application providing REST APIs for SkySentinel services with rate limiting and caching.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import redis
import time
import os
import secrets
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Redis for caching and rate limiting
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True
)

# Rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}",
    enabled=True
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    FastAPICache.init(RedisBackend(redis_client), prefix="skysentinel-cache")
    logger.info("API Gateway started")
    yield
    # Shutdown
    logger.info("API Gateway shutting down")

# Create FastAPI app
app = FastAPI(
    title="SkySentinel API Gateway",
    description="Cloud Policy Engine API Gateway with Rate Limiting & Caching",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Add exception handler for rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*.skysentinel.io"])
app.add_middleware(SlowAPIMiddleware)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all API requests"""
    start_time = time.time()
    
    # Get request details
    request_id = request.headers.get("X-Request-ID", secrets.token_urlsafe(16))
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "unknown")
    
    # Add request ID to headers
    request.scope["headers"].append((b"x-request-id", request_id.encode()))
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path} | "
        f"Status: {response.status_code} | "
        f"Time: {process_time:.3f}s | "
        f"IP: {client_ip} | "
        f"User-Agent: {user_agent} | "
        f"Request-ID: {request_id}"
    )
    
    # Add headers to response
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request_id
    
    return response

# Tenant isolation middleware
@app.middleware("http")
async def tenant_isolation(request: Request, call_next):
    """Ensure tenant isolation for all requests"""
    # Get tenant from JWT or API key
    tenant_id = None
    
    # Check for JWT in Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            # Decode JWT to get tenant (without verifying for speed)
            # In production, use proper verification
            import jwt
            payload = jwt.decode(token, options={"verify_signature": False})
            tenant_id = payload.get("tenant_id")
        except:
            pass
    
    # Check for tenant header (for internal services)
    if not tenant_id:
        tenant_id = request.headers.get("X-Tenant-ID")
    
    # Set tenant in request state
    request.state.tenant_id = tenant_id
    
    # Check if request is allowed for this tenant
    if tenant_id and not is_tenant_active(tenant_id):
        return JSONResponse(
            status_code=403,
            content={"detail": f"Tenant {tenant_id} is not active"}
        )
    
    response = await call_next(request)
    return response

# Rate limiting by tenant/user
def get_rate_limit_key(request: Request) -> str:
    """Get rate limit key based on tenant and user"""
    tenant_id = getattr(request.state, 'tenant_id', 'anonymous')
    user_id = "anonymous"
    
    # Try to get user from JWT
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            import jwt
            payload = jwt.decode(token, options={"verify_signature": False})
            user_id = payload.get("sub", "unknown")
        except:
            pass
    
    return f"{tenant_id}:{user_id}"

# Apply rate limits based on subscription tier
def get_rate_limit_for_tenant(tenant_id: str) -> str:
    """Get rate limit string based on tenant subscription"""
    # In production, query database for tenant tier
    tiers = {
        "free": "10/minute",
        "basic": "100/minute",
        "professional": "1000/minute",
        "enterprise": "10000/minute"
    }
    
    # Default to basic
    return tiers.get(get_tenant_tier(tenant_id), "100/minute")

# API Routes with rate limiting
@app.get("/api/v1/violations")
@limiter.limit(lambda request: get_rate_limit_for_tenant(request.state.tenant_id))
@cache(expire=60)  # Cache for 60 seconds
async def get_violations(
    request: Request,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get violations with rate limiting and caching"""
    tenant_id = request.state.tenant_id
    
    # Query Neo4j with tenant isolation
    # This would be implemented with a service
    violations = []
    
    return {
        "violations": violations,
        "count": len(violations),
        "limit": limit,
        "offset": offset
    }

@app.post("/api/v1/violations/{violation_id}/remediate")
@limiter.limit("10/minute")  # Lower limit for write operations
async def remediate_violation(
    request: Request,
    violation_id: str,
    action: str
):
    """Remediate a violation"""
    tenant_id = request.state.tenant_id
    
    # Check if user has permission
    # This would use the auth service
    
    # Perform remediation
    # This would call the policy engine
    
    return {"status": "success", "message": "Remediation initiated"}

# Health check endpoint (no rate limiting)
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    services = {
        "api_gateway": True,
        "redis": redis_client.ping(),
        "neo4j": check_neo4j_health(),
        "event_processor": check_event_processor_health()
    }
    
    all_healthy = all(services.values())
    status_code = 200 if all_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "unhealthy",
            "services": services,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Metrics endpoint for monitoring
@app.get("/metrics")
async def get_metrics(request: Request):
    """Get API metrics"""
    tenant_id = request.state.tenant_id
    
    # Get rate limit usage
    rate_limit_key = get_rate_limit_key(request)
    current_usage = get_rate_limit_usage(rate_limit_key)
    
    # Get cache statistics
    cache_stats = FastAPICache.get_stats()
    
    # Get request statistics
    request_stats = {
        "total_requests": get_request_count(tenant_id),
        "success_rate": get_success_rate(tenant_id),
        "avg_response_time": get_avg_response_time(tenant_id)
    }
    
    return {
        "rate_limit": current_usage,
        "cache": cache_stats,
        "requests": request_stats,
        "timestamp": datetime.utcnow().isoformat()
    }

# Helper functions
def is_tenant_active(tenant_id: str) -> bool:
    """Check if tenant is active"""
    # In production, query database
    return True

def get_tenant_tier(tenant_id: str) -> str:
    """Get tenant subscription tier"""
    # In production, query database
    return "professional"

def get_rate_limit_usage(key: str) -> Dict:
    """Get current rate limit usage"""
    return {
        "key": key,
        "limit": 100,
        "remaining": 95,
        "reset": int(time.time() + 60)
    }

def check_neo4j_health() -> bool:
    """Check Neo4j health"""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )
        with driver.session() as session:
            result = session.run("RETURN 1 as health")
            return result.single()["health"] == 1
    except:
        return False

def check_event_processor_health() -> bool:
    """Check event processor health"""
    # In production, check event processor service
    return True

def get_request_count(tenant_id: str) -> int:
    """Get request count for tenant"""
    # In production, query metrics database
    return 1000

def get_success_rate(tenant_id: str) -> float:
    """Get success rate for tenant"""
    # In production, query metrics database
    return 0.95

def get_avg_response_time(tenant_id: str) -> float:
    """Get average response time for tenant"""
    # In production, query metrics database
    return 0.150

# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": f"Endpoint {request.url.path} not found",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
