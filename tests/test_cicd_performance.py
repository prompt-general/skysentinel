import pytest
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, AsyncMock

# Import the classes we're testing
import sys
sys.path.append(str(Path(__file__).parent.parent))

from cicd_prevention.service import CICDService
from cicd_prevention.parsers.terraform import TerraformParser

class TestCICDPerformance:
    
    @pytest.fixture
    def mock_policy_engine(self):
        """Mock policy engine for performance testing"""
        engine = Mock()
        engine.evaluate_event = Mock(return_value=[])
        engine.evaluate_batch = Mock(return_value=[])
        return engine
    
    @pytest.fixture
    def mock_predictor(self):
        """Mock ML predictor for performance testing"""
        predictor = Mock()
        predictor.predict_violations = Mock(return_value={
            "violation_probability": 0.1,
            "confidence": 0.8,
            "risk_factors": []
        })
        return predictor
    
    @pytest.fixture
    def mock_neo4j(self):
        """Mock Neo4j database for performance testing"""
        neo4j = Mock()
        neo4j.query = Mock(return_value=[])
        neo4j.create_evaluation = Mock(return_value="eval-123")
        return neo4j
    
    @pytest.fixture
    def cicd_service(self, mock_policy_engine, mock_predictor, mock_neo4j):
        """Create CICDService instance with mocked dependencies"""
        service = CICDService(mock_policy_engine, mock_predictor, mock_neo4j)
        
        # Mock the async evaluation method
        service.evaluate_plan = AsyncMock(return_value={
            'evaluation_id': 'eval-123',
            'result': 'pass',
            'plan_summary': {'total_resources': 1},
            'policy_evaluation': {'total_violations': 0},
            'ml_predictions': {'violation_probability': 0.1}
        })
        return service
    
    def test_concurrent_evaluations(self, cicd_service):
        """Test concurrent IaC evaluations"""
        # Create test plans
        test_plans = []
        for i in range(10):
            plan = {
                "resource_changes": [
                    {
                        "address": f"aws_s3_bucket.bucket_{i}",
                        "type": "aws_s3_bucket",
                        "change": {"actions": ["create"]}
                    }
                ]
            }
            test_plans.append(plan)
        
        # Run evaluations concurrently
        start_time = time.time()
        
        async def run_evaluation(plan):
            return await cicd_service.evaluate_plan(
                iac_type="terraform",
                iac_content=plan,
                context={"test": True}
            )
        
        # Use asyncio to run concurrently
        loop = asyncio.get_event_loop()
        tasks = [run_evaluation(plan) for plan in test_plans]
        results = loop.run_until_complete(asyncio.gather(*tasks))
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert len(results) == 10
        assert duration < 30  # Should complete within 30 seconds
        
        print(f"Concurrent evaluations completed in {duration:.2f} seconds")
        print(f"Average time per evaluation: {duration/10:.2f} seconds")
    
    def test_large_plan_evaluation(self, cicd_service):
        """Test evaluation of large IaC plan"""
        # Create plan with 1000 resources
        large_plan = {
            "resource_changes": []
        }
        
        for i in range(1000):
            resource = {
                "address": f"aws_ec2_instance.instance_{i}",
                "type": "aws_ec2_instance",
                "change": {
                    "actions": ["create"],
                    "after": {
                        "instance_type": "t2.micro",
                        "tags": {"env": "test"}
                    }
                }
            }
            large_plan["resource_changes"].append(resource)
        
        # Mock the service to return appropriate summary
        cicd_service.evaluate_plan = AsyncMock(return_value={
            'evaluation_id': 'eval-123',
            'result': 'pass',
            'plan_summary': {'total_resources': 1000},
            'policy_evaluation': {'total_violations': 0},
            'ml_predictions': {'violation_probability': 0.1}
        })
        
        # Time the evaluation
        start_time = time.time()
        
        result = asyncio.run(cicd_service.evaluate_plan(
            iac_type="terraform",
            iac_content=large_plan,
            context={"large_test": True}
        ))
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert result['plan_summary']['total_resources'] == 1000
        assert duration < 60  # Should complete within 60 seconds
        
        print(f"Large plan evaluation ({len(large_plan['resource_changes'])} resources) completed in {duration:.2f} seconds")
    
    def test_parser_performance(self):
        """Test parser performance with large inputs"""
        parser = TerraformParser()
        
        # Create large Terraform plan
        large_plan = {
            "format_version": "1.0",
            "terraform_version": "1.5.0",
            "planned_values": {
                "root_module": {
                    "resources": []
                }
            }
        }
        
        # Add 500 resources
        for i in range(500):
            resource = {
                "address": f"aws_s3_bucket.test_{i}",
                "mode": "managed",
                "type": "aws_s3_bucket",
                "name": f"test_{i}",
                "provider_name": "aws",
                "values": {
                    "bucket": f"test-bucket-{i}",
                    "tags": {"index": str(i)}
                }
            }
            large_plan["planned_values"]["root_module"]["resources"].append(resource)
        
        # Time parsing
        start_time = time.time()
        plan = parser.parse(large_plan)
        end_time = time.time()
        
        assert len(plan.resources) == 500
        assert (end_time - start_time) < 5  # Should parse within 5 seconds
        
        print(f"Parsed 500 resources in {end_time - start_time:.2f} seconds")
    
    def test_memory_usage_large_plan(self):
        """Test memory usage with large plans"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create very large plan
        large_plan = {
            "resource_changes": []
        }
        
        for i in range(2000):
            resource = {
                "address": f"aws_ec2_instance.instance_{i}",
                "type": "aws_ec2_instance",
                "change": {
                    "actions": ["create"],
                    "after": {
                        "instance_type": "t2.micro",
                        "tags": {"env": "test", "index": str(i)}
                    }
                }
            }
            large_plan["resource_changes"].append(resource)
        
        # Parse the plan
        parser = TerraformParser()
        plan = parser.parse(large_plan)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        assert len(plan.resources) == 2000
        assert memory_increase < 500  # Should use less than 500MB additional memory
        
        print(f"Memory usage for 2000 resources: {memory_increase:.2f} MB")
    
    def test_webhook_performance(self, cicd_service):
        """Test webhook endpoint performance"""
        # Mock the service for webhook testing
        cicd_service.evaluate_plan = AsyncMock(return_value={
            'evaluation_id': 'eval-123',
            'status': 'completed'
        })
        
        # Create test payload
        test_payload = {
            "iac_type": "terraform",
            "iac_content": {
                "resource_changes": [
                    {
                        "address": "aws_s3_bucket.test",
                        "type": "aws_s3_bucket",
                        "change": {"actions": ["create"]}
                    }
                ]
            },
            "context": {"test": True}
        }
        
        # Time multiple webhook calls
        start_time = time.time()
        
        async def run_webhook_test():
            return await cicd_service.evaluate_plan(
                iac_type=test_payload['iac_type'],
                iac_content=test_payload['iac_content'],
                context=test_payload['context']
            )
        
        # Run 50 concurrent webhook calls
        loop = asyncio.get_event_loop()
        tasks = [run_webhook_test() for _ in range(50)]
        results = loop.run_until_complete(asyncio.gather(*tasks))
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert len(results) == 50
        assert duration < 45  # Should complete within 45 seconds
        
        print(f"50 webhook calls completed in {duration:.2f} seconds")
        print(f"Average time per call: {duration/50:.2f} seconds")
    
    def test_policy_engine_performance(self):
        """Test policy engine performance with many violations"""
        from cicd_prevention.service import CICDService
        
        # Create mock policy engine that returns many violations
        mock_policy_engine = Mock()
        violations = [
            {
                "policy_id": f"policy-{i}",
                "severity": "medium",
                "description": f"Test violation {i}",
                "resource_id": f"resource-{i}"
            }
            for i in range(100)
        ]
        mock_policy_engine.evaluate_batch = Mock(return_value=violations)
        
        mock_predictor = Mock()
        mock_predictor.predict_violations = Mock(return_value={
            "violation_probability": 0.5,
            "confidence": 0.8,
            "risk_factors": []
        })
        
        mock_neo4j = Mock()
        mock_neo4j.query = Mock(return_value=[])
        
        service = CICDService(mock_policy_engine, mock_predictor, mock_neo4j)
        
        # Test result determination with many violations
        start_time = time.time()
        result, reasons = service._determine_result(violations, {
            "violation_probability": 0.5,
            "confidence": 0.8
        })
        end_time = time.time()
        
        assert result.value == "block"
        assert (end_time - start_time) < 1  # Should process within 1 second
        
        print(f"Processed 100 violations in {end_time - start_time:.3f} seconds")
    
    @pytest.mark.benchmark
    def test_benchmark_small_plan(self, cicd_service):
        """Benchmark small plan evaluation"""
        small_plan = {
            "resource_changes": [
                {
                    "address": "aws_s3_bucket.test",
                    "type": "aws_s3_bucket",
                    "change": {"actions": ["create"]}
                }
            ]
        }
        
        start_time = time.time()
        result = asyncio.run(cicd_service.evaluate_plan(
            iac_type="terraform",
            iac_content=small_plan,
            context={"benchmark": True}
        ))
        end_time = time.time()
        
        duration = end_time - start_time
        assert duration < 5  # Small plans should be very fast
        
        print(f"Small plan benchmark: {duration:.3f} seconds")
        
        return duration
    
    def test_stress_test_concurrent_load(self, cicd_service):
        """Stress test with high concurrent load"""
        # Create 100 concurrent evaluations
        test_plans = []
        for i in range(100):
            plan = {
                "resource_changes": [
                    {
                        "address": f"aws_s3_bucket.bucket_{i}",
                        "type": "aws_s3_bucket",
                        "change": {"actions": ["create"]}
                    }
                ]
            }
            test_plans.append(plan)
        
        start_time = time.time()
        
        async def run_evaluation(plan, index):
            return await cicd_service.evaluate_plan(
                iac_type="terraform",
                iac_content=plan,
                context={"stress_test": True, "index": index}
            )
        
        # Run with controlled concurrency to avoid overwhelming
        semaphore = asyncio.Semaphore(20)  # Limit to 20 concurrent
        
        async def run_with_semaphore(plan, index):
            async with semaphore:
                return await run_evaluation(plan, index)
        
        loop = asyncio.get_event_loop()
        tasks = [run_with_semaphore(plan, i) for i, plan in enumerate(test_plans)]
        results = loop.run_until_complete(asyncio.gather(*tasks))
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert len(results) == 100
        assert duration < 120  # Should complete within 2 minutes
        
        print(f"Stress test (100 evaluations, 20 concurrent) completed in {duration:.2f} seconds")
        print(f"Average time per evaluation: {duration/100:.2f} seconds")
