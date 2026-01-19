import json
from datetime import datetime, timedelta
import random
import uuid
from typing import Dict, List, Any
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models.events import CloudProvider, Principal, ResourceReference


class TestDataGenerator:
    """Generate realistic test data for SkySentinel testing"""
    
    def __init__(self, seed: int = None):
        if seed:
            random.seed(seed)
        
        # AWS event patterns
        self.aws_events = {
            'EC2': [
                'RunInstances', 'StopInstances', 'StartInstances', 'TerminateInstances',
                'ModifyInstanceAttribute', 'CreateImage', 'RebootInstances',
                'DescribeInstances', 'AssociateIamInstanceProfile'
            ],
            'S3': [
                'CreateBucket', 'DeleteBucket', 'PutObject', 'GetObject',
                'DeleteObject', 'ListBucket', 'GetBucketVersioning',
                'PutBucketAcl', 'GetBucketAcl'
            ],
            'IAM': [
                'CreateUser', 'DeleteUser', 'CreateRole', 'DeleteRole',
                'AttachUserPolicy', 'DetachUserPolicy', 'CreatePolicy',
                'DeletePolicy', 'AddUserToGroup', 'RemoveUserFromGroup'
            ],
            'RDS': [
                'CreateDBInstance', 'DeleteDBInstance', 'ModifyDBInstance',
                'StartDBInstance', 'StopDBInstance', 'CreateDBSnapshot',
                'DeleteDBSnapshot', 'RestoreDBInstanceFromDBSnapshot'
            ],
            'Lambda': [
                'CreateFunction', 'DeleteFunction', 'UpdateFunctionCode',
                'InvokeFunction', 'CreateEventSourceMapping', 'DeleteEventSourceMapping'
            ]
        }
        
        # Azure event patterns
        self.azure_events = [
            'Microsoft.Compute/virtualMachines/write',
            'Microsoft.Compute/virtualMachines/delete',
            'Microsoft.Storage/storageAccounts/write',
            'Microsoft.Storage/storageAccounts/delete',
            'Microsoft.Network/networkSecurityGroups/write',
            'Microsoft.Sql/servers/databases/write',
            'Microsoft.Sql/servers/databases/delete'
        ]
        
        # GCP event patterns
        self.gcp_events = [
            'compute.instances.insert',
            'compute.instances.delete',
            'compute.instances.start',
            'compute.instances.stop',
            'storage.buckets.create',
            'storage.buckets.delete',
            'storage.objects.create',
            'storage.objects.delete',
            'iam.serviceAccounts.create',
            'iam.serviceAccounts.delete'
        ]
        
        # Mock principals
        self.principals = {
            'aws': [
                {
                    'id': 'arn:aws:iam::123456789012:user/alice',
                    'type': 'IAMUser',
                    'name': 'alice',
                    'department': 'engineering'
                },
                {
                    'id': 'arn:aws:iam::123456789012:user/bob',
                    'type': 'IAMUser',
                    'name': 'bob',
                    'department': 'security'
                },
                {
                    'id': 'arn:aws:iam::123456789012:role/AdminRole',
                    'type': 'IAMRole',
                    'name': 'AdminRole',
                    'department': 'it'
                },
                {
                    'id': 'arn:aws:iam::123456789012:role/DeveloperRole',
                    'type': 'IAMRole',
                    'name': 'DeveloperRole',
                    'department': 'engineering'
                }
            ],
            'azure': [
                {
                    'id': 'alice@company.com',
                    'type': 'User',
                    'name': 'alice',
                    'department': 'engineering'
                },
                {
                    'id': 'bob@company.com',
                    'type': 'User',
                    'name': 'bob',
                    'department': 'security'
                }
            ],
            'gcp': [
                {
                    'id': 'alice@company.iam.gserviceaccount.com',
                    'type': 'ServiceAccount',
                    'name': 'alice',
                    'department': 'engineering'
                }
            ]
        }
        
        # Resource templates
        self.resource_templates = {
            'aws': {
                'ec2:instance': {
                    'id_template': 'arn:aws:ec2:{region}:{account}:instance/i-{instance_id}',
                    'properties': {
                        'instance_type': ['t3.micro', 't3.small', 't3.medium', 'm5.large'],
                        'vpc_id': 'vpc-{vpc_id}',
                        'subnet_id': 'subnet-{subnet_id}',
                        'security_groups': ['sg-{sg_id}']
                    }
                },
                's3:bucket': {
                    'id_template': 'arn:aws:s3:::{bucket_name}',
                    'properties': {
                        'versioning': ['Enabled', 'Disabled'],
                        'encryption': ['AES256', 'aws:kms'],
                        'public_read': [True, False]
                    }
                },
                'iam:user': {
                    'id_template': 'arn:aws:iam::{account}:user/{username}',
                    'properties': {
                        'create_date': 'timestamp',
                        'password_last_used': 'timestamp'
                    }
                },
                'iam:role': {
                    'id_template': 'arn:aws:iam::{account}:role/{role_name}',
                    'properties': {
                        'max_session_duration': [3600, 7200, 43200],
                        'path': ['/']
                    }
                },
                'rds:instance': {
                    'id_template': 'arn:aws:rds:{region}:{account}:db:{db_identifier}',
                    'properties': {
                        'engine': ['mysql', 'postgres', 'mariadb'],
                        'instance_class': ['db.t3.micro', 'db.t3.small', 'db.t3.medium'],
                        'storage_size': [20, 50, 100, 200],
                        'multi_az': [True, False]
                    }
                },
                'lambda:function': {
                    'id_template': 'arn:aws:lambda:{region}:{account}:function:{function_name}',
                    'properties': {
                        'runtime': ['python3.9', 'nodejs18.x', 'go1.x'],
                        'timeout': [30, 60, 300],
                        'memory_size': [128, 256, 512, 1024]
                    }
                }
            }
        }
    
    def generate_cloud_event(self, cloud_provider: str = "aws") -> Dict[str, Any]:
        """Generate a realistic cloud event"""
        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow() - timedelta(minutes=random.randint(0, 1440))
        
        if cloud_provider.lower() == "aws":
            return self._generate_aws_event(event_id, timestamp)
        elif cloud_provider.lower() == "azure":
            return self._generate_azure_event(event_id, timestamp)
        elif cloud_provider.lower() == "gcp":
            return self._generate_gcp_event(event_id, timestamp)
        else:
            raise ValueError(f"Unsupported cloud provider: {cloud_provider}")
    
    def _generate_aws_event(self, event_id: str, timestamp: datetime) -> Dict[str, Any]:
        """Generate AWS event"""
        service = random.choice(list(self.aws_events.keys()))
        operation = random.choice(self.aws_events[service])
        principal = random.choice(self.principals['aws'])
        
        # Determine event type
        event_type = self._classify_aws_event(operation)
        
        # Generate resource
        resource = self._generate_aws_resource(service, timestamp)
        
        # Generate source IP (corporate vs external)
        if random.random() < 0.7:  # 70% corporate IP
            source_ip = f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        else:  # 30% external IP
            source_ip = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,254)}"
        
        event = {
            'id': event_id,
            'cloud': CloudProvider.AWS.value,
            'event_type': event_type,
            'event_time': timestamp.timestamp(),
            'operation': operation,
            'principal_id': principal['id'],
            'resource_id': resource['id'],
            'request_parameters': self._generate_request_params(service, operation, resource),
            'response_elements': self._generate_response_params(service, operation, resource),
            'source_ip': source_ip,
            'user_agent': random.choice([
                'aws-cli/2.0.0 Python/3.9.0',
                'aws-cli/1.27.0 Python/3.8.0',
                'console.amazonaws.com',
                'Terraform/1.0.0',
                'boto3/1.26.0 Python/3.9.0'
            ]),
            'status': 'SUCCESS' if random.random() < 0.95 else 'FAILED',
            'raw_event': {
                'eventVersion': '1.08',
                'userIdentity': {
                    'type': principal['type'],
                    'principalId': principal['id'].split('/')[-1],
                    'arn': principal['id']
                },
                'eventSource': f"{service.lower()}.amazonaws.com",
                'awsRegion': resource.get('region', 'us-east-1'),
                'recipientAccountId': '123456789012'
            }
        }
        
        return event
    
    def _generate_azure_event(self, event_id: str, timestamp: datetime) -> Dict[str, Any]:
        """Generate Azure event"""
        operation = random.choice(self.azure_events)
        principal = random.choice(self.principals['azure'])
        
        resource = self._generate_azure_resource(operation, timestamp)
        
        event = {
            'id': event_id,
            'cloud': CloudProvider.AZURE.value,
            'event_type': 'API_CALL',
            'event_time': timestamp.timestamp(),
            'operation': operation,
            'principal_id': principal['id'],
            'resource_id': resource['id'],
            'request_parameters': {},
            'response_elements': {},
            'source_ip': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,254)}",
            'user_agent': 'Azure-CLI/2.0.0',
            'status': 'SUCCESS',
            'raw_event': {
                'category': 'Administrative',
                'operationName': operation,
                'resourceType': resource['type'],
                'resourceGroupName': resource.get('resource_group', 'skysentinel-rg')
            }
        }
        
        return event
    
    def _generate_gcp_event(self, event_id: str, timestamp: datetime) -> Dict[str, Any]:
        """Generate GCP event"""
        operation = random.choice(self.gcp_events)
        principal = random.choice(self.principals['gcp'])
        
        resource = self._generate_gcp_resource(operation, timestamp)
        
        event = {
            'id': event_id,
            'cloud': CloudProvider.GCP.value,
            'event_type': 'API_CALL',
            'event_time': timestamp.timestamp(),
            'operation': operation,
            'principal_id': principal['id'],
            'resource_id': resource['id'],
            'request_parameters': {},
            'response_elements': {},
            'source_ip': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,254)}",
            'user_agent': 'gcloud/400.0.0',
            'status': 'SUCCESS',
            'raw_event': {
                'protoPayload': {
                    'methodName': operation,
                    'resourceName': resource['id']
                }
            }
        }
        
        return event
    
    def _classify_aws_event(self, operation: str) -> str:
        """Classify AWS event type"""
        if operation.startswith('Create'):
            return 'RESOURCE_CREATE'
        elif operation.startswith('Delete'):
            return 'RESOURCE_DELETE'
        elif operation.startswith('Modify'):
            return 'RESOURCE_MODIFY'
        elif operation in ['RunInstances', 'StartInstances']:
            return 'COMPUTE_START'
        elif operation in ['StopInstances', 'TerminateInstances']:
            return 'COMPUTE_STOP'
        elif operation.startswith('Attach') or operation.startswith('Detach'):
            return 'PERMISSION_MODIFY'
        elif operation.startswith('Describe') or operation.startswith('List'):
            return 'RESOURCE_READ'
        else:
            return 'API_CALL'
    
    def _generate_aws_resource(self, service: str, timestamp: datetime) -> Dict[str, Any]:
        """Generate AWS resource"""
        resource_type = f"aws:{service.lower()}:"
        
        if service == 'EC2':
            resource_type += 'instance'
            template = self.resource_templates['aws']['ec2:instance']
        elif service == 'S3':
            resource_type += 'bucket'
            template = self.resource_templates['aws']['s3:bucket']
        elif service == 'IAM':
            if random.random() < 0.5:
                resource_type += 'user'
                template = self.resource_templates['aws']['iam:user']
            else:
                resource_type += 'role'
                template = self.resource_templates['aws']['iam:role']
        elif service == 'RDS':
            resource_type += 'instance'
            template = self.resource_templates['aws']['rds:instance']
        elif service == 'Lambda':
            resource_type += 'function'
            template = self.resource_templates['aws']['lambda:function']
        else:
            resource_type += 'unknown'
            template = {'id_template': 'arn:aws:unknown:::unknown-{id}'}
        
        return self._build_resource_from_template(template, resource_type, timestamp)
    
    def _generate_azure_resource(self, operation: str, timestamp: datetime) -> Dict[str, Any]:
        """Generate Azure resource"""
        if 'virtualMachines' in operation:
            return {
                'id': f"/subscriptions/{random.randint(10000000,99999999)}/resourceGroups/skysentinel-rg/providers/Microsoft.Compute/virtualMachines/vm-{random.randint(1000,9999)}",
                'type': 'Microsoft.Compute/virtualMachines',
                'region': 'eastus',
                'resource_group': 'skysentinel-rg',
                'name': f'vm-{random.randint(1000,9999)}',
                'state': random.choice(['Running', 'Stopped', 'Deallocated']),
                'created_at': timestamp.timestamp()
            }
        elif 'storageAccounts' in operation:
            return {
                'id': f"/subscriptions/{random.randint(10000000,99999999)}/resourceGroups/skysentinel-rg/providers/Microsoft.Storage/storageAccounts/st{random.randint(1000,9999)}",
                'type': 'Microsoft.Storage/storageAccounts',
                'region': 'eastus',
                'resource_group': 'skysentinel-rg',
                'name': f'st{random.randint(1000,9999)}',
                'state': 'ACTIVE',
                'created_at': timestamp.timestamp()
            }
        else:
            return {
                'id': f"/subscriptions/{random.randint(10000000,99999999)}/resourceGroups/skysentinel-rg/providers/Unknown/resource-{random.randint(1000,9999)}",
                'type': 'Unknown',
                'region': 'eastus',
                'resource_group': 'skysentinel-rg',
                'name': f'unknown-{random.randint(1000,9999)}',
                'state': 'ACTIVE',
                'created_at': timestamp.timestamp()
            }
    
    def _generate_gcp_resource(self, operation: str, timestamp: datetime) -> Dict[str, Any]:
        """Generate GCP resource"""
        project_id = 'skysentinel-project'
        
        if 'compute.instances' in operation:
            return {
                'id': f"projects/{project_id}/zones/us-central1-a/instances/instance-{random.randint(1000,9999)}",
                'type': 'compute.instances',
                'region': 'us-central1',
                'project': project_id,
                'name': f'instance-{random.randint(1000,9999)}',
                'state': random.choice(['RUNNING', 'STOPPED', 'TERMINATED']),
                'created_at': timestamp.timestamp()
            }
        elif 'storage.buckets' in operation:
            return {
                'id': f"projects/{project_id}/buckets/bucket-{random.randint(1000,9999)}",
                'type': 'storage.buckets',
                'region': 'us-central1',
                'project': project_id,
                'name': f'bucket-{random.randint(1000,9999)}',
                'state': 'ACTIVE',
                'created_at': timestamp.timestamp()
            }
        else:
            return {
                'id': f"projects/{project_id}/unknown/resource-{random.randint(1000,9999)}",
                'type': 'unknown',
                'region': 'us-central1',
                'project': project_id,
                'name': f'unknown-{random.randint(1000,9999)}',
                'state': 'ACTIVE',
                'created_at': timestamp.timestamp()
            }
    
    def _build_resource_from_template(self, template: Dict, resource_type: str, timestamp: datetime) -> Dict[str, Any]:
        """Build resource from template"""
        id_template = template['id_template']
        properties = template.get('properties', {})
        
        # Generate ID
        resource_id = id_template.format(
            region='us-east-1',
            account='123456789012',
            instance_id=f"{random.randint(1000000000000000000, 9999999999999999999)}",
            bucket_name=f"skysentinel-bucket-{random.randint(1000,9999)}",
            username=f"user-{random.randint(100,999)}",
            role_name=f"role-{random.randint(100,999)}",
            db_identifier=f"skysentinel-db-{random.randint(100,999)}",
            function_name=f"lambda-{random.randint(100,999)}",
            vpc_id=f"vpc-{random.randint(10000000, 99999999)}",
            subnet_id=f"subnet-{random.randint(10000000, 99999999)}",
            sg_id=f"sg-{random.randint(10000000, 99999999)}"
        )
        
        # Generate properties
        resource_properties = {}
        for key, value in properties.items():
            if isinstance(value, list):
                resource_properties[key] = random.choice(value)
            elif value == 'timestamp':
                resource_properties[key] = timestamp.timestamp()
            else:
                resource_properties[key] = value
        
        return {
            'id': resource_id,
            'arn': resource_id,
            'type': resource_type,
            'region': 'us-east-1',
            'account': '123456789012',
            'name': resource_id.split('/')[-1],
            'state': random.choice(['ACTIVE', 'RUNNING', 'STOPPED', 'TERMINATED']),
            'created_at': timestamp.timestamp(),
            'properties': resource_properties,
            'tags': {
                'Environment': random.choice(['prod', 'dev', 'staging']),
                'Owner': random.choice(['alice', 'bob', 'engineering', 'security']),
                'Application': 'skysentinel'
            }
        }
    
    def _generate_request_params(self, service: str, operation: str, resource: Dict) -> Dict:
        """Generate request parameters"""
        if service == 'EC2':
            if 'Instances' in operation:
                return {
                    'InstanceType': resource['properties'].get('instance_type', 't3.micro'),
                    'ImageId': f"ami-{random.randint(10000000, 99999999)}",
                    'MinCount': 1,
                    'MaxCount': random.randint(1, 5)
                }
        elif service == 'S3':
            if 'Bucket' in operation:
                return {
                    'Bucket': resource['name']
                }
            elif 'Object' in operation:
                return {
                    'Bucket': resource['name'],
                    'Key': f"file-{random.randint(1000,9999)}.txt"
                }
        elif service == 'IAM':
            if 'User' in operation:
                return {
                    'UserName': resource['name']
                }
            elif 'Role' in operation:
                return {
                    'RoleName': resource['name']
                }
        
        return {}
    
    def _generate_response_params(self, service: str, operation: str, resource: Dict) -> Dict:
        """Generate response elements"""
        if service == 'EC2':
            if 'Instances' in operation:
                return {
                    'Instances': [{
                        'InstanceId': resource['id'].split('/')[-1],
                        'State': {'Name': resource['state']}
                    }]
                }
        elif service == 'S3':
            if 'Bucket' in operation:
                return {
                    'Location': f"/{resource['name']}"
                }
        
        return {'status': 'success'}
    
    def generate_resource_graph(self, count: int = 100, cloud_provider: str = "aws") -> List[Dict]:
        """Generate a test resource graph"""
        resources = []
        
        for i in range(count):
            if cloud_provider.lower() == "aws":
                resource = self._generate_aws_resource(
                    random.choice(list(self.aws_events.keys())),
                    datetime.utcnow() - timedelta(days=random.randint(0, 365))
                )
            elif cloud_provider.lower() == "azure":
                resource = self._generate_azure_resource(
                    random.choice(self.azure_events),
                    datetime.utcnow() - timedelta(days=random.randint(0, 365))
                )
            elif cloud_provider.lower() == "gcp":
                resource = self._generate_gcp_resource(
                    random.choice(self.gcp_events),
                    datetime.utcnow() - timedelta(days=random.randint(0, 365))
                )
            
            resources.append(resource)
        
        return resources
    
    def generate_event_stream(self, count: int = 1000, cloud_provider: str = "aws", 
                           time_window_hours: int = 24) -> List[Dict]:
        """Generate a stream of events over time"""
        events = []
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_window_hours)
        
        for i in range(count):
            # Generate timestamp within time window
            event_time = start_time + timedelta(
                seconds=random.randint(0, int((end_time - start_time).total_seconds()))
            )
            
            event = self.generate_cloud_event(cloud_provider)
            event['event_time'] = event_time.timestamp()
            events.append(event)
        
        # Sort by timestamp
        events.sort(key=lambda x: x['event_time'])
        return events
    
    def generate_attack_scenarios(self) -> List[Dict]:
        """Generate realistic attack scenarios"""
        scenarios = []
        
        # Scenario 1: Privilege escalation
        attacker_principal = {
            'id': 'arn:aws:iam::123456789012:user/attacker',
            'type': 'IAMUser',
            'name': 'attacker'
        }
        
        scenarios.append({
            'scenario': 'privilege_escalation',
            'description': 'Attacker attempts to escalate privileges',
            'events': [
                {
                    'id': str(uuid.uuid4()),
                    'cloud': CloudProvider.AWS.value,
                    'event_type': 'PERMISSION_MODIFY',
                    'event_time': (datetime.utcnow() - timedelta(minutes=30)).timestamp(),
                    'operation': 'AttachUserPolicy',
                    'principal_id': attacker_principal['id'],
                    'resource_id': 'arn:aws:iam::123456789012:user/attacker',
                    'request_parameters': {
                        'UserName': 'attacker',
                        'PolicyArn': 'arn:aws:iam::aws:policy/AdministratorAccess'
                    },
                    'response_elements': {},
                    'source_ip': '203.0.113.1',
                    'user_agent': 'aws-cli/2.0.0',
                    'status': 'FAILED',
                    'raw_event': {'scenario': 'privilege_escalation'}
                }
            ]
        })
        
        # Scenario 2: Data exfiltration
        scenarios.append({
            'scenario': 'data_exfiltration',
            'description': 'Attacker attempts to exfiltrate sensitive data',
            'events': [
                {
                    'id': str(uuid.uuid4()),
                    'cloud': CloudProvider.AWS.value,
                    'event_type': 'OBJECT_READ',
                    'event_time': (datetime.utcnow() - timedelta(minutes=15)).timestamp(),
                    'operation': 'GetObject',
                    'principal_id': attacker_principal['id'],
                    'resource_id': 'arn:aws:s3:::sensitive-data/secret-file.txt',
                    'request_parameters': {
                        'Bucket': 'sensitive-data',
                        'Key': 'secret-file.txt'
                    },
                    'response_elements': {},
                    'source_ip': '203.0.113.1',
                    'user_agent': 'curl/7.68.0',
                    'status': 'FAILED',
                    'raw_event': {'scenario': 'data_exfiltration'}
                }
            ]
        })
        
        return scenarios
    
    def save_to_file(self, data: Any, filename: str, format: str = 'json'):
        """Save generated data to file"""
        filepath = os.path.join(os.path.dirname(__file__), 'data', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            if format == 'json':
                json.dump(data, f, indent=2, default=str)
            else:
                f.write(str(data))
        
        print(f"Data saved to {filepath}")


def main():
    """Main function for generating test data"""
    generator = TestDataGenerator(seed=42)
    
    print("Generating test data for SkySentinel...")
    
    # Generate events
    print("Generating cloud events...")
    aws_events = generator.generate_event_stream(count=100, cloud_provider="aws")
    generator.save_to_file(aws_events, 'aws_events.json')
    
    azure_events = generator.generate_event_stream(count=50, cloud_provider="azure")
    generator.save_to_file(azure_events, 'azure_events.json')
    
    gcp_events = generator.generate_event_stream(count=50, cloud_provider="gcp")
    generator.save_to_file(gcp_events, 'gcp_events.json')
    
    # Generate resources
    print("Generating resource graph...")
    resources = generator.generate_resource_graph(count=200, cloud_provider="aws")
    generator.save_to_file(resources, 'aws_resources.json')
    
    # Generate attack scenarios
    print("Generating attack scenarios...")
    scenarios = generator.generate_attack_scenarios()
    generator.save_to_file(scenarios, 'attack_scenarios.json')
    
    print("Test data generation complete!")
    print(f"Generated {len(aws_events)} AWS events")
    print(f"Generated {len(azure_events)} Azure events")
    print(f"Generated {len(gcp_events)} GCP events")
    print(f"Generated {len(resources)} AWS resources")
    print(f"Generated {len(scenarios)} attack scenarios")


if __name__ == "__main__":
    main()
