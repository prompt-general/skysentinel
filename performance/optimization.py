import asyncio
import time
import statistics
from typing import Dict, List, Any, Optional
import json
import psutil
import subprocess
import threading
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import logging
from pathlib import Path

@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation"""
    category: str
    component: str
    issue: str
    impact: str
    recommendation: str
    priority: str
    estimated_improvement: float
    implementation_effort: str

@dataclass
class SystemResource:
    """System resource information"""
    cpu_cores: int
    cpu_freq: float
    total_memory: int
    available_memory: int
    disk_space: int
    network_interfaces: List[str]

@dataclass
class PerformanceProfile:
    """Performance profile for analysis"""
    timestamp: float
    cpu_usage: List[float]
    memory_usage: List[float]
    disk_io: List[float]
    network_io: List[float]
    process_count: int
    active_connections: int

class PerformanceOptimizer:
    """Performance optimization and tuning for SkySentinel"""
    
    def __init__(self):
        self.system_resources = self._get_system_resources()
        self.performance_profiles = []
        self.recommendations = []
        self.optimization_history = []
        
    def _get_system_resources(self) -> SystemResource:
        """Get system resource information"""
        cpu_info = psutil.cpu_freq()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        return SystemResource(
            cpu_cores=psutil.cpu_count(),
            cpu_freq=cpu_info.current if cpu_info else 0,
            total_memory=memory.total,
            available_memory=memory.available,
            disk_space=disk.total,
            network_interfaces=list(psutil.net_if_addrs().keys())
        )
    
    def collect_performance_profile(self, duration: int = 300) -> PerformanceProfile:
        """Collect performance profile for analysis"""
        profile = PerformanceProfile(
            timestamp=time.time(),
            cpu_usage=[],
            memory_usage=[],
            disk_io=[],
            network_io=[],
            process_count=0,
            active_connections=0
        )
        
        end_time = time.time() + duration
        
        while time.time() < end_time:
            # Collect metrics
            profile.cpu_usage.append(psutil.cpu_percent(interval=1))
            memory = psutil.virtual_memory()
            profile.memory_usage.append(memory.percent)
            
            # I/O metrics
            disk_io = psutil.disk_io_counters()
            if disk_io:
                profile.disk_io.append(disk_io.read_bytes + disk_io.write_bytes)
            
            net_io = psutil.net_io_counters()
            if net_io:
                profile.network_io.append(net_io.bytes_sent + net_io.bytes_recv)
            
            # Process and connection metrics
            profile.process_count = len(psutil.pids())
            
            try:
                profile.active_connections = len(psutil.net_connections())
            except:
                profile.active_connections = 0
            
            time.sleep(1)
        
        return profile
    
    def analyze_performance(self, profile: PerformanceProfile) -> List[OptimizationRecommendation]:
        """Analyze performance profile and generate recommendations"""
        recommendations = []
        
        # CPU analysis
        if profile.cpu_usage:
            avg_cpu = statistics.mean(profile.cpu_usage)
            max_cpu = max(profile.cpu_usage)
            
            if max_cpu > 90:
                recommendations.append(OptimizationRecommendation(
                    category="CPU",
                    component="System",
                    issue="High CPU usage detected",
                    impact="System performance degradation",
                    recommendation="Consider CPU-intensive task optimization or scaling",
                    priority="HIGH",
                    estimated_improvement=15.0,
                    implementation_effort="MEDIUM"
                ))
            elif avg_cpu > 70:
                recommendations.append(OptimizationRecommendation(
                    category="CPU",
                    component="System",
                    issue="Elevated CPU usage",
                    impact="Potential performance issues",
                    recommendation="Monitor CPU-intensive processes and optimize algorithms",
                    priority="MEDIUM",
                    estimated_improvement=10.0,
                    implementation_effort="LOW"
                ))
        
        # Memory analysis
        if profile.memory_usage:
            avg_memory = statistics.mean(profile.memory_usage)
            max_memory = max(profile.memory_usage)
            
            if max_memory > 90:
                recommendations.append(OptimizationRecommendation(
                    category="Memory",
                    component="System",
                    issue="High memory usage detected",
                    impact="System instability and swapping",
                    recommendation="Optimize memory usage and consider adding more RAM",
                    priority="HIGH",
                    estimated_improvement=20.0,
                    implementation_effort="HIGH"
                ))
            elif avg_memory > 80:
                recommendations.append(OptimizationRecommendation(
                    category="Memory",
                    component="System",
                    issue="Elevated memory usage",
                    impact="Performance degradation",
                    recommendation="Monitor memory leaks and optimize data structures",
                    priority="MEDIUM",
                    estimated_improvement=12.0,
                    implementation_effort="MEDIUM"
                ))
        
        # Disk I/O analysis
        if profile.disk_io:
            avg_disk_io = statistics.mean(profile.disk_io)
            if avg_disk_io > 100 * 1024 * 1024:  # 100MB/s
                recommendations.append(OptimizationRecommendation(
                    category="Disk I/O",
                    component="Storage",
                    issue="High disk I/O activity",
                    impact="Application slowdown",
                    recommendation="Optimize database queries and implement caching",
                    priority="HIGH",
                    estimated_improvement=25.0,
                    implementation_effort="HIGH"
                ))
        
        # Network I/O analysis
        if profile.network_io:
            avg_network_io = statistics.mean(profile.network_io)
            if avg_network_io > 50 * 1024 * 1024:  # 50MB/s
                recommendations.append(OptimizationRecommendation(
                    category="Network I/O",
                    component="Network",
                    issue="High network I/O activity",
                    impact="Network bottlenecks",
                    recommendation="Optimize API responses and implement compression",
                    priority="MEDIUM",
                    estimated_improvement=15.0,
                    implementation_effort="MEDIUM"
                ))
        
        # Process count analysis
        if profile.process_count > 500:
            recommendations.append(OptimizationRecommendation(
                category="Processes",
                component="System",
                issue="High process count",
                impact="Resource contention",
                recommendation="Consolidate processes and optimize application architecture",
                priority="MEDIUM",
                estimated_improvement=8.0,
                implementation_effort="HIGH"
            ))
        
        return recommendations
    
    def optimize_system_settings(self) -> Dict[str, Any]:
        """Optimize system settings for performance"""
        optimizations = {
            "cpu": {},
            "memory": {},
            "disk": {},
            "network": {},
            "kernel": {}
        }
        
        try:
            # CPU optimizations
            if self.system_resources.cpu_cores >= 4:
                # Enable CPU governor performance mode
                try:
                    result = subprocess.run(
                        ["cpupctl", "performance"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    optimizations["cpu"]["governor"] = "Set to performance mode"
                except:
                    optimizations["cpu"]["governor"] = "Failed to set CPU governor"
            
            # Memory optimizations
            if self.system_resources.total_memory >= 8 * 1024 * 1024 * 1024:  # 8GB+
                try:
                    # Configure swappiness (lower for better performance)
                    with open("/proc/sys/vm/swappiness", "w") as f:
                        f.write("10")
                    optimizations["memory"]["swappiness"] = "Set swappiness to 10"
                except:
                    optimizations["memory"]["swappiness"] = "Failed to set swappiness"
            
            # Disk optimizations
            try:
                # Enable disk I/O scheduler
                with open("/sys/block/sda/queue/scheduler", "w") as f:
                    f.write("deadline")
                optimizations["disk"]["scheduler"] = "Set I/O scheduler to deadline"
            except:
                optimizations["disk"]["scheduler"] = "Failed to set I/O scheduler"
            
            # Network optimizations
            try:
                # Enable TCP fast open
                with open("/proc/sys/net/ipv4/tcp_fastopen", "w") as f:
                    f.write("3")
                optimizations["network"]["tcp_fastopen"] = "Enabled TCP fast open"
            except:
                optimizations["network"]["tcp_fastopen"] = "Failed to enable TCP fast open"
            
            # Kernel optimizations
            try:
                # Increase file descriptor limit
                with open("/proc/sys/fs/file-max", "w") as f:
                    f.write("65536")
                optimizations["kernel"]["file_max"] = "Increased file descriptor limit"
            except:
                    optimizations["kernel"]["file_max"] = "Failed to increase file descriptor limit"
                
        except Exception as e:
            logging.error(f"System optimization failed: {e}")
        
        return optimizations
    
    def optimize_application_config(self, app_config: Dict) -> Dict[str, Any]:
        """Optimize application configuration for performance"""
        optimizations = {
            "database": {},
            "caching": {},
            "connection_pooling": {},
            "async_config": {}
        }
        
        # Database optimizations
        if "database" in app_config:
            db_config = app_config["database"]
            
            # Connection pool recommendations
            if "pool_size" not in db_config:
                optimizations["database"]["pool_size"] = "Recommended: Set connection pool size to 20"
            
            if "max_overflow" not in db_config:
                optimizations["database"]["max_overflow"] = "Recommended: Set max overflow to 10"
            
            # Query optimization
            optimizations["database"]["query_timeout"] = "Recommended: Set query timeout to 30s"
            optimizations["database"]["statement_timeout"] = "Recommended: Set statement timeout to 60s"
            optimizations["database"]["pool_pre_ping"] = "Recommended: Enable pool pre-ping"
        
        # Caching optimizations
        if "caching" not in app_config:
            optimizations["caching"]["redis"] = "Recommended: Implement Redis caching"
            optimizations["caching"]["cache_ttl"] = "Recommended: Set appropriate cache TTL"
            optimizations["caching"]["cache_size"] = "Recommended: Set cache size based on memory"
        
        # Async configuration
        if "async" not in app_config:
            optimizations["async_config"]["workers"] = "Recommended: Set workers based on CPU cores"
            optimizations["async_config"]["worker_class"] = "Recommended: Use uvicorn workers"
            optimizations["async_config"]["worker_connections"] = "Recommended: Set worker connections to 1000"
        
        return optimizations
    
    def generate_optimization_plan(self, profile: PerformanceProfile) -> Dict[str, Any]:
        """Generate comprehensive optimization plan"""
        recommendations = self.analyze_performance(profile)
        
        # Group recommendations by priority
        high_priority = [r for r in recommendations if r.priority == "HIGH"]
        medium_priority = [r for r in recommendations if r.priority == "MEDIUM"]
        low_priority = [r for r in recommendations if r.priority == "LOW"]
        
        # Calculate estimated improvements
        total_improvement = sum(r.estimated_improvement for r in recommendations)
        
        plan = {
            "timestamp": time.time(),
            "profile_summary": {
                "avg_cpu": statistics.mean(profile.cpu_usage) if profile.cpu_usage else 0,
                "max_cpu": max(profile.cpu_usage) if profile.cpu_usage else 0,
                "avg_memory": statistics.mean(profile.memory_usage) if profile.memory_usage else 0,
                "max_memory": max(profile.memory_usage) if profile.memory_usage else 0,
                "process_count": profile.process_count,
                "duration": len(profile.cpu_usage)  # seconds of data
            },
            "recommendations": {
                "high_priority": high_priority,
                "medium_priority": medium_priority,
                "low_priority": low_priority
            },
            "estimated_improvement": total_improvement,
            "implementation_plan": self._create_implementation_plan(recommendations),
            "optimization_history": self.optimization_history
        }
        
        return plan
    
    def _create_implementation_plan(self, recommendations: List[OptimizationRecommendation]) -> Dict[str, Any]:
        """Create implementation plan from recommendations"""
        plan = {
            "immediate_actions": [],
            "short_term": [],
            "medium_term": [],
            "long_term": []
        }
        
        for rec in recommendations:
            action = {
                "recommendation": rec.recommendation,
                "component": rec.component,
                "estimated_improvement": rec.estimated_improvement,
                "implementation_effort": rec.implementation_effort
            }
            
            if rec.priority == "HIGH":
                plan["immediate_actions"].append(action)
            elif rec.priority == "MEDIUM":
                plan["short_term"].append(action)
            else:
                plan["medium_term"].append(action)
        
        return plan
    
    def apply_optimizations(self, optimizations: Dict[str, Any]) -> Dict[str, Any]:
        """Apply performance optimizations"""
        applied = {}
        
        for category, settings in optimizations.items():
            applied[category] = {}
            
            if category == "cpu" and "governor" in settings:
                try:
                    subprocess.run(["cpupctl", "performance"], check=True)
                    applied[category]["governor"] = "Applied: CPU governor set to performance"
                except:
                    applied[category]["governor"] = "Failed to apply CPU governor setting"
            
            elif category == "memory" and "swappiness" in settings:
                try:
                    with open("/proc/sys/vm/swappiness", "w") as f:
                        f.write("10")
                    applied[category]["swappiness"] = "Applied: Swappiness set to 10"
                except:
                    applied[category]["swappiness"] = "Failed to apply swappiness setting"
            
            elif category == "disk" and "scheduler" in settings:
                try:
                    with open("/proc/sys/block/sda/queue/scheduler", "w") as f:
                        f.write("deadline")
                    applied[category]["scheduler"] = "Applied: I/O scheduler set to deadline"
                except:
                    applied[category]["scheduler"] = "Failed to apply I/O scheduler setting"
            
            elif category == "network" and "tcp_fastopen" in settings:
                try:
                    with open("/proc/sys/net/ipv4/tcp_fastopen", "w") as f:
                        f.write("3")
                    applied[category]["tcp_fastopen"] = "Applied: TCP fast open enabled"
                except:
                    applied[category]["tcp_fastopen"] = "Failed to enable TCP fast open"
            
            elif category == "kernel" and "file_max" in settings:
                try:
                    with open("/proc/sys/fs/file-max", "w") as f:
                        f.write("65536")
                    applied[category]["file_max"] = "Applied: File descriptor limit increased"
                except:
                    applied[category]["file_max"] = "Failed to increase file descriptor limit"
        
        return applied
    
    def monitor_optimization_impact(self, duration: int = 300) -> Dict[str, Any]:
        """Monitor the impact of optimizations"""
        # Collect baseline profile
        print("Collecting baseline performance profile...")
        baseline_profile = self.collect_performance_profile(duration=60)
        
        # Apply optimizations
        print("Applying system optimizations...")
        system_optimizations = self.optimize_system_settings()
        applied_optimizations = self.apply_optimizations(system_optimizations)
        
        # Wait for optimizations to take effect
        time.sleep(30)
        
        # Collect optimized profile
        print("Collecting optimized performance profile...")
        optimized_profile = self.collect_performance_profile(duration=duration)
        
        # Compare profiles
        baseline_avg_cpu = statistics.mean(baseline_profile.cpu_usage) if baseline_profile.cpu_usage else 0
        optimized_avg_cpu = statistics.mean(optimized_profile.cpu_usage) if optimized_profile.cpu_usage else 0
        
        baseline_avg_memory = statistics.mean(baseline_profile.memory_usage) if baseline_profile.memory_usage else 0
        optimized_avg_memory = statistics.mean(optimized_profile.memory_usage) if optimized_profile.memory_usage else 0
        
        impact = {
            "baseline_profile": baseline_profile,
            "optimized_profile": optimized_profile,
            "applied_optimizations": applied_optimizations,
            "performance_impact": {
                "cpu_improvement": baseline_avg_cpu - optimized_avg_cpu,
                "memory_improvement": baseline_avg_memory - optimized_avg_memory,
                "overall_improvement": (baseline_avg_cpu + baseline_avg_memory) - (optimized_avg_cpu + optimized_avg_memory)
            },
            "timestamp": time.time()
        }
        
        return impact
    
    def generate_performance_report(self, plan: Dict) -> str:
        """Generate performance optimization report"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SkySentinel Performance Optimization Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .recommendation {{ margin: 10px; padding: 15px; border-left: 4px solid #ddd; }}
                .high {{ border-left-color: #f44336; }}
                .medium {{ border-left-color: #ff9800; }}
                .low {{ border-left-color: #4caf50; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background: white; border-radius: 3px; }}
                .success {{ color: green; }}
                .warning {{ color: orange; }}
                .error {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #d; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .chart {{ height: 400px; margin: 20px 0; }}
            </style>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <h1>SkySentinel Performance Optimization Report</h1>
            
            <div class="summary">
                <h2>Performance Profile Summary</h2>
                <div class="metric">
                    <h3>Avg CPU Usage</h3>
                    <p>{plan['profile_summary']['avg_cpu']:.1f}%</p>
                </div>
                <div class="metric">
                    <h3>Max CPU Usage</h3>
                    <p>{plan['profile_summary']['max_cpu']:.1f}%</p>
                </div>
                <div class="metric">
                    <h3>Avg Memory Usage</h3>
                    <p>{plan['profile_summary']['avg_memory']:.1f}%</p>
                </div>
                <div class="metric">
                    <h3>Process Count</h3>
                    <p>{plan['profile_summary']['process_count']}</p>
                </div>
                <div class="metric">
                    <h3>Estimated Improvement</h3>
                    <p class="success">{plan['estimated_improvement']:.1f}%</p>
                </div>
            </div>
            
            <h2>Optimization Recommendations</h2>
            
            <h3>High Priority (Immediate)</h3>
            {self._generate_recommendation_html(plan['recommendations']['high_priority'])}
            
            <h3>Medium Priority (Short Term)</h3>
            {self._generate_recommendation_html(plan['recommendations']['medium_priority'])}
            
            <h3>Low Priority (Medium Term)</h3>
            {self._generate_recommendation_html(plan['recommendations']['low_priority'])}
            
            <h2>Implementation Plan</h2>
            <div class="summary">
                <h3>Immediate Actions</h3>
                <ul>
                    {self._generate_action_items(plan['implementation_plan']['immediate_actions'])}
                </ul>
                
                <h3>Short Term</h3>
                <ul>
                    {self._generate_action_items(plan['implementation_plan']['short_term'])}
                </ul>
                
                <h3>Medium Term</h3>
                <ul>
                    {self._generate_action_items(plan['implementation_plan']['medium_term'])}
                </ul>
            </div>
            
            <h2>Performance Charts</h2>
            <div class="chart">
                <canvas id="performanceChart"></canvas>
            </div>
            
            <script>
                // Performance comparison chart
                const ctx = document.getElementById('performanceChart').getContext('2d');
                const chart = new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: ['CPU Usage', 'Memory Usage', 'Estimated Improvement'],
                        datasets: [{
                            label: 'Current',
                            data: [
                                {plan['profile_summary']['avg_cpu']},
                                {plan['profile_summary']['avg_memory']},
                                {plan['estimated_improvement']}
                            ],
                            backgroundColor: 'rgba(255, 99, 132, 0.8)'
                        }]
                    }},
                    options: {{
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                max: 100
                            }}
                        }}
                    }}
                }});
            </script>
        </body>
        </html>
        """
        
        return html
    
    def _generate_recommendation_html(self, recommendations: List[OptimizationRecommendation]) -> str:
        """Generate HTML for recommendations"""
        html = ""
        
        for rec in recommendations:
            css_class = rec.priority.lower()
            html += f"""
            <div class="recommendation {css_class}">
                <h4>{rec.issue}</h4>
                <p><strong>Component:</strong> {rec.component}</p>
                <p><strong>Impact:</strong> {rec.impact}</p>
                <p><strong>Recommendation:</strong> {rec.recommendation}</p>
                <p><strong>Estimated Improvement:</strong> {rec.estimated_improvement:.1f}%</p>
                <p><strong>Implementation Effort:</strong> {rec.implementation_effort}</p>
            </div>
            """
        
        return html
    
    def _generate_action_items(self, actions: List[Dict]) -> str:
        """Generate HTML action items"""
        html = ""
        
        for action in actions:
            html += f"<li>{action['recommendation']} (Est. improvement: {action['estimated_improvement']:.1f}%)</li>\n"
        
        return html


class ApplicationOptimizer:
    """Application-specific performance optimization"""
    
    def __init__(self):
        self.optimization_rules = self._load_optimization_rules()
    
    def _load_optimization_rules(self) -> Dict[str, Any]:
        """Load optimization rules"""
        return {
            "database": {
                "connection_pooling": {
                    "min_connections": 5,
                    "max_connections": 20,
                    "max_overflow": 10,
                    "pool_timeout": 30,
                    "pool_recycle": 300
                },
                "query_optimization": {
                    "statement_timeout": 60,
                    "query_timeout": 30,
                    "enable_pre_ping": True
                }
            },
            "caching": {
                "redis": {
                    "max_connections": 10,
                    "socket_timeout": 5,
                    "socket_connect_timeout": 5,
                    "retry_on_timeout": True
                },
                "application": {
                    "cache_ttl": 300,
                    "cache_size": 1000
                }
            },
            "async": {
                "workers": 4,
                "worker_class": "uvicorn.workers.UvicornWorker",
                "worker_connections": 1000,
                "worker_connections_per_core": 1000,
                "max_requests": 1000,
                "timeout": 30
            }
        }
    
    def optimize_database_config(self, current_config: Dict) -> Dict[str, Any]:
        """Optimize database configuration"""
        optimized_config = current_config.copy()
        rules = self.optimization_rules["database"]
        
        # Apply connection pooling rules
        if "pool" not in optimized_config:
            optimized_config["pool"] = {}
        
        for key, value in rules["connection_pooling"].items():
            if key not in optimized_config["pool"]:
                optimized_config["pool"][key] = value
                logging.info(f"Database optimization: Set {key} to {value}")
        
        # Apply query optimization rules
        if "query_optimization" not in optimized_config:
            optimized_config["query_optimization"] = {}
        
        for key, value in rules["query_optimization"].items():
            if key not in optimized_config["query_optimization"]:
                optimized_config["query_optimization"][key] = value
                logging.info(f"Database optimization: Set {key} to {value}")
        
        return optimized_config
    
    def optimize_caching_config(self, current_config: Dict) -> Dict[str, Any]:
        """Optimize caching configuration"""
        optimized_config = current_config.copy()
        rules = self.optimization_rules["caching"]
        
        # Apply Redis rules
        if "redis" not in optimized_config:
            optimized_config["redis"] = {}
        
        for key, value in rules["redis"].items():
            if key not in optimized_config["redis"]:
                optimized_config["redis"][key] = value
                logging.info(f"Caching optimization: Set {key} to {value}")
        
        # Apply application caching rules
        if "application" not in optimized_config:
            optimized_config["application"] = {}
        
        for key, value in rules["application"].items():
            if key not in optimized_config["application"]:
                optimized_config["application"][key] = value
                logging.info(f"Caching optimization: Set {key} to {value}")
        
        return optimized_config
    
    def optimize_async_config(self, current_config: Dict) -> Dict[str, Any]:
        """Optimize async configuration"""
        optimized_config = current_config.copy()
        rules = self.optimization_rules["async"]
        
        # Apply async rules
        for key, value in rules.items():
            if key not in optimized_config:
                optimized_config[key] = value
                logging.info(f"Async optimization: Set {key} to {value}")
        
        return optimized_config


# Example usage
async def main():
    """Example performance optimization usage"""
    optimizer = PerformanceOptimizer()
    
    # Collect performance profile
    print("Collecting performance profile...")
    profile = optimizer.collect_performance_profile(duration=300)
    
    # Generate optimization plan
    print("Generating optimization plan...")
    plan = optimizer.generate_optimization_plan(profile)
    
    # Generate report
    report = optimizer.generate_performance_report(plan)
    with open("performance_optimization_report.html", "w") as f:
        f.write(report)
    
    print("Performance optimization report saved to performance_optimization_report.html")
    
    # Monitor optimization impact
    print("Monitoring optimization impact...")
    impact = optimizer.monitor_optimization_impact(duration=300)
    
    print(f"CPU improvement: {impact['performance_impact']['cpu_improvement']:.1f}%")
    print(f"Memory improvement: {impact['performance_impact']['memory_improvement']:.1f}%")
    print(f"Overall improvement: {impact['performance_impact']['overall_improvement']:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())
