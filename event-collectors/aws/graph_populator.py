import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .discovery import AWSResourceDiscovery
from shared.models.events import CloudProvider, ResourceReference, Principal
from graph_engine.service import GraphEngine


class GraphPopulator:
    """Populates Neo4j graph with discovered AWS resources"""
    
    def __init__(self, graph_engine: GraphEngine, discovery: AWSResourceDiscovery):
        self.graph_engine = graph_engine
        self.discovery = discovery
        self.logger = logging.getLogger(__name__)
    
    def populate_all_resources(self) -> Dict[str, int]:
        """Discover and populate all AWS resources into graph"""
        self.logger.info("Starting AWS resource discovery and graph population")
        
        # Initialize graph schema
        self.graph_engine.initialize_schema()
        
        # Discover all resources
        resources = self.discovery.discover_all_resources()
        
        # Group resources by type for processing
        resource_counts = {}
        
        # Process resources in batches
        for resource in resources:
            try:
                self._populate_resource(resource)
                resource_type = resource['type']
                resource_counts[resource_type] = resource_counts.get(resource_type, 0) + 1
                
                if resource_counts[resource_type] % 100 == 0:
                    self.logger.info(f"Processed {resource_counts[resource_type]} {resource_type} resources")
                    
            except Exception as e:
                self.logger.error(f"Failed to populate resource {resource.get('id', 'unknown')}: {e}")
                continue
        
        # Create relationships between resources
        self._create_resource_relationships(resources)
        
        self.logger.info(f"Completed graph population. Total resources: {len(resources)}")
        return resource_counts
    
    def _populate_resource(self, resource: Dict[str, Any]) -> None:
        """Populate a single resource into the graph"""
        # Normalize resource for graph storage
        graph_resource = {
            'id': resource['id'],
            'type': resource['type'],
            'cloud': CloudProvider.AWS.value,
            'region': resource.get('region'),
            'account': resource.get('account'),
            'name': resource.get('name'),
            'state': resource.get('state', 'UNKNOWN'),
            'created_at': datetime.utcnow().timestamp(),
            'last_modified': datetime.utcnow().timestamp(),
            'valid_from': datetime.utcnow().timestamp(),
            'valid_to': None,
            'tags': resource.get('tags', {}),
            **resource.get('properties', {})
        }
        
        # Upsert resource node
        self.graph_engine.upsert_resource(graph_resource)
        
        # Create identity nodes for IAM resources
        if resource['type'].startswith('aws:iam:'):
            self._create_identity_from_resource(resource)
    
    def _create_identity_from_resource(self, resource: Dict[str, Any]) -> None:
        """Create identity node from IAM resource"""
        identity_type = resource['type'].split(':')[-1]  # Extract user, role, policy
        
        identity = {
            'id': resource['id'],
            'type': identity_type.upper(),
            'arn': resource['arn'],
            'principal': resource['arn'],
            'name': resource.get('name'),
            'cloud': CloudProvider.AWS.value,
            'created_at': resource.get('properties', {}).get('create_date', datetime.utcnow()).timestamp(),
            'last_activity': datetime.utcnow().timestamp(),
            'valid_from': datetime.utcnow().timestamp(),
            'valid_to': None,
            **{k: v for k, v in resource.get('properties', {}).items() 
               if k not in ['create_date', 'policy_document']}
        }
        
        self.graph_engine.upsert_identity(identity)
    
    def _create_resource_relationships(self, resources: List[Dict[str, Any]]) -> None:
        """Create relationships between discovered resources"""
        self.logger.info("Creating resource relationships")
        
        # Create resource map for quick lookup
        resource_map = {r['id']: r for r in resources}
        
        for resource in resources:
            try:
                self._create_resource_specific_relationships(resource, resource_map)
            except Exception as e:
                self.logger.error(f"Failed to create relationships for {resource.get('id', 'unknown')}: {e}")
                continue
    
    def _create_resource_specific_relationships(self, resource: Dict[str, Any], resource_map: Dict[str, Dict]) -> None:
        """Create relationships based on resource type"""
        resource_type = resource['type']
        properties = resource.get('properties', {})
        
        if resource_type == 'aws:ec2:instance':
            self._create_ec2_relationships(resource, resource_map)
        elif resource_type == 'aws:s3:bucket':
            self._create_s3_relationships(resource, resource_map)
        elif resource_type == 'aws:iam:user':
            self._create_iam_user_relationships(resource, resource_map)
        elif resource_type == 'aws:iam:role':
            self._create_iam_role_relationships(resource, resource_map)
        elif resource_type == 'aws:rds:instance':
            self._create_rds_relationships(resource, resource_map)
        elif resource_type == 'aws:ec2:security-group':
            self._create_security_group_relationships(resource, resource_map)
        elif resource_type == 'aws:lambda:function':
            self._create_lambda_relationships(resource, resource_map)
    
    def _create_ec2_relationships(self, instance: Dict[str, Any], resource_map: Dict[str, Dict]) -> None:
        """Create relationships for EC2 instance"""
        properties = instance.get('properties', {})
        instance_id = instance['id']
        
        # Security group relationships
        for sg in properties.get('security_groups', []):
            sg_id = sg.get('GroupId')
            if sg_id and sg_id in resource_map:
                self.graph_engine.create_relationship(
                    from_id=instance_id,
                    to_id=sg_id,
                    rel_type='MEMBER_OF',
                    properties={
                        'relationship_type': 'security_group',
                        'created_at': datetime.utcnow().timestamp()
                    }
                )
        
        # VPC relationship
        vpc_id = properties.get('vpc_id')
        if vpc_id and vpc_id in resource_map:
            self.graph_engine.create_relationship(
                from_id=instance_id,
                to_id=vpc_id,
                rel_type='LOCATED_IN',
                properties={
                    'relationship_type': 'vpc',
                    'created_at': datetime.utcnow().timestamp()
                }
            )
        
        # Subnet relationship
        subnet_id = properties.get('subnet_id')
        if subnet_id and subnet_id in resource_map:
            self.graph_engine.create_relationship(
                from_id=instance_id,
                to_id=subnet_id,
                rel_type='LOCATED_IN',
                properties={
                    'relationship_type': 'subnet',
                    'created_at': datetime.utcnow().timestamp()
                }
            )
        
        # EBS volume relationships
        for attachment in properties.get('attachments', []):
            volume_id = attachment.get('VolumeId')
            if volume_id and volume_id in resource_map:
                self.graph_engine.create_relationship(
                    from_id=instance_id,
                    to_id=volume_id,
                    rel_type='USES',
                    properties={
                        'device': attachment.get('Device'),
                        'attach_time': attachment.get('AttachTime'),
                        'delete_on_termination': attachment.get('DeleteOnTermination', False),
                        'created_at': datetime.utcnow().timestamp()
                    }
                )
    
    def _create_s3_relationships(self, bucket: Dict[str, Any], resource_map: Dict[str, Dict]) -> None:
        """Create relationships for S3 bucket"""
        # S3 buckets don't typically have direct relationships with other AWS resources
        # but we can create relationships based on access patterns and policies
        pass
    
    def _create_iam_user_relationships(self, user: Dict[str, Any], resource_map: Dict[str, Dict]) -> None:
        """Create relationships for IAM user"""
        properties = user.get('properties', {})
        user_id = user['id']
        
        # Policy relationships
        for policy_arn in properties.get('policies', []):
            if policy_arn in resource_map:
                self.graph_engine.create_relationship(
                    from_id=user_id,
                    to_id=policy_arn,
                    rel_type='HAS_POLICY',
                    properties={
                        'attachment_type': 'user_policy',
                        'created_at': datetime.utcnow().timestamp()
                    }
                )
    
    def _create_iam_role_relationships(self, role: Dict[str, Any], resource_map: Dict[str, Dict]) -> None:
        """Create relationships for IAM role"""
        role_id = role['id']
        
        # Policy relationships would be created here if we had policy attachment data
        # This would require additional API calls to get attached policies
        pass
    
    def _create_rds_relationships(self, rds: Dict[str, Any], resource_map: Dict[str, Dict]) -> None:
        """Create relationships for RDS instance"""
        properties = rds.get('properties', {})
        rds_id = rds['id']
        
        # VPC relationship
        vpc_id = properties.get('vpc_id')
        if vpc_id and vpc_id in resource_map:
            self.graph_engine.create_relationship(
                from_id=rds_id,
                to_id=vpc_id,
                rel_type='LOCATED_IN',
                properties={
                    'relationship_type': 'vpc',
                    'created_at': datetime.utcnow().timestamp()
                }
            )
        
        # Subnet group relationships
        subnet_group = properties.get('subnet_group')
        if subnet_group:
            # This would require additional API calls to get subnet group details
            pass
    
    def _create_security_group_relationships(self, sg: Dict[str, Any], resource_map: Dict[str, Dict]) -> None:
        """Create relationships for security group"""
        properties = sg.get('properties', {})
        sg_id = sg['id']
        
        # VPC relationship
        vpc_id = properties.get('vpc_id')
        if vpc_id and vpc_id in resource_map:
            self.graph_engine.create_relationship(
                from_id=sg_id,
                to_id=vpc_id,
                rel_type='MEMBER_OF',
                properties={
                    'relationship_type': 'vpc',
                    'created_at': datetime.utcnow().timestamp()
                }
            )
        
        # Security group rule relationships would be created here
        # This would require parsing ingress/egress rules and finding referenced security groups
        pass
    
    def _create_lambda_relationships(self, lambda_func: Dict[str, Any], resource_map: Dict[str, Dict]) -> None:
        """Create relationships for Lambda function"""
        properties = lambda_func.get('properties', {})
        lambda_id = lambda_func['id']
        
        # VPC relationships
        vpc_id = properties.get('vpc_id')
        if vpc_id and vpc_id in resource_map:
            self.graph_engine.create_relationship(
                from_id=lambda_id,
                to_id=vpc_id,
                rel_type='LOCATED_IN',
                properties={
                    'relationship_type': 'vpc',
                    'created_at': datetime.utcnow().timestamp()
                }
            )
        
        # Security group relationships
        for sg_id in properties.get('security_groups', []):
            if sg_id in resource_map:
                self.graph_engine.create_relationship(
                    from_id=lambda_id,
                    to_id=sg_id,
                    rel_type='MEMBER_OF',
                    properties={
                        'relationship_type': 'security_group',
                        'created_at': datetime.utcnow().timestamp()
                    }
                )
    
    def populate_account_structure(self) -> None:
        """Populate basic account structure and hierarchy"""
        self.logger.info("Populating account structure")
        
        # Create account node
        account_id = self.discovery.account_id
        account_node = {
            'id': f"arn:aws:iam::{account_id}:root",
            'type': 'aws:account',
            'cloud': CloudProvider.AWS.value,
            'region': None,
            'account': account_id,
            'name': f"AWS Account {account_id}",
            'state': 'ACTIVE',
            'created_at': datetime.utcnow().timestamp(),
            'valid_from': datetime.utcnow().timestamp(),
            'valid_to': None
        }
        
        self.graph_engine.upsert_resource(account_node)
        
        # Create organizational structure if available
        # This would require AWS Organizations API calls
        pass
    
    def get_population_status(self) -> Dict[str, Any]:
        """Get status of graph population"""
        try:
            # Get node counts by type
            query = """
            MATCH (n)
            WHERE n.valid_to IS NULL
            RETURN n.type as resource_type, count(n) as count
            ORDER BY count DESC
            """
            
            with self.graph_engine.driver.session() as session:
                result = session.run(query)
                resource_counts = {record['resource_type']: record['count'] for record in result}
                
                # Get relationship counts
                rel_query = """
                MATCH ()-[r]->()
                WHERE r.valid_to IS NULL
                RETURN type(r) as relationship_type, count(r) as count
                ORDER BY count DESC
                """
                
                rel_result = session.run(rel_query)
                relationship_counts = {record['relationship_type']: record['count'] for record in rel_result}
                
                return {
                    'resource_counts': resource_counts,
                    'relationship_counts': relationship_counts,
                    'total_nodes': sum(resource_counts.values()),
                    'total_relationships': sum(relationship_counts.values()),
                    'last_updated': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get population status: {e}")
            return {
                'error': str(e),
                'last_updated': datetime.utcnow().isoformat()
            }
