import asyncio
import aiohttp
import time
import statistics
from typing import Dict, List, Any
import json
from concurrent.futures import ThreadPoolExecutor
import random

class LoadTest:
    """Load testing framework for SkySentinel"""
    
    def __init__(self, base_url: str, auth_token: str = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}" if auth_token else ""
        }
    
    async def test_api_endpoint(self, endpoint: str, method: str = "GET", 
                               payload: Dict = None, concurrent_users: int = 10,
                               duration: int = 60) -> Dict[str, Any]:
        """Test API endpoint with concurrent users"""
        start_time = time.time()
        results = {
            "endpoint": endpoint,
            "method": method,
            "concurrent_users": concurrent_users,
            "duration": duration,
            "requests": [],
            "summary": {}
        }
        
        semaphore = asyncio.Semaphore(concurrent_users)
        
        async def make_request(session, request_id: int):
            async with semaphore:
                request_start = time.time()
                try:
                    if method == "GET":
                        async with session.get(f"{self.base_url}{endpoint}") as response:
                            status = response.status
                            body = await response.text()
                    elif method == "POST":
                        async with session.post(f"{self.base_url}{endpoint}", 
                                              json=payload) as response:
                            status = response.status
                            body = await response.text()
                    else:
                        raise ValueError(f"Unsupported method: {method}")
                    
                    request_time = time.time() - request_start
                    
                    results["requests"].append({
                        "id": request_id,
                        "status": status,
                        "response_time": request_time,
                        "success": status < 400
                    })
                    
                    return request_time, status
                    
                except Exception as e:
                    request_time = time.time() - request_start
                    results["requests"].append({
                        "id": request_id,
                        "status": 0,
                        "response_time": request_time,
                        "success": False,
                        "error": str(e)
                    })
                    return request_time, 0
        
        # Create async session
        async with aiohttp.ClientSession(headers=self.headers) as session:
            tasks = []
            request_id = 0
            
            # Run for specified duration
            while time.time() - start_time < duration:
                tasks.append(make_request(session, request_id))
                request_id += 1
                
                # Control rate to maintain concurrent users
                await asyncio.sleep(random.uniform(0.01, 0.1))
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks)
        
        # Calculate statistics
        successful_requests = [r for r in results["requests"] if r["success"]]
        failed_requests = [r for r in results["requests"] if not r["success"]]
        
        if successful_requests:
            response_times = [r["response_time"] for r in successful_requests]
            results["summary"] = {
                "total_requests": len(results["requests"]),
                "successful_requests": len(successful_requests),
                "failed_requests": len(failed_requests),
                "success_rate": len(successful_requests) / len(results["requests"]) * 100,
                "avg_response_time": statistics.mean(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "p50_response_time": statistics.median(response_times),
                "p90_response_time": sorted(response_times)[int(len(response_times) * 0.9)],
                "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)],
                "p99_response_time": sorted(response_times)[int(len(response_times) * 0.99)],
                "requests_per_second": len(results["requests"]) / duration
            }
        
        return results
    
    async def test_scenario(self, scenario: Dict) -> Dict[str, Any]:
        """Test a complete user scenario"""
        results = {
            "scenario": scenario["name"],
            "start_time": time.time(),
            "steps": [],
            "summary": {}
        }
        
        for step in scenario["steps"]:
            step_result = await self.test_api_endpoint(
                endpoint=step["endpoint"],
                method=step.get("method", "GET"),
                payload=step.get("payload"),
                concurrent_users=step.get("concurrent_users", 1),
                duration=step.get("duration", 10)
            )
            
            results["steps"].append(step_result)
        
        # Calculate scenario statistics
        total_requests = sum(len(step["requests"]) for step in results["steps"])
        total_success = sum(step["summary"].get("successful_requests", 0) for step in results["steps"])
        avg_response_time = statistics.mean(
            step["summary"].get("avg_response_time", 0) 
            for step in results["steps"] 
            if step["summary"].get("avg_response_time")
        )
        
        results["summary"] = {
            "total_steps": len(results["steps"]),
            "total_requests": total_requests,
            "total_success": total_success,
            "success_rate": total_success / total_requests * 100 if total_requests > 0 else 0,
            "avg_response_time": avg_response_time,
            "total_duration": time.time() - results["start_time"]
        }
        
        return results
    
    def generate_report(self, test_results: Dict) -> str:
        """Generate HTML report from test results"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SkySentinel Load Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background: white; border-radius: 3px; }}
                .success {{ color: green; }}
                .warning {{ color: orange; }}
                .error {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .chart {{ height: 300px; margin: 20px 0; }}
            </style>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <h1>SkySentinel Load Test Report</h1>
            <div class="summary">
                <h2>Summary</h2>
                <div class="metric">
                    <h3>Success Rate</h3>
                    <p class="{'success' if test_results['summary']['success_rate'] > 95 else 'warning' if test_results['summary']['success_rate'] > 80 else 'error'}">
                        {test_results['summary']['success_rate']:.2f}%
                    </p>
                </div>
                <div class="metric">
                    <h3>Avg Response Time</h3>
                    <p>{test_results['summary']['avg_response_time']:.3f}s</p>
                </div>
                <div class="metric">
                    <h3>Total Requests</h3>
                    <p>{test_results['summary']['total_requests']}</p>
                </div>
                <div class="metric">
                    <h3>Total Duration</h3>
                    <p>{test_results['summary']['total_duration']:.2f}s</p>
                </div>
            </div>
            
            <h2>Response Time Distribution</h2>
            <div class="chart">
                <canvas id="responseTimeChart"></canvas>
            </div>
            
            <h2>Detailed Results</h2>
            <table>
                <tr>
                    <th>Endpoint</th>
                    <th>Method</th>
                    <th>Requests</th>
                    <th>Success Rate</th>
                    <th>Avg Response Time</th>
                    <th>P95 Response Time</th>
                    <th>RPS</th>
                </tr>
        """
        
        for step in test_results.get("steps", []):
            html += f"""
                <tr>
                    <td>{step['endpoint']}</td>
                    <td>{step['method']}</td>
                    <td>{step['summary'].get('total_requests', 0)}</td>
                    <td>{step['summary'].get('success_rate', 0):.2f}%</td>
                    <td>{step['summary'].get('avg_response_time', 0):.3f}s</td>
                    <td>{step['summary'].get('p95_response_time', 0):.3f}s</td>
                    <td>{step['summary'].get('requests_per_second', 0):.2f}</td>
                </tr>
            """
        
        html += """
            </table>
            
            <script>
                // Response time chart
                const ctx = document.getElementById('responseTimeChart').getContext('2d');
                const chart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: ['P50', 'P90', 'P95', 'P99', 'Max'],
                        datasets: [{
                            label: 'Response Time (ms)',
                            data: [
                                """ + str(test_results['summary'].get('p50_response_time', 0) * 1000) + """,
                                """ + str(test_results['summary'].get('p90_response_time', 0) * 1000) + """,
                                """ + str(test_results['summary'].get('p95_response_time', 0) * 1000) + """,
                                """ + str(test_results['summary'].get('p99_response_time', 0) * 1000) + """
                            ],
                            borderColor: 'rgb(75, 192, 192)',
                            tension: 0.1
                        }]
                    },
                    options: {
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'Response Time (ms)'
                                }
                            }
                        }
                    }
                });
            </script>
        </body>
        </html>
        """
        
        return html

# Example test scenarios
TEST_SCENARIOS = {
    "dashboard_load": {
        "name": "Dashboard Load Test",
        "steps": [
            {
                "name": "Get Dashboard Overview",
                "endpoint": "/api/v1/dashboard/overview",
                "method": "GET",
                "concurrent_users": 20,
                "duration": 300  # 5 minutes
            },
            {
                "name": "Get Violations",
                "endpoint": "/api/v1/violations",
                "method": "GET",
                "concurrent_users": 10,
                "duration": 300
            },
            {
                "name": "Get Resources",
                "endpoint": "/api/v1/resources",
                "method": "GET",
                "concurrent_users": 15,
                "duration": 300
            }
        ]
    },
    
    "policy_evaluation": {
        "name": "Policy Evaluation Load Test",
        "steps": [
            {
                "name": "Evaluate IaC Plan",
                "endpoint": "/api/v1/evaluate/iac",
                "method": "POST",
                "payload": {
                    "iac_type": "terraform",
                    "resources": [
                        {
                            "type": "aws:s3:bucket",
                            "properties": {"acl": "public-read"}
                        }
                    ]
                },
                "concurrent_users": 5,
                "duration": 600  # 10 minutes
            }
        ]
    },
    
    "graph_queries": {
        "name": "Graph Query Performance Test",
        "steps": [
            {
                "name": "Query Attack Paths",
                "endpoint": "/api/v1/graph/attack-paths",
                "method": "POST",
                "payload": {
                    "from": "internet",
                    "to": "database",
                    "max_depth": 5
                },
                "concurrent_users": 3,
                "duration": 300
            },
            {
                "name": "Query Resource Graph",
                "endpoint": "/api/v1/graph/resources",
                "method": "POST",
                "payload": {
                    "filters": {
                        "cloud": "aws",
                        "has_violations": True
                    }
                },
                "concurrent_users": 5,
                "duration": 300
            }
        ]
    }
}

async def run_performance_suite():
    """Run complete performance test suite"""
    load_tester = LoadTest(
        base_url="https://api.skysentinel.io",
        auth_token="your-test-token"
    )
    
    all_results = {}
    
    # Run each scenario
    for scenario_name, scenario_config in TEST_SCENARIOS.items():
        print(f"Running scenario: {scenario_name}")
        
        results = await load_tester.test_scenario(scenario_config)
        all_results[scenario_name] = results
        
        # Print summary
        summary = results["summary"]
        print(f"  Success Rate: {summary['success_rate']:.2f}%")
        print(f"  Avg Response Time: {summary['avg_response_time']:.3f}s")
        print(f"  Total Requests: {summary['total_requests']}")
        print()
    
    # Generate combined report
    combined_report = load_tester.generate_report({
        "summary": {
            "success_rate": statistics.mean(r["summary"]["success_rate"] for r in all_results.values()),
            "avg_response_time": statistics.mean(r["summary"]["avg_response_time"] for r in all_results.values()),
            "total_requests": sum(r["summary"]["total_requests"] for r in all_results.values()),
            "total_duration": sum(r["summary"]["total_duration"] for r in all_results.values()),
            "p50_response_time": statistics.median(
                r["summary"].get("p50_response_time", 0) 
                for r in all_results.values() 
                if r["summary"].get("p50_response_time")
            ),
            "p95_response_time": statistics.median(
                r["summary"].get("p95_response_time", 0) 
                for r in all_results.values() 
                if r["summary"].get("p95_response_time")
            )
        },
        "steps": [step for r in all_results.values() for step in r["steps"]]
    })
    
    # Save report
    with open("performance_report.html", "w") as f:
        f.write(combined_report)
    
    print("Performance test completed. Report saved to performance_report.html")
    
    return all_results

if __name__ == "__main__":
    asyncio.run(run_performance_suite())
