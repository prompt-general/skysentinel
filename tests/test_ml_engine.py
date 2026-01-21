import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import asyncio
from unittest.mock import Mock, AsyncMock

class TestPredictionEngine:
    
    @pytest.fixture
    def mock_neo4j_driver(self):
        """Mock Neo4j driver for testing"""
        driver = Mock()
        session = Mock()
        driver.session.return_value.__enter__.return_value = session
        driver.session.return_value.__exit__.return_value = None
        return driver
    
    @pytest.fixture
    def feature_engineer(self, mock_neo4j_driver):
        from prediction_engine.features import FeatureEngineer
        return FeatureEngineer(mock_neo4j_driver)
    
    @pytest.fixture
    def sample_resource(self):
        return {
            'resource_type': 'aws:s3:bucket',
            'cloud_provider': 'aws',
            'properties': {
                'bucket': 'test-bucket',
                'acl': 'private',
                'versioning': {'enabled': True}
            },
            'tags': {
                'env': 'prod',
                'owner': 'security-team',
                'confidentiality': 'high'
            },
            'change_type': 'create'
        }
    
    @pytest.fixture
    def sample_iac_plan(self):
        return {
            'resources': [
                {
                    'iac_id': 'aws_s3_bucket.test',
                    'resource_type': 'aws:s3:bucket',
                    'cloud_provider': 'aws',
                    'properties': {'bucket': 'test', 'acl': 'public-read'},
                    'tags': {'env': 'prod'},
                    'change_type': 'create'
                },
                {
                    'iac_id': 'aws_ec2_instance.web',
                    'resource_type': 'aws:ec2:instance',
                    'cloud_provider': 'aws',
                    'properties': {'instance_type': 't2.micro'},
                    'tags': {'env': 'prod'},
                    'change_type': 'create'
                }
            ],
            'dependencies': [
                {'from': 'aws_ec2_instance.web', 'to': 'aws_s3_bucket.test'}
            ]
        }
    
    @pytest.fixture
    def sample_training_data(self):
        """Generate sample training data"""
        np.random.seed(42)
        
        features = pd.DataFrame({
            'resource_type': np.random.choice(['aws:s3:bucket', 'aws:ec2:instance', 'aws:iam:role'], 200),
            'cloud_provider': ['aws'] * 200,
            'change_type': np.random.choice(['create', 'update', 'delete'], 200),
            'property_count': np.random.randint(1, 20, 200),
            'tag_count': np.random.randint(0, 10, 200),
            'is_public_resource': np.random.choice([True, False], 200),
            'has_sensitive_tags': np.random.choice([True, False], 200),
            'base_risk_score': np.random.uniform(1, 10, 200),
            'historical_violation_count': np.random.poisson(0.5, 200)
        })
        
        # Create labels based on features (simple rule-based labeling)
        labels = pd.Series([
            1 if (row['is_public_resource'] or 
                  row['has_sensitive_tags'] or 
                  row['base_risk_score'] > 7) and np.random.random() > 0.3
            else 0
            for _, row in features.iterrows()
        ])
        
        return features, labels
    
    @pytest.fixture
    def xgboost_predictor(self):
        from prediction_engine.models.xgboost_predictor import XGBoostPredictor
        return XGBoostPredictor()
    
    @pytest.fixture
    def model_trainer(self, mock_neo4j_driver):
        from prediction_engine.training.trainer import ModelTrainer
        return ModelTrainer(mock_neo4j_driver)
    
    @pytest.fixture
    def model_monitor(self, mock_neo4j_driver):
        from prediction_engine.monitoring.monitor import ModelMonitor
        return ModelMonitor(mock_neo4j_driver)
    
    @pytest.fixture
    def prediction_engine(self, mock_neo4j_driver):
        from prediction_engine.service import PredictionEngine
        return PredictionEngine(mock_neo4j_driver)
    
    def test_feature_extraction(self, feature_engineer, sample_resource):
        """Test feature extraction from resource"""
        features = feature_engineer._extract_resource_features(sample_resource)
        
        assert 'resource_type' in features
        assert 'cloud_provider' in features
        assert 'property_count' in features
        assert 'tag_count' in features
        assert 'has_sensitive_tags' in features
        assert 'is_public_resource' in features
        assert 'base_risk_score' in features
        
        # Check specific feature values
        assert features['resource_type'] == 'aws:s3:bucket'
        assert features['cloud_provider'] == 'aws'
        assert features['change_type'] == 'create'
        assert isinstance(features['property_count'], int)
        assert isinstance(features['tag_count'], int)
        
        # Check derived features
        assert 'weekday' in features
        assert 'hour_of_day' in features
        assert 'is_business_hours' in features
    
    def test_iac_feature_extraction(self, feature_engineer, sample_iac_plan):
        """Test feature extraction from IaC plan"""
        features_df = feature_engineer.extract_iac_features(sample_iac_plan)
        
        assert isinstance(features_df, pd.DataFrame)
        assert len(features_df) == 2  # Two resources
        
        # Check columns
        expected_columns = [
            'resource_type', 'cloud_provider', 'change_type',
            'property_count', 'tag_count', 'is_public_resource'
        ]
        for col in expected_columns:
            assert col in features_df.columns
    
    def test_historical_feature_extraction(self, feature_engineer, mock_neo4j_driver):
        """Test historical feature extraction"""
        # Mock Neo4j response
        mock_record = Mock()
        mock_record.__getitem__ = lambda self, key: {
            'violation_count': 2,
            'critical_count': 1,
            'high_count': 1,
            'days_since_last_violation': 7
        }.get(key)
        
        mock_result = Mock()
        mock_result.single.return_value = mock_record
        
        mock_session = Mock()
        mock_session.run.return_value = mock_result
        mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
        
        resource = {'resource_type': 'aws:s3:bucket', 'cloud_provider': 'aws'}
        features = feature_engineer._extract_historical_features(resource)
        
        assert features['historical_violation_count'] == 2
        assert features['historical_critical_violations'] == 1
        assert features['historical_high_violations'] == 1
        assert features['days_since_last_violation'] == 7
    
    def test_risk_score_calculation(self, feature_engineer):
        """Test risk score calculation"""
        features = {
            'resource_type': 'aws:iam:role',
            'change_type': 'create',
            'is_public_resource': True,
            'has_sensitive_tags': True,
            'historical_violation_count': 3
        }
        
        risk_score = feature_engineer._calculate_base_risk_score(features)
        
        # IAM role (3) + create (1) + public (3) + sensitive tags (2) + historical (1.5) = 10.5, capped at 10
        assert risk_score == 10.0
    
    @pytest.mark.asyncio
    async def test_prediction_engine_integration(self, prediction_engine, sample_iac_plan):
        """Test prediction engine integration"""
        # Mock the predictor
        mock_predictor = Mock()
        mock_predictor.predict_batch.return_value = {
            'violation_probability': 0.75,
            'confidence': 0.8,
            'high_risk_resources': [
                {'resource_id': 'aws_s3_bucket.test', 'violation_probability': 0.9}
            ],
            'warnings': ['High violation probability detected']
        }
        prediction_engine.active_predictor = mock_predictor
        
        context = {'tenant_id': 'test-tenant', 'stage': 'pre_deployment'}
        
        result = await prediction_engine.predict_iac(sample_iac_plan, context)
        
        assert 'violation_probability' in result
        assert 'confidence' in result
        assert 'high_risk_resources' in result
        assert 'warnings' in result
        
        # Check types
        assert isinstance(result['violation_probability'], float)
        assert 0 <= result['violation_probability'] <= 1
        assert isinstance(result['confidence'], float)
        assert 0 <= result['confidence'] <= 1
        assert isinstance(result['high_risk_resources'], list)
        assert isinstance(result['warnings'], list)
    
    def test_xgboost_predictor_training(self, xgboost_predictor, sample_training_data):
        """Test XGBoost predictor training"""
        features, labels = sample_training_data
        
        # Train model
        metrics = xgboost_predictor.train(features, labels)
        
        assert metrics.accuracy > 0.5  # Should be better than random
        assert 0 <= metrics.precision <= 1
        assert 0 <= metrics.recall <= 1
        assert 0 <= metrics.f1_score <= 1
        assert 0 <= metrics.auc_roc <= 1
        assert metrics.training_time_seconds > 0
        
        # Test prediction
        predictions = xgboost_predictor.predict(features.head(10))
        assert len(predictions) == 10
        
        for pred in predictions:
            assert 0 <= pred.violation_probability <= 1
            assert 0 <= pred.confidence <= 1
            assert 'resource_type' in pred.features
            assert 'explanation' in pred
    
    @pytest.mark.asyncio
    async def test_model_training_pipeline(self, model_trainer, mock_neo4j_driver):
        """Test model training pipeline"""
        # Mock training data collection
        mock_features = pd.DataFrame({
            'resource_type': ['aws:s3:bucket'] * 100 + ['aws:ec2:instance'] * 100,
            'cloud_provider': ['aws'] * 200,
            'is_public_resource': np.random.choice([True, False], 200),
            'has_sensitive_tags': np.random.choice([True, False], 200),
            'base_risk_score': np.random.uniform(1, 10, 200)
        })
        mock_labels = pd.Series(np.random.choice([0, 1], 200))
        
        # Mock data collector
        mock_collector = Mock()
        mock_collector.collect_training_data.return_value = (mock_features, mock_labels)
        model_trainer.data_collector = mock_collector
        
        # Train models
        result = await model_trainer.train_all_models('test-tenant')
        
        assert result['status'] == 'success'
        assert 'best_model' in result
        assert 'results' in result
        assert 'training_summary' in result
        
        # Check that models were created
        model_info = model_trainer.get_model_info('test-tenant')
        assert any(info['exists'] for info in model_info.values())
    
    def test_model_monitoring(self, model_monitor, mock_neo4j_driver):
        """Test model monitoring"""
        # Mock prediction data
        mock_predictions = [
            {
                'predicted_prob': np.random.random(),
                'actual_label': np.random.choice([0, 1]),
                'confidence': np.random.uniform(0.6, 0.9),
                'resource_type': 'aws:s3:bucket'
            }
            for _ in range(100)
        ]
        
        mock_record = Mock()
        mock_record.__getitem__ = lambda self, key: {
            'predicted_prob': pred['predicted_prob'],
            'actual_label': pred['actual_label'],
            'confidence': pred['confidence'],
            'resource_type': pred['resource_type']
        }.get(key)
        
        mock_result = Mock()
        mock_result.__iter__ = lambda self: iter([mock_record] * 100)
        mock_result.__len__ = lambda self: 100
        
        mock_session = Mock()
        mock_session.run.return_value = mock_result
        mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
        
        # Test monitoring
        result = asyncio.run(model_monitor.monitor_model_performance('test-tenant'))
        
        assert 'status' in result
        if result['status'] == 'success':
            assert 'metrics' in result
            assert 'drift_detected' in result
            assert 'data_quality' in result
    
    def test_calibration_error_calculation(self):
        """Test calibration error calculation"""
        from prediction_engine.monitoring.monitor import ModelMonitor
        
        probabilities = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
        labels = pd.Series([0, 0, 0, 1, 0, 1, 1, 1, 1])
        
        monitor = ModelMonitor(None)
        calibration_error = monitor._calculate_calibration_error(probabilities, labels)
        
        assert 0 <= calibration_error <= 1
        
        # Perfect calibration should have low error
        perfect_probs = pd.Series([0.1, 0.9])
        perfect_labels = pd.Series([0, 1])
        perfect_error = monitor._calculate_calibration_error(perfect_probs, perfect_labels)
        assert perfect_error < 0.1
    
    @pytest.mark.parametrize("historical_f1,current_f1,expected_drift", [
        ([0.8, 0.81, 0.79, 0.82, 0.8], 0.81, False),  # No drift
        ([0.8, 0.81, 0.79, 0.82, 0.8], 0.5, True),   # Significant drop
        ([0.5, 0.51, 0.49, 0.52, 0.5], 0.8, True),   # Significant improvement
    ])
    def test_drift_detection(self, historical_f1, current_f1, expected_drift):
        """Test concept drift detection"""
        from prediction_engine.monitoring.monitor import ModelMonitor
        
        monitor = ModelMonitor(None)
        
        # Mock the drift test
        def mock_drift_test(hist, curr):
            # Simple test: drift if difference > 0.2
            mean_hist = np.mean(hist)
            return abs(mean_hist - curr) > 0.2, 0.01
        
        monitor._perform_drift_test = mock_drift_test
        
        drift_result, p_value = monitor._perform_drift_test(historical_f1, current_f1)
        
        assert drift_result == expected_drift
    
    def test_recommendation_generation(self):
        """Test recommendation generation"""
        from prediction_engine.monitoring.monitor import ModelMonitor
        
        monitor = ModelMonitor(None)
        
        # Test with poor performance
        poor_performance = {
            'status': 'success',
            'metrics': {'f1_score': 0.5, 'calibration_error': 0.15},
            'drift_detected': {'detected': True, 'p_value': 0.01},
            'data_quality': {'issue_count': 2, 'issues': ['Missing values', 'Class imbalance']}
        }
        
        recommendations = monitor._generate_recommendations(poor_performance)
        
        assert len(recommendations) >= 3  # Should have multiple recommendations
        assert any(rec['type'] == 'performance' for rec in recommendations)
        assert any(rec['type'] == 'drift' for rec in recommendations)
        assert any(rec['type'] == 'data_quality' for rec in recommendations)
        
        # Test with good performance
        good_performance = {
            'status': 'success',
            'metrics': {'f1_score': 0.9, 'calibration_error': 0.05},
            'drift_detected': {'detected': False},
            'data_quality': {'issue_count': 0, 'issues': []}
        }
        
        good_recommendations = monitor._generate_recommendations(good_performance)
        
        assert len(good_recommendations) == 1
        assert good_recommendations[0]['type'] == 'info'
    
    def test_feature_preprocessing(self):
        """Test feature preprocessing"""
        from prediction_engine.preprocessing import FeaturePreprocessor
        
        # Create sample data
        df = pd.DataFrame({
            'numerical_col': [1, 2, 3, 4, 5],
            'categorical_col': ['A', 'B', 'A', 'C', 'B'],
            'text_col': ['text1', 'text2', 'text3', 'text4', 'text5']
        })
        
        preprocessor = FeaturePreprocessor()
        processed_df = preprocessor.fit_transform(df)
        
        assert processed_df.shape[0] == df.shape[0]  # Same number of rows
        assert processed_df.shape[1] > df.shape[1]  # More columns due to one-hot encoding
        
        # Check feature names are stored
        assert len(preprocessor.get_feature_names()) > 0
    
    def test_feature_selection(self):
        """Test feature selection"""
        from prediction_engine.preprocessing import FeatureSelector
        
        # Create sample data
        X = pd.DataFrame({
            'feature1': np.random.randn(100),
            'feature2': np.random.randn(100),
            'feature3': np.random.randn(100),
            'feature4': np.random.randn(100)
        })
        y = pd.Series(np.random.choice([0, 1], 100))
        
        selector = FeatureSelector(method='correlation', threshold=0.8)
        selected_df = selector.fit_transform(X, y)
        
        assert selected_df.shape[0] == X.shape[0]  # Same number of rows
        assert selected_df.shape[1] <= X.shape[1]  # Same or fewer columns
        
        # Check selected features
        selected_features = selector.get_selected_features()
        assert len(selected_features) > 0
        assert len(selected_features) <= X.shape[1]
    
    def test_lightgbm_predictor(self, sample_training_data):
        """Test LightGBM predictor"""
        from prediction_engine.models.lightgbm_predictor import LightGBMPredictor
        
        features, labels = sample_training_data
        predictor = LightGBMPredictor()
        
        # Train model
        metrics = predictor.train(features, labels)
        
        assert metrics.accuracy > 0.5
        assert 0 <= metrics.f1_score <= 1
        assert metrics.training_time_seconds > 0
        
        # Test prediction
        predictions = predictor.predict(features.head(5))
        assert len(predictions) == 5
        
        for pred in predictions:
            assert 0 <= pred.violation_probability <= 1
            assert 0 <= pred.confidence <= 1
    
    def test_training_data_collector(self, mock_neo4j_driver):
        """Test training data collector"""
        from prediction_engine.training.data_collector import TrainingDataCollector
        
        collector = TrainingDataCollector(mock_neo4j_driver)
        
        # Mock Neo4j response
        mock_records = [
            {
                'resource_id': f'resource_{i}',
                'resource_type': 'aws:s3:bucket',
                'cloud_provider': 'aws',
                'properties': {'bucket': f'test-{i}'},
                'tags': {'env': 'test'},
                'violation_label': i % 2  # Alternate labels
            }
            for i in range(100)
        ]
        
        mock_record = Mock()
        mock_record.__getitem__ = lambda self, key: mock_records[0].get(key)
        
        mock_result = Mock()
        mock_result.__iter__ = lambda self: iter([mock_record] * 100)
        mock_result.__len__ = lambda self: 100
        
        mock_session = Mock()
        mock_session.run.return_value = mock_result
        mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
        
        # Test data collection
        features, labels = collector.collect_training_data(lookback_days=90)
        
        assert isinstance(features, pd.DataFrame)
        assert isinstance(labels, pd.Series)
        assert len(features) == len(labels)
    
    def test_drift_detection_advanced(self):
        """Test advanced drift detection"""
        from prediction_engine.monitoring.drift_detection import DriftDetector
        
        detector = DriftDetector(None)
        
        # Test KL divergence calculation
        p = np.array([0.1, 0.2, 0.3, 0.4])
        q = np.array([0.1, 0.2, 0.3, 0.4])  # Same distribution
        
        kl_div = detector._calculate_kl_divergence(p, q)
        assert kl_div == 0.0  # KL divergence of identical distributions is 0
        
        # Test Jensen-Shannon distance
        js_dist = detector._calculate_jensen_shannon(p, q)
        assert js_dist == 0.0  # JS distance of identical distributions is 0
        
        # Test PSI calculation
        psi = detector._calculate_psi(p, q)
        assert psi == 0.0  # PSI of identical distributions is 0
