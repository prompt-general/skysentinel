from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import logging

logger = logging.getLogger(__name__)

class TrainingDataCollector:
    """Collect and prepare training data from historical violations"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
    
    def collect_training_data(self, 
                            lookback_days: int = 90,
                            min_samples: int = 1000) -> Tuple[pd.DataFrame, pd.Series]:
        """Collect labeled training data from historical violations"""
        
        # Query for violations and non-violations
        query = """
        // Get resources that had violations
        MATCH (r:Resource)-[:DETECTED_ON]-(v:Violation)
        WHERE v.timestamp > datetime() - duration('P' + $lookback_days + 'D')
        WITH r, 
             count(v) as violation_count,
             collect(v.severity) as severities,
             collect(v.timestamp) as violation_times
        RETURN r.id as resource_id,
               r.type as resource_type,
               r.cloud as cloud_provider,
               r.tags as tags,
               r.properties as properties,
               true as violation_label,
               violation_count,
               severities,
               violation_times
        
        UNION
        
        // Get resources without violations (negative samples)
        MATCH (r:Resource)
        WHERE NOT EXISTS {
            MATCH (r)<-[:DETECTED_ON]-(v:Violation)
            WHERE v.timestamp > datetime() - duration('P' + $lookback_days + 'D')
        }
        AND r.created_at > datetime() - duration('P' + $lookback_days + 'D')
        RETURN r.id as resource_id,
               r.type as resource_type,
               r.cloud as cloud_provider,
               r.tags as tags,
               r.properties as properties,
               false as violation_label,
               0 as violation_count,
               [] as severities,
               [] as violation_times
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, lookback_days=lookback_days)
                records = [dict(record) for record in result]
                
                if len(records) < min_samples:
                    logger.warning(f"Insufficient training data: {len(records)} records")
                    return self._generate_synthetic_data(min_samples)
                
                # Convert to DataFrame
                df = pd.DataFrame(records)
                
                # Balance classes (undersample majority)
                df_balanced = self._balance_classes(df)
                
                # Extract features
                from ..features import FeatureEngineer
                feature_engineer = FeatureEngineer(self.driver)
                features = []
                labels = []
                
                for _, row in df_balanced.iterrows():
                    # Create resource dict
                    resource = {
                        'resource_type': row['resource_type'],
                        'cloud_provider': row['cloud_provider'],
                        'properties': row['properties'],
                        'tags': row['tags']
                    }
                    
                    # Extract features
                    resource_features = feature_engineer._extract_resource_features(resource)
                    resource_features['resource_id'] = row['resource_id']
                    
                    features.append(resource_features)
                    labels.append(row['violation_label'])
                
                features_df = pd.DataFrame(features)
                labels_series = pd.Series(labels, dtype=int)
                
                return features_df, labels_series
                
        except Exception as e:
            logger.error(f"Error collecting training data: {e}")
            return pd.DataFrame(), pd.Series()
    
    def _balance_classes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Balance positive and negative classes"""
        positive_samples = df[df['violation_label'] == True]
        negative_samples = df[df['violation_label'] == False]
        
        # Undersample majority class
        if len(positive_samples) > len(negative_samples):
            # More violations than non-violations
            positive_sampled = positive_samples.sample(
                n=min(len(negative_samples) * 2, len(positive_samples)),
                random_state=42
            )
            balanced_df = pd.concat([positive_sampled, negative_samples])
        else:
            # More non-violations than violations
            negative_sampled = negative_samples.sample(
                n=min(len(positive_samples) * 2, len(negative_samples)),
                random_state=42
            )
            balanced_df = pd.concat([positive_samples, negative_sampled])
        
        return balanced_df.sample(frac=1, random_state=42)  # Shuffle
    
    def _generate_synthetic_data(self, min_samples: int) -> Tuple[pd.DataFrame, pd.Series]:
        """Generate synthetic training data when real data is insufficient"""
        logger.info(f"Generating synthetic data for {min_samples} samples")
        
        # Define resource types and their base violation probabilities
        resource_types = {
            'aws:s3:bucket': 0.3,
            'aws:ec2:instance': 0.2,
            'aws:iam:role': 0.4,
            'aws:rds:dbinstance': 0.25,
            'azure:storage:blob': 0.3,
            'gcp:compute:instance': 0.2
        }
        
        features = []
        labels = []
        
        for i in range(min_samples):
            # Randomly select resource type
            resource_type = np.random.choice(list(resource_types.keys()))
            base_prob = resource_types[resource_type]
            
            # Generate synthetic features
            resource_features = {
                'resource_type': resource_type,
                'cloud_provider': resource_type.split(':')[0],
                'change_type': np.random.choice(['create', 'update', 'delete']),
                'property_count': np.random.randint(5, 50),
                'tag_count': np.random.randint(0, 10),
                'has_sensitive_tags': np.random.random() < 0.1,
                'is_public_resource': np.random.random() < 0.2,
                'base_risk_score': np.random.uniform(1, 10),
                'historical_violation_count': np.random.poisson(0.5),
                'affects_existing_resources': np.random.random() < 0.3,
                'dependency_count': np.random.randint(0, 5)
            }
            
            # Calculate violation probability
            violation_prob = base_prob
            if resource_features['is_public_resource']:
                violation_prob += 0.3
            if resource_features['has_sensitive_tags']:
                violation_prob += 0.2
            if resource_features['historical_violation_count'] > 0:
                violation_prob += 0.1
            
            # Generate label based on probability
            violation_label = np.random.random() < violation_prob
            
            features.append(resource_features)
            labels.append(violation_label)
        
        return pd.DataFrame(features), pd.Series(labels)
    
    def collect_cross_validation_data(self, 
                                    lookback_days: int = 90,
                                    cv_folds: int = 5) -> List[Tuple[pd.DataFrame, pd.Series]]:
        """Collect data for cross-validation with temporal splits"""
        
        # Get date range for splitting
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        fold_duration = lookback_days // cv_folds
        
        cv_data = []
        
        for fold in range(cv_folds):
            # Calculate fold date range
            fold_start = start_date + timedelta(days=fold * fold_duration)
            fold_end = fold_start + timedelta(days=fold_duration)
            
            # Query for this time period
            query = """
            MATCH (r:Resource)-[:DETECTED_ON]-(v:Violation)
            WHERE v.timestamp >= datetime($start_date) 
              AND v.timestamp < datetime($end_date)
            RETURN r.id as resource_id,
                   r.type as resource_type,
                   r.cloud as cloud_provider,
                   r.tags as tags,
                   r.properties as properties,
                   true as violation_label
            
            UNION
            
            MATCH (r:Resource)
            WHERE NOT EXISTS {
                MATCH (r)<-[:DETECTED_ON]-(v:Violation)
                WHERE v.timestamp >= datetime($start_date) 
                  AND v.timestamp < datetime($end_date)
            }
            AND r.created_at >= datetime($start_date) 
              AND r.created_at < datetime($end_date)
            RETURN r.id as resource_id,
                   r.type as resource_type,
                   r.cloud as cloud_provider,
                   r.tags as tags,
                   r.properties as properties,
                   false as violation_label
            """
            
            try:
                with self.driver.session() as session:
                    result = session.run(query, start_date=fold_start, end_date=fold_end)
                    records = [dict(record) for record in result]
                    
                    if records:
                        df = pd.DataFrame(records)
                        df_balanced = self._balance_classes(df)
                        
                        # Extract features
                        from ..features import FeatureEngineer
                        feature_engineer = FeatureEngineer(self.driver)
                        features = []
                        labels = []
                        
                        for _, row in df_balanced.iterrows():
                            resource = {
                                'resource_type': row['resource_type'],
                                'cloud_provider': row['cloud_provider'],
                                'properties': row['properties'],
                                'tags': row['tags']
                            }
                            
                            resource_features = feature_engineer._extract_resource_features(resource)
                            resource_features['resource_id'] = row['resource_id']
                            
                            features.append(resource_features)
                            labels.append(row['violation_label'])
                        
                        features_df = pd.DataFrame(features)
                        labels_series = pd.Series(labels, dtype=int)
                        
                        cv_data.append((features_df, labels_series))
                        
            except Exception as e:
                logger.error(f"Error collecting CV data for fold {fold}: {e}")
                continue
        
        return cv_data
    
    def collect_incremental_data(self, 
                                last_training_date: datetime,
                                new_samples: int = 100) -> Tuple[pd.DataFrame, pd.Series]:
        """Collect new data for incremental model training"""
        
        query = """
        MATCH (r:Resource)-[:DETECTED_ON]-(v:Violation)
        WHERE v.timestamp >= datetime($last_date)
        RETURN r.id as resource_id,
               r.type as resource_type,
               r.cloud as cloud_provider,
               r.tags as tags,
               r.properties as properties,
               true as violation_label
        
        UNION
        
        MATCH (r:Resource)
        WHERE NOT EXISTS {
            MATCH (r)<-[:DETECTED_ON]-(v:Violation)
            WHERE v.timestamp >= datetime($last_date)
        }
        AND r.created_at >= datetime($last_date)
        RETURN r.id as resource_id,
               r.type as resource_type,
               r.cloud as cloud_provider,
               r.tags as tags,
               r.properties as properties,
               false as violation_label
        LIMIT $limit
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, last_date=last_training_date, limit=new_samples)
                records = [dict(record) for record in result]
                
                if not records:
                    logger.info("No new data available for incremental training")
                    return pd.DataFrame(), pd.Series()
                
                df = pd.DataFrame(records)
                df_balanced = self._balance_classes(df)
                
                # Extract features
                from ..features import FeatureEngineer
                feature_engineer = FeatureEngineer(self.driver)
                features = []
                labels = []
                
                for _, row in df_balanced.iterrows():
                    resource = {
                        'resource_type': row['resource_type'],
                        'cloud_provider': row['cloud_provider'],
                        'properties': row['properties'],
                        'tags': row['tags']
                    }
                    
                    resource_features = feature_engineer._extract_resource_features(resource)
                    resource_features['resource_id'] = row['resource_id']
                    
                    features.append(resource_features)
                    labels.append(row['violation_label'])
                
                features_df = pd.DataFrame(features)
                labels_series = pd.Series(labels, dtype=int)
                
                logger.info(f"Collected {len(features_df)} new samples for incremental training")
                return features_df, labels_series
                
        except Exception as e:
            logger.error(f"Error collecting incremental data: {e}")
            return pd.DataFrame(), pd.Series()
    
    def get_data_statistics(self, lookback_days: int = 90) -> Dict[str, Any]:
        """Get statistics about available training data"""
        
        query = """
        MATCH (r:Resource)-[:DETECTED_ON]-(v:Violation)
        WHERE v.timestamp > datetime() - duration('P' + $lookback_days + 'D')
        WITH r, count(v) as violation_count
        RETURN 
            count(r) as resources_with_violations,
            sum(violation_count) as total_violations,
            avg(violation_count) as avg_violations_per_resource
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, lookback_days=lookback_days)
                record = result.single()
                
                if record:
                    return {
                        'resources_with_violations': record['resources_with_violations'],
                        'total_violations': record['total_violations'],
                        'avg_violations_per_resource': record['avg_violations_per_resource'],
                        'lookback_days': lookback_days
                    }
                
        except Exception as e:
            logger.error(f"Error getting data statistics: {e}")
        
        return {}
    
    def validate_data_quality(self, features_df: pd.DataFrame, labels_series: pd.Series) -> Dict[str, Any]:
        """Validate training data quality"""
        
        quality_report = {
            'total_samples': len(features_df),
            'positive_samples': int(labels_series.sum()),
            'negative_samples': int(len(labels_series) - labels_series.sum()),
            'class_balance': float(labels_series.mean()),
            'missing_values': features_df.isnull().sum().to_dict(),
            'feature_types': features_df.dtypes.to_dict(),
            'duplicate_rows': features_df.duplicated().sum()
        }
        
        # Check for data quality issues
        issues = []
        
        if quality_report['total_samples'] < 100:
            issues.append("Very small dataset (< 100 samples)")
        
        if quality_report['class_balance'] < 0.1 or quality_report['class_balance'] > 0.9:
            issues.append("Severe class imbalance")
        
        if quality_report['duplicate_rows'] > 0:
            issues.append(f"Found {quality_report['duplicate_rows']} duplicate rows")
        
        high_missing = [col for col, count in quality_report['missing_values'].items() 
                      if count > quality_report['total_samples'] * 0.5]
        if high_missing:
            issues.append(f"High missing values in: {high_missing}")
        
        quality_report['quality_issues'] = issues
        quality_report['data_quality_score'] = max(0, 100 - len(issues) * 10)
        
        return quality_report
