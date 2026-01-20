"""
ARM Template IaC Parser

This module provides ARM (Azure Resource Manager) template parsing functionality
with support for both ARM templates and What-If results.
"""

import json
import re
from typing import Dict, List, Any, Optional, Union
from .base import IaCParser, IaCPlan, IaCResource, IaCDependency, CloudProvider, ChangeType


class ARMParser(IaCParser):
    """ARM Template IaC parser with support for templates and What-If results"""
    
    def parse(self, content: Union[str, Dict]) -> IaCPlan:
        """Parse ARM template or what-if result"""
        if isinstance(content, str):
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON - ARM templates must be valid JSON")
        else:
            data = content
        
        # Check if it's a what-if result or template
        if 'changes' in data:
            return self._parse_what_if(data)
        else:
            return self._parse_template(data)
    
    def _parse_template(self, template: Dict) -> IaCPlan:
        """Parse ARM template"""
        plan_id = self._generate_plan_id('arm')
        timestamp = template.get('contentVersion', 'unknown')
        
        # Extract resources
        resources = []
        resources_section = template.get('resources', [])
        for resource_def in resources_section:
            resource = self._parse_template_resource(resource_def)
            if resource:
                resources.append(resource)
        
        # Extract dependencies
        dependencies = self._extract_template_dependencies(resources_section)
        
        return IaCPlan(
            id=plan_id,
            source_type='arm',
            source_content=template,
            resources=resources,
            dependencies=dependencies,
            timestamp=timestamp,
            metadata={
                'schema': template.get('$schema', ''),
                'content_version': template.get('contentVersion', ''),
                'api_profile': template.get('apiProfile', ''),
                'parameters': list(template.get('parameters', {}).keys()),
                'outputs': list(template.get('outputs', {}).keys()),
                'parsed_from': 'template'
            }
        )
    
    def _parse_what_if(self, what_if: Dict) -> IaCPlan:
        """Parse ARM what-if result"""
        plan_id = what_if.get('status', 'unknown')
        timestamp = what_if.get('timestamp', '')
        
        # Extract resources from changes
        resources = []
        changes = what_if.get('changes', [])
        for change in changes:
            resource = self._parse_what_if_change(change)
            if resource:
                resources.append(resource)
        
        return IaCPlan(
            id=plan_id,
            source_type='arm',
            source_content=what_if,
            resources=resources,
            dependencies=[],  # What-if doesn't include explicit dependencies
            timestamp=timestamp,
            metadata={
                'target_resource_group': what_if.get('targetResourceGroup', ''),
                'what_if_format': what_if.get('format', ''),
                'error_details': what_if.get('error', {}),
                'changes_count': len(changes),
                'parsed_from': 'what_if'
            }
        )
    
    def extract_resources(self, content: Dict) -> List[IaCResource]:
        """Extract resources from ARM content"""
        resources = []
        
        if 'changes' in content:
            # What-if result
            changes = content.get('changes', [])
            for change in changes:
                resource = self._parse_what_if_change(change)
                if resource:
                    resources.append(resource)
        else:
            # ARM template
            resources_section = content.get('resources', [])
            for resource_def in resources_section:
                resource = self._parse_template_resource(resource_def)
                if resource:
                    resources.append(resource)
        
        return resources
    
    def _parse_template_resource(self, resource_def: Dict) -> Optional[IaCResource]:
        """Parse resource from ARM template"""
        try:
            resource_type = resource_def.get('type', '')
            name = resource_def.get('name', '')
            properties = resource_def.get('properties', {})
            
            if not resource_type or not name:
                return None
            
            # Determine cloud provider and normalize type
            cloud_provider = CloudProvider.AZURE  # ARM is Azure-specific
            normalized_type = self.normalize_resource_type(resource_type, cloud_provider)
            
            # Create IaC ID
            iac_id = f"{resource_type}/{name}"
            
            # Extract tags
            tags = self._extract_arm_tags(resource_def, properties)
            
            return IaCResource(
                iac_id=iac_id,
                resource_type=normalized_type,
                cloud_provider=cloud_provider,
                properties=properties,
                tags=tags,
                metadata={
                    'arm_type': resource_type,
                    'arm_name': name,
                    'api_version': resource_def.get('apiVersion', ''),
                    'location': resource_def.get('location', properties.get('location', '')),
                    'sku': resource_def.get('sku', {}),
                    'kind': resource_def.get('kind', ''),
                    'managed_by': resource_def.get('managedBy', ''),
                    'parsed_from': 'template'
                },
                change_type=ChangeType.CREATE  # Assume create for templates
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to parse ARM template resource {resource_def.get('name')}: {e}")
            return None
    
    def _parse_what_if_change(self, change: Dict) -> Optional[IaCResource]:
        """Parse resource from ARM what-if change"""
        try:
            resource_type = change.get('resourceType', '')
            change_type_str = change.get('changeType', '')
            resource_id = change.get('resourceId', '')
            
            if not resource_type or not resource_id:
                return None
            
            # Map ARM change type to our change type
            change_type = self._map_arm_change_type(change_type_str)
            
            # Determine cloud provider and normalize type
            cloud_provider = CloudProvider.AZURE
            normalized_type = self.normalize_resource_type(resource_type, cloud_provider)
            
            # Extract properties and tags
            properties = {}
            if change_type in [ChangeType.CREATE, ChangeType.UPDATE]:
                properties = change.get('after', {}).get('properties', {})
            else:
                properties = change.get('before', {}).get('properties', {})
            
            tags = self._extract_arm_tags(change, properties)
            
            return IaCResource(
                iac_id=resource_id,
                resource_type=normalized_type,
                cloud_provider=cloud_provider,
                properties=properties,
                tags=tags,
                metadata={
                    'arm_type': resource_type,
                    'resource_id': resource_id,
                    'change_type': change_type_str,
                    'delta': change.get('delta', {}),
                    'before': change.get('before', {}),
                    'after': change.get('after', {}),
                    'parsed_from': 'what_if'
                },
                change_type=change_type
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to parse ARM what-if change {change.get('resourceId')}: {e}")
            return None
    
    def extract_dependencies(self, content: Dict) -> List[IaCDependency]:
        """Extract dependencies from ARM content"""
        dependencies = []
        
        if 'changes' in content:
            # What-if result - dependencies are not typically included
            return dependencies
        else:
            # ARM template
            resources_section = content.get('resources', [])
            dependencies.extend(self._extract_template_dependencies(resources_section))
        
        return dependencies
    
    def _extract_template_dependencies(self, resources_section: List[Dict]) -> List[IaCDependency]:
        """Extract dependencies from ARM template resources"""
        dependencies = []
        
        # Create resource lookup for dependency resolution
        resource_map = {}
        for resource_def in resources_section:
            resource_type = resource_def.get('type', '')
            name = resource_def.get('name', '')
            if resource_type and name:
                resource_id = f"{resource_type}/{name}"
                resource_map[resource_id] = resource_def
        
        # Extract dependencies from each resource
        for resource_def in resources_section:
            resource_type = resource_def.get('type', '')
            name = resource_def.get('name', '')
            if not resource_type or not name:
                continue
            
            source_id = f"{resource_type}/{name}"
            
            # Extract explicit dependencies
            depends_on = resource_def.get('dependsOn', [])
            if isinstance(depends_on, str):
                depends_on = [depends_on]
            
            for dep in depends_on:
                if dep in resource_map:
                    target_id = f"{resource_map[dep].get('type', '')}/{resource_map[dep].get('name', '')}"
                    dependency = IaCDependency(
                        source_id=source_id,
                        target_id=target_id,
                        dependency_type='explicit',
                        metadata={
                            'format': 'arm',
                            'type': 'dependsOn'
                        }
                    )
                    dependencies.append(dependency)
            
            # Extract dependencies from properties (resource references)
            properties = resource_def.get('properties', {})
            property_deps = self._extract_property_dependencies(properties, source_id, resource_map)
            dependencies.extend(property_deps)
        
        return dependencies
    
    def _extract_property_dependencies(self, properties: Dict, source_id: str,
                                     resource_map: Dict) -> List[IaCDependency]:
        """Extract dependencies from ARM resource properties"""
        dependencies = []
        
        def find_resource_references(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # Look for resource ID patterns
                    if isinstance(value, str):
                        # ARM resource reference format: [resourceId('name')]
                        ref_pattern = r"\[resourceId\('([^']+)'\)\]"
                        matches = re.findall(ref_pattern, value)
                        for match in matches:
                            ref_name = match
                            if ref_name in resource_map:
                                target_def = resource_map[ref_name]
                                target_id = f"{target_def.get('type', '')}/{target_def.get('name', '')}"
                                
                                dependency = IaCDependency(
                                    source_id=source_id,
                                    target_id=target_id,
                                    dependency_type='reference',
                                    property_path=current_path,
                                    metadata={
                                        'format': 'arm',
                                        'function': 'resourceId',
                                        'reference': ref_name
                                    }
                                )
                                dependencies.append(dependency)
                    
                    # Look for list references
                    list_ref_pattern = r"\[concat\([^)]+\)\]"
                    list_matches = re.findall(list_ref_pattern, value)
                    for match in list_matches:
                        # Check if it contains resourceId
                        if 'resourceId' in match:
                            dependencies.extend(self._parse_list_reference(match, source_id, resource_map))
                    
                    # Recurse into nested objects
                    find_resource_references(value, current_path)
            
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    find_resource_references(item, f"{path}[{i}]")
        
        find_resource_references(properties)
        return dependencies
    
    def _parse_list_reference(self, list_ref: str, source_id: str,
                           resource_map: Dict) -> List[IaCDependency]:
        """Parse ARM list function references for dependencies"""
        dependencies = []
        
        # This is a simplified parser for ARM list functions
        # In a full implementation, we'd need to parse the concat function
        # and extract resourceId references
        
        # Look for resourceId patterns in the list reference
        ref_pattern = r"'([^']*)'"
        matches = re.findall(ref_pattern, list_ref)
        
        for match in matches:
            if 'resourceId' in match:
                # Extract the resource name from the match
                resource_name_pattern = r"resourceId\('([^']+)'\)"
                resource_name_match = re.search(resource_name_pattern, match)
                
                if resource_name_match:
                    resource_name = resource_name_match.group(1)
                    if resource_name in resource_map:
                        target_def = resource_map[resource_name]
                        target_id = f"{target_def.get('type', '')}/{target_def.get('name', '')}"
                        
                        dependency = IaCDependency(
                            source_id=source_id,
                            target_id=target_id,
                            dependency_type='reference',
                            property_path='list_function',
                            metadata={
                                'format': 'arm',
                                'function': 'concat',
                                'reference': resource_name,
                                'list_expression': list_ref
                            }
                        )
                        dependencies.append(dependency)
        
        return dependencies
    
    def _extract_arm_tags(self, resource_def: Dict, properties: Dict) -> Dict[str, str]:
        """Extract tags from ARM resource"""
        tags = {}
        
        # Check for explicit Tags property in resource definition
        if 'tags' in resource_def:
            tags_obj = resource_def['tags']
            if isinstance(tags_obj, dict):
                # String-based tags
                tags.update(tags_obj)
            elif isinstance(tags_obj, list):
                # Object-based tags
                for tag in tags_obj:
                    if isinstance(tag, dict):
                        key = tag.get('key', tag.get('name', ''))
                        value = tag.get('value', tag.get('property', ''))
                        if key and value:
                            tags[key] = value
        
        # Check for tags in properties
        if 'tags' in properties:
            props_tags = properties['tags']
            if isinstance(props_tags, dict):
                tags.update(props_tags)
            elif isinstance(props_tags, list):
                for tag in props_tags:
                    if isinstance(tag, dict):
                        key = tag.get('key', tag.get('name', ''))
                        value = tag.get('value', tag.get('property', ''))
                        if key and value:
                            tags[key] = value
        
        return tags
    
    def _map_arm_change_type(self, arm_change_type: str) -> ChangeType:
        """Map ARM change type to unified change type"""
        change_mapping = {
            'Create': ChangeType.CREATE,
            'Modify': ChangeType.UPDATE,
            'Delete': ChangeType.DELETE,
            'NoChange': ChangeType.NO_CHANGE,
            'Ignore': ChangeType.NO_CHANGE
        }
        
        return change_mapping.get(arm_change_type, ChangeType.NO_CHANGE)
    
    def detect_format(self, content: Union[str, Dict]) -> bool:
        """Detect if content is ARM format"""
        if isinstance(content, str):
            # Check for ARM-specific keywords
            arm_indicators = [
                '$schema',
                'contentVersion',
                'apiProfile',
                'parameters',
                'variables',
                'functions',
                'resources',
                'outputs',
                'Microsoft.',
                'resources(',
                '[parameters(',
                '[resourceId(',
                '[list(',
                '[concat(',
                '[reference(',
                '[subscription(',
                '[resourceGroup('
            ]
            
            content_lower = content.lower()
            return any(indicator in content_lower for indicator in arm_indicators)
        
        elif isinstance(content, dict):
            # Check for ARM structure
            arm_keys = [
                '$schema',
                'contentVersion',
                'apiProfile',
                'parameters',
                'variables',
                'functions',
                'resources',
                'outputs',
                'changes',  # What-if result
                'targetResourceGroup',
                'format'
            ]
            
            # Check for Microsoft resource types
            has_microsoft_resources = False
            if 'resources' in content:
                for resource in content['resources']:
                    if isinstance(resource, dict) and 'type' in resource:
                        resource_type = resource['type']
                        if resource_type.startswith('Microsoft.'):
                            has_microsoft_resources = True
                            break
            
            return any(key in content for key in arm_keys) or has_microsoft_resources
        
        return False


# Register the parser
from .base import IaCParserFactory
IaCParserFactory.register_parser('arm', ARMParser)
