import React, { useState, useEffect } from 'react';
import { FiSave, FiX, FiPlus, FiTrash2 } from 'react-icons/fi';

const PolicyForm = ({ policy, onSave, onCancel, initialData = {} }) => {
  const [formData, setFormData] = useState({
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
    rules: [],
    ...initialData
  });

  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const categories = ['SECURITY', 'COMPLIANCE', 'COST', 'OPERATIONS', 'GOVERNANCE'];
  const severities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];
  const cloudProviders = ['AWS', 'AZURE', 'GCP', 'KUBERNETES'];
  const resourceTypes = {
    'AWS': [
      'aws:s3:bucket',
      'aws:ec2:instance',
      'aws:iam:role',
      'aws:rds:dbinstance',
      'aws:security:group'
    ],
    'AZURE': [
      'azure:storage:blob',
      'azure:compute:virtualmachine',
      'azure:network:securitygroup',
      'azure:database:mysql',
      'azure:container:container'
    ],
    'GCP': [
      'gcp:compute:instance',
      'gcp:storage:bucket',
      'gcp:sql:database',
      'gcp:iam:service-account',
      'gcp:cloudfunction'
    ],
    'KUBERNETES': [
      'kubernetes:deployment',
      'kubernetes:service',
      'kubernetes:configmap',
      'kubernetes:secret',
      'kubernetes:ingress'
    ]
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.name.trim()) {
      newErrors.name = 'Policy name is required';
    }
    
    if (!formData.description.trim()) {
      newErrors.description = 'Description is required';
    }
    
    if (!formData.resourceType.trim()) {
      newErrors.resourceType = 'Resource type is required';
    }
    
    if (formData.rules.length === 0) {
      newErrors.rules = 'At least one rule is required';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    
    try {
      await onSave(formData);
      setFormData({
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
      });
    } catch (error) {
      console.error('Error saving policy:', error);
      setErrors({ submit: 'Failed to save policy' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear related errors when user starts typing
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const handleRuleChange = (index, field, value) => {
    const newRules = [...formData.rules];
    newRules[index] = {
      ...newRules[index],
      [field]: value
    };
    setFormData(prev => ({ ...prev, rules: newRules }));
  };

  const addRule = () => {
    const newRule = {
      id: Date.now().toString(),
      field: '',
      operator: 'EQUALS',
      value: '',
      condition: 'AND',
      description: ''
    };
    
    setFormData(prev => ({
      ...prev,
      rules: [...prev.rules, newRule]
    }));
  };

  const removeRule = (index) => {
    const newRules = formData.rules.filter((_, i) => i !== index);
    setFormData(prev => ({ ...prev, rules: newRules }));
  };

  const handleTagAdd = (tag) => {
    if (tag && !formData.tags.includes(tag)) {
      setFormData(prev => ({
        ...prev,
        tags: [...prev.tags, tag]
      }));
    }
  };

  const handleTagRemove = (tagToRemove) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(tag => tag !== tagToRemove)
    }));
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg">
      <form onSubmit={handleSubmit}>
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            {policy?.id ? 'Edit Policy' : 'Create New Policy'}
          </h2>
        </div>

        <div className="px-6 pb-6 space-y-6">
          {/* Basic Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Policy Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                className={`w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                  errors.name ? 'border-red-500' : ''
                }`}
                placeholder="Enter policy name"
              />
              {errors.name && (
                <p className="text-red-500 text-xs mt-1">{errors.name}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Description *
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                rows={3}
                className={`w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                  errors.description ? 'border-red-500' : ''
                }`}
                placeholder="Describe what this policy does"
              />
              {errors.description && (
                <p className="text-red-500 text-xs mt-1">{errors.description}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Category *
              </label>
              <select
                value={formData.category}
                onChange={(e) => handleInputChange('category', e.target.value)}
                className={`w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
              >
                {categories.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Severity *
              </label>
              <select
                value={formData.severity}
                onChange={(e) => handleInputChange('severity', e.target.value)}
                className={`w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
              >
                {severities.map((severity) => (
                  <option key={severity} value={severity}>
                    {severity}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Cloud Provider *
              </label>
              <select
                value={formData.cloudProvider}
                onChange={(e) => handleInputChange('cloudProvider', e.target.value)}
                className={`w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
              >
                {cloudProviders.map((provider) => (
                  <option key={provider} value={provider}>
                    {provider}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Resource Type *
              </label>
              <select
                value={formData.resourceType}
                onChange={(e) => handleInputChange('resourceType', e.target.value)}
                className={`w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
              >
                <option value="">Select resource type...</option>
                {formData.cloudProvider && resourceTypes[formData.cloudProvider]?.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
              {errors.resourceType && (
                <p className="text-red-500 text-xs mt-1">{errors.resourceType}</p>
              )}
            </div>
          </div>

          {/* ML Enhancement */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="flex items-center space-x-3">
              <input
                type="checkbox"
                id="ml-enhanced"
                checked={formData.mlEnhanced}
                onChange={(e) => handleInputChange('mlEnhanced', e.target.checked)}
                className="h-4 w-4 text-blue-600 rounded border-gray-300 dark:border-gray-600 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <label htmlFor="ml-enhanced" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                ML Enhanced
              </label>
            </div>

            {formData.mlEnhanced && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    ML Threshold
                  </label>
                  <input
                    type="number"
                    value={formData.mlThreshold}
                    onChange={(e) => handleInputChange('mlThreshold', e.target.value)}
                    min="0"
                    max="1"
                    step="0.1"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    Probability threshold for blocking violations
                  </span>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    ML Weight
                  </label>
                  <input
                    type="number"
                    value={formData.mlWeight}
                    onChange={(e) => handleInputChange('mlWeight', e.target.value)}
                    min="0"
                    max="1"
                    step="0.1"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    Weight for ML predictions
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Tags */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Tags
              </label>
              <button
                type="button"
                onClick={addRule}
                className="px-3 py-1 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900 rounded-lg transition-colors"
              >
                <FiPlus size={16} />
                Add Rule
              </button>
            </div>

            <div className="space-y-2">
              {formData.rules.map((rule, index) => (
                <div key={rule.id} className="flex items-center space-x-2 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <input
                    type="text"
                    value={rule.field}
                    onChange={(e) => handleRuleChange(index, 'field', e.target.value)}
                    placeholder="Field name"
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <select
                    value={rule.operator}
                    onChange={(e) => handleRuleChange(index, 'operator', e.target.value)}
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="EQUALS">Equals</option>
                    <option value="NOT_EQUALS">Not Equals</option>
                    <option value="CONTAINS">Contains</option>
                    <option value="NOT_CONTAINS">Not Contains</option>
                    <option value="GREATER_THAN">Greater Than</option>
                    <option value="LESS_THAN">Less Than</option>
                    <option value="IN">In</option>
                    <option value="NOT_IN">Not In</option>
                    <option value="REGEX">Regex</option>
                  </select>
                  <input
                    type="text"
                    value={rule.value}
                    onChange={(e) => handleRuleChange(index, 'value', e.target.value)}
                    placeholder="Value"
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <button
                    type="button"
                    onClick={() => removeRule(index)}
                    className="text-red-600 hover:text-red-800 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900 rounded-lg transition-colors"
                  >
                    <FiTrash2 size={16} />
                  </button>
                </div>
              ))}
            </div>

            {/* Tags */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Tags
              </label>
              <div className="flex flex-wrap gap-2">
                <input
                  type="text"
                  placeholder="Add tag..."
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' && e.target.value.trim()) {
                      handleTagAdd(e.target.value);
                    }
                  }}
                  className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <button
                  onClick={() => handleTagAdd('')}
                  className="px-3 py-2 text-blue-600 hover:text-blue-800 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900 rounded-lg transition-colors"
                >
                  <FiPlus size={16} />
                </button>
              </div>
              
              {formData.tags.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {formData.tags.map((tag, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full text-xs"
                    >
                      {tag}
                      <button
                        onClick={() => handleTagRemove(tag)}
                        className="ml-1 text-red-600 hover:text-red-800 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900 rounded-full transition-colors"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end space-x-3 pt-6">
            <button
              type="button"
              onClick={() => onCancel()}
              className="px-6 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {isSubmitting ? (
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-300 dark:border-gray-600 border-t-transparent border-b-transparent"></div>
                  <span>Saving...</span>
                </div>
              ) : (
                <div className="flex items-center space-x-2">
                  <FiSave size={16} />
                  <span>{policy?.id ? 'Update' : 'Save'} Policy</span>
                </div>
              )}
            </button>
        </div>
      </form>
    </div>
  );
};

export default PolicyForm;
