import json
import re
from typing import Dict, List, Any, Union, Optional, Set
from datetime import datetime
import logging

from .base import (
    IaCAdapter, IaCType, IaCPlan, IaCResource, IaCDependency, 
    IaCValidationResult, ResourceType, CloudProvider
)


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
    
    def normalize_resource(self, raw_resource: Dict) -> IaCResource:
        """Normalize Terraform resource to unified model"""
        resource_type = raw_resource.get('type', '')
        resource_name = raw_resource.get('name', '')
        mode = raw_resource.get('mode', 'managed')
        
        # Extract provider from resource type
        provider = self._extract_cloud_provider(raw_resource)
        
        # Create resource ID
        resource_id = f"{resource_type}.{resource_name}"
        
        # Extract properties
        values = raw_resource.get('values', {})
        if mode == 'data':
            values = raw_resource.get('values', {})
        
        # Extract change type
        change_actions = raw_resource.get('change', {}).get('actions', [])
        if 'create' in change_actions:
            change_type = 'create'
        elif 'delete' in change_actions:
            change_type = 'delete'
        elif 'update' in change_actions:
            change_type = 'update'
        else:
            change_type = 'read'
        
        return IaCResource(
            id=resource_id,
            type=resource_type,
            name=resource_name,
            provider=provider,
            resource_category=self._normalize_resource_type(resource_type),
            properties=self._sanitize_properties(values),
            change_type=change_type,
            metadata={
                'mode': mode,
                'address': raw_resource.get('address', ''),
                'index': raw_resource.get('index'),
                'provider_name': raw_resource.get('provider_name', ''),
                'change_actions': change_actions
            }
        )
    
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
            return resource
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


# Register the adapter
from .base import IaCAdapterFactory
IaCAdapterFactory.register_adapter(IaCType.TERRAFORM, TerraformAdapter)
