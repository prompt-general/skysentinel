import pytest
import tempfile
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from graph_engine.service import GraphEngine
from shared.models.events import CloudProvider, NormalizedEvent, Principal, ResourceReference


@pytest.fixture(scope="session")
def neo4j_config():
    """Neo4j configuration for testing"""
    return {
        'uri': os.environ.get('NEO4J_TEST_URI', 'bolt://localhost:7687'),
        'username': os.environ.get('NEO4J_TEST_USER', 'neo4j'),
        'password': os.environ.get('NEO4J_TEST_PASSWORD', 'test_password')
    }


@pytest.fixture(scope="function")
def graph_engine(neo4j_config):
    """Graph engine instance for testing"""
    engine = GraphEngine(
        uri=neo4j_config['uri'],
        username=neo4j_config['username'],
        password=neo4j_config['password']
    )
    
    # Initialize schema
    engine.initialize_schema()
    
    yield engine
    
    # Cleanup: delete all nodes and relationships
    with engine.driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")


@pytest.fixture
def sample_principal():
    """Sample principal for testing"""
    return Principal(
        id="arn:aws:iam::123456789012:user/test-user",
        type="IAMUser",
        arn="arn:aws:iam::123456789012:user/test-user",
        name="test-user"
    )


@pytest.fixture
def sample_resource():
    """Sample resource for testing"""
    return ResourceReference(
        id="arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0",
        type="aws:ec2:instance",
        region="us-east-1",
        account="123456789012",
        name="test-instance"
    )


@pytest.fixture
def sample_event(sample_principal, sample_resource):
    """Sample event for testing"""
    from datetime import datetime
    return {
        'id': "test-event-123",
        'cloud': CloudProvider.AWS.value,
        'event_type': 'RESOURCE_CREATE',
        'event_time': datetime.utcnow().timestamp(),
        'operation': 'RunInstances',
        'principal_id': sample_principal.id,
        'resource_id': sample_resource.id,
        'request_parameters': {
            'instanceType': 't3.micro',
            'imageId': 'ami-12345678'
        },
        'response_elements': {
            'instances': [{
                'instanceId': 'i-1234567890abcdef0',
                'state': 'pending'
            }]
        },
        'source_ip': '192.168.1.100',
        'user_agent': 'aws-cli/2.0.0',
        'status': 'SUCCESS',
        'raw_event': {
            'eventVersion': '1.08',
            'userIdentity': {
                'type': 'IAMUser',
                'principalId': 'AIDACKCEVSQ6C2EXAMPLE',
                'arn': 'arn:aws:iam::123456789012:user/test-user'
            }
        }
    }


@pytest.fixture
def sample_aws_events():
    """Sample AWS events for testing"""
    from datetime import datetime
    return [
        {
            'id': 'evt-1',
            'cloud': CloudProvider.AWS.value,
            'event_type': 'RESOURCE_CREATE',
            'event_time': datetime.utcnow().timestamp(),
            'operation': 'CreateBucket',
            'principal_id': 'arn:aws:iam::123456789012:user/user1',
            'resource_id': 'arn:aws:s3:::test-bucket',
            'request_parameters': {'bucketName': 'test-bucket'},
            'response_elements': {'location': '/test-bucket'},
            'source_ip': '192.168.1.100',
            'user_agent': 'aws-cli/2.0.0',
            'status': 'SUCCESS',
            'raw_event': {'service': 's3'}
        },
        {
            'id': 'evt-2',
            'cloud': CloudProvider.AWS.value,
            'event_type': 'RESOURCE_MODIFY',
            'event_time': datetime.utcnow().timestamp(),
            'operation': 'ModifyInstanceAttribute',
            'principal_id': 'arn:aws:iam::123456789012:user/user2',
            'resource_id': 'arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0',
            'request_parameters': {'instanceType': 't3.small'},
            'response_elements': {'instance': {'instanceType': 't3.small'}},
            'source_ip': '192.168.1.101',
            'user_agent': 'aws-cli/2.0.0',
            'status': 'SUCCESS',
            'raw_event': {'service': 'ec2'}
        }
    ]


@pytest.fixture
def mock_aws_resources():
    """Mock AWS resources for testing"""
    return [
        {
            'id': 'i-1234567890abcdef0',
            'arn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0',
            'type': 'aws:ec2:instance',
            'region': 'us-east-1',
            'account': '123456789012',
            'name': 'web-server-1',
            'state': 'running',
            'properties': {
                'instance_type': 't3.micro',
                'vpc_id': 'vpc-12345678',
                'subnet_id': 'subnet-12345678'
            },
            'tags': {'Environment': 'test', 'Application': 'skysentinel'}
        },
        {
            'id': 'arn:aws:s3:::test-bucket',
            'arn': 'arn:aws:s3:::test-bucket',
            'type': 'aws:s3:bucket',
            'region': 'us-east-1',
            'account': '123456789012',
            'name': 'test-bucket',
            'state': 'ACTIVE',
            'properties': {
                'versioning': 'Enabled',
                'encryption_enabled': True,
                'public_read': False
            },
            'tags': {'Environment': 'test'}
        }
    ]


@pytest.fixture
def temp_config_file():
    """Temporary configuration file for testing"""
    import tempfile
    import yaml
    
    config_data = {
        'neo4j': {
            'uri': 'bolt://localhost:7687',
            'username': 'neo4j',
            'password': 'test_password'
        },
        'logging': {
            'level': 'DEBUG',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_file = f.name
    
    yield temp_file
    
    # Cleanup
    os.unlink(temp_file)


@pytest.fixture
def mock_cloudtrail_event():
    """Mock CloudTrail event for testing"""
    return {
        'eventVersion': '1.08',
        'userIdentity': {
            'type': 'IAMUser',
            'principalId': 'AIDACKCEVSQ6C2EXAMPLE',
            'arn': 'arn:aws:iam::123456789012:user/test-user',
            'accountId': '123456789012',
            'accessKeyId': 'AKIAIOSFODNN7EXAMPLE',
            'userName': 'test-user'
        },
        'eventTime': '2023-01-01T12:00:00Z',
        'eventSource': 'ec2.amazonaws.com',
        'eventName': 'RunInstances',
        'awsRegion': 'us-east-1',
        'sourceIPAddress': '192.168.1.100',
        'userAgent': 'aws-cli/2.0.0 Python/3.9.0',
        'requestParameters': {
            'instancesSet': {
                'items': [{
                    'imageId': 'ami-12345678',
                    'instanceType': 't3.micro',
                    'minCount': 1,
                    'maxCount': 1
                }]
            }
        },
        'responseElements': {
            'instancesSet': {
                'items': [{
                    'instanceId': 'i-1234567890abcdef0',
                    'imageId': 'ami-12345678',
                    'state': {
                        'name': 'pending'
                    }
                }]
            }
        },
        'requestID': '12345678-1234-1234-1234-123456789012',
        'eventID': '87654321-4321-4321-4321-210987654321',
        'eventType': 'AwsApiCall',
        'recipientAccountId': '123456789012'
    }


@pytest.fixture
def mock_security_event():
    """Mock security event for testing"""
    return {
        'id': 'security-event-123',
        'cloud': CloudProvider.AWS.value,
        'event_type': 'SECURITY_ALERT',
        'event_time': datetime.utcnow().timestamp(),
        'operation': 'UnauthorizedAccess',
        'principal_id': 'arn:aws:iam::123456789012:user/attacker',
        'resource_id': 'arn:aws:s3:::sensitive-bucket',
        'request_parameters': {
            'bucketName': 'sensitive-bucket',
            'objectKey': 'secret-data.txt'
        },
        'response_elements': {},
        'source_ip': '203.0.113.1',
        'user_agent': 'curl/7.68.0',
        'status': 'FAILED',
        'raw_event': {
            'service': 'guardduty',
            'severity': 'HIGH',
            'title': 'Unauthorized S3 Access Attempt'
        }
    }
