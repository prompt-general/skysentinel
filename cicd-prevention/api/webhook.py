"""
CI/CD Webhook API

This module provides webhook endpoints for CI/CD systems to submit
IaC for evaluation and receive results via callbacks.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Header, BackgroundTasks, Request, Response
from pydantic import BaseModel, Field
import redis.asyncio as redis

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/cicd", tags=["CI/CD"])

# Redis client for result storage (in production, use proper configuration)
redis_client = redis.Redis.from_url("redis://localhost:6379/0", decode_responses=True)


class CIWebhookRequest(BaseModel):
    """Webhook request model for IaC evaluation"""
    iac_type: str = Field(..., description="Type of IaC (terraform, cloudformation, arm)")
    iac_content: Dict[str, Any] = Field(..., description="IaC content to evaluate")
    context: Dict[str, Any] = Field(..., description="Evaluation context")
    callback_url: Optional[str] = Field(None, description="Callback URL for results")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class CIWebhookResponse(BaseModel):
    """Webhook response model"""
    evaluation_id: str = Field(..., description="Unique evaluation identifier")
    status: str = Field(..., description="Evaluation status")
    result_url: Optional[str] = Field(None, description="URL to fetch results")
    estimated_completion: Optional[float] = Field(None, description="Estimated completion time (seconds)")


class GitHubWebhookPayload(BaseModel):
    """GitHub webhook payload model"""
    action: Optional[str] = None
    number: Optional[int] = None
    repository: Optional[Dict[str, Any]] = None
    pull_request: Optional[Dict[str, Any]] = None
    sender: Optional[Dict[str, Any]] = None
    ref: Optional[str] = None
    commits: Optional[List[Dict[str, Any]]] = None


class GitLabWebhookPayload(BaseModel):
    """GitLab webhook payload model"""
    object_kind: Optional[str] = None
    object_attributes: Optional[Dict[str, Any]] = None
    project: Optional[Dict[str, Any]] = None
    merge_request: Optional[Dict[str, Any]] = None
    user: Optional[Dict[str, Any]] = None


@router.post("/webhook/evaluate", response_model=CIWebhookResponse)
async def evaluate_iac_webhook(
    request: CIWebhookRequest,
    background_tasks: BackgroundTasks,
    x_sky_api_key: Optional[str] = Header(None, description="SkySentinel API key"),
    x_sky_tenant: Optional[str] = Header(None, description="Tenant identifier")
):
    """
    Webhook endpoint for CI/CD systems to submit IaC for evaluation
    
    This endpoint accepts IaC content and returns immediately with an evaluation ID.
    The actual evaluation runs in the background and results can be retrieved
    via the results endpoint or callback URL.
    """
    try:
        # Authenticate and authorize
        if not await _authenticate_request(x_sky_api_key, x_sky_tenant):
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        # Generate evaluation ID
        evaluation_id = str(uuid.uuid4())
        
        # Store initial status
        await _store_initial_status(evaluation_id, request.dict(), x_sky_tenant)
        
        # Start background evaluation
        background_tasks.add_task(
            process_evaluation,
            evaluation_id=evaluation_id,
            request=request.dict(),
            api_key=x_sky_api_key,
            tenant_id=x_sky_tenant
        )
        
        logger.info(f"Started evaluation {evaluation_id} for IaC type {request.iac_type}")
        
        # Return immediate response
        return CIWebhookResponse(
            evaluation_id=evaluation_id,
            status="processing",
            result_url=f"/cicd/results/{evaluation_id}",
            estimated_completion=30.0  # seconds
        )
        
    except Exception as e:
        logger.error(f"Error in evaluate_iac_webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/results/{evaluation_id}")
async def get_evaluation_result(
    evaluation_id: str,
    x_sky_api_key: Optional[str] = Header(None, description="SkySentinel API key")
):
    """
    Get evaluation result by ID
    
    Returns the evaluation result including violations, recommendations,
    and overall status. Returns 404 if evaluation not found.
    """
    try:
        # Check authentication
        if not await _authenticate_request(x_sky_api_key):
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        # Get result from storage
        result = await _get_stored_result(evaluation_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        logger.info(f"Retrieved evaluation result: {evaluation_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting evaluation result {evaluation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/github/webhook")
async def github_webhook(
    payload: Dict[str, Any],
    x_github_event: str = Header(..., description="GitHub event type"),
    x_github_signature: Optional[str] = Header(None, description="GitHub signature"),
    x_hub_signature_256: Optional[str] = Header(None, description="GitHub SHA-256 signature")
):
    """
    GitHub-specific webhook handler
    
    Handles GitHub webhook events for pull requests and pushes.
    Automatically extracts IaC files and triggers evaluation.
    """
    try:
        # Verify GitHub signature
        if not _verify_github_signature(payload, x_github_signature, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Process based on event type
        if x_github_event == "pull_request":
            result = await _handle_github_pr(payload)
        elif x_github_event == "push":
            result = await _handle_github_push(payload)
        else:
            result = {"status": "ignored", "reason": f"Event {x_github_event} not supported"}
        
        logger.info(f"Processed GitHub webhook event: {x_github_event}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing GitHub webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/gitlab/webhook")
async def gitlab_webhook(
    payload: Dict[str, Any],
    x_gitlab_token: str = Header(..., description="GitLab webhook token"),
    x_gitlab_event: str = Header(..., description="GitLab event type")
):
    """
    GitLab-specific webhook handler
    
    Handles GitLab webhook events for merge requests and pushes.
    Automatically extracts IaC files and triggers evaluation.
    """
    try:
        # Verify GitLab token
        if not _verify_gitlab_token(x_gitlab_token):
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Process based on event type
        if x_gitlab_event == "Merge Request Hook":
            result = await _handle_gitlab_mr(payload)
        elif x_gitlab_event == "Push Hook":
            result = await _handle_gitlab_push(payload)
        else:
            result = {"status": "ignored", "reason": f"Event {x_gitlab_event} not supported"}
        
        logger.info(f"Processed GitLab webhook event: {x_gitlab_event}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing GitLab webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def webhook_health():
    """Health check endpoint for webhook service"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "cicd-webhook"
    }


@router.get("/metrics")
async def webhook_metrics():
    """Metrics endpoint for webhook service"""
    try:
        # Get basic metrics from Redis
        total_evaluations = await redis_client.get("cicd:total_evaluations") or "0"
        active_evaluations = await redis_client.get("cicd:active_evaluations") or "0"
        
        return {
            "total_evaluations": int(total_evaluations),
            "active_evaluations": int(active_evaluations),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {"error": "Metrics unavailable"}


# Background task processing
async def process_evaluation(evaluation_id: str, request: Dict, api_key: str, tenant_id: str):
    """
    Background task to process evaluation
    
    This runs asynchronously to avoid blocking the webhook response.
    """
    try:
        # Update status to processing
        await _update_evaluation_status(evaluation_id, "processing")
        
        # Initialize services (in production, use dependency injection)
        from cicd_prevention.service import CICDService
        from policy_engine.engine import PolicyEngine
        from prediction_engine.predictor import Predictor
        from graph_engine.neo4j_client import Neo4jClient
        
        # Get services (in production, use proper factory)
        neo4j_client = Neo4jClient()
        policy_engine = PolicyEngine()
        predictor = Predictor()
        cicd_service = CICDService(policy_engine, predictor, neo4j_client)
        
        # Process evaluation
        result = await cicd_service.evaluate_plan(
            iac_type=request['iac_type'],
            iac_content=request['iac_content'],
            context=request['context']
        )
        
        # Store result
        await _store_result(evaluation_id, result)
        
        # Send callback if provided
        if request.get('callback_url'):
            await _send_callback(request['callback_url'], result, api_key)
        
        logger.info(f"Completed evaluation {evaluation_id} with status {result.get('result')}")
        
    except Exception as e:
        logger.error(f"Error processing evaluation {evaluation_id}: {e}", exc_info=True)
        error_result = {
            "evaluation_id": evaluation_id,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
        await _store_result(evaluation_id, error_result)


# Helper functions
async def _authenticate_request(api_key: str, tenant_id: Optional[str] = None) -> bool:
    """
    Authenticate API request
    
    In production, validate against database or auth service.
    For MVP, simple key validation.
    """
    if not api_key:
        return False
    
    # Simple validation - in production, use proper auth
    valid_keys = await redis_client.smembers("cicd:valid_api_keys")
    return api_key in valid_keys


def _verify_github_signature(payload: Dict, signature1: str, signature256: str) -> bool:
    """
    Verify GitHub webhook signature
    
    Implementation depends on your GitHub app setup.
    For MVP, simplified validation.
    """
    # In production, implement proper signature verification
    # using your GitHub app secret
    return True


def _verify_gitlab_token(token: str) -> bool:
    """
    Verify GitLab webhook token
    
    Implementation depends on your GitLab setup.
    For MVP, simplified validation.
    """
    # In production, validate against stored GitLab tokens
    return token == "gitlab-webhook-secret"  # Simplified for MVP


async def _handle_github_pr(payload: Dict) -> Dict:
    """Handle GitHub pull request webhook"""
    action = payload.get('action')
    pr_number = payload.get('number')
    repository = payload.get('repository', {}).get('full_name')
    pull_request = payload.get('pull_request', {})
    
    if action in ['opened', 'synchronize']:
        # Extract IaC files from PR
        iac_files = await _extract_github_iac_files(pull_request)
        
        if iac_files:
            # Trigger evaluation for each IaC file
            evaluation_ids = []
            for iac_file in iac_files:
                evaluation_id = str(uuid.uuid4())
                
                # Store and process
                await _store_initial_status(evaluation_id, {
                    'iac_type': iac_file['type'],
                    'iac_content': iac_file['content'],
                    'context': {
                        'source': 'github',
                        'event': 'pull_request',
                        'pr_number': pr_number,
                        'repository': repository,
                        'branch': pull_request.get('head', {}).get('ref'),
                        'commit': pull_request.get('head', {}).get('sha')
                    }
                })
                
                # Start background processing
                asyncio.create_task(process_evaluation(
                    evaluation_id=evaluation_id,
                    request={
                        'iac_type': iac_file['type'],
                        'iac_content': iac_file['content'],
                        'context': {
                            'source': 'github',
                            'event': 'pull_request',
                            'pr_number': pr_number,
                            'repository': repository
                        }
                    },
                    api_key='internal',
                    tenant_id='github'
                ))
                
                evaluation_ids.append(evaluation_id)
            
            return {
                "status": "evaluation_triggered",
                "pr": pr_number,
                "repository": repository,
                "evaluations": evaluation_ids,
                "iac_files_found": len(iac_files)
            }
        else:
            return {
                "status": "no_iac_files",
                "pr": pr_number,
                "repository": repository
            }
    
    return {"status": "no_action_needed", "action": action}


async def _handle_github_push(payload: Dict) -> Dict:
    """Handle GitHub push webhook"""
    ref = payload.get('ref')
    repository = payload.get('repository', {}).get('full_name')
    commits = payload.get('commits', [])
    
    if ref and ref.startswith('refs/heads/'):
        branch = ref.replace('refs/heads/', '')
        
        # Extract IaC files from commits
        iac_files = await _extract_github_push_iac_files(commits)
        
        if iac_files:
            evaluation_ids = []
            for iac_file in iac_files:
                evaluation_id = str(uuid.uuid4())
                
                await _store_initial_status(evaluation_id, {
                    'iac_type': iac_file['type'],
                    'iac_content': iac_file['content'],
                    'context': {
                        'source': 'github',
                        'event': 'push',
                        'repository': repository,
                        'branch': branch,
                        'commits': [c.get('id') for c in commits]
                    }
                })
                
                asyncio.create_task(process_evaluation(
                    evaluation_id=evaluation_id,
                    request={
                        'iac_type': iac_file['type'],
                        'iac_content': iac_file['content'],
                        'context': {
                            'source': 'github',
                            'event': 'push',
                            'repository': repository,
                            'branch': branch
                        }
                    },
                    api_key='internal',
                    tenant_id='github'
                ))
                
                evaluation_ids.append(evaluation_id)
            
            return {
                "status": "evaluation_triggered",
                "repository": repository,
                "branch": branch,
                "evaluations": evaluation_ids,
                "iac_files_found": len(iac_files)
            }
    
    return {"status": "no_action_needed"}


async def _handle_gitlab_mr(payload: Dict) -> Dict:
    """Handle GitLab merge request webhook"""
    object_attributes = payload.get('object_attributes', {})
    state = object_attributes.get('state')
    action = object_attributes.get('action')
    mr_iid = object_attributes.get('iid')
    project = payload.get('project', {}).get('path_with_namespace')
    
    if state == 'opened' or action == 'update':
        # Extract IaC files from MR
        iac_files = await _extract_gitlab_iac_files(payload)
        
        if iac_files:
            evaluation_ids = []
            for iac_file in iac_files:
                evaluation_id = str(uuid.uuid4())
                
                await _store_initial_status(evaluation_id, {
                    'iac_type': iac_file['type'],
                    'iac_content': iac_file['content'],
                    'context': {
                        'source': 'gitlab',
                        'event': 'merge_request',
                        'mr_iid': mr_iid,
                        'project': project,
                        'branch': object_attributes.get('source_branch')
                    }
                })
                
                asyncio.create_task(process_evaluation(
                    evaluation_id=evaluation_id,
                    request={
                        'iac_type': iac_file['type'],
                        'iac_content': iac_file['content'],
                        'context': {
                            'source': 'gitlab',
                            'event': 'merge_request',
                            'mr_iid': mr_iid,
                            'project': project
                        }
                    },
                    api_key='internal',
                    tenant_id='gitlab'
                ))
                
                evaluation_ids.append(evaluation_id)
            
            return {
                "status": "evaluation_triggered",
                "merge_request": mr_iid,
                "project": project,
                "evaluations": evaluation_ids,
                "iac_files_found": len(iac_files)
            }
        else:
            return {
                "status": "no_iac_files",
                "merge_request": mr_iid,
                "project": project
            }
    
    return {"status": "no_action_needed", "state": state, "action": action}


async def _handle_gitlab_push(payload: Dict) -> Dict:
    """Handle GitLab push webhook"""
    ref = payload.get('ref')
    project = payload.get('project', {}).get('path_with_namespace')
    commits = payload.get('commits', [])
    
    if ref and ref.startswith('refs/heads/'):
        branch = ref.replace('refs/heads/', '')
        
        # Extract IaC files from commits
        iac_files = await _extract_gitlab_push_iac_files(commits)
        
        if iac_files:
            evaluation_ids = []
            for iac_file in iac_files:
                evaluation_id = str(uuid.uuid4())
                
                await _store_initial_status(evaluation_id, {
                    'iac_type': iac_file['type'],
                    'iac_content': iac_file['content'],
                    'context': {
                        'source': 'gitlab',
                        'event': 'push',
                        'project': project,
                        'branch': branch,
                        'commits': [c.get('id') for c in commits]
                    }
                })
                
                asyncio.create_task(process_evaluation(
                    evaluation_id=evaluation_id,
                    request={
                        'iac_type': iac_file['type'],
                        'iac_content': iac_file['content'],
                        'context': {
                            'source': 'gitlab',
                            'event': 'push',
                            'project': project,
                            'branch': branch
                        }
                    },
                    api_key='internal',
                    tenant_id='gitlab'
                ))
                
                evaluation_ids.append(evaluation_id)
            
            return {
                "status": "evaluation_triggered",
                "project": project,
                "branch": branch,
                "evaluations": evaluation_ids,
                "iac_files_found": len(iac_files)
            }
    
    return {"status": "no_action_needed"}


# Storage functions
async def _store_initial_status(evaluation_id: str, request: Dict, tenant_id: str = None):
    """Store initial evaluation status"""
    status_data = {
        "evaluation_id": evaluation_id,
        "status": "queued",
        "timestamp": datetime.utcnow().isoformat(),
        "request": request,
        "tenant_id": tenant_id
    }
    
    await redis_client.setex(
        f"cicd:evaluation:{evaluation_id}",
        3600,  # 1 hour TTL
        json.dumps(status_data)
    )
    
    # Update metrics
    await redis_client.incr("cicd:total_evaluations")
    await redis_client.incr("cicd:active_evaluations")


async def _store_result(evaluation_id: str, result: Dict):
    """Store evaluation result"""
    result_data = {
        "evaluation_id": evaluation_id,
        "status": result.get('status', 'completed'),
        "timestamp": datetime.utcnow().isoformat(),
        "result": result
    }
    
    await redis_client.setex(
        f"cicd:evaluation:{evaluation_id}",
        86400,  # 24 hour TTL
        json.dumps(result_data)
    )
    
    # Update metrics
    await redis_client.decr("cicd:active_evaluations")


async def _get_stored_result(evaluation_id: str) -> Optional[Dict]:
    """Get stored evaluation result"""
    try:
        data = await redis_client.get(f"cicd:evaluation:{evaluation_id}")
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Error getting stored result: {e}")
        return None


async def _update_evaluation_status(evaluation_id: str, status: str):
    """Update evaluation status"""
    try:
        existing = await _get_stored_result(evaluation_id)
        if existing:
            existing['status'] = status
            existing['updated_at'] = datetime.utcnow().isoformat()
            
            await redis_client.setex(
                f"cicd:evaluation:{evaluation_id}",
                3600,
                json.dumps(existing)
            )
    except Exception as e:
        logger.error(f"Error updating evaluation status: {e}")


async def _send_callback(callback_url: str, result: Dict, api_key: str):
    """Send callback with evaluation result"""
    try:
        import httpx
        
        headers = {
            "Content-Type": "application/json",
            "X-Sky-API-Key": api_key,
            "User-Agent": "SkySentinel-CICD-Webhook/1.0"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                callback_url,
                json=result,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully sent callback to {callback_url}")
            else:
                logger.warning(f"Callback failed with status {response.status_code}: {response.text}")
                
    except Exception as e:
        logger.error(f"Error sending callback: {e}")


# IaC file extraction functions (simplified for MVP)
async def _extract_github_iac_files(pull_request: Dict) -> List[Dict]:
    """Extract IaC files from GitHub pull request"""
    # In production, use GitHub API to fetch files
    # For MVP, return empty list
    return []


async def _extract_github_push_iac_files(commits: List[Dict]) -> List[Dict]:
    """Extract IaC files from GitHub push"""
    # In production, use GitHub API to fetch changed files
    # For MVP, return empty list
    return []


async def _extract_gitlab_iac_files(payload: Dict) -> List[Dict]:
    """Extract IaC files from GitLab merge request"""
    # In production, use GitLab API to fetch files
    # For MVP, return empty list
    return []


async def _extract_gitlab_push_iac_files(commits: List[Dict]) -> List[Dict]:
    """Extract IaC files from GitLab push"""
    # In production, use GitLab API to fetch changed files
    # For MVP, return empty list
    return []
