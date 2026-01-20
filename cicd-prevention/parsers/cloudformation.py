"""
CloudFormation IaC Parser

This module provides CloudFormation-specific parsing functionality.
"""

import json
import re
from typing import Dict, List, Any, Optional, Union
from .base import IaCParser, IaCPlan, IaCResource, IaCDependency, CloudProvider, ChangeType


class CloudFormationParser(IaCParser):
    """CloudFormation IaC parser"""
    
    def parse(self, content: Union[str, Dict]) -> IaCPlan:
        """Parse CloudFormation content and return unified plan"""
        parsed_content = self._parse_content(content)
        
        plan_id = self._generate_plan_id('cloudformation')
        timestamp = parsed_content.get('AWSTemplateFormatVersion', '2010-09-09')
        
        # Extract resources
        resources = self.extract_resources(parsed_content)
        
        # Extract dependencies
        dependencies = self.extract_dependencies(parsed_content)
        
        return IaCPlan(
            id=plan_id,
            source_type='cloudformation',
            source_content=parsed_content,
            resources=resources,
            dependencies=dependencies,
            timestamp=timestamp,
            metadata={
                'format_version': parsed_content.get('AWSTemplateFormatVersion'),
                'description': parsed_content.get('Description', ''),
                'transform': parsed_content.get('Transform', []),
                'parameters': list(parsed_content.get('Parameters', {}).keys()),
                'mappings': list(parsed_content.get('Mappings', {}).keys()),
                'conditions': list(parsed_content.get('Conditions', {}).keys())
            }
        )
    
    def extract_resources(self, content: Dict) -> List[IaCResource]:
        """Extract resources from CloudFormation content"""
        resources = []
        
        resources_section = content.get('Resources', {})
        for logical_id, resource_data in resources_section.items():
            try:
                resource = self._create_resource_from_cf_resource(logical_id, resource_data)
                if resource:
                    resources.append(resource)
            except Exception as e:
                self.logger.warning(f"Failed to create resource from CF resource {logical_id}: {e}")
        
        return resources
    
    def extract_dependencies(self, content: Dict) -> List[IaCDependency]:
        """Extract dependencies from CloudFormation content"""
        dependencies = []
        
        resources_section = content.get('Resources', {})
        for logical_id, resource_data in resources_section.items():
            resource_deps = self._extract_dependencies_from_cf_resource(
                logical_id, resource_data, resources_section
            )
            dependencies.extend(resource_deps)
        
        return dependencies
    
    def detect_format(self, content: Union[str, Dict]) -> bool:
        """Detect if content is CloudFormation format"""
        if isinstance(content, str):
            # Check for CloudFormation-specific keywords
            cf_indicators = [
                'AWSTemplateFormatVersion',
                'Resources:',
                'Parameters:',
                'Mappings:',
                'Conditions:',
                'Transform:',
                'Outputs:',
                'AWS::',
                'Fn::',
                'Ref:',
                'GetAtt:'
            ]
            
            content_lower = content.lower()
            return any(indicator in content_lower for indicator in cf_indicators)
        
        elif isinstance(content, dict):
            # Check for CloudFormation structure
            cf_keys = [
                'AWSTemplateFormatVersion',
                'Resources',
                'Parameters',
                'Mappings',
                'Conditions',
                'Transform',
                'Outputs'
            ]
            
            return any(key in content for key in cf_keys)
        
        return False
    
    def _create_resource_from_cf_resource(self, logical_id: str, 
                                      resource_data: Dict) -> Optional[IaCResource]:
        """Create IaCResource from CloudFormation resource"""
        try:
            resource_type = resource_data.get('Type', '')
            properties = resource_data.get('Properties', {})
            
            # Determine cloud provider and normalize type
            cloud_provider = CloudProvider.AWS  # CloudFormation is AWS-specific
            normalized_type = self.normalize_resource_type(resource_type, cloud_provider)
            
            # Extract tags
            tags = self._extract_cf_tags(resource_data, properties)
            
            # Determine change type
            change_type = self._determine_change_type(resource_data)
            
            # Create IaC ID
            iac_id = f"cloudformation:{logical_id}"
            
            return IaCResource(
                iac_id=iac_id,
                resource_type=normalized_type,
                cloud_provider=cloud_provider,
                properties=properties,
                tags=tags,
                metadata={
                    'logical_id': logical_id,
                    'resource_type': resource_type,
                    'condition': resource_data.get('Condition'),
                    'creation_policy': resource_data.get('CreationPolicy'),
                    'deletion_policy': resource_data.get('DeletionPolicy'),
                    'update_policy': resource_data.get('UpdatePolicy'),
                    'metadata': resource_data.get('Metadata', {}),
                    'depends_on': resource_data.get('DependsOn', [])
                },
                change_type=change_type
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create resource from CF resource {logical_id}: {e}")
            return None
    
    def _extract_cf_tags(self, resource_data: Dict, properties: Dict) -> Dict[str, str]:
        """Extract tags from CloudFormation resource"""
        tags = {}
        
        # Check for explicit Tags property
        if 'Tags' in properties:
            tag_list = properties['Tags']
            if isinstance(tag_list, list):
                for tag in tag_list:
                    if isinstance(tag, dict):
                        key = tag.get('Key', tag.get('key', ''))
                        value = tag.get('Value', tag.get('value', ''))
                        if key and value:
                            tags[key] = value
        
        # Check for tag specification in resource metadata
        metadata = resource_data.get('Metadata', {})
        if 'Tags' in metadata:
            metadata_tags = metadata['Tags']
            if isinstance(metadata_tags, dict):
                tags.update(metadata_tags)
        
        return tags
    
    def _extract_dependencies_from_cf_resource(self, logical_id: str, resource_data: Dict,
                                           all_resources: Dict) -> List[IaCDependency]:
        """Extract dependencies from CloudFormation resource"""
        dependencies = []
        
        # Extract explicit DependsOn
        depends_on = resource_data.get('DependsOn', [])
        if isinstance(depends_on, str):
            depends_on = [depends_on]
        
        for dep in depends_on:
            if isinstance(dep, str):
                dependency = IaCDependency(
                    source_id=f"cloudformation:{logical_id}",
                    target_id=f"cloudformation:{dep}",
                    dependency_type='explicit',
                    metadata={
                        'format': 'cloudformation',
                        'type': 'DependsOn'
                    }
                )
                dependencies.append(dependency)
        
        # Extract dependencies from properties (Ref, GetAtt, etc.)
        properties = resource_data.get('Properties', {})
        property_deps = self._extract_dependencies_from_cf_properties(
            properties, logical_id, all_resources
        )
        dependencies.extend(property_deps)
        
        return dependencies
    
    def _extract_dependencies_from_cf_properties(self, properties: Dict, logical_id: str,
                                              all_resources: Dict) -> List[IaCDependency]:
        """Extract dependencies from CloudFormation properties"""
        dependencies = []
        
        def find_intrinsic_functions(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # Check for Ref function
                    if key == 'Ref' and isinstance(value, str):
                        if value in all_resources:
                            dep = IaCDependency(
                                source_id=f"cloudformation:{logical_id}",
                                target_id=f"cloudformation:{value}",
                                dependency_type='reference',
                                property_path=current_path,
                                metadata={
                                    'function': 'Ref',
                                    'reference': value
                                }
                            )
                            dependencies.append(dep)
                    
                    # Check for GetAtt function
                    elif key == 'Fn::GetAtt' and isinstance(value, list) and len(value) >= 2:
                        resource_ref = value[0]
                        if resource_ref in all_resources:
                            dep = IaCDependency(
                                source_id=f"cloudformation:{logical_id}",
                                target_id=f"cloudformation:{resource_ref}",
                                dependency_type='attribute',
                                property_path=current_path,
                                metadata={
                                    'function': 'Fn::GetAtt',
                                    'reference': resource_ref,
                                    'attribute': value[1] if len(value) > 1 else ''
                                }
                            )
                            dependencies.append(dep)
                    
                    # Check for other functions that might contain references
                    elif key.startswith('Fn::'):
                        func_deps = self._extract_from_function(
                            value, logical_id, all_resources, current_path, key
                        )
                        dependencies.extend(func_deps)
                    
                    else:
                        find_intrinsic_functions(value, current_path)
            
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    find_intrinsic_functions(item, f"{path}[{i}]")
        
        find_intrinsic_functions(properties)
        return dependencies
    
    def _extract_from_function(self, func_value: Any, logical_id: str, all_resources: Dict,
                             property_path: str, func_name: str) -> List[IaCDependency]:
        """Extract dependencies from CloudFormation intrinsic function"""
        dependencies = []
        
        if func_name == 'Fn::Join':
            # Join function might contain references
            if isinstance(func_value, list) and len(func_value) >= 2:
                delimiter = func_value[0]
                values = func_value[1]
                if isinstance(values, list):
                    for i, value in enumerate(values):
                        if isinstance(value, dict):
                            func_deps = self._extract_dependencies_from_cf_properties(
                                value, logical_id, all_resources
                            )
                            dependencies.extend(func_deps)
        
        elif func_name == 'Fn::Split':
            # Split function might contain references
            if isinstance(func_value, list) and len(func_value) >= 2:
                delimiter = func_value[0]
                source_string = func_value[1]
                if isinstance(source_string, dict):
                    func_deps = self._extract_dependencies_from_cf_properties(
                        source_string, logical_id, all_resources
                    )
                    dependencies.extend(func_deps)
        
        elif func_name == 'Fn::Sub':
            # Sub function might contain references
            if isinstance(func_value, list):
                for item in func_value:
                    if isinstance(item, dict):
                        func_deps = self._extract_dependencies_from_cf_properties(
                            item, logical_id, all_resources
                        )
                        dependencies.extend(func_deps)
            elif isinstance(func_value, dict):
                func_deps = self._extract_dependencies_from_cf_properties(
                    func_value, logical_id, all_resources
                )
                dependencies.extend(func_deps)
        
        return dependencies
