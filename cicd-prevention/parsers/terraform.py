"""
Terraform IaC Parser

This module provides Terraform-specific parsing functionality with support for both
plan JSON and HCL configuration formats.
"""

import json
import re
from typing import Dict, List, Any, Optional, Union
from .base import IaCParser, IaCPlan, IaCResource, IaCDependency, CloudProvider, ChangeType

try:
    import hcl2
    HCL_AVAILABLE = True
except ImportError:
    HCL_AVAILABLE = False
    print("Warning: hcl2 library not available. HCL parsing will be disabled.")


class TerraformParser(IaCParser):
    """Terraform IaC parser with support for plan JSON and HCL"""
    
    def parse(self, content: Union[str, Dict]) -> IaCPlan:
        """Parse Terraform content (plan JSON or HCL)"""
        if isinstance(content, str):
            try:
                # Try to parse as JSON (terraform plan -json)
                data = json.loads(content)
                return self._parse_plan_json(data)
            except json.JSONDecodeError:
                if HCL_AVAILABLE:
                    # Try to parse as HCL
                    return self._parse_hcl(content)
                else:
                    raise ValueError("Content is not valid JSON and hcl2 library is not available")
        elif isinstance(content, dict):
            return self._parse_plan_json(content)
        else:
            raise ValueError("Unsupported content type")
    
    def _parse_plan_json(self, plan_data: Dict) -> IaCPlan:
        """Parse Terraform plan JSON output"""
        plan_id = self._generate_plan_id('terraform')
        timestamp = plan_data.get('terraform_version', 'unknown')
        
        # Extract resources from planned values and resource changes
        resources = []
        resources.extend(self._extract_configuration_resources(plan_data))
        resources.extend(self._extract_planned_changes(plan_data))
        
        # Extract dependencies
        dependencies = self._extract_dependencies(plan_data)
        
        return IaCPlan(
            id=plan_id,
            source_type='terraform',
            source_content=plan_data,
            resources=resources,
            dependencies=dependencies,
            timestamp=timestamp,
            metadata={
                'terraform_version': plan_data.get('terraform_version'),
                'format_version': plan_data.get('format_version'),
                'planned_values_hash': self._calculate_hash(plan_data.get('planned_values', {})),
                'configuration_hash': self._calculate_hash(plan_data.get('configuration', {})),
                'parsed_from': 'plan_json'
            }
        )
    
    def _parse_hcl(self, hcl_content: str) -> IaCPlan:
        """Parse Terraform HCL configuration"""
        if not HCL_AVAILABLE:
            raise ImportError("hcl2 library is required for HCL parsing")
        
        try:
            parsed_hcl = hcl2.loads(hcl_content)
        except Exception as e:
            raise ValueError(f"Failed to parse HCL: {e}")
        
        plan_id = self._generate_plan_id('terraform')
        timestamp = 'hcl_config'
        
        # Extract resources from HCL
        resources = self._extract_hcl_resources(parsed_hcl)
        
        # Extract dependencies from HCL
        dependencies = self._extract_hcl_dependencies(parsed_hcl)
        
        return IaCPlan(
            id=plan_id,
            source_type='terraform',
            source_content=parsed_hcl,
            resources=resources,
            dependencies=dependencies,
            timestamp=timestamp,
            metadata={
                'parsed_from': 'hcl',
                'terraform_version': 'unknown',
                'format_version': 'unknown'
            }
        )
    
    def extract_resources(self, content: Dict) -> List[IaCResource]:
        """Extract resources from Terraform content"""
        resources = []
        
        if self._is_terraform_plan(content):
            resources.extend(self._extract_configuration_resources(content))
            resources.extend(self._extract_planned_changes(content))
        else:
            # Assume HCL parsed content
            resources.extend(self._extract_hcl_resources(content))
        
        return resources
    
    def _extract_configuration_resources(self, plan_data: Dict) -> List[IaCResource]:
        """Extract resources from Terraform configuration section"""
        resources = []
        
        configuration = plan_data.get('configuration', {})
        root_module = configuration.get('root_module', {})
        
        # Extract resources from root module
        resources.extend(self._walk_module(root_module))
        
        return resources
    
    def _extract_planned_changes(self, plan_data: Dict) -> List[IaCResource]:
        """Extract resources from Terraform planned changes"""
        resources = []
        
        resource_changes = plan_data.get('resource_changes', [])
        for change in resource_changes:
            try:
                resource = self._create_resource_from_change(change)
                if resource:
                    resources.append(resource)
            except Exception as e:
                self.logger.warning(f"Failed to create resource from change: {e}")
        
        return resources
    
    def _extract_hcl_resources(self, parsed_hcl: Dict) -> List[IaCResource]:
        """Extract resources from HCL parsed content"""
        resources = []
        
        # Extract from resource blocks
        resource_blocks = parsed_hcl.get('resource', {})
        for resource_type, resource_defs in resource_blocks.items():
            if isinstance(resource_defs, dict):
                for resource_name, resource_config in resource_defs.items():
                    try:
                        resource = self._create_resource_from_hcl(
                            resource_type, resource_name, resource_config
                        )
                        if resource:
                            resources.append(resource)
                    except Exception as e:
                        self.logger.warning(f"Failed to create HCL resource: {e}")
            elif isinstance(resource_defs, list):
                for i, resource_config in enumerate(resource_defs):
                    try:
                        resource = self._create_resource_from_hcl(
                            resource_type, f"{resource_name}[{i}]", resource_config
                        )
                        if resource:
                            resources.append(resource)
                    except Exception as e:
                        self.logger.warning(f"Failed to create HCL resource: {e}")
        
        return resources
    
    def _create_resource_from_hcl(self, resource_type: str, resource_name: str,
                                  resource_config: Dict) -> Optional[IaCResource]:
        """Create IaCResource from HCL resource definition"""
        try:
            # Determine cloud provider and normalize type
            cloud_provider = self._determine_cloud_provider(resource_type)
            normalized_type = self.normalize_resource_type(resource_type, cloud_provider)
            
            # Create IaC ID
            iac_id = f"{resource_type}.{resource_name}"
            
            # Extract properties and tags
            properties = resource_config if isinstance(resource_config, dict) else {}
            tags = self._extract_tags(properties)
            
            # Determine change type (assume create for HCL)
            change_type = ChangeType.CREATE
            
            return IaCResource(
                iac_id=iac_id,
                resource_type=normalized_type,
                cloud_provider=cloud_provider,
                properties=properties,
                tags=tags,
                metadata={
                    'terraform_address': iac_id,
                    'resource_type': resource_type,
                    'resource_name': resource_name,
                    'parsed_from': 'hcl'
                },
                change_type=change_type
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create HCL resource {resource_name}: {e}")
            return None
    
    def _create_resource_from_change(self, change: Dict) -> Optional[IaCResource]:
        """Create IaCResource from Terraform resource change"""
        try:
            address = change.get('address', '')
            change_actions = change.get('change', {}).get('actions', ['no-change'])
            
            # Determine change type
            if 'create' in change_actions:
                change_type = ChangeType.CREATE
            elif 'update' in change_actions:
                change_type = ChangeType.UPDATE
            elif 'delete' in change_actions:
                change_type = ChangeType.DELETE
            else:
                change_type = ChangeType.NO_CHANGE
            
            # Extract resource type and name from address
            resource_type, name = self._parse_terraform_address(address)
            
            # Determine cloud provider and normalize type
            cloud_provider = self._determine_cloud_provider(resource_type)
            normalized_type = self.normalize_resource_type(resource_type, cloud_provider)
            
            # Extract properties and tags
            properties = {}
            if change_type in [ChangeType.CREATE, ChangeType.UPDATE]:
                properties = change.get('change', {}).get('after', {})
            else:
                properties = change.get('change', {}).get('before', {})
            
            tags = self._extract_tags(properties)
            
            # Create IaC ID
            iac_id = address
            
            return IaCResource(
                iac_id=iac_id,
                resource_type=normalized_type,
                cloud_provider=cloud_provider,
                properties=properties,
                tags=tags,
                metadata={
                    'terraform_address': address,
                    'resource_type': resource_type,
                    'resource_name': name,
                    'change_actions': change_actions,
                    'import_id': change.get('import_id'),
                    'deposed': change.get('deposed', False),
                    'parsed_from': 'plan_json'
                },
                change_type=change_type
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create resource from change {change.get('address')}: {e}")
            return None
    
    def _walk_module(self, module_data: Dict, module_path: str = "") -> List[IaCResource]:
        """Recursively walk through Terraform modules"""
        resources = []
        
        # Extract resources from module
        module_resources = module_data.get('resources', {})
        for resource_name, resource_data in module_resources.items():
            if isinstance(resource_data, list):
                for i, resource_instance in enumerate(resource_data):
                    resource = self._create_resource_from_module_resource(
                        resource_instance, resource_name, module_path, i
                    )
                    if resource:
                        resources.append(resource)
            else:
                resource = self._create_resource_from_module_resource(
                    resource_data, resource_name, module_path
                )
                if resource:
                    resources.append(resource)
        
        # Recursively extract from child modules
        child_modules = module_data.get('child_modules', {})
        for child_name, child_data in child_modules.items():
            child_path = f"{module_path}.{child_name}" if module_path else child_name
            child_resources = self._walk_module(child_data, child_path)
            resources.extend(child_resources)
        
        return resources
    
    def _create_resource_from_module_resource(self, resource_data: Dict, resource_name: str,
                                          module_path: str = "", index: int = None) -> Optional[IaCResource]:
        """Create IaCResource from Terraform module resource"""
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
                    'index': index,
                    'parsed_from': 'plan_json'
                },
                change_type=change_type
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create resource from module resource {resource_name}: {e}")
            return None
    
    def extract_dependencies(self, content: Dict) -> List[IaCDependency]:
        """Extract dependencies from Terraform content"""
        dependencies = []
        
        if self._is_terraform_plan(content):
            dependencies.extend(self._extract_plan_dependencies(content))
        else:
            # Assume HCL parsed content
            dependencies.extend(self._extract_hcl_dependencies(content))
        
        return dependencies
    
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
    
    def _extract_hcl_dependencies(self, parsed_hcl: Dict) -> List[IaCDependency]:
        """Extract dependencies from HCL parsed content"""
        dependencies = []
        
        # Extract from resource blocks
        resource_blocks = parsed_hcl.get('resource', {})
        for resource_type, resource_defs in resource_blocks.items():
            if isinstance(resource_defs, dict):
                for resource_name, resource_config in resource_defs.items():
                    resource_deps = self._extract_dependencies_from_resource_config(
                        resource_config, f"{resource_type}.{resource_name}"
                    )
                    dependencies.extend(resource_deps)
            elif isinstance(resource_defs, list):
                for i, resource_config in enumerate(resource_defs):
                    resource_id = f"{resource_type}.{resource_name}[{i}]"
                    resource_deps = self._extract_dependencies_from_resource_config(
                        resource_config, resource_id
                    )
                    dependencies.extend(resource_deps)
        
        return dependencies
    
    def _extract_dependencies_from_resource_config(self, resource_config: Dict,
                                                resource_id: str) -> List[IaCDependency]:
        """Extract dependencies from Terraform resource configuration"""
        dependencies = []
        
        # Look for references in resource properties
        if isinstance(resource_config, dict):
            for key, value in resource_config.items():
                refs = self._find_references_in_value(value)
                for ref in refs:
                    dependency = IaCDependency(
                        source_id=resource_id,
                        target_id=ref,
                        dependency_type='reference',
                        property_path=key,
                        metadata={
                            'format': 'terraform',
                            'reference': ref
                        }
                    )
                    dependencies.append(dependency)
        
        return dependencies
    
    def _find_references_in_value(self, value: Any) -> List[str]:
        """Find Terraform references in a value"""
        references = []
        
        if isinstance(value, str):
            # Look for ${var.name} and ${resource.name.attr} patterns
            ref_pattern = r'\$\{([^}]+)\}'
            matches = re.findall(ref_pattern, value)
            references.extend(matches)
        
        elif isinstance(value, dict):
            for v in value.values():
                references.extend(self._find_references_in_value(v))
        
        elif isinstance(value, list):
            for item in value:
                references.extend(self._find_references_in_value(item))
        
        return references
    
    def _extract_dependencies_from_change(self, change: Dict) -> List[IaCDependency]:
        """Extract dependencies from Terraform resource change"""
        dependencies = []
        
        address = change.get('address', '')
        change_data = change.get('change', {})
        
        # Extract from before and after states
        for state_key in ['before', 'after']:
            state_data = change_data.get(state_key, {})
            if isinstance(state_data, dict):
                state_deps = self._extract_dependencies_from_resource_config(
                    state_data, address
                )
                dependencies.extend(state_deps)
        
        return dependencies
    
    def _extract_config_dependencies(self, configuration: Dict) -> List[IaCDependency]:
        """Extract dependencies from Terraform configuration"""
        dependencies = []
        
        def extract_from_module(module_data: Dict, module_path: str = ""):
            # Extract from module resources
            module_resources = module_data.get('resources', {})
            for resource_name, resource_data in module_resources.items():
                resource_id = f"{module_path}.{resource_name}" if module_path else resource_name
                resource_deps = self._extract_dependencies_from_resource_config(
                    resource_data, resource_id
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
                'output "',
                'data "',
                'locals {'
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
                'terraform_version',
                'format_version'
            ]
            
            # Check for HCL structure
            hcl_keys = [
                'resource',
                'terraform',
                'provider',
                'module',
                'variable',
                'output',
                'data',
                'locals'
            ]
            
            return any(key in content for key in terraform_keys) or \
                   any(key in content for key in hcl_keys)
        
        return False
    
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
    
    def _calculate_hash(self, data: Dict) -> str:
        """Calculate hash of data for tracking"""
        import hashlib
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()


# Register the parser
from .base import IaCParserFactory
IaCParserFactory.register_parser('terraform', TerraformParser)
