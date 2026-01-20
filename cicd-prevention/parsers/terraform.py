"""
Terraform IaC Parser

This module provides Terraform-specific parsing functionality.
"""

import json
import re
from typing import Dict, List, Any, Optional, Union
from .base import IaCParser, IaCPlan, IaCResource, IaCDependency, CloudProvider, ChangeType


class TerraformParser(IaCParser):
    """Terraform IaC parser"""
    
    def parse(self, content: Union[str, Dict]) -> IaCPlan:
        """Parse Terraform content and return unified plan"""
        parsed_content = self._parse_content(content)
        
        # Determine if this is a plan or configuration
        if self._is_terraform_plan(parsed_content):
            return self._parse_terraform_plan(parsed_content)
        else:
            return self._parse_terraform_config(parsed_content)
    
    def extract_resources(self, content: Dict) -> List[IaCResource]:
        """Extract resources from Terraform content"""
        resources = []
        
        if self._is_terraform_plan(content):
            resources.extend(self._extract_plan_resources(content))
        else:
            resources.extend(self._extract_config_resources(content))
        
        return resources
    
    def extract_dependencies(self, content: Dict) -> List[IaCDependency]:
        """Extract dependencies from Terraform content"""
        dependencies = []
        
        if self._is_terraform_plan(content):
            dependencies.extend(self._extract_plan_dependencies(content))
        else:
            dependencies.extend(self._extract_config_dependencies(content))
        
        return dependencies
    
    def detect_format(self, content: Union[str, Dict]) -> bool:
        """Detect if content is Terraform format"""
        if isinstance(content, str):
            # Check for Terraform-specific keywords
            terraform_indicators = [
                'resource "',
                'terraform {',
                'provider "',
                'module "',
                'variable "',
                'output "'
            ]
            
            content_lower = content.lower()
            return any(indicator in content_lower for indicator in terraform_indicators)
        
        elif isinstance(content, dict):
            # Check for Terraform plan structure
            terraform_keys = [
                'planned_values',
                'resource_changes',
                'configuration',
                'prior_state',
                'terraform_version'
            ]
            
            return any(key in content for key in terraform_keys)
        
        return False
    
    def _parse_terraform_plan(self, content: Dict) -> IaCPlan:
        """Parse Terraform plan JSON"""
        plan_id = self._generate_plan_id('terraform')
        timestamp = content.get('terraform_version', 'unknown')
        
        # Extract resources from planned values and resource changes
        resources = []
        resources.extend(self._extract_plan_resources(content))
        
        # Extract dependencies
        dependencies = self._extract_plan_dependencies(content)
        
        return IaCPlan(
            id=plan_id,
            source_type='terraform',
            source_content=content,
            resources=resources,
            dependencies=dependencies,
            timestamp=timestamp,
            metadata={
                'terraform_version': content.get('terraform_version'),
                'format_version': content.get('format_version'),
                'planned_values_hash': self._calculate_hash(content.get('planned_values', {})),
                'configuration_hash': self._calculate_hash(content.get('configuration', {}))
            }
        )
    
    def _parse_terraform_config(self, content: Dict) -> IaCPlan:
        """Parse Terraform configuration (HCL converted to JSON)"""
        plan_id = self._generate_plan_id('terraform')
        timestamp = 'config'
        
        # Extract resources from configuration
        resources = self._extract_config_resources(content)
        
        # Extract dependencies
        dependencies = self._extract_config_dependencies(content)
        
        return IaCPlan(
            id=plan_id,
            source_type='terraform',
            source_content=content,
            resources=resources,
            dependencies=dependencies,
            timestamp=timestamp,
            metadata={
                'format': 'configuration',
                'provider_count': len(content.get('provider', {})),
                'resource_count': len(content.get('resource', {})),
                'variable_count': len(content.get('variable', {}))
            }
        )
    
    def _extract_plan_resources(self, content: Dict) -> List[IaCResource]:
        """Extract resources from Terraform plan"""
        resources = []
        
        # Extract from planned values
        planned_values = content.get('planned_values', {})
        resources.extend(self._extract_resources_from_planned_values(planned_values))
        
        # Extract from resource changes
        resource_changes = content.get('resource_changes', [])
        resources.extend(self._extract_resources_from_changes(resource_changes))
        
        return resources
    
    def _extract_resources_from_planned_values(self, planned_values: Dict) -> List[IaCResource]:
        """Extract resources from Terraform planned values"""
        resources = []
        
        def extract_from_module(module_data: Dict, module_path: str = ""):
            # Extract resources from module
            module_resources = module_data.get('resources', {})
            for resource_name, resource_data in module_resources.items():
                if isinstance(resource_data, list):
                    for i, resource_instance in enumerate(resource_data):
                        resource = self._create_resource_from_planned_value(
                            resource_instance, resource_name, module_path, i
                        )
                        if resource:
                            resources.append(resource)
                else:
                    resource = self._create_resource_from_planned_value(
                        resource_data, resource_name, module_path
                    )
                    if resource:
                        resources.append(resource)
            
            # Recursively extract from child modules
            child_modules = module_data.get('child_modules', {})
            for child_name, child_data in child_modules.items():
                child_path = f"{module_path}.{child_name}" if module_path else child_name
                extract_from_module(child_data, child_path)
        
        # Start extraction from root module
        root_module = planned_values.get('root_module', {})
        extract_from_module(root_module)
        
        return resources
    
    def _create_resource_from_planned_value(self, resource_data: Dict, resource_name: str,
                                         module_path: str = "", index: int = None) -> Optional[IaCResource]:
        """Create IaCResource from Terraform planned value"""
        try:
            # Parse resource type and name
            if '.' in resource_name:
                resource_type, name = resource_name.split('.', 1)
            else:
                resource_type = resource_name
                name = resource_name
            
            # Create unique IaC ID
            if index is not None:
                iac_id = f"{module_path}.{resource_name}[{index}]" if module_path else f"{resource_name}[{index}]"
            else:
                iac_id = f"{module_path}.{resource_name}" if module_path else resource_name
            
            # Determine cloud provider and normalize type
            cloud_provider = self._determine_cloud_provider(resource_type)
            normalized_type = self.normalize_resource_type(resource_type, cloud_provider)
            
            # Extract properties and tags
            properties = resource_data.get('values', {})
            tags = self._extract_tags(properties)
            
            # Determine change type
            change_type = self._determine_change_type(resource_data)
            
            return IaCResource(
                iac_id=iac_id,
                resource_type=normalized_type,
                cloud_provider=cloud_provider,
                properties=properties,
                tags=tags,
                metadata={
                    'terraform_address': iac_id,
                    'resource_type': resource_type,
                    'resource_name': name,
                    'module_path': module_path,
                    'index': index
                },
                change_type=change_type
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create resource from planned value {resource_name}: {e}")
            return None
    
    def _extract_resources_from_changes(self, resource_changes: List[Dict]) -> List[IaCResource]:
        """Extract resources from Terraform resource changes"""
        resources = []
        
        for change in resource_changes:
            try:
                resource = self._create_resource_from_change(change)
                if resource:
                    resources.append(resource)
            except Exception as e:
                self.logger.warning(f"Failed to create resource from change: {e}")
        
        return resources
    
    def _create_resource_from_change(self, change: Dict) -> Optional[IaCResource]:
        """Create IaCResource from Terraform resource change"""
        try:
            address = change.get('address', '')
            change_type_str = change.get('change', {}).get('actions', ['no-change'])[0]
            
            # Determine change type
            change_type_map = {
                'create': ChangeType.CREATE,
                'update': ChangeType.UPDATE,
                'delete': ChangeType.DELETE,
                'no-change': ChangeType.NO_CHANGE
            }
            change_type = change_type_map.get(change_type_str, ChangeType.NO_CHANGE)
            
            # Extract resource type and name from address
            resource_type, name = self._parse_terraform_address(address)
            
            # Determine cloud provider
            cloud_provider = self._determine_cloud_provider(resource_type)
            normalized_type = self.normalize_resource_type(resource_type, cloud_provider)
            
            # Extract properties and tags
            properties = {}
            if change_type_str in ['create', 'update']:
                properties = change.get('change', {}).get('after', {})
            else:
                properties = change.get('change', {}).get('before', {})
            
            tags = self._extract_tags(properties)
            
            return IaCResource(
                iac_id=address,
                resource_type=normalized_type,
                cloud_provider=cloud_provider,
                properties=properties,
                tags=tags,
                metadata={
                    'terraform_address': address,
                    'resource_type': resource_type,
                    'resource_name': name,
                    'change_actions': change.get('change', {}).get('actions', []),
                    'import_id': change.get('import_id'),
                    'deposed': change.get('deposed', False)
                },
                change_type=change_type
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create resource from change {change.get('address')}: {e}")
            return None
    
    def _extract_plan_dependencies(self, content: Dict) -> List[IaCDependency]:
        """Extract dependencies from Terraform plan"""
        dependencies = []
        
        # Extract from configuration
        configuration = content.get('configuration', {})
        dependencies.extend(self._extract_config_dependencies(configuration))
        
        # Extract from resource changes
        resource_changes = content.get('resource_changes', [])
        for change in resource_changes:
            change_deps = self._extract_dependencies_from_change(change)
            dependencies.extend(change_deps)
        
        return dependencies
    
    def _extract_config_dependencies(self, configuration: Dict) -> List[IaCDependency]:
        """Extract dependencies from Terraform configuration"""
        dependencies = []
        
        def extract_from_module(module_data: Dict, module_path: str = ""):
            # Extract from module resources
            module_resources = module_data.get('resources', {})
            for resource_name, resource_data in module_resources.items():
                resource_deps = self._extract_dependencies_from_resource_data(
                    resource_data, resource_name, module_path
                )
                dependencies.extend(resource_deps)
            
            # Recursively extract from child modules
            child_modules = module_data.get('child_modules', {})
            for child_name, child_data in child_modules.items():
                child_path = f"{module_path}.{child_name}" if module_path else child_name
                extract_from_module(child_data, child_path)
        
        # Start extraction from root module
        root_module = configuration.get('root_module', {})
        extract_from_module(root_module)
        
        return dependencies
    
    def _extract_dependencies_from_resource_data(self, resource_data: Dict, resource_name: str,
                                             module_path: str = "") -> List[IaCDependency]:
        """Extract dependencies from Terraform resource data"""
        dependencies = []
        
        # Extract from expressions
        expressions = resource_data.get('expressions', {})
        for expr_key, expr_data in expressions.items():
            if 'references' in expr_data:
                for ref in expr_data['references']:
                    dep = self._create_dependency_from_reference(
                        ref, resource_name, module_path, expr_key
                    )
                    if dep:
                        dependencies.append(dep)
        
        return dependencies
    
    def _extract_dependencies_from_change(self, change: Dict) -> List[IaCDependency]:
        """Extract dependencies from Terraform resource change"""
        dependencies = []
        
        address = change.get('address', '')
        change_data = change.get('change', {})
        
        # Extract from before and after states
        for state_key in ['before', 'after']:
            state_data = change_data.get(state_key, {})
            if isinstance(state_data, dict):
                state_deps = self._extract_dependencies_from_state(
                    state_data, address, state_key
                )
                dependencies.extend(state_deps)
        
        return dependencies
    
    def _extract_dependencies_from_state(self, state_data: Dict, resource_address: str,
                                      state_key: str) -> List[IaCDependency]:
        """Extract dependencies from Terraform state"""
        dependencies = []
        
        def find_references(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if self._is_reference(value):
                        dep = self._create_dependency_from_reference(
                            value, resource_address, "", current_path
                        )
                        if dep:
                            dependencies.append(dep)
                    else:
                        find_references(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    find_references(item, f"{path}[{i}]")
        
        find_references(state_data)
        return dependencies
    
    def _create_dependency_from_reference(self, reference: Any, source_resource: str,
                                       module_path: str = "", property_path: str = "") -> Optional[IaCDependency]:
        """Create dependency from Terraform reference"""
        try:
            if isinstance(reference, str):
                # Handle different reference formats
                if reference.startswith('var.'):
                    # Variable reference
                    target_id = reference
                    dependency_type = 'variable'
                elif '.' in reference:
                    # Resource reference
                    target_id = reference
                    dependency_type = 'resource'
                else:
                    return None
                
                source_id = f"{module_path}.{source_resource}" if module_path else source_resource
                
                return IaCDependency(
                    source_id=source_id,
                    target_id=target_id,
                    dependency_type=dependency_type,
                    property_path=property_path,
                    metadata={
                        'reference_format': 'terraform',
                        'module_path': module_path
                    }
                )
            
        except Exception as e:
            self.logger.warning(f"Failed to create dependency from reference {reference}: {e}")
            return None
    
    def _is_terraform_plan(self, content: Dict) -> bool:
        """Check if content is a Terraform plan"""
        plan_indicators = [
            'planned_values',
            'resource_changes',
            'configuration',
            'prior_state'
        ]
        
        return any(key in content for key in plan_indicators)
    
    def _parse_terraform_address(self, address: str) -> tuple:
        """Parse Terraform address into type and name"""
        if '.' in address:
            parts = address.split('.')
            if len(parts) >= 2:
                resource_type = '.'.join(parts[:-1])
                name = parts[-1]
                return resource_type, name
        
        return address, address
    
    def _determine_cloud_provider(self, resource_type: str) -> CloudProvider:
        """Determine cloud provider from resource type"""
        resource_type_lower = resource_type.lower()
        
        if any(provider in resource_type_lower for provider in ['aws_', 'aws::']):
            return CloudProvider.AWS
        elif any(provider in resource_type_lower for provider in ['azurerm_', 'azure']):
            return CloudProvider.AZURE
        elif any(provider in resource_type_lower for provider in ['google_', 'gcp_']):
            return CloudProvider.GCP
        elif any(provider in resource_type_lower for provider in ['kubernetes_', 'k8s_']):
            return CloudProvider.KUBERNETES
        
        return CloudProvider.MULTI_CLOUD
    
    def _is_reference(self, value: Any) -> bool:
        """Check if value is a Terraform reference"""
        if isinstance(value, str):
            reference_patterns = [
                'var.',
                'count.',
                'each.',
                'self.',
                'terraform.',
                'data.',
                'module.'
            ]
            return any(value.startswith(pattern) for pattern in reference_patterns)
        return False
    
    def _calculate_hash(self, data: Dict) -> str:
        """Calculate hash of data for tracking"""
        import hashlib
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()


# Register the parser
from .base import IaCParserFactory
IaCParserFactory.register_parser('terraform', TerraformParser)
