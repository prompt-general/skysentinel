from flask import Flask, request, jsonify
import base64
import json
import logging
from typing import Dict, Any, List
from datetime import datetime

app = Flask(__name__)

class KubernetesAdmissionController:
    def __init__(self, cicd_service):
        self.cicd_service = cicd_service
        self.supported_kinds = [
            'Deployment',
            'Service',
            'ConfigMap',
            'Secret',
            'Ingress',
            'PersistentVolumeClaim',
            'StatefulSet',
            'DaemonSet',
            'Job',
            'CronJob'
        ]
    
    def validate_admission_request(self, request_data: Dict) -> Dict:
        """Validate Kubernetes admission request"""
        admission_request = request_data.get('request', {})
        
        # Extract resource information
        resource = admission_request.get('object', {})
        old_resource = admission_request.get('oldObject', {})
        operation = admission_request.get('operation', '')
        
        # Check if we should evaluate this resource
        if not self._should_evaluate(resource, operation):
            return self._allow_response()
        
        # Convert to IaC format
        iac_resource = self._convert_to_iac_resource(resource, operation)
        
        # Evaluate against policies
        violations = self._evaluate_resource(iac_resource)
        
        # Determine response
        if violations:
            return self._deny_response(violations)
        else:
            return self._allow_response()
    
    def _should_evaluate(self, resource: Dict, operation: str) -> bool:
        """Determine if resource should be evaluated"""
        # Only evaluate CREATE and UPDATE operations
        if operation not in ['CREATE', 'UPDATE']:
            return False
        
        # Check if kind is supported
        kind = resource.get('kind', '')
        if kind not in self.supported_kinds:
            return False
        
        # Check namespace (optional: skip kube-system, etc.)
        metadata = resource.get('metadata', {})
        namespace = metadata.get('namespace', 'default')
        if namespace in ['kube-system', 'kube-public']:
            return False
        
        return True
    
    def _convert_to_iac_resource(self, resource: Dict, operation: str) -> Dict:
        """Convert Kubernetes resource to IaC format"""
        metadata = resource.get('metadata', {})
        spec = resource.get('spec', {})
        
        # Determine change type
        change_type = "create" if operation == 'CREATE' else "update"
        
        # Extract annotations and labels as tags
        tags = metadata.get('labels', {})
        annotations = metadata.get('annotations', {})
        
        # Merge annotations with tags (with annotation prefix)
        for key, value in annotations.items():
            tags[f"annotation.{key}"] = value
        
        return {
            "iac_id": f"{resource.get('kind')}/{metadata.get('name')}",
            "resource_type": f"kubernetes:{resource.get('kind').lower()}",
            "cloud_provider": "kubernetes",
            "properties": {
                "apiVersion": resource.get('apiVersion'),
                "kind": resource.get('kind'),
                "metadata": metadata,
                "spec": spec
            },
            "tags": tags,
            "change_type": change_type,
            "metadata": {
                "namespace": metadata.get('namespace'),
                "creation_timestamp": metadata.get('creationTimestamp'),
                "uid": metadata.get('uid')
            }
        }
    
    def _evaluate_resource(self, resource: Dict) -> List[Dict]:
        """Evaluate resource against policies"""
        # Create evaluation event
        event = {
            "cloud": "kubernetes",
            "resource": {
                "id": resource['iac_id'],
                "type": resource['resource_type'],
                "properties": resource['properties'],
                "tags": resource['tags'],
                "change_type": resource['change_type']
            },
            "operation": f"{resource['change_type']}_resource",
            "principal": "kubernetes-admission",
            "source_ip": "0.0.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "context": {
                "stage": "kubernetes_admission"
            }
        }
        
        # Evaluate against policies
        return self.cicd_service.policy_engine.evaluate_event(event)
    
    def _allow_response(self) -> Dict:
        """Generate allow admission response"""
        return {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid": request.json['request']['uid'],
                "allowed": True
            }
        }
    
    def _deny_response(self, violations: List[Dict]) -> Dict:
        """Generate deny admission response"""
        messages = [v.get('description', 'Policy violation') for v in violations[:5]]
        message = "; ".join(messages)
        
        return {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid": request.json['request']['uid'],
                "allowed": False,
                "status": {
                    "code": 403,
                    "message": message,
                    "reason": "SkySentinelPolicyViolation"
                }
            }
        }

# Flask routes
controller = None

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/validate', methods=['POST'])
def validate():
    """Validate admission request"""
    try:
        request_data = request.json
        response = controller.validate_admission_request(request_data)
        return jsonify(response), 200
    except Exception as e:
        logging.error(f"Error validating admission: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/mutate', methods=['POST'])
def mutate():
    """Mutate admission request (future enhancement)"""
    # For MVP, we only validate
    return jsonify({
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "response": {
            "uid": request.json['request']['uid'],
            "allowed": True,
            "patchType": "JSONPatch",
            "patch": ""  # No mutations for MVP
        }
    }), 200

# Kubernetes configuration
def create_webhook_configuration():
    """Generate Kubernetes ValidatingWebhookConfiguration"""
    config = {
        "apiVersion": "admissionregistration.k8s.io/v1",
        "kind": "ValidatingWebhookConfiguration",
        "metadata": {
            "name": "skysentinel-webhook"
        },
        "webhooks": [
            {
                "name": "skysentinel.skysecurity.io",
                "rules": [
                    {
                        "apiGroups": ["*"],
                        "apiVersions": ["*"],
                        "operations": ["CREATE", "UPDATE"],
                        "resources": ["*"]
                    }
                ],
                "failurePolicy": "Fail",
                "sideEffects": "None",
                "admissionReviewVersions": ["v1"],
                "clientConfig": {
                    "service": {
                        "name": "skysentinel-webhook",
                        "namespace": "skysentinel",
                        "path": "/validate",
                        "port": 443
                    },
                    "caBundle": "<CA_BUNDLE>"
                }
            }
        ]
    }
    return config
