import yaml
import json
from typing import Dict, List, Any, Union, Optional, Set
from datetime import datetime
import logging

from .base import (
    IaCAdapter, IaCType, IaCPlan, IaCResource, IaCDependency, 
    IaCValidationResult, ResourceType, CloudProvider
)


class KubernetesAdapter(IaCAdapter):
    """Kubernetes YAML/JSON IaC adapter"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def get_iac_type(self) -> IaCType:
        return IaCType.KUBERNETES
    
    def _get_resource_type_mapping(self) -> Dict[str, ResourceType]:
        """Map Kubernetes resource types to standardized types"""
        return {
            # Compute resources
            'Pod': ResourceType.COMPUTE,
            'Deployment': ResourceType.COMPUTE,
            'ReplicaSet': ResourceType.COMPUTE,
            'StatefulSet': ResourceType.COMPUTE,
            'DaemonSet': ResourceType.COMPUTE,
            'Job': ResourceType.COMPUTE,
            'CronJob': ResourceType.COMPUTE,
            
            # Container resources
            'Namespace': ResourceType.CONTAINER,
            'Node': ResourceType.CONTAINER,
            'Cluster': ResourceType.CONTAINER,
            
            # Network resources
            'Service': ResourceType.NETWORK,
            'Ingress': ResourceType.NETWORK,
            'NetworkPolicy': ResourceType.SECURITY,
            'Endpoint': ResourceType.NETWORK,
            'EndpointSlice': ResourceType.NETWORK,
            
            # Storage resources
            'PersistentVolume': ResourceType.STORAGE,
            'PersistentVolumeClaim': ResourceType.STORAGE,
            'StorageClass': ResourceType.STORAGE,
            'Volume': ResourceType.STORAGE,
            'VolumeAttachment': ResourceType.STORAGE,
            
            # Configuration resources
            'ConfigMap': ResourceType.OTHER,
            'Secret': ResourceType.SECURITY,
            'ResourceQuota': ResourceType.OTHER,
            'LimitRange': ResourceType.OTHER,
            
            # Security resources
            'Role': ResourceType.IDENTITY,
            'RoleBinding': ResourceType.IDENTITY,
            'ClusterRole': ResourceType.IDENTITY,
            'ClusterRoleBinding': ResourceType.IDENTITY,
            'ServiceAccount': ResourceType.IDENTITY,
            'PodSecurityPolicy': ResourceType.SECURITY,
            
            # Monitoring resources
            'HorizontalPodAutoscaler': ResourceType.MONITORING,
            'VerticalPodAutoscaler': ResourceType.MONITORING,
            'PodDisruptionBudget': ResourceType.MONITORING,
            
            # Application resources
            'CustomResourceDefinition': ResourceType.OTHER,
            'CustomResource': ResourceType.OTHER,
        }
    
    def _get_provider_mapping(self) -> Dict[str, CloudProvider]:
        """Map Kubernetes providers to CloudProvider enum"""
        return {
            'kubernetes': CloudProvider.KUBERNETES,
            'k8s': CloudProvider.KUBERNETES,
        }
    
    def parse_plan(self, plan_content: Union[str, Dict]) -> IaCPlan:
        """Parse Kubernetes manifest or kubectl output"""
        if isinstance(plan_content, str):
            try:
                # Try YAML first, then JSON
                try:
                    data = yaml.safe_load(plan_content)
                except yaml.YAMLError:
                    data = json.loads(plan_content)
            except (yaml.YAMLError, json.JSONDecodeError) as e:
                raise ValueError(f"Invalid Kubernetes manifest: {e}")
        else:
            data = plan_content
        
        # Handle list of resources or single resource
        if isinstance(data, dict):
            resources = [data]
        elif isinstance(data, list):
            resources = data
        else:
            raise ValueError("Kubernetes manifest must be a dict or list")
        
        # Create plan object
        plan = IaCPlan(
            id='kubernetes-manifest',
            iac_type=self.get_iac_type(),
            version='unknown',
            created_at=datetime.utcnow(),
            metadata={
                'resource_count': len(resources),
                'source': 'kubernetes_manifest'
            }
        )
        
        # Parse each resource
        for resource_data in resources:
            resource = self._parse_kubernetes_resource(resource_data)
            if resource:
                plan.resources.append(resource)
        
        # Extract dependencies
        dependencies = self.extract_dependencies({'resources': resources})
        for dep in dependencies:
            for resource in plan.resources:
                if resource.id == dep.source_id:
                    resource.dependencies.add(dep.target_id)
        
        return plan
    
    def parse_configuration(self, config_content: Union[str, Dict]) -> IaCPlan:
        """Parse Kubernetes configuration (same as manifest)"""
        return self.parse_plan(config_content)
    
    def normalize_resource(self, raw_resource: Dict) -> IaCResource:
        """Normalize Kubernetes resource to unified model"""
        api_version = raw_resource.get('apiVersion', '')
        kind = raw_resource.get('kind', '')
        metadata = raw_resource.get('metadata', {})
        spec = raw_resource.get('spec', {})
        
        # Extract resource name and namespace
        resource_name = metadata.get('name', '')
        namespace = metadata.get('namespace', 'default')
        
        # Create resource ID
        resource_id = f"{kind.lower()}.{namespace}.{resource_name}"
        
        # Extract provider (always Kubernetes)
        provider = CloudProvider.KUBERNETES
        
        # Create properties
        properties = {
            'api_version': api_version,
            'kind': kind,
            'namespace': namespace,
            'spec': spec,
            'status': raw_resource.get('status', {}),
            'metadata': {
                'labels': metadata.get('labels', {}),
                'annotations': metadata.get('annotations', {}),
                'uid': metadata.get('uid', ''),
                'creation_timestamp': metadata.get('creationTimestamp', ''),
                **{k: v for k, v in metadata.items() 
                   if k not in ['name', 'namespace', 'labels', 'annotations', 'uid', 'creationTimestamp']}
            }
        }
        
        return IaCResource(
            id=resource_id,
            type=f"{api_version}/{kind}",
            name=resource_name,
            provider=provider,
            resource_category=self._normalize_resource_type(kind),
            properties=self._sanitize_properties(properties),
            change_type='create',
            metadata={
                'api_version': api_version,
                'kind': kind,
                'namespace': namespace,
                'uid': metadata.get('uid', ''),
                'generation': metadata.get('generation', 0)
            }
        )
    
    def extract_dependencies(self, iac_content: Dict) -> List[IaCDependency]:
        """Extract dependencies from Kubernetes resources"""
        dependencies = []
        resources = iac_content.get('resources', [])
        
        # Build resource lookup
        resource_lookup = {}
        for resource in resources:
            kind = resource.get('kind', '')
            metadata = resource.get('metadata', {})
            name = metadata.get('name', '')
            namespace = metadata.get('namespace', 'default')
            resource_key = f"{kind.lower()}.{namespace}.{name}"
            resource_lookup[name] = resource
            resource_lookup[f"{namespace}/{name}"] = resource
            resource_lookup[f"{kind.lower()}/{name}"] = resource
        
        for resource in resources:
            kind = resource.get('kind', '')
            metadata = resource.get('metadata', {})
            spec = resource.get('spec', {})
            resource_name = metadata.get('name', '')
            namespace = metadata.get('namespace', 'default')
            source_id = f"{kind.lower()}.{namespace}.{resource_name}"
            
            # Extract dependencies based on resource type
            if kind == 'Pod':
                deps = self._extract_pod_dependencies(spec, resource_lookup)
                dependencies.extend(deps)
            elif kind == 'Deployment':
                deps = self._extract_deployment_dependencies(spec, resource_lookup)
                dependencies.extend(deps)
            elif kind == 'Service':
                deps = self._extract_service_dependencies(spec, resource_lookup)
                dependencies.extend(deps)
            elif kind == 'Ingress':
                deps = self._extract_ingress_dependencies(spec, resource_lookup)
                dependencies.extend(deps)
            elif kind == 'PersistentVolumeClaim':
                deps = self._extract_pvc_dependencies(spec, resource_lookup)
                dependencies.extend(deps)
            elif kind == 'ConfigMap':
                deps = self._extract_configmap_dependencies(resource, resource_lookup)
                dependencies.extend(deps)
            elif kind == 'Secret':
                deps = self._extract_secret_dependencies(resource, resource_lookup)
                dependencies.extend(deps)
            
            # Extract volume dependencies
            volume_deps = self._extract_volume_dependencies(spec, resource_lookup, namespace)
            dependencies.extend(volume_deps)
        
        return dependencies
    
    def validate_syntax(self, content: Union[str, Dict]) -> IaCValidationResult:
        """Validate Kubernetes manifest syntax"""
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
        
        # Handle list of resources or single resource
        if isinstance(data, dict):
            resources = [data]
        elif isinstance(data, list):
            resources = data
        else:
            result.is_valid = False
            result.errors.append("Kubernetes manifest must be a dict or list")
            return result
        
        # Validate each resource
        for resource in resources:
            if not isinstance(resource, dict):
                result.errors.append("Each resource must be a dictionary")
                result.is_valid = False
                continue
            
            # Check required fields
            if 'apiVersion' not in resource:
                result.errors.append("Resource missing apiVersion")
                result.is_valid = False
            
            if 'kind' not in resource:
                result.errors.append("Resource missing kind")
                result.is_valid = False
            
            if 'metadata' not in resource:
                result.errors.append("Resource missing metadata")
                result.is_valid = False
            else:
                metadata = resource['metadata']
                if not isinstance(metadata, dict):
                    result.errors.append("Resource metadata must be a dictionary")
                    result.is_valid = False
                elif 'name' not in metadata:
                    result.errors.append("Resource metadata missing name")
                    result.is_valid = False
        
        return result
    
    def _parse_kubernetes_resource(self, resource_data: Dict) -> Optional[IaCResource]:
        """Parse Kubernetes resource"""
        try:
            return self.normalize_resource(resource_data)
        except Exception as e:
            self.logger.warning(f"Failed to parse Kubernetes resource: {e}")
            return None
    
    def _extract_pod_dependencies(self, spec: Dict, resource_lookup: Dict) -> List[IaCDependency]:
        """Extract dependencies from Pod spec"""
        dependencies = []
        
        # Service Account dependency
        service_account_name = spec.get('serviceAccountName')
        if service_account_name and service_account_name in resource_lookup:
            sa_resource = resource_lookup[service_account_name]
            dependencies.append(IaCDependency(
                source_id=f"pod.default.{spec.get('name', 'unknown')}",
                target_id=f"serviceaccount.default.{service_account_name}",
                dependency_type='service_account'
            ))
        
        # ConfigMap and Secret dependencies from volumes
        volumes = spec.get('volumes', [])
        for volume in volumes:
            if 'configMap' in volume:
                cm_name = volume['configMap'].get('name')
                if cm_name and cm_name in resource_lookup:
                    dependencies.append(IaCDependency(
                        source_id=f"pod.default.{spec.get('name', 'unknown')}",
                        target_id=f"configmap.default.{cm_name}",
                        dependency_type='volume',
                        property_path=f"volumes.{volume.get('name', 'unknown')}"
                    ))
            
            if 'secret' in volume:
                secret_name = volume['secret'].get('secretName')
                if secret_name and secret_name in resource_lookup:
                    dependencies.append(IaCDependency(
                        source_id=f"pod.default.{spec.get('name', 'unknown')}",
                        target_id=f"secret.default.{secret_name}",
                        dependency_type='volume',
                        property_path=f"volumes.{volume.get('name', 'unknown')}"
                    ))
            
            if 'persistentVolumeClaim' in volume:
                pvc_name = volume['persistentVolumeClaim'].get('claimName')
                if pvc_name and pvc_name in resource_lookup:
                    dependencies.append(IaCDependency(
                        source_id=f"pod.default.{spec.get('name', 'unknown')}",
                        target_id=f"persistentvolumeclaim.default.{pvc_name}",
                        dependency_type='volume',
                        property_path=f"volumes.{volume.get('name', 'unknown')}"
                    ))
        
        return dependencies
    
    def _extract_deployment_dependencies(self, spec: Dict, resource_lookup: Dict) -> List[IaCDependency]:
        """Extract dependencies from Deployment spec"""
        dependencies = []
        
        # Pod template dependencies
        pod_template = spec.get('template', {})
        pod_spec = pod_template.get('spec', {})
        
        # Service Account
        service_account_name = pod_spec.get('serviceAccountName')
        if service_account_name and service_account_name in resource_lookup:
            dependencies.append(IaCDependency(
                source_id=f"deployment.default.{spec.get('name', 'unknown')}",
                target_id=f"serviceaccount.default.{service_account_name}",
                dependency_type='service_account'
            ))
        
        return dependencies
    
    def _extract_service_dependencies(self, spec: Dict, resource_lookup: Dict) -> List[IaCDependency]:
        """Extract dependencies from Service spec"""
        dependencies = []
        
        # Selector dependencies (pods/deployments)
        selector = spec.get('selector', {})
        match_labels = selector.get('matchLabels', {})
        
        # This is more complex as it depends on label matching
        # For now, we'll note the dependency type
        if match_labels:
            dependencies.append(IaCDependency(
                source_id=f"service.default.{spec.get('name', 'unknown')}",
                target_id="pods-with-matching-labels",
                dependency_type='selector',
                property_path=str(match_labels)
            ))
        
        return dependencies
    
    def _extract_ingress_dependencies(self, spec: Dict, resource_lookup: Dict) -> List[IaCDependency]:
        """Extract dependencies from Ingress spec"""
        dependencies = []
        
        # Service dependencies from rules
        rules = spec.get('rules', [])
        for rule in rules:
            http = rule.get('http', {})
            paths = http.get('paths', [])
            for path in paths:
                backend = path.get('backend', {})
                service = backend.get('service', {})
                service_name = service.get('name')
                
                if service_name and service_name in resource_lookup:
                    dependencies.append(IaCDependency(
                        source_id=f"ingress.default.{spec.get('name', 'unknown')}",
                        target_id=f"service.default.{service_name}",
                        dependency_type='backend',
                        property_path=f"rules.{rule.get('host', 'unknown')}"
                    ))
        
        return dependencies
    
    def _extract_pvc_dependencies(self, spec: Dict, resource_lookup: Dict) -> List[IaCDependency]:
        """Extract dependencies from PersistentVolumeClaim spec"""
        dependencies = []
        
        # StorageClass dependency
        storage_class_name = spec.get('storageClassName')
        if storage_class_name and storage_class_name in resource_lookup:
            dependencies.append(IaCDependency(
                source_id=f"persistentvolumeclaim.default.{spec.get('name', 'unknown')}",
                target_id=f"storageclass.{storage_class_name}",
                dependency_type='storage_class'
            ))
        
        return dependencies
    
    def _extract_configmap_dependencies(self, resource: Dict, resource_lookup: Dict) -> List[IaCDependency]:
        """Extract dependencies from ConfigMap"""
        dependencies = []
        
        # ConfigMaps typically don't have dependencies on other resources
        # But they might reference other ConfigMaps in some cases
        
        return dependencies
    
    def _extract_secret_dependencies(self, resource: Dict, resource_lookup: Dict) -> List[IaCDependency]:
        """Extract dependencies from Secret"""
        dependencies = []
        
        # Secrets might reference other secrets or certificates
        # This is less common but possible
        
        return dependencies
    
    def _extract_volume_dependencies(self, spec: Dict, resource_lookup: Dict, namespace: str) -> List[IaCDependency]:
        """Extract volume dependencies from any spec"""
        dependencies = []
        
        volumes = spec.get('volumes', [])
        for volume in volumes:
            volume_name = volume.get('name', '')
            
            if 'configMap' in volume:
                cm_name = volume['configMap'].get('name')
                if cm_name and f"{namespace}/{cm_name}" in resource_lookup:
                    dependencies.append(IaCDependency(
                        source_id=f"resource.{namespace}.unknown",  # Will be overridden by caller
                        target_id=f"configmap.{namespace}.{cm_name}",
                        dependency_type='volume',
                        property_path=f"volumes.{volume_name}"
                    ))
            
            if 'secret' in volume:
                secret_name = volume['secret'].get('secretName')
                if secret_name and f"{namespace}/{secret_name}" in resource_lookup:
                    dependencies.append(IaCDependency(
                        source_id=f"resource.{namespace}.unknown",  # Will be overridden by caller
                        target_id=f"secret.{namespace}.{secret_name}",
                        dependency_type='volume',
                        property_path=f"volumes.{volume_name}"
                    ))
            
            if 'persistentVolumeClaim' in volume:
                pvc_name = volume['persistentVolumeClaim'].get('claimName')
                if pvc_name and f"{namespace}/{pvc_name}" in resource_lookup:
                    dependencies.append(IaCDependency(
                        source_id=f"resource.{namespace}.unknown",  # Will be overridden by caller
                        target_id=f"persistentvolumeclaim.{namespace}.{pvc_name}",
                        dependency_type='volume',
                        property_path=f"volumes.{volume_name}"
                    ))
        
        return dependencies
    
    def _extract_cloud_provider(self, resource: Dict) -> CloudProvider:
        """Extract cloud provider from Kubernetes resource"""
        # Kubernetes is always Kubernetes
        return CloudProvider.KUBERNETES


# Register the adapter
from .base import IaCAdapterFactory
IaCAdapterFactory.register_adapter(IaCType.KUBERNETES, KubernetesAdapter)
