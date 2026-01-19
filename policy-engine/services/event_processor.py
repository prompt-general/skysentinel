import asyncio
from typing import Dict, List, Any, Optional, Callable
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import redis
from pydantic import ValidationError
import logging
import uuid
from dataclasses import dataclass
from enum import Enum
import time
from collections import defaultdict

from ..schemas.policy import Policy, Severity
from shared.metrics import get_metrics, MetricsTimer

logger = logging.getLogger(__name__)


class EventPriority(str, Enum):
    """Event processing priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventStatus(str, Enum):
    """Event processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class ProcessingResult:
    """Result of event processing"""
    event_id: str
    status: EventStatus
    violations: List[Dict]
    processing_time: float
    error: Optional[str] = None
    retry_count: int = 0


class EventProcessor:
    """Real-time event processing service for SkySentinel"""
    
    def __init__(self, 
                 policy_engine,
                 redis_url: str = "redis://localhost:6379",
                 max_workers: int = 10,
                 batch_size: int = 100,
                 batch_timeout: float = 5.0):
        self.policy_engine = policy_engine
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        
        # Queue keys
        self.event_queue_key = "skysentinel:events:queue"
        self.priority_queue_prefix = "skysentinel:events:priority:"
        self.results_queue_key = "skysentinel:results:queue"
        self.dead_letter_key = "skysentinel:events:dead_letter"
        self.metrics_key = "skysentinel:metrics:processing"
        
        # Processing state
        self._running = False
        self._task = None
        self._event_handlers = defaultdict(list)
        self._processing_stats = {
            'total_processed': 0,
            'total_violations': 0,
            'total_errors': 0,
            'avg_processing_time': 0.0
        }
        
        # Metrics
        self.metrics = get_metrics()
        
    async def start(self):
        """Start the event processing service"""
        if self._running:
            logger.warning("Event processor is already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._process_event_stream())
        logger.info("Event processor started")
        
        # Start background tasks
        asyncio.create_task(self._update_metrics())
        asyncio.create_task(self._cleanup_old_events())
    
    async def stop(self):
        """Stop the event processing service"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        self.executor.shutdown(wait=True)
        logger.info("Event processor stopped")
    
    async def _process_event_stream(self):
        """Main event processing loop"""
        while self._running:
            try:
                # Process events in batches for efficiency
                events = await self._get_event_batch()
                
                if events:
                    await self._process_event_batch(events)
                else:
                    # No events, brief pause
                    await asyncio.sleep(0.1)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}")
                await asyncio.sleep(1)  # Brief pause on error
    
    async def _get_event_batch(self) -> List[Dict]:
        """Get a batch of events from queue"""
        events = []
        
        try:
            # Check priority queues first
            for priority in [EventPriority.CRITICAL, EventPriority.HIGH, EventPriority.MEDIUM]:
                priority_key = f"{self.priority_queue_prefix}{priority.value}"
                priority_events = self.redis.lrange(priority_key, 0, self.batch_size - len(events))
                
                for event_json in priority_events:
                    events.append(json.loads(event_json))
                
                if priority_events:
                    # Remove processed events from priority queue
                    self.redis.ltrim(priority_key, len(priority_events), -1)
                
                if len(events) >= self.batch_size:
                    break
            
            # Fill remaining slots from regular queue
            if len(events) < self.batch_size:
                remaining = self.batch_size - len(events)
                regular_events = self.redis.lrange(self.event_queue_key, 0, remaining - 1)
                
                for event_json in regular_events:
                    events.append(json.loads(event_json))
                
                if regular_events:
                    self.redis.ltrim(self.event_queue_key, len(regular_events), -1)
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting event batch: {e}")
            return []
    
    async def _process_event_batch(self, events: List[Dict]):
        """Process a batch of events concurrently"""
        if not events:
            return
        
        start_time = time.time()
        
        try:
            # Submit all events to thread pool
            loop = asyncio.get_event_loop()
            futures = []
            
            for event in events:
                future = loop.run_in_executor(
                    self.executor,
                    self._process_single_event,
                    event
                )
                futures.append((event['id'], future))
            
            # Wait for all to complete
            results = []
            for event_id, future in futures:
                try:
                    result = await future
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing event {event_id}: {e}")
                    results.append(ProcessingResult(
                        event_id=event_id,
                        status=EventStatus.FAILED,
                        violations=[],
                        processing_time=0.0,
                        error=str(e)
                    ))
            
            # Store results and update metrics
            await self._store_batch_results(results)
            
            # Update processing stats
            batch_time = time.time() - start_time
            self._update_processing_stats(results, batch_time)
            
            # Call event handlers
            await self._call_event_handlers(results)
            
        except Exception as e:
            logger.error(f"Error processing event batch: {e}")
    
    def _process_single_event(self, event: Dict) -> ProcessingResult:
        """Process a single event through policy engine"""
        start_time = time.time()
        event_id = event.get('id', 'unknown')
        
        try:
            # Validate event structure
            self._validate_event(event)
            
            # Add processing metadata
            event['processing_metadata'] = {
                'received_at': datetime.utcnow().isoformat(),
                'processor_id': id(self)
            }
            
            # Evaluate against all policies
            with MetricsTimer(self.metrics.event_processing_duration):
                violations = self.policy_engine.evaluate_event(event)
            
            processing_time = time.time() - start_time
            
            return ProcessingResult(
                event_id=event_id,
                status=EventStatus.COMPLETED,
                violations=violations,
                processing_time=processing_time
            )
            
        except ValidationError as e:
            logger.error(f"Invalid event structure for {event_id}: {e}")
            return ProcessingResult(
                event_id=event_id,
                status=EventStatus.FAILED,
                violations=[],
                processing_time=time.time() - start_time,
                error=f"Validation error: {e}"
            )
        except Exception as e:
            logger.error(f"Error evaluating event {event_id}: {e}")
            return ProcessingResult(
                event_id=event_id,
                status=EventStatus.FAILED,
                violations=[],
                processing_time=time.time() - start_time,
                error=str(e)
            )
    
    def _validate_event(self, event: Dict):
        """Validate event structure"""
        required_fields = ['id', 'cloud', 'event_type', 'timestamp']
        
        for field in required_fields:
            if field not in event:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate timestamp format
        if isinstance(event['timestamp'], str):
            try:
                datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
            except ValueError:
                raise ValidationError(f"Invalid timestamp format: {event['timestamp']}")
    
    async def _store_batch_results(self, results: List[ProcessingResult]):
        """Store batch processing results"""
        pipe = self.redis.pipeline()
        
        for result in results:
            # Store individual violation results
            for violation in result.violations:
                violation_key = f"skysentinel:violation:{violation['id']}"
                pipe.setex(
                    violation_key,
                    86400 * 7,  # 7 days TTL
                    json.dumps(violation)
                )
                
                # Push to results queue for downstream processing
                pipe.lpush(self.results_queue_key, json.dumps(violation))
            
            # Store processing result
            result_key = f"skysentinel:processing:{result.event_id}"
            result_data = {
                'event_id': result.event_id,
                'status': result.status.value,
                'violation_count': len(result.violations),
                'processing_time': result.processing_time,
                'error': result.error,
                'timestamp': datetime.utcnow().isoformat()
            }
            pipe.setex(result_key, 86400, json.dumps(result_data))
            
            # Update violation counters
            for violation in result.violations:
                severity = violation.get('severity', 'medium')
                pipe.hincrby(f"{self.metrics_key}:violations", severity, 1)
        
        # Execute pipeline
        await asyncio.get_event_loop().run_in_executor(
            self.executor,
            pipe.execute
        )
    
    def _update_processing_stats(self, results: List[ProcessingResult], batch_time: float):
        """Update processing statistics"""
        self._processing_stats['total_processed'] += len(results)
        
        total_violations = sum(len(r.violations) for r in results)
        self._processing_stats['total_violations'] += total_violations
        
        total_errors = sum(1 for r in results if r.status == EventStatus.FAILED)
        self._processing_stats['total_errors'] += total_errors
        
        # Update average processing time
        total_time = sum(r.processing_time for r in results)
        if self._processing_stats['total_processed'] > 0:
            self._processing_stats['avg_processing_time'] = (
                total_time / len(results)
            )
        
        # Update queue size metrics
        queue_size = self.redis.llen(self.event_queue_key)
        self.metrics.update_queue_size(queue_size)
    
    async def _call_event_handlers(self, results: List[ProcessingResult]):
        """Call registered event handlers"""
        for result in results:
            if result.violations:
                # Call violation handlers
                for handler in self._event_handlers['violation']:
                    try:
                        await handler(result)
                    except Exception as e:
                        logger.error(f"Error in violation handler: {e}")
            
            # Call completion handlers
            for handler in self._event_handlers['completion']:
                try:
                    await handler(result)
                except Exception as e:
                    logger.error(f"Error in completion handler: {e}")
    
    async def _update_metrics(self):
        """Periodically update Redis metrics"""
        while self._running:
            try:
                # Update processing metrics
                metrics_data = {
                    'total_processed': self._processing_stats['total_processed'],
                    'total_violations': self._processing_stats['total_violations'],
                    'total_errors': self._processing_stats['total_errors'],
                    'avg_processing_time': self._processing_stats['avg_processing_time'],
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                self.redis.setex(
                    f"{self.metrics_key}:stats",
                    3600,  # 1 hour TTL
                    json.dumps(metrics_data)
                )
                
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_old_events(self):
        """Clean up old event data"""
        while self._running:
            try:
                # Clean up processing results older than 24 hours
                pattern = "skysentinel:processing:*"
                keys = self.redis.keys(pattern)
                
                if keys:
                    # Check each key's TTL and remove if expired
                    pipe = self.redis.pipeline()
                    for key in keys:
                        ttl = self.redis.ttl(key)
                        if ttl == -1:  # No TTL set
                            pipe.expire(key, 86400)  # Set 24 hour TTL
                    
                    await asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        pipe.execute
                    )
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
                await asyncio.sleep(3600)
    
    def submit_event(self, event: Dict, priority: EventPriority = EventPriority.MEDIUM) -> str:
        """Submit event for processing (synchronous interface)"""
        if 'id' not in event:
            event['id'] = str(uuid.uuid4())
        
        event['submitted_at'] = datetime.utcnow().isoformat()
        
        # Add to appropriate queue based on priority
        if priority != EventPriority.MEDIUM:
            priority_key = f"{self.priority_queue_prefix}{priority.value}"
            self.redis.lpush(priority_key, json.dumps(event))
        else:
            self.redis.lpush(self.event_queue_key, json.dumps(event))
        
        logger.debug(f"Submitted event {event['id']} with priority {priority.value}")
        return event['id']
    
    def submit_events_batch(self, events: List[Dict], priority: EventPriority = EventPriority.MEDIUM):
        """Submit multiple events for processing"""
        pipe = self.redis.pipeline()
        
        for event in events:
            if 'id' not in event:
                event['id'] = str(uuid.uuid4())
            
            event['submitted_at'] = datetime.utcnow().isoformat()
            
            if priority != EventPriority.MEDIUM:
                priority_key = f"{self.priority_queue_prefix}{priority.value}"
                pipe.lpush(priority_key, json.dumps(event))
            else:
                pipe.lpush(self.event_queue_key, json.dumps(event))
        
        pipe.execute()
        logger.info(f"Submitted batch of {len(events)} events")
    
    async def get_violation_status(self, event_id: str) -> Dict:
        """Get violation status for an event"""
        try:
            # Check processing result first
            result_key = f"skysentinel:processing:{event_id}"
            result_data = self.redis.get(result_key)
            
            if result_data:
                result = json.loads(result_data)
                
                # Get violations
                pattern = f"skysentinel:violation:*{event_id}*"
                keys = self.redis.keys(pattern)
                
                violations = []
                for key in keys:
                    violation_data = self.redis.get(key)
                    if violation_data:
                        violations.append(json.loads(violation_data))
                
                return {
                    "event_id": event_id,
                    "status": result['status'],
                    "violation_count": result['violation_count'],
                    "violations": violations,
                    "has_critical": any(v.get('severity') == 'critical' for v in violations),
                    "processing_time": result.get('processing_time', 0.0),
                    "error": result.get('error'),
                    "timestamp": result.get('timestamp')
                }
            else:
                return {
                    "event_id": event_id,
                    "status": "not_found",
                    "violation_count": 0,
                    "violations": [],
                    "has_critical": False
                }
                
        except Exception as e:
            logger.error(f"Error getting violation status: {e}")
            return {
                "event_id": event_id,
                "status": "error",
                "error": str(e)
            }
    
    def get_queue_stats(self) -> Dict:
        """Get queue statistics"""
        try:
            stats = {
                'regular_queue_size': self.redis.llen(self.event_queue_key),
                'priority_queues': {},
                'results_queue_size': self.redis.llen(self.results_queue_key),
                'dead_letter_size': self.redis.llen(self.dead_letter_key),
                'processing_stats': self._processing_stats.copy()
            }
            
            # Get priority queue sizes
            for priority in EventPriority:
                priority_key = f"{self.priority_queue_prefix}{priority.value}"
                size = self.redis.llen(priority_key)
                stats['priority_queues'][priority.value] = size
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {}
    
    def add_event_handler(self, event_type: str, handler: Callable):
        """Add event handler for specific event types"""
        self._event_handlers[event_type].append(handler)
        logger.info(f"Added handler for {event_type} events")
    
    def remove_event_handler(self, event_type: str, handler: Callable):
        """Remove event handler"""
        if handler in self._event_handlers[event_type]:
            self._event_handlers[event_type].remove(handler)
            logger.info(f"Removed handler for {event_type} events")
    
    def get_processing_metrics(self) -> Dict:
        """Get detailed processing metrics"""
        try:
            # Get Redis metrics
            violation_metrics = self.redis.hgetall(f"{self.metrics_key}:violations")
            
            return {
                'processing_stats': self._processing_stats,
                'violation_counts': violation_metrics,
                'queue_stats': self.get_queue_stats(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting processing metrics: {e}")
            return {}
