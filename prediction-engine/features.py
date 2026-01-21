import hashlib
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import re
import logging

logger = logging.getLogger(__name__)

class FeatureEngineer:
    """Feature engineering for violation prediction"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        self.feature_cache = {}
        
    def extract_iac_features(self, iac_plan: Dict) -> pd.DataFrame:
        """Extract features from IaC plan"""
        features = []
        
        for resource in iac_plan.get('resources', []):
            resource_features = self._extract_resource_features(resource)
            
            # Add context features
            resource_features.update({
                'plan_total_resources': len(iac_plan.get('resources', [])),
                'plan_resource_types_count': self._count_resource_types(iac_plan),
                'plan_change_types_distribution': self._change_type_distribution(iac_plan),
                'plan_has_dependencies': len(iac_plan.get('dependencies', [])) > 0
            })
            
            features.append(resource_features)
        
        return pd.DataFrame(features)
    
    def _extract_resource_features(self, resource: Dict) -> Dict[str, Any]:
        """Extract features from a single resource"""
        features = {}
        
        # Basic features
        features['resource_type'] = resource.get('resource_type', '')
        features['cloud_provider'] = resource.get('cloud_provider', '')
        features['change_type'] = resource.get('change_type', 'create')
        
        # Property-based features
        properties = resource.get('properties', {})
        tags = resource.get('tags', {})
        
        # Complexity features
        features['property_count'] = len(properties)
        features['tag_count'] = len(tags)
        features['has_sensitive_tags'] = self._has_sensitive_tags(tags)
        features['is_public_resource'] = self._is_public_resource(resource)
        
        # Numerical features from properties
        features = self._extract_numerical_features(features, properties)
        
        # Categorical features
        features = self._extract_categorical_features(features, properties, tags)
        
        # Historical features
        features.update(self._extract_historical_features(resource))
        
        # Graph features
        features.update(self._extract_graph_features(resource))
        
        # Derived features
        features = self._create_derived_features(features)
        
        return features
    
    def _extract_historical_features(self, resource: Dict) -> Dict[str, Any]:
        """Extract historical violation features"""
        resource_type = resource.get('resource_type', '')
        cloud_provider = resource.get('cloud_provider', '')
        
        # Query Neo4j for historical data
        query = """
        MATCH (r:Resource {type: $type, cloud: $cloud})
        OPTIONAL MATCH (r)<-[:DETECTED_ON]-(v:Violation)
        WITH r, count(v) as violation_count,
             collect(v.severity) as violation_severities,
             collect(v.timestamp) as violation_timestamps
        RETURN violation_count,
               size([s in violation_severities WHERE s = 'critical']) as critical_count,
               size([s in violation_severities WHERE s = 'high']) as high_count,
               CASE WHEN violation_count > 0 
                    THEN duration.inSeconds(
                        datetime(reduction.violation_timestamps[-1]), 
                        datetime()
                    ).days 
                    ELSE null END as days_since_last_violation
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, type=resource_type, cloud=cloud_provider)
                record = result.single()
                
                if record:
                    return {
                        'historical_violation_count': record['violation_count'],
                        'historical_critical_violations': record['critical_count'],
                        'historical_high_violations': record['high_count'],
                        'days_since_last_violation': record['days_since_last_violation'] or 0
                    }
        except Exception as e:
            logger.error(f"Error extracting historical features: {e}")
        
        return {
            'historical_violation_count': 0,
            'historical_critical_violations': 0,
            'historical_high_violations': 0,
            'days_since_last_violation': 0
        }
    
    def _extract_graph_features(self, resource: Dict) -> Dict[str, Any]:
        """Extract graph-based features"""
        resource_id = resource.get('iac_id', '')
        
        query = """
        MATCH (r:IaCResource {id: $id})
        OPTIONAL MATCH (r)-[:WILL_AFFECT]->(existing:Resource)
        OPTIONAL MATCH (existing)-[:CONNECTED_TO*1..3]-(connected:Resource)
        WITH r, 
             count(DISTINCT existing) as existing_resources,
             count(DISTINCT connected) as connected_resources,
             collect(DISTINCT existing.type) as existing_types
        OPTIONAL MATCH (r)-[:DEPENDS_ON]->(dep:IaCResource)
        WITH r, existing_resources, connected_resources, existing_types,
             count(DISTINCT dep) as dependency_count
        RETURN existing_resources,
               connected_resources,
               dependency_count,
               size(existing_types) as existing_types_count,
               CASE WHEN existing_resources > 0 THEN true ELSE false END as affects_existing
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, id=resource_id)
                record = result.single()
                
                if record:
                    return {
                        'affects_existing_resources': record['affects_existing'],
                        'existing_resources_count': record['existing_resources'],
                        'connected_resources_count': record['connected_resources'],
                        'dependency_count': record['dependency_count'],
                        'existing_resource_types_count': record['existing_types_count']
                    }
        except Exception as e:
            logger.error(f"Error extracting graph features: {e}")
        
        return {
            'affects_existing_resources': False,
            'existing_resources_count': 0,
            'connected_resources_count': 0,
            'dependency_count': 0,
            'existing_resource_types_count': 0
        }
    
    def _extract_numerical_features(self, features: Dict, properties: Dict) -> Dict:
        """Extract numerical features from properties"""
        # Size-related features (for different resource types)
        if 'aws:ec2:instance' in features['resource_type']:
            instance_type = properties.get('instance_type', 't2.micro')
            features['instance_size_score'] = self._instance_size_score(instance_type)
            features['has_public_ip'] = properties.get('associate_public_ip_address', False)
            
        elif 'aws:s3:bucket' in features['resource_type']:
            features['versioning_enabled'] = properties.get('versioning', {}).get('enabled', False)
            features['encryption_enabled'] = 'server_side_encryption_configuration' in properties
            
        elif 'aws:rds:' in features['resource_type']:
            features['instance_class'] = properties.get('instance_class', '')
            features['storage_size_gb'] = properties.get('allocated_storage', 20)
            features['multi_az'] = properties.get('multi_az', False)
            features['publicly_accessible'] = properties.get('publicly_accessible', False)
        
        # Generic numerical features
        features['property_depth'] = self._calculate_property_depth(properties)
        features['list_property_count'] = self._count_list_properties(properties)
        features['map_property_count'] = self._count_map_properties(properties)
        
        return features
    
    def _extract_categorical_features(self, features: Dict, properties: Dict, tags: Dict) -> Dict:
        """Extract categorical features"""
        # Environment from tags
        features['environment'] = tags.get('env', tags.get('environment', 'unknown'))
        features['team'] = tags.get('team', tags.get('owner', 'unknown'))
        
        # Compliance categories
        features['has_compliance_tags'] = any(
            tag.lower() in ['pci', 'hipaa', 'gdpr', 'soc2'] 
            for tag in tags.values()
        )
        
        # Cost-related features
        features['cost_center'] = tags.get('cost_center', 'unknown')
        features['project'] = tags.get('project', 'unknown')
        
        # Security categories
        features['confidentiality'] = tags.get('confidentiality', 'low')
        features['integrity'] = tags.get('integrity', 'low')
        features['availability'] = tags.get('availability', 'low')
        
        return features
    
    def _create_derived_features(self, features: Dict) -> Dict:
        """Create derived/engineered features"""
        # Risk scores
        features['base_risk_score'] = self._calculate_base_risk_score(features)
        
        # Interaction features
        if features.get('is_public_resource', False):
            features['public_with_sensitive_tags'] = (
                features.get('has_sensitive_tags', False) and 
                features.get('is_public_resource', False)
            )
        
        # Temporal features
        features['weekday'] = datetime.now().weekday()
        features['hour_of_day'] = datetime.now().hour
        features['is_business_hours'] = 9 <= datetime.now().hour <= 17
        
        # Feature ratios
        if features.get('property_count', 0) > 0:
            features['tag_to_property_ratio'] = (
                features.get('tag_count', 0) / features.get('property_count', 1)
            )
        
        return features
    
    # Helper methods
    @staticmethod
    def _has_sensitive_tags(tags: Dict) -> bool:
        """Check if tags contain sensitive information"""
        sensitive_patterns = [
            'password', 'secret', 'key', 'token', 'credential',
            'pii', 'phi', 'confidential', 'restricted', 'internal'
        ]
        
        for tag_value in tags.values():
            tag_lower = str(tag_value).lower()
            if any(pattern in tag_lower for pattern in sensitive_patterns):
                return True
        
        return False
    
    @staticmethod
    def _is_public_resource(resource: Dict) -> bool:
        """Check if resource is configured for public access"""
        properties = resource.get('properties', {})
        resource_type = resource.get('resource_type', '')
        
        if 'aws:s3:bucket' in resource_type:
            acl = properties.get('acl', 'private')
            return acl in ['public-read', 'public-read-write']
        
        elif 'aws:ec2:security-group' in resource_type:
            ingress_rules = properties.get('ingress', [])
            for rule in ingress_rules:
                if rule.get('cidr_blocks') == ['0.0.0.0/0']:
                    return True
        
        return False
    
    @staticmethod
    def _calculate_base_risk_score(features: Dict) -> float:
        """Calculate base risk score from features"""
        score = 0.0
        
        # Resource type risk
        resource_type = features.get('resource_type', '')
        if any(rt in resource_type for rt in ['iam', 'kms', 'secret']):
            score += 3.0
        elif any(rt in resource_type for rt in ['rds', 's3', 'ec2']):
            score += 2.0
        else:
            score += 1.0
        
        # Change type risk
        change_type = features.get('change_type', 'create')
        if change_type == 'delete':
            score += 2.0
        elif change_type == 'update':
            score += 1.0
        
        # Public access risk
        if features.get('is_public_resource', False):
            score += 3.0
        
        # Sensitive tags risk
        if features.get('has_sensitive_tags', False):
            score += 2.0
        
        # Historical violations
        historical_count = features.get('historical_violation_count', 0)
        score += min(historical_count * 0.5, 5.0)
        
        return min(score, 10.0)  # Cap at 10
    
    @staticmethod
    def _instance_size_score(instance_type: str) -> int:
        """Score instance size based on type"""
        size_map = {
            'nano': 1, 'micro': 2, 'small': 3, 'medium': 4,
            'large': 5, 'xlarge': 6, '2xlarge': 7, '4xlarge': 8,
            '8xlarge': 9, '12xlarge': 10, '16xlarge': 11,
            '24xlarge': 12, '32xlarge': 13, 'metal': 14
        }
        
        for size, score in size_map.items():
            if size in instance_type.lower():
                return score
        
        return 3  # Default to small
    
    @staticmethod
    def _count_resource_types(iac_plan: Dict) -> int:
        """Count unique resource types in plan"""
        return len(set(r.get('resource_type', '') for r in iac_plan.get('resources', [])))
    
    @staticmethod
    def _change_type_distribution(iac_plan: Dict) -> str:
        """Get distribution of change types"""
        changes = [r.get('change_type', 'create') for r in iac_plan.get('resources', [])]
        return f"c{changes.count('create')}_u{changes.count('update')}_d{changes.count('delete')}"
    
    @staticmethod
    def _calculate_property_depth(obj: Any, current_depth: int = 0) -> int:
        """Calculate maximum depth of nested properties"""
        if not isinstance(obj, dict):
            return current_depth
        
        max_depth = current_depth
        for value in obj.values():
            depth = FeatureEngineer._calculate_property_depth(value, current_depth + 1)
            max_depth = max(max_depth, depth)
        
        return max_depth
    
    @staticmethod
    def _count_list_properties(obj: Any) -> int:
        """Count list properties"""
        if not isinstance(obj, dict):
            return 0
        
        count = 0
        for value in obj.values():
            if isinstance(value, list):
                count += 1
            elif isinstance(value, dict):
                count += FeatureEngineer._count_list_properties(value)
        
        return count
    
    @staticmethod
    def _count_map_properties(obj: Any) -> int:
        """Count map/dict properties"""
        if not isinstance(obj, dict):
            return 0
        
        count = len(obj)
        for value in obj.values():
            if isinstance(value, dict):
                count += FeatureEngineer._count_map_properties(value)
        
        return count
