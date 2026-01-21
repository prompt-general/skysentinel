import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import asyncio
from unittest.mock import Mock, AsyncMock

class TestMLIntegration:
    
    @pytest.fixture
    def mock_neo4j_driver(self):
        """Mock Neo4j driver for testing"""
        driver = Mock()
        session = Mock()
        driver.session.return_value.__enter__.return_value = session
        driver.session.return_value.__exit__.return_value = None
        return driver
    
    @pytest.fixture
    def mock_prediction_engine(self):
        """Mock prediction engine"""
        engine = Mock()
        engine.predict_single = AsyncMock(return_value={
            'violation_probability': 0.75,
            'confidence': 0.8,
            'predicted_violations': ['public_access'],
            'explanation': {'top_features': {'is_public': 0.9}}
        })
        engine.predict_iac = AsyncMock(return_value={
            'violation_probability': 0.6,
            'confidence': 0.7,
            'high_risk_resources': [],
            'warnings': []
        })
        return engine
    
    @pytest.fixture
    def sample_event(self):
        return {
            'cloud': 'aws',
            'operation': 'create_resource',
            'resource': {
                'id': 'resource-123',
                'type': 'aws:s3:bucket',
                'properties': {
                    'bucket': 'test-bucket',
                    'acl': 'public-read'
                },
                'tags': {
                    'env': 'prod',
                    'owner': 'team-a'
                }
            },
            'principal': {
                'type': 'user',
                'id': 'user-123'
            },
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @pytest.fixture
    def sample_iac_plan(self):
        return {
            'resources': [
                {
                    'iac_id': 'aws_s3_bucket.data',
                    'resource_type': 'aws:s3:bucket',
                    'cloud_provider': 'aws',
                    'properties': {
                        'bucket': 'data-bucket',
                        'acl': 'private',
                        'versioning': {'enabled': True}
                    },
                    'tags': {'env': 'prod', 'team': 'data'},
                    'change_type': 'create'
                },
                {
                    'iac_id': 'aws_ec2_instance.web',
                    'resource_type': 'aws:ec2:instance',
                    'cloud_provider': 'aws',
                    'properties': {
                        'instance_type': 't3.medium',
                        'ami': 'ami-12345678'
                    },
                    'tags': {'env': 'prod', 'team': 'web'},
                    'change_type': 'create'
                }
            ]
        }
    
    @pytest.fixture
    def ml_enhanced_policy_engine(self, mock_neo4j_driver, mock_prediction_engine):
        from policy_engine.engine_ml_integrated import MLEnhancedPolicyEngine
        
        # Mock cloud clients
        mock_cloud_clients = {'aws': Mock()}
        
        return MLEnhancedPolicyEngine(mock_neo4j_driver, mock_cloud_clients, mock_prediction_engine)
    
    def test_ml_enhanced_event_evaluation(self, ml_enhanced_policy_engine, sample_event):
        """Test ML-enhanced event evaluation"""
        
        # Mock base engine evaluation
        ml_enhanced_policy_engine.base_engine.evaluate_event = Mock(return_value=[
            {
                'policy_name': 's3-public-access',
                'severity': 'high',
                'description': 'S3 bucket should not be public'
            }
        ])
        
        # Test evaluation
        result = asyncio.run(
            ml_enhanced_policy_engine.evaluate_event_with_ml(sample_event)
        )
        
        # Check result structure
        assert 'action' in result
        assert 'combined_risk_score' in result
        assert 'policy_violations' in result
        assert 'ml_prediction' in result
        assert 'explanation' in result
        assert 'timestamp' in result
        
        # Check action is one of expected values
        assert result['action'] in ['allow', 'warn', 'block']
        
        # Check combined risk score
        assert 0 <= result['combined_risk_score'] <= 1
        
        # Check ML prediction
        ml_pred = result['ml_prediction']
        assert 'violation_probability' in ml_pred
        assert 'confidence' in ml_pred
        assert 0 <= ml_pred['violation_probability'] <= 1
        assert 0 <= ml_pred['confidence'] <= 1
    
    def test_ml_enhanced_iac_evaluation(self, ml_enhanced_policy_engine, sample_iac_plan):
        """Test ML-enhanced IaC evaluation"""
        
        # Mock CICD service evaluation
        mock_cicd_result = {
            'evaluation_id': 'eval-123',
            'result': 'pass',
            'policy_evaluation': {'total_violations': 1},
            'ml_predictions': {},
            'recommendations': []
        }
        
        from cicd_prevention.service import CICDService
        mock_cicd_service = Mock(spec=CICDService)
        mock_cicd_service.evaluate_plan = AsyncMock(return_value=mock_cicd_result)
        
        # Replace the cicd_service creation
        original_import = __import__('cicd_prevention.service', fromlist=['CICDService'])
        original_cicd = original_import.CICDService
        original_import.CICDService = Mock(return_value=mock_cicd_service)
        
        try:
            context = {'iac_type': 'terraform', 'stage': 'pre_deployment'}
            result = asyncio.run(
                ml_enhanced_policy_engine.evaluate_iac_with_ml(sample_iac_plan, context)
            )
            
            # Check result structure
            assert 'ml_predictions' in result
            assert 'recommendations' in result
            assert isinstance(result['recommendations'], list)
            
        finally:
            # Restore original import
            original_import.CICDService = original_cicd
    
    def test_result_combination_logic(self, ml_enhanced_policy_engine):
        """Test result combination logic"""
        
        # Test case 1: High ML risk, no policy violations
        policy_violations = []
        ml_prediction = {'violation_probability': 0.9, 'confidence': 0.8}
        
        result = ml_enhanced_policy_engine._combine_results(policy_violations, ml_prediction)
        
        assert result['action'] == 'block'  # High ML risk should block
        assert result['combined_risk_score'] > 0.8
        
        # Test case 2: Low ML risk, some policy violations
        policy_violations = [
            {'policy_name': 'test-policy', 'severity': 'medium', 'description': 'Test'}
        ]
        ml_prediction = {'violation_probability': 0.2, 'confidence': 0.7}
        
        result = ml_enhanced_policy_engine._combine_results(policy_violations, ml_prediction)
        
        assert result['action'] in ['allow', 'warn']  # Should not block
        assert result['combined_risk_score'] < 0.8
        
        # Test case 3: High ML risk and policy violations
        policy_violations = [
            {'policy_name': 'test-policy', 'severity': 'high', 'description': 'Test'}
        ]
        ml_prediction = {'violation_probability': 0.8, 'confidence': 0.9}
        
        result = ml_enhanced_policy_engine._combine_results(policy_violations, ml_prediction)
        
        assert result['action'] == 'block'  # Should definitely block
        assert result['combined_risk_score'] > 0.8
    
    def test_iac_enhancement_logic(self, ml_enhanced_policy_engine):
        """Test IaC enhancement logic"""
        
        # Test case: ML predicts high risk
        policy_result = {
            'result': 'pass',
            'recommendations': []
        }
        ml_result = {
            'violation_probability': 0.85,
            'high_risk_resources': [
                {
                    'resource_id': 'resource-1',
                    'violation_probability': 0.9,
                    'top_features': {'is_public': 0.95}
                }
            ]
        }
        
        enhanced = ml_enhanced_policy_engine._enhance_with_ml(policy_result, ml_result)
        
        # Should be upgraded to warn due to high ML risk
        assert enhanced['result'] == 'warn'
        assert enhanced['result_reason'] == 'High ML-predicted violation probability'
        
        # Should have ML-based recommendations
        assert len(enhanced['recommendations']) > 0
        ml_recs = [r for r in enhanced['recommendations'] if r['type'] == 'ml_high_risk']
        assert len(ml_recs) > 0
    
    def test_batch_evaluation(self, ml_enhanced_policy_engine):
        """Test batch evaluation"""
        
        # Mock base engine
        ml_enhanced_policy_engine.base_engine.evaluate_event = Mock(side_effect=[
            [{'policy_name': f'policy-{i}', 'severity': 'low', 'description': f'Desc {i}'}]
            for i in range(3)
        ])
        
        # Mock batch ML predictions
        ml_enhanced_policy_engine._get_batch_ml_predictions = AsyncMock(return_value=[
            {'violation_probability': 0.3, 'confidence': 0.7},
            {'violation_probability': 0.6, 'confidence': 0.8},
            {'violation_probability': 0.9, 'confidence': 0.9}
        ])
        
        # Create test events
        events = [
            {
                'resource': {'id': f'resource-{i}', 'type': 'aws:s3:bucket'},
                'operation': 'create'
            }
            for i in range(3)
        ]
        
        results = asyncio.run(
            ml_enhanced_policy_engine.evaluate_batch_with_ml(events)
        )
        
        assert len(results) == 3
        for result in results:
            assert 'action' in result
            assert 'combined_risk_score' in result
            assert 'ml_prediction' in result
    
    def test_ml_weights_management(self, ml_enhanced_policy_engine, mock_neo4j_driver):
        """Test ML weights management"""
        
        # Mock Neo4j response for getting weights
        mock_record = Mock()
        mock_record.__getitem__ = lambda self, key: {
            'policy_weight': 0.3,
            'ml_weight': 0.7,
            'updated_at': '2024-01-01T00:00:00Z'
        }.get(key)
        
        mock_result = Mock()
        mock_result.single.return_value = mock_record
        mock_session = Mock()
        mock_session.run.return_value = mock_result
        mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
        
        # Test getting weights
        weights = asyncio.run(
            ml_enhanced_policy_engine.get_ml_weights('test-tenant')
        )
        
        assert 'policy_weight' in weights
        assert 'ml_weight' in weights
        assert weights['policy_weight'] + weights['ml_weight'] == 1.0
        
        # Test updating weights
        new_weights = {'policy': 0.4, 'ml': 0.6}
        update_result = asyncio.run(
            ml_enhanced_policy_engine.update_ml_weights('test-tenant', new_weights)
        )
        
        assert update_result['status'] == 'success'
        assert update_result['weights'] == new_weights
    
    def test_ml_insights_generation(self, ml_enhanced_policy_engine, mock_neo4j_driver):
        """Test ML insights generation"""
        
        # Mock evaluation data
        mock_evaluations = [
            {
                'result': {
                    'action': 'block',
                    'ml_prediction': {'violation_probability': 0.9, 'confidence': 0.8},
                    'policy_violations': []
                },
                'timestamp': '2024-01-01T00:00:00Z'
            },
            {
                'result': {
                    'action': 'warn',
                    'ml_prediction': {'violation_probability': 0.6, 'confidence': 0.7},
                    'policy_violations': [{'policy_name': 'test'}]
                },
                'timestamp': '2024-01-01T01:00:00Z'
            }
        ]
        
        mock_record = Mock()
        mock_record.__getitem__ = lambda self, key: {
            'result': json.dumps(eval['result']),
            'timestamp': eval['timestamp']
        }.get(key)
        
        mock_result = Mock()
        mock_result.__iter__ = lambda self: iter([mock_record] * len(mock_evaluations))
        mock_result.__len__ = lambda self: len(mock_evaluations)
        
        mock_session = Mock()
        mock_session.run.return_value = mock_result
        mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
        
        # Test insights generation
        insights = asyncio.run(
            ml_enhanced_policy_engine.get_ml_enhanced_insights('test-tenant')
        )
        
        assert 'tenant_id' in insights
        assert 'ml_impact' in insights
        assert 'top_ml_violations' in insights
        assert 'evaluation_count' in insights
        
        # Check ML impact statistics
        ml_impact = insights['ml_impact']
        assert 'total_evaluations' in ml_impact
        assert 'ml_triggered_blocks' in ml_impact
        assert 'ml_enhancement_rate' in ml_impact
    
    def test_error_handling(self, ml_enhanced_policy_engine, sample_event):
        """Test error handling in ML-enhanced evaluation"""
        
        # Mock ML prediction failure
        ml_enhanced_policy_engine._get_ml_prediction = AsyncMock(
            side_effect=Exception("ML prediction failed")
        )
        
        # Mock base engine
        ml_enhanced_policy_engine.base_engine.evaluate_event = Mock(return_value=[
            {'policy_name': 'test-policy', 'severity': 'medium', 'description': 'Test'}
        ])
        
        # Should still return a result even with ML failure
        result = asyncio.run(
            ml_enhanced_policy_engine.evaluate_event_with_ml(sample_event)
        )
        
        assert 'action' in result
        assert 'ml_prediction' in result
        assert 'error' in result['ml_prediction']
        assert result['ml_prediction']['error'] == "ML prediction failed"
    
    def test_explanation_generation(self, ml_enhanced_policy_engine):
        """Test explanation generation"""
        
        policy_violations = [
            {'policy_name': 's3-public-access', 'severity': 'high', 'description': 'Public S3 bucket'}
        ]
        ml_prediction = {
            'violation_probability': 0.8,
            'confidence': 0.7,
            'explanation': {
                'top_features': {'is_public': 0.9, 'no_encryption': 0.7}
            }
        }
        
        result = ml_enhanced_policy_engine._combine_results(policy_violations, ml_prediction)
        explanation = result['explanation']
        
        assert 'policy_violation_count' in explanation
        assert 'ml_violation_probability' in explanation
        assert 'ml_confidence' in explanation
        assert 'combined_risk_score' in explanation
        assert 'ml_explanation' in explanation
        assert 'policy_violations' in explanation
        
        # Check policy violations list
        policy_violations_list = explanation['policy_violations']
        assert len(policy_violations_list) == 1
        assert policy_violations_list[0]['policy'] == 's3-public-access'
        assert policy_violations_list[0]['severity'] == 'high'
