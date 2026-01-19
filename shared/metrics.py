from prometheus_client import Counter, Gauge, Histogram, start_http_server
import time
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SkySentinelMetrics:
    """Prometheus metrics collection for SkySentinel"""
    
    def __init__(self, port: int = 8000):
        # Event metrics
        self.events_processed = Counter(
            'skysentinel_events_processed_total',
            'Total events processed',
            ['cloud', 'event_type']
        )
        
        self.event_processing_duration = Histogram(
            'skysentinel_event_processing_duration_seconds',
            'Time spent processing events',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
        )
        
        self.events_queue_size = Gauge(
            'skysentinel_events_queue_size',
            'Current size of event processing queue'
        )
        
        # Graph metrics
        self.graph_nodes_total = Gauge(
            'skysentinel_graph_nodes_total',
            'Total nodes in graph',
            ['node_type']
        )
        
        self.graph_relationships_total = Gauge(
            'skysentinel_graph_relationships_total',
            'Total relationships in graph'
        )
        
        self.graph_query_duration = Histogram(
            'skysentinel_graph_query_duration_seconds',
            'Time spent executing graph queries',
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
        )
        
        # Policy engine metrics
        self.policy_evaluations = Counter(
            'skysentinel_policy_evaluations_total',
            'Total policy evaluations',
            ['policy_type', 'result']
        )
        
        self.policy_evaluation_duration = Histogram(
            'skysentinel_policy_evaluation_duration_seconds',
            'Time spent evaluating policies',
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0]
        )
        
        # Alert metrics
        self.alerts_generated = Counter(
            'skysentinel_alerts_generated_total',
            'Total alerts generated',
            ['severity', 'alert_type']
        )
        
        self.alerts_suppressed = Counter(
            'skysentinel_alerts_suppressed_total',
            'Total alerts suppressed',
            ['suppression_reason']
        )
        
        # Error metrics
        self.processing_errors = Counter(
            'skysentinel_processing_errors_total',
            'Total processing errors',
            ['error_type', 'component']
        )
        
        self.api_requests = Counter(
            'skysentinel_api_requests_total',
            'Total API requests',
            ['method', 'endpoint', 'status']
        )
        
        self.api_request_duration = Histogram(
            'skysentinel_api_request_duration_seconds',
            'Time spent processing API requests',
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
        )
        
        # System metrics
        self.memory_usage = Gauge(
            'skysentinel_memory_usage_bytes',
            'Memory usage in bytes'
        )
        
        self.cpu_usage = Gauge(
            'skysentinel_cpu_usage_percent',
            'CPU usage percentage'
        )
        
        # Database connection metrics
        self.db_connections_active = Gauge(
            'skysentinel_db_connections_active',
            'Active database connections'
        )
        
        self.db_connection_errors = Counter(
            'skysentinel_db_connection_errors_total',
            'Database connection errors',
            ['database_type']
        )
        
        self.port = port
        self._server_started = False
    
    def start_metrics_server(self) -> None:
        """Start the Prometheus metrics HTTP server"""
        if not self._server_started:
            try:
                start_http_server(self.port)
                self._server_started = True
                logger.info(f"Prometheus metrics server started on port {self.port}")
            except Exception as e:
                logger.error(f"Failed to start metrics server: {e}")
                raise
    
    def record_event_processed(self, cloud: str, event_type: str, duration: float) -> None:
        """Record a processed event"""
        self.events_processed.labels(cloud=cloud, event_type=event_type).inc()
        self.event_processing_duration.observe(duration)
    
    def update_queue_size(self, size: int) -> None:
        """Update event queue size"""
        self.events_queue_size.set(size)
    
    def update_graph_metrics(self, driver) -> None:
        """Update graph size metrics"""
        try:
            with driver.session() as session:
                # Count nodes by type
                result = session.run("""
                    MATCH (n)
                    RETURN labels(n)[0] as type, count(*) as count
                """)
                
                # Reset existing node metrics
                self.graph_nodes_total.clear()
                
                for record in result:
                    node_type = record['type'] or 'Unknown'
                    self.graph_nodes_total.labels(node_type=node_type).set(record['count'])
                
                # Count relationships
                result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                self.graph_relationships_total.set(result.single()['count'])
                
        except Exception as e:
            logger.error(f"Failed to update graph metrics: {e}")
            self.processing_errors.labels(
                error_type='metrics_update', 
                component='graph'
            ).inc()
    
    def record_graph_query(self, duration: float) -> None:
        """Record graph query execution time"""
        self.graph_query_duration.observe(duration)
    
    def record_policy_evaluation(self, policy_type: str, result: str, duration: float) -> None:
        """Record policy evaluation"""
        self.policy_evaluations.labels(policy_type=policy_type, result=result).inc()
        self.policy_evaluation_duration.observe(duration)
    
    def record_alert_generated(self, severity: str, alert_type: str) -> None:
        """Record generated alert"""
        self.alerts_generated.labels(severity=severity, alert_type=alert_type).inc()
    
    def record_alert_suppressed(self, suppression_reason: str) -> None:
        """Record suppressed alert"""
        self.alerts_suppressed.labels(suppression_reason=suppression_reason).inc()
    
    def record_error(self, error_type: str, component: str) -> None:
        """Record processing error"""
        self.processing_errors.labels(error_type=error_type, component=component).inc()
    
    def record_api_request(self, method: str, endpoint: str, status: str, duration: float) -> None:
        """Record API request"""
        self.api_requests.labels(method=method, endpoint=endpoint, status=status).inc()
        self.api_request_duration.observe(duration)
    
    def update_system_metrics(self, memory_bytes: int, cpu_percent: float) -> None:
        """Update system resource metrics"""
        self.memory_usage.set(memory_bytes)
        self.cpu_usage.set(cpu_percent)
    
    def update_db_metrics(self, active_connections: int) -> None:
        """Update database connection metrics"""
        self.db_connections_active.set(active_connections)
    
    def record_db_connection_error(self, database_type: str) -> None:
        """Record database connection error"""
        self.db_connection_errors.labels(database_type=database_type).inc()
    
    def get_metrics_summary(self) -> dict:
        """Get a summary of current metrics"""
        try:
            from prometheus_client import REGISTRY
            import prometheus_client
            
            metrics_data = {}
            
            for metric_family in REGISTRY.collect():
                metric_name = metric_family.name
                metrics_data[metric_name] = []
                
                for sample in metric_family.samples:
                    metrics_data[metric_name].append({
                        'labels': dict(sample.labels),
                        'value': sample.value
                    })
            
            return metrics_data
            
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {}


# Global metrics instance
_metrics_instance: Optional[SkySentinelMetrics] = None


def get_metrics() -> SkySentinelMetrics:
    """Get the global metrics instance"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = SkySentinelMetrics()
    return _metrics_instance


def init_metrics(port: int = 8000) -> SkySentinelMetrics:
    """Initialize the metrics system"""
    global _metrics_instance
    _metrics_instance = SkySentinelMetrics(port=port)
    _metrics_instance.start_metrics_server()
    return _metrics_instance


# Context manager for timing operations
class MetricsTimer:
    """Context manager for timing operations and recording metrics"""
    
    def __init__(self, metric_histogram, labels: dict = None):
        self.metric_histogram = metric_histogram
        self.labels = labels or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            if self.labels:
                self.metric_histogram.labels(**self.labels).observe(duration)
            else:
                self.metric_histogram.observe(duration)


def time_graph_query(labels: dict = None):
    """Decorator for timing graph queries"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            metrics = get_metrics()
            with MetricsTimer(metrics.graph_query_duration, labels):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def time_event_processing(labels: dict = None):
    """Decorator for timing event processing"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            metrics = get_metrics()
            with MetricsTimer(metrics.event_processing_duration, labels):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def time_policy_evaluation(labels: dict = None):
    """Decorator for timing policy evaluation"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            metrics = get_metrics()
            with MetricsTimer(metrics.policy_evaluation_duration, labels):
                return func(*args, **kwargs)
        return wrapper
    return decorator
