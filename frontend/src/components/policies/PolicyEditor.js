import React, { useState, useEffect } from 'react';
import { FiSave, FiX, FiPlus, FiTrash2, FiCode, FiEye } from 'react-icons/fi';

const PolicyEditor = ({ policy, onSave, onCancel }) => {
  const [yamlContent, setYamlContent] = useState('');
  const [isValid, setIsValid] = useState(true);
  const [validationErrors, setValidationErrors] = useState([]);
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    if (policy) {
      // Convert policy to YAML format
      const yaml = convertPolicyToYaml(policy);
      setYamlContent(yaml);
    }
  }, [policy]);

  const convertPolicyToYaml = (policyData) => {
    return `
apiVersion: v1
kind: Policy
metadata:
  name: ${policyData.name || 'policy-name'}
  description: "${policyData.description || 'Policy description'}"
  category: ${policyData.category || 'SECURITY'}
  severity: ${policyData.severity || 'MEDIUM'}
  cloudProvider: ${policyData.cloudProvider || 'AWS'}
  resourceType: ${policyData.resourceType || 'aws:s3:bucket'}
  enabled: ${policyData.enabled !== false}
  mlEnhanced: ${policyData.mlEnhanced || false}
  mlThreshold: ${policyData.mlThreshold || 0.7}
  mlWeight: ${policyData.mlWeight || 0.7}
  tags:
${(policyData.tags || []).map(tag => `  - ${tag}`).join('\n')}

spec:
  rules:
${(policyData.rules || []).map(rule => `  - field: ${rule.field}
    operator: ${rule.operator}
    value: ${rule.value}
    condition: ${rule.condition}
    description: "${rule.description || ''}"`).join('\n')}

actions:
  - type: alert
    severity: ${policyData.severity || 'MEDIUM'}
  - type: block
    condition: mlEnhanced && violationProbability > ${policyData.mlThreshold || 0.7}
  
remediation:
  automated: false
  steps:
    - description: "Manual remediation required"
      command: "aws s3api put-bucket-acl --bucket $RESOURCE_NAME --acl private"
    `.trim();
  };

  const validateYaml = (content) => {
    try {
      // Basic YAML validation
      const lines = content.split('\n');
      const errors = [];
      
      lines.forEach((line, index) => {
        if (line.trim() && !line.includes(':') && !line.startsWith(' ') && !line.startsWith('-')) {
          errors.push(`Line ${index + 1}: Invalid YAML syntax`);
        }
      });

      setValidationErrors(errors);
      setIsValid(errors.length === 0);
      return errors.length === 0;
    } catch (error) {
      setValidationErrors([error.message]);
      setIsValid(false);
      return false;
    }
  };

  const handleYamlChange = (content) => {
    setYamlContent(content);
    validateYaml(content);
  };

  const handleSave = () => {
    if (!isValid) {
      return;
    }

    try {
      // Parse YAML back to policy object
      const policyData = parseYamlToPolicy(yamlContent);
      onSave(policyData);
    } catch (error) {
      console.error('Error parsing YAML:', error);
    }
  };

  const parseYamlToPolicy = (yaml) => {
    // Simple YAML parser for demonstration
    const lines = yaml.split('\n');
    const policy = {
      name: '',
      description: '',
      category: 'SECURITY',
      severity: 'MEDIUM',
      cloudProvider: 'AWS',
      resourceType: '',
      enabled: true,
      mlEnhanced: false,
      mlThreshold: 0.7,
      mlWeight: 0.7,
      tags: [],
      rules: []
    };

    let currentSection = '';
    let currentRule = null;

    lines.forEach(line => {
      const trimmed = line.trim();
      
      if (trimmed.startsWith('name:')) {
        policy.name = trimmed.split(':')[1].trim();
      } else if (trimmed.startsWith('description:')) {
        policy.description = trimmed.split(':')[1].trim().replace(/"/g, '');
      } else if (trimmed.startsWith('category:')) {
        policy.category = trimmed.split(':')[1].trim();
      } else if (trimmed.startsWith('severity:')) {
        policy.severity = trimmed.split(':')[1].trim();
      } else if (trimmed.startsWith('cloudProvider:')) {
        policy.cloudProvider = trimmed.split(':')[1].trim();
      } else if (trimmed.startsWith('resourceType:')) {
        policy.resourceType = trimmed.split(':')[1].trim();
      } else if (trimmed.startsWith('enabled:')) {
        policy.enabled = trimmed.split(':')[1].trim() === 'true';
      } else if (trimmed.startsWith('mlEnhanced:')) {
        policy.mlEnhanced = trimmed.split(':')[1].trim() === 'true';
      }
    });

    return policy;
  };

  const insertTemplate = (template) => {
    const templates = {
      's3-public': `
# S3 Public Access Policy
apiVersion: v1
kind: Policy
metadata:
  name: s3-public-access-denied
  description: "S3 buckets should not have public access"
  category: SECURITY
  severity: HIGH
  cloudProvider: AWS
  resourceType: aws:s3:bucket
spec:
  rules:
    - field: acl
      operator: NOT_EQUALS
      value: public-read
      condition: AND
    - field: policy
      operator: NOT_EQUALS
      value: public
      condition: AND
      `,
      'ec2-security': `
# EC2 Security Group Policy
apiVersion: v1
kind: Policy
metadata:
  name: ec2-security-group-restricted
  description: "EC2 instances should use restricted security groups"
  category: SECURITY
  severity: MEDIUM
  cloudProvider: AWS
  resourceType: aws:ec2:instance
spec:
  rules:
    - field: securityGroup
      operator: CONTAINS
      value: restricted
      condition: AND
      `
    };

    const templateContent = templates[template] || '';
    setYamlContent(templateContent);
    validateYaml(templateContent);
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Policy Editor
          </h2>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowPreview(!showPreview)}
              className="flex items-center space-x-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <FiEye size={16} />
              <span>{showPreview ? 'Hide' : 'Show'} Preview</span>
            </button>
            <button
              onClick={() => insertTemplate('s3-public')}
              className="flex items-center space-x-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <FiCode size={16} />
              <span>Template</span>
            </button>
          </div>
        </div>
      </div>

      {/* Editor */}
      <div className="flex h-96">
        {/* YAML Editor */}
        <div className="flex-1 flex flex-col">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                YAML Configuration
              </h3>
              <div className={`flex items-center space-x-2 text-xs ${
                isValid ? 'text-green-600' : 'text-red-600'
              }`}>
                <div className={`w-2 h-2 rounded-full ${
                  isValid ? 'bg-green-600' : 'bg-red-600'
                }`} />
                <span>{isValid ? 'Valid' : 'Invalid'}</span>
              </div>
            </div>
          </div>
          
          <div className="flex-1 p-6">
            <textarea
              value={yamlContent}
              onChange={(e) => handleYamlChange(e.target.value)}
              className={`w-full h-full p-4 font-mono text-sm border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                isValid
                  ? 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white'
                  : 'border-red-500 bg-red-50 dark:bg-red-900 text-red-900 dark:text-red-100'
              }`}
              placeholder="Enter policy configuration in YAML format..."
              spellCheck={false}
            />
          </div>

          {/* Validation Errors */}
          {validationErrors.length > 0 && (
            <div className="px-6 pb-4">
              <div className="bg-red-50 dark:bg-red-900 border border-red-200 dark:border-red-700 rounded-lg p-3">
                <h4 className="text-sm font-medium text-red-800 dark:text-red-200 mb-2">
                  Validation Errors
                </h4>
                <ul className="text-sm text-red-600 dark:text-red-300 space-y-1">
                  {validationErrors.map((error, index) => (
                    <li key={index}>• {error}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Preview Panel */}
        {showPreview && (
          <div className="w-96 border-l border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Preview
              </h3>
            </div>
            <div className="p-4 overflow-y-auto h-full">
              <div className="space-y-4">
                <div>
                  <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Policy Details
                  </h4>
                  <div className="mt-2 space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Name:</span>
                      <span className="text-sm text-gray-900 dark:text-white">
                        {policy?.name || 'Untitled Policy'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Category:</span>
                      <span className="text-sm text-gray-900 dark:text-white">
                        {policy?.category || 'SECURITY'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Severity:</span>
                      <span className="text-sm text-gray-900 dark:text-white">
                        {policy?.severity || 'MEDIUM'}
                      </span>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Rules
                  </h4>
                  <div className="mt-2 space-y-2">
                    {(policy?.rules || []).map((rule, index) => (
                      <div key={index} className="bg-white dark:bg-gray-800 p-2 rounded border border-gray-200 dark:border-gray-700">
                        <div className="text-xs text-gray-600 dark:text-gray-400">
                          {rule.field} {rule.operator} {rule.value}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    ML Settings
                  </h4>
                  <div className="mt-2 space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Enhanced:</span>
                      <span className="text-sm text-gray-900 dark:text-white">
                        {policy?.mlEnhanced ? 'Yes' : 'No'}
                      </span>
                    </div>
                    {policy?.mlEnhanced && (
                      <>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600 dark:text-gray-400">Threshold:</span>
                          <span className="text-sm text-gray-900 dark:text-white">
                            {policy?.mlThreshold}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600 dark:text-gray-400">Weight:</span>
                          <span className="text-sm text-gray-900 dark:text-white">
                            {policy?.mlWeight}
                          </span>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end space-x-3">
        <button
          onClick={onCancel}
          className="px-6 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleSave}
          disabled={!isValid}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <div className="flex items-center space-x-2">
            <FiSave size={16} />
            <span>Save Policy</span>
          </div>
        </button>
      </div>
    </div>
  );
};

export default PolicyEditor;
