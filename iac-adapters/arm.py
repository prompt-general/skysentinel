import json
from typing import Dict, List, Any, Union, Optional, Set
from datetime import datetime
import logging

from .base import (
    IaCAdapter, IaCType, IaCPlan, IaCResource, IaCDependency, 
    IaCValidationResult, ResourceType, CloudProvider
)
from shared.models.events import ResourceReference


class ARMAdapter(IaCAdapter):
    """Azure ARM Template IaC adapter"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def get_iac_type(self) -> IaCType:
        return IaCType.ARM_TEMPLATE
    
    def _get_resource_type_mapping(self) -> Dict[str, ResourceType]:
        """Map ARM resource types to standardized types"""
        return {
            # Compute resources
            'Microsoft.Compute/virtualMachines': ResourceType.COMPUTE,
            'Microsoft.Compute/availabilitySets': ResourceType.COMPUTE,
            'Microsoft.Compute/virtualMachineScaleSets': ResourceType.COMPUTE,
            'Microsoft.ContainerService/managedClusters': ResourceType.CONTAINER,
            'Microsoft.ContainerInstance/containerGroups': ResourceType.COMPUTE,
            'Microsoft.Web/serverfarms': ResourceType.COMPUTE,
            'Microsoft.Web/sites': ResourceType.COMPUTE,
            'Microsoft.Functions/functionApps': ResourceType.SERVERLESS,
            
            # Storage resources
            'Microsoft.Storage/storageAccounts': ResourceType.STORAGE,
            'Microsoft.Storage/storageAccounts/blobServices': ResourceType.STORAGE,
            'Microsoft.Storage/storageAccounts/fileServices': ResourceType.STORAGE,
            'Microsoft.Storage/storageAccounts/tableServices': ResourceType.STORAGE,
            'Microsoft.Storage/storageAccounts/queueServices': ResourceType.STORAGE,
            
            # Network resources
            'Microsoft.Network/virtualNetworks': ResourceType.NETWORK,
            'Microsoft.Network/subnets': ResourceType.NETWORK,
            'Microsoft.Network/networkInterfaces': ResourceType.NETWORK,
            'Microsoft.Network/publicIPAddresses': ResourceType.NETWORK,
            'Microsoft.Network/networkSecurityGroups': ResourceType.SECURITY,
            'Microsoft.Network/routeTables': ResourceType.NETWORK,
            'Microsoft.Network/virtualNetworkGateways': ResourceType.NETWORK,
            'Microsoft.Network/expressRouteCircuits': ResourceType.NETWORK,
            'Microsoft.Network/loadBalancers': ResourceType.NETWORK,
            
            # Database resources
            'Microsoft.Sql/servers': ResourceType.DATABASE,
            'Microsoft.Sql/databases': ResourceType.DATABASE,
            'Microsoft.Sql/elasticPools': ResourceType.DATABASE,
            'Microsoft.DBforPostgreSQL/servers': ResourceType.DATABASE,
            'Microsoft.DBforMySQL/servers': ResourceType.DATABASE,
            'Microsoft.DBforMariaDB/servers': ResourceType.DATABASE,
            'Microsoft.Cache/redis': ResourceType.DATABASE,
            'Microsoft.DocumentDB/databaseAccounts': ResourceType.DATABASE,
            'Microsoft.CosmosDB/databaseAccounts': ResourceType.DATABASE,
            
            # Security resources
            'Microsoft.Authorization/roleDefinitions': ResourceType.IDENTITY,
            'Microsoft.Authorization/roleAssignments': ResourceType.IDENTITY,
            'Microsoft.ManagedIdentity/userAssignedIdentities': ResourceType.IDENTITY,
            'Microsoft.KeyVault/vaults': ResourceType.SECURITY,
            'Microsoft.KeyVault/keys': ResourceType.SECURITY,
            'Microsoft.KeyVault/secrets': ResourceType.SECURITY,
            'Microsoft.Security/securitySolutions': ResourceType.SECURITY,
            'Microsoft.Security/locations': ResourceType.SECURITY,
            
            # Monitoring resources
            'Microsoft.Insights/components': ResourceType.MONITORING,
            'Microsoft.Insights/metricAlerts': ResourceType.MONITORING,
            'Microsoft.Insights/activityLogAlerts': ResourceType.MONITORING,
            'Microsoft.OperationalInsights/workspaces': ResourceType.MONITORING,
            'Microsoft.Monitor/accounts': ResourceType.MONITORING,
            
            # Messaging resources
            'Microsoft.ServiceBus/namespaces': ResourceType.MESSAGING,
            'Microsoft.ServiceBus/queues': ResourceType.MESSAGING,
            'Microsoft.ServiceBus/topics': ResourceType.MESSAGING,
            'Microsoft.EventGrid/topics': ResourceType.MESSAGING,
            'Microsoft.EventGrid/eventSubscriptions': ResourceType.MESSAGING,
            'Microsoft.EventHub/namespaces': ResourceType.MESSAGING,
            
            # Analytics resources
            'Microsoft.StreamAnalytics/streamingjobs': ResourceType.ANALYTICS,
            'Microsoft.DataFactory/factories': ResourceType.ANALYTICS,
            'Microsoft.Synapse/workspaces': ResourceType.ANALYTICS,
            'MachineLearningServices/workspaces': ResourceType.AI_ML,
            'Microsoft.MachineLearningServices/workspaces': ResourceType.AI_ML,
        }
    
    def _get_provider_mapping(self) -> Dict[str, CloudProvider]:
        """Map ARM providers to CloudProvider enum"""
        return {
            'Microsoft': CloudProvider.AZURE,
            'Microsoft.': CloudProvider.AZURE,
        }
    
    def parse(self, what_if_result: Dict) -> List[ResourceReference]:
        """Parse ARM Template What-If result and return list of ResourceReferences"""
        resources = []
        
        for change in what_if_result.get('changes', []):
            resource_type = change.get('resourceType', '')
            
            # Only process resources that are being created or updated
            change_type = change.get('changeType', '')
            if change_type not in ['Create', 'Modify', 'Delete']:
                continue
            
            normalized = self.normalize_resource(change)
            if normalized:
                resources.append(normalized)
        
        return resources

    def normalize_resource(self, arm_resource: Dict) -> Optional[ResourceReference]:
        """Normalize an ARM resource to our model."""
        resource_type = arm_resource.get('resourceType', '')
        
        # Example: Microsoft.Storage/storageAccounts -> azure:storage:storageaccount
        cloud, service, resource = self._parse_arm_type(resource_type)
        
        if not cloud:
            return None
        
        # Use the resource ID as the unique identifier
        resource_id = arm_resource.get('resourceId', '')
        
        # Extract tags (if available)
        tags = arm_resource.get('tags', {})
        
        # Extract region and subscription
        region = self._extract_region(resource_id)
        subscription = self._extract_subscription(resource_id)
        resource_name = self._extract_resource_name(resource_id)
        
        return ResourceReference(
            id=resource_id,
            type=f"{cloud}:{service}:{resource}",
            region=region,
            account=subscription,
            name=resource_name,
            tags=tags,
            properties=arm_resource.get('properties', {}),
            metadata={
                'iac_type': 'arm_template',
                'resource_type': resource_type,
                'change_type': arm_resource.get('changeType'),
                'resource_id': resource_id,
                'subscription_id': subscription,
                'resource_group': self._extract_resource_group(resource_id),
                'properties': arm_resource.get('properties', {})
            }
        )
    
    def _parse_arm_type(self, arm_type: str) -> tuple:
        """Parse ARM resource type to (cloud, service, resource)."""
        # Example: Microsoft.Storage/storageAccounts -> (azure, storage, storageaccount)
        if not arm_type.startswith('Microsoft.'):
            return (None, None, None)
        
        parts = arm_type.split('/')
        if len(parts) < 2:
            return (None, None, None)
        
        cloud = 'azure'
        service = parts[0].split('.')[1].lower()
        resource = parts[1].lower()
        
        return (cloud, service, resource)
    
    def _extract_region(self, resource_id: str) -> Optional[str]:
        """Extract region from ARM resource ID."""
        # Format: /subscriptions/{sub}/resourceGroups/{rg}/providers/{type}/{name}
        # Region might be in resource group name or need to be looked up
        # For now, we'll try to extract from common patterns
        parts = resource_id.split('/')
        for i, part in enumerate(parts):
            if part == 'resourceGroups' and i+1 < len(parts):
                rg_name = parts[i+1]
                # Common pattern: rg-{region}-{name}
                if rg_name.startswith('rg-') and '-' in rg_name:
                    return rg_name.split('-')[1]
        return None
    
    def _extract_subscription(self, resource_id: str) -> Optional[str]:
        """Extract subscription ID from ARM resource ID."""
        parts = resource_id.split('/')
        for i, part in enumerate(parts):
            if part == 'subscriptions' and i+1 < len(parts):
                return parts[i+1]
        return None
    
    def _extract_resource_group(self, resource_id: str) -> Optional[str]:
        """Extract resource group from ARM resource ID."""
        parts = resource_id.split('/')
        for i, part in enumerate(parts):
            if part == 'resourceGroups' and i+1 < len(parts):
                return parts[i+1]
        return None
    
    def _extract_resource_name(self, resource_id: str) -> str:
        """Extract resource name from ARM resource ID."""
        # The last part of the resource ID is typically the resource name
        parts = resource_id.split('/')
        return parts[-1] if parts else ''
    
    def parse_plan(self, plan_content: Union[str, Dict]) -> IaCPlan:
        """Parse ARM template or What-If result"""
        if isinstance(plan_content, str):
            try:
                template_data = json.loads(plan_content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid ARM template JSON: {e}")
        else:
            template_data = plan_content
        
        # Create plan object
        plan = IaCPlan(
            id=template_data.get('metadata', {}).get('templateName', 'arm-template'),
            iac_type=self.get_iac_type(),
            version=template_data.get('schema', 'unknown'),
            created_at=datetime.utcnow(),
            metadata={
                'schema': template_data.get('schema', ''),
                'contentVersion': template_data.get('contentVersion', ''),
                'parameters': template_data.get('parameters', {}),
                'variables': template_data.get('variables', {}),
                'functions': template_data.get('functions', {}),
                'outputs': template_data.get('outputs', {}),
                'metadata': template_data.get('metadata', {})
            }
        )
        
        # Parse resources
        resources = template_data.get('resources', [])
        for resource_data in resources:
            resource = self._parse_arm_resource(resource_data)
            if resource:
                plan.resources.append(resource)
        
        # Parse parameters
        parameters = template_data.get('parameters', {})
        plan.variables = {k: v.get('defaultValue', '') for k, v in parameters.items()}
        
        # Parse outputs
        outputs = template_data.get('outputs', {})
        plan.outputs = {k: v.get('value', '') for k, v in outputs.items()}
        
        # Extract dependencies
        dependencies = self.extract_dependencies(template_data)
        for dep in dependencies:
            for resource in plan.resources:
                if resource.id == dep.source_id:
                    resource.dependencies.add(dep.target_id)
        
        return plan
    
    def parse_configuration(self, config_content: Union[str, Dict]) -> IaCPlan:
        """Parse ARM template configuration"""
        return self.parse_plan(config_content)
    
    def extract_dependencies(self, iac_content: Dict) -> List[IaCDependency]:
        """Extract dependencies from ARM template"""
        dependencies = []
        resources = iac_content.get('resources', [])
        
        # Build resource lookup
        resource_lookup = {}
        for resource in resources:
            resource_name = resource.get('name', '')
            resource_type = resource.get('type', '')
            resource_lookup[resource_name] = resource_type
        
        for resource in resources:
            resource_name = resource.get('name', '')
            resource_type = resource.get('type', '')
            resource_properties = resource.get('properties', {})
            
            # Extract dependencies from resource properties
            deps = self._extract_dependencies_from_object(resource_properties, resource_lookup)
            for dep in deps:
                dependencies.append(IaCDependency(
                    source_id=f"{resource_type}.{resource_name}",
                    target_id=f"{dep['type']}.{dep['name']}",
                    dependency_type='reference',
                    property_path=dep['path']
                ))
            
            # Extract explicit dependencies
            depends_on = resource.get('dependsOn', [])
            if isinstance(depends_on, str):
                depends_on = [depends_on]
            
            for dep in depends_on:
                if isinstance(dep, str):
                    # Simple dependency by name
                    if dep in resource_lookup:
                        dependencies.append(IaCDependency(
                            source_id=f"{resource_type}.{resource_name}",
                            target_id=f"{resource_lookup[dep]}.{dep}",
                            dependency_type='explicit'
                        ))
                elif isinstance(dep, dict):
                    # Complex dependency with resource type
                    dep_type = dep.get('type', '')
                    dep_name = dep.get('name', '')
                    dependencies.append(IaCDependency(
                        source_id=f"{resource_type}.{resource_name}",
                        target_id=f"{dep_type}.{dep_name}",
                        dependency_type='explicit'
                    ))
        
        return dependencies
    
    def validate_syntax(self, content: Union[str, Dict]) -> IaCValidationResult:
        """Validate ARM template syntax"""
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
        if '$schema' not in data:
            result.warnings.append("Missing $schema field")
        
        if 'resources' not in data:
            result.errors.append("ARM template must have resources section")
            result.is_valid = False
        
        # Validate resources
        resources = data.get('resources', [])
        for resource in resources:
            if 'type' not in resource:
                result.errors.append(f"Resource missing type: {resource}")
                result.is_valid = False
            
            if 'name' not in resource:
                result.errors.append(f"Resource missing name: {resource}")
                result.is_valid = False
            
            if not isinstance(resource.get('properties', {}), dict):
                result.errors.append(f"Resource properties must be a dictionary: {resource}")
                result.is_valid = False
        
        # Validate parameters
        parameters = data.get('parameters', {})
        for param_name, param_data in parameters.items():
            if not isinstance(param_data, dict):
                result.errors.append(f"Parameter {param_name} must be a dictionary")
                result.is_valid = False
        
        # Validate outputs
        outputs = data.get('outputs', {})
        for output_name, output_data in outputs.items():
            if not isinstance(output_data, dict):
                result.errors.append(f"Output {output_name} must be a dictionary")
                result.is_valid = False
            elif 'value' not in output_data and 'reference' not in output_data:
                result.errors.append(f"Output {output_name} missing value or reference")
                result.is_valid = False
        
        return result
    
    def _parse_arm_resource(self, resource_data: Dict) -> Optional[IaCResource]:
        """Parse ARM resource"""
        try:
            resource_type = resource_data.get('type', '')
            resource_name = resource_data.get('name', '')
            resource_properties = resource_data.get('properties', {})
            
            # Add ARM-specific properties
            arm_properties = {
                'resource_type': resource_type,
                'resource_name': resource_name,
                'location': resource_data.get('location', ''),
                'api_version': resource_data.get('apiVersion', ''),
                **resource_properties
            }
            
            # Extract resource ID for identification
            resource_id = f"{resource_type}/{resource_name}"
            
            return IaCResource(
                id=resource_id,
                type=resource_type,
                name=resource_name,
                provider=CloudProvider.AZURE,
                resource_category=self._normalize_resource_type(resource_type),
                properties=self._sanitize_properties(arm_properties),
                change_type='create',
                metadata={
                    'resource_type': resource_type,
                    'resource_name': resource_name,
                    'location': resource_data.get('location', ''),
                    'api_version': resource_data.get('apiVersion', ''),
                    'depends_on': resource_data.get('dependsOn', []),
                    'comments': resource_data.get('comments', '')
                }
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse ARM resource: {e}")
            return None
    
    def _extract_dependencies_from_object(self, obj: Any, resource_lookup: Dict[str, str]) -> List[Dict[str, str]]:
        """Extract dependencies from ARM template object"""
        dependencies = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Check for reference expressions
                if isinstance(value, str) and value.startswith('[reference('):
                    # Extract reference: [reference('resourceName')]
                    ref_match = value.match(r"\[reference\('([^']+)'\)\]")
                    if ref_match:
                        ref_name = ref_match.group(1)
                        if ref_name in resource_lookup:
                            dependencies.append({
                                'name': ref_name,
                                'type': resource_lookup[ref_name],
                                'path': key
                            })
                
                # Check for resource ID expressions
                elif isinstance(value, str) and 'resourceId(' in value:
                    # Extract resourceId: resourceId('Microsoft.Storage/storageAccounts', 'accountName')
                    # This is more complex and would need additional parsing
                    pass
                
                # Recurse into nested objects
                deps = self._extract_dependencies_from_object(value, resource_lookup)
                dependencies.extend(deps)
        
        elif isinstance(obj, list):
            for item in obj:
                deps = self._extract_dependencies_from_object(item, resource_lookup)
                dependencies.extend(deps)
        
        return dependencies
    
    def _extract_cloud_provider(self, resource: Dict) -> CloudProvider:
        """Extract cloud provider from ARM resource"""
        # ARM is always Azure
        return CloudProvider.AZURE
    
    def _to_iac_resource(self, resource_ref: ResourceReference) -> IaCResource:
        """Convert ResourceReference to IaCResource"""
        return IaCResource(
            id=resource_ref.id,
            type=resource_ref.type,
            name=resource_ref.name,
            provider=CloudProvider.AZURE,
            resource_category=self._normalize_resource_type(resource_ref.type),
            properties=resource_ref.properties,
            metadata=resource_ref.metadata,
            change_type=resource_ref.metadata.get('change_type', 'create')
        )
