import json
import os
import boto3
import logging
from datetime import datetime
from botocore.exceptions import ClientError

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Neo4j connection details
NEO4J_URI = os.environ.get('NEO4J_URI')
NEO4J_USERNAME_SECRET = os.environ.get('NEO4J_USERNAME_SECRET')
S3_BUCKET = os.environ.get('S3_BUCKET')
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

def get_neo4j_credentials():
    """Retrieve Neo4j credentials from Secrets Manager"""
    try:
        client = boto3.client('secretsmanager')
        response = client.get_secret_value(SecretId=NEO4J_USERNAME_SECRET)
        secret_data = json.loads(response['SecretString'])
        return secret_data
    except Exception as e:
        logger.error(f"Failed to retrieve Neo4j credentials: {e}")
        raise

def store_raw_event(event_data):
    """Store raw event in S3 for archival"""
    try:
        s3 = boto3.client('s3')
        event_id = event_data.get('event_id', 'unknown')
        timestamp = datetime.utcnow().isoformat()
        
        key = f"raw-events/{timestamp[:10]}/{event_id}.json"
        
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=json.dumps(event_data, default=str),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        
        logger.info(f"Stored raw event {event_id} to S3")
        
    except Exception as e:
        logger.error(f"Failed to store event in S3: {e}")

def process_cloudtrail_event(event_data):
    """Process CloudTrail event"""
    try:
        # Extract relevant information
        event_name = event_data.get('event_name', '')
        principal = event_data.get('principal', '')
        aws_account = event_data.get('aws_account', '')
        aws_region = event_data.get('aws_region', '')
        
        # Create normalized event for Neo4j
        normalized_event = {
            'id': event_data.get('event_id', ''),
            'cloud': 'aws',
            'event_type': determine_event_type(event_name),
            'event_time': event_data.get('timestamp', ''),
            'operation': event_name,
            'principal': {
                'id': principal,
                'type': extract_principal_type(principal),
                'arn': principal
            },
            'resource': extract_resource_from_event(event_data),
            'request_parameters': event_data.get('request_parameters', {}),
            'response_elements': event_data.get('response_elements', {}),
            'source_ip': event_data.get('source_ip'),
            'user_agent': event_data.get('user_agent'),
            'error': event_data.get('error_message'),
            'status': 'FAILED' if event_data.get('error_code') else 'SUCCESS',
            'raw_event': event_data
        }
        
        # Store in Neo4j (implementation would go here)
        logger.info(f"Processed CloudTrail event: {event_name} by {principal}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to process CloudTrail event: {e}")
        return False

def process_security_event(event_data):
    """Process security event (GuardDuty, Security Hub)"""
    try:
        event_name = event_data.get('event_name', '')
        severity = event_data.get('severity', 'MEDIUM')
        title = event_data.get('title', '')
        
        # Create normalized security event
        normalized_event = {
            'id': event_data.get('event_id', ''),
            'cloud': 'aws',
            'event_type': 'SECURITY_ALERT',
            'event_time': event_data.get('timestamp', ''),
            'operation': event_name,
            'principal': {
                'id': event_data.get('principal', ''),
                'type': 'SECURITY_SERVICE',
                'arn': event_data.get('principal', '')
            },
            'resource': {
                'id': f"security-alert-{event_data.get('event_id', '')}",
                'type': 'aws:security:alert',
                'region': event_data.get('aws_region', ''),
                'account': event_data.get('aws_account', ''),
                'name': title
            },
            'request_parameters': {
                'severity': severity,
                'service': event_data.get('service', ''),
                'description': event_data.get('description', '')
            },
            'response_elements': {},
            'source_ip': None,
            'user_agent': None,
            'error': None,
            'status': 'ALERT',
            'raw_event': event_data
        }
        
        # Store in Neo4j (implementation would go here)
        logger.info(f"Processed security event: {title} ({severity})")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to process security event: {e}")
        return False

def determine_event_type(event_name):
    """Determine normalized event type from AWS event name"""
    if event_name.startswith('Create'):
        return 'RESOURCE_CREATE'
    elif event_name.startswith('Delete'):
        return 'RESOURCE_DELETE'
    elif event_name.startswith('Modify'):
        return 'RESOURCE_MODIFY'
    elif event_name.startswith('Attach'):
        return 'PERMISSION_MODIFY'
    elif event_name.startswith('Detach'):
        return 'PERMISSION_MODIFY'
    elif event_name in ['RunInstances', 'StartInstances']:
        return 'COMPUTE_START'
    elif event_name in ['StopInstances', 'TerminateInstances']:
        return 'COMPUTE_STOP'
    else:
        return 'API_CALL'

def extract_principal_type(principal_arn):
    """Extract principal type from ARN"""
    if not principal_arn:
        return 'UNKNOWN'
    
    if ':user/' in principal_arn:
        return 'IAMUser'
    elif ':role/' in principal_arn:
        return 'IAMRole'
    elif ':assumed-role/' in principal_arn:
        return 'AssumedRole'
    else:
        return 'Service'

def extract_resource_from_event(event_data):
    """Extract resource information from event data"""
    request_params = event_data.get('request_parameters', {})
    
    # Try to extract resource from request parameters
    if 'bucketName' in request_params:
        return {
            'id': f"arn:aws:s3:::{request_params['bucketName']}",
            'type': 'aws:s3:bucket',
            'region': event_data.get('aws_region', ''),
            'account': event_data.get('aws_account', ''),
            'name': request_params['bucketName']
        }
    elif 'instanceId' in request_params:
        return {
            'id': request_params['instanceId'],
            'type': 'aws:ec2:instance',
            'region': event_data.get('aws_region', ''),
            'account': event_data.get('aws_account', ''),
            'name': request_params['instanceId']
        }
    elif 'userName' in request_params:
        return {
            'id': f"arn:aws:iam::{event_data.get('aws_account', '')}:user/{request_params['userName']}",
            'type': 'aws:iam:user',
            'region': None,
            'account': event_data.get('aws_account', ''),
            'name': request_params['userName']
        }
    elif 'roleName' in request_params:
        return {
            'id': f"arn:aws:iam::{event_data.get('aws_account', '')}:role/{request_params['roleName']}",
            'type': 'aws:iam:role',
            'region': None,
            'account': event_data.get('aws_account', ''),
            'name': request_params['roleName']
        }
    else:
        return {
            'id': f"unknown-resource-{event_data.get('event_id', '')}",
            'type': 'aws:unknown',
            'region': event_data.get('aws_region', ''),
            'account': event_data.get('aws_account', ''),
            'name': 'Unknown'
        }

def lambda_handler(event, context):
    """Main Lambda handler"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Store raw event in S3
        store_raw_event(event)
        
        # Determine event type and process accordingly
        event_type = event.get('event_type', '')
        
        if event_type == 'cloudtrail':
            success = process_cloudtrail_event(event)
        elif event_type == 'security':
            success = process_security_event(event)
        else:
            logger.warning(f"Unknown event type: {event_type}")
            success = False
        
        if success:
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Event processed successfully'})
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({'message': 'Failed to process event'})
            }
            
    except Exception as e:
        logger.error(f"Lambda handler error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': f'Error: {str(e)}'})
        }
