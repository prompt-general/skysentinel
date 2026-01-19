import json
import yaml
from typing import Dict, List, Any, Union, Optional, Set
from datetime import datetime
import logging

from .base import (
    IaCAdapter, IaCType, IaCPlan, IaCResource, IaCDependency, 
    IaCValidationResult, ResourceType, CloudProvider
)


class CloudFormationAdapter(IaCAdapter):
    """AWS CloudFormation IaC adapter"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def get_iac_type(self) -> IaCType:
        return IaCType.CLOUDFORMATION
    
    def _get_resource_type_mapping(self) -> Dict[str, ResourceType]:
        """Map CloudFormation resource types to standardized types"""
        return {
            # Compute resources
            'AWS::EC2::Instance': ResourceType.COMPUTE,
            'AWS::EC2::LaunchTemplate': ResourceType.COMPUTE,
            'AWS::AutoScaling::AutoScalingGroup': ResourceType.COMPUTE,
            'AWS::ECS::Service': ResourceType.COMPUTE,
            'AWS::ECS::TaskDefinition': ResourceType.COMPUTE,
            'AWS::Lambda::Function': ResourceType.SERVERLESS,
            'AWS::ElasticBeanstalk::Application': ResourceType.COMPUTE,
            'AWS::ElasticBeanstalk::Environment': ResourceType.COMPUTE,
            
            # Storage resources
            'AWS::S3::Bucket': ResourceType.STORAGE,
            'AWS::EC2::Volume': ResourceType.STORAGE,
            'AWS::EFS::FileSystem': ResourceType.STORAGE,
            'AWS::Backup::BackupPlan': ResourceType.STORAGE,
            'AWS::Backup::BackupVault': ResourceType.STORAGE,
            
            # Network resources
            'AWS::EC2::VPC': ResourceType.NETWORK,
            'AWS::EC2::Subnet': ResourceType.NETWORK,
            'AWS::EC2::SecurityGroup': ResourceType.SECURITY,
            'AWS::EC2::RouteTable': ResourceType.NETWORK,
            'AWS::EC2::InternetGateway': ResourceType.NETWORK,
            'AWS::EC2::NatGateway': ResourceType.NETWORK,
            'AWS::CloudFront::Distribution': ResourceType.NETWORK,
            'AWS::Route53::HostedZone': ResourceType.NETWORK,
            
            # Database resources
            'AWS::RDS::DBInstance': ResourceType.DATABASE,
            'AWS::RDS::DBCluster': ResourceType.DATABASE,
            'AWS::DynamoDB::Table': ResourceType.DATABASE,
            'AWS::ElastiCache::CacheCluster': ResourceType.DATABASE,
            'AWS::ElastiCache::ReplicationGroup': ResourceType.DATABASE,
            'AWS::DocumentDB::DBCluster': ResourceType.DATABASE,
            'AWS::Neptune::DBCluster': ResourceType.DATABASE,
            
            # Security resources
            'AWS::IAM::Role': ResourceType.IDENTITY,
            'AWS::IAM::Policy': ResourceType.SECURITY,
            'AWS::IAM::User': ResourceType.IDENTITY,
            'AWS::IAM::Group': ResourceType.IDENTITY,
            'AWS::IAM::InstanceProfile': ResourceType.IDENTITY,
            'AWS::KMS::Key': ResourceType.SECURITY,
            'AWS::SecretsManager::Secret': ResourceType.SECURITY,
            'AWS::CertificateManager::Certificate': ResourceType.SECURITY,
            
            # Container resources
            'AWS::ECS::Cluster': ResourceType.CONTAINER,
            'AWS::EKS::Cluster': ResourceType.CONTAINER,
            'AWS::EKS::Nodegroup': ResourceType.CONTAINER,
            
            # Messaging resources
            'AWS::SQS::Queue': ResourceType.MESSAGING,
            'AWS::SNS::Topic': ResourceType.MESSAGING,
            'AWS::EventBridge::EventBus': ResourceType.MESSAGING,
            'AWS::EventBridge::Rule': ResourceType.MESSAGING,
            
            # Analytics resources
            'AWS::Kinesis::Stream': ResourceType.ANALYTICS,
            'AWS::Redshift::Cluster': ResourceType.ANALYTICS,
            'AWS::Glue::Job': ResourceType.ANALYTICS,
            'AWS::EMR::Cluster': ResourceType.ANALYTICS,
            
            # AI/ML resources
            'AWS::SageMaker::NotebookInstance': ResourceType.AI_ML,
            'AWS::SageMaker::TrainingJob': ResourceType.AI_ML,
            'AWS::Comprehend::EntityRecognizer': ResourceType.AI_ML,
            
            # Monitoring resources
            'AWS::CloudWatch::Alarm': ResourceType.MONITORING,
            'AWS::CloudWatch::LogGroup': ResourceType.MONITORING,
            'AWS::CloudWatch::MetricFilter': ResourceType.MONITORING,
        }
    
    def _get_provider_mapping(self) -> Dict[str, CloudProvider]:
        """Map CloudFormation providers to CloudProvider enum"""
        return {
            'AWS': CloudProvider.AWS,
            'AWS::': CloudProvider.AWS,
        }
    
    def parse_plan(self, plan_content: Union[str, Dict]) -> IaCPlan:
        """Parse CloudFormation change set or template"""
        if isinstance(plan_content, str):
            try:
                # Try YAML first, then JSON
                try:
                    template_data = yaml.safe_load(plan_content)
                except yaml.YAMLError:
                    template_data = json.loads(plan_content)
            except (yaml.YAMLError, json.JSONDecodeError) as e:
                raise ValueError(f"Invalid CloudFormation template: {e}")
        else:
            template_data = plan_content
        
        # Create plan object
        plan = IaCPlan(
            id=template_data.get('Description', 'cloudformation-template'),
            iac_type=self.get_iac_type(),
            version=template_data.get('AWSTemplateFormatVersion', '2010-09-09'),
            created_at=datetime.utcnow(),
            metadata={
                'description': template_data.get('Description', ''),
                'metadata': template_data.get('Metadata', {}),
                'transform': template_data.get('Transform', []),
                'conditions': template_data.get('Conditions', {})
            }
        )
        
        # Parse resources
        resources = template_data.get('Resources', {})
        for resource_name, resource_data in resources.items():
            resource = self._parse_cloudformation_resource(resource_name, resource_data)
            if resource:
                plan.resources.append(resource)
        
        # Parse parameters
        parameters = template_data.get('Parameters', {})
        plan.variables = {k: v.get('Default', '') for k, v in parameters.items()}
        
        # Parse outputs
        outputs = template_data.get('Outputs', {})
        plan.outputs = {k: v.get('Value', '') for k, v in outputs.items()}
        
        # Extract dependencies
        dependencies = self.extract_dependencies(template_data)
        for dep in dependencies:
            for resource in plan.resources:
                if resource.id == dep.source_id:
                    resource.dependencies.add(dep.target_id)
        
        return plan
    
    def parse_configuration(self, config_content: Union[str, Dict]) -> IaCPlan:
        """Parse CloudFormation configuration (same as template)"""
        return self.parse_plan(config_content)
    
    def normalize_resource(self, raw_resource: Dict) -> IaCResource:
        """Normalize CloudFormation resource to unified model"""
        resource_type = raw_resource.get('Type', '')
        resource_name = raw_resource.get('LogicalId', '')
        properties = raw_resource.get('Properties', {})
        
        # Extract provider (always AWS for CloudFormation)
        provider = CloudProvider.AWS
        
        # Create resource ID
        resource_id = f"{resource_type}.{resource_name}"
        
        # Extract change type (default to create for templates)
        change_type = raw_resource.get('ChangeType', 'create')
        
        return IaCResource(
            id=resource_id,
            type=resource_type,
            name=resource_name,
            provider=provider,
            resource_category=self._normalize_resource_type(resource_type),
            properties=self._sanitize_properties(properties),
            change_type=change_type,
            metadata={
                'logical_id': resource_name,
                'condition': raw_resource.get('Condition'),
                'creation_policy': raw_resource.get('CreationPolicy'),
                'deletion_policy': raw_resource.get('DeletionPolicy'),
                'update_policy': raw_resource.get('UpdatePolicy'),
                'metadata': raw_resource.get('Metadata', {})
            }
        )
    
    def extract_dependencies(self, iac_content: Dict) -> List[IaCDependency]:
        """Extract dependencies from CloudFormation template"""
        dependencies = []
        resources = iac_content.get('Resources', {})
        
        for resource_name, resource_data in resources.items():
            resource_type = resource_data.get('Type', '')
            properties = resource_data.get('Properties', {})
            
            # Extract Ref dependencies
            refs = self._extract_refs_from_object(properties)
            for ref in refs:
                if ref in resources:
                    dependencies.append(IaCDependency(
                        source_id=f"{resource_type}.{resource_name}",
                        target_id=f"{resources[ref].get('Type', '')}.{ref}",
                        dependency_type='reference'
                    ))
            
            # Extract Fn::GetAtt dependencies
            get_atts = self._extract_get_atts_from_object(properties)
            for get_att in get_atts:
                ref_resource = get_att.split('.')[0]
                if ref_resource in resources:
                    dependencies.append(IaCDependency(
                        source_id=f"{resource_type}.{resource_name}",
                        target_id=f"{resources[ref_resource].get('Type', '')}.{ref_resource}",
                        dependency_type='attribute',
                        property_path=get_att
                    ))
            
            # Extract explicit DependsOn
            depends_on = resource_data.get('DependsOn', [])
            if isinstance(depends_on, str):
                depends_on = [depends_on]
            
            for dep in depends_on:
                if dep in resources:
                    dependencies.append(IaCDependency(
                        source_id=f"{resource_type}.{resource_name}",
                        target_id=f"{resources[dep].get('Type', '')}.{dep}",
                        dependency_type='explicit'
                    ))
        
        return dependencies
    
    def validate_syntax(self, content: Union[str, Dict]) -> IaCValidationResult:
        """Validate CloudFormation template syntax"""
        result = IaCValidationResult(is_valid=True)
        
        if isinstance(content, str):
            try:
                try:
                    data = yaml.safe_load(content)
                except yaml.YAMLError:
                    data = json.loads(content)
            except (yaml.YAMLError, json.JSONDecodeError) as e:
                result.is_valid = False
                result.errors.append(f"Invalid YAML/JSON: {e}")
                return result
        else:
            data = content
        
        # Check required sections
        if 'Resources' not in data:
            result.errors.append("CloudFormation template must have Resources section")
            result.is_valid = False
        
        # Validate resources
        resources = data.get('Resources', {})
        for resource_name, resource_data in resources.items():
            if 'Type' not in resource_data:
                result.errors.append(f"Resource {resource_name} missing Type")
                result.is_valid = False
            
            if not isinstance(resource_data.get('Properties', {}), dict):
                result.errors.append(f"Resource {resource_name} Properties must be a dictionary")
                result.is_valid = False
        
        # Validate parameters
        parameters = data.get('Parameters', {})
        for param_name, param_data in parameters.items():
            if not isinstance(param_data, dict):
                result.errors.append(f"Parameter {param_name} must be a dictionary")
                result.is_valid = False
        
        # Validate outputs
        outputs = data.get('Outputs', {})
        for output_name, output_data in outputs.items():
            if not isinstance(output_data, dict):
                result.errors.append(f"Output {output_name} must be a dictionary")
                result.is_valid = False
            elif 'Value' not in output_data:
                result.errors.append(f"Output {output_name} missing Value")
                result.is_valid = False
        
        return result
    
    def _parse_cloudformation_resource(self, logical_id: str, resource_data: Dict) -> Optional[IaCResource]:
        """Parse CloudFormation resource"""
        try:
            resource_type = resource_data.get('Type', '')
            properties = resource_data.get('Properties', {})
            
            # Add CloudFormation-specific properties
            cf_properties = {
                'logical_id': logical_id,
                'resource_type': resource_type,
                **properties
            }
            
            return IaCResource(
                id=f"{resource_type}.{logical_id}",
                type=resource_type,
                name=logical_id,
                provider=CloudProvider.AWS,
                resource_category=self._normalize_resource_type(resource_type),
                properties=self._sanitize_properties(cf_properties),
                change_type='create',
                metadata={
                    'logical_id': logical_id,
                    'condition': resource_data.get('Condition'),
                    'creation_policy': resource_data.get('CreationPolicy'),
                    'deletion_policy': resource_data.get('DeletionPolicy'),
                    'update_policy': resource_data.get('UpdatePolicy'),
                    'metadata': resource_data.get('Metadata', {}),
                    'depends_on': resource_data.get('DependsOn', [])
                }
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse CloudFormation resource {logical_id}: {e}")
            return None
    
    def _extract_refs_from_object(self, obj: Any) -> Set[str]:
        """Extract all Ref references from an object"""
        refs = set()
        
        if isinstance(obj, dict):
            if 'Ref' in obj:
                refs.add(obj['Ref'])
            for key, value in obj.items():
                refs.update(self._extract_refs_from_object(value))
        elif isinstance(obj, list):
            for item in obj:
                refs.update(self._extract_refs_from_object(item))
        
        return refs
    
    def _extract_get_atts_from_object(self, obj: Any) -> Set[str]:
        """Extract all Fn::GetAtt references from an object"""
        get_atts = set()
        
        if isinstance(obj, dict):
            if 'Fn::GetAtt' in obj:
                get_att = obj['Fn::GetAtt']
                if isinstance(get_att, list):
                    get_atts.add(f"{get_att[0]}.{get_att[1]}")
                else:
                    get_atts.add(get_att)
            for key, value in obj.items():
                get_atts.update(self._extract_get_atts_from_object(value))
        elif isinstance(obj, list):
            for item in obj:
                get_atts.update(self._extract_get_atts_from_object(item))
        
        return get_atts
    
    def _extract_cloud_provider(self, resource: Dict) -> CloudProvider:
        """Extract cloud provider from CloudFormation resource"""
        # CloudFormation is always AWS
        return CloudProvider.AWS


# Register the adapter
from .base import IaCAdapterFactory
IaCAdapterFactory.register_adapter(IaCType.CLOUDFORMATION, CloudFormationAdapter)
