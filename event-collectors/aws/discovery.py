import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from shared.models.events import CloudProvider, ResourceReference, Principal


class AWSResourceDiscovery:
    """AWS Resource Discovery service for initial graph population"""
    
    def __init__(self, account_id: str, role_arn: Optional[str] = None, region: str = 'us-east-1'):
        self.account_id = account_id
        self.role_arn = role_arn
        self.region = region
        self.logger = logging.getLogger(__name__)
        
        # Initialize STS client
        self.sts = boto3.client('sts', region_name=region)
        
        # Assume role if provided
        if role_arn:
            self.credentials = self.assume_role()
            self.session = boto3.Session(
                aws_access_key_id=self.credentials['AccessKeyId'],
                aws_secret_access_key=self.credentials['SecretAccessKey'],
                aws_session_token=self.credentials['SessionToken'],
                region_name=region
            )
        else:
            self.session = boto3.Session(region_name=region)
    
    def assume_role(self) -> Dict[str, Any]:
        """Assume cross-account role for discovery"""
        try:
            response = self.sts.assume_role(
                RoleArn=self.role_arn,
                RoleSessionName='SkySentinelDiscovery',
                DurationSeconds=3600
            )
            return response['Credentials']
        except ClientError as e:
            self.logger.error(f"Failed to assume role {self.role_arn}: {e}")
            raise
    
    def discover_all_resources(self) -> List[Dict[str, Any]]:
        """Discover all resources in AWS account"""
        resources = []
        
        try:
            # Compute resources
            resources.extend(self.discover_ec2_instances())
            resources.extend(self.discover_lambda_functions())
            resources.extend(self.discover_ecs_clusters())
            
            # Storage resources
            resources.extend(self.discover_s3_buckets())
            resources.extend(self.discover_ebs_volumes())
            
            # Database resources
            resources.extend(self.discover_rds_instances())
            resources.extend(self.discover_dynamodb_tables())
            
            # Network resources
            resources.extend(self.discover_vpc_resources())
            resources.extend(self.discover_elb_load_balancers())
            
            # Security resources
            resources.extend(self.discover_iam_entities())
            resources.extend(self.discover_security_groups())
            resources.extend(self.discover_iam_policies())
            
            # Monitoring resources
            resources.extend(self.discover_cloudtrail_trails())
            resources.extend(self.discover_guardduty_detectors())
            
            self.logger.info(f"Discovered {len(resources)} total resources")
            return resources
            
        except Exception as e:
            self.logger.error(f"Resource discovery failed: {e}")
            raise
    
    def discover_ec2_instances(self) -> List[Dict]:
        """Discover EC2 instances and their relationships"""
        try:
            ec2 = self.session.client('ec2')
            instances = []
            paginator = ec2.get_paginator('describe_instances')
            
            for page in paginator.paginate():
                for reservation in page['Reservations']:
                    for instance in reservation['Instances']:
                        resource = {
                            'id': instance['InstanceId'],
                            'arn': f"arn:aws:ec2:{instance['Placement']['AvailabilityZone'][:-1]}:{self.account_id}:instance/{instance['InstanceId']}",
                            'type': 'aws:ec2:instance',
                            'region': instance['Placement']['AvailabilityZone'][:-1],
                            'account': self.account_id,
                            'name': self._get_name_from_tags(instance.get('Tags', [])),
                            'state': instance['State']['Name'],
                            'properties': {
                                'instance_type': instance['InstanceType'],
                                'vpc_id': instance.get('VpcId'),
                                'subnet_id': instance.get('SubnetId'),
                                'security_groups': instance.get('SecurityGroups', []),
                                'key_name': instance.get('KeyName'),
                                'launch_time': instance.get('LaunchTime'),
                                'platform': instance.get('Platform', 'linux'),
                                'architecture': instance.get('Architecture', 'x86_64')
                            },
                            'tags': {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                        }
                        instances.append(resource)
            
            self.logger.debug(f"Discovered {len(instances)} EC2 instances")
            return instances
            
        except ClientError as e:
            self.logger.error(f"Failed to discover EC2 instances: {e}")
            return []
    
    def discover_s3_buckets(self) -> List[Dict]:
        """Discover S3 buckets"""
        try:
            s3 = self.session.client('s3')
            buckets = []
            
            paginator = s3.get_paginator('list_buckets')
            for page in paginator.paginate():
                for bucket in page['Buckets']:
                    try:
                        # Get bucket location
                        location = s3.get_bucket_location(Bucket=bucket['Name'])
                        region = location['LocationConstraint'] or 'us-east-1'
                        
                        # Get bucket versioning
                        versioning = s3.get_bucket_versioning(Bucket=bucket['Name'])
                        
                        # Get bucket encryption
                        try:
                            encryption = s3.get_bucket_encryption(Bucket=bucket['Name'])
                            encryption_enabled = True
                        except ClientError:
                            encryption_enabled = False
                        
                        resource = {
                            'id': f"arn:aws:s3:::{bucket['Name']}",
                            'arn': f"arn:aws:s3:::{bucket['Name']}",
                            'type': 'aws:s3:bucket',
                            'region': region,
                            'account': self.account_id,
                            'name': bucket['Name'],
                            'state': 'ACTIVE',
                            'properties': {
                                'creation_date': bucket['CreationDate'],
                                'versioning': versioning.get('Status', 'Disabled'),
                                'encryption_enabled': encryption_enabled,
                                'public_read': self._check_s3_public_read(s3, bucket['Name']),
                                'website_enabled': self._check_s3_website(s3, bucket['Name'])
                            },
                            'tags': self._get_s3_bucket_tags(s3, bucket['Name'])
                        }
                        buckets.append(resource)
                        
                    except ClientError as e:
                        self.logger.warning(f"Failed to get details for bucket {bucket['Name']}: {e}")
                        continue
            
            self.logger.debug(f"Discovered {len(buckets)} S3 buckets")
            return buckets
            
        except ClientError as e:
            self.logger.error(f"Failed to discover S3 buckets: {e}")
            return []
    
    def discover_iam_entities(self) -> List[Dict]:
        """Discover IAM users, roles, and groups"""
        try:
            iam = self.session.client('iam')
            entities = []
            
            # Discover users
            users_paginator = iam.get_paginator('list_users')
            for page in users_paginator.paginate():
                for user in page['Users']:
                    # Get user policies
                    policies = self._get_user_policies(iam, user['UserName'])
                    
                    resource = {
                        'id': user['Arn'],
                        'arn': user['Arn'],
                        'type': 'aws:iam:user',
                        'region': None,
                        'account': self.account_id,
                        'name': user['UserName'],
                        'state': 'ACTIVE',
                        'properties': {
                            'create_date': user['CreateDate'],
                            'password_last_used': user.get('PasswordLastUsed'),
                            'mfa_enabled': self._check_user_mfa(iam, user['UserName']),
                            'access_keys_count': self._count_user_access_keys(iam, user['UserName']),
                            'policies': policies
                        },
                        'tags': {tag['Key']: tag['Value'] for tag in user.get('Tags', [])}
                    }
                    entities.append(resource)
            
            # Discover roles
            roles_paginator = iam.get_paginator('list_roles')
            for page in roles_paginator.paginate():
                for role in page['Roles']:
                    resource = {
                        'id': role['Arn'],
                        'arn': role['Arn'],
                        'type': 'aws:iam:role',
                        'region': None,
                        'account': self.account_id,
                        'name': role['RoleName'],
                        'state': 'ACTIVE',
                        'properties': {
                            'create_date': role['CreateDate'],
                            'assume_role_policy': role.get('AssumeRolePolicyDocument'),
                            'max_session_duration': role.get('MaxSessionDuration', 3600),
                            'path': role.get('Path', '/')
                        },
                        'tags': {tag['Key']: tag['Value'] for tag in role.get('Tags', [])}
                    }
                    entities.append(resource)
            
            self.logger.debug(f"Discovered {len(entities)} IAM entities")
            return entities
            
        except ClientError as e:
            self.logger.error(f"Failed to discover IAM entities: {e}")
            return []
    
    def discover_rds_instances(self) -> List[Dict]:
        """Discover RDS instances"""
        try:
            rds = self.session.client('rds')
            instances = []
            
            paginator = rds.get_paginator('describe_db_instances')
            for page in paginator.paginate():
                for instance in page['DBInstances']:
                    resource = {
                        'id': instance['DBInstanceArn'],
                        'arn': instance['DBInstanceArn'],
                        'type': 'aws:rds:instance',
                        'region': instance['AvailabilityZone'][:-1] if instance.get('AvailabilityZone') else self.region,
                        'account': self.account_id,
                        'name': instance['DBInstanceIdentifier'],
                        'state': instance['DBInstanceStatus'],
                        'properties': {
                            'engine': instance.get('Engine'),
                            'engine_version': instance.get('EngineVersion'),
                            'instance_class': instance.get('DBInstanceClass'),
                            'allocated_storage': instance.get('AllocatedStorage'),
                            'storage_type': instance.get('StorageType'),
                            'multi_az': instance.get('MultiAZ', False),
                            'publicly_accessible': instance.get('PubliclyAccessible', False),
                            'vpc_id': instance.get('DBSubnetGroup', {}).get('VpcId'),
                            'subnet_group': instance.get('DBSubnetGroup', {}).get('DBSubnetGroupName'),
                            'backup_retention': instance.get('BackupRetentionPeriod', 0),
                            'encryption_enabled': instance.get('StorageEncrypted', False)
                        },
                        'tags': {tag['Key']: tag['Value'] for tag in instance.get('TagList', [])}
                    }
                    instances.append(resource)
            
            self.logger.debug(f"Discovered {len(instances)} RDS instances")
            return instances
            
        except ClientError as e:
            self.logger.error(f"Failed to discover RDS instances: {e}")
            return []
    
    def discover_vpc_resources(self) -> List[Dict]:
        """Discover VPC, subnets, and network components"""
        try:
            ec2 = self.session.client('ec2')
            resources = []
            
            # Discover VPCs
            vpcs_paginator = ec2.get_paginator('describe_vpcs')
            for page in vpcs_paginator.paginate():
                for vpc in page['Vpcs']:
                    resource = {
                        'id': vpc['VpcId'],
                        'arn': f"arn:aws:ec2:{self.region}:{self.account_id}:vpc/{vpc['VpcId']}",
                        'type': 'aws:ec2:vpc',
                        'region': self.region,
                        'account': self.account_id,
                        'name': self._get_name_from_tags(vpc.get('Tags', [])),
                        'state': 'AVAILABLE',
                        'properties': {
                            'cidr_block': vpc['CidrBlock'],
                            'is_default': vpc['IsDefault'],
                            'state': vpc['State'],
                            'dhcp_options_id': vpc['DhcpOptionsId'],
                            'instance_tenancy': vpc['InstanceTenancy']
                        },
                        'tags': {tag['Key']: tag['Value'] for tag in vpc.get('Tags', [])}
                    }
                    resources.append(resource)
            
            # Discover Subnets
            subnets_paginator = ec2.get_paginator('describe_subnets')
            for page in subnets_paginator.paginate():
                for subnet in page['Subnets']:
                    resource = {
                        'id': subnet['SubnetId'],
                        'arn': f"arn:aws:ec2:{self.region}:{self.account_id}:subnet/{subnet['SubnetId']}",
                        'type': 'aws:ec2:subnet',
                        'region': self.region,
                        'account': self.account_id,
                        'name': self._get_name_from_tags(subnet.get('Tags', [])),
                        'state': 'AVAILABLE',
                        'properties': {
                            'vpc_id': subnet['VpcId'],
                            'cidr_block': subnet['CidrBlock'],
                            'availability_zone': subnet['AvailabilityZone'],
                            'available_ip_count': subnet['AvailableIpAddressCount'],
                            'map_public_ip': subnet['MapPublicIpOnLaunch'],
                            'assign_ipv6': subnet['AssignIpv6AddressOnCreation']
                        },
                        'tags': {tag['Key']: tag['Value'] for tag in subnet.get('Tags', [])}
                    }
                    resources.append(resource)
            
            self.logger.debug(f"Discovered {len(resources)} VPC resources")
            return resources
            
        except ClientError as e:
            self.logger.error(f"Failed to discover VPC resources: {e}")
            return []
    
    def discover_lambda_functions(self) -> List[Dict]:
        """Discover Lambda functions"""
        try:
            lambda_client = self.session.client('lambda')
            functions = []
            
            paginator = lambda_client.get_paginator('list_functions')
            for page in paginator.paginate():
                for function in page['Functions']:
                    resource = {
                        'id': function['FunctionArn'],
                        'arn': function['FunctionArn'],
                        'type': 'aws:lambda:function',
                        'region': self.region,
                        'account': self.account_id,
                        'name': function['FunctionName'],
                        'state': 'ACTIVE',
                        'properties': {
                            'runtime': function.get('Runtime'),
                            'handler': function.get('Handler'),
                            'code_size': function.get('CodeSize'),
                            'timeout': function.get('Timeout'),
                            'memory_size': function.get('MemorySize'),
                            'last_modified': function.get('LastModified'),
                            'vpc_id': function.get('VpcConfig', {}).get('VpcId'),
                            'security_groups': function.get('VpcConfig', {}).get('SecurityGroupIds', []),
                            'environment_variables': function.get('Environment', {}).get('Variables', {}),
                            'layers': [layer['Arn'] for layer in function.get('Layers', [])]
                        },
                        'tags': function.get('Tags', {})
                    }
                    functions.append(resource)
            
            self.logger.debug(f"Discovered {len(functions)} Lambda functions")
            return functions
            
        except ClientError as e:
            self.logger.error(f"Failed to discover Lambda functions: {e}")
            return []
    
    def discover_security_groups(self) -> List[Dict]:
        """Discover security groups"""
        try:
            ec2 = self.session.client('ec2')
            security_groups = []
            
            paginator = ec2.get_paginator('describe_security_groups')
            for page in paginator.paginate():
                for sg in page['SecurityGroups']:
                    resource = {
                        'id': sg['GroupId'],
                        'arn': f"arn:aws:ec2:{self.region}:{self.account_id}:security-group/{sg['GroupId']}",
                        'type': 'aws:ec2:security-group',
                        'region': self.region,
                        'account': self.account_id,
                        'name': sg.get('GroupName'),
                        'state': 'ACTIVE',
                        'properties': {
                            'description': sg.get('Description'),
                            'vpc_id': sg.get('VpcId'),
                            'ingress_rules': sg.get('IpPermissions', []),
                            'egress_rules': sg.get('IpPermissionsEgress', []),
                            'owner_id': sg.get('OwnerId')
                        },
                        'tags': {tag['Key']: tag['Value'] for tag in sg.get('Tags', [])}
                    }
                    security_groups.append(resource)
            
            self.logger.debug(f"Discovered {len(security_groups)} security groups")
            return security_groups
            
        except ClientError as e:
            self.logger.error(f"Failed to discover security groups: {e}")
            return []
    
    def discover_ebs_volumes(self) -> List[Dict]:
        """Discover EBS volumes"""
        try:
            ec2 = self.session.client('ec2')
            volumes = []
            
            paginator = ec2.get_paginator('describe_volumes')
            for page in paginator.paginate():
                for volume in page['Volumes']:
                    resource = {
                        'id': volume['VolumeId'],
                        'arn': f"arn:aws:ec2:{self.region}:{self.account_id}:volume/{volume['VolumeId']}",
                        'type': 'aws:ec2:volume',
                        'region': self.region,
                        'account': self.account_id,
                        'name': self._get_name_from_tags(volume.get('Tags', [])),
                        'state': volume['State'],
                        'properties': {
                            'size': volume['Size'],
                            'volume_type': volume.get('VolumeType'),
                            'iops': volume.get('Iops'),
                            'throughput': volume.get('Throughput'),
                            'encrypted': volume.get('Encrypted', False),
                            'kms_key_id': volume.get('KmsKeyId'),
                            'availability_zone': volume.get('AvailabilityZone'),
                            'snapshot_id': volume.get('SnapshotId'),
                            'attachments': volume.get('Attachments', [])
                        },
                        'tags': {tag['Key']: tag['Value'] for tag in volume.get('Tags', [])}
                    }
                    volumes.append(resource)
            
            self.logger.debug(f"Discovered {len(volumes)} EBS volumes")
            return volumes
            
        except ClientError as e:
            self.logger.error(f"Failed to discover EBS volumes: {e}")
            return []
    
    def discover_dynamodb_tables(self) -> List[Dict]:
        """Discover DynamoDB tables"""
        try:
            dynamodb = self.session.client('dynamodb')
            tables = []
            
            paginator = dynamodb.get_paginator('list_tables')
            for page in paginator.paginate():
                for table_name in page['TableNames']:
                    try:
                        table_desc = dynamodb.describe_table(TableName=table_name)
                        table = table_desc['Table']
                        
                        resource = {
                            'id': table['TableArn'],
                            'arn': table['TableArn'],
                            'type': 'aws:dynamodb:table',
                            'region': self.region,
                            'account': self.account_id,
                            'name': table['TableName'],
                            'state': table['TableStatus'],
                            'properties': {
                                'item_count': table.get('ItemCount', 0),
                                'table_size_bytes': table.get('TableSizeBytes', 0),
                                'creation_date': table.get('CreationDateTime'),
                                'billing_mode': table.get('BillingModeSummary', {}).get('BillingMode'),
                                'global_secondary_indexes': len(table.get('GlobalSecondaryIndexes', [])),
                                'local_secondary_indexes': len(table.get('LocalSecondaryIndexes', [])),
                                'streams': table.get('StreamSpecification'),
                                'point_in_time_recovery': table.get('PointInTimeRecoveryDescription', {}).get('PointInTimeRecoveryStatus')
                            },
                            'tags': self._get_dynamodb_tags(dynamodb, table_name)
                        }
                        tables.append(resource)
                        
                    except ClientError as e:
                        self.logger.warning(f"Failed to describe DynamoDB table {table_name}: {e}")
                        continue
            
            self.logger.debug(f"Discovered {len(tables)} DynamoDB tables")
            return tables
            
        except ClientError as e:
            self.logger.error(f"Failed to discover DynamoDB tables: {e}")
            return []
    
    def discover_ecs_clusters(self) -> List[Dict]:
        """Discover ECS clusters"""
        try:
            ecs = self.session.client('ecs')
            clusters = []
            
            paginator = ecs.get_paginator('list_clusters')
            for page in paginator.paginate():
                for cluster_arn in page['clusterArns']:
                    try:
                        cluster_desc = ecs.describe_clusters(clusters=[cluster_arn])['clusters'][0]
                        
                        resource = {
                            'id': cluster_arn,
                            'arn': cluster_arn,
                            'type': 'aws:ecs:cluster',
                            'region': self.region,
                            'account': self.account_id,
                            'name': cluster_desc['clusterName'],
                            'state': cluster_desc['status'],
                            'properties': {
                                'running_tasks_count': cluster_desc.get('runningTasksCount', 0),
                                'pending_tasks_count': cluster_desc.get('pendingTasksCount', 0),
                                'active_services_count': cluster_desc.get('activeServicesCount', 0),
                                'registered_container_instances_count': cluster_desc.get('registeredContainerInstancesCount', 0),
                                'capacity_providers': cluster_desc.get('capacityProviders', []),
                                'default_capacity_provider_strategy': cluster_desc.get('defaultCapacityProviderStrategy', [])
                            },
                            'tags': {tag['Key']: tag['Value'] for tag in cluster_desc.get('tags', [])}
                        }
                        clusters.append(resource)
                        
                    except ClientError as e:
                        self.logger.warning(f"Failed to describe ECS cluster {cluster_arn}: {e}")
                        continue
            
            self.logger.debug(f"Discovered {len(clusters)} ECS clusters")
            return clusters
            
        except ClientError as e:
            self.logger.error(f"Failed to discover ECS clusters: {e}")
            return []
    
    def discover_elb_load_balancers(self) -> List[Dict]:
        """Discover ELB/ALB load balancers"""
        try:
            elb = self.session.client('elbv2')
            load_balancers = []
            
            paginator = elb.get_paginator('describe_load_balancers')
            for page in paginator.paginate():
                for lb in page['LoadBalancers']:
                    resource = {
                        'id': lb['LoadBalancerArn'],
                        'arn': lb['LoadBalancerArn'],
                        'type': f"aws:elbv2:{lb['Type'].lower()}",
                        'region': self.region,
                        'account': self.account_id,
                        'name': lb['LoadBalancerName'],
                        'state': lb['State']['Code'],
                        'properties': {
                            'scheme': lb.get('Scheme'),
                            'vpc_id': lb.get('VpcId'),
                            'type': lb.get('Type'),
                            'ip_address_type': lb.get('IpAddressType'),
                            'security_groups': lb.get('SecurityGroups', []),
                            'subnets': lb.get('AvailabilityZones', []),
                            'created_time': lb.get('CreatedTime'),
                            'dns_name': lb.get('DNSName'),
                            'canonical_hosted_zone_id': lb.get('CanonicalHostedZoneId')
                        },
                        'tags': {tag['Key']: tag['Value'] for tag in lb.get('Tags', [])}
                    }
                    load_balancers.append(resource)
            
            self.logger.debug(f"Discovered {len(load_balancers)} load balancers")
            return load_balancers
            
        except ClientError as e:
            self.logger.error(f"Failed to discover load balancers: {e}")
            return []
    
    def discover_cloudtrail_trails(self) -> List[Dict]:
        """Discover CloudTrail trails"""
        try:
            cloudtrail = self.session.client('cloudtrail')
            trails = []
            
            response = cloudtrail.describe_trails()
            for trail in response['trailList']:
                resource = {
                    'id': trail['TrailARN'],
                    'arn': trail['TrailARN'],
                    'type': 'aws:cloudtrail:trail',
                    'region': trail.get('HomeRegion', self.region),
                    'account': self.account_id,
                    'name': trail.get('Name'),
                    'state': 'ACTIVE' if trail.get('IsLogging') else 'INACTIVE',
                    'properties': {
                        's3_bucket_name': trail.get('S3BucketName'),
                        's3_key_prefix': trail.get('S3KeyPrefix'),
                        'include_global_service_events': trail.get('IncludeGlobalServiceEvents', False),
                        'is_multi_region_trail': trail.get('IsMultiRegionTrail', False),
                        'home_region': trail.get('HomeRegion'),
                        'trail_arn': trail.get('TrailARN'),
                        'log_file_validation_enabled': trail.get('LogFileValidationEnabled', False),
                        'cloud_watch_logs_log_group_arn': trail.get('CloudWatchLogsLogGroupArn'),
                        'cloud_watch_logs_role_arn': trail.get('CloudWatchLogsRoleArn'),
                        'kms_key_id': trail.get('KmsKeyId')
                    },
                    'tags': trail.get('Tags', {})
                }
                trails.append(resource)
            
            self.logger.debug(f"Discovered {len(trails)} CloudTrail trails")
            return trails
            
        except ClientError as e:
            self.logger.error(f"Failed to discover CloudTrail trails: {e}")
            return []
    
    def discover_guardduty_detectors(self) -> List[Dict]:
        """Discover GuardDuty detectors"""
        try:
            guardduty = self.session.client('guardduty')
            detectors = []
            
            response = guardduty.list_detectors()
            for detector_id in response['DetectorIds']:
                try:
                    detector = guardduty.get_detector(DetectorId=detector_id)
                    
                    resource = {
                        'id': detector_id,
                        'arn': f"arn:aws:guardduty:{self.region}:{self.account_id}:detector/{detector_id}",
                        'type': 'aws:guardduty:detector',
                        'region': self.region,
                        'account': self.account_id,
                        'name': detector_id,
                        'state': 'ENABLED' if detector['Status'] == 'ENABLED' else 'DISABLED',
                        'properties': {
                            'created_at': detector.get('CreatedAt'),
                            'updated_at': detector.get('UpdatedAt'),
                            'status': detector.get('Status'),
                            'finding_publishing_frequency': detector.get('FindingPublishingFrequency'),
                            'data_sources': detector.get('DataSources', {}),
                            'features': detector.get('Features', [])
                        },
                        'tags': detector.get('Tags', {})
                    }
                    detectors.append(resource)
                    
                except ClientError as e:
                    self.logger.warning(f"Failed to describe GuardDuty detector {detector_id}: {e}")
                    continue
            
            self.logger.debug(f"Discovered {len(detectors)} GuardDuty detectors")
            return detectors
            
        except ClientError as e:
            self.logger.error(f"Failed to discover GuardDuty detectors: {e}")
            return []
    
    def discover_iam_policies(self) -> List[Dict]:
        """Discover IAM policies"""
        try:
            iam = self.session.client('iam')
            policies = []
            
            # Get managed policies
            paginator = iam.get_paginator('list_policies')
            for page in paginator.paginate(Scope='Local', OnlyAttached=False):
                for policy in page['Policies']:
                    try:
                        policy_version = iam.get_policy(
                            PolicyArn=policy['Arn'],
                            VersionId=policy['DefaultVersionId']
                        )
                        
                        resource = {
                            'id': policy['Arn'],
                            'arn': policy['Arn'],
                            'type': 'aws:iam:policy',
                            'region': None,
                            'account': self.account_id,
                            'name': policy['PolicyName'],
                            'state': 'ACTIVE',
                            'properties': {
                                'create_date': policy['CreateDate'],
                                'update_date': policy['UpdateDate'],
                                'default_version_id': policy['DefaultVersionId'],
                                'attachment_count': policy['AttachmentCount'],
                                'permissions_count': policy.get('PermissionsBoundaryUsageCount', 0),
                                'is_attachable': policy['IsAttachable'],
                                'description': policy.get('Description'),
                                'path': policy.get('Path'),
                                'policy_document': policy_version['Policy']['Version']['Document']
                            },
                            'tags': {tag['Key']: tag['Value'] for tag in policy.get('Tags', [])}
                        }
                        policies.append(resource)
                        
                    except ClientError as e:
                        self.logger.warning(f"Failed to get policy version for {policy['Arn']}: {e}")
                        continue
            
            self.logger.debug(f"Discovered {len(policies)} IAM policies")
            return policies
            
        except ClientError as e:
            self.logger.error(f"Failed to discover IAM policies: {e}")
            return []
    
    # Helper methods
    def _get_name_from_tags(self, tags: List[Dict]) -> Optional[str]:
        """Extract name from tags, checking common tag keys"""
        if not tags:
            return None
        
        name_tags = ['Name', 'name', 'aws:cloudformation:stack-name']
        for tag in tags:
            if tag['Key'] in name_tags:
                return tag['Value']
        
        return tags[0]['Value'] if tags else None
    
    def _get_s3_bucket_tags(self, s3_client, bucket_name: str) -> Dict[str, str]:
        """Get tags for S3 bucket"""
        try:
            response = s3_client.get_bucket_tagging(Bucket=bucket_name)
            return {tag['Key']: tag['Value'] for tag in response['TagSet']}
        except ClientError:
            return {}
    
    def _check_s3_public_read(self, s3_client, bucket_name: str) -> bool:
        """Check if S3 bucket has public read access"""
        try:
            acl = s3_client.get_bucket_acl(Bucket=bucket_name)
            for grant in acl['Grants']:
                if grant.get('Grantee', {}).get('URI') == 'http://acs.amazonaws.com/groups/global/AllUsers':
                    return True
            return False
        except ClientError:
            return False
    
    def _check_s3_website(self, s3_client, bucket_name: str) -> bool:
        """Check if S3 bucket has website hosting enabled"""
        try:
            s3_client.get_bucket_website(Bucket=bucket_name)
            return True
        except ClientError:
            return False
    
    def _get_user_policies(self, iam_client, username: str) -> List[str]:
        """Get attached policies for IAM user"""
        policies = []
        try:
            # Get managed policies
            response = iam_client.list_attached_user_policies(UserName=username)
            policies.extend([policy['PolicyArn'] for policy in response['AttachedPolicies']])
            
            # Get inline policies
            response = iam_client.list_user_policies(UserName=username)
            policies.extend(response['PolicyNames'])
            
        except ClientError:
            pass
        
        return policies
    
    def _check_user_mfa(self, iam_client, username: str) -> bool:
        """Check if user has MFA enabled"""
        try:
            response = iam_client.list_mfa_devices(UserName=username)
            return len(response['MFADevices']) > 0
        except ClientError:
            return False
    
    def _count_user_access_keys(self, iam_client, username: str) -> int:
        """Count active access keys for user"""
        try:
            response = iam_client.list_access_keys(UserName=username)
            return len([key for key in response['AccessKeyMetadata'] if key['Status'] == 'Active'])
        except ClientError:
            return 0
    
    def _get_dynamodb_tags(self, dynamodb_client, table_name: str) -> Dict[str, str]:
        """Get tags for DynamoDB table"""
        try:
            response = dynamodb_client.list_tags_of_resource(ResourceArn=f"arn:aws:dynamodb:{self.region}:{self.account_id}:table/{table_name}")
            return {tag['Key']: tag['Value'] for tag in response['Tags']}
        except ClientError:
            return {}
