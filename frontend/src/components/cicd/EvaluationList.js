import React, { useState, useEffect } from 'react';
import { FiActivity, FiCheckCircle, FiAlertTriangle, FiClock, FiFilter, FiRefreshCw, FiSearch, FiDownload, FiEye, FiGitBranch, FiGitCommit, FiPlay, FiPause, FiStopCircle, FiTrendingUp, FiTrendingDown } from 'react-icons/fi';
import { formatDistanceToNow } from 'date-fns';

const EvaluationList = ({ evaluations, onFilter, onRefresh, onView, onExport }) => {
  const [filteredEvaluations, setFilteredEvaluations] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [resultFilter, setResultFilter] = useState('all');
  const [environmentFilter, setEnvironmentFilter] = useState('all');
  const [sortBy, setSortBy] = useState('timestamp');
  const [sortOrder, setSortOrder] = useState('desc');
  const [selectedEvaluations, setSelectedEvaluations] = useState([]);

  useEffect(() => {
    filterEvaluations();
  }, [evaluations, searchQuery, typeFilter, statusFilter, resultFilter, environmentFilter, sortBy, sortOrder]);

  const filterEvaluations = () => {
    let filtered = evaluations || [];

    // Apply search filter
    if (searchQuery) {
      filtered = filtered.filter(evaluation =>
        evaluation.iacPlan?.repository?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        evaluation.iacPlan?.branch?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        evaluation.iacPlan?.commit?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        evaluation.environment?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        evaluation.triggeredBy?.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Apply type filter
    if (typeFilter !== 'all') {
      filtered = filtered.filter(evaluation => evaluation.type === typeFilter);
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(evaluation => evaluation.status === statusFilter);
    }

    // Apply result filter
    if (resultFilter !== 'all') {
      filtered = filtered.filter(evaluation => evaluation.result === resultFilter);
    }

    // Apply environment filter
    if (environmentFilter !== 'all') {
      filtered = filtered.filter(evaluation => evaluation.environment === environmentFilter);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aValue = a[sortBy];
      let bValue = b[sortBy];

      if (sortBy === 'timestamp' || sortBy === 'triggeredAt' || sortBy === 'completedAt') {
        aValue = new Date(aValue);
        bValue = new Date(bValue);
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    setFilteredEvaluations(filtered);
  };

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

  const getTypeIcon = (type) => {
    switch (type) {
      case 'CI_CD':
        return <FiGitBranch className="text-blue-500" />;
      case 'RUNTIME':
        return <FiActivity className="text-green-500" />;
      case 'MANUAL':
        return <FiCheckCircle className="text-purple-500" />;
      case 'SCHEDULED':
        return <FiClock className="text-orange-500" />;
      default:
        return <FiActivity className="text-gray-500" />;
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

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const handleSelectEvaluation = (evaluationId) => {
    setSelectedEvaluations(prev =>
      prev.includes(evaluationId)
        ? prev.filter(id => id !== evaluationId)
        : [...prev, evaluationId]
    );
  };

  const handleSelectAll = () => {
    if (selectedEvaluations.length === filteredEvaluations.length) {
      setSelectedEvaluations([]);
    } else {
      setSelectedEvaluations(filteredEvaluations.map(e => e.id));
    }
  };

  const handleBulkAction = (action) => {
    onFilter({ action, evaluations: selectedEvaluations });
    setSelectedEvaluations([]);
  };

  const exportEvaluations = () => {
    const data = {
      evaluations: filteredEvaluations,
      exportedAt: new Date().toISOString(),
      filters: {
        searchQuery,
        typeFilter,
        statusFilter,
        resultFilter,
        environmentFilter
      }
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'evaluations.json';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const getUniqueTypes = () => {
    const types = new Set();
    filteredEvaluations.forEach(evaluation => types.add(evaluation.type));
    return Array.from(types);
  };

  const getUniqueStatuses = () => {
    const statuses = new Set();
    filteredEvaluations.forEach(evaluation => statuses.add(evaluation.status));
    return Array.from(statuses);
  };

  const getUniqueResults = () => {
    const results = new Set();
    filteredEvaluations.forEach(evaluation => results.add(evaluation.result));
    return Array.from(results);
  };

  const getUniqueEnvironments = () => {
    const environments = new Set();
    filteredEvaluations.forEach(evaluation => environments.add(evaluation.environment));
    return Array.from(environments);
  };

  const getEvaluationStats = () => {
    const stats = {
      total: filteredEvaluations.length,
      byStatus: {},
      byResult: {},
      byType: {},
      avgScore: 0,
      avgDuration: 0,
      successRate: 0
    };

    filteredEvaluations.forEach(evaluation => {
      // By status
      stats.byStatus[evaluation.status] = (stats.byStatus[evaluation.status] || 0) + 1;
      
      // By result
      if (evaluation.result) {
        stats.byResult[evaluation.result] = (stats.byResult[evaluation.result] || 0) + 1;
      }
      
      // By type
      stats.byType[evaluation.type] = (stats.byType[evaluation.type] || 0) + 1;
      
      // Average score
      if (evaluation.score !== undefined) {
        stats.avgScore += evaluation.score;
      }
      
      // Average duration
      if (evaluation.duration !== undefined) {
        stats.avgDuration += evaluation.duration;
      }
    });

    if (filteredEvaluations.length > 0) {
      stats.avgScore = stats.avgScore / filteredEvaluations.length;
      stats.avgDuration = stats.avgDuration / filteredEvaluations.length;
      
      // Success rate (PASS + WARN)
      const successful = (stats.byResult.PASS || 0) + (stats.byResult.WARN || 0);
      stats.successRate = (successful / filteredEvaluations.length) * 100;
    }

    return stats;
  };

  const stats = getEvaluationStats();

  const formatDuration = (duration) => {
    if (duration < 60) {
      return `${duration}s`;
    } else if (duration < 3600) {
      return `${Math.floor(duration / 60)}m ${duration % 60}s`;
    } else {
      return `${Math.floor(duration / 3600)}h ${Math.floor((duration % 3600) / 60)}m`;
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Evaluations ({filteredEvaluations.length})
          </h2>
          <div className="flex items-center space-x-3">
            <button
              onClick={exportEvaluations}
              className="flex items-center space-x-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <FiDownload size={16} />
              <span>Export</span>
            </button>
            <button
              onClick={onRefresh}
              className="flex items-center space-x-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <FiRefreshCw size={16} />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{stats.total}</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Total Evaluations</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{stats.byStatus.COMPLETED || 0}</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Completed</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{stats.byStatus.RUNNING || 0}</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Running</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">{Math.round(stats.successRate)}%</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Success Rate</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">{formatDuration(stats.avgDuration)}</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Avg Duration</div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {/* Search */}
          <div className="relative">
            <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search evaluations..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Type Filter */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Types</option>
            {getUniqueTypes().map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Statuses</option>
            {getUniqueStatuses().map(status => (
              <option key={status} value={status}>{status}</option>
            ))}
          </select>

          {/* Result Filter */}
          <select
            value={resultFilter}
            onChange={(e) => setResultFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Results</option>
            {getUniqueResults().map(result => (
              <option key={result} value={result}>{result}</option>
            ))}
          </select>

          {/* Environment Filter */}
          <select
            value={environmentFilter}
            onChange={(e) => setEnvironmentFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Environments</option>
            {getUniqueEnvironments().map(environment => (
              <option key={environment} value={environment}>{environment}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedEvaluations.length > 0 && (
        <div className="px-6 py-3 bg-blue-50 dark:bg-blue-900 border-b border-blue-200 dark:border-blue-700">
          <div className="flex items-center justify-between">
            <span className="text-sm text-blue-800 dark:text-blue-200">
              {selectedEvaluations.length} evaluations selected
            </span>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleBulkAction('cancel')}
                className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 transition-colors text-sm"
              >
                Cancel
              </button>
              <button
                onClick={() => handleBulkAction('rerun')}
                className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm"
              >
                Rerun
              </button>
              <button
                onClick={() => handleBulkAction('export')}
                className="px-3 py-1 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors text-sm"
              >
                Export
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Evaluations Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left">
                <input
                  type="checkbox"
                  checked={selectedEvaluations.length === filteredEvaluations.length}
                  onChange={handleSelectAll}
                  className="rounded border-gray-300 dark:border-gray-600"
                />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Evaluation
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Result
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Score
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Duration
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('timestamp')}
                  className="flex items-center space-x-1 hover:text-gray-700 dark:hover:text-gray-300"
                >
                  <span>Time</span>
                </button>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {filteredEvaluations.map((evaluation) => (
              <tr key={evaluation.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                <td className="px-6 py-4">
                  <input
                    type="checkbox"
                    checked={selectedEvaluations.includes(evaluation.id)}
                    onChange={() => handleSelectEvaluation(evaluation.id)}
                    className="rounded border-gray-300 dark:border-gray-600"
                  />
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center space-x-3">
                    <div className="text-2xl">{getIacIcon(evaluation.iacPlan?.type)}</div>
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {evaluation.iacPlan?.repository || 'Unknown'}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        <div className="flex items-center space-x-2">
                          <FiGitBranch size={10} />
                          <span>{evaluation.iacPlan?.branch || 'main'}</span>
                          <FiGitCommit size={10} />
                          <span>{evaluation.iacPlan?.commit?.substring(0, 8) || 'N/A'}</span>
                        </div>
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {evaluation.environment} • {evaluation.triggeredBy}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center space-x-2">
                    {getTypeIcon(evaluation.type)}
                    <span className="text-sm text-gray-900 dark:text-white">
                      {evaluation.type}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center space-x-2">
                    {getStatusIcon(evaluation.status)}
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(evaluation.status)}`}>
                      {evaluation.status}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  {evaluation.result ? (
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getResultColor(evaluation.result)}`}>
                      {evaluation.result}
                    </span>
                  ) : (
                    <span className="text-gray-400">N/A</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  {evaluation.score !== undefined ? (
                    <div className="flex items-center space-x-2">
                      <div className="w-16 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
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
                  ) : (
                    <span className="text-gray-400">N/A</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-900 dark:text-white">
                    {evaluation.duration !== undefined ? formatDuration(evaluation.duration) : 'N/A'}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-900 dark:text-white">
                    <div>{formatDistanceToNow(new Date(evaluation.timestamp), { addSuffix: true })}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {new Date(evaluation.timestamp).toLocaleDateString()}
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => onView(evaluation.id)}
                      className="text-blue-600 hover:text-blue-800 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900 rounded p-1"
                    >
                      <FiEye size={16} />
                    </button>
                    {evaluation.status === 'RUNNING' && (
                      <button
                        className="text-red-600 hover:text-red-800 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900 rounded p-1"
                      >
                        <FiPause size={16} />
                      </button>
                    )}
                    {evaluation.status === 'FAILED' && (
                      <button
                        className="text-green-600 hover:text-green-800 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900 rounded p-1"
                      >
                        <FiPlay size={16} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Empty State */}
      {filteredEvaluations.length === 0 && (
        <div className="text-center py-12">
          <FiActivity className="mx-auto text-gray-400 text-4xl mb-4" />
          <p className="text-gray-500 dark:text-gray-400">No evaluations found</p>
          <p className="text-sm text-gray-400 dark:text-gray-500">
            Try adjusting your filters or search criteria
          </p>
        </div>
      )}
    </div>
  );
};

export default EvaluationList;
