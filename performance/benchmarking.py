import asyncio
import time
import statistics
import json
import hashlib
import pickle
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging
import aiofiles
import aiohttp
import psutil

@dataclass
class BenchmarkResult:
    """Individual benchmark result"""
    test_name: str
    timestamp: datetime
    metrics: Dict[str, float]
    metadata: Dict[str, Any]
    success: bool
    error: Optional[str] = None

@dataclass
class BenchmarkSuite:
    """Collection of benchmark results"""
    name: str
    timestamp: datetime
    results: List[BenchmarkResult]
    summary: Dict[str, Any]

@dataclass
class BenchmarkComparison:
    """Comparison between benchmark runs"""
    baseline: BenchmarkSuite
    current: BenchmarkSuite
    comparison: Dict[str, Any]
    improvements: Dict[str, float]
    regressions: Dict[str, float]

class PerformanceBenchmark:
    """Performance benchmarking and comparison framework"""
    
    def __init__(self):
        self.benchmark_history = []
        self.baseline_suite = None
        self.current_suite = None
        self.benchmark_storage_path = "benchmark_results"
        self.comparison_threshold = 5.0  # 5% threshold for significant changes
    
    async def run_load_benchmark(self, test_name: str, target_url: str,
                               auth_token: str = None, duration: int = 300,
                               concurrent_users: int = 50) -> BenchmarkResult:
        """Run load benchmark test"""
        from .load_testing import LoadTest
        
        load_tester = LoadTest(target_url, auth_token)
        
        print(f"Running load benchmark: {test_name}")
        
        # Run the load test
        result = await load_tester.test_api_endpoint(
            endpoint="/api/v1/benchmark",
            method="GET",
            concurrent_users=concurrent_users,
            duration=duration
        )
        
        # Extract metrics
        metrics = {
            "avg_response_time": result["summary"]["avg_response_time"],
            "p95_response_time": result["summary"].get("p95_response_time", 0),
            "p99_response_time": result["summary"].get("p99_response_time", 0),
            "requests_per_second": result["summary"]["requests_per_second"],
            "success_rate": result["summary"]["success_rate"],
            "total_requests": result["summary"]["total_requests"]
        }
        
        benchmark_result = BenchmarkResult(
            test_name=test_name,
            timestamp=datetime.utcnow(),
            metrics=metrics,
            metadata={
                "concurrent_users": concurrent_users,
                "duration": duration,
                "target_url": target_url
            },
            success=result["summary"]["success_rate"] > 95
        )
        
        return benchmark_result
    
    async def run_database_benchmark(self, test_name: str, connection_string: str,
                                 query: str, iterations: int = 100) -> BenchmarkResult:
        """Run database benchmark test"""
        from .database_performance import DatabasePerformanceTester
        
        tester = DatabasePerformanceTester(connection_string)
        
        print(f"Running database benchmark: {test_name}")
        
        try:
            await tester.initialize_pool()
            
            # Create test query
            from .database_performance import DatabaseQuery
            test_query = DatabaseQuery(
                query_id=test_name,
                query_type="SELECT",
                sql=query,
                parameters={},
                expected_rows=10,
                complexity="benchmark"
            )
            
            # Run the benchmark
            result = await tester.run_query_test(test_query, iterations=iterations)
            
            metrics = {
                "avg_execution_time": result["summary"]["avg_execution_time"],
                "p95_execution_time": result["summary"].get("p95_execution_time", 0),
                "success_rate": result["summary"]["success_rate"],
                "avg_rows_returned": result["summary"].get("avg_rows_returned", 0),
                "cache_hit_rate": result["summary"].get("cache_hit_rate", 0)
            }
            
            benchmark_result = BenchmarkResult(
                test_name=test_name,
                timestamp=datetime.utcnow(),
                metrics=metrics,
                metadata={
                    "iterations": iterations,
                    "query": query
                },
                success=result["summary"]["success_rate"] > 95
            )
            
            return benchmark_result
            
        finally:
            await tester.close_pool()
            
    except Exception as e:
            return BenchmarkResult(
                test_name=test_name,
                timestamp=datetime.utcnow(),
                metrics={},
                metadata={"error": str(e)},
                success=False
            )
    
    async def run_stress_benchmark(self, test_name: str, target_url: str,
                                auth_token: str = None,
                                max_users: int = 200, duration: int = 600) -> BenchmarkResult:
        """Run stress benchmark test"""
        from .stress_testing import StressTest, StressTestType
        
        stress_tester = StressTest(target_url, auth_token)
        
        print(f"Running stress benchmark: {test_name}")
        
        # Run breakpoint test to find breaking point
        result = await stress_tester.breakpoint_test(
            endpoint="/api/v1/benchmark",
            initial_users=10,
            user_increment=10,
            max_duration=duration,
            failure_threshold=0.05
        )
        
        metrics = {
            "breakpoint_users": result["breakpoint"]["users"] if result.get("breakpoint") else 0,
            "breakpoint_success_rate": result["breakpoint"]["success_rate"] if result.get("breakpoint") else 0,
            "max_cpu_usage": max(m.cpu_percent for m in stress_tester.system_metrics) if stress_tester.system_metrics else 0,
            "max_memory_usage": max(m.memory_percent for m in stress_tester.system_metrics) if stress_tester.system_metrics else 0,
            "peak_users": max(p["users"] for p in result["performance_metrics"]) if result.get("performance_metrics") else 0
        }
        
        benchmark_result = BenchmarkResult(
            test_name=test_name,
            timestamp=datetime.utcnow(),
            metrics=metrics,
            metadata={
                "max_users": max_users,
                "duration": duration,
                "target_url": target_url,
                "breakpoint": result.get("breakpoint")
            },
            success=result.get("summary", {}).get("success_rate", 0) > 80
        )
        
        return benchmark_result
    
    async def run_endurance_benchmark(self, test_name: str, target_url: str,
                                   auth_token: str = None,
                                   users: int = 50, duration: int = 3600) -> BenchmarkResult:
        """Run endurance benchmark test"""
        from .stress_testing import StressTest
        
        stress_tester = StressTest(target_url, auth_token)
        
        print(f"Running endurance benchmark: {test_name}")
        
        # Run endurance test
        result = await stress_tester.endurance_test(
            endpoint="/api/v1/benchmark",
            users=users,
            duration=duration
        )
        
        metrics = {
            "success_rate": result["summary"]["success_rate"],
            "avg_response_time": result["summary"]["avg_response_time"],
            "max_response_time": result["summary"]["max_response_time"],
            "requests_per_second": result["summary"]["requests_per_second"],
            "avg_cpu_usage": statistics.mean(m.cpu_percent for m in stress_tester.system_metrics) if stress_tester.system_metrics else 0,
            "avg_memory_usage": statistics.mean(m.memory_percent for m in stress_tester.system_metrics) if stress_tester.system_metrics else 0
        }
        
        benchmark_result = BenchmarkResult(
            test_name=test_name,
            timestamp=datetime.utcnow(),
            metrics=metrics,
            metadata={
                "users": users,
                "duration": duration,
                "target_url": target_url
            },
            success=result["summary"]["success_rate"] > 90
        )
        
        return benchmark_result
    
    def create_benchmark_suite(self, name: str, results: List[BenchmarkResult]) -> BenchmarkSuite:
        """Create a benchmark suite from results"""
        return BenchmarkSuite(
            name=name,
            timestamp=datetime.utcnow(),
            results=results,
            summary=self._calculate_suite_summary(results)
        )
    
    def _calculate_suite_summary(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Calculate summary statistics for benchmark suite"""
        if not results:
            return {"error": "No results provided"}
        
        successful_results = [r for r in results if r.success]
        
        # Calculate overall metrics
        if successful_results:
            avg_response_time = statistics.mean(r.metrics.get("avg_response_time", 0) for r in successful_results)
            success_rate = statistics.mean(r.metrics.get("success_rate", 0) for r in successful_results)
            
            return {
                "total_tests": len(results),
                "successful_tests": len(successful_results),
                "failed_tests": len(results) - len(successful_results),
                "overall_success_rate": success_rate,
                "avg_response_time": avg_response_time,
                "test_names": [r.test_name for r in results]
            }
        else:
            return {
                "total_tests": len(results),
                "successful_tests": 0,
                "failed_tests": len(results),
                "overall_success_rate": 0,
                "avg_response_time": 0,
                "test_names": [r.test_name for r in results]
            }
    
    def set_baseline(self, suite: BenchmarkSuite):
        """Set baseline benchmark suite"""
        self.baseline_suite = suite
        logging.info(f"Baseline benchmark set: {suite.name}")
    
    def set_current(self, suite: BenchmarkSuite):
        """Set current benchmark suite"""
        self.current_suite = suite
        logging.info(f"Current benchmark set: {suite.name}")
    
    def compare_benchmarks(self) -> Optional[BenchmarkComparison]:
        """Compare current benchmark with baseline"""
        if not self.baseline_suite or not self.current_suite:
            return None
        
        comparison = self._compare_suites(self.baseline_suite, self.current_suite)
        
        # Store comparison in history
        self.benchmark_history.append(comparison)
        
        return comparison
    
    def _compare_suites(self, baseline: BenchmarkSuite, current: BenchmarkSuite) -> BenchmarkComparison:
        """Compare two benchmark suites"""
        comparison = {
            "baseline": baseline,
            "current": current,
            "timestamp": datetime.utcnow(),
            "comparisons": {},
            "improvements": {},
            "regressions": {},
            "summary": {}
        }
        
        # Compare individual tests
        baseline_tests = {r.test_name: r for r in baseline.results}
        current_tests = {r.test_name: r for r in current.results}
        
        # Find common tests
        common_tests = set(baseline_tests.keys()) & set(current_tests.keys())
        
        for test_name in common_tests:
            baseline_result = baseline_tests[test_name]
            current_result = current_tests[test_name]
            
            baseline_metric = baseline_result.metrics.get("avg_response_time", 0)
            current_metric = current_result.metrics.get("avg_response_time", 0)
            
            if baseline_metric > 0:
                improvement = ((baseline_metric - current_metric) / baseline_metric) * 100
                if improvement > 0:
                    comparison["improvements"][test_name] = improvement
                else:
                    comparison["regressions"][test_name] = abs(improvement)
                
                comparison["comparisons"][test_name] = {
                    "baseline": baseline_metric,
                    "current": current_metric,
                    "improvement_pct": improvement,
                    "regression_pct": comparison["regressions"][test_name]
                }
        
        # Calculate summary
        improvements = list(comparison["improvements"].values())
        regressions = list(comparison["regressions"].values())
        
        comparison["summary"] = {
            "common_tests": len(common_tests),
            "total_improvements": len(improvements),
            "total_regressions": len(regressions),
            "avg_improvement": statistics.mean(improvements) if improvements else 0,
            "avg_regression": statistics.mean(regressions) if regressions else 0,
            "net_improvement": statistics.mean(improvements) - statistics.mean(regressions) if improvements and regressions else 0
        }
        
        return comparison
    
    def get_benchmark_trends(self, test_name: str = None, days: int = 30) -> Dict[str, Any]:
        """Get benchmark trends over time"""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        # Filter results by test name if specified
        if test_name:
            filtered_results = [
                r for suite in self.benchmark_history + ([self.current_suite] if self.current_suite else [])
                for r in suite.results
                if r.test_name == test_name
            ]
        else:
            filtered_results = [
                r for suite in self.benchmark_history + ([self.current_suite] if self.current_suite else [])
                for r in suite.results
            ]
        
        # Filter by time
        recent_results = [
            r for r in filtered_results
            if r.timestamp >= cutoff_time
        ]
        
        if not recent_results:
            return {"error": "No recent results found"}
        
        # Group by date
        daily_results = {}
        for result in recent_results:
            date_key = result.timestamp.date().isoformat()
            if date_key not in daily_results:
                daily_results[date_key] = []
            daily_results[date_key].append(result)
        
        # Calculate trends
        trends = {}
        for date, results in daily_results.items():
            if results:
                avg_response_time = statistics.mean(r.metrics.get("avg_response_time", 0) for r in results if r.success)
                success_rate = statistics.mean(r.metrics.get("success_rate", 0) for r in results if r.success)
                
                trends[date] = {
                    "avg_response_time": avg_response_time,
                    "success_rate": success_rate,
                    "test_count": len(results)
                }
        
        return trends
    
    def export_benchmark_data(self, format: str = "json", days: int = 30) -> str:
        """Export benchmark data to file"""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        # Collect all recent results
        all_results = []
        
        # Add historical results
        for suite in self.benchmark_history:
            for result in suite.results:
                if result.timestamp >= cutoff_time:
                    all_results.append(result)
        
        # Add current suite
        if self.current_suite:
            for result in self.current_suite.results:
                if result.timestamp >= cutoff_time:
                    all_results.append(result)
        
        # Sort by timestamp
        all_results.sort(key=lambda x: x.timestamp)
        
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "days": days,
            "total_results": len(all_results),
            "benchmark_history": [
                {
                    "name": suite.name,
                    "timestamp": suite.timestamp.isoformat(),
                    "results": [asdict(r) for r in suite.results]
                }
                for suite in self.benchmark_history
            ],
            "current_suite": asdict(self.current_suite) if self.current_suite else None,
            "all_results": [asdict(r) for r in all_results]
        }
        
        if format == "json":
            return json.dumps(export_data, indent=2, default=str)
        elif format == "csv":
            # Convert to CSV format
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "test_name", "timestamp", "metric_name", "metric_value", "success", "error"
            ])
            
            # Write data rows
            for result in all_results:
                for metric_name, metric_value in result.metrics.items():
                    writer.writerow([
                        result.test_name,
                        result.timestamp.isoformat(),
                        metric_name,
                        metric_value,
                        result.success,
                        result.error or ""
                    ])
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def generate_benchmark_report(self, comparison: BenchmarkComparison = None) -> str:
        """Generate comprehensive benchmark report"""
        if not comparison:
            return "<html><body><h1>No benchmark comparison available</h1></body></html>"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SkySentinel Benchmark Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background: white; border-radius: 3px; }}
                .improvement {{ color: green; }}
                .regression {{ color: red; }}
                .neutral {{ color: gray; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .chart {{ height: 400px; margin: 20px 0; }}
            </style>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <h1>SkySentinel Benchmark Report</h1>
            <h2>Benchmark Comparison</h2>
            
            <div class="summary">
                <h3>Comparison Summary</h3>
                <div class="metric">
                    <h4>Common Tests</h4>
                    <p>{len(comparison['comparisons'])}</p>
                </div>
                <div class="metric">
                    <h4>Total Improvements</h4>
                    <p class="improvement">{len(comparison['improvements'])}</p>
                </div>
                <div class="metric">
                    <h4>Total Regressions</h4>
                    <p class="regression">{len(comparison['regressions'])}</p>
                </div>
                <div class="metric">
                    <h4>Net Improvement</h4>
                    <p class="{'improvement' if comparison['summary']['net_improvement'] > 0 else 'regression' if comparison['summary']['net_improvement'] < 0 else 'neutral'}>
                        {comparison['summary']['net_improvement']:.2f}%
                    </p>
                </div>
            </div>
            
            <h2>Detailed Comparisons</h2>
            <table>
                <tr>
                    <th>Test Name</th>
                    <th>Baseline</th>
                    <th>Current</th>
                    <th>Improvement</th>
                    <th>Status</th>
                </tr>
        """
        
        for test_name, comparison_data in comparison["comparisons"].items():
            status = "IMPROVEMENT" if comparison_data["improvement_pct"] > 0 else "REGRESSION" if comparison_data["improvement_pct"] < 0 else "NEUTRAL"
            css_class = status.lower()
            
            html += f"""
                <tr>
                    <td>{test_name}</td>
                    <td>{comparison_data['baseline']:.3f}s</td>
                    <td>{comparison_data['current']:.3f}s</td>
                    <td>{comparison_data['improvement_pct']:.2f}%</td>
                    <td class="{css_class}">{status}</td>
                </tr>
            """
        
        html += """
            </table>
            
            <h2>Performance Trends</h2>
            <div class="chart">
                <canvas id="trendsChart"></canvas>
            </div>
            
            <h2>Recommendations</h2>
            <div class="summary">
                {self._generate_recommendations_html(comparison)}
            </div>
            
            <script>
                // Trends chart
                const trendsChart = document.getElementById('trendsChart').getContext('2d');
                const trendsData = {self._generate_trends_data(comparison)};
                
                const chart = new Chart(trendsChart, {{
                    type: 'line',
                    data: {{
                        labels: Object.keys(trendsData),
                        datasets: [{
                            label: 'Response Time (ms)',
                            data: Object.values(trendsData).map(d => d['avg_response_time'] * 1000),
                            borderColor: 'rgb(75, 192, 192)',
                            tension: 0.1
                        }]
                    }},
                    options: {{
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                title: 'Response Time (ms)'
                            }}
                        }}
                    }}
                }});
            </script>
        </body>
        </html>
        """
        
        return html
    
    def _generate_recommendations_html(self, comparison: BenchmarkComparison) -> str:
        """Generate recommendations HTML"""
        html = ""
        
        # Improvement recommendations
        if comparison["improvements"]:
            html += "<h3>Performance Improvements</h3><ul>"
            for test_name, improvement in comparison["improvements"].items():
                html += f"<li>{test_name}: {improvement:.2f}% improvement</li>"
            html += "</ul>"
        
        # Regression warnings
        if comparison["regressions"]:
            html += "<h3>Performance Regressions</h3><ul>"
            for test_name, regression in comparison["regressions"].items():
                html += f"<li>{test_name}: {regression:.2f}% regression</li>"
            html += "</ul>"
        
        # General recommendations
        html += "<h3>General Recommendations</h3><ul>"
        
        if comparison["summary"]["net_improvement"] < 0:
            html += "<li>Consider investigating performance regressions</li>"
        
        if comparison["summary"]["net_improvement"] < 5:
            html += "<li>Focus on optimizing slowest queries</li>"
        
        if len(comparison["improvements"]) < len(comparison["regressions"]):
            html += "<li>Overall performance trend is positive</li>"
        
        html += "<li>Continue monitoring and regular benchmarking</li>"
        html += "</ul>"
        
        return html
    
    def _generate_trends_data(self, comparison: BenchmarkComparison) -> Dict[str, Any]:
        """Generate trends data for charting"""
        # This would extract trend data from comparison
        trends = {}
        
        # For now, return sample data
        return {
            "2024-01-20": {"avg_response_time": 150},
            "2024-01-21": {"avg_response_time": 145},
            "2024-01-22": {"avg_response_time": 140},
            "2024-01-23": {"avg_response_time": 135},
            "2024-01-24": {"avg_response_time": 130}
        }


class BenchmarkScheduler:
    """Automated benchmark scheduling"""
    
    def __init__(self):
        self.scheduled_tests = []
        self.is_running = False
        self.scheduler_thread = None
    
    def schedule_benchmark(self, test_config: Dict) -> str:
        """Schedule a benchmark test"""
        test_id = f"benchmark_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        scheduled_test = {
            "id": test_id,
            "config": test_config,
            "scheduled_time": datetime.utcnow(),
            "status": "scheduled",
            "result": None
        }
        
        self.scheduled_tests.append(scheduled_test)
        
        return test_id
    
    def start_scheduler(self):
        """Start the benchmark scheduler"""
        if self.is_running:
            return
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
    
    def stop_scheduler(self):
        """Stop the benchmark scheduler"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            current_time = time.time()
            
            # Check for due tests
            for test in self.scheduled_tests:
                if test["status"] == "scheduled" and current_time >= test["scheduled_time"]:
                    print(f"Running scheduled benchmark: {test['config'].get('name', 'unnamed')}")
                    
                    # Run the benchmark
                    try:
                        if test["config"]["type"] == "load":
                            result = await self._run_load_benchmark(test["config"])
                        elif test["config"]["type"] == "database":
                            result = await self._run_database_benchmark(test["config"])
                        elif test["config"]["type"] == "stress":
                            result = await self._run_stress_benchmark(test["config"])
                        elif test["config"]["type"] == "endurance":
                            result = await self._run_endurance_benchmark(test["config"])
                        else:
                            result = await self._run_generic_benchmark(test["config"])
                        
                        test["result"] = result
                        test["status"] = "completed"
                        
                    except Exception as e:
                        test["result"] = BenchmarkResult(
                            test_name=test["config"].get("name", "unnamed"),
                            timestamp=datetime.utcnow(),
                            metrics={},
                            metadata={},
                            success=False,
                            error=str(e)
                        )
                        test["status"] = "failed"
                    
            # Clean up old completed tests
            self.scheduled_tests = [
                t for t in self.scheduled_tests
                if t["status"] not in ["completed", "failed"]
            ]
            
            time.sleep(60)  # Check every minute
    
    async def _run_load_benchmark(self, config: Dict) -> BenchmarkResult:
        """Run load benchmark"""
        return await self.run_load_benchmark(
            test_name=config["name"],
            target_url=config["target_url"],
            auth_token=config.get("auth_token"),
            duration=config.get("duration", 300),
            concurrent_users=config.get("concurrent_users", 50)
        )
    
    async def _run_database_benchmark(self, config: Dict) -> BenchmarkResult:
        """Run database benchmark"""
        return await self.run_database_benchmark(
            test_name=config["name"],
            connection_string=config["connection_string"],
            query=config.get("query", "SELECT 1"),
            iterations=config.get("iterations", 100)
        )
    
    async def _run_stress_benchmark(self, config: Dict) -> BenchmarkResult:
        """Run stress benchmark"""
        return await self.run_stress_benchmark(
            test_name=config["name"],
            target_url=config["target_url"],
            auth_token=config.get("auth_token"),
            max_users=config.get("max_users", 200),
            duration=config.get("duration", 600)
        )
    
    async def _run_endurance_benchmark(self, config: Dict) -> BenchmarkResult:
        """Run endurance benchmark"""
        return await self.run_endurance_benchmark(
            test_name=config["name"],
            target_url=config["target_url"],
            auth_token=config.get("auth_token"),
            users=config.get("users", 50),
            duration=config.get("duration", 3600)
        )
    
    async def _run_generic_benchmark(self, config: Dict) -> BenchmarkResult:
        """Run generic benchmark"""
        # Default to load test
        return await self._run_load_benchmark(config)


# Example usage
async def main():
    """Example benchmark usage"""
    scheduler = BenchmarkScheduler()
    
    # Schedule benchmarks
    scheduler.start_scheduler()
    
    # Schedule different types of benchmarks
    load_test_id = scheduler.schedule_benchmark({
        "name": "API Load Test",
        "type": "load",
        "target_url": "https://api.skysentinel.io",
        "auth_token": "your-token",
        "concurrent_users": 50,
        "duration": 300
    })
    
    db_test_id = scheduler.schedule_benchmark({
        "name": "Database Query Test",
        "type": "database",
        "connection_string": "postgresql://user:password@localhost:5432/skysentinel",
        "query": "SELECT COUNT(*) FROM violations",
        "iterations": 100
    })
    
    stress_test_id = scheduler.schedule_benchmark({
        "name": "Stress Test",
        "type": "stress",
        "target_url": "https://api.skysentinel.io",
        "auth_token": "your-token",
        "max_users": 200,
        "duration": 600
    })
    
    endurance_test_id = scheduler_id = scheduler.schedule_benchmark({
        "name": "Endurance Test",
        "type": "endurance",
        "target_url": "https://api.skysentinel.io",
        "auth_token": "your-token",
        "users": 50,
        "duration": 3600
    })
    
    print(f"Scheduled {len(scheduler.scheduled_tests)} benchmarks")
    
    # Wait for some tests to complete
    await asyncio.sleep(600)
    
    # Generate comparison report
    if scheduler.current_suite and scheduler.baseline_suite:
        comparison = scheduler.compare_benchmarks()
        report = scheduler.generate_benchmark_report(comparison)
        
        with open("benchmark_comparison_report.html", "w") as f:
            f.write(report)
        
        print("Benchmark comparison report saved to benchmark_comparison_report.html")
    
    # Stop scheduler
    scheduler.stop_scheduler()


if __name__ == "__main__":
    asyncio.run(main())
