import pytest
import yaml
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import concurrent.futures
import time
from typing import Dict, List, Any

from policy_engine.engine import PolicyEngine
from policy_engine.schemas.policy import Policy, Severity, ActionType, EnforcementMode
from policy_engine.services.event_processor import EventProcessor, EventPriority
from policy_engine.services.scheduled_evaluator import ScheduledEvaluator, EvaluationType


class TestPolicyEngine:
    """Test suite for core policy engine functionality"""
    
    @pytest.fixture
    def mock_neo4j_driver(self):
        """Mock Neo4j driver for testing"""
        driver = Mock()
        session = Mock()
        driver.session.return_value = session
        return driver
    
    @pytest.fixture
    def mock_cloud_clients(self):
        """Mock cloud client configurations"""
        return {
            'aws': {
                'eventbridge': Mock(),
                's3': Mock(),
                'ec2': Mock()
            },
            'azure': {
                'policy_client': Mock()
            },
            'gcp': {
                'cloud_resource_manager': Mock()
            }
        }
    
    @pytest.fixture
    def policy_engine(self, mock_neo4j_driver, mock_cloud_clients):
        """Create policy engine instance for testing"""
        return PolicyEngine(mock_neo4j_driver, mock_cloud_clients)
    
    def test_load_valid_policy(self, policy_engine):
        """Test loading a valid policy from YAML"""
        policy_yaml = """
        policy:
          name: test-policy
          description: Test policy for unit testing
          version: "1.0"
          severity: medium
          resources:
            cloud: aws
            resource_types: ["aws:s3:bucket"]
          condition:
            all:
              - field:
                  field: "acl.public"
                  operator: "eq"
                  value: true
          enforcement:
            runtime:
              mode: post-event
          actions:
            - type: notify
              parameters:
                channels:
                  - type: slack
                    target: "#test-channel"
        """
        
        policy = policy_engine.load_policy(policy_yaml)
        
        assert policy.name == "test-policy"
        assert policy.description == "Test policy for unit testing"
        assert policy.version == "1.0"
        assert policy.severity == Severity.MEDIUM
        assert policy.enabled == True
        assert len(policy.actions) == 1
        assert policy.actions[0].type == ActionType.NOTIFY
        assert policy in policy_engine.policies.values()
    
    def test_load_invalid_policy(self, policy_engine):
        """Test loading an invalid policy raises appropriate error"""
        invalid_policy_yaml = """
        policy:
          name: ""
          resources:
            cloud: invalid-cloud
        """
        
        with pytest.raises(Exception):
            policy_engine.load_policy(invalid_policy_yaml)
    
    def test_policy_applicability_filtering(self, policy_engine):
        """Test policy applicability filtering"""
        # Load AWS-specific policy
        policy_yaml = """
        policy:
          name: aws-only-policy
          resources:
            cloud: aws
            resource_types: ["aws:s3:bucket"]
          condition:
            field:
              field: "acl.public"
              operator: "eq"
              value: true
        """
        policy_engine.load_policy(policy_yaml)
        
        # Test AWS event - should apply
        aws_event = {
            "cloud": "aws",
            "resource": {
                "type": "aws:s3:bucket",
                "id": "arn:aws:s3:::test-bucket"
            }
        }
        
        applicable_policies = policy_engine._get_applicable_policies(aws_event)
        assert len(applicable_policies) == 1
        
        # Test Azure event - should not apply
        azure_event = {
            "cloud": "azure",
            "resource": {
                "type": "azure:blob:container",
                "id": "/subscriptions/test/providers/Microsoft.Storage/storageAccounts/test/containers/test"
            }
        }
        
        applicable_policies = policy_engine._get_applicable_policies(azure_event)
        assert len(applicable_policies) == 0
    
    def test_evaluate_public_bucket_violation(self, policy_engine):
        """Test evaluation of public bucket policy violation"""
        policy_yaml = """
        policy:
          name: no-public-buckets
          severity: high
          resources:
            cloud: aws
            resource_types: ["aws:s3:bucket"]
          condition:
            all:
              - field:
                  field: "acl.public"
                  operator: "eq"
                  value: true
          actions:
            - type: notify
              parameters:
                channels:
                  - type: slack
                    target: "#security-alerts"
        """
        policy_engine.load_policy(policy_yaml)
        
        # Create violating event
        violating_event = {
            "cloud": "aws",
            "resource": {
                "type": "aws:s3:bucket",
                "id": "arn:aws:s3:::public-bucket",
                "acl": {"public": True},
                "tags": {"environment": "prod"}
            },
            "operation": "PutBucketAcl",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        violations = policy_engine.evaluate_event(violating_event)
        
        assert len(violations) == 1
        assert violations[0]['policy_name'] == "no-public-buckets"
        assert violations[0]['severity'] == 'high'
        assert violations[0]['resource']['id'] == "arn:aws:s3:::public-bucket"
    
    def test_evaluate_compliant_event(self, policy_engine):
        """Test evaluation of compliant event (no violations)"""
        policy_yaml = """
        policy:
          name: no-public-buckets
          resources:
            cloud: aws
            resource_types: ["aws:s3:bucket"]
          condition:
            all:
              - field:
                  field: "acl.public"
                  operator: "eq"
                  value: true
        """
        policy_engine.load_policy(policy_yaml)
        
        # Create compliant event
        compliant_event = {
            "cloud": "aws",
            "resource": {
                "type": "aws:s3:bucket",
                "id": "arn:aws:s3:::private-bucket",
                "acl": {"public": False},
                "tags": {"environment": "prod"}
            },
            "operation": "PutObject",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        violations = policy_engine.evaluate_event(compliant_event)
        
        assert len(violations) == 0
    
    def test_wildcard_resource_type_matching(self, policy_engine):
        """Test wildcard resource type matching"""
        policy_yaml = """
        policy:
          name: all-databases-policy
          resources:
            cloud: all
            resource_types: ["*:database:*", "*:rds:*", "*:sql:*"]
          condition:
            field:
              field: "tags.backup_enabled"
              operator: "eq"
              value: false
        """
        policy_engine.load_policy(policy_yaml)
        
        # Test matching resource types
        test_events = [
            {
                "cloud": "aws",
                "resource": {"type": "aws:rds:dbinstance", "id": "test-db-1"}
            },
            {
                "cloud": "azure", 
                "resource": {"type": "azure:sql:server", "id": "test-sql-1"}
            },
            {
                "cloud": "gcp",
                "resource": {"type": "gcp:database:instance", "id": "test-db-2"}
            },
            {
                "cloud": "aws",
                "resource": {"type": "aws:ec2:instance", "id": "test-vm"}  # Should not match
            }
        ]
        
        matching_events = [e for e in test_events 
                          if policy_engine._matches_resource_type(
                              e['resource']['type'], 
                              ["*:database:*", "*:rds:*", "*:sql:*"]
                          )]
        
        assert len(matching_events) == 3
        assert matching_events[0]['resource']['type'] == "aws:rds:dbinstance"
        assert matching_events[1]['resource']['type'] == "azure:sql:server"
        assert matching_events[2]['resource']['type'] == "gcp:database:instance"
    
    def test_logical_conditions(self, policy_engine):
        """Test complex logical conditions (AND/OR/NOT)"""
        policy_yaml = """
        policy:
          name: complex-condition-policy
          resources:
            cloud: aws
            resource_types: ["aws:s3:bucket"]
          condition:
            all:
              - field:
                  field: "tags.environment"
                  operator: "eq"
                  value: "prod"
              - any:
                  - field:
                      field: "acl.public"
                      operator: "eq"
                      value: true
                  - field:
                      field: "acl.public_write"
                      operator: "eq"
                      value: true
              - not:
                  field:
                    field: "tags.exclude_from_policy"
                    operator: "exists"
                    value: true
        """
        policy_engine.load_policy(policy_yaml)
        
        # Violating event (prod + public + not excluded)
        violating_event = {
            "cloud": "aws",
            "resource": {
                "type": "aws:s3:bucket",
                "id": "arn:aws:s3:::prod-public-bucket",
                "acl": {"public": True},
                "tags": {"environment": "prod"}
            }
        }
        
        violations = policy_engine.evaluate_event(violating_event)
        assert len(violations) == 1
        
        # Compliant event (not prod)
        compliant_event_1 = {
            "cloud": "aws",
            "resource": {
                "type": "aws:s3:bucket",
                "id": "arn:aws:s3:::dev-public-bucket",
                "acl": {"public": True},
                "tags": {"environment": "dev"}
            }
        }
        
        violations = policy_engine.evaluate_event(compliant_event_1)
        assert len(violations) == 0
        
        # Compliant event (excluded)
        compliant_event_2 = {
            "cloud": "aws",
            "resource": {
                "type": "aws:s3:bucket",
                "id": "arn:aws:s3:::prod-excluded-bucket",
                "acl": {"public": True},
                "tags": {"environment": "prod", "exclude_from_policy": "true"}
            }
        }
        
        violations = policy_engine.evaluate_event(compliant_event_2)
        assert len(violations) == 0


class TestGraphConditions:
    """Test suite for graph-based policy conditions"""
    
    @pytest.fixture
    def mock_neo4j_driver(self):
        """Mock Neo4j driver for graph testing"""
        driver = Mock()
        session = Mock()
        result = Mock()
        record = Mock()
        
        # Mock successful graph query result
        record.return_value = {"exists": True}
        result.single.return_value = record
        session.run.return_value = result
        driver.session.return_value = session
        
        return driver
    
    @pytest.fixture
    def policy_engine(self, mock_neo4j_driver):
        """Create policy engine with mocked Neo4j"""
        mock_cloud_clients = {}
        return PolicyEngine(mock_neo4j_driver, mock_cloud_clients)
    
    def test_graph_condition_evaluation(self, policy_engine, mock_neo4j_driver):
        """Test graph-based condition evaluation"""
        policy_yaml = """
        policy:
          name: internet-to-database
          severity: high
          resources:
            cloud: aws
            resource_types: ["aws:rds:*"]
          condition:
            graph:
              path:
                from: internet
                to: resource
                via: ["load_balancer", "security_group"]
              where:
                all:
                  - field:
                      field: "resource.tags.env"
                      operator: "eq"
                      value: "prod"
                  - field:
                      field: "resource.type"
                      operator: "contains"
                      value: "database"
              max_depth: 5
          actions:
            - type: notify
              parameters:
                channels:
                  - type: email
                    target: "security@company.com"
        """
        policy_engine.load_policy(policy_yaml)
        
        # Test event
        event = {
            "cloud": "aws",
            "resource": {
                "type": "aws:rds:dbinstance",
                "id": "arn:aws:rds:us-east-1:123456789012:db:prod-db",
                "tags": {"env": "prod"}
            },
            "operation": "ModifyDBInstance"
        }
        
        violations = policy_engine.evaluate_event(event)
        
        assert len(violations) == 1
        assert violations[0]['policy_name'] == "internet-to-database"
        
        # Verify Neo4j query was called
        mock_neo4j_driver.session.return_value.run.assert_called()
        
        # Check query structure
        call_args = mock_neo4j_driver.session.return_value.run.call_args
        query = call_args[0][0]
        assert "MATCH" in query
        assert "WHERE" in query
        assert "count(*) > 0" in query
    
    def test_graph_condition_no_path(self, policy_engine, mock_neo4j_driver):
        """Test graph condition when no path exists"""
        # Mock no path found
        mock_neo4j_driver.session.return_value.run.return_value.single.return_value = {"exists": False}
        
        policy_yaml = """
        policy:
          name: isolated-database
          resources:
            cloud: aws
            resource_types: ["aws:rds:*"]
          condition:
            graph:
              path:
                from: internet
                to: resource
              max_depth: 3
        """
        policy_engine.load_policy(policy_yaml)
        
        event = {
            "cloud": "aws",
            "resource": {
                "type": "aws:rds:dbinstance",
                "id": "arn:aws:rds:us-east-1:123456789012:db:isolated-db"
            }
        }
        
        violations = policy_engine.evaluate_event(event)
        
        assert len(violations) == 0  # No violation when no path exists


class TestPolicyPerformance:
    """Performance tests for policy engine"""
    
    @pytest.fixture
    def policy_engine(self):
        """Create policy engine for performance testing"""
        mock_driver = Mock()
        mock_driver.session.return_value.__enter__.return_value = Mock()
        mock_cloud_clients = {}
        return PolicyEngine(mock_driver, mock_cloud_clients)
    
    def test_concurrent_evaluation(self, policy_engine):
        """Test concurrent policy evaluation performance"""
        # Load multiple policies
        for i in range(10):
            policy_yaml = f"""
            policy:
              name: policy-{i}
              severity: medium
              resources:
                cloud: aws
                resource_types: ["aws:s3:bucket"]
              condition:
                all:
                  - field:
                      field: "tags.cost_center"
                      operator: "eq"
                      value: "IT"
                  - field:
                      field: "acl.public"
                      operator: "eq"
                      value: false
            """
            policy_engine.load_policy(policy_yaml)
        
        # Create test events
        events = []
        for i in range(100):
            event = {
                "cloud": "aws",
                "resource": {
                    "type": "aws:s3:bucket",
                    "id": f"arn:aws:s3:::bucket-{i}",
                    "tags": {"cost_center": "IT"},
                    "acl": {"public": False}
                },
                "operation": "PutObject",
                "timestamp": datetime.utcnow().isoformat()
            }
            events.append(event)
        
        # Measure performance
        start_time = time.time()
        
        # Evaluate concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(policy_engine.evaluate_event, events))
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verify results
        assert len(results) == 100
        total_violations = sum(len(r) for r in results)
        assert total_violations == 0  # All events should be compliant
        
        # Performance assertion (should complete within reasonable time)
        assert duration < 10.0  # 100 events with 10 policies should complete in < 10 seconds
        print(f"Processed 100 events with 10 policies in {duration:.2f} seconds")
    
    def test_large_policy_set_performance(self, policy_engine):
        """Test performance with large number of policies"""
        # Load many policies
        policy_count = 50
        for i in range(policy_count):
            policy_yaml = f"""
            policy:
              name: policy-{i}
              resources:
                cloud: aws
                resource_types: ["aws:ec2:instance"]
              condition:
                field:
                  field: "tags.environment"
                  operator: "eq"
                  value: "prod"
            """
            policy_engine.load_policy(policy_yaml)
        
        # Test single event evaluation
        event = {
            "cloud": "aws",
            "resource": {
                "type": "aws:ec2:instance",
                "id": "arn:aws:ec2:us-east-1:123456789012:instance/test-instance",
                "tags": {"environment": "prod"}
            },
            "operation": "StartInstances"
        }
        
        # Measure performance
        start_time = time.time()
        violations = policy_engine.evaluate_event(event)
        end_time = time.time()
        duration = end_time - start_time
        
        # Should trigger all 50 policies
        assert len(violations) == policy_count
        
        # Performance assertion
        assert duration < 5.0  # Single event with 50 policies should complete in < 5 seconds
        print(f"Evaluated 1 event against {policy_count} policies in {duration:.3f} seconds")


class TestEventProcessor:
    """Test suite for event processing service"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        redis_client = Mock()
        redis_client.decode_responses.return_value = True
        return redis_client
    
    @pytest.fixture
    def mock_policy_engine(self):
        """Mock policy engine"""
        engine = Mock()
        engine.evaluate_event.return_value = []
        return engine
    
    @pytest.fixture
    def event_processor(self, mock_policy_engine, mock_redis):
        """Create event processor for testing"""
        return EventProcessor(mock_policy_engine, "redis://localhost:6379")
    
    @patch('redis.Redis.from_url')
    def test_submit_event(self, mock_redis_from_url, event_processor):
        """Test event submission"""
        mock_redis_from_url.return_value = event_processor.redis
        
        event = {
            "cloud": "aws",
            "resource": {"type": "aws:s3:bucket", "id": "test-bucket"},
            "operation": "PutObject"
        }
        
        event_id = event_processor.submit_event(event, EventPriority.HIGH)
        
        assert event_id is not None
        assert 'id' in event
        assert 'submitted_at' in event
        
        # Verify Redis was called
        event_processor.redis.lpush.assert_called()
    
    @patch('redis.Redis.from_url')
    @patch('asyncio.get_event_loop')
    def test_get_violation_status(self, mock_loop, mock_redis_from_url, event_processor):
        """Test getting violation status"""
        mock_redis_from_url.return_value = event_processor.redis
        
        # Mock Redis responses
        event_processor.redis.get.return_value = json.dumps({
            "status": "completed",
            "violation_count": 2,
            "processing_time": 0.5
        })
        event_processor.redis.keys.return_value = ["skysentinel:violation:test-event-123"]
        
        # Mock async loop
        loop = Mock()
        mock_loop.return_value = loop
        
        # Test
        status = event_processor.get_violation_status("test-event-123")
        
        assert status["event_id"] == "test-event-123"
        assert status["status"] == "completed"
        assert status["violation_count"] == 2


class TestScheduledEvaluator:
    """Test suite for scheduled evaluation service"""
    
    @pytest.fixture
    def mock_policy_engine(self):
        """Mock policy engine"""
        engine = Mock()
        engine.policies = {}
        engine.evaluate_event.return_value = []
        return engine
    
    @pytest.fixture
    def mock_neo4j_driver(self):
        """Mock Neo4j driver"""
        driver = Mock()
        session = Mock()
        result = Mock()
        result.single.return_value = {"count": 100}
        session.run.return_value = result
        driver.session.return_value = session
        return driver
    
    @pytest.fixture
    def scheduled_evaluator(self, mock_policy_engine, mock_neo4j_driver):
        """Create scheduled evaluator for testing"""
        return ScheduledEvaluator(mock_policy_engine, mock_neo4j_driver)
    
    def test_evaluation_configuration(self, scheduled_evaluator):
        """Test evaluation schedule configuration"""
        # Test default configuration
        config = scheduled_evaluator.schedule_config
        assert config['hourly_evaluation'] is True
        assert config['daily_drift_check'] is True
        assert config['weekly_compliance'] is True
        assert config['monthly_report'] is True
        
        # Test configuration update
        new_config = {
            'hourly_evaluation': False,
            'daily_drift_check': True
        }
        scheduled_evaluator.configure_schedule(new_config)
        
        assert scheduled_evaluator.schedule_config['hourly_evaluation'] is False
        assert scheduled_evaluator.schedule_config['daily_drift_check'] is True
    
    def test_resource_counting(self, scheduled_evaluator, mock_neo4j_driver):
        """Test resource counting for policies"""
        # Create test policy
        policy = Mock()
        policy.resources.cloud = 'aws'
        policy.resources.resource_types = ['aws:s3:bucket']
        policy.id = 'test-policy'
        
        count = scheduled_evaluator._count_resources_for_policy(policy)
        
        assert count == 100
        mock_neo4j_driver.session.return_value.run.assert_called()
    
    def test_compliance_calculation(self, scheduled_evaluator, mock_neo4j_driver):
        """Test compliance calculation"""
        # Mock compliant count
        mock_neo4j_driver.session.return_value.run.return_value.single.return_value = {"count": 80}
        
        policy = Mock()
        policy.id = 'test-policy'
        
        compliant_count = scheduled_evaluator._count_compliant_resources(policy)
        
        assert compliant_count == 80


class TestCloudIntegration:
    """Test suite for cloud provider integrations"""
    
    @pytest.fixture
    def mock_azure_credentials(self):
        """Mock Azure credentials"""
        return {
            'tenant_id': 'test-tenant-id',
            'client_id': 'test-client-id',
            'client_secret': 'test-client-secret'
        }
    
    def test_azure_integration_initialization(self, mock_azure_credentials):
        """Test Azure integration initialization"""
        with patch('policy_engine.cloud.azure_integration.DefaultAzureCredential'), \
             patch('policy_engine.cloud.azure_integration.PolicyClient') as mock_policy_client:
            
            from policy_engine.cloud.azure_integration import AzureIntegration
            
            integration = AzureIntegration(
                subscription_id="test-subscription-id",
                credential_config=mock_azure_credentials
            )
            
            assert integration.subscription_id == "test-subscription-id"
            assert integration.credential is not None
            mock_policy_client.assert_called()
    
    def test_azure_policy_rule_generation(self):
        """Test Azure Policy rule generation"""
        with patch('policy_engine.cloud.azure_integration.DefaultAzureCredential'), \
             patch('policy_engine.cloud.azure_integration.PolicyClient'):
            
            from policy_engine.cloud.azure_integration import AzureIntegration
            from policy_engine.schemas.policy import Policy, ResourceSelector, Condition, ConditionField, ConditionOperator
            
            integration = AzureIntegration("test-subscription-id")
            
            # Create test policy
            policy = Policy(
                name="test-azure-policy",
                resources=ResourceSelector(
                    resource_types=["azure:blob:container"],
                    tags={"environment": "prod"}
                ),
                condition=Condition(
                    all=[Condition(
                        field=ConditionField(
                            field="tags.environment",
                            operator=ConditionOperator.EQUALS,
                            value="prod"
                        )
                    )]
                )
            )
            
            rule = integration.generate_policy_rule(policy)
            
            assert "if" in rule
            assert "then" in rule
            assert rule["then"]["effect"] in ["audit", "deny"]
            assert "allOf" in rule["if"]


# Integration tests
class TestEndToEndIntegration:
    """End-to-end integration tests"""
    
    @pytest.fixture
    def full_system(self):
        """Set up complete system for integration testing"""
        # This would set up real connections or comprehensive mocks
        # For now, return mock objects
        mock_driver = Mock()
        mock_cloud_clients = {}
        
        engine = PolicyEngine(mock_driver, mock_cloud_clients)
        
        with patch('redis.Redis.from_url'):
            processor = EventProcessor(engine, "redis://localhost:6379")
        
        evaluator = ScheduledEvaluator(engine, mock_driver)
        
        return {
            'engine': engine,
            'processor': processor,
            'evaluator': evaluator
        }
    
    def test_policy_to_violation_flow(self, full_system):
        """Test complete flow from policy loading to violation detection"""
        engine = full_system['engine']
        
        # Load policy
        policy_yaml = """
        policy:
          name: integration-test-policy
          severity: high
          resources:
            cloud: aws
            resource_types: ["aws:s3:bucket"]
          condition:
            all:
              - field:
                  field: "acl.public"
                  operator: "eq"
                  value: true
          actions:
            - type: notify
              parameters:
                channels:
                  - type: slack
                    target: "#test"
        """
        
        policy = engine.load_policy(policy_yaml)
        assert policy in engine.policies.values()
        
        # Create violating event
        event = {
            "cloud": "aws",
            "resource": {
                "type": "aws:s3:bucket",
                "id": "arn:aws:s3:::test-bucket",
                "acl": {"public": True}
            },
            "operation": "PutBucketAcl"
        }
        
        # Evaluate
        violations = engine.evaluate_event(event)
        
        # Verify violation
        assert len(violations) == 1
        assert violations[0]['policy_name'] == "integration-test-policy"
        assert violations[0]['severity'] == 'high'
        assert len(violations[0]['remediation_actions']) == 1


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
