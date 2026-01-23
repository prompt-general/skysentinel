# SkySentinel Performance Testing & Optimization

Comprehensive performance testing, monitoring, and optimization framework for SkySentinel.

## Overview

The performance framework provides:
- **Load Testing** - Concurrent user testing with detailed metrics
- **Stress Testing** - System breaking point and endurance testing
- **Performance Monitoring** - Real-time system and application metrics
- **Database Performance** - Query optimization and connection pool testing
- **Performance Optimization** - System tuning and application optimization
- **Benchmarking** - Performance comparison and trend analysis
- **Real-time Dashboard** - Live performance monitoring and alerting

## Components

### 1. Load Testing (`load_testing.py`)

Load testing framework for API and application performance:

**Features:**
- Concurrent user simulation
- Response time analysis (P50, P90, P95, P99)
- Success rate tracking
- Requests per second measurement
- HTML report generation with charts

**Usage Example:**
```python
from performance.load_testing import LoadTest, run_performance_suite

# Basic load test
load_tester = LoadTest(
    base_url="https://api.skysentinel.io",
    auth_token="your-token"
)

results = await load_tester.test_api_endpoint(
    endpoint="/api/v1/dashboard/overview",
    method="GET",
    concurrent_users=50,
    duration=300
)

print(f"Success Rate: {results['summary']['success_rate']:.2f}%")
print(f"Avg Response Time: {results['summary']['avg_response_time']:.3f}s")
```

**Test Scenarios:**
- Dashboard load testing
- Policy evaluation performance
- Graph query performance
- Custom scenario testing

### 2. Stress Testing (`stress_testing.py`)

Comprehensive stress testing capabilities:

**Test Types:**
- **Spike Test**: Sudden load increase
- **Gradual Test**: Slowly increasing load
- **Surge Test**: Multiple load spikes
- **Breakpoint Test**: Find system breaking point
- **Endurance Test**: Sustained load testing

**System Monitoring:**
- CPU and memory usage tracking
- Disk I/O monitoring
- Network I/O measurement
- Process count tracking

**Usage Example:**
```python
from performance.stress_testing import StressTest

stress_tester = StressTest(
    base_url="https://api.skysentinel.io",
    auth_token="your-token"
)

# Find breaking point
results = await stress_tester.breakpoint_test(
    endpoint="/api/v1/dashboard",
    initial_users=10,
    user_increment=10,
    max_duration=600
)

if results["breakpoint"]:
    print(f"Breaking point: {results['breakpoint']['users']} users")
    print(f"Success rate at breakpoint: {results['breakpoint']['success_rate']:.2f}%")
```

### 3. Performance Monitoring (`monitoring.py`)

Real-time performance monitoring and alerting:

**Metrics Collected:**
- System metrics (CPU, memory, disk, network)
- Application metrics (response times, error rates)
- Database metrics (query times, connection pools)
- Custom metrics integration

**Alerting:**
- Configurable thresholds
- Multiple alert handlers
- Real-time notifications
- Alert history tracking

**Usage Example:**
```python
from performance.monitoring import PerformanceMonitor, PerformanceAlertHandler

monitor = PerformanceMonitor(redis_url="redis://localhost:6379")

# Add alert handler
monitor.add_alert_handler(PerformanceAlertHandler(webhook_url="https://hooks.slack.com/..."))

# Start monitoring
await monitor.start_monitoring()

# Record application metric
from performance.monitoring import ApplicationMetric

metric = ApplicationMetric(
    timestamp=time.time(),
    endpoint="/api/v1/dashboard",
    method="GET",
    response_time=0.150,
    status_code=200,
    success=True,
    user_id="user123",
    tenant_id="tenant1",
    request_size=100,
    response_size=500
)

monitor.record_application_metric(metric)

# Get performance summary
summary = monitor.get_performance_summary(duration_minutes=60)
print(f"Success Rate: {summary['application']['success_rate']:.2f}%")
print(f"Avg Response Time: {summary['application']['avg_response_time']:.3f}s")
```

### 4. Database Performance (`database_performance.py`)

Database performance testing and optimization:

**Test Types:**
- Single query performance testing
- Concurrent connection testing
- Load testing for specific RPS
- Connection pool optimization
- Query plan analysis

**Query Types:**
- Simple SELECT queries
- Complex JOIN operations
- Aggregate functions
- Subqueries and CTEs
- Window functions
- INSERT/UPDATE/DELETE operations

**Usage Example:**
```python
from performance.database_performance import DatabasePerformanceTester

tester = DatabasePerformanceTester(
    connection_string="postgresql://user:password@localhost:5432/skysentinel"
)

await tester.initialize_pool()

# Run full benchmark
results = await tester.run_full_benchmark()

# Generate report
report = tester.generate_performance_report(results)
with open("database_performance_report.html", "w") as f:
    f.write(report)

await tester.close_pool()
```

### 5. Performance Optimization (`optimization.py`)

System and application performance optimization:

**Optimization Areas:**
- System resource tuning
- Database configuration optimization
- Application performance tuning
- Resource allocation optimization

**Features:**
- Performance profile analysis
- Optimization recommendations
- System setting optimization
- Impact monitoring

**Usage Example:**
```python
from performance.optimization import PerformanceOptimizer

optimizer = PerformanceOptimizer()

# Collect performance profile
profile = optimizer.collect_performance_profile(duration=300)

# Generate optimization plan
plan = optimizer.generate_optimization_plan(profile)

# Apply optimizations
applied = optimizer.apply_optimizations(plan["recommendations"])

# Monitor impact
impact = optimizer.monitor_optimization_impact(duration=300)
print(f"CPU improvement: {impact['performance_impact']['cpu_improvement']:.1f}%")
```

### 6. Benchmarking (`benchmarking.py`)

Performance benchmarking and comparison:

**Benchmark Types:**
- Load benchmarks
- Database benchmarks
- Stress benchmarks
- Endurance benchmarks

**Features:**
- Baseline comparison
- Trend analysis
- Performance regression detection
- Automated benchmark scheduling

**Usage Example:**
```python
from performance.benchmarking import PerformanceBenchmark

benchmark = PerformanceBenchmark()

# Run load benchmark
load_result = await benchmark.run_load_benchmark(
    test_name="API Load Test",
    target_url="https://api.skysentinel.io",
    concurrent_users=50,
    duration=300
)

# Run database benchmark
db_result = await benchmark.run_database_benchmark(
    test_name="Query Performance",
    connection_string="postgresql://...",
    query="SELECT COUNT(*) FROM violations",
    iterations=100
)

# Create benchmark suite
suite = benchmark.create_benchmark_suite(
    name="Performance Suite",
    results=[load_result, db_result]
)

# Set as baseline
benchmark.set_baseline(suite)
```

### 7. Performance Dashboard (`dashboard.py`)

Real-time performance monitoring dashboard:

**Dashboard Features:**
- Real-time metrics display
- Performance trends visualization
- Alert notifications
- System resource monitoring
- Historical data analysis

**Metrics Displayed:**
- CPU and memory usage
- Response time trends
- Error rates
- Request rates
- Database performance

**Usage Example:**
```python
from performance.dashboard import PerformanceDashboard

dashboard = PerformanceDashboard(redis_url="redis://localhost:6379")

# Start dashboard
await dashboard.start_dashboard()

# Get real-time data
data = dashboard.get_real_time_dashboard_data()
print(f"Current CPU: {data['real_time_stats']['cpu_current']:.1f}%")
print(f"Current Memory: {data['real_time_stats']['memory_current']:.1f}%")

# Create HTML dashboard
dashboard.create_performance_dashboard("performance_dashboard.html")
```

## Quick Start

### 1. Basic Load Testing

```python
import asyncio
from performance.load_testing import LoadTest

async def quick_load_test():
    load_tester = LoadTest(
        base_url="https://api.skysentinel.io",
        auth_token="your-token"
    )
    
    results = await load_tester.test_api_endpoint(
        endpoint="/api/v1/dashboard",
        concurrent_users=20,
        duration=60
    )
    
    print(f"Success Rate: {results['summary']['success_rate']:.2f}%")
    print(f"Avg Response Time: {results['summary']['avg_response_time']:.3f}s")
    print(f"Requests/sec: {results['summary']['requests_per_second']:.2f}")

asyncio.run(quick_load_test())
```

### 2. Performance Monitoring

```python
import asyncio
from performance.monitoring import PerformanceMonitor

async def start_monitoring():
    monitor = PerformanceMonitor()
    await monitor.start_monitoring()
    
    # Monitor for 5 minutes
    await asyncio.sleep(300)
    
    # Get summary
    summary = monitor.get_performance_summary(duration_minutes=5)
    print(f"Overall Success Rate: {summary['application']['success_rate']:.2f}%")
    
    monitor.stop_monitoring()

asyncio.run(start_monitoring())
```

### 3. Database Performance Testing

```python
import asyncio
from performance.database_performance import DatabasePerformanceTester

async def test_database():
    tester = DatabasePerformanceTester("postgresql://user:password@localhost:5432/skysentinel")
    
    try:
        await tester.initialize_pool()
        results = await tester.run_full_benchmark()
        
        summary = results["summary"]
        print(f"Avg Query Time: {summary['avg_single_query_time']:.3f}s")
        print(f"Overall Success Rate: {summary['overall_success_rate']:.2f}%")
        
    finally:
        await tester.close_pool()

asyncio.run(test_database())
```

## Configuration

### Environment Setup

**Dependencies:**
```bash
pip install aiohttp psutil asyncpg redis aioredis statistics
```

**System Requirements:**
- Python 3.8+
- Redis server (for monitoring)
- PostgreSQL (for database testing)
- Sufficient system resources for testing

### Test Configuration

**Load Test Configuration:**
```python
load_config = {
    "base_url": "https://api.skysentinel.io",
    "auth_token": "your-token",
    "concurrent_users": 50,
    "duration": 300,
    "endpoints": [
        {"path": "/api/v1/dashboard", "method": "GET"},
        {"path": "/api/v1/violations", "method": "GET"},
        {"path": "/api/v1/resources", "method": "GET"}
    ]
}
```

**Monitoring Configuration:**
```python
monitoring_config = {
    "redis_url": "redis://localhost:6379",
    "alert_thresholds": {
        "cpu_warning": 80.0,
        "cpu_critical": 95.0,
        "memory_warning": 85.0,
        "memory_critical": 95.0,
        "response_time_warning": 2.0,
        "response_time_critical": 5.0
    },
    "refresh_interval": 5
}
```

**Database Configuration:**
```python
db_config = {
    "connection_string": "postgresql://user:password@localhost:5432/skysentinel",
    "pool_size": 20,
    "max_overflow": 10,
    "pool_timeout": 30
}
```

## Test Scenarios

### 1. API Load Testing

**Dashboard Load Test:**
```python
dashboard_scenario = {
    "name": "Dashboard Load Test",
    "steps": [
        {
            "name": "Get Dashboard Overview",
            "endpoint": "/api/v1/dashboard/overview",
            "method": "GET",
            "concurrent_users": 20,
            "duration": 300
        },
        {
            "name": "Get Violations",
            "endpoint": "/api/v1/violations",
            "method": "GET",
            "concurrent_users": 10,
            "duration": 300
        }
    ]
}
```

### 2. Stress Testing Scenarios

**Spike Test:**
```python
spike_config = {
    "base_users": 10,
    "spike_users": 100,
    "spike_duration": 30,
    "total_duration": 300
}
```

**Breakpoint Test:**
```python
breakpoint_config = {
    "initial_users": 10,
    "user_increment": 10,
    "max_duration": 600,
    "failure_threshold": 0.05
}
```

### 3. Database Performance Tests

**Query Performance:**
```python
query_tests = [
    {
        "name": "Simple Select",
        "sql": "SELECT id, name FROM users WHERE tenant_id = %(tenant_id)s LIMIT 100",
        "parameters": {"tenant_id": "test_tenant"},
        "iterations": 100
    },
    {
        "name": "Complex Join",
        "sql": """
        SELECT u.id, u.name, COUNT(v.id) as violation_count
        FROM users u
        LEFT JOIN violations v ON u.id = v.user_id
        WHERE u.tenant_id = %(tenant_id)s
        GROUP BY u.id, u.name
        """,
        "parameters": {"tenant_id": "test_tenant"},
        "iterations": 50
    }
]
```

## Reporting

### 1. Load Test Reports

**HTML Report Features:**
- Executive summary with key metrics
- Response time distribution charts
- Detailed results table
- Performance recommendations

**Generate Report:**
```python
from performance.load_testing import LoadTest

load_tester = LoadTest(base_url, auth_token)
results = await load_tester.test_scenario(scenario)
report = load_tester.generate_report(results)

with open("load_test_report.html", "w") as f:
    f.write(report)
```

### 2. Stress Test Reports

**Stress Test Report Features:**
- System resource usage charts
- Performance over time graphs
- Breakpoint analysis
- System capacity assessment

### 3. Database Performance Reports

**Database Report Features:**
- Query performance metrics
- Index usage analysis
- Cache hit rates
- Connection pool statistics

### 4. Benchmark Comparison Reports

**Comparison Report Features:**
- Baseline vs current performance
- Performance trends
- Improvement/regression analysis
- Recommendations

## Monitoring & Alerting

### 1. Real-time Monitoring

**Metrics Monitored:**
- CPU and memory usage
- Response times and error rates
- Database query performance
- System resource utilization

**Dashboard Features:**
- Real-time metric display
- Historical trend charts
- Alert notifications
- System health indicators

### 2. Alert Configuration

**Alert Types:**
- CPU usage alerts
- Memory usage alerts
- Response time alerts
- Error rate alerts
- Database performance alerts

**Alert Handlers:**
- Slack webhook integration
- Email notifications
- Custom alert handlers
- Alert history tracking

## Performance Optimization

### 1. System Optimization

**Optimization Areas:**
- CPU governor settings
- Memory swappiness
- I/O scheduler configuration
- Network parameters
- File descriptor limits

**Implementation:**
```python
from performance.optimization import PerformanceOptimizer

optimizer = PerformanceOptimizer()

# Apply system optimizations
optimizations = optimizer.optimize_system_settings()
applied = optimizer.apply_optimizations(optimizations)

# Monitor impact
impact = optimizer.monitor_optimization_impact(duration=300)
```

### 2. Application Optimization

**Optimization Areas:**
- Database connection pooling
- Query optimization
- Caching configuration
- Async worker configuration
- Resource allocation

**Configuration Recommendations:**
```python
app_config = {
    "database": {
        "pool_size": 20,
        "max_overflow": 10,
        "pool_timeout": 30
    },
    "caching": {
        "redis": {
            "max_connections": 10,
            "socket_timeout": 5
        }
    },
    "async": {
        "workers": 4,
        "worker_connections": 1000
    }
}
```

## Benchmarking & Comparison

### 1. Baseline Establishment

**Creating Baselines:**
```python
from performance.benchmarking import PerformanceBenchmark

benchmark = PerformanceBenchmark()

# Run baseline tests
baseline_results = await benchmark.run_full_benchmark()
baseline_suite = benchmark.create_benchmark_suite("Baseline", baseline_results)
benchmark.set_baseline(baseline_suite)
```

### 2. Performance Comparison

**Comparing Performance:**
```python
# Run current tests
current_results = await benchmark.run_full_benchmark()
current_suite = benchmark.create_benchmark_suite("Current", current_results)
benchmark.set_current(current_suite)

# Compare with baseline
comparison = benchmark.compare_benchmarks()

if comparison:
    print(f"Net improvement: {comparison['summary']['net_improvement']:.2f}%")
    print(f"Improvements: {len(comparison['improvements'])}")
    print(f"Regressions: {len(comparison['regressions'])}")
```

### 3. Trend Analysis

**Performance Trends:**
```python
# Get performance trends
trends = benchmark.get_benchmark_trends(days=30)

for date, metrics in trends.items():
    print(f"{date}: Avg Response Time: {metrics['avg_response_time']:.3f}s")
```

## Best Practices

### 1. Test Planning

**Test Design:**
- Define clear performance objectives
- Use realistic test scenarios
- Include multiple load levels
- Test during different times

**Test Environment:**
- Use production-like environment
- Isolate test environment
- Monitor system resources
- Document test conditions

### 2. Monitoring Strategy

**Metrics Collection:**
- Monitor all relevant metrics
- Use appropriate sampling rates
- Store historical data
- Set meaningful alert thresholds

**Alert Management:**
- Configure appropriate thresholds
- Use multiple alert channels
- Implement alert escalation
- Track alert history

### 3. Performance Optimization

**Optimization Process:**
1. Profile performance
2. Identify bottlenecks
3. Implement optimizations
4. Measure impact
5. Iterate as needed

**Optimization Priorities:**
1. Critical performance issues
2. High-impact improvements
3. Low-effort optimizations
4. Long-term architectural changes

### 4. Benchmarking Strategy

**Benchmark Management:**
- Establish baselines
- Track performance trends
- Compare against targets
- Document regressions

**Continuous Improvement:**
- Regular benchmarking
- Performance regression testing
- Trend analysis
- Optimization tracking

## Troubleshooting

### Common Issues

1. **Test Execution Failures**
   - Check target availability
   - Verify authentication
   - Review test configuration
   - Check system resources

2. **Performance Degradation**
   - Monitor system resources
   - Check database performance
   - Review recent changes
   - Analyze performance trends

3. **Monitoring Issues**
   - Verify Redis connectivity
   - Check alert thresholds
   - Review metric collection
   - Validate alert handlers

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration

### CI/CD Integration

**Pipeline Integration:**
```yaml
# Example GitLab CI configuration
performance_test:
  stage: test
  script:
    - python -m performance.load_testing
    - python -m performance.stress_testing
    - python -m performance.database_performance
  artifacts:
    reports:
      junit: performance_reports/*.xml
    paths:
      - performance_reports/*.html
```

### Monitoring Integration

**Prometheus Integration:**
```python
from performance.monitoring import PerformanceMonitor

monitor = PerformanceMonitor()

# Export metrics to Prometheus
def prometheus_exporter():
    metrics = monitor.get_current_metrics()
    # Export to Prometheus format
    pass
```

## Security Considerations

### Test Security

- Use test credentials only
- Secure test data
- Isolate test environment
- Monitor test impact

### Data Protection

- Encrypt sensitive metrics
- Limit metric retention
- Secure alert configurations
- Access control for dashboards

## Performance Optimization

### Resource Management

- Monitor resource usage
- Optimize test configurations
- Use appropriate concurrency
- Implement resource limits

### Test Efficiency

- Use parallel execution
- Optimize test data
- Cache test results
- Minimize test overhead

## Extending the Framework

### Custom Tests

```python
from performance.load_testing import LoadTest

class CustomLoadTest(LoadTest):
    async def custom_test(self, config):
        # Implement custom test logic
        pass
```

### Custom Metrics

```python
from performance.monitoring import ApplicationMetric

# Create custom metric
custom_metric = ApplicationMetric(
    timestamp=time.time(),
    metric_name="custom_metric",
    value=100.0,
    unit="ms",
    tags=["custom"],
    source="application"
)
```

### Custom Optimizations

```python
from performance.optimization import PerformanceOptimizer

class CustomOptimizer(PerformanceOptimizer):
    def custom_optimization(self):
        # Implement custom optimization logic
        pass
```

## Support

### Documentation

- API documentation available
- Code examples and tutorials
- Best practices guide
- Troubleshooting guide

### Community

- GitHub issues for bug reports
- Feature requests and discussions
- Contribution guidelines
- Performance optimization tips

## License

This performance testing framework is part of SkySentinel and follows the project's licensing terms.

## Version History

- **v1.0**: Initial release with load testing and monitoring
- **v1.1**: Added stress testing and database performance testing
- **v1.2**: Enhanced optimization tools and benchmarking
- **v1.3**: Added real-time dashboard and alerting
- **v1.4**: Improved reporting and integration capabilities
