import React, { useState, useEffect } from 'react';
import { FiAlertTriangle, FiCheckCircle, FiClock, FiEye, FiEdit, FiTrash2, FiDownload, FiExternalLink, FiShield, FiDatabase, FiActivity, FiTrendingUp, FiInfo } from 'react-icons/fi';
import { formatDistanceToNow } from 'date-fns';

const ViolationDetail = ({ violation, onUpdate, onResolve, onIgnore, onDelete }) => {
  const [activeTab, setActiveTab] = useState('details');
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({});

  useEffect(() => {
    if (violation) {
      setEditForm({
        status: violation.status,
        notes: violation.notes || '',
        tags: violation.tags || []
      });
    }
  }, [violation]);

  if (!violation) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
        <div className="text-center py-12">
          <FiAlertTriangle className="mx-auto text-gray-400 text-4xl mb-4" />
          <p className="text-gray-500 dark:text-gray-400">No violation selected</p>
        </div>
      </div>
    );
  }

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'CRITICAL':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'HIGH':
        return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'MEDIUM':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'LOW':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'OPEN':
        return <FiAlertTriangle className="text-red-500" />;
      case 'IN_PROGRESS':
        return <FiClock className="text-yellow-500" />;
      case 'RESOLVED':
        return <FiCheckCircle className="text-green-500" />;
      case 'IGNORED':
        return <FiEye className="text-gray-500" />;
      default:
        return <FiAlertTriangle className="text-gray-500" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'OPEN':
        return 'bg-red-100 text-red-800';
      case 'IN_PROGRESS':
        return 'bg-yellow-100 text-yellow-800';
      case 'RESOLVED':
        return 'bg-green-100 text-green-800';
      case 'IGNORED':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const handleSave = () => {
    onUpdate(violation.id, editForm);
    setIsEditing(false);
  };

  const handleResolve = () => {
    onResolve(violation.id, {
      type: 'FIXED',
      notes: editForm.notes,
      evidence: []
    });
  };

  const handleIgnore = () => {
    onIgnore(violation.id, editForm.notes);
  };

  const exportViolation = () => {
    const data = {
      violation: {
        id: violation.id,
        policy: violation.policy,
        resource: violation.resource,
        severity: violation.severity,
        description: violation.description,
        status: violation.status,
        timestamp: violation.timestamp,
        confidence: violation.confidence,
        falsePositive: violation.falsePositive,
        tags: violation.tags,
        evidence: violation.evidence
      },
      exportedAt: new Date().toISOString()
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `violation-${violation.id}.json`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const renderDetailsTab = () => (
    <div className="space-y-6">
      {/* Basic Information */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Basic Information</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Severity
            </label>
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${getSeverityColor(violation.severity)}`}>
              {violation.severity}
            </span>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Status
            </label>
            <div className="flex items-center space-x-2">
              {getStatusIcon(violation.status)}
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(violation.status)}`}>
                {violation.status}
              </span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Confidence
            </label>
            <div className="flex items-center space-x-2">
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full"
                  style={{ width: `${violation.confidence * 100}%` }}
                />
              </div>
              <span className="text-sm text-gray-900 dark:text-white">
                {Math.round(violation.confidence * 100)}%
              </span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              False Positive
            </label>
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
              violation.falsePositive
                ? 'bg-red-100 text-red-800'
                : 'bg-green-100 text-green-800'
            }`}>
              {violation.falsePositive ? 'Yes' : 'No'}
            </span>
          </div>
        </div>
      </div>

      {/* Policy Information */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Policy Information</h3>
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Policy Name
              </label>
              <p className="text-sm text-gray-900 dark:text-white">{violation.policy.name}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Category
              </label>
              <p className="text-sm text-gray-900 dark:text-white">{violation.policy.category}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Cloud Provider
              </label>
              <p className="text-sm text-gray-900 dark:text-white">{violation.policy.cloudProvider}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Resource Type
              </label>
              <p className="text-sm text-gray-900 dark:text-white">{violation.policy.resourceType}</p>
            </div>
          </div>
          {violation.policy.description && (
            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Policy Description
              </label>
              <p className="text-sm text-gray-900 dark:text-white">{violation.policy.description}</p>
            </div>
          )}
        </div>
      </div>

      {/* Resource Information */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Resource Information</h3>
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Resource Name
              </label>
              <p className="text-sm text-gray-900 dark:text-white">{violation.resource.name}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Type
              </label>
              <p className="text-sm text-gray-900 dark:text-white">{violation.resource.type}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Cloud Provider
              </label>
              <p className="text-sm text-gray-900 dark:text-white">{violation.resource.cloud}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Region
              </label>
              <p className="text-sm text-gray-900 dark:text-white">{violation.resource.region}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Account
              </label>
              <p className="text-sm text-gray-900 dark:text-white">{violation.resource.account}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                State
              </label>
              <p className="text-sm text-gray-900 dark:text-white">{violation.resource.state}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Description */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Description</h3>
        <p className="text-sm text-gray-900 dark:text-white bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
          {violation.description}
        </p>
      </div>

      {/* Timeline */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Timeline</h3>
        <div className="space-y-3">
          <div className="flex items-center space-x-3">
            <FiAlertTriangle className="text-red-500" />
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">First Detected</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {formatDistanceToNow(new Date(violation.firstDetected), { addSuffix: true })}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <FiActivity className="text-blue-500" />
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">Last Detected</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {formatDistanceToNow(new Date(violation.lastDetected), { addSuffix: true })}
              </p>
            </div>
          </div>
          {violation.resolvedAt && (
            <div className="flex items-center space-x-3">
              <FiCheckCircle className="text-green-500" />
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">Resolved</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {formatDistanceToNow(new Date(violation.resolvedAt), { addSuffix: true })}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const renderMLTab = () => (
    <div className="space-y-6">
      {violation.mlPrediction ? (
        <>
          {/* ML Prediction Summary */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">ML Prediction Summary</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Violation Probability
                </label>
                <div className="flex items-center space-x-2">
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-red-600 h-2 rounded-full"
                      style={{ width: `${violation.mlPrediction.violationProbability * 100}%` }}
                    />
                  </div>
                  <span className="text-sm text-gray-900 dark:text-white">
                    {Math.round(violation.mlPrediction.violationProbability * 100)}%
                  </span>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Model Confidence
                </label>
                <div className="flex items-center space-x-2">
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{ width: `${violation.mlPrediction.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-sm text-gray-900 dark:text-white">
                    {Math.round(violation.mlPrediction.confidence * 100)}%
                  </span>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Model Type
                </label>
                <p className="text-sm text-gray-900 dark:text-white">{violation.mlPrediction.modelType}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Model Version
                </label>
                <p className="text-sm text-gray-900 dark:text-white">{violation.mlPrediction.modelVersion}</p>
              </div>
            </div>
          </div>

          {/* Risk Factors */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Risk Factors</h3>
            <div className="space-y-3">
              {violation.mlPrediction.riskFactors?.map((factor, index) => (
                <div key={index} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">{factor.factor}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{factor.description}</p>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-24 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                        <div
                          className="bg-orange-600 h-2 rounded-full"
                          style={{ width: `${factor.weight * 100}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-900 dark:text-white">
                        {Math.round(factor.weight * 100)}%
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Explanation */}
          {violation.mlPrediction.explanation && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Model Explanation</h3>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <pre className="text-sm text-gray-900 dark:text-white whitespace-pre-wrap">
                  {JSON.stringify(violation.mlPrediction.explanation, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Features */}
          {violation.mlPrediction.features && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Model Features</h3>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <pre className="text-sm text-gray-900 dark:text-white whitespace-pre-wrap">
                  {JSON.stringify(violation.mlPrediction.features, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-12">
          <FiInfo className="mx-auto text-gray-400 text-4xl mb-4" />
          <p className="text-gray-500 dark:text-gray-400">No ML prediction data available</p>
        </div>
      )}
    </div>
  );

  const renderRemediationTab = () => (
    <div className="space-y-6">
      {violation.remediation ? (
        <>
          {/* Remediation Summary */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Remediation Summary</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Type
                </label>
                <p className="text-sm text-gray-900 dark:text-white">{violation.remediation.type}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Status
                </label>
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                  violation.remediation.status === 'COMPLETED'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-yellow-100 text-yellow-800'
                }`}>
                  {violation.remediation.status}
                </span>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Automated
                </label>
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                  violation.remediation.automated
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {violation.remediation.automated ? 'Yes' : 'No'}
                </span>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Risk Reduction
                </label>
                <p className="text-sm text-gray-900 dark:text-white">{violation.remediation.riskReduction}%</p>
              </div>
            </div>
          </div>

          {/* Remediation Steps */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Remediation Steps</h3>
            <div className="space-y-3">
              {violation.remediation.steps?.map((step, index) => (
                <div key={index} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs">
                      {step.order}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                        {step.description}
                      </p>
                      {step.command && (
                        <div className="bg-gray-900 text-gray-100 rounded p-2 mt-2">
                          <code className="text-xs">{step.command}</code>
                        </div>
                      )}
                      {step.rollbackCommand && (
                        <div className="mt-2">
                          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Rollback:</p>
                          <div className="bg-gray-900 text-gray-100 rounded p-2">
                            <code className="text-xs">{step.rollbackCommand}</code>
                          </div>
                        </div>
                      )}
                      <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500 dark:text-gray-400">
                        <span>Est. time: {step.estimatedTime}s</span>
                        {step.dependencies.length > 0 && (
                          <span>Dependencies: {step.dependencies.join(', ')}</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : (
        <div className="text-center py-12">
          <FiInfo className="mx-auto text-gray-400 text-4xl mb-4" />
          <p className="text-gray-500 dark:text-gray-400">No remediation data available</p>
        </div>
      )}
    </div>
  );

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Violation Details
          </h2>
          <div className="flex items-center space-x-3">
            <button
              onClick={exportViolation}
              className="flex items-center space-x-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <FiDownload size={16} />
              <span>Export</span>
            </button>
            <button
              onClick={() => setIsEditing(!isEditing)}
              className="flex items-center space-x-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <FiEdit size={16} />
              <span>{isEditing ? 'Cancel' : 'Edit'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Edit Form */}
      {isEditing && (
        <div className="px-6 py-4 bg-blue-50 dark:bg-blue-900 border-b border-blue-200 dark:border-blue-700">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Status
              </label>
              <select
                value={editForm.status}
                onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="OPEN">Open</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="RESOLVED">Resolved</option>
                <option value="IGNORED">Ignored</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Notes
              </label>
              <textarea
                value={editForm.notes}
                onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Add notes about this violation..."
              />
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={handleSave}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Save Changes
              </button>
              <button
                onClick={() => setIsEditing(false)}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-3">
          {violation.status === 'OPEN' && (
            <button
              onClick={handleResolve}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <FiCheckCircle size={16} className="inline mr-2" />
              Resolve
            </button>
          )}
          {violation.status === 'OPEN' && (
            <button
              onClick={handleIgnore}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              <FiEye size={16} className="inline mr-2" />
              Ignore
            </button>
          )}
          <button
            onClick={() => onDelete(violation.id)}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            <FiTrash2 size={16} className="inline mr-2" />
            Delete
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex space-x-8 px-6" aria-label="Tabs">
          <button
            onClick={() => setActiveTab('details')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'details'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Details
          </button>
          <button
            onClick={() => setActiveTab('ml')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'ml'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            ML Analysis
          </button>
          <button
            onClick={() => setActiveTab('remediation')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'remediation'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Remediation
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      <div className="px-6 py-6">
        {activeTab === 'details' && renderDetailsTab()}
        {activeTab === 'ml' && renderMLTab()}
        {activeTab === 'remediation' && renderRemediationTab()}
      </div>
    </div>
  );
};

export default ViolationDetail;
