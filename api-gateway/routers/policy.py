from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from policy_engine.engine import PolicyEngine
from shared.metrics import MetricsCollector


router = APIRouter(prefix="/policy", tags=["Policy"])

# Global services (use dependency injection in production)
_policy_engine: Optional[PolicyEngine] = None
_metrics_collector: Optional[MetricsCollector] = None


class PolicyEvaluationRequest(BaseModel):
    """Request model for policy evaluation"""
    event: Dict[str, Any] = Field(..., description="Cloud event to evaluate")
    context: Optional[Dict[str, Any]] = Field(None, description="Evaluation context")


class PolicyEvaluationResponse(BaseModel):
    """Response model for policy evaluation"""
    violations: List[Dict[str, Any]] = Field(..., description="Policy violations found")
    evaluation_time: datetime = Field(..., description="When evaluation was performed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


def get_policy_engine() -> PolicyEngine:
    """Get policy engine instance"""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine


def get_metrics_collector() -> MetricsCollector:
    """Get metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector("policy_api")
    return _metrics_collector


@router.post("/evaluate", response_model=PolicyEvaluationResponse)
async def evaluate_event(
    request: PolicyEvaluationRequest,
    policy_engine: PolicyEngine = Depends(get_policy_engine),
    metrics: MetricsCollector = Depends(get_metrics_collector)
):
    """Evaluate an event against policies"""
    
    try:
        # Evaluate event
        violations = policy_engine.evaluate_event(request.event)
        
        # Record metrics
        metrics.counter('policy_api_evaluations_total').inc()
        metrics.counter('policy_api_violations_total').inc(len(violations))
        
        return PolicyEvaluationResponse(
            violations=violations,
            evaluation_time=datetime.utcnow(),
            metadata={
                'event_id': request.event.get('id', 'unknown'),
                'context': request.context
            }
        )
        
    except Exception as e:
        logging.error(f"Policy evaluation failed: {e}")
        metrics.counter('policy_api_evaluations_total').inc(
            labels={'status': 'error'}
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Policy evaluation failed: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check for policy service"""
    try:
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "policy_engine"
            }
        )
        
    except Exception as e:
        logging.error(f"Policy health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Health check failed: {str(e)}"
        )
