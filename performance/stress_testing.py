import asyncio
import aiohttp
import time
import statistics
import psutil
import threading
from typing import Dict, List, Any, Optional
import json
import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum

class StressTestType(Enum):
    """Types of stress tests"""
    SPIKE = "spike"
    GRADUAL = "gradual"
    SURGE = "surge"
    BREAKPOINT = "breakpoint"
    ENDURANCE = "endurance"

@dataclass
class SystemMetrics:
    """System performance metrics"""
    cpu_percent: float
    memory_percent: float
    disk_io_read: float
    disk_io_write: float
    network_io_sent: float
    network_io_recv: float
    timestamp: float

class StressTest:
    """Stress testing framework for SkySentinel"""
    
    def __init__(self, base_url: str, auth_token: str = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}" if auth_token else ""
        }
        self.system_metrics = []
        self.monitoring_thread = None
        self.is_monitoring = False
    
    def start_system_monitoring(self):
        """Start system resource monitoring"""
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitor_system)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
    
    def stop_system_monitoring(self):
        """Stop system resource monitoring"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
    
    def _monitor_system(self):
        """Monitor system resources"""
        while self.is_monitoring:
            try:
                # Get CPU and memory usage
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                
                # Get disk I/O
                disk_io = psutil.disk_io_counters()
                disk_read = disk_io.read_bytes / 1024 / 1024  # MB
                disk_write = disk_io.write_bytes / 1024 / 1024  # MB
                
                # Get network I/O
                net_io = psutil.net_io_counters()
                net_sent = net_io.bytes_sent / 1024 / 1024  # MB
                net_recv = net_io.bytes_recv / 1024 / 1024  # MB
                
                metrics = SystemMetrics(
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    disk_io_read=disk_read,
                    disk_io_write=disk_write,
                    network_io_sent=net_sent,
                    network_io_recv=net_recv,
                    timestamp=time.time()
                )
                
                self.system_metrics.append(metrics)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
    
    async def spike_test(self, endpoint: str, base_users: int = 10, 
                         spike_users: int = 100, spike_duration: int = 30,
                         total_duration: int = 300) -> Dict[str, Any]:
        """Spike test: sudden increase in load"""
        results = {
            "test_type": StressTestType.SPIKE.value,
            "endpoint": endpoint,
            "base_users": base_users,
            "spike_users": spike_users,
            "spike_duration": spike_duration,
            "total_duration": total_duration,
            "system_metrics": [],
            "performance_metrics": [],
            "summary": {}
        }
        
        self.start_system_monitoring()
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                start_time = time.time()
                current_users = base_users
                spike_start = random.randint(60, total_duration - spike_duration - 60)
                
                while time.time() - start_time < total_duration:
                    elapsed = time.time() - start_time
                    
                    # Determine current user count
                    if spike_start <= elapsed <= spike_start + spike_duration:
                        current_users = spike_users
                    else:
                        current_users = base_users
                    
                    # Execute requests with current user count
                    tasks = []
                    for i in range(current_users):
                        task = self._make_request(session, endpoint, i)
                        tasks.append(task)
                    
                    # Wait for all requests to complete
                    await asyncio.gather(*tasks)
                    
                    # Record performance metrics
                    metrics = self._calculate_performance_metrics(tasks)
                    results["performance_metrics"].append({
                        "timestamp": elapsed,
                        "users": current_users,
                        "metrics": metrics
                    })
                    
                    # Control rate
                    await asyncio.sleep(1)
            
            # Stop monitoring
            self.stop_system_monitoring()
            results["system_metrics"] = self.system_metrics
            
            # Calculate summary
            results["summary"] = self._calculate_stress_summary(results)
            
        except Exception as e:
            self.stop_system_monitoring()
            results["error"] = str(e)
        
        return results
    
    async def gradual_test(self, endpoint: str, initial_users: int = 10,
                          max_users: int = 200, ramp_up_time: int = 120,
                          total_duration: int = 300) -> Dict[str, Any]:
        """Gradual test: slowly increase load"""
        results = {
            "test_type": StressTestType.GRADUAL.value,
            "endpoint": endpoint,
            "initial_users": initial_users,
            "max_users": max_users,
            "ramp_up_time": ramp_up_time,
            "total_duration": total_duration,
            "system_metrics": [],
            "performance_metrics": [],
            "summary": {}
        }
        
        self.start_system_monitoring()
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                start_time = time.time()
                current_users = initial_users
                user_increment = (max_users - initial_users) / ramp_up_time
                
                while time.time() - start_time < total_duration:
                    elapsed = time.time() - start_time
                    
                    # Gradually increase users
                    if elapsed < ramp_up_time:
                        current_users = min(initial_users + int(elapsed * user_increment), max_users)
                    else:
                        current_users = max_users
                    
                    # Execute requests
                    tasks = []
                    for i in range(int(current_users)):
                        task = self._make_request(session, endpoint, i)
                        tasks.append(task)
                    
                    await asyncio.gather(*tasks)
                    
                    # Record metrics
                    metrics = self._calculate_performance_metrics(tasks)
                    results["performance_metrics"].append({
                        "timestamp": elapsed,
                        "users": int(current_users),
                        "metrics": metrics
                    })
                    
                    await asyncio.sleep(1)
            
            self.stop_system_monitoring()
            results["system_metrics"] = self.system_metrics
            results["summary"] = self._calculate_stress_summary(results)
            
        except Exception as e:
            self.stop_system_monitoring()
            results["error"] = str(e)
        
        return results
    
    async def surge_test(self, endpoint: str, base_users: int = 10,
                        surge_users: int = 100, surge_count: int = 3,
                        surge_interval: int = 60, total_duration: int = 300) -> Dict[str, Any]:
        """Surge test: multiple load spikes"""
        results = {
            "test_type": StressTestType.SURGE.value,
            "endpoint": endpoint,
            "base_users": base_users,
            "surge_users": surge_users,
            "surge_count": surge_count,
            "surge_interval": surge_interval,
            "total_duration": total_duration,
            "system_metrics": [],
            "performance_metrics": [],
            "summary": {}
        }
        
        self.start_system_monitoring()
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                start_time = time.time()
                current_users = base_users
                surge_times = [i * surge_interval for i in range(1, surge_count + 1)]
                
                while time.time() - start_time < total_duration:
                    elapsed = time.time() - start_time
                    
                    # Check if it's time for a surge
                    if any(abs(elapsed - surge_time) < 1 for surge_time in surge_times):
                        current_users = surge_users
                    else:
                        current_users = base_users
                    
                    # Execute requests
                    tasks = []
                    for i in range(current_users):
                        task = self._make_request(session, endpoint, i)
                        tasks.append(task)
                    
                    await asyncio.gather(*tasks)
                    
                    # Record metrics
                    metrics = self._calculate_performance_metrics(tasks)
                    results["performance_metrics"].append({
                        "timestamp": elapsed,
                        "users": current_users,
                        "metrics": metrics
                    })
                    
                    await asyncio.sleep(1)
            
            self.stop_system_monitoring()
            results["system_metrics"] = self.system_metrics
            results["summary"] = self._calculate_stress_summary(results)
            
        except Exception as e:
            self.stop_system_monitoring()
            results["error"] = str(e)
        
        return results
    
    async def breakpoint_test(self, endpoint: str, initial_users: int = 10,
                             user_increment: int = 10, max_duration: int = 600,
                             failure_threshold: float = 0.05) -> Dict[str, Any]:
        """Breakpoint test: find the breaking point"""
        results = {
            "test_type": StressTestType.BREAKPOINT.value,
            "endpoint": endpoint,
            "initial_users": initial_users,
            "user_increment": user_increment,
            "max_duration": max_duration,
            "failure_threshold": failure_threshold,
            "system_metrics": [],
            "performance_metrics": [],
            "breakpoint": None,
            "summary": {}
        }
        
        self.start_system_monitoring()
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                start_time = time.time()
                current_users = initial_users
                breakpoint_found = False
                
                while time.time() - start_time < max_duration and not breakpoint_found:
                    elapsed = time.time() - start_time
                    
                    # Execute requests
                    tasks = []
                    for i in range(current_users):
                        task = self._make_request(session, endpoint, i)
                        tasks.append(task)
                    
                    await asyncio.gather(*tasks)
                    
                    # Calculate success rate
                    successful_tasks = [t for t in tasks if t.get("success", False)]
                    success_rate = len(successful_tasks) / len(tasks) if tasks else 0
                    
                    # Record metrics
                    metrics = self._calculate_performance_metrics(tasks)
                    results["performance_metrics"].append({
                        "timestamp": elapsed,
                        "users": current_users,
                        "success_rate": success_rate,
                        "metrics": metrics
                    })
                    
                    # Check for breakpoint
                    if success_rate < (1 - failure_threshold):
                        results["breakpoint"] = {
                            "users": current_users,
                            "success_rate": success_rate,
                            "timestamp": elapsed
                        }
                        breakpoint_found = True
                    else:
                        current_users += user_increment
                    
                    await asyncio.sleep(1)
            
            self.stop_system_monitoring()
            results["system_metrics"] = self.system_metrics
            results["summary"] = self._calculate_stress_summary(results)
            
        except Exception as e:
            self.stop_system_monitoring()
            results["error"] = str(e)
        
        return results
    
    async def endurance_test(self, endpoint: str, users: int = 50,
                            duration: int = 3600) -> Dict[str, Any]:
        """Endurance test: sustained load over time"""
        results = {
            "test_type": StressTestType.ENDURANCE.value,
            "endpoint": endpoint,
            "users": users,
            "duration": duration,
            "system_metrics": [],
            "performance_metrics": [],
            "summary": {}
        }
        
        self.start_system_monitoring()
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                start_time = time.time()
                
                while time.time() - start_time < duration:
                    elapsed = time.time() - start_time
                    
                    # Execute requests
                    tasks = []
                    for i in range(users):
                        task = self._make_request(session, endpoint, i)
                        tasks.append(task)
                    
                    await asyncio.gather(*tasks)
                    
                    # Record metrics
                    metrics = self._calculate_performance_metrics(tasks)
                    results["performance_metrics"].append({
                        "timestamp": elapsed,
                        "users": users,
                        "metrics": metrics
                    })
                    
                    await asyncio.sleep(1)
            
            self.stop_system_monitoring()
            results["system_metrics"] = self.system_metrics
            results["summary"] = self._calculate_stress_summary(results)
            
        except Exception as e:
            self.stop_system_monitoring()
            results["error"] = str(e)
        
        return results
    
    async def _make_request(self, session: aiohttp.ClientSession, 
                           endpoint: str, request_id: int) -> Dict[str, Any]:
        """Make a single request"""
        request_start = time.time()
        try:
            async with session.get(f"{self.base_url}{endpoint}") as response:
                status = response.status
                body = await response.text()
                request_time = time.time() - request_start
                
                return {
                    "id": request_id,
                    "status": status,
                    "response_time": request_time,
                    "success": status < 400,
                    "timestamp": request_start
                }
                
        except Exception as e:
            request_time = time.time() - request_start
            return {
                "id": request_id,
                "status": 0,
                "response_time": request_time,
                "success": False,
                "error": str(e),
                "timestamp": request_start
            }
    
    def _calculate_performance_metrics(self, tasks: List[Dict]) -> Dict[str, Any]:
        """Calculate performance metrics from task results"""
        successful_tasks = [t for t in tasks if t.get("success", False)]
        
        if not successful_tasks:
            return {
                "total_requests": len(tasks),
                "successful_requests": 0,
                "success_rate": 0,
                "avg_response_time": 0,
                "min_response_time": 0,
                "max_response_time": 0,
                "p50_response_time": 0,
                "p95_response_time": 0,
                "requests_per_second": 0
            }
        
        response_times = [t["response_time"] for t in successful_tasks]
        
        return {
            "total_requests": len(tasks),
            "successful_requests": len(successful_tasks),
            "success_rate": len(successful_tasks) / len(tasks) * 100,
            "avg_response_time": statistics.mean(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "p50_response_time": statistics.median(response_times),
            "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)],
            "p99_response_time": sorted(response_times)[int(len(response_times) * 0.99)],
            "requests_per_second": len(tasks) / 1  # Assuming 1 second intervals
        }
    
    def _calculate_stress_summary(self, results: Dict) -> Dict[str, Any]:
        """Calculate stress test summary"""
        performance_data = results["performance_metrics"]
        
        if not performance_data:
            return {"error": "No performance data available"}
        
        # Calculate overall metrics
        total_requests = sum(p["metrics"]["total_requests"] for p in performance_data)
        total_successful = sum(p["metrics"]["successful_requests"] for p in performance_data)
        
        response_times = []
        for p in performance_data:
            if p["metrics"]["successful_requests"] > 0:
                response_times.append(p["metrics"]["avg_response_time"])
        
        # Calculate system resource averages
        if self.system_metrics:
            avg_cpu = statistics.mean(m.cpu_percent for m in self.system_metrics)
            avg_memory = statistics.mean(m.memory_percent for m in self.system_metrics)
            max_cpu = max(m.cpu_percent for m in self.system_metrics)
            max_memory = max(m.memory_percent for m in self.system_metrics)
        else:
            avg_cpu = avg_memory = max_cpu = max_memory = 0
        
        summary = {
            "total_requests": total_requests,
            "successful_requests": total_successful,
            "overall_success_rate": total_successful / total_requests * 100 if total_requests > 0 else 0,
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "peak_users": max(p["users"] for p in performance_data),
            "avg_cpu_usage": avg_cpu,
            "max_cpu_usage": max_cpu,
            "avg_memory_usage": avg_memory,
            "max_memory_usage": max_memory,
            "test_duration": performance_data[-1]["timestamp"] if performance_data else 0
        }
        
        # Add breakpoint information if available
        if results.get("breakpoint"):
            summary["breakpoint"] = results["breakpoint"]
        
        return summary
    
    def generate_stress_report(self, results: Dict) -> str:
        """Generate HTML stress test report"""
        summary = results["summary"]
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SkySentinel Stress Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background: white; border-radius: 3px; min-width: 150px; }}
                .success {{ color: green; }}
                .warning {{ color: orange; }}
                .error {{ color: red; }}
                .chart {{ height: 400px; margin: 20px 0; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
            </style>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <h1>SkySentinel Stress Test Report</h1>
            <h2>Test Type: {results['test_type'].upper()}</h2>
            
            <div class="summary">
                <h3>Test Summary</h3>
                <div class="metric">
                    <h4>Success Rate</h4>
                    <p class="{'success' if summary['overall_success_rate'] > 95 else 'warning' if summary['overall_success_rate'] > 80 else 'error'}">
                        {summary['overall_success_rate']:.2f}%
                    </p>
                </div>
                <div class="metric">
                    <h4>Peak Users</h4>
                    <p>{summary['peak_users']}</p>
                </div>
                <div class="metric">
                    <h4>Avg Response Time</h4>
                    <p>{summary['avg_response_time']:.3f}s</p>
                </div>
                <div class="metric">
                    <h4>Max Response Time</h4>
                    <p>{summary['max_response_time']:.3f}s</p>
                </div>
                <div class="metric">
                    <h4>Total Requests</h4>
                    <p>{summary['total_requests']}</p>
                </div>
                <div class="metric">
                    <h4>Test Duration</h4>
                    <p>{summary['test_duration']:.2f}s</p>
                </div>
            </div>
            
            <div class="summary">
                <h3>System Resources</h3>
                <div class="metric">
                    <h4>Avg CPU Usage</h4>
                    <p>{summary['avg_cpu_usage']:.1f}%</p>
                </div>
                <div class="metric">
                    <h4>Max CPU Usage</h4>
                    <p>{summary['max_cpu_usage']:.1f}%</p>
                </div>
                <div class="metric">
                    <h4>Avg Memory Usage</h4>
                    <p>{summary['avg_memory_usage']:.1f}%</p>
                </div>
                <div class="metric">
                    <h4>Max Memory Usage</h4>
                    <p>{summary['max_memory_usage']:.1f}%</p>
                </div>
            </div>
            
            <h2>Performance Over Time</h2>
            <div class="chart">
                <canvas id="performanceChart"></canvas>
            </div>
            
            <h2>System Resources Over Time</h2>
            <div class="chart">
                <canvas id="resourceChart"></canvas>
            </div>
            
            <h2>Breakpoint Analysis</h2>
            {self._generate_breakpoint_section(results)}
            
            <script>
                // Performance chart
                const perfCtx = document.getElementById('performanceChart').getContext('2d');
                const perfChart = new Chart(perfCtx, {{
                    type: 'line',
                    data: {{
                        labels: {self._generate_time_labels(results)},
                        datasets: [
                            {{
                                label: 'Users',
                                data: {self._generate_user_data(results)},
                                borderColor: 'rgb(75, 192, 192)',
                                yAxisID: 'y'
                            }},
                            {{
                                label: 'Response Time (ms)',
                                data: {self._generate_response_time_data(results)},
                                borderColor: 'rgb(255, 99, 132)',
                                yAxisID: 'y1'
                            }},
                            {{
                                label: 'Success Rate (%)',
                                data: {self._generate_success_rate_data(results)},
                                borderColor: 'rgb(54, 162, 235)',
                                yAxisID: 'y2'
                            }}
                        ]
                    }},
                    options: {{
                        scales: {{
                            y: {{
                                type: 'linear',
                                display: true,
                                position: 'left',
                                title: {{
                                    display: true,
                                    text: 'Users'
                                }}
                            }},
                            y1: {{
                                type: 'linear',
                                display: true,
                                position: 'right',
                                title: {{
                                    display: true,
                                    text: 'Response Time (ms)'
                                }}
                            }},
                            y2: {{
                                type: 'linear',
                                display: false,
                                position: 'right',
                                min: 0,
                                max: 100,
                                title: {{
                                    display: true,
                                    text: 'Success Rate (%)'
                                }}
                            }}
                        }}
                    }}
                }});
                
                // Resource chart
                const resCtx = document.getElementById('resourceChart').getContext('2d');
                const resChart = new Chart(resCtx, {{
                    type: 'line',
                    data: {{
                        labels: {self._generate_time_labels(results)},
                        datasets: [
                            {{
                                label: 'CPU Usage (%)',
                                data: {self._generate_cpu_data(results)},
                                borderColor: 'rgb(255, 205, 86)',
                                backgroundColor: 'rgba(255, 205, 86, 0.2)'
                            }},
                            {{
                                label: 'Memory Usage (%)',
                                data: {self._generate_memory_data(results)},
                                borderColor: 'rgb(54, 162, 235)',
                                backgroundColor: 'rgba(54, 162, 235, 0.2)'
                            }}
                        ]
                    }},
                    options: {{
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                max: 100,
                                title: {{
                                    display: true,
                                    text: 'Usage (%)'
                                }}
                            }}
                        }}
                    }}
                }});
            </script>
        </body>
        </html>
        """
        
        return html
    
    def _generate_breakpoint_section(self, results: Dict) -> str:
        """Generate breakpoint analysis section"""
        if results.get("breakpoint"):
            breakpoint = results["breakpoint"]
            return f"""
            <div class="summary">
                <h3>Breakpoint Found</h3>
                <div class="metric">
                    <h4>Breakpoint Users</h4>
                    <p class="error">{breakpoint['users']}</p>
                </div>
                <div class="metric">
                    <h4>Success Rate at Breakpoint</h4>
                    <p class="error">{breakpoint['success_rate']:.2f}%</p>
                </div>
                <div class="metric">
                    <h4>Time to Breakpoint</h4>
                    <p>{breakpoint['timestamp']:.2f}s</p>
                </div>
            </div>
            """
        else:
            return """
            <div class="summary">
                <h3>Breakpoint Analysis</h3>
                <p>No breakpoint found. System handled all load levels successfully.</p>
            </div>
            """
    
    def _generate_time_labels(self, results: Dict) -> str:
        """Generate time labels for charts"""
        if not results.get("performance_metrics"):
            return "[]"
        
        labels = [f"{p['timestamp']:.0f}s" for p in results["performance_metrics"]]
        return json.dumps(labels)
    
    def _generate_user_data(self, results: Dict) -> str:
        """Generate user count data for charts"""
        if not results.get("performance_metrics"):
            return "[]"
        
        data = [p["users"] for p in results["performance_metrics"]]
        return json.dumps(data)
    
    def _generate_response_time_data(self, results: Dict) -> str:
        """Generate response time data for charts"""
        if not results.get("performance_metrics"):
            return "[]"
        
        data = [p["metrics"]["avg_response_time"] * 1000 for p in results["performance_metrics"]]
        return json.dumps(data)
    
    def _generate_success_rate_data(self, results: Dict) -> str:
        """Generate success rate data for charts"""
        if not results.get("performance_metrics"):
            return "[]"
        
        data = [p["metrics"]["success_rate"] for p in results["performance_metrics"]]
        return json.dumps(data)
    
    def _generate_cpu_data(self, results: Dict) -> str:
        """Generate CPU usage data for charts"""
        if not results.get("system_metrics"):
            return "[]"
        
        # Sample system metrics at regular intervals
        metrics = results["system_metrics"]
        if len(metrics) > len(results["performance_metrics"]):
            step = len(metrics) // len(results["performance_metrics"])
            sampled = [metrics[i * step] for i in range(len(results["performance_metrics"]))]
        else:
            sampled = metrics
        
        data = [m.cpu_percent for m in sampled]
        return json.dumps(data)
    
    def _generate_memory_data(self, results: Dict) -> str:
        """Generate memory usage data for charts"""
        if not results.get("system_metrics"):
            return "[]"
        
        metrics = results["system_metrics"]
        if len(metrics) > len(results["performance_metrics"]):
            step = len(metrics) // len(results["performance_metrics"])
            sampled = [metrics[i * step] for i in range(len(results["performance_metrics"]))]
        else:
            sampled = metrics
        
        data = [m.memory_percent for m in sampled]
        return json.dumps(data)


async def run_stress_test_suite():
    """Run complete stress test suite"""
    stress_tester = StressTest(
        base_url="https://api.skysentinel.io",
        auth_token="your-test-token"
    )
    
    all_results = {}
    
    # Run different stress tests
    tests = [
        ("spike", stress_tester.spike_test),
        ("gradual", stress_tester.gradual_test),
        ("surge", stress_tester.surge_test),
        ("breakpoint", stress_tester.breakpoint_test),
        ("endurance", stress_tester.endurance_test)
    ]
    
    for test_name, test_func in tests:
        print(f"Running {test_name} stress test...")
        
        try:
            if test_name == "spike":
                results = await test_func("/api/v1/dashboard/overview")
            elif test_name == "gradual":
                results = await test_func("/api/v1/violations")
            elif test_name == "surge":
                results = await test_func("/api/v1/resources")
            elif test_name == "breakpoint":
                results = await test_func("/api/v1/policies")
            elif test_name == "endurance":
                results = await test_func("/api/v1/health")
            
            all_results[test_name] = results
            
            # Generate individual report
            report = stress_tester.generate_stress_report(results)
            with open(f"stress_test_{test_name}_report.html", "w") as f:
                f.write(report)
            
            # Print summary
            summary = results["summary"]
            print(f"  Success Rate: {summary['overall_success_rate']:.2f}%")
            print(f"  Peak Users: {summary['peak_users']}")
            print(f"  Max Response Time: {summary['max_response_time']:.3f}s")
            print(f"  Max CPU Usage: {summary['max_cpu_usage']:.1f}%")
            print(f"  Max Memory Usage: {summary['max_memory_usage']:.1f}%")
            print()
            
        except Exception as e:
            print(f"  Error: {e}")
            print()
    
    print("Stress test suite completed. Reports saved to individual HTML files.")
    
    return all_results

if __name__ == "__main__":
    asyncio.run(run_stress_test_suite())
