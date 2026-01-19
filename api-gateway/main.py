"""
SkySentinel API Gateway

FastAPI application providing REST APIs for SkySentinel services.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

from routers import policy, cicd, monitoring
from shared.metrics import MetricsCollector


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global metrics collector
metrics_collector = MetricsCollector("api_gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting SkySentinel API Gateway")
    metrics_collector.counter('api_gateway_startup_total').inc()
    
    yield
    
    # Shutdown
    logger.info("Shutting down SkySentinel API Gateway")
    metrics_collector.counter('api_gateway_shutdown_total').inc()


# Create FastAPI app
app = FastAPI(
    title="SkySentinel API Gateway",
    description="REST API for SkySentinel cloud security platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(policy.router, prefix="/api/v1")
app.include_router(cicd.router, prefix="/api/v1")
app.include_router(monitoring.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "SkySentinel API Gateway",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "policy": "/api/v1/policy",
            "cicd": "/api/v1/cicd",
            "monitoring": "/api/v1/monitoring"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check all services
        health_status = {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",
            "version": "1.0.0",
            "services": {
                "api_gateway": "healthy",
                "policy_engine": "healthy",  # Would check actual service
                "cicd_service": "healthy",   # Would check actual service
                "metrics": "healthy"
            }
        }
        
        metrics_collector.gauge('api_gateway_health_status').set(1)
        
        return JSONResponse(
            status_code=200,
            content=health_status
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        metrics_collector.gauge('api_gateway_health_status').set(0)
        
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": "2024-01-01T00:00:00Z",
                "error": str(e)
            }
        )


@app.get("/metrics")
async def get_metrics():
    """Get application metrics"""
    try:
        prometheus_metrics = metrics_collector.get_metrics()
        
        return JSONResponse(
            status_code=200,
            content={
                "metrics": prometheus_metrics,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics: {str(e)}"
        )


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors"""
    metrics_collector.counter('api_gateway_404_errors_total').inc()
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": f"Endpoint {request.url.path} not found",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {exc}")
    metrics_collector.counter('api_gateway_500_errors_total').inc()
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "timestamp": "2024-01-01T00:00:00Z"
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
