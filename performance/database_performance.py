import asyncio
import time
import statistics
from typing import Dict, List, Any, Optional
import json
import asyncpg
import psycopg2
from dataclasses import dataclass
import random
import threading
from concurrent.futures import ThreadPoolExecutor
import logging

@dataclass
class DatabaseQuery:
    """Database query definition"""
    query_id: str
    query_type: str
    sql: str
    parameters: Dict[str, Any]
    expected_rows: int
    complexity: str

@dataclass
class QueryResult:
    """Database query result"""
    query_id: str
    execution_time: float
    rows_returned: int
    bytes_returned: int
    cache_hit: bool
    index_used: str
    error: Optional[str]
    timestamp: float

class DatabasePerformanceTester:
    """Database performance testing for SkySentinel"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool = None
        self.query_results = []
        self.baseline_metrics = {}
        self.test_queries = self._load_test_queries()
        
    def _load_test_queries(self) -> List[DatabaseQuery]:
        """Load test queries"""
        return [
            DatabaseQuery(
                query_id="simple_select",
                query_type="SELECT",
                sql="SELECT id, name, created_at FROM users WHERE tenant_id = %(tenant_id)s LIMIT 100",
                parameters={"tenant_id": "test_tenant"},
                expected_rows=100,
                complexity="simple"
            ),
            DatabaseQuery(
                query_id="complex_join",
                query_type="SELECT",
                sql="""
                SELECT u.id, u.name, COUNT(v.id) as violation_count
                FROM users u
                LEFT JOIN violations v ON u.id = v.user_id
                WHERE u.tenant_id = %(tenant_id)s
                GROUP BY u.id, u.name
                ORDER BY violation_count DESC
                LIMIT 50
                """,
                parameters={"tenant_id": "test_tenant"},
                expected_rows=50,
                complexity="complex"
            ),
            DatabaseQuery(
                query_id="aggregate_function",
                query_type="SELECT",
                sql="""
                SELECT 
                    COUNT(*) as total_violations,
                    COUNT(CASE WHEN severity = 'CRITICAL' THEN 1 END) as critical_violations,
                    COUNT(CASE WHEN severity = 'HIGH' THEN 1 END) as high_violations,
                    DATE_TRUNC('hour', created_at) as hour
                FROM violations
                WHERE tenant_id = %(tenant_id)s
                  AND created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY hour
                ORDER BY hour
                """,
                parameters={"tenant_id": "test_tenant"},
                expected_rows=24,
                complexity="aggregate"
            ),
            DatabaseQuery(
                query_id="subquery",
                query_type="SELECT",
                sql="""
                SELECT u.id, u.name, u.email
                FROM users u
                WHERE u.id IN (
                    SELECT DISTINCT user_id
                    FROM violations
                    WHERE severity = 'CRITICAL'
                    AND tenant_id = %(tenant_id)s
                )
                """,
                parameters={"tenant_id": "test_tenant"},
                expected_rows=10,
                complexity="subquery"
            ),
            DatabaseQuery(
                query_id="window_function",
                query_type="SELECT",
                sql="""
                SELECT 
                    id,
                    name,
                    created_at,
                    ROW_NUMBER() OVER (PARTITION BY tenant_id ORDER BY created_at DESC) as rn
                FROM users
                WHERE tenant_id = %(tenant_id)s
                """,
                parameters={"tenant_id": "test_tenant"},
                expected_rows=100,
                complexity="window"
            ),
            DatabaseQuery(
                query_id="cte_query",
                query_type="SELECT",
                sql="""
                WITH user_stats AS (
                    SELECT 
                        user_id,
                        COUNT(*) as violation_count,
                        MAX(created_at) as last_violation
                    FROM violations
                    WHERE tenant_id = %(tenant_id)s
                    GROUP BY user_id
                )
                SELECT u.id, u.name, us.violation_count, us.last_violation
                FROM users u
                LEFT JOIN user_stats us ON u.id = us.user_id
                WHERE u.tenant_id = %(tenant_id)s
                """,
                parameters={"tenant_id": "test_tenant"},
                expected_rows=100,
                complexity="cte"
            ),
            DatabaseQuery(
                query_id="insert_statement",
                query_type="INSERT",
                sql="""
                INSERT INTO audit_logs (tenant_id, user_id, action, resource_type, created_at)
                VALUES (%(tenant_id)s, %(user_id)s, %(action)s, %(resource_type)s, NOW())
                """,
                parameters={"tenant_id": "test_tenant", "user_id": "test_user", "action": "test_action", "resource_type": "test_resource"},
                expected_rows=1,
                complexity="simple"
            ),
            DatabaseQuery(
                query_id="update_statement",
                query_type="UPDATE",
                sql="""
                UPDATE users 
                SET last_login = NOW()
                WHERE tenant_id = %(tenant_id)s AND id = %(user_id)s
                """,
                parameters={"tenant_id": "test_tenant", "user_id": 1},
                expected_rows=1,
                complexity="simple"
            ),
            DatabaseQuery(
                query_id="delete_statement",
                query_type="DELETE",
                sql="""
                DELETE FROM temp_data
                WHERE created_at < NOW() - INTERVAL '1 hour'
                """,
                parameters={},
                expected_rows=0,
                complexity="simple"
            )
        ]
    
    async def initialize_pool(self, min_connections: int = 5, max_connections: int = 20):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=min_connections,
                max_size=max_connections
            )
            logging.info("Database connection pool initialized")
        except Exception as e:
            logging.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def close_pool(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logging.info("Database connection pool closed")
    
    async def run_query_test(self, query: DatabaseQuery, iterations: int = 10) -> Dict[str, Any]:
        """Run single query performance test"""
        results = {
            "query_id": query.query_id,
            "query_type": query.query_type,
            "iterations": iterations,
            "results": [],
            "summary": {}
        }
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                async with self.pool.acquire() as conn:
                    # Enable query plan analysis
                    await conn.execute("EXPLAIN (ANALYZE, BUFFERS) " + query.sql, query.parameters)
                    explain_result = await conn.fetchrow()
                    
                    # Execute actual query
                    start_query = time.time()
                    result = await conn.fetch(query.sql, query.parameters)
                    end_query = time.time()
                    
                    execution_time = end_query - start_query
                    rows_returned = len(result)
                    bytes_returned = sum(len(str(row)) for row in result)
                    
                    # Parse explain result
                    index_used = self._parse_index_used(explain_result)
                    cache_hit = self._check_cache_hit(explain_result)
                    
                    query_result = QueryResult(
                        query_id=query.query_id,
                        execution_time=execution_time,
                        rows_returned=rows_returned,
                        bytes_returned=bytes_returned,
                        cache_hit=cache_hit,
                        index_used=index_used,
                        error=None,
                        timestamp=start_time
                    )
                    
                    results["results"].append(query_result)
                    
            except Exception as e:
                execution_time = time.time() - start_time
                query_result = QueryResult(
                    query_id=query.query_id,
                    execution_time=execution_time,
                    rows_returned=0,
                    bytes_returned=0,
                    cache_hit=False,
                    index_used="",
                    error=str(e),
                    timestamp=start_time
                )
                
                results["results"].append(query_result)
        
        # Calculate summary statistics
        successful_results = [r for r in results["results"] if not r.error]
        
        if successful_results:
            execution_times = [r.execution_time for r in successful_results]
            results["summary"] = {
                "total_iterations": iterations,
                "successful_iterations": len(successful_results),
                "failed_iterations": len(results["results"]) - len(successful_results),
                "success_rate": len(successful_results) / iterations * 100,
                "avg_execution_time": statistics.mean(execution_times),
                "min_execution_time": min(execution_times),
                "max_execution_time": max(execution_times),
                "p50_execution_time": statistics.median(execution_times),
                "p95_execution_time": sorted(execution_times)[int(len(execution_times) * 0.95)],
                "p99_execution_time": sorted(execution_times)[int(len(execution_times) * 0.99)],
                "avg_rows_returned": statistics.mean(r.rows_returned for r in successful_results),
                "avg_bytes_returned": statistics.mean(r.bytes_returned for r in successful_results),
                "cache_hit_rate": sum(1 for r in successful_results if r.cache_hit) / len(successful_results) * 100,
                "index_usage_rate": sum(1 for r in successful_results if r.index_used) / len(successful_results) * 100
            }
        else:
            results["summary"] = {
                "total_iterations": iterations,
                "successful_iterations": 0,
                "failed_iterations": iterations,
                "success_rate": 0,
                "error": "All iterations failed"
            }
        
        return results
    
    async def run_concurrent_test(self, query: DatabaseQuery, concurrent_connections: int = 10,
                              duration: int = 60) -> Dict[str, Any]:
        """Run concurrent database test"""
        results = {
            "query_id": query.query_id,
            "concurrent_connections": concurrent_connections,
            "duration": duration,
            "results": [],
            "summary": {}
        }
        
        start_time = time.time()
        tasks = []
        
        async def worker_task(worker_id: int):
            """Worker task for concurrent execution"""
            worker_results = []
            end_time = start_time + duration
            
            while time.time() < end_time:
                query_start = time.time()
                
                try:
                    async with self.pool.acquire() as conn:
                        result = await conn.fetch(query.sql, query.parameters)
                        execution_time = time.time() - query_start
                        
                        worker_results.append({
                            "worker_id": worker_id,
                            "execution_time": execution_time,
                            "rows_returned": len(result),
                            "success": True,
                            "timestamp": query_start
                        })
                        
                except Exception as e:
                    execution_time = time.time() - query_start
                    worker_results.append({
                        "worker_id": worker_id,
                        "execution_time": execution_time,
                        "rows_returned": 0,
                        "success": False,
                        "error": str(e),
                        "timestamp": query_start
                    })
                
                # Small delay to prevent overwhelming the database
                await asyncio.sleep(0.1)
            
            return worker_results
        
        # Create worker tasks
        for i in range(concurrent_connections):
            tasks.append(worker_task(i))
        
        # Wait for all tasks to complete
        worker_results = await asyncio.gather(*tasks)
        
        # Flatten results
        for worker_result in worker_results:
            results["results"].extend(worker_result)
        
        # Calculate summary
        successful_results = [r for r in results["results"] if r["success"]]
        
        if successful_results:
            execution_times = [r["execution_time"] for r in successful_results]
            results["summary"] = {
                "total_requests": len(results["results"]),
                "successful_requests": len(successful_results),
                "failed_requests": len(results["results"]) - len(successful_results),
                "success_rate": len(successful_results) / len(results["results"]) * 100,
                "avg_execution_time": statistics.mean(execution_times),
                "min_execution_time": min(execution_times),
                "max_execution_time": max(execution_times),
                "p50_execution_time": statistics.median(execution_times),
                "p95_execution_time": sorted(execution_times)[int(len(execution_times) * 0.95)],
                "p99_execution_time": sorted(execution_times)[int(len(execution_times) * 0.99)],
                "requests_per_second": len(results["results"]) / duration,
                "avg_rows_returned": statistics.mean(r["rows_returned"] for r in successful_results)
            }
        else:
            results["summary"] = {
                "total_requests": len(results["results"]),
                "successful_requests": 0,
                "failed_requests": len(results["results"]),
                "success_rate": 0,
                "error": "All requests failed"
            }
        
        return results
    
    async def run_load_test(self, query: DatabaseQuery, target_rps: int = 100,
                        duration: int = 300) -> Dict[str, Any]:
        """Run database load test targeting specific RPS"""
        results = {
            "query_id": query.query_id,
            "target_rps": target_rps,
            "duration": duration,
            "results": [],
            "summary": {}
        }
        
        start_time = time.time()
        request_interval = 1.0 / target_rps
        
        async def make_request(request_id: int):
            """Make a single database request"""
            request_start = time.time()
            
            try:
                async with self.pool.acquire() as conn:
                    result = await conn.fetch(query.sql, query.parameters)
                    execution_time = time.time() - request_start
                    
                    return {
                        "request_id": request_id,
                        "execution_time": execution_time,
                        "rows_returned": len(result),
                        "success": True,
                        "timestamp": request_start
                    }
                    
            except Exception as e:
                execution_time = time.time() - request_start
                return {
                    "request_id": request_id,
                    "execution_time": execution_time,
                    "rows_returned": 0,
                    "success": False,
                    "error": str(e),
                    "timestamp": request_start
                }
        
        request_id = 0
        
        while time.time() - start_time < duration:
            # Calculate delay to maintain target RPS
            elapsed = time.time() - start_time
            expected_requests = int(elapsed * target_rps)
            
            if len(results["results"]) < expected_requests:
                # Make request immediately
                result = await make_request(request_id)
                results["results"].append(result)
                request_id += 1
            else:
                # Wait to maintain RPS
                await asyncio.sleep(request_interval)
        
        # Calculate summary
        successful_results = [r for r in results["results"] if r["success"]]
        
        if successful_results:
            execution_times = [r["execution_time"] for r in successful_results]
            actual_rps = len(results["results"]) / duration
            
            results["summary"] = {
                "target_rps": target_rps,
                "actual_rps": actual_rps,
                "rps_efficiency": (actual_rps / target_rps) * 100,
                "total_requests": len(results["results"]),
                "successful_requests": len(successful_results),
                "failed_requests": len(results["results"]) - len(successful_results),
                "success_rate": len(successful_results) / len(results["results"]) * 100,
                "avg_execution_time": statistics.mean(execution_times),
                "min_execution_time": min(execution_times),
                "max_execution_time": max(execution_times),
                "p95_execution_time": sorted(execution_times)[int(len(execution_times) * 0.95)],
                "p99_execution_time": sorted(execution_times)[int(len(execution_times) * 0.99)],
                "avg_rows_returned": statistics.mean(r["rows_returned"] for r in successful_results)
            }
        else:
            results["summary"] = {
                "target_rps": target_rps,
                "actual_rps": 0,
                "rps_efficiency": 0,
                "total_requests": len(results["results"]),
                "successful_requests": 0,
                "failed_requests": len(results["results"]),
                "success_rate": 0,
                "error": "All requests failed"
            }
        
        return results
    
    async def run_full_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive database performance benchmark"""
        benchmark_results = {
            "timestamp": time.time(),
            "queries": {},
            "summary": {}
        }
        
        # Test each query type
        for query in self.test_queries:
            print(f"Testing query: {query.query_id}")
            
            # Single query test
            single_result = await self.run_query_test(query, iterations=10)
            benchmark_results["queries"][query.query_id] = {
                "single_query": single_result
            }
            
            # Concurrent test
            concurrent_result = await self.run_concurrent_test(query, concurrent_connections=5, duration=30)
            benchmark_results["queries"][query.query_id]["concurrent"] = concurrent_result
            
            # Load test (for SELECT queries only)
            if query.query_type == "SELECT":
                load_result = await self.run_load_test(query, target_rps=50, duration=60)
                benchmark_results["queries"][query.query_id]["load_test"] = load_result
            
            print(f"  Single query avg time: {single_result['summary'].get('avg_execution_time', 0):.3f}s")
            print(f"  Concurrent success rate: {concurrent_result['summary'].get('success_rate', 0):.1f}%")
            if query.query_type == "SELECT":
                print(f"  Load test RPS: {load_result['summary'].get('actual_rps', 0):.1f}")
            print()
        
        # Calculate overall summary
        all_single_results = [r["single_query"]["summary"] for r in benchmark_results["queries"].values()]
        all_concurrent_results = [r["concurrent"]["summary"] for r in benchmark_results["queries"].values()]
        all_load_results = [r["load_test"]["summary"] for r in benchmark_results["queries"].values() if "load_test" in r]
        
        benchmark_results["summary"] = {
            "total_queries": len(self.test_queries),
            "avg_single_query_time": statistics.mean(r["avg_execution_time"] for r in all_single_results if "avg_execution_time" in r),
            "avg_concurrent_success_rate": statistics.mean(r["success_rate"] for r in all_concurrent_results if "success_rate" in r),
            "avg_load_rps": statistics.mean(r["actual_rps"] for r in all_load_results if "actual_rps" in r) if all_load_results else 0,
            "overall_success_rate": statistics.mean(r["success_rate"] for r in all_single_results if "success_rate" in r)
        }
        
        return benchmark_results
    
    def _parse_index_used(self, explain_result) -> str:
        """Parse index used from EXPLAIN result"""
        if not explain_result:
            return ""
        
        explain_text = str(explain_result)
        if "Index Scan" in explain_text:
            # Extract index name from "Index Scan using index_name"
            import re
            match = re.search(r"Index Scan using (\w+)", explain_text)
            return match.group(1) if match else ""
        elif "Index Only Scan" in explain_text:
            match = re.search(r"Index Only Scan using (\w+)", explain_text)
            return match.group(1) if match else ""
        elif "Bitmap Heap Scan" in explain_text:
            return "heap_scan"
        elif "Seq Scan" in explain_text:
            return "sequential_scan"
        
        return ""
    
    def _check_cache_hit(self, explain_result) -> bool:
        """Check if query hit cache"""
        if not explain_result:
            return False
        
        explain_text = str(explain_result)
        return "Index Only Scan" in explain_text or "Index Scan" in explain_text
    
    def generate_performance_report(self, results: Dict) -> str:
        """Generate HTML performance report"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SkySentinel Database Performance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background: white; border-radius: 3px; }}
                .success {{ color: green; }}
                .warning {{ color: orange; }}
                .error {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .chart {{ height: 400px; margin: 20px 0; }}
                .query-section {{ margin-bottom: 30px; }}
                .query-header {{ background: #2196F3; color: white; padding: 10px; border-radius: 5px; }}
            </style>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <h1>SkySentinel Database Performance Report</h1>
            
            <div class="summary">
                <h2>Overall Summary</h2>
                <div class="metric">
                    <h3>Total Queries</h3>
                    <p>{results['summary']['total_queries']}</p>
                </div>
                <div class="metric">
                    <h3>Avg Single Query Time</h3>
                    <p>{results['summary']['avg_single_query_time']:.3f}s</p>
                </div>
                <div class="metric">
                    <h3>Avg Concurrent Success Rate</h3>
                    <p>{results['summary']['avg_concurrent_success_rate']:.1f}%</p>
                </div>
                <div class="metric">
                    <h3>Avg Load Test RPS</h3>
                    <p>{results['summary']['avg_load_rps']:.1f}</p>
                </div>
                <div class="metric">
                    <h3>Overall Success Rate</h3>
                    <p class="{'success' if results['summary']['overall_success_rate'] > 95 else 'warning' if results['summary']['overall_success_rate'] > 80 else 'error'}">
                        {results['summary']['overall_success_rate']:.1f}%
                    </p>
                </div>
            </div>
            
            <h2>Query Performance Details</h2>
        """
        
        for query_id, query_data in results["queries"].items():
            html += f"""
            <div class="query-section">
                <div class="query-header">
                    <h3>{query_id}</h3>
                </div>
                
                <h4>Single Query Test</h4>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td>Iterations</td>
                        <td>{query_data['single_query']['summary']['total_iterations']}</td>
                    </tr>
                    <tr>
                        <td>Success Rate</td>
                        <td>{query_data['single_query']['summary']['success_rate']:.2f}%</td>
                    </tr>
                    <tr>
                        <td>Avg Execution Time</td>
                        <td>{query_data['single_query']['summary']['avg_execution_time']:.3f}s</td>
                    </tr>
                    <tr>
                        <td>P95 Execution Time</td>
                        <td>{query_data['single_query']['summary'].get('p95_execution_time', 0):.3f}s</td>
                    </tr>
                    <tr>
                        <td>Avg Rows Returned</td>
                        <td>{query_data['single_query']['summary'].get('avg_rows_returned', 0):.0f}</td>
                    </tr>
                </table>
                
                <h4>Concurrent Test</h4>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td>Concurrent Connections</td>
                        <td>{query_data['concurrent']['summary']['total_requests']}</td>
                    </tr>
                    <tr>
                        <td>Success Rate</td>
                        <td>{query_data['concurrent']['summary']['success_rate']:.2f}%</td>
                    </tr>
                    <tr>
                        <td>Requests Per Second</td>
                        <td>{query_data['concurrent']['summary'].get('requests_per_second', 0):.2f}</td>
                    </tr>
                </table>
            """
            
            if "load_test" in query_data:
                html += f"""
                <h4>Load Test</h4>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td>Target RPS</td>
                        <td>{query_data['load_test']['summary']['target_rps']}</td>
                    </tr>
                    <tr>
                        <td>Actual RPS</td>
                        <td>{query_data['load_test']['summary']['actual_rps']:.2f}</td>
                    </tr>
                    <tr>
                        <td>RPS Efficiency</td>
                        <td>{query_data['load_test']['summary']['rps_efficiency']:.1f}%</td>
                    </tr>
                    <tr>
                        <td>Avg Execution Time</td>
                        <td>{query_data['load_test']['summary']['avg_execution_time']:.3f}s</td>
                    </tr>
                </table>
                """
            
            html += "</div>"
        
        html += """
            <h2>Performance Charts</h2>
            <div class="chart">
                <canvas id="performanceChart"></canvas>
            </div>
            
            <script>
                const ctx = document.getElementById('performanceChart').getContext('2d');
                const chart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: [""" + '","'.join([f"'{q}'" for q in results["queries"].keys()]) + """],
                        datasets: [
                            {
                                label: 'Single Query Time (ms)',
                                data: [""" + '","'.join([f"{r['single_query']['summary'].get('avg_execution_time', 0) * 1000}" for r in results["queries"].values()]) + """],
                                backgroundColor: 'rgba(54, 162, 235, 0.8)'
                            },
                            {
                                label: 'Concurrent Success Rate (%)',
                                data: [""" + '","'.join([f"{r['concurrent']['summary'].get('success_rate', 0)}" for r in results["queries"].values()]) + """],
                                backgroundColor: 'rgba(75, 192, 192, 0.8)'
                            }
                        ]
                    },
                    options: {
                        scales: {
                            y: {
                                beginAtZero: true
                            }
                        }
                    }
                });
            </script>
        </body>
        </html>
        """
        
        return html


async def run_database_performance_suite():
    """Run complete database performance test suite"""
    # Example connection string - replace with actual
    connection_string = "postgresql://user:password@localhost:5432/skysentinel"
    
    tester = DatabasePerformanceTester(connection_string)
    
    try:
        # Initialize connection pool
        await tester.initialize_pool()
        
        # Run full benchmark
        print("Running database performance benchmark...")
        results = await tester.run_full_benchmark()
        
        # Generate report
        report = tester.generate_performance_report(results)
        with open("database_performance_report.html", "w") as f:
            f.write(report)
        
        # Print summary
        summary = results["summary"]
        print(f"Benchmark completed:")
        print(f"  Total queries: {summary['total_queries']}")
        print(f"  Avg single query time: {summary['avg_single_query_time']:.3f}s")
        print(f"  Avg concurrent success rate: {summary['avg_concurrent_success_rate']:.1f}%")
        print(f"  Avg load test RPS: {summary['avg_load_rps']:.1f}")
        print(f"  Overall success rate: {summary['overall_success_rate']:.1f}%")
        print(f"Report saved to database_performance_report.html")
        
        return results
        
    finally:
        await tester.close_pool()


if __name__ == "__main__":
    asyncio.run(run_database_performance_suite())
