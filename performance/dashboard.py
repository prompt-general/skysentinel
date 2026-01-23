import asyncio
import time
import statistics
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, asdict
import aiohttp
import aiofiles
import psutil
from pathlib import Path

@dataclass
class DashboardMetric:
    """Dashboard metric data point"""
    timestamp: float
    metric_name: str
    value: float
    unit: str
    tags: List[str]
    source: str

@dataclass
class DashboardConfig:
    """Dashboard configuration"""
    refresh_interval: int
    history_duration: int
        # in minutes
    alert_thresholds: Dict[str, float]
    chart_configs: Dict[str, Dict]

class PerformanceDashboard:
    """Real-time performance dashboard for SkySentinel"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.aioredis_client = None
        self.metrics_history = []
        self.dashboard_config = DashboardConfig(
            refresh_interval=5,  # 5 seconds
            history_duration=60,  # 60 minutes
            alert_thresholds={
                "cpu_warning": 80.0,
                "cpu_critical": 95.0,
                "memory_warning": 85.0,
                "memory_critical": 95.0,
                "response_time_warning": 2.0,
                "response_time_critical": 5.0,
                "error_rate_warning": 5.0,
                "error_rate_critical": 10.0
            }
        )
        self.is_running = False
        self.dashboard_thread = None
        self.alert_handlers = []
        
    async def start_dashboard(self):
        """Start the dashboard"""
        if self.is_running:
            return
        
        try:
            # Initialize Redis clients
            self.redis_client = redis.Redis.from_url(self.redis_url)
            self.aioredis_client = await aioredis.from_url(self.redis_url)
            
            self.is_running = True
            self.dashboard_thread = threading.Thread(target=self._dashboard_loop)
            self.dashboard_thread.daemon = True
            self.dashboard_thread.start()
            
            logging.info("Performance dashboard started")
            
        except Exception as e:
            logging.error(f"Failed to start dashboard: {e}")
    
    def stop_dashboard(self):
        """Stop the dashboard"""
        self.is_running = False
        if self.dashboard_thread:
            self.dashboard_thread.join()
        
        if self.redis_client:
            self.redis_client.close()
        
        if self.aioredis_client:
            self.aioredis_client.close()
        
        logging.info("Performance dashboard stopped")
    
    def _dashboard_loop(self):
        """Main dashboard loop"""
        while self.is_running:
            try:
                # Collect current metrics
                current_time = time.time()
                
                # System metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk_io = psutil.disk_io_counters()
                net_io = psutil.net_io_counters()
                
                # Application metrics (from monitoring)
                app_metrics = self._get_application_metrics()
                
                # Create dashboard metrics
                dashboard_metrics = [
                    DashboardMetric(
                        timestamp=current_time,
                        metric_name="cpu_usage",
                        value=cpu_percent,
                        unit="%",
                        tags=["system", "cpu"],
                        source="system"
                    ),
                    DashboardMetric(
                        timestamp=current_time,
                        metric_name="memory_usage",
                        value=memory.percent,
                        unit="%",
                        tags=["system", "memory"],
                        source="system"
                    ),
                    DashboardMetric(
                        timestamp=current_time,
                        metric_name="disk_io",
                        value=(disk_io.read_bytes + disk_io.write_bytes) / 1024 / 1024, 2),  # MB/s
                        unit="MB/s",
                        tags=["system", "disk"],
                        source="system"
                    ),
                    DashboardMetric(
                        timestamp=current_time,
                        metric_name="network_io",
                        value=(net_io.bytes_sent + net_io.bytes_recv) / 1024 / 1024, 2),  # MB/s
                        unit="MB/s",
                        tags=["system", "network"],
                        source="system"
                    )
                ]
                
                # Add application metrics
                for metric in app_metrics:
                    dashboard_metrics.append(metric)
                
                # Store in Redis for real-time access
                await self._store_dashboard_metrics(dashboard_metrics)
                
                # Check for alerts
                self._check_alerts(dashboard_metrics)
                
                # Clean old metrics
                cutoff_time = current_time - (self.dashboard_config.history_duration * 60)
                self.metrics_history = [
                    m for m in self.metrics_history
                    if m.timestamp >= cutoff_time
                ]
                
                time.sleep(self.dashboard_config.refresh_interval)
                
            except Exception as e:
                logging.error(f"Dashboard error: {e}")
                time.sleep(5)
    
    def _get_application_metrics(self) -> List[DashboardMetric]:
        """Get application metrics from monitoring"""
        # This would integrate with the monitoring system
        app_metrics = []
        
        # Get recent application metrics from monitoring
        try:
            if self.aioredis_client:
                # Get recent application metrics from Redis
                recent_metrics = await self.aioredis_client.lrange(
                    f"performance:app:*",
                    start=0,
                    end=int(time.time()),
                    size=100
                )
                
                for metric_key in recent_metrics:
                    try:
                        data = json.loads(metric_key.decode())
                        if isinstance(data, dict) and "timestamp" in data:
                            app_metrics.append(DashboardMetric(
                                timestamp=data["timestamp"],
                                metric_name=data.get("metric_name"),
                                value=data.get("value", 0),
                                unit=data.get("unit", ""),
                                tags=data.get("tags", []),
                                source="application"
                            ))
                    except:
                        continue
        except Exception as e:
            logging.error(f"Failed to get application metrics: {e}")
        
        return app_metrics
    
    async def _store_dashboard_metrics(self, metrics: List[DashboardMetric]):
        """Store dashboard metrics in Redis"""
        try:
            if self.aioredis_client:
                for metric in metrics:
                    key = f"dashboard:{metric.metric_name}:{int(metric.timestamp)}"
                    value = json.dumps(asdict(metric))
                    await self.aioredis_client.setex(key, value, ex=3600)  # 1 hour
                
        except Exception as e:
            logging.error(f"Failed to store dashboard metrics: {e}")
    
    def _check_alerts(self, metrics: List[DashboardMetric]):
        """Check for performance alerts"""
        alerts = []
        
        for metric in metrics:
            alert_thresholds = self.dashboard_config.alert_thresholds
            metric_name = metric.metric_name
            
            if metric_name in alert_thresholds:
                threshold = alert_thresholds[metric_name]
                if metric.value >= threshold:
                    alerts.append({
                        "type": "performance",
                        "severity": "critical" if metric.value >= alert_thresholds[metric_name] * 1.1 else "warning",
                        "metric": metric_name,
                        "value": metric.value,
                        "threshold": threshold,
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
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data"""
        if not self.metrics_history:
            return {"error": "No data available"}
        
        # Get latest metrics
        latest_metrics = self.metrics_history[-100:] if len(self.metrics_history) > 100 else self.metrics_history
        
        # Calculate current metrics
        current_metrics = {}
        
        if latest_metrics:
            cpu_metrics = [m for m in latest_metrics if m.metric_name == "cpu_usage"]
            memory_metrics = [m for m in latest_metrics if m.metric_name == "memory_usage"]
            
            if cpu_metrics:
                current_metrics["cpu"] = {
                    "current": cpu_metrics[-1].value,
                    "avg": statistics.mean(m.value for m in cpu_metrics),
                    "min": min(m.value for m in cpu_metrics),
                    "max": max(m.value for m in cpu_metrics),
                    "trend": "increasing" if cpu_metrics[-1].value > cpu_metrics[0].value else "decreasing"
                }
            
            if memory_metrics:
                current_metrics["memory"] = {
                    "current": memory_metrics[-1].value,
                    "avg": statistics.mean(m.value for m in memory_metrics),
                    "min": min(m.value for m in memory_metrics),
                    "max": max(m.value for m in memory_metrics),
                    "trend": "increasing" if memory_metrics[-1].value > memory_metrics[0].value else "decreasing"
                }
        
        return {
            "timestamp": time.time(),
            "metrics": current_metrics,
            "alert_count": len(self._get_recent_alerts()),
            "system_resources": self._get_system_resources()
        }
    
    def _get_recent_alerts(self) -> List[Dict]:
        """Get recent alerts"""
        # This would typically query from Redis or a database
        return []
    
    def _get_system_resources(self) -> Dict[str, Any]:
        """Get current system resources"""
        try:
            return {
                "cpu_cores": psutil.cpu_count(),
                "cpu_freq": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
                "total_memory": psutil.virtual_memory().total,
                "available_memory": psutil.virtual_memory().available,
                "disk_space": psutil.disk_usage('/').total,
                "network_interfaces": list(psutil.net_if_addrs().keys()),
                "process_count": len(psutil.pids()),
                "active_connections": len(psutil.net_connections()) if hasattr(psutil, 'net_connections') else 0
            }
        except Exception as e:
            return {"error": f"Failed to get system resources: {e}"}
    
    def get_metrics_history(self, metric_name: str = None, 
                           duration_minutes: int = 60) -> List[DashboardMetric]:
        """Get historical metrics for a specific metric"""
        cutoff_time = time.time() - (duration_minutes * 60)
        
        if metric_name:
            filtered_metrics = [
                m for m in self.metrics_history
                if m.metric_name == metric_name and m.timestamp >= cutoff_time
            ]
        else:
            filtered_metrics = [
                m for m in self.metrics_history
                if m.timestamp >= cutoff_time
            ]
        
        return filtered_metrics
    
    def get_real_time_dashboard_data(self) -> Dict[str, Any]:
        """Get real-time dashboard data"""
        if not self.is_running:
            return {"error": "Dashboard not running"}
        
        current_metrics = self.get_dashboard_data()
        
        # Calculate real-time stats
        if "metrics" in current_metrics:
            cpu_metrics = [m for m in self.metrics_history if m.metric_name == "cpu_usage"]
            memory_metrics = [m for m in self.metrics_history if m.metric_name == "memory_usage"]
            
            if cpu_metrics and memory_metrics:
                cpu_trend = "increasing" if cpu_metrics[-1].value > cpu_metrics[0].value else "decreasing"
                memory_trend = "increasing" if memory_metrics[-1].value > memory_metrics[0].value else "decreasing"
                
                real_time_stats = {
                    "cpu_trend": cpu_trend,
                    "memory_trend": memory_trend,
                    "cpu_current": cpu_metrics[-1].value,
                    "memory_current": memory_metrics[-1].value,
                    "process_count": current_metrics.get("system_resources", {}).get("process_count", 0),
                    "active_connections": current_metrics.get("system_resources", {}).get("active_connections", 0)
                }
            else:
                real_time_stats = {}
        else:
            real_time_stats = {}
        
        return real_time_stats
    
    def generate_dashboard_html(self) -> str:
        """Generate HTML dashboard"""
        dashboard_data = self.get_real_time_dashboard_data()
        
        if "error" in dashboard_data:
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>SkySentinel Performance Dashboard</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .dashboard {{ background: #f8f9fa; padding: 20px; border-radius: 5px; }}
                    .metric {{ display: inline-block; margin: 10px; padding: 10px; background: white; border-radius: 3px; }}
                    .success {{ color: green; }}
                    .warning {{ color: orange; }}
                    .error {{ color: red; }}
                    .chart {{ height: 400px; margin: 20px 0; }}
                </style>
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            </head>
            <body>
                <h1>SkySentinel Performance Dashboard</h1>
                
                <div class="dashboard">
                    <h2>Real-time Metrics</h2>
                    <div class="metric">
                        <h3>CPU Usage</h3>
                        <p class="{'success' if dashboard_data.get("real_time_stats", {}).get("cpu_current", 0) < 80 else 'warning' if dashboard_data.get("real_time_stats", {}).get("cpu_current", 0) < 95 else 'error'}">
                            {dashboard_data.get("real_time_stats", {}).get("cpu_current", 0):.1f}%
                        </p>
                    </div>
                    
                    <div class="metric">
                        <h3>Memory Usage</h3>
                        <p class="{'success' if dashboard_data.get("real_time_stats", {}).get("memory_current", 0) < 80 else 'warning' if dashboard_data.get("real_time_stats", {}).get("memory_current", 0) < 95 else 'error'}">
                            {dashboard_data.get("real_time_stats", {}).get("memory_current", 0):.1f}%
                        </p>
                    </div>
                    
                    <div class="metric">
                        <h3>Process Count</h3>
                        <p>{dashboard_data.get("real_time_stats", {}).get("process_count", 0)}</p>
                    </div>
                    
                    <div class="metric">
                        <h3>Active Connections</h3>
                        <p>{dashboard_data.get("real_time_stats", {}).get("active_connections", 0)}</p>
                    </div>
                </div>
                
                <h2>Performance Trends</h2>
                <div class="chart">
                    <canvas id="trendsChart"></canvas>
                </div>
                
                <h2>Recent Alerts</h2>
                <div class="dashboard">
                    <p>Recent alerts: {dashboard_data.get("alert_count", 0)}</p>
                </div>
            </body>
            
            <script>
                // CPU and Memory trends chart
                const ctx = document.getElementById('trendsChart').getContext('2d');
                const cpu_data = [
                    {{"x": m.timestamp, "y": m.value} for m in [m for m in self.metrics_history if m.metric_name == "cpu_usage"][-100:]],
                    {{"x": m.timestamp, "y": m.value} for m in [m for m in self.metrics_history if m.metric_name == "memory_usage"][-100:]}
                ];
                
                const chart = new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        datasets: [
                            {{
                                label: 'CPU Usage (%)',
                                data: cpu_data,
                                borderColor: 'rgb(255, 99, 132)',
                                tension: 0.1
                            }},
                            {{
                                label: 'Memory Usage (%)',
                                data: memory_data,
                                borderColor: 'rgb(54, 162, 235)',
                                tension: 0.1
                            }}
                        ]
                    }},
                    options: {{
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                max: 100,
                                title: 'Usage (%)'
                            }}
                        }}
                    }}
                });
            </script>
        </body>
        </html>
        """
        
        return html
    
    def export_dashboard_data(self, format: str = "json", duration_minutes: int = 60) -> str:
        """Export dashboard data"""
        cutoff_time = time.time() - (duration_minutes * 60)
        
        # Collect recent metrics
        recent_metrics = [
            m for m in self.metrics_history
            if m.timestamp >= cutoff_time
        ]
        
        export_data = {
            "export_timestamp": time.time(),
            "duration_minutes": duration_minutes,
            "total_metrics": len(recent_metrics),
            "metrics": [asdict(m) for m in recent_metrics],
            "system_resources": self.get_system_resources()
        }
        
        if format == "json":
            return json.dumps(export_data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def create_performance_dashboard(self, output_path: str = "performance_dashboard.html"):
        """Create performance dashboard HTML file"""
        html = self.generate_dashboard_html()
        
        try:
            with open(output_path, "w") as f:
                f.write(html)
            logging.info(f"Performance dashboard saved to {output_path}")
        except Exception as e:
            logging.error(f"Failed to save dashboard: {e}")


class RealTimeMonitor:
    """Real-time performance monitoring"""
    
    def __init__(self):
        self.monitoring = False
        self.metrics = []
        self.alerts = []
    
    def start_monitoring(self):
        """Start real-time monitoring"""
        self.monitoring = True
        monitor_thread = threading.Thread(target=self._monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop real-time monitoring"""
        self.monitoring = False
        if monitor_thread:
            monitor_thread.join()
    
    def _monitor_loop(self):
        """Real-time monitoring loop"""
        while self.monitoring:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil virtual_memory().percent
                
                # Create metric
                metric = DashboardMetric(
                    timestamp=time.time(),
                    metric_name="cpu_usage",
                    value=cpu_percent,
                    unit="%",
                    tags=["system", "cpu"],
                    source="system"
                )
                
                self.metrics.append(metric)
                
                # Check for alerts
                if cpu_percent > 90:
                    self.alerts.append({
                        "type": "system",
                        "severity": "critical",
                        "metric": "cpu",
                        "value": cpu_percent,
                        "timestamp": metric.timestamp,
                        "message": "High CPU usage detected"
                    })
                
                # Clean old metrics (keep last 100)
                if len(self.metrics) > 100:
                    self.metrics = self.metrics[-100:]
                
                time.sleep(1)
                
            except Exception as e:
                logging.error(f"Monitoring error: {e}")
                time.sleep(5)


# Example usage
async def main():
    """Example performance dashboard usage"""
    dashboard = PerformanceDashboard()
    
    # Start dashboard
    dashboard.start_dashboard()
    
    # Monitor for 5 minutes
    await asyncio.sleep(300)
    
    # Get dashboard data
    dashboard_data = dashboard.get_real_time_dashboard_data()
    print(f"Current CPU: {dashboard_data.get('real_time_stats', {}).get('cpu_current', 0):.1f}%")
    print(f"Current Memory: {dashboard_data.get('real_time_stats', {}).get('memory_current', 0):.1f}%")
    
    # Export dashboard data
    dashboard.export_dashboard_data()
    
    # Stop dashboard
    dashboard.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
