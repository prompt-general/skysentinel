import React, { useState, useEffect } from 'react';
import { FiActivity, FiCheckCircle, FiAlertTriangle, FiClock, FiGitBranch, FiGitCommit, FiPlay, FiPause, FiStopCircle, FiDownload, FiEye, FiEdit, FiRefreshCw, FiFileText, FiShield, FiDatabase, FiTrendingUp, FiZap, FiAlertCircle } from 'react-icons/fi';
import { formatDistanceToNow } from 'date-fns';

const EvaluationDetail = ({ evaluation, onUpdate, onCancel, onRerun, onExport }) => {
  const [activeTab, setActiveTab] = useState('overview');
  const [isExpanded, setIsExpanded] = useState(false);

  if (!evaluation) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
        <div className="text-center py-12">
          <FiActivity className="mx-auto text-gray-400 text-4xl mb-4" />
          <p className="text-gray-500 dark:text-gray-400">No evaluation selected</p>
        </div>
      </div>
    );
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'COMPLETED':
        return <FiCheckCircle className="text-green-500" />;
      case 'RUNNING':
        return <FiActivity className="text-blue-500" />;
      case 'FAILED':
        return <FiAlertTriangle className="text-red-500" />;
      case 'CANCELLED':
        return <FiStopCircle className="text-gray-500" />;
      case 'PENDING':
        return <FiClock className="text-yellow-500" />;
      default:
        return <FiClock className="text-gray-500" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'COMPLETED':
        return 'bg-green-100 text-green-800';
      case 'RUNNING':
        return 'bg-blue-100 text-blue-800';
      case 'FAILED':
        return 'bg-red-100 text-red-800';
      case 'CANCELLED':
        return 'bg-gray-100 text-gray-800';
      case 'PENDING':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getResultColor = (result) => {
    switch (result) {
      case 'PASS':
        return 'bg-green-100 text-green-800';
      case 'WARN':
        return 'bg-yellow-100 text-yellow-800';
      case 'BLOCK':
        return 'bg-red-100 text-red-800';
      case 'ERROR':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getIacIcon = (iacType) => {
    switch (iacType) {
      case 'TERRAFORM':
        return '🟧';
      case 'CLOUDFORMATION':
        return '🟦';
      case 'ARM':
        return '🟥';
      case 'KUBERNETES':
        return '⚓';
      case 'PULUMI':
        return '🟪';
      case 'CDK':
        return '🟨';
      default:
        return '📄';
    }
  };

  const formatDuration = (duration) => {
    if (duration < 60) {
      return `${duration}s`;
    } else if (duration < 3600) {
      return `${Math.floor(duration / 60)}m ${duration % 60}s`;
    } else {
      return `${Math.floor(duration / 3600)}h ${Math.floor((duration % 3600) / 60)}m`;
    }
  };

  const handleExport = () => {
    const data = {
      evaluation: evaluation,
      exportedAt: new Date().toISOString()
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `evaluation-${evaluation.id}.json`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const renderOverviewTab = () => (
    <div className="space-y-6">
      {/* Basic Information */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Basic Information</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Evaluation ID
            </label>
            <p className="text-sm text-gray-900 dark:text-white">{evaluation.id}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Type
            </label>
            <div className="flex items-center space-x-2">
              <FiActivity className="text-blue-500" />
              <span className="text-sm text-gray-900 dark:text-white">{evaluation.type}</span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Status
            </label>
            <div className="flex items-center space-x-2">
              {getStatusIcon(evaluation.status)}
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(evaluation.status)}`}>
                {evaluation.status}
              </span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Result
            </label>
            {evaluation.result ? (
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getResultColor(evaluation.result)}`}>
                {evaluation.result}
              </span>
            ) : (
              <span className="text-gray-400">N/A</span>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Score
            </label>
            <div className="flex items-center space-x-2">
              <div className="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className="h-2 rounded-full"
                  style={{ 
                    width: `${evaluation.score}%`,
                    backgroundColor: evaluation.score >= 80 ? '#10b981' : evaluation.score >= 60 ? '#3b82f6' : evaluation.score >= 40 ? '#f59e0b' : '#ef4444'
                  }}
                />
              </div>
              <span className="text-sm text-gray-900 dark:text-white">
                {evaluation.score}%
              </span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Confidence
            </label>
            <div className="flex items-center space-x-2">
              <div className="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className="h-2 rounded-full bg-blue-600"
                  style={{ width: `${evaluation.confidence}%` }}
                />
              </div>
              <span className="text-sm text-gray-900 dark:text-white">
                {evaluation.confidence}%
              </span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Duration
            </label>
            <p className="text-sm text-gray-900 dark:text-white">
              {formatDuration(evaluation.duration)}
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Environment
            </label>
            <p className="text-sm text-gray-900 dark:text-white">{evaluation.environment}</p>
          </div>
        </div>
      </div>

      {/* IaC Plan Information */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">IaC Plan</h3>
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center space-x-3">
              <div className="text-2xl">{getIacIcon(evaluation.iacPlan?.type)}</div>
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {evaluation.iacPlan?.type}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {evaluation.iacPlan?.format}
                </p>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Repository
              </label>
              <p className="text-sm text-gray-900 dark:text-white">
                {evaluation.iacPlan?.repository || 'N/A'}
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Branch
              </label>
              <div className="flex items-center space-x-2">
                <FiGitBranch size={14} />
                <p className="text-sm text-gray-900 dark:text-white">
                  {evaluation.iacPlan?.branch || 'main'}
                </p>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Commit
              </label>
              <div className="flex items-center space-x-2">
                <FiGitCommit size={14} />
                <p className="text-sm text-gray-900 dark:text-white font-mono">
                  {evaluation.iacPlan?.commit?.substring(0, 8) || 'N/A'}
                </p>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Resources
              </label>
              <p className="text-sm text-gray-900 dark:text-white">
                {evaluation.iacPlan?.resources || 0}
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Dependencies
              </label>
              <p className="text-sm text-gray-900 dark:text-white">
                {evaluation.iacPlan?.dependencies || 0}
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Size
              </label>
              <p className="text-sm text-gray-900 dark:text-white">
                {evaluation.iacPlan?.size ? `${(evaluation.iacPlan.size / 1024).toFixed(1)} KB` : 'N/A'}
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Path
              </label>
              <p className="text-sm text-gray-900 dark:text-white">
                {evaluation.iacPlan?.path || 'N/A'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Timeline</h3>
        <div className="space-y-3">
          <div className="flex items-center space-x-3">
            <FiClock className="text-yellow-500" />
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">Triggered</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {formatDistanceToNow(new Date(evaluation.triggeredAt), { addSuffix: true })} by {evaluation.triggeredBy}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <FiActivity className="text-blue-500" />
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">Started</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {formatDistanceToNow(new Date(evaluation.timestamp), { addSuffix: true })}
              </p>
            </div>
          </div>
          {evaluation.completedAt && (
            <div className="flex items-center space-x-3">
              <FiCheckCircle className="text-green-500" />
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">Completed</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {formatDistanceToNow(new Date(evaluation.completedAt), { addSuffix: true })}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const renderViolationsTab = () => (
    <div className="space-y-6">
      {evaluation.violations && evaluation.violations.length > 0 ? (
        <>
          {/* Violations Summary */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Violations Summary</h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">
                  {evaluation.violations.filter(v => v.severity === 'CRITICAL').length}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Critical</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {evaluation.violations.filter(v => v.severity === 'HIGH').length}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">High</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {evaluation.violations.filter(v => v.severity === 'MEDIUM').length}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Medium</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {evaluation.violations.filter(v => v.severity === 'LOW').length}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Low</div>
              </div>
            </div>
          </div>

          {/* Violations List */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">All Violations</h3>
            <div className="space-y-3">
              {evaluation.violations.map((violation, index) => (
                <div key={index} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          violation.severity === 'CRITICAL' ? 'bg-red-100 text-red-800' :
                          violation.severity === 'HIGH' ? 'bg-orange-100 text-orange-800' :
                          violation.severity === 'MEDIUM' ? 'bg-blue-100 text-blue-800' :
                          'bg-green-100 text-green-800'
                        }`}>
                          {violation.severity}
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {violation.policy?.name}
                        </span>
                      </div>
                      <p className="text-sm text-gray-900 dark:text-white mb-2">
                        {violation.description}
                      </p>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        Resource: {violation.resource?.name} ({violation.resource?.type})
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
          <FiShield className="mx-auto text-gray-400 text-4xl mb-4" />
          <p className="text-gray-500 dark:text-gray-400">No violations found</p>
        </div>
      )}
    </div>
  );

  const renderMLTab = () => (
    <div className="space-y-6">
      {evaluation.mlPredictions && evaluation.mlPredictions.length > 0 ? (
        <>
          {/* ML Predictions Summary */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">ML Predictions Summary</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {evaluation.mlPredictions.map((prediction, index) => (
                <div key={index} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                      {prediction.modelType}
                    </h4>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      v{prediction.modelVersion}
                    </span>
                  </div>
                  <div className="space-y-2">
                    <div>
                      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                        Violation Probability
                      </label>
                      <div className="flex items-center space-x-2">
                        <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                          <div
                            className="h-2 rounded-full bg-red-600"
                            style={{ width: `${prediction.violationProbability * 100}%` }}
                          />
                        </div>
                        <span className="text-sm text-gray-900 dark:text-white">
                          {Math.round(prediction.violationProbability * 100)}%
                        </span>
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                        Confidence
                      </label>
                      <div className="flex items-center space-x-2">
                        <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                          <div
                            className="h-2 rounded-full bg-blue-600"
                            style={{ width: `${prediction.confidence * 100}%` }}
                          />
                        </div>
                        <span className="text-sm text-gray-900 dark:text-white">
                          {Math.round(prediction.confidence * 100)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ML Explanation */}
          {evaluation.mlPredictions[0]?.explanation && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">ML Explanation</h3>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <pre className="text-sm text-gray-900 dark:text-white whitespace-pre-wrap">
                  {JSON.stringify(evaluation.mlPredictions[0].explanation, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-12">
          <FiZap className="mx-auto text-gray-400 text-4xl mb-4" />
          <p className="text-gray-500 dark:text-gray-400">No ML predictions available</p>
        </div>
      )}
    </div>
  );

  const renderResourcesTab = () => (
    <div className="space-y-6">
      {evaluation.resources && evaluation.resources.length > 0 ? (
        <>
          {/* Resources Summary */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Resources Summary</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {evaluation.resources.length}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Total Resources</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {evaluation.resources.filter(r => r.state === 'running').length}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Running</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {evaluation.resources.filter(r => r.violations && r.violations.length > 0).length}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">With Violations</div>
              </div>
            </div>
          </div>

          {/* Resources List */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">All Resources</h3>
            <div className="space-y-3">
              {evaluation.resources.map((resource, index) => (
                <div key={index} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <FiDatabase className="text-blue-500" />
                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                          {resource.name}
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {resource.type}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {resource.cloud} • {resource.region}
                      </div>
                      {resource.violations && resource.violations.length > 0 && (
                        <div className="mt-2">
                          <span className="text-xs text-red-600 dark:text-red-400">
                            {resource.violations.length} violations
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : (
        <div className="text-center py-12">
          <FiDatabase className="mx-auto text-gray-400 text-4xl mb-4" />
          <p className="text-gray-500 dark:text-gray-400">No resources found</p>
        </div>
      )}
    </div>
  );

  const renderPoliciesTab = () => (
    <div className="space-y-6">
      {evaluation.policies && evaluation.policies.length > 0 ? (
        <>
          {/* Policies Summary */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Policies Summary</h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {evaluation.policies.length}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Total Policies</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {evaluation.policies.filter(p => p.enabled).length}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Enabled</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {evaluation.policies.filter(p => p.mlEnhanced).length}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">ML Enhanced</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {evaluation.policies.filter(p => p.violations && p.violations.length > 0).length}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">With Violations</div>
              </div>
            </div>
          </div>

          {/* Policies List */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">All Policies</h3>
            <div className="space-y-3">
              {evaluation.policies.map((policy, index) => (
                <div key={index} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <FiShield className="text-blue-500" />
                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                          {policy.name}
                        </span>
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          policy.severity === 'CRITICAL' ? 'bg-red-100 text-red-800' :
                          policy.severity === 'HIGH' ? 'bg-orange-100 text-orange-800' :
                          policy.severity === 'MEDIUM' ? 'bg-blue-100 text-blue-800' :
                          'bg-green-100 text-green-800'
                        }`}>
                          {policy.severity}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {policy.category} • {policy.cloudProvider}
                      </div>
                      <div className="flex items-center space-x-2 mt-2">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          policy.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {policy.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                        {policy.mlEnhanced && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                            ML Enhanced
                          </span>
                        )}
                      </div>
                      {policy.violations && policy.violations.length > 0 && (
                        <div className="mt-2">
                          <span className="text-xs text-red-600 dark:text-red-400">
                            {policy.violations.length} violations
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : (
        <div className="text-center py-12">
          <FiShield className="mx-auto text-gray-400 text-4xl mb-4" />
          <p className="text-gray-500 dark:text-gray-400">No policies found</p>
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
            Evaluation Details
          </h2>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleExport}
              className="flex items-center space-x-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <FiDownload size={16} />
              <span>Export</span>
            </button>
            {evaluation.status === 'FAILED' && (
              <button
                onClick={() => onRerun && onRerun(evaluation.id)}
                className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <FiRefreshCw size={16} />
                <span>Rerun</span>
              </button>
            )}
            {evaluation.status === 'RUNNING' && (
              <button
                onClick={() => onCancel && onCancel(evaluation.id)}
                className="flex items-center space-x-2 px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                <FiStopCircle size={16} />
                <span>Cancel</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex space-x-8 px-6" aria-label="Tabs">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'overview'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('violations')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'violations'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Violations ({evaluation.violations?.length || 0})
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
            onClick={() => setActiveTab('resources')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'resources'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Resources ({evaluation.resources?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('policies')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'policies'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Policies ({evaluation.policies?.length || 0})
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      <div className="px-6 py-6">
        {activeTab === 'overview' && renderOverviewTab()}
        {activeTab === 'violations' && renderViolationsTab()}
        {activeTab === 'ml' && renderMLTab()}
        {activeTab === 'resources' && renderResourcesTab()}
        {activeTab === 'policies' && renderPoliciesTab()}
      </div>
    </div>
  );
};

export default EvaluationDetail;
