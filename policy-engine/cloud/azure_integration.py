from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.resource.policy import PolicyClient
from azure.mgmt.resource.policy.models import (
    PolicyAssignment, 
    PolicyDefinition, 
    ParameterDefinitionsValue,
    ParameterType,
    PolicyMode,
    EnforcementMode
)
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.sql import SqlManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.core.exceptions import AzureError
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from ..schemas.policy import Policy, ActionType, EnforcementMode

logger = logging.getLogger(__name__)


class AzureIntegration:
    """Azure integration layer for SkySentinel policy engine"""
    
    def __init__(self, subscription_id: str, credential_config: Optional[Dict] = None):
        self.subscription_id = subscription_id
        
        # Initialize credentials
        if credential_config:
            # Use service principal credentials
            self.credential = ClientSecretCredential(
                tenant_id=credential_config.get('tenant_id'),
                client_id=credential_config.get('client_id'),
                client_secret=credential_config.get('client_secret')
            )
        else:
            # Use default Azure credential
            self.credential = DefaultAzureCredential()
        
        # Initialize Azure clients
        self.policy_client = PolicyClient(self.credential, subscription_id)
        self.resource_client = ResourceManagementClient(self.credential, subscription_id)
        self.storage_client = StorageManagementClient(self.credential, subscription_id)
        self.compute_client = ComputeManagementClient(self.credential, subscription_id)
        self.sql_client = SqlManagementClient(self.credential, subscription_id)
        self.network_client = NetworkManagementClient(self.credential, subscription_id)
        
        # Resource type mappings
        self.resource_type_map = {
            'azure:blob:container': 'Microsoft.Storage/storageAccounts/blobServices/containers',
            'azure:storage:account': 'Microsoft.Storage/storageAccounts',
            'azure:vm:virtualmachine': 'Microsoft.Compute/virtualMachines',
            'azure:vm:scaleSet': 'Microsoft.Compute/virtualMachineScaleSets',
            'azure:sql:server': 'Microsoft.Sql/servers',
            'azure:sql:database': 'Microsoft.Sql/servers/databases',
            'azure:network:vnet': 'Microsoft.Network/virtualNetworks',
            'azure:network:subnet': 'Microsoft.Network/virtualNetworks/subnets',
            'azure:network:nsg': 'Microsoft.Network/networkSecurityGroups',
            'azure:network:publicip': 'Microsoft.Network/publicIPAddresses',
            'azure:web:app': 'Microsoft.Web/sites',
            'azure:web:plan': 'Microsoft.Web/serverfarms',
            'azure:keyvault:vault': 'Microsoft.KeyVault/vaults',
            'azure:container:registry': 'Microsoft.ContainerRegistry/registries',
            'azure:container:group': 'Microsoft.ContainerInstance/containerGroups',
            'azure:kubernetes:cluster': 'Microsoft.ContainerService/managedClusters',
            'azure:cosmos:account': 'Microsoft.DocumentDB/databaseAccounts',
            'azure:eventgrid:topic': 'Microsoft.EventGrid/topics',
            'azure:eventhub:namespace': 'Microsoft.EventHub/namespaces',
            'azure:servicebus:namespace': 'Microsoft.ServiceBus/namespaces',
        }
        
        # Policy effect mappings
        self.effect_map = {
            EnforcementMode.INLINE_DENY: 'deny',
            EnforcementMode.POST_EVENT: 'audit',
            EnforcementMode.AUDIT_ONLY: 'audit',
            EnforcementMode.SCHEDULED: 'audit',
            EnforcementMode.PRE_DEPLOYMENT: 'deny'
        }
    
    def create_policy_definition(self, policy: Policy) -> str:
        """Create Azure Policy definition from SkySentinel policy"""
        try:
            policy_rule = self.generate_policy_rule(policy)
            parameters = self._create_parameters(policy)
            
            policy_definition = PolicyDefinition(
                policy_type='Custom',
                mode=PolicyMode.INDEXED,
                display_name=policy.name,
                description=policy.description or f'SkySentinel policy: {policy.name}',
                metadata={
                    'category': 'SkySentinel',
                    'version': policy.version,
                    'severity': policy.severity,
                    'created_by': 'SkySentinel',
                    'policy_id': policy.id
                },
                parameters=parameters,
                policy_rule=policy_rule
            )
            
            # Generate unique policy name
            azure_policy_name = f"skysentinel-{policy.name.lower().replace(' ', '-')}-{policy.id[-8:]}"
            
            definition = self.policy_client.policy_definitions.create_or_update_at_subscription(
                azure_policy_name,
                policy_definition
            )
            
            logger.info(f"Created Azure Policy definition: {definition.name}")
            return definition.id
            
        except AzureError as e:
            logger.error(f"Azure API error creating policy: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create Azure Policy: {e}")
            raise
    
    def assign_policy(self, definition_id: str, scope: Optional[str] = None, 
                     enforcement_mode: str = 'Default') -> str:
        """Assign policy to a scope (subscription, resource group)"""
        try:
            # Default to subscription level if no scope provided
            if not scope:
                scope = f"/subscriptions/{self.subscription_id}"
            
            assignment_name = f"skysentinel-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            assignment = PolicyAssignment(
                display_name=f'SkySentinel Assignment - {datetime.utcnow().strftime("%Y-%m-%d")}',
                description='SkySentinel automated policy assignment',
                policy_definition_id=definition_id,
                enforcement_mode=enforcement_mode,
                metadata={
                    'assigned_by': 'SkySentinel',
                    'assignment_date': datetime.utcnow().isoformat()
                },
                parameters=self._get_assignment_parameters()
            )
            
            result = self.policy_client.policy_assignments.create(
                scope,
                assignment_name,
                assignment
            )
            
            logger.info(f"Created Azure Policy assignment: {result.name}")
            return result.id
            
        except AzureError as e:
            logger.error(f"Azure API error assigning policy: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to assign Azure Policy: {e}")
            raise
    
    def generate_policy_rule(self, policy: Policy) -> Dict:
        """Generate Azure Policy rule from SkySentinel policy"""
        try:
            resource_types = policy.resources.resource_types
            conditions = policy.condition
            
            # Convert to Azure Policy format
            policy_rule = {
                "if": {
                    "allOf": []
                },
                "then": {
                    "effect": self._get_policy_effect(policy)
                }
            }
            
            # Add resource type conditions
            azure_types = []
            for rtype in resource_types:
                azure_type = self._map_to_azure_type(rtype)
                if azure_type:
                    azure_types.append(azure_type)
            
            if azure_types:
                if len(azure_types) == 1:
                    policy_rule["if"]["allOf"].append({
                        "field": "type",
                        "equals": azure_types[0]
                    })
                else:
                    policy_rule["if"]["allOf"].append({
                        "field": "type",
                        "in": azure_types
                    })
            
            # Add tag conditions
            if policy.resources.tags:
                for key, value in policy.resources.tags.items():
                    if '|' in str(value):
                        # Handle OR logic in tag values
                        values = [v.strip() for v in str(value).split('|')]
                        policy_rule["if"]["allOf"].append({
                            "field": f"tags['{key}']",
                            "in": values
                        })
                    else:
                        policy_rule["if"]["allOf"].append({
                            "field": f"tags['{key}']",
                            "equals": value
                        })
            
            # Add location/region conditions
            if policy.resources.region:
                policy_rule["if"]["allOf"].append({
                    "field": "location",
                    "equals": policy.resources.region
                })
            
            # Convert SkySentinel conditions to Azure Policy conditions
            if hasattr(conditions, 'all') and conditions.all:
                for condition in conditions.all:
                    azure_condition = self._convert_condition_to_azure(condition)
                    if azure_condition:
                        policy_rule["if"]["allOf"].append(azure_condition)
            elif hasattr(conditions, 'any') and conditions.any:
                # Convert ANY to OR condition
                or_conditions = []
                for condition in conditions.any:
                    azure_condition = self._convert_condition_to_azure(condition)
                    if azure_condition:
                        or_conditions.append(azure_condition)
                
                if or_conditions:
                    if len(or_conditions) == 1:
                        policy_rule["if"]["allOf"].append(or_conditions[0])
                    else:
                        policy_rule["if"]["allOf"].append({
                            "anyOf": or_conditions
                        })
            elif isinstance(conditions, dict):
                # Handle legacy format
                azure_condition = self._convert_dict_condition_to_azure(conditions)
                if azure_condition:
                    policy_rule["if"]["allOf"].append(azure_condition)
            
            # If no conditions, add a catch-all
            if not policy_rule["if"]["allOf"]:
                policy_rule["if"] = {"field": "type", "exists": "true"}
            
            return policy_rule
            
        except Exception as e:
            logger.error(f"Error generating Azure Policy rule: {e}")
            raise
    
    def _convert_condition_to_azure(self, condition) -> Optional[Dict]:
        """Convert SkySentinel condition to Azure Policy condition"""
        try:
            if hasattr(condition, 'field') and condition.field:
                field = condition.field.field
                operator = condition.field.operator
                value = condition.field.value
                
                # Map field names to Azure Policy fields
                azure_field = self._map_field_to_azure(field)
                if not azure_field:
                    return None
                
                # Convert operators
                azure_condition = {"field": azure_field}
                
                if operator == "eq":
                    azure_condition["equals"] = value
                elif operator == "ne":
                    azure_condition["notEquals"] = value
                elif operator == "contains":
                    azure_condition["contains"] = value
                elif operator == "not_contains":
                    azure_condition["notContains"] = value
                elif operator == "in":
                    azure_condition["in"] = value
                elif operator == "not_in":
                    azure_condition["notIn"] = value
                elif operator == "exists":
                    azure_condition["exists"] = "true"
                elif operator == "not_exists":
                    azure_condition["exists"] = "false"
                elif operator == "gt":
                    azure_condition["greater"] = value
                elif operator == "gte":
                    azure_condition["greaterOrEquals"] = value
                elif operator == "lt":
                    azure_condition["less"] = value
                elif operator == "lte":
                    azure_condition["lessOrEquals"] = value
                else:
                    logger.warning(f"Unsupported operator: {operator}")
                    return None
                
                return azure_condition
                
        except Exception as e:
            logger.error(f"Error converting condition: {e}")
        
        return None
    
    def _convert_dict_condition_to_azure(self, condition: Dict) -> Optional[Dict]:
        """Convert dictionary condition to Azure Policy format"""
        try:
            if 'field' in condition:
                field = condition['field']
                operator = condition.get('operator', 'eq')
                value = condition.get('value')
                
                azure_field = self._map_field_to_azure(field)
                if not azure_field:
                    return None
                
                azure_condition = {"field": azure_field}
                
                if operator == "equals" or operator == "eq":
                    azure_condition["equals"] = value
                elif operator == "not_equals" or operator == "ne":
                    azure_condition["notEquals"] = value
                elif operator == "contains":
                    azure_condition["contains"] = value
                elif operator == "in":
                    azure_condition["in"] = value
                elif operator == "exists":
                    azure_condition["exists"] = "true"
                else:
                    azure_condition["equals"] = value
                
                return azure_condition
                
        except Exception as e:
            logger.error(f"Error converting dict condition: {e}")
        
        return None
    
    def _map_field_to_azure(self, field: str) -> Optional[str]:
        """Map SkySentinel field to Azure Policy field"""
        field_mappings = {
            'resource.type': 'type',
            'resource.name': 'name',
            'resource.location': 'location',
            'resource.tags': 'tags',
            'resource.properties': 'properties',
            'tags.env': "tags['env']",
            'tags.environment': "tags['environment']",
            'tags.classification': "tags['classification']",
            'tags.owner': "tags['owner']",
            'properties.publicRead': 'properties.publicRead',
            'properties.allowPublicAccess': 'properties.allowPublicAccess',
            'properties.networkAcls': 'properties.networkAcls',
            'properties.accessTier': 'properties.accessTier',
            'properties.sku.tier': 'properties.sku.tier',
            'properties.sku.name': 'properties.sku.name',
        }
        
        return field_mappings.get(field, field)
    
    def _get_policy_effect(self, policy: Policy) -> str:
        """Get Azure Policy effect based on SkySentinel enforcement mode"""
        runtime_mode = policy.enforcement.get('runtime', {}).get('mode', EnforcementMode.POST_EVENT)
        return self.effect_map.get(runtime_mode, 'audit')
    
    def _map_to_azure_type(self, sky_type: str) -> str:
        """Map SkySentinel resource type to Azure resource type"""
        return self.resource_type_map.get(sky_type, '')
    
    def _create_parameters(self, policy: Policy) -> Dict[str, ParameterDefinitionsValue]:
        """Create parameters for Azure Policy"""
        parameters = {}
        
        # Add effect parameter
        parameters["effect"] = ParameterDefinitionsValue(
            type=ParameterType.STRING,
            allowed_values=["audit", "deny", "disabled"],
            default_value=self._get_policy_effect(policy),
            metadata={
                "displayName": "Effect",
                "description": "The effect of the policy"
            }
        )
        
        # Add parameters based on policy conditions
        if policy.resources.tags:
            for key, value in policy.resources.tags.items():
                if '|' in str(value):
                    # Create parameter for OR values
                    param_name = f"{key}Value"
                    parameters[param_name] = ParameterDefinitionsValue(
                        type=ParameterType.STRING,
                        allowed_values=[v.strip() for v in str(value).split('|')],
                        default_value=v.strip().split('|')[0],
                        metadata={
                            "displayName": f"{key.title()} Value",
                            "description": f"Allowed values for {key} tag"
                        }
                    )
        
        return parameters
    
    def _get_assignment_parameters(self) -> Dict[str, Any]:
        """Get parameters for policy assignment"""
        return {
            "effect": self.effect_map.get(EnforcementMode.POST_EVENT, 'audit')
        }
    
    def get_resource_compliance(self, resource_id: str) -> Dict[str, Any]:
        """Get compliance status for a specific resource"""
        try:
            # Parse resource ID to get resource type and name
            resource_info = self._parse_resource_id(resource_id)
            if not resource_info:
                return {"compliant": False, "error": "Invalid resource ID"}
            
            # Get policy states for the resource
            policy_states = self.policy_client.policy_states.list_query_results_for_resource(
                resource_id
            )
            
            compliance_info = {
                "resource_id": resource_id,
                "compliant": True,
                "violations": [],
                "last_evaluated": datetime.utcnow().isoformat()
            }
            
            for state in policy_states:
                if state.is_compliant is False:
                    compliance_info["compliant"] = False
                    compliance_info["violations"].append({
                        "policy_definition_id": state.policy_definition_id,
                        "policy_assignment_id": state.policy_assignment_id,
                        "effect": state.effect,
                        "timestamp": state.timestamp.isoformat() if state.timestamp else None
                    })
            
            return compliance_info
            
        except AzureError as e:
            logger.error(f"Azure API error getting compliance: {e}")
            return {"compliant": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Error getting resource compliance: {e}")
            return {"compliant": False, "error": str(e)}
    
    def _parse_resource_id(self, resource_id: str) -> Optional[Dict]:
        """Parse Azure resource ID to extract components"""
        try:
            # Azure resource ID format: /subscriptions/{subId}/resourceGroups/{rgName}/providers/{provider}/{resourceType}/{resourceName}
            parts = resource_id.split('/')
            if len(parts) < 8:
                return None
            
            return {
                "subscription_id": parts[2],
                "resource_group": parts[4],
                "provider": parts[6],
                "resource_type": parts[7],
                "resource_name": parts[8] if len(parts) > 8 else ""
            }
        except Exception:
            return None
    
    def remediate_resource(self, resource_id: str, action: Dict[str, Any]) -> bool:
        """Execute remediation action on a resource"""
        try:
            resource_info = self._parse_resource_id(resource_id)
            if not resource_info:
                logger.error(f"Invalid resource ID: {resource_id}")
                return False
            
            action_type = action.get('type')
            
            if action_type == ActionType.TAG:
                return self._apply_tags(resource_info, action.get('parameters', {}))
            elif action_type == ActionType.STOP:
                return self._stop_resource(resource_info)
            elif action_type == ActionType.DISABLE:
                return self._disable_resource(resource_info)
            elif action_type == ActionType.DELETE:
                return self._delete_resource(resource_info)
            else:
                logger.warning(f"Unsupported action type: {action_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error remediating resource {resource_id}: {e}")
            return False
    
    def _apply_tags(self, resource_info: Dict, parameters: Dict) -> bool:
        """Apply tags to a resource"""
        try:
            tags = parameters.get('tags', {})
            if not tags:
                return True
            
            # Get resource group client
            resource_group = resource_info['resource_group']
            resource_name = resource_info['resource_name']
            provider = resource_info['provider']
            resource_type = resource_info['resource_type']
            
            # Get existing resource
            if provider == 'Microsoft.Storage' and 'storageAccounts' in resource_type:
                storage_account = self.storage_client.storage_accounts.get_properties(
                    resource_group, resource_name
                )
                # Update tags
                if storage_account.tags:
                    storage_account.tags.update(tags)
                else:
                    storage_account.tags = tags
                
                # Apply changes
                poller = self.storage_client.storage_accounts.begin_update(
                    resource_group, resource_name, storage_account
                )
                poller.wait()
                
            elif provider == 'Microsoft.Compute' and 'virtualMachines' in resource_type:
                vm = self.compute_client.virtual_machines.get(
                    resource_group, resource_name
                )
                if vm.tags:
                    vm.tags.update(tags)
                else:
                    vm.tags = tags
                
                poller = self.compute_client.virtual_machines.begin_create_or_update(
                    resource_group, resource_name, vm
                )
                poller.wait()
            
            logger.info(f"Applied tags to resource {resource_info['resource_name']}")
            return True
            
        except Exception as e:
            logger.error(f"Error applying tags: {e}")
            return False
    
    def _stop_resource(self, resource_info: Dict) -> bool:
        """Stop a resource"""
        try:
            resource_group = resource_info['resource_group']
            resource_name = resource_info['resource_name']
            provider = resource_info['provider']
            resource_type = resource_info['resource_type']
            
            if provider == 'Microsoft.Compute' and 'virtualMachines' in resource_type:
                poller = self.compute_client.virtual_machines.begin_power_off(
                    resource_group, resource_name
                )
                poller.wait()
                logger.info(f"Stopped VM {resource_name}")
                return True
            
        except Exception as e:
            logger.error(f"Error stopping resource: {e}")
            return False
    
    def _disable_resource(self, resource_info: Dict) -> bool:
        """Disable a resource"""
        # Implementation depends on resource type
        logger.info(f"Disable action not implemented for {resource_info['resource_type']}")
        return False
    
    def _delete_resource(self, resource_info: Dict) -> bool:
        """Delete a resource"""
        try:
            resource_group = resource_info['resource_group']
            resource_name = resource_info['resource_name']
            provider = resource_info['provider']
            resource_type = resource_info['resource_type']
            
            # This is a dangerous operation - implement with caution
            logger.warning(f"Delete operation requested for {resource_name} - not implemented")
            return False
            
        except Exception as e:
            logger.error(f"Error deleting resource: {e}")
            return False
    
    def list_policy_assignments(self, scope: Optional[str] = None) -> List[Dict]:
        """List policy assignments in a scope"""
        try:
            if not scope:
                scope = f"/subscriptions/{self.subscription_id}"
            
            assignments = self.policy_client.policy_assignments.list_for_scope(scope)
            
            result = []
            for assignment in assignments:
                result.append({
                    "id": assignment.id,
                    "name": assignment.name,
                    "display_name": assignment.display_name,
                    "policy_definition_id": assignment.policy_definition_id,
                    "enforcement_mode": assignment.enforcement_mode,
                    "scope": assignment.scope
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing policy assignments: {e}")
            return []
    
    def get_policy_definitions(self) -> List[Dict]:
        """Get all SkySentinel policy definitions"""
        try:
            definitions = self.policy_client.policy_definitions.list_built_in()
            
            result = []
            for definition in definitions:
                if (definition.metadata and 
                    isinstance(definition.metadata, dict) and
                    definition.metadata.get('created_by') == 'SkySentinel'):
                    
                    result.append({
                        "id": definition.id,
                        "name": definition.name,
                        "display_name": definition.display_name,
                        "description": definition.description,
                        "policy_rule": definition.policy_rule,
                        "parameters": definition.parameters
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting policy definitions: {e}")
            return []
