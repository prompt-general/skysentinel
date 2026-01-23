import asyncio
import time
import statistics
import psutil
import threading
from typing import Dict, List, Any, Optional
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import redis
import aioredis
from concurrent.futures import ThreadPoolExecutor
import logging

@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_available: float
    memory_used: float
    disk_usage_percent: float
    disk_read_bytes: float
    disk_write_bytes: float
    network_sent_bytes: float
    network_recv_bytes: float
    active_connections: int
    process_count: int
    load_average: List[float]

@dataclass
class ApplicationMetric:
    """Application-specific performance metric"""
    timestamp: float
    endpoint: str
    method: str
    response_time: float
    status_code: int
    success: bool
    error_type: Optional[str]
    user_id: Optional[str]
    tenant_id: Optional[str]
    request_size: int
    response_size: int

@dataclass
class DatabaseMetric:
    """Database performance metric"""
    timestamp: float
    query_time: float
    query_type: str
    table_name: str
    rows_affected: int
    index_used: bool
    cache_hit: bool
    connection_pool_size: int
    active_connections: int

class PerformanceMonitor:
    """Real-time performance monitoring for SkySentinel"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.aioredis_client = None
        self.is_monitoring = False
        self.monitoring_thread = None
        self.metrics_history = []
        self.app_metrics_history = []
        self.db_metrics_history = []
        self.alert_thresholds = self._load_alert_thresholds()
        self.alert_handlers = []
        
    def _load_alert_thresholds(self) -> Dict[str, float]:
        """Load alert thresholds"""
        return {
            "cpu_warning": 70.0,
            "cpu_critical": 90.0,
            "memory_warning": 80.0,
            "memory_critical": 95.0,
            "disk_warning": 85.0,
            "disk_critical": 95.0,
            "response_time_warning": 2.0,
            "response_time_critical": 5.0,
            "error_rate_warning": 5.0,
            "error_rate_critical": 10.0
        }
    
    async def start_monitoring(self):
        """Start performance monitoring"""
        if self.is_monitoring:
            return
        
        try:
            # Initialize Redis clients
            self.redis_client = redis.Redis.from_url(self.redis_url)
            self.aioredis_client = await aioredis.from_url(self.redis_url)
            
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
            
            logging.info("Performance monitoring started")
            
        except Exception as e:
            logging.error(f"Failed to start monitoring: {e}")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
        
        if self.redis_client:
            self.redis_client.close()
        
        logging.info("Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Collect system metrics
                system_metric = self._collect_system_metrics()
                self.metrics_history.append(system_metric)
                
                # Store in Redis for real-time access
                self._store_metric_redis("system", system_metric)
                
                # Check for alerts
                self._check_system_alerts(system_metric)
                
                # Clean old metrics (keep last 1000)
                if len(self.metrics_history) > 1000:
                    self.metrics_history = self.metrics_history[-1000:]
                
                time.sleep(1)  # Collect metrics every second
                
            except Exception as e:
                logging.error(f"Monitoring error: {e}")
                time.sleep(5)  # Wait before retrying
    
    def _collect_system_metrics(self) -> PerformanceMetric:
        """Collect system performance metrics"""
        timestamp = time.time()
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_available = memory.available / 1024 / 1024 / 1024  # GB
        memory_used = memory.used / 1024 / 1024 / 1024  # GB
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_usage_percent = disk.percent
        
        # I/O metrics
        disk_io = psutil.disk_io_counters()
        disk_read_bytes = disk_io.read_bytes / 1024 / 1024  # MB
        disk_write_bytes = disk_io.write_bytes / 1024 / 1024  # MB
        
        # Network metrics
        net_io = psutil.net_io_counters()
        network_sent_bytes = net_io.bytes_sent / 1024 / 1024  # MB
        network_recv_bytes = net_io.bytes_recv / 1024 / 1024  # MB
        
        # Process metrics
        process_count = len(psutil.pids())
        
        # Network connections
        try:
            active_connections = len(psutil.net_connections())
        except:
            active_connections = 0
        
        # Load average (Unix systems)
        try:
            load_average = list(psutil.getloadavg())
        except:
            load_average = [0.0, 0.0, 0.0]
        
        return PerformanceMetric(
            timestamp=timestamp,
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_available=memory_available,
            memory_used=memory_used,
            disk_usage_percent=disk_usage_percent,
            disk_read_bytes=disk_read_bytes,
            disk_write_bytes=disk_write_bytes,
            network_sent_bytes=network_sent_bytes,
            network_recv_bytes=network_recv_bytes,
            active_connections=active_connections,
            process_count=process_count,
            load_average=load_average
        )
    
    def record_application_metric(self, metric: ApplicationMetric):
        """Record application-specific metric"""
        self.app_metrics_history.append(metric)
        
        # Store in Redis
        self._store_metric_redis("application", metric)
        
        # Check for alerts
        self._check_application_alerts(metric)
        
        # Clean old metrics
        if len(self.app_metrics_history) > 10000:
            self.app_metrics_history = self.app_metrics_history[-10000:]
    
    def record_database_metric(self, metric: DatabaseMetric):
        """Record database performance metric"""
        self.db_metrics_history.append(metric)
        
        # Store in Redis
        self._store_metric_redis("database", metric)
        
        # Check for alerts
        self._check_database_alerts(metric)
        
        # Clean old metrics
        if len(self.db_metrics_history) > 10000:
            self.db_metrics_history = self.db_metrics_history[-10000:]
    
    def _store_metric_redis(self, metric_type: str, metric):
        """Store metric in Redis"""
        try:
            if self.aioredis_client:
                key = f"performance:{metric_type}:{metric.timestamp}"
                value = json.dumps(asdict(metric))
                self.aioredis_client.setex(key, 3600, value)  # Keep for 1 hour
        except Exception as e:
            logging.error(f"Failed to store metric in Redis: {e}")
    
    def _check_system_alerts(self, metric: PerformanceMetric):
        """Check for system performance alerts"""
        alerts = []
        
        # CPU alerts
        if metric.cpu_percent >= self.alert_thresholds["cpu_critical"]:
            alerts.append({
                "type": "system",
                "severity": "critical",
                "metric": "cpu",
                "value": metric.cpu_percent,
                "threshold": self.alert_thresholds["cpu_critical"],
                "timestamp": metric.timestamp
            })
        elif metric.cpu_percent >= self.alert_thresholds["cpu_warning"]:
            alerts.append({
                "type": "system",
                "severity": "warning",
                "metric": "cpu",
                "value": metric.cpu_percent,
                "threshold": self.alert_thresholds["cpu_warning"],
                "timestamp": metric.timestamp
            })
        
        # Memory alerts
        if metric.memory_percent >= self.alert_thresholds["memory_critical"]:
            alerts.append({
                "type": "system",
                "severity": "critical",
                "metric": "memory",
                "value": metric.memory_percent,
                "threshold": self.alert_thresholds["memory_critical"],
                "timestamp": metric.timestamp
            })
        elif metric.memory_percent >= self.alert_thresholds["memory_warning"]:
            alerts.append({
                "type": "system",
                "severity": "warning",
                "metric": "memory",
                "value": metric.memory_percent,
                "threshold": self.alert_thresholds["memory_warning"],
                "timestamp": metric.timestamp
            })
        
        # Disk alerts
        if metric.disk_usage_percent >= self.alert_thresholds["disk_critical"]:
            alerts.append({
                "type": "system",
                "severity": "critical",
                "metric": "disk",
                "value": metric.disk_usage_percent,
                "threshold": self.alert_thresholds["disk_critical"],
                "timestamp": metric.timestamp
            })
        elif metric.disk_usage_percent >= self.alert_thresholds["disk_warning"]:
            alerts.append({
                "type": "system",
                "severity": "warning",
                "metric": "disk",
                "value": metric.disk_usage_percent,
                "threshold": self.alert_thresholds["disk_warning"],
                "timestamp": metric.timestamp
            })
        
        # Trigger alert handlers
        for alert in alerts:
            self._trigger_alert(alert)
    
    def _check_application_alerts(self, metric: ApplicationMetric):
        """Check for application performance alerts"""
        alerts = []
        
        # Response time alerts
        if metric.response_time >= self.alert_thresholds["response_time_critical"]:
            alerts.append({
                "type": "application",
                "severity": "critical",
                "metric": "response_time",
                "value": metric.response_time,
                "threshold": self.alert_thresholds["response_time_critical"],
                "endpoint": metric.endpoint,
                "timestamp": metric.timestamp
            })
        elif metric.response_time >= self.alert_thresholds["response_time_warning"]:
            alerts.append({
                "type": "application",
                "severity": "warning",
                "metric": "response_time",
                "value": metric.response_time,
                "threshold": self.alert_thresholds["response_time_warning"],
                "endpoint": metric.endpoint,
                "timestamp": metric.timestamp
            })
        
        # Error rate alerts (check recent metrics)
        recent_metrics = [m for m in self.app_metrics_history 
                         if m.timestamp > metric.timestamp - 60 and m.endpoint == metric.endpoint]
        if recent_metrics:
            error_rate = sum(1 for m in recent_metrics if not m.success) / len(recent_metrics) * 100
            
            if error_rate >= self.alert_thresholds["error_rate_critical"]:
                alerts.append({
                    "type": "application",
                    "severity": "critical",
                    "metric": "error_rate",
                    "value": error_rate,
                    "threshold": self.alert_thresholds["error_rate_critical"],
                    "endpoint": metric.endpoint,
                    "timestamp": metric.timestamp
                })
            elif error_rate >= self.alert_thresholds["error_rate_warning"]:
                alerts.append({
                    "type": "application",
                    "severity": "warning",
                    "metric": "error_rate",
                    "value": error_rate,
                    "threshold": self.alert_thresholds["error_rate_warning"],
                    "endpoint": metric.endpoint,
                    "timestamp": metric.timestamp
                })
        
        # Trigger alert handlers
        for alert in alerts:
            self._trigger_alert(alert)
    
    def _check_database_alerts(self, metric: DatabaseMetric):
        """Check for database performance alerts"""
        alerts = []
        
        # Query time alerts
        if metric.query_time >= 5.0:  # 5 seconds threshold
            alerts.append({
                "type": "database",
                "severity": "warning",
                "metric": "query_time",
                "value": metric.query_time,
                "threshold": 5.0,
                "query_type": metric.query_type,
                "table": metric.table_name,
                "timestamp": metric.timestamp
            })
        
        # Connection pool alerts
        if metric.active_connections >= metric.connection_pool_size * 0.9:
            alerts.append({
                "type": "database",
                "severity": "warning",
                "metric": "connection_pool",
                "value": metric.active_connections,
                "threshold": metric.connection_pool_size * 0.9,
                "timestamp": metric.timestamp
            })
        
        # Trigger alert handlers
        for alert in alerts:
            self._trigger_alert(alert)
    
    def _trigger_alert(self, alert: Dict):
        """Trigger alert handlers"""
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logging.error(f"Alert handler error: {e}")
    
    def add_alert_handler(self, handler):
        """Add custom alert handler"""
        self.alert_handlers.append(handler)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        if not self.metrics_history:
            return {"error": "No metrics available"}
        
        current = self.metrics_history[-1]
        return {
            "system": asdict(current),
            "timestamp": current.timestamp
        }
    
    def get_metrics_history(self, metric_type: str = "system", 
                           duration_minutes: int = 60) -> List[Dict]:
        """Get metrics history for specified duration"""
        cutoff_time = time.time() - (duration_minutes * 60)
        
        if metric_type == "system":
            history = [asdict(m) for m in self.metrics_history if m.timestamp >= cutoff_time]
        elif metric_type == "application":
            history = [asdict(m) for m in self.app_metrics_history if m.timestamp >= cutoff_time]
        elif metric_type == "database":
            history = [asdict(m) for m in self.db_metrics_history if m.timestamp >= cutoff_time]
        else:
            return []
        
        return history
    
    def get_performance_summary(self, duration_minutes: int = 60) -> Dict[str, Any]:
        """Get performance summary for specified duration"""
        cutoff_time = time.time() - (duration_minutes * 60)
        
        # System metrics summary
        system_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        if system_metrics:
            system_summary = {
                "avg_cpu": statistics.mean(m.cpu_percent for m in system_metrics),
                "max_cpu": max(m.cpu_percent for m in system_metrics),
                "avg_memory": statistics.mean(m.memory_percent for m in system_metrics),
                "max_memory": max(m.memory_percent for m in system_metrics),
                "avg_disk": statistics.mean(m.disk_usage_percent for m in system_metrics),
                "max_disk": max(m.disk_usage_percent for m in system_metrics),
                "avg_load": statistics.mean(m.load_average[0] for m in system_metrics),
                "max_load": max(m.load_average[0] for m in system_metrics)
            }
        else:
            system_summary = {}
        
        # Application metrics summary
        app_metrics = [m for m in self.app_metrics_history if m.timestamp >= cutoff_time]
        if app_metrics:
            successful_requests = [m for m in app_metrics if m.success]
            app_summary = {
                "total_requests": len(app_metrics),
                "successful_requests": len(successful_requests),
                "error_rate": (len(app_metrics) - len(successful_requests)) / len(app_metrics) * 100,
                "avg_response_time": statistics.mean(m.response_time for m in successful_requests),
                "max_response_time": max(m.response_time for m in app_metrics),
                "p95_response_time": sorted(m.response_time for m in app_metrics)[int(len(app_metrics) * 0.95)],
                "requests_per_second": len(app_metrics) / duration_minutes / 60,
                "top_endpoints": self._get_top_endpoints(app_metrics)
            }
        else:
            app_summary = {}
        
        # Database metrics summary
        db_metrics = [m for m in self.db_metrics_history if m.timestamp >= cutoff_time]
        if db_metrics:
            db_summary = {
                "total_queries": len(db_metrics),
                "avg_query_time": statistics.mean(m.query_time for m in db_metrics),
                "max_query_time": max(m.query_time for m in db_metrics),
                "cache_hit_rate": sum(1 for m in db_metrics if m.cache_hit) / len(db_metrics) * 100,
                "avg_connections": statistics.mean(m.active_connections for m in db_metrics),
                "max_connections": max(m.active_connections for m in db_metrics),
                "top_tables": self._get_top_tables(db_metrics)
            }
        else:
            db_summary = {}
        
        return {
            "duration_minutes": duration_minutes,
            "system": system_summary,
            "application": app_summary,
            "database": db_summary,
            "timestamp": time.time()
        }
    
    def _get_top_endpoints(self, metrics: List[ApplicationMetric]) -> List[Dict]:
        """Get top endpoints by request count"""
        endpoint_counts = {}
        response_times = {}
        
        for metric in metrics:
            endpoint = metric.endpoint
            if endpoint not in endpoint_counts:
                endpoint_counts[endpoint] = 0
                response_times[endpoint] = []
            
            endpoint_counts[endpoint] += 1
            response_times[endpoint].append(metric.response_time)
        
        # Sort by request count
        sorted_endpoints = sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {
                "endpoint": endpoint,
                "request_count": count,
                "avg_response_time": statistics.mean(response_times[endpoint]),
                "max_response_time": max(response_times[endpoint])
            }
            for endpoint, count in sorted_endpoints[:10]
        ]
    
    def _get_top_tables(self, metrics: List[DatabaseMetric]) -> List[Dict]:
        """Get top database tables by query count"""
        table_counts = {}
        query_times = {}
        
        for metric in metrics:
            table = metric.table_name
            if table not in table_counts:
                table_counts[table] = 0
                query_times[table] = []
            
            table_counts[table] += 1
            query_times[table].append(metric.query_time)
        
        # Sort by query count
        sorted_tables = sorted(table_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {
                "table": table,
                "query_count": count,
                "avg_query_time": statistics.mean(query_times[table]),
                "max_query_time": max(query_times[table])
            }
            for table, count in sorted_tables[:10]
        ]
    
    def get_real_time_dashboard_data(self) -> Dict[str, Any]:
        """Get real-time dashboard data"""
        current_metrics = self.get_current_metrics()
        
        # Recent application metrics (last 5 minutes)
        recent_app_metrics = self.get_metrics_history("application", 5)
        
        # Calculate real-time stats
        if recent_app_metrics:
            recent_success = [m for m in recent_app_metrics if m.success]
            real_time_stats = {
                "requests_per_second": len(recent_app_metrics) / 300,
                "success_rate": len(recent_success) / len(recent_app_metrics) * 100,
                "avg_response_time": statistics.mean(m.response_time for m in recent_success) if recent_success else 0,
                "active_endpoints": len(set(m.endpoint for m in recent_app_metrics))
            }
        else:
            real_time_stats = {
                "requests_per_second": 0,
                "success_rate": 100,
                "avg_response_time": 0,
                "active_endpoints": 0
            }
        
        return {
            "timestamp": time.time(),
            "system": current_metrics.get("system", {}),
            "real_time": real_time_stats,
            "recent_alerts": self._get_recent_alerts()
        }
    
    def _get_recent_alerts(self) -> List[Dict]:
        """Get recent alerts (last 5 minutes)"""
        # This would typically be stored in Redis or a database
        # For now, return empty list
        return []
    
    def export_metrics(self, format: str = "json", duration_minutes: int = 60) -> str:
        """Export metrics to file"""
        data = {
            "export_timestamp": time.time(),
            "duration_minutes": duration_minutes,
            "system_metrics": self.get_metrics_history("system", duration_minutes),
            "application_metrics": self.get_metrics_history("application", duration_minutes),
            "database_metrics": self.get_metrics_history("database", duration_minutes),
            "summary": self.get_performance_summary(duration_minutes)
        }
        
        if format == "json":
            return json.dumps(data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported format: {format}")


class PerformanceAlertHandler:
    """Default performance alert handler"""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url
    
    def __call__(self, alert: Dict):
        """Handle performance alert"""
        print(f"ALERT: {alert['type'].upper()} - {alert['metric']} = {alert['value']:.2f} (threshold: {alert['threshold']:.2f})")
        
        # Send webhook if configured
        if self.webhook_url:
            self._send_webhook(alert)
    
    def _send_webhook(self, alert: Dict):
        """Send alert webhook"""
        try:
            import requests
            
            payload = {
                "alert_type": alert["type"],
                "severity": alert["severity"],
                "metric": alert["metric"],
                "value": alert["value"],
                "threshold": alert["threshold"],
                "timestamp": alert["timestamp"],
                "service": "skysentinel-performance"
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=5)
            response.raise_for_status()
            
        except Exception as e:
            print(f"Failed to send webhook: {e}")


# Example usage
async def main():
    """Example performance monitoring usage"""
    monitor = PerformanceMonitor()
    
    # Add alert handler
    monitor.add_alert_handler(PerformanceAlertHandler())
    
    # Start monitoring
    await monitor.start_monitoring()
    
    # Simulate some application metrics
    for i in range(10):
        metric = ApplicationMetric(
            timestamp=time.time(),
            endpoint="/api/v1/dashboard",
            method="GET",
            response_time=0.1 + random.random() * 0.5,
            status_code=200,
            success=True,
            user_id=f"user_{i}",
            tenant_id="tenant_1",
            request_size=100,
            response_size=500
        )
        monitor.record_application_metric(metric)
        await asyncio.sleep(1)
    
    # Get performance summary
    summary = monitor.get_performance_summary(duration_minutes=5)
    print(f"Performance Summary: {json.dumps(summary, indent=2, default=str)}")
    
    # Get real-time dashboard data
    dashboard_data = monitor.get_real_time_dashboard_data()
    print(f"Dashboard Data: {json.dumps(dashboard_data, indent=2, default=str)}")
    
    # Stop monitoring
    monitor.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
