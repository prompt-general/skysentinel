import pytest
from datetime import datetime, timedelta
from graph_engine.service import GraphEngine
from shared.models.events import CloudProvider


class TestGraphEngine:
    """Test cases for GraphEngine service"""
    
    def test_upsert_resource(self, graph_engine, mock_aws_resources):
        """Test resource upsertion"""
        resource = mock_aws_resources[0]
        
        # Insert resource
        result = graph_engine.upsert_resource(resource)
        assert result is True
        
        # Verify resource exists
        with graph_engine.driver.session() as session:
            result = session.run(
                "MATCH (r:Resource {id: $id}) RETURN r",
                id=resource['id']
            )
            node = result.single()
            assert node is not None
            assert node['r']['id'] == resource['id']
            assert node['r']['type'] == resource['type']
    
    def test_upsert_identity(self, graph_engine):
        """Test identity upsertion"""
        identity = {
            'id': 'arn:aws:iam::123456789012:user/test-user',
            'type': 'USER',
            'arn': 'arn:aws:iam::123456789012:user/test-user',
            'principal': 'arn:aws:iam::123456789012:user/test-user',
            'name': 'test-user',
            'cloud': CloudProvider.AWS.value,
            'created_at': datetime.utcnow().timestamp(),
            'last_activity': datetime.utcnow().timestamp(),
            'valid_from': datetime.utcnow().timestamp(),
            'valid_to': None
        }
        
        # Insert identity
        result = graph_engine.upsert_identity(identity)
        assert result is True
        
        # Verify identity exists
        with graph_engine.driver.session() as session:
            result = session.run(
                "MATCH (i:Identity {id: $id}) RETURN i",
                id=identity['id']
            )
            node = result.single()
            assert node is not None
            assert node['i']['id'] == identity['id']
            assert node['i']['type'] == identity['type']
    
    def test_create_event_node(self, graph_engine, sample_event):
        """Test event node creation"""
        # Create event
        result = graph_engine.create_event_node(sample_event)
        assert result is True
        
        # Verify event exists
        with graph_engine.driver.session() as session:
            result = session.run(
                "MATCH (e:Event {id: $id}) RETURN e",
                id=sample_event['id']
            )
            node = result.single()
            assert node is not None
            assert node['e']['id'] == sample_event['id']
            assert node['e']['event_type'] == sample_event['event_type']
            assert node['e']['operation'] == sample_event['operation']
    
    def test_create_relationship(self, graph_engine, sample_event):
        """Test relationship creation"""
        # Create nodes first
        principal = {
            'id': sample_event['principal_id'],
            'type': 'USER',
            'arn': sample_event['principal_id'],
            'principal': sample_event['principal_id'],
            'name': 'test-user',
            'cloud': CloudProvider.AWS.value,
            'created_at': datetime.utcnow().timestamp(),
            'last_activity': datetime.utcnow().timestamp(),
            'valid_from': datetime.utcnow().timestamp(),
            'valid_to': None
        }
        
        resource = {
            'id': sample_event['resource_id'],
            'type': 'aws:ec2:instance',
            'region': 'us-east-1',
            'account': '123456789012',
            'name': 'test-instance',
            'state': 'running',
            'created_at': datetime.utcnow().timestamp(),
            'valid_from': datetime.utcnow().timestamp(),
            'valid_to': None
        }
        
        graph_engine.upsert_identity(principal)
        graph_engine.upsert_resource(resource)
        
        # Create relationship
        result = graph_engine.create_relationship(
            from_id=sample_event['principal_id'],
            to_id=sample_event['resource_id'],
            rel_type='PERFORMED',
            properties={
                'event_name': sample_event['operation'],
                'timestamp': sample_event['event_time'],
                'status': sample_event['status']
            }
        )
        assert result is True
        
        # Verify relationship exists
        with graph_engine.driver.session() as session:
            result = session.run("""
                MATCH (i:Identity)-[r:PERFORMED]->(r:Resource)
                WHERE i.id = $from_id AND r.id = $to_id
                RETURN r
            """, from_id=sample_event['principal_id'], to_id=sample_event['resource_id'])
            relationship = result.single()
            assert relationship is not None
            assert relationship['r']['event_name'] == sample_event['operation']
    
    def test_get_resource_lineage(self, graph_engine, mock_aws_resources):
        """Test resource lineage retrieval"""
        resource = mock_aws_resources[0]
        
        # Insert resource
        graph_engine.upsert_resource(resource)
        
        # Get lineage
        lineage = graph_engine.get_resource_lineage(resource['id'])
        assert lineage is not None
        assert len(lineage) >= 1
        assert lineage[0]['id'] == resource['id']
    
    def test_get_resource_relationships(self, graph_engine, mock_aws_resources):
        """Test resource relationships retrieval"""
        resource = mock_aws_resources[0]
        
        # Insert resource
        graph_engine.upsert_resource(resource)
        
        # Get relationships
        relationships = graph_engine.get_resource_relationships(resource['id'])
        assert relationships is not None
        assert isinstance(relationships, list)
    
    def test_find_attack_paths(self, graph_engine):
        """Test attack path detection"""
        # Create test data
        attacker_identity = {
            'id': 'arn:aws:iam::123456789012:user/attacker',
            'type': 'USER',
            'arn': 'arn:aws:iam::123456789012:user/attacker',
            'principal': 'arn:aws:iam::123456789012:user/attacker',
            'name': 'attacker',
            'cloud': CloudProvider.AWS.value,
            'created_at': datetime.utcnow().timestamp(),
            'last_activity': datetime.utcnow().timestamp(),
            'valid_from': datetime.utcnow().timestamp(),
            'valid_to': None
        }
        
        target_resource = {
            'id': 'arn:aws:s3:::sensitive-data',
            'type': 'aws:s3:bucket',
            'region': 'us-east-1',
            'account': '123456789012',
            'name': 'sensitive-data',
            'state': 'ACTIVE',
            'created_at': datetime.utcnow().timestamp(),
            'valid_from': datetime.utcnow().timestamp(),
            'valid_to': None
        }
        
        graph_engine.upsert_identity(attacker_identity)
        graph_engine.upsert_resource(target_resource)
        
        # Find attack paths
        paths = graph_engine.find_attack_paths(
            from_entity=attacker_identity['id'],
            to_entity=target_resource['id'],
            max_depth=3
        )
        assert paths is not None
        assert isinstance(paths, list)
    
    def test_detect_anomalous_access(self, graph_engine):
        """Test anomalous access detection"""
        # Create test data with normal patterns
        normal_principal = {
            'id': 'arn:aws:iam::123456789012:user/normal-user',
            'type': 'USER',
            'arn': 'arn:aws:iam::123456789012:user/normal-user',
            'principal': 'arn:aws:iam::123456789012:user/normal-user',
            'name': 'normal-user',
            'cloud': CloudProvider.AWS.value,
            'created_at': datetime.utcnow().timestamp(),
            'last_activity': datetime.utcnow().timestamp(),
            'valid_from': datetime.utcnow().timestamp(),
            'valid_to': None
        }
        
        resource = {
            'id': 'arn:aws:ec2:us-east-1:123456789012:instance/normal-instance',
            'type': 'aws:ec2:instance',
            'region': 'us-east-1',
            'account': '123456789012',
            'name': 'normal-instance',
            'state': 'running',
            'created_at': datetime.utcnow().timestamp(),
            'valid_from': datetime.utcnow().timestamp(),
            'valid_to': None
        }
        
        graph_engine.upsert_identity(normal_principal)
        graph_engine.upsert_resource(resource)
        
        # Create some normal events
        for i in range(5):
            event = {
                'id': f'normal-event-{i}',
                'cloud': CloudProvider.AWS.value,
                'event_type': 'API_CALL',
                'event_time': (datetime.utcnow() - timedelta(hours=i)).timestamp(),
                'operation': 'DescribeInstances',
                'principal_id': normal_principal['id'],
                'resource_id': resource['id'],
                'request_parameters': {},
                'response_elements': {},
                'source_ip': '192.168.1.100',
                'user_agent': 'aws-cli/2.0.0',
                'status': 'SUCCESS',
                'raw_event': {}
            }
            graph_engine.create_event_node(event)
        
        # Detect anomalies
        anomalies = graph_engine.detect_anomalous_access(
            principal_id=normal_principal['id'],
            time_window_hours=24
        )
        assert anomalies is not None
        assert isinstance(anomalies, list)
    
    def test_health_check(self, graph_engine):
        """Test health check functionality"""
        health = graph_engine.health_check()
        assert health is not None
        assert 'status' in health
        assert 'neo4j_connection' in health
        assert 'timestamp' in health
    
    def test_initialize_schema(self, graph_engine):
        """Test schema initialization"""
        # Initialize schema
        result = graph_engine.initialize_schema()
        assert result is True
        
        # Verify constraints exist
        with graph_engine.driver.session() as session:
            result = session.run("SHOW CONSTRAINTS")
            constraints = list(result)
            assert len(constraints) > 0
    
    def test_get_identity_permissions(self, graph_engine):
        """Test identity permissions retrieval"""
        identity = {
            'id': 'arn:aws:iam::123456789012:user/test-user',
            'type': 'USER',
            'arn': 'arn:aws:iam::123456789012:user/test-user',
            'principal': 'arn:aws:iam::123456789012:user/test-user',
            'name': 'test-user',
            'cloud': CloudProvider.AWS.value,
            'created_at': datetime.utcnow().timestamp(),
            'last_activity': datetime.utcnow().timestamp(),
            'valid_from': datetime.utcnow().timestamp(),
            'valid_to': None
        }
        
        graph_engine.upsert_identity(identity)
        
        # Get permissions
        permissions = graph_engine.get_identity_permissions(identity['id'])
        assert permissions is not None
        assert isinstance(permissions, list)
    
    def test_get_resource_dependencies(self, graph_engine, mock_aws_resources):
        """Test resource dependencies retrieval"""
        resource = mock_aws_resources[0]
        
        # Insert resource
        graph_engine.upsert_resource(resource)
        
        # Get dependencies
        dependencies = graph_engine.get_resource_dependencies(resource['id'])
        assert dependencies is not None
        assert isinstance(dependencies, list)
