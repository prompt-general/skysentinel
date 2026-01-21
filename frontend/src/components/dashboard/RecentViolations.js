import React, { useState, useEffect } from 'react';
import { FiAlertTriangle, FiCheckCircle, FiClock, FiFilter, FiExternalLink, FiRefreshCw } from 'react-icons/fi';
import { formatDistanceToNow } from 'date-fns';

const RecentViolations = ({ violations, onRefresh, onFilter }) => {
  const [filteredViolations, setFilteredViolations] = useState([]);
  const [severityFilter, setSeverityFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setFilteredViolations(violations || []);
  }, [violations]);

  useEffect(() => {
    let filtered = violations || [];
    
    if (severityFilter !== 'all') {
      filtered = filtered.filter(v => v.severity === severityFilter);
    }
    
    if (statusFilter !== 'all') {
      filtered = filtered.filter(v => v.status === statusFilter);
    }
    
    setFilteredViolations(filtered);
  }, [violations, severityFilter, statusFilter]);

  const handleRefresh = async () => {
    setLoading(true);
    try {
      await onRefresh();
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'CRITICAL':
        return 'text-red-600 bg-red-100 dark:bg-red-900 dark:text-red-300';
      case 'HIGH':
        return 'text-orange-600 bg-orange-100 dark:bg-orange-900 dark:text-orange-300';
      case 'MEDIUM':
        return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900 dark:text-yellow-300';
      case 'LOW':
        return 'text-blue-600 bg-blue-100 dark:bg-blue-900 dark:text-blue-300';
      default:
        return 'text-gray-600 bg-gray-100 dark:bg-gray-900 dark:text-gray-300';
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
      default:
        return <FiAlertTriangle className="text-gray-500" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'OPEN':
        return 'text-red-600';
      case 'IN_PROGRESS':
        return 'text-yellow-600';
      case 'RESOLVED':
        return 'text-green-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Violations</h3>
        <div className="flex items-center space-x-3">
          {/* Severity Filter */}
          <div className="relative">
            <button
              onClick={() => setSeverityFilter(severityFilter === 'all' ? '' : severityFilter)}
              className="flex items-center space-x-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <FiFilter size={16} />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                {severityFilter === 'all' ? 'All Severities' : severityFilter}
              </span>
            </button>
            
            {/* Dropdown */}
            {severityFilter !== 'all' && (
              <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-10">
                {['all', 'CRITICAL', 'HIGH', 'M3EDIUM', 'LOW'].map((severity) => (
                  <button
                    key={severity}
                    onClick={() => setSeverityFilter(severity === 'all' ? '' : severity)}
                    className={`block w-full text-left px-4 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 ${
                      severityFilter === severity || severityFilter === 'all'
                        ? 'bg-blue-50 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                        : 'text-gray-700 dark:text-gray-300'
                    }`}
                  >
                    {severity === 'all' ? 'All Severities' : severity}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Status Filter */}
          <div className="relative">
            <button
              onClick={() => setStatusFilter(statusFilter === 'all' ? '' : statusFilter)}
              className="flex items-center space-x-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <FiFilter size={16} />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                {statusFilter === 'all' ? 'All Status' : statusFilter}
              </span>
            </button>
            
            {/* Dropdown */}
            {statusFilter !== 'all' && (
              <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-10">
                {['all', 'OPEN', 'IN_PROGRESS', 'RESOLVED', 'IGNORED'].map((status) => (
                  <button
                    key={status}
                    onClick={() => setStatusFilter(status === 'all' ? '' : status)}
                    className={`block w-full text-left px-4 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 ${
                      statusFilter === status || statusFilter === 'all'
                        ? 'bg-blue-50 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                        : 'text-gray-700 dark:text-gray-300'
                    }`}
                  >
                    {status === 'all' ? 'All Status' : status}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Refresh */}
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="flex items-center space-x-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
          >
            <FiRefreshCw className={loading ? 'animate-spin' : ''} size={16} />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              {loading ? 'Refreshing...' : 'Refresh'}
            </span>
          </button>
        </div>
      </div>

      {/* Violations List */}
      <div className="space-y-4">
        {filteredViolations.length === 0 ? (
          <div className="text-center py-12">
            <FiAlertTriangle className="mx-auto text-gray-400 text-4xl mb-4" />
            <p className="text-gray-500 dark:text-gray-400">No violations found</p>
            <p className="text-sm text-gray-400 dark:text-gray-500">
              Try adjusting your filters or check back later.
            </p>
          </div>
        ) : (
          filteredViolations.map((violation) => (
            <div
              key={violation.id}
              className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3 flex-1">
                  <div className={`p-2 rounded-lg ${getSeverityColor(violation.severity)}`}>
                    {getStatusIcon(violation.status)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        {violation.title}
                      </h4>
                      <span className={`text-xs px-2 py-1 rounded-full ${getSeverityColor(violation.severity)}`}>
                        {violation.severity}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      {violation.description}
                    </p>
                    <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                      <span>Resource: {violation.resourceName}</span>
                      <span>•</span>
                      <span>Policy: {violation.policyName}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => window.open(`/violations/${violation.id}`, '_blank')}
                    className="p-2 text-blue-600 hover:text-blue-800 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900 rounded transition-colors"
                  >
                    <FiExternalLink size={16} />
                  </button>
                </div>
              </div>

              {/* Metadata */}
              <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>Detected {formatDistanceToNow(new Date(violation.detectedAt))}</span>
                  <span>•</span>
                  <span>ID: {violation.id}</span>
                </div>
                {violation.resolvedAt && (
                  <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span>Resolved {formatDistanceToNow(new Date(violation.resolvedAt))}</span>
                    <span>•</span>
                    <span>By: {violation.resolvedBy}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))
        )}
      </div>
    </div>
  );
};

export default RecentViolations;
