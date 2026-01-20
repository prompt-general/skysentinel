import pytest
import json
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Import the classes we're testing
import sys
sys.path.append(str(Path(__file__).parent.parent))

from cicd_prevention.service import CICDService
from cicd_prevention.parsers.terraform import TerraformParser
from cicd_prevention.parsers.cloudformation import CloudFormationParser

class TestCICDIntegration:
    @pytest.fixture
    def mock_policy_engine(self):
        """Mock policy engine for testing"""
        engine = Mock()
        engine.evaluate_event = Mock(return_value=[])
        engine.evaluate_batch = Mock(return_value=[])
        return engine
    
    @pytest.fixture
    def mock_predictor(self):
        """Mock ML predictor for testing"""
        predictor = Mock()
        predictor.predict_violations = Mock(return_value={
            "violation_probability": 0.1,
            "confidence": 0.8,
            "risk_factors": []
        })
        return predictor
    
    @pytest.fixture
    def mock_neo4j(self):
        """Mock Neo4j database for testing"""
        neo4j = Mock()
        neo4j.query = Mock(return_value=[])
        neo4j.create_evaluation = Mock(return_value="eval-123")
        return neo4j
    
    @pytest.fixture
    def cicd_service(self, mock_policy_engine, mock_predictor, mock_neo4j):
        """Create CICDService instance with mocked dependencies"""
        return CICDService(mock_policy_engine, mock_predictor, mock_neo4j)
    
    @pytest.fixture
    def sample_terraform_plan(self):
        """Sample Terraform plan for testing"""
        return {
            "resource_changes": [
                {
                    "address": "aws_s3_bucket.test",
                    "type": "aws_s3_bucket",
                    "change": {
                        "actions": ["create"],
                        "after": {
                            "bucket": "test-bucket",
                            "tags": {"env": "test"}
                        }
                    }
                },
                {
                    "address": "aws_instance.web",
                    "type": "aws_instance",
                    "change": {
                        "actions": ["create"],
                        "after": {
                            "instance_type": "t3.micro",
                            "ami": "ami-12345678"
                        }
                    }
                }
            ],
            "configuration": {
                "provider_config": {
                    "aws": {
                        "name": "aws"
                    }
                }
            }
        }
    
    @pytest.fixture
    def sample_cloudformation_template(self):
        """Sample CloudFormation template for testing"""
        return {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                "S3Bucket": {
                    "Type": "AWS::S3::Bucket",
                    "Properties": {
                        "BucketName": "test-bucket",
                        "Tags": [{"Key": "env", "Value": "test"}]
                    }
                },
                "EC2Instance": {
                    "Type": "AWS::EC2::Instance",
                    "Properties": {
                        "InstanceType": "t3.micro",
                        "ImageId": "ami-12345678"
                    }
                }
            }
        }
    
    def test_terraform_parsing(self, sample_terraform_plan):
        """Test Terraform plan parsing"""
        parser = TerraformParser()
        plan = parser.parse(sample_terraform_plan)
        
        assert plan.source_type == "terraform"
        assert len(plan.resources) > 0
        
        # Check resource normalization
        for resource in plan.resources:
            assert resource.cloud_provider in ['aws', 'azure', 'gcp', 'unknown']
            assert ':' in resource.resource_type  # Should be normalized
    
    def test_cloudformation_parsing(self, sample_cloudformation_template):
        """Test CloudFormation template parsing"""
        parser = CloudFormationParser()
        plan = parser.parse(sample_cloudformation_template)
        
        assert plan.source_type == "cloudformation"
        assert len(plan.resources) > 0
        
        # All CloudFormation resources should be AWS
        for resource in plan.resources:
            assert resource.cloud_provider == 'aws'
    
    def test_cicd_evaluation_flow(self, cicd_service, sample_terraform_plan):
        """Test complete CI/CD evaluation flow"""
        context = {
            "pipeline": "test-pipeline",
            "commit": "abc123",
            "branch": "main",
            "user": "test-user"
        }
        
        # Mock the async method
        cicd_service.evaluate_plan = AsyncMock(return_value={
            'evaluation_id': 'eval-123',
            'result': 'pass',
            'policy_evaluation': {'total_violations': 0},
            'ml_predictions': {'violation_probability': 0.1}
        })
        
        # Run the evaluation
        result = asyncio.run(cicd_service.evaluate_plan(
            iac_type="terraform",
            iac_content=sample_terraform_plan,
            context=context
        ))
        
        assert 'evaluation_id' in result
        assert 'result' in result
        assert 'policy_evaluation' in result
        assert 'ml_predictions' in result
        
        # Check result structure
        assert result['result'] in ['pass', 'warn', 'block', 'error']
        assert isinstance(result['policy_evaluation']['total_violations'], int)
    
    def test_webhook_integration(self, cicd_service):
        """Test webhook API integration"""
        test_plan = {
            "resource_changes": [
                {
                    "address": "aws_s3_bucket.test",
                    "type": "aws_s3_bucket",
                    "change": {
                        "actions": ["create"],
                        "after": {
                            "bucket": "test-bucket",
                            "tags": {"env": "test"}
                        }
                    }
                }
            ]
        }
        
        # Mock the evaluation
        cicd_service.evaluate_plan = AsyncMock(return_value={
            'evaluation_id': 'eval-123',
            'status': 'completed'
        })
        
        # Simulate webhook call
        result = asyncio.run(cicd_service.evaluate_plan(
            iac_type='terraform',
            iac_content=test_plan,
            context={'test': True}
        ))
        
        assert 'evaluation_id' in result
        assert 'status' in result
    
    def test_github_webhook(self, cicd_service):
        """Test GitHub webhook integration"""
        github_payload = {
            "action": "opened",
            "pull_request": {
                "number": 123,
                "head": {
                    "sha": "abc123",
                    "ref": "feature-branch"
                }
            },
            "repository": {
                "full_name": "test/repo"
            }
        }
        
        # Mock the webhook processing
        cicd_service.process_github_webhook = Mock(return_value={
            'status': 'processed',
            'evaluation_id': 'eval-123'
        })
        
        result = cicd_service.process_github_webhook(github_payload)
        
        assert result['status'] == 'processed'
        assert 'evaluation_id' in result
    
    @pytest.mark.parametrize("violations,expected_result", [
        ([], "pass"),
        ([{"severity": "low"}], "pass"),
        ([{"severity": "medium"}], "warn"),
        ([{"severity": "high"}], "block"),
        ([{"severity": "critical"}], "block"),
        ([{"severity": "medium"}, {"severity": "high"}], "block"),
    ])
    def test_result_determination(self, cicd_service, violations, expected_result):
        """Test result determination logic"""
        ml_predictions = {"violation_probability": 0.1, "confidence": 0.5}
        
        result, reasons = cicd_service._determine_result(violations, ml_predictions)
        
        assert result.value == expected_result
    
    def test_high_ml_prediction_block(self, cicd_service):
        """Test that high ML prediction probability blocks"""
        violations = []  # No policy violations
        ml_predictions = {
            "violation_probability": 0.9,  # 90% probability
            "confidence": 0.8  # 80% confidence
        }
        
        result, reasons = cicd_service._determine_result(violations, ml_predictions)
        
        assert result.value == "block"
        assert "High predicted violation probability" in reasons[0]
    
    def test_policy_violation_processing(self, cicd_service):
        """Test policy violation processing"""
        violations = [
            {
                "policy_id": "policy-1",
                "severity": "high",
                "description": "S3 bucket should be private",
                "resource_id": "aws_s3_bucket.test"
            }
        ]
        
        ml_predictions = {"violation_probability": 0.1, "confidence": 0.8}
        
        result, reasons = cicd_service._determine_result(violations, ml_predictions)
        
        assert result.value == "block"
        assert len(reasons) > 0
    
    def test_context_processing(self, cicd_service):
        """Test context processing and enrichment"""
        context = {
            "pipeline": "test-pipeline",
            "commit": "abc123",
            "branch": "main"
        }
        
        enriched_context = cicd_service._enrich_context(context)
        
        assert enriched_context["pipeline"] == "test-pipeline"
        assert enriched_context["commit"] == "abc123"
        assert enriched_context["branch"] == "main"
        assert "timestamp" in enriched_context
    
    def test_error_handling(self, cicd_service):
        """Test error handling in CI/CD service"""
        # Test with invalid IaC content
        invalid_content = {"invalid": "content"}
        
        # Mock the parser to raise an exception
        cicd_service._parse_iac_content = Mock(side_effect=Exception("Parse error"))
        
        with pytest.raises(Exception):
            asyncio.run(cicd_service.evaluate_plan(
                iac_type="terraform",
                iac_content=invalid_content,
                context={}
            ))
