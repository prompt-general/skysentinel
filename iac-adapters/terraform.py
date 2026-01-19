import json
import re
from typing import Dict, List, Any, Union, Optional, Set
from datetime import datetime
import logging

from .base import (
    IaCAdapter, IaCType, IaCPlan, IaCResource, IaCDependency, 
    IaCValidationResult, ResourceType, CloudProvider
)
from shared.models.events import ResourceReference


class TerraformAdapter(IaCAdapter):
    """Terraform IaC adapter"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def get_iac_type(self) -> IaCType:
        return IaCType.TERRAFORM
    
    def _get_resource_type_mapping(self) -> Dict[str, ResourceType]:
        """Map Terraform resource types to standardized types"""
        return {
            # Compute resources
            'aws_instance': ResourceType.COMPUTE,
            'aws_launch_template': ResourceType.COMPUTE,
            'aws_autoscaling_group': ResourceType.COMPUTE,
            'aws_ecs_service': ResourceType.COMPUTE,
            'aws_ecs_task_definition': ResourceType.COMPUTE,
            'aws_lambda_function': ResourceType.SERVERLESS,
            'azure_virtual_machine': ResourceType.COMPUTE,
            'google_compute_instance': ResourceType.COMPUTE,
            
            # Storage resources
            'aws_s3_bucket': ResourceType.STORAGE,
            'aws_ebs_volume': ResourceType.STORAGE,
            'aws_efs_file_system': ResourceType.STORAGE,
            'azure_storage_account': ResourceType.STORAGE,
            'azure_storage_container': ResourceType.STORAGE,
            'google_storage_bucket': ResourceType.STORAGE,
            
            # Network resources
            'aws_vpc': ResourceType.NETWORK,
            'aws_subnet': ResourceType.NETWORK,
            'aws_security_group': ResourceType.SECURITY,
            'aws_route_table': ResourceType.NETWORK,
            'aws_internet_gateway': ResourceType.NETWORK,
            'azure_virtual_network': ResourceType.NETWORK,
            'azure_subnet': ResourceType.NETWORK,
            'google_compute_network': ResourceType.NETWORK,
            
            # Database resources
            'aws_rds_instance': ResourceType.DATABASE,
            'aws_dynamodb_table': ResourceType.DATABASE,
            'aws_elasticache_cluster': ResourceType.DATABASE,
            'azure_sql_database': ResourceType.DATABASE,
            'google_sql_database': ResourceType.DATABASE,
            
            # Security resources
            'aws_iam_role': ResourceType.IDENTITY,
            'aws_iam_policy': ResourceType.SECURITY,
            'aws_iam_user': ResourceType.IDENTITY,
            'azure_role_definition': ResourceType.IDENTITY,
            'google_service_account': ResourceType.IDENTITY,
            
            # Container resources
            'aws_ecs_cluster': ResourceType.CONTAINER,
            'aws_eks_cluster': ResourceType.CONTAINER,
            'azure_kubernetes_cluster': ResourceType.CONTAINER,
            'google_container_cluster': ResourceType.CONTAINER,
            
            # Messaging resources
            'aws_sqs_queue': ResourceType.MESSAGING,
            'aws_sns_topic': ResourceType.MESSAGING,
            'azure_service_bus_queue': ResourceType.MESSAGING,
            'google_pubsub_topic': ResourceType.MESSAGING,
        }
    
    def _get_provider_mapping(self) -> Dict[str, CloudProvider]:
        """Map Terraform providers to CloudProvider enum"""
        return {
            'aws': CloudProvider.AWS,
            'awscc': CloudProvider.AWS,
            'azurerm': CloudProvider.AZURE,
            'google': CloudProvider.GCP,
            'gcp': CloudProvider.GCP,
            'kubernetes': CloudProvider.KUBERNETES,
            'helm': CloudProvider.KUBERNETES,
        }
    
    def parse(self, tfplan_json: Dict) -> List[ResourceReference]:
        """Parse Terraform plan JSON and return list of ResourceReferences"""
        resources = []
        
        # Terraform plan JSON structure: planned_values -> root_module -> resources
        root_module = tfplan_json.get('planned_values', {}).get('root_module', {})
        resources.extend(self._extract_resources_from_module(root_module))
        
        # Also check child modules
        for child_module in root_module.get('child_modules', []):
            resources.extend(self._extract_resources_from_module(child_module))
        
        return resources

    def _extract_resources_from_module(self, module: Dict) -> List[ResourceReference]:
        """Extract resources from a Terraform module"""
        resources = []
        for resource in module.get('resources', []):
            # Skip data resources
            if resource.get('mode', '') == 'data':
                continue
                
            normalized = self.normalize_resource(resource)
            if normalized:
                resources.append(normalized)
        return resources

    def normalize_resource(self, tf_resource: Dict) -> Optional[ResourceReference]:
        """Normalize a Terraform resource to our model."""
        resource_type = tf_resource.get('type', '')
        resource_name = tf_resource.get('name', '')
        resource_values = tf_resource.get('values', {})
        
        # Generate a unique ID for resource (using Terraform's address)
        address = tf_resource.get('address', '')
        
        # Map Terraform resource type to our resource type
        # Example: aws_s3_bucket -> aws:s3:bucket
        cloud, service, resource = self._parse_terraform_type(resource_type)
        
        if not cloud:
            return None
        
        # Construct an ARN-like ID (we don't have actual ARN until creation, so we use a placeholder)
        # For IaC, we use Terraform address as ID because it's unique within the plan.
        resource_id = f"terraform:{address}"
        
        # Extract tags if present
        tags = resource_values.get('tags', {})
        
        # Determine region (if available)
        region = resource_values.get('region', '')
        
        return ResourceReference(
            id=resource_id,
            type=f"{cloud}:{service}:{resource}",
            region=region,
            account=self._extract_account(resource_values),
            name=resource_name,
            tags=tags,
            properties=resource_values,
            metadata={
                'iac_type': 'terraform',
                'terraform_address': address,
                'terraform_type': resource_type,
                'terraform_name': resource_name,
                'mode': tf_resource.get('mode', 'managed'),
                'provider_name': tf_resource.get('provider_name', ''),
                'values': resource_values
            }
        )
    
    def _parse_terraform_type(self, tf_type: str) -> tuple:
        """Parse Terraform resource type to (cloud, service, resource)."""
        # Example: aws_s3_bucket -> (aws, s3, bucket)
        parts = tf_type.split('_')
        if len(parts) < 2:
            return (None, None, None)
        
        cloud = parts[0]
        service = parts[1]
        resource = '_'.join(parts[2:]) if len(parts) > 2 else ''
        
        return (cloud, service, resource)
    
    def _extract_account(self, values: Dict) -> Optional[str]:
        """Extract account ID from Terraform values (if available)."""
        # This might be in provider config or resource values
        # For AWS, we might have an 'account_id' attribute or it might be in the provider
        return values.get('account_id')
    
    def parse_plan(self, plan_content: Union[str, Dict]) -> IaCPlan:
        """Parse Terraform plan JSON output"""
        if isinstance(plan_content, str):
            try:
                plan_data = json.loads(plan_content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON plan content: {e}")
        else:
            plan_data = plan_content
        
        # Create plan object
        plan = IaCPlan(
            id=plan_data.get('configuration', {}).get('configuration', {}).get('root_module', {}).get('resources', [{}])[0].get('name', 'unknown'),
            iac_type=self.get_iac_type(),
            version=plan_data.get('terraform_version', 'unknown'),
            created_at=datetime.utcnow(),
            workspace=plan_data.get('configuration', {}).get('configuration', {}).get('root_module', {}).get('module_calls', {}).get('workspace', 'default'),
            metadata={
                'format_version': plan_data.get('format_version'),
                'planned_values': plan_data.get('planned_values', {}),
                'prior_state': plan_data.get('prior_state', {}),
                'configuration': plan_data.get('configuration', {})
            }
        )
        
        # Parse resources from planned values
        planned_resources = plan_data.get('planned_values', {}).get('root_module', {}).get('resources', [])
        for resource_data in planned_resources:
            resource = self._parse_resource_from_planned_values(resource_data)
            if resource:
                plan.resources.append(resource)
        
        # Parse resources from configuration
        config_resources = plan_data.get('configuration', {}).get('configuration', {}).get('root_module', {}).get('resources', [])
        for resource_data in config_resources:
            resource = self._parse_resource_from_configuration(resource_data)
            if resource:
                plan.resources.append(resource)
        
        # Parse resource changes
        resource_changes = plan_data.get('resource_changes', [])
        for change_data in resource_changes:
            resource = self._parse_resource_from_change(change_data)
            if resource:
                plan.resources.append(resource)
        
        # Extract dependencies
        dependencies = self.extract_dependencies(plan_data)
        for dep in dependencies:
            # Add dependencies to resources
            for resource in plan.resources:
                if resource.id == dep.source_id:
                    resource.dependencies.add(dep.target_id)
        
        return plan
    
    def parse_configuration(self, config_content: Union[str, Dict]) -> IaCPlan:
        """Parse Terraform configuration"""
        if isinstance(config_content, str):
            # This would require terraform-config-inspect or similar tool
            # For now, return a basic plan
            plan = IaCPlan(
                id='config-parse',
                iac_type=self.get_iac_type(),
                version='unknown',
                created_at=datetime.utcnow()
            )
            return plan
        else:
            return self.parse_plan(config_content)
    
    def extract_dependencies(self, iac_content: Dict) -> List[IaCDependency]:
        """Extract dependencies from Terraform plan"""
        dependencies = []
        
        # Extract from configuration
        config = iac_content.get('configuration', {}).get('configuration', {}).get('root_module', {})
        
        # Module dependencies
        module_calls = config.get('module_calls', {})
        for module_name, module_data in module_calls.items():
            module_resources = module_data.get('module', {}).get('resources', [])
            for resource in module_resources:
                # Extract explicit dependencies
                explicit_deps = resource.get('expressions', {}).get('depends_on', [])
                for dep in explicit_deps:
                    if isinstance(dep, list) and len(dep) > 0:
                        dependencies.append(IaCDependency(
                            source_id=f"{resource.get('type', '')}.{resource.get('name', '')}",
                            target_id=dep[0],
                            dependency_type='explicit'
                        ))
        
        # Resource dependencies
        resources = config.get('resources', [])
        for resource in resources:
            resource_id = f"{resource.get('type', '')}.{resource.get('name', '')}"
            
            # Extract from expressions
            expressions = resource.get('expressions', {})
            for key, expression in expressions.items():
                if isinstance(expression, dict) and 'references' in expression:
                    for ref in expression['references']:
                        dependencies.append(IaCDependency(
                            source_id=resource_id,
                            target_id=ref,
                            dependency_type='implicit',
                            property_path=key
                        ))
        
        # Extract from resource changes
        resource_changes = iac_content.get('resource_changes', [])
        for change in resource_changes:
            resource_id = change.get('address', '')
            
            # Check for dependencies in change
            change_deps = change.get('change', {}).get('before', {}).get('depends_on', [])
            for dep in change_deps:
                dependencies.append(IaCDependency(
                    source_id=resource_id,
                    target_id=dep,
                    dependency_type='explicit'
                ))
        
        return dependencies
    
    def validate_syntax(self, content: Union[str, Dict]) -> IaCValidationResult:
        """Validate Terraform plan syntax"""
        result = IaCValidationResult(is_valid=True)
        
        if isinstance(content, str):
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                result.is_valid = False
                result.errors.append(f"Invalid JSON: {e}")
                return result
        else:
            data = content
        
        # Check required fields
        if 'format_version' not in data:
            result.warnings.append("Missing format_version field")
        
        if 'terraform_version' not in data:
            result.warnings.append("Missing terraform_version field")
        
        # Validate resources
        resources = data.get('resource_changes', [])
        for resource in resources:
            if 'address' not in resource:
                result.errors.append(f"Resource missing address: {resource}")
                result.is_valid = False
            
            if 'type' not in resource:
                result.errors.append(f"Resource missing type: {resource}")
                result.is_valid = False
            
            if 'change' not in resource:
                result.errors.append(f"Resource missing change: {resource}")
                result.is_valid = False
        
        return result
    
    def _parse_resource_from_planned_values(self, resource_data: Dict) -> Optional[IaCResource]:
        """Parse resource from planned values section"""
        try:
            resource = self.normalize_resource(resource_data)
            if resource:
                return self._to_iac_resource(resource)
            return None
        except Exception as e:
            self.logger.warning(f"Failed to parse resource from planned values: {e}")
            return None
    
    def _parse_resource_from_configuration(self, resource_data: Dict) -> Optional[IaCResource]:
        """Parse resource from configuration section"""
        try:
            # Configuration resources don't have values, just expressions
            resource_type = resource_data.get('type', '')
            resource_name = resource_data.get('name', '')
            mode = resource_data.get('mode', 'managed')
            
            provider = self._extract_cloud_provider(resource_data)
            
            # Extract properties from expressions
            expressions = resource_data.get('expressions', {})
            properties = {}
            
            for key, expr in expressions.items():
                if isinstance(expr, dict) and 'constant_value' in expr:
                    properties[key] = expr['constant_value']
                elif isinstance(expr, dict) and 'references' in expr:
                    properties[key] = f"REF:{','.join(expr['references'])}"
            
            return IaCResource(
                id=f"{resource_type}.{resource_name}",
                type=resource_type,
                name=resource_name,
                provider=provider,
                resource_category=self._normalize_resource_type(resource_type),
                properties=self._sanitize_properties(properties),
                change_type='create',  # Configuration resources are typically creates
                metadata={
                    'mode': mode,
                    'source': 'configuration'
                }
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse resource from configuration: {e}")
            return None
    
    def _parse_resource_from_change(self, change_data: Dict) -> Optional[IaCResource]:
        """Parse resource from resource changes section"""
        try:
            address = change_data.get('address', '')
            resource_type = change_data.get('type', '')
            resource_name = change_data.get('name', '')
            mode = change_data.get('mode', 'managed')
            
            provider = self._extract_cloud_provider(change_data)
            
            # Extract values from change
            change = change_data.get('change', {})
            actions = change.get('actions', [])
            
            # Determine change type
            if 'create' in actions:
                change_type = 'create'
                values = change.get('after', {})
            elif 'delete' in actions:
                change_type = 'delete'
                values = change.get('before', {})
            elif 'update' in actions:
                change_type = 'update'
                values = change.get('after', {})
            else:
                change_type = 'read'
                values = change.get('after', {})
            
            return IaCResource(
                id=address,
                type=resource_type,
                name=resource_name,
                provider=provider,
                resource_category=self._normalize_resource_type(resource_type),
                properties=self._sanitize_properties(values),
                change_type=change_type,
                metadata={
                    'mode': mode,
                    'address': address,
                    'change_actions': actions,
                    'provider_name': change_data.get('provider_name', ''),
                    'source': 'resource_changes'
                }
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse resource from change: {e}")
            return None
    
    def _extract_cloud_provider(self, resource: Dict) -> CloudProvider:
        """Extract cloud provider from Terraform resource"""
        resource_type = resource.get('type', '')
        provider_name = resource.get('provider_name', '')
        
        # Check provider name first
        if provider_name:
            return self._normalize_provider(provider_name)
        
        # Check resource type prefix
        if resource_type.startswith('aws_'):
            return CloudProvider.AWS
        elif resource_type.startswith('azurerm_'):
            return CloudProvider.AZURE
        elif resource_type.startswith('google_'):
            return CloudProvider.GCP
        elif resource_type.startswith('kubernetes_') or resource_type.startswith('k8s_'):
            return CloudProvider.KUBERNETES
        
        return CloudProvider.AWS
    
    def _to_iac_resource(self, resource_ref: ResourceReference) -> IaCResource:
        """Convert ResourceReference to IaCResource"""
        return IaCResource(
            id=resource_ref.id,
            type=resource_ref.type,
            name=resource_ref.name,
            provider=self._extract_cloud_provider({'type': resource_ref.type}),
            resource_category=self._normalize_resource_type(resource_ref.type),
            properties=resource_ref.properties,
            metadata=resource_ref.metadata,
            change_type=resource_ref.metadata.get('change_type', 'create')
        )


# Register the adapter
from .base import IaCAdapterFactory
IaCAdapterFactory.register_adapter(IaCType.TERRAFORM, TerraformAdapter)
