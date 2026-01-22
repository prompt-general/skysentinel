import React, { useState, useEffect } from 'react';
import { FiAlertTriangle, FiFilter, FiSearch, FiRefreshCw } from 'react-icons/fi';
import { useQuery, useSubscription } from '@apollo/client';
import { VIOLATIONS_QUERY, VIOLATION_CREATED_SUBSCRIPTION, VIOLATION_UPDATED_SUBSCRIPTION } from '../services/queries';
import ViolationList from '../components/violations/ViolationList';
import ViolationDetail from '../components/violations/ViolationDetail';

const Violations = ({ mode = 'list', violationId }) => {
  const [viewMode, setViewMode] = useState(mode);
  const [selectedViolationId, setSelectedViolationId] = useState(violationId);
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState({
    severity: 'all',
    status: 'all',
    cloud: 'all',
    resolved: 'all',
    timeframe: '30d'
  });

  const { data, loading, error, refetch } = useQuery(VIOLATIONS_QUERY, {
    variables: {
      filter: {
        search: searchQuery,
        severity: filters.severity === 'all' ? undefined : filters.severity,
        status: filters.status === 'all' ? undefined : filters.status,
        cloud: filters.cloud === 'all' ? undefined : filters.cloud,
        resolved: filters.resolved === 'all' ? undefined : filters.resolved === 'true',
        timeframe: filters.timeframe
      },
      tenantId: 'default-tenant'
    },
    pollInterval: 30000,
    errorPolicy: 'all'
  });

  useSubscription(VIOLATION_CREATED_SUBSCRIPTION, {
    variables: { tenantId: 'default-tenant' },
    onSubscriptionData: () => refetch()
  });

  useSubscription(VIOLATION_UPDATED_SUBSCRIPTION, {
    variables: { tenantId: 'default-tenant' },
    onSubscriptionData: () => refetch()
  });

  const handleViolationSelect = (violationId) => {
    setSelectedViolationId(violationId);
    setViewMode('detail');
  };

  const handleViolationEdit = (violationId) => {
    setSelectedViolationId(violationId);
    setViewMode('edit');
  };

  const handleViolationDelete = (violationId) => {
    console.log('Delete violation:', violationId);
  };

  const handleViolationUpdate = (violationId, updates) => {
    console.log('Update violation:', violationId, updates);
    refetch();
  };

  const handleViolationResolve = (violationId, resolution) => {
    console.log('Resolve violation:', violationId, resolution);
    refetch();
  };

  const handleViolationIgnore = (violationId, reason) => {
    console.log('Ignore violation:', violationId, reason);
    refetch();
  };

  const handleFilterChange = (newFilters) => {
    setFilters({ ...filters, ...newFilters });
  };

  const handleSearch = (query) => {
    setSearchQuery(query);
  };

  const handleRefresh = () => {
    refetch();
  };

  const selectedViolation = data?.violations?.find(v => v.id === selectedViolationId);

  if (viewMode === 'detail' && selectedViolation) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Violation Details
          </h1>
          <button
            onClick={() => setViewMode('list')}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            Back to List
          </button>
        </div>
        <ViolationDetail
          violation={selectedViolation}
          onUpdate={handleViolationUpdate}
          onResolve={handleViolationResolve}
          onIgnore={handleViolationIgnore}
          onDelete={handleViolationDelete}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Security Violations
        </h1>
        <button
          onClick={handleRefresh}
          className="flex items-center space-x-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          <FiRefreshCw size={16} />
          Refresh
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="relative">
            <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="Search violations..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <select
            value={filters.severity}
            onChange={(e) => handleFilterChange({ severity: e.target.value })}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          <select
            value={filters.status}
            onChange={(e) => handleFilterChange({ status: e.target.value })}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Statuses</option>
            <option value="OPEN">Open</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="RESOLVED">Resolved</option>
            <option value="IGNORED">Ignored</option>
          </select>

          <select
            value={filters.cloud}
            onChange={(e) => handleFilterChange({ cloud: e.target.value })}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Clouds</option>
            <option value="AWS">AWS</option>
            <option value="AZURE">Azure</option>
            <option value="GCP">GCP</option>
            <option value="KUBERNETES">Kubernetes</option>
          </select>

          <select
            value={filters.resolved}
            onChange={(e) => handleFilterChange({ resolved: e.target.value })}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Violations</option>
            <option value="true">Resolved</option>
            <option value="false">Unresolved</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-12">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </div>
      ) : error ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-12">
          <div className="text-center">
            <FiAlertTriangle className="mx-auto text-gray-400 text-4xl mb-4" />
            <p className="text-gray-500 dark:text-gray-400">Error loading violations</p>
            <button
              onClick={handleRefresh}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      ) : (
        <ViolationList
          violations={data?.violations || []}
          onView={handleViolationSelect}
          onEdit={handleViolationEdit}
          onDelete={handleViolationDelete}
          onFilter={handleFilterChange}
          onRefresh={handleRefresh}
        />
      )}
    </div>
  );
};

export default Violations;
