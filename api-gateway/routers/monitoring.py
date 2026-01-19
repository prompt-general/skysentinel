from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from shared.metrics import MetricsCollector


router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

# Global metrics collector
metrics_collector = MetricsCollector("monitoring_api")


class MetricsResponse(BaseModel):
    """Response model for metrics"""
    metrics: Dict[str, Any]
    timestamp: datetime


class HealthResponse(BaseModel):
    """Response model for health checks"""
    status: str
    timestamp: datetime
    services: Dict[str, str]
    details: Optional[Dict[str, Any]] = None


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check for monitoring service"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "services": {
                "monitoring": "healthy",
                "metrics": "healthy"
            }
        }
        
        return HealthResponse(**health_status)
        
    except Exception as e:
        logging.error(f"Monitoring health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get monitoring metrics"""
    try:
        prometheus_metrics = metrics_collector.get_metrics()
        
        return MetricsResponse(
            metrics=prometheus_metrics,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logging.error(f"Failed to get metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics: {str(e)}"
        )
