import boto3
import json
import time
import logging
from typing import Dict, Any, Generator, Optional
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError

from shared.models.events import NormalizedEvent, PrincipalInfo, ResourceInfo


class AWSEventCollector:
    """AWS Event Collector for CloudTrail and EventBridge events"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize AWS clients
        try:
            self.session = boto3.Session(
                aws_access_key_id=config.get('credentials', {}).get('access_key_id'),
                aws_secret_access_key=config.get('credentials', {}).get('secret_access_key'),
                aws_session_token=config.get('credentials', {}).get('session_token'),
                region_name=config.get('region', 'us-east-1')
            )
            
            self.eventbridge = self.session.client('events')
            self.cloudtrail = self.session.client('cloudtrail')
            self.sts = self.session.client('sts')
            
            # Verify credentials
            self.sts.get_caller_identity()
            
        except NoCredentialsError:
            raise ValueError("AWS credentials not found or invalid")
        except ClientError as e:
            raise ValueError(f"AWS client initialization failed: {e}")
    
    def normalize_event(self, raw_event: Dict) -> NormalizedEvent:
        """Convert AWS event to normalized schema"""
        try:
            detail = raw_event.get('detail', {})
            user_identity = detail.get('userIdentity', {})
            
            # Extract principal information
            principal = PrincipalInfo(
                id=user_identity.get('arn', ''),
                type=user_identity.get('type', ''),
                name=user_identity.get('userName', user_identity.get('principalId', '')),
                session_context=user_identity.get('sessionContext')
            )
            
            # Extract resource information
            resource = self._extract_resource_info(raw_event)
            
            # Determine event status
            error_code = detail.get('errorCode')
            status = "FAILED" if error_code else "SUCCESS"
            
            return NormalizedEvent(
                id=raw_event.get('id', ''),
                cloud='aws',
                event_type=self._determine_event_type(raw_event),
                event_time=datetime.fromisoformat(raw_event.get('time', '').replace('Z', '+00:00')),
                operation=detail.get('eventName', ''),
                principal=principal,
                resource=resource,
                request_parameters=detail.get('requestParameters', {}),
                response_elements=detail.get('responseElements', {}),
                source_ip=detail.get('sourceIPAddress'),
                user_agent=detail.get('userAgent'),
                error=error_code,
                status=status,
                raw_event=raw_event
            )
        except Exception as e:
            self.logger.error(f"Failed to normalize event: {e}")
            raise
    
    def stream_events(self) -> Generator[NormalizedEvent, None, None]:
        """Stream events from AWS EventBridge/CloudTrail"""
        try:
            # Set up EventBridge rule if it doesn't exist
            self._setup_eventbridge_rule()
            
            # Start streaming events
            self.logger.info("Starting AWS event stream...")
            
            while True:
                try:
                    events = self._poll_events()
                    for event in events:
                        try:
                            normalized_event = self.normalize_event(event)
                            yield normalized_event
                        except Exception as e:
                            self.logger.error(f"Failed to normalize event {event.get('id', 'unknown')}: {e}")
                            continue
                    
                    # Wait before next poll
                    time.sleep(self.config.get('poll_interval', 30))
                    
                except ClientError as e:
                    self.logger.error(f"AWS API error during polling: {e}")
                    time.sleep(60)  # Wait longer on API errors
                except Exception as e:
                    self.logger.error(f"Unexpected error during polling: {e}")
                    time.sleep(30)
                    
        except KeyboardInterrupt:
            self.logger.info("Event streaming stopped by user")
        except Exception as e:
            self.logger.error(f"Fatal error in event streaming: {e}")
            raise
    
    def _setup_eventbridge_rule(self) -> None:
        """Set up EventBridge rule for security events"""
        try:
            rule_name = 'skysentinel-collector'
            
            # Check if rule exists
            try:
                self.eventbridge.describe_rule(Name=rule_name)
                self.logger.debug(f"EventBridge rule {rule_name} already exists")
            except self.eventbridge.exceptions.ResourceNotFoundException:
                # Create the rule
                event_pattern = {
                    'source': ['aws.ec2', 'aws.s3', 'aws.iam', 'aws.rds', 'aws.lambda'],
                    'detail-type': ['AWS API Call via CloudTrail'],
                    'detail': {
                        'eventSource': [
                            'ec2.amazonaws.com',
                            's3.amazonaws.com',
                            'iam.amazonaws.com',
                            'rds.amazonaws.com',
                            'lambda.amazonaws.com'
                        ]
                    }
                }
                
                self.eventbridge.put_rule(
                    Name=rule_name,
                    EventPattern=json.dumps(event_pattern),
                    State='ENABLED',
                    Description='SkySentinel security event collection rule'
                )
                
                self.logger.info(f"Created EventBridge rule: {rule_name}")
                
        except ClientError as e:
            self.logger.warning(f"Failed to setup EventBridge rule: {e}")
    
    def _poll_events(self) -> list[Dict]:
        """Poll for recent CloudTrail events"""
        try:
            # Get events from the last poll interval
            end_time = datetime.utcnow()
            start_time = end_time.timestamp() - (self.config.get('poll_interval', 30) * 2)  # 2x interval for overlap
            
            response = self.cloudtrail.lookup_events(
                LookupAttributes=[
                    {'AttributeKey': 'EventName', 'AttributeValue': ''}
                ],
                StartTime=start_time,
                EndTime=end_time,
                MaxResults=self.config.get('batch_size', 100)
            )
            
            events = response.get('Events', [])
            
            # Process CloudTrail events to EventBridge format
            processed_events = []
            for event in events:
                # Convert CloudTrail event to EventBridge format
                event_bridge_event = {
                    'id': event.get('EventId', ''),
                    'time': event.get('EventTime', ''),
                    'detail': json.loads(event.get('CloudTrailEvent', '{}')),
                    'source': 'aws.cloudtrail',
                    'detail-type': 'AWS API Call via CloudTrail'
                }
                processed_events.append(event_bridge_event)
            
            self.logger.debug(f"Polled {len(processed_events)} events")
            return processed_events
            
        except ClientError as e:
            self.logger.error(f"Failed to poll CloudTrail events: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error in _poll_events: {e}")
            return []
    
    def _determine_event_type(self, event: Dict) -> str:
        """Determine normalized event type from AWS event"""
        detail = event.get('detail', {})
        event_name = detail.get('eventName', '')
        event_source = detail.get('eventSource', '')
        
        # Map AWS events to normalized types
        if event_source == 'ec2.amazonaws.com':
            if event_name.startswith('Run') or event_name.startswith('Start'):
                return 'COMPUTE_START'
            elif event_name.startswith('Stop') or event_name.startswith('Terminate'):
                return 'COMPUTE_STOP'
            elif event_name in ['AuthorizeSecurityGroupIngress', 'AuthorizeSecurityGroupEgress']:
                return 'NETWORK_MODIFY'
        elif event_source == 's3.amazonaws.com':
            if event_name in ['PutObject', 'GetObject']:
                return 'DATA_ACCESS'
            elif event_name == 'CreateBucket':
                return 'RESOURCE_CREATE'
            elif event_name == 'DeleteBucket':
                return 'RESOURCE_DELETE'
        elif event_source == 'iam.amazonaws.com':
            if event_name.startswith('Create'):
                return 'IDENTITY_CREATE'
            elif event_name.startswith('Delete'):
                return 'IDENTITY_DELETE'
            elif event_name.startswith('Attach') or event_name.startswith('Detach'):
                return 'PERMISSION_MODIFY'
        elif event_source == 'rds.amazonaws.com':
            if event_name.startswith('Create'):
                return 'DATABASE_CREATE'
            elif event_name.startswith('Delete'):
                return 'DATABASE_DELETE'
        
        # Default to API call type
        return 'API_CALL'
    
    def _extract_resource_info(self, event: Dict) -> ResourceInfo:
        """Extract resource information from AWS event"""
        detail = event.get('detail', {})
        
        # Try to extract from resources array
        resources = detail.get('resources', [])
        if resources:
            resource_arn = resources[0].get('ARN', '')
            if resource_arn:
                return self._parse_arn(resource_arn)
        
        # Try to extract from request parameters
        request_params = detail.get('requestParameters', {})
        
        # Handle different AWS services
        event_source = detail.get('eventSource', '')
        
        if event_source == 's3.amazonaws.com':
            bucket_name = request_params.get('bucketName')
            if bucket_name:
                arn = f"arn:aws:s3:::{bucket_name}"
                return self._parse_arn(arn)
        
        elif event_source == 'ec2.amazonaws.com':
            instance_id = request_params.get('instanceId')
            if instance_id:
                arn = f"arn:aws:ec2:{self.config.get('region', 'us-east-1')}:{self._get_account_id()}:instance/{instance_id}"
                return self._parse_arn(arn)
        
        elif event_source == 'iam.amazonaws.com':
            user_name = request_params.get('userName')
            role_name = request_params.get('roleName')
            if user_name:
                arn = f"arn:aws:iam::{self._get_account_id()}:user/{user_name}"
                return self._parse_arn(arn)
            elif role_name:
                arn = f"arn:aws:iam::{self._get_account_id()}:role/{role_name}"
                return self._parse_arn(arn)
        
        # Fallback to minimal resource info
        return ResourceInfo(
            id='',
            type=event_source.replace('.amazonaws.com', ''),
            region=self.config.get('region'),
            account=self._get_account_id()
        )
    
    def _parse_arn(self, arn: str) -> ResourceInfo:
        """Parse AWS ARN into ResourceInfo"""
        try:
            parts = arn.split(':')
            if len(parts) >= 6:
                resource_type = parts[5].split('/')[0]
                return ResourceInfo(
                    id=arn,
                    type=f"aws:{parts[2]}:{resource_type}",
                    region=parts[3] if parts[3] != '' else None,
                    account=parts[4] if parts[4] != '' else None
                )
        except Exception as e:
            self.logger.warning(f"Failed to parse ARN {arn}: {e}")
        
        return ResourceInfo(id=arn, type='unknown')
    
    def _get_account_id(self) -> str:
        """Get AWS account ID"""
        try:
            if not hasattr(self, '_account_id'):
                response = self.sts.get_caller_identity()
                self._account_id = response.get('Account', '')
            return self._account_id
        except ClientError as e:
            self.logger.error(f"Failed to get account ID: {e}")
            return ''
    
    def get_supported_services(self) -> list[str]:
        """Get list of supported AWS services"""
        return [
            'ec2',
            's3', 
            'iam',
            'rds',
            'lambda',
            'cloudtrail',
            'eventbridge'
        ]
    
    def test_connection(self) -> bool:
        """Test AWS connection and permissions"""
        try:
            # Test basic AWS connectivity
            self.sts.get_caller_identity()
            
            # Test CloudTrail access
            self.cloudtrail.lookup_events(MaxResults=1)
            
            # Test EventBridge access
            self.eventbridge.list_rules()
            
            self.logger.info("AWS connection test successful")
            return True
            
        except Exception as e:
            self.logger.error(f"AWS connection test failed: {e}")
            return False
