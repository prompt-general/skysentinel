from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List
import uuid
import asyncio
from datetime import datetime, timedelta
import logging

from cicd.service import CICDService, CIStatus, EvaluationResult, create_cicd_service
from policy_engine.engine import PolicyEngine
from shared.metrics import MetricsCollector


router = APIRouter(prefix="/cicd", tags=["CI/CD"])

# Global services (in production, use dependency injection)
_cicd_service: Optional[CICDService] = None
_metrics_collector: Optional[MetricsCollector] = None

# In-memory storage for demo (use Redis/database in production)
evaluation_store: Dict[str, Dict] = {}
evaluation_results: Dict[str, EvaluationResult] = {}


class IaCEvaluationRequest(BaseModel):
    """Request model for IaC evaluation"""
    iac_type: str = Field(..., description="IaC type: terraform, cloudformation, arm, kubernetes")
    iac_content: Dict[str, Any] = Field(..., description="IaC plan or template content")
    context: Optional[Dict[str, Any]] = Field(None, description="Evaluation context (PR info, user, etc.)")
    priority: Optional[str] = Field("normal", description="Evaluation priority: low, normal, high, critical")
    
    @validator('iac_type')
    def validate_iac_type(cls, v):
        allowed_types = ['terraform', 'cloudformation', 'arm', 'kubernetes']
        if v.lower() not in allowed_types:
            raise ValueError(f"IaC type must be one of: {allowed_types}")
        return v.lower()


class IaCEvaluationResponse(BaseModel):
    """Response model for IaC evaluation"""
    evaluation_id: str = Field(..., description="Unique evaluation identifier")
    status: str = Field(..., description="Evaluation status: processing, completed, failed, cancelled")
    submitted_at: datetime = Field(..., description="When the evaluation was submitted")
    started_at: Optional[datetime] = Field(None, description="When evaluation started")
    completed_at: Optional[datetime] = Field(None, description="When evaluation completed")
    result: Optional[Dict[str, Any]] = Field(None, description="Evaluation results")
    error: Optional[str] = Field(None, description="Error message if evaluation failed")
    progress: Optional[float] = Field(None, description="Evaluation progress (0-100)")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")


class PullRequestEvaluationRequest(BaseModel):
    """Request model for pull request evaluation"""
    pull_request: Dict[str, Any] = Field(..., description="Pull request information")
    iac_changes: List[Dict[str, Any]] = Field(..., description="List of IaC file changes")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class DeploymentEvaluationRequest(BaseModel):
    """Request model for deployment evaluation"""
    deployment: Dict[str, Any] = Field(..., description="Deployment configuration")
    iac_type: str = Field(..., description="IaC type")
    iac_content: Dict[str, Any] = Field(..., description="IaC content")
    context: Optional[Dict[str, Any]] = Field(None, description="Deployment context")


class EvaluationStatusResponse(BaseModel):
    """Response model for evaluation status"""
    evaluation_id: str
    status: str
    progress: Optional[float] = None
    submitted_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    result_summary: Optional[Dict[str, Any]] = None


def get_cicd_service() -> CICDService:
    """Get CI/CD service instance (dependency injection)"""
    global _cicd_service
    if _cicd_service is None:
        # Initialize with default components (in production, use proper DI)
        from policy_engine.engine import PolicyEngine
        from shared.metrics import MetricsCollector
        
        policy_engine = PolicyEngine()
        metrics_collector = MetricsCollector("cicd_api")
        _cicd_service = create_cicd_service(policy_engine, metrics_collector=metrics_collector)
        _metrics_collector = metrics_collector
    
    return _cicd_service


def get_metrics_collector() -> MetricsCollector:
    """Get metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector("cicd_api")
    return _metrics_collector


@router.post("/evaluate", response_model=IaCEvaluationResponse, status_code=status.HTTP_202_ACCEPTED)
async def evaluate_iac(
    request: IaCEvaluationRequest, 
    background_tasks: BackgroundTasks,
    cicd_service: CICDService = Depends(get_cicd_service),
    metrics: MetricsCollector = Depends(get_metrics_collector)
):
    """Submit IaC content for evaluation"""
    evaluation_id = str(uuid.uuid4())
    submitted_at = datetime.utcnow()
    
    # Store initial evaluation record
    evaluation_store[evaluation_id] = {
        'evaluation_id': evaluation_id,
        'status': 'processing',
        'submitted_at': submitted_at,
        'request': request.dict()
    }
    
    # Add background task
    background_tasks.add_task(
        run_evaluation_task,
        evaluation_id,
        request,
        cicd_service,
        metrics
    )
    
    # Record metrics
    metrics.counter('cicd_api_evaluations_submitted_total').inc(
        labels={'iac_type': request.iac_type}
    )
    
    return IaCEvaluationResponse(
        evaluation_id=evaluation_id,
        status="processing",
        submitted_at=submitted_at
    )


@router.get("/evaluate/{evaluation_id}", response_model=EvaluationStatusResponse)
async def get_evaluation_status(
    evaluation_id: str,
    cicd_service: CICDService = Depends(get_cicd_service),
    metrics: MetricsCollector = Depends(get_metrics_collector)
):
    """Get evaluation status and results"""
    
    # Check if evaluation exists
    if evaluation_id not in evaluation_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation {evaluation_id} not found"
        )
    
    # Check if we have completed results
    if evaluation_id in evaluation_results:
        result = evaluation_results[evaluation_id]
        
        response = EvaluationStatusResponse(
            evaluation_id=evaluation_id,
            status=result.status.value,
            progress=100.0,
            submitted_at=evaluation_store[evaluation_id]['submitted_at'],
            started_at=result.metadata.get('started_at'),
            completed_at=result.timestamp,
            result_summary={
                'status': result.status.value,
                'violations_count': len(result.violations),
                'resources_evaluated': result.resources_count,
                'prediction_risk': result.prediction.get('risk_level', 'unknown')
            }
        )
        
        # Record metrics
        metrics.counter('cicd_api_status_checks_total').inc(
            labels={'status': 'completed'}
        )
        
        return response
    
    # Return current status
    eval_record = evaluation_store[evaluation_id]
    response = EvaluationStatusResponse(
        evaluation_id=evaluation_id,
        status=eval_record['status'],
        progress=eval_record.get('progress', 0.0),
        submitted_at=eval_record['submitted_at'],
        started_at=eval_record.get('started_at'),
        estimated_completion=eval_record.get('estimated_completion')
    )
    
    # Record metrics
    metrics.counter('cicd_api_status_checks_total').inc(
        labels={'status': eval_record['status']}
    )
    
    return response


@router.post("/evaluate/pr", response_model=Dict[str, Any])
async def evaluate_pull_request(
    request: PullRequestEvaluationRequest,
    cicd_service: CICDService = Depends(get_cicd_service),
    metrics: MetricsCollector = Depends(get_metrics_collector)
):
    """Evaluate IaC changes in a pull request"""
    
    try:
        # Add PR context
        context = request.context or {}
        context.update({
            'pull_request': request.pull_request,
            'evaluation_type': 'pull_request'
        })
        
        # Evaluate PR changes
        result = await cicd_service.evaluate_pull_request(
            request.pull_request,
            request.iac_changes
        )
        
        # Record metrics
        metrics.counter('cicd_api_pr_evaluations_total').inc()
        metrics.counter('cicd_api_pr_evaluations_by_status').inc(
            labels={'status': result['overall_status']}
        )
        
        return {
            'success': True,
            'pull_request': request.pull_request,
            'evaluation': result,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        metrics.counter('cicd_api_pr_evaluations_total').inc(
            labels={'status': 'error'}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PR evaluation failed: {str(e)}"
        )


@router.post("/evaluate/deployment", response_model=Dict[str, Any])
async def evaluate_deployment(
    request: DeploymentEvaluationRequest,
    cicd_service: CICDService = Depends(get_cicd_service),
    metrics: MetricsCollector = Depends(get_metrics_collector)
):
    """Evaluate a deployment configuration"""
    
    try:
        # Add deployment context
        context = request.context or {}
        context.update({
            'deployment': request.deployment,
            'evaluation_type': 'deployment'
        })
        
        # Evaluate deployment
        result = await cicd_service.evaluate_deployment(request.deployment)
        
        # Record metrics
        metrics.counter('cicd_api_deployment_evaluations_total').inc()
        metrics.counter('cicd_api_deployment_evaluations_by_status').inc(
            labels={'status': result['evaluation']['status']}
        )
        
        return {
            'success': True,
            'deployment': request.deployment,
            'evaluation': result,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        metrics.counter('cicd_api_deployment_evaluations_total').inc(
            labels={'status': 'error'}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment evaluation failed: {str(e)}"
        )


@router.delete("/evaluate/{evaluation_id}")
async def cancel_evaluation(
    evaluation_id: str,
    cicd_service: CICDService = Depends(get_cicd_service),
    metrics: MetricsCollector = Depends(get_metrics_collector)
):
    """Cancel an ongoing evaluation"""
    
    if evaluation_id not in evaluation_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation {evaluation_id} not found"
        )
    
    eval_record = evaluation_store[evaluation_id]
    if eval_record['status'] not in ['processing']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Evaluation {evaluation_id} cannot be cancelled (status: {eval_record['status']})"
        )
    
    # Update status
    eval_record['status'] = 'cancelled'
    eval_record['completed_at'] = datetime.utcnow()
    
    # Remove from results if exists
    if evaluation_id in evaluation_results:
        del evaluation_results[evaluation_id]
    
    # Record metrics
    metrics.counter('cicd_api_evaluations_cancelled_total').inc()
    
    return {
        'evaluation_id': evaluation_id,
        'status': 'cancelled',
        'message': 'Evaluation cancelled successfully',
        'timestamp': datetime.utcnow().isoformat()
    }


@router.get("/evaluations", response_model=List[Dict[str, Any]])
async def list_evaluations(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    iac_type: Optional[str] = None,
    metrics: MetricsCollector = Depends(get_metrics_collector)
):
    """List recent evaluations"""
    
    # Filter evaluations
    filtered_evaluations = []
    for eval_id, eval_record in evaluation_store.items():
        # Apply filters
        if status and eval_record['status'] != status:
            continue
        
        if iac_type:
            request_iac_type = eval_record['request'].get('iac_type', '')
            if request_iac_type != iac_type:
                continue
        
        # Add result if available
        result = None
        if eval_id in evaluation_results:
            result = evaluation_results[eval_id].to_dict()
        
        filtered_evaluations.append({
            'evaluation_id': eval_id,
            'status': eval_record['status'],
            'submitted_at': eval_record['submitted_at'],
            'started_at': eval_record.get('started_at'),
            'completed_at': eval_record.get('completed_at'),
            'iac_type': eval_record['request'].get('iac_type'),
            'result': result
        })
    
    # Sort by submitted_at (newest first)
    filtered_evaluations.sort(
        key=lambda x: x['submitted_at'],
        reverse=True
    )
    
    # Apply pagination
    paginated_evaluations = filtered_evaluations[offset:offset + limit]
    
    # Record metrics
    metrics.counter('cicd_api_list_evaluations_total').inc()
    
    return paginated_evaluations


@router.get("/health")
async def health_check(
    cicd_service: CICDService = Depends(get_cicd_service),
    metrics: MetricsCollector = Depends(get_metrics_collector)
):
    """Health check for CI/CD API"""
    
    try:
        # Check CI/CD service health
        service_health = await cicd_service.health_check()
        
        # Check API health
        api_health = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'evaluations_in_progress': len([
                e for e in evaluation_store.values() 
                if e['status'] == 'processing'
            ]),
            'total_evaluations': len(evaluation_store)
        }
        
        # Record metrics
        metrics.gauge('cicd_api_health_status').set(1 if service_health['status'] == 'healthy' else 0)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'api': api_health,
                'service': service_health
            }
        )
        
    except Exception as e:
        metrics.gauge('cicd_api_health_status').set(0)
        
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                'status': 'unhealthy',
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
        )


@router.get("/metrics")
async def get_metrics(
    cicd_service: CICDService = Depends(get_cicd_service),
    metrics: MetricsCollector = Depends(get_metrics_collector)
):
    """Get CI/CD service metrics"""
    
    try:
        # Get service metrics
        service_metrics = {
            'evaluations_total': len(evaluation_store),
            'evaluations_by_status': {},
            'evaluations_by_iac_type': {},
            'evaluations_in_progress': 0
        }
        
        # Calculate metrics
        for eval_record in evaluation_store.values():
            status = eval_record['status']
            iac_type = eval_record['request'].get('iac_type', 'unknown')
            
            service_metrics['evaluations_by_status'][status] = \
                service_metrics['evaluations_by_status'].get(status, 0) + 1
            
            service_metrics['evaluations_by_iac_type'][iac_type] = \
                service_metrics['evaluations_by_iac_type'].get(iac_type, 0) + 1
            
            if status == 'processing':
                service_metrics['evaluations_in_progress'] += 1
        
        # Get Prometheus metrics
        prometheus_metrics = metrics.get_metrics()
        
        return {
            'service_metrics': service_metrics,
            'prometheus_metrics': prometheus_metrics,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


# Background task functions
async def run_evaluation_task(
    evaluation_id: str,
    request: IaCEvaluationRequest,
    cicd_service: CICDService,
    metrics: MetricsCollector
):
    """Run evaluation in background"""
    
    try:
        # Update status to started
        evaluation_store[evaluation_id]['status'] = 'processing'
        evaluation_store[evaluation_id]['started_at'] = datetime.utcnow()
        evaluation_store[evaluation_id]['progress'] = 0.0
        
        # Estimate completion time (based on IaC type and content size)
        content_size = len(str(request.iac_content))
        estimated_duration = estimate_evaluation_duration(request.iac_type, content_size)
        estimated_completion = datetime.utcnow() + timedelta(seconds=estimated_duration)
        evaluation_store[evaluation_id]['estimated_completion'] = estimated_completion
        
        # Run evaluation
        result = await cicd_service.evaluate_iac(
            request.iac_type,
            request.iac_content,
            request.context or {}
        )
        
        # Store result
        evaluation_results[evaluation_id] = result
        
        # Update status
        evaluation_store[evaluation_id]['status'] = 'completed'
        evaluation_store[evaluation_id]['completed_at'] = result.timestamp
        evaluation_store[evaluation_id]['progress'] = 100.0
        
        # Record metrics
        metrics.counter('cicd_evaluations_completed_total').inc(
            labels={
                'iac_type': request.iac_type,
                'status': result.status.value
            }
        )
        
        metrics.histogram('cicd_evaluation_duration_seconds').observe(
            (datetime.utcnow() - evaluation_store[evaluation_id]['started_at']).total_seconds()
        )
        
    except Exception as e:
        # Update status to failed
        evaluation_store[evaluation_id]['status'] = 'failed'
        evaluation_store[evaluation_id]['completed_at'] = datetime.utcnow()
        evaluation_store[evaluation_id]['error'] = str(e)
        
        # Record metrics
        metrics.counter('cicd_evaluations_failed_total').inc(
            labels={'iac_type': request.iac_type}
        )


def estimate_evaluation_duration(iac_type: str, content_size: int) -> int:
    """Estimate evaluation duration in seconds"""
    # Base durations by IaC type
    base_durations = {
        'terraform': 30,
        'cloudformation': 25,
        'arm': 20,
        'kubernetes': 15
    }
    
    base_duration = base_durations.get(iac_type, 30)
    
    # Adjust based on content size (larger content takes longer)
    size_factor = min(content_size / 10000, 5.0)  # Max 5x base duration
    
    return int(base_duration * (1 + size_factor))
