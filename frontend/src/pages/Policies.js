import React, { useState, useEffect } from 'react';
import { FiShield, FiPlus, FiFilter, FiSearch, FiRefreshCw } from 'react-icons/fi';
import { useQuery, useSubscription } from '@apollo/client';
import { POLICIES_QUERY, POLICY_CREATED_SUBSCRIPTION, POLICY_UPDATED_SUBSCRIPTION } from '../services/queries';
import PolicyList from '../components/policies/PolicyList';
import PolicyForm from '../components/policies/PolicyForm';
import PolicyEditor from '../components/policies/PolicyEditor';

const Policies = ({ mode = 'list', policyId }) => {
  const [viewMode, setViewMode] = useState(mode);
  const [selectedPolicyId, setSelectedPolicyId] = useState(policyId);
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState({
    category: 'all',
    severity: 'all',
    cloudProvider: 'all',
    enabled: 'all',
    mlEnhanced: 'all'
  });

  // Query policies
  const { data, loading, error, refetch } = useQuery(POLICIES_QUERY, {
    variables: {
      filter: {
        search: searchQuery,
        category: filters.category === 'all' ? undefined : filters.category,
        severity: filters.severity === 'all' ? undefined : filters.severity,
        cloudProvider: filters.cloudProvider === 'all' ? undefined : filters.cloudProvider,
        enabled: filters.enabled === 'all' ? undefined : filters.enabled === 'true',
        mlEnhanced: filters.mlEnhanced === 'all' ? undefined : filters.mlEnhanced === 'true'
      },
      tenantId: 'default-tenant'
    },
    pollInterval: 30000,
    errorPolicy: 'all'
  });

  // Subscriptions for real-time updates
  useSubscription(POLICY_CREATED_SUBSCRIPTION, {
    variables: { tenantId: 'default-tenant' },
    onSubscriptionData: () => {
      refetch();
    }
  });

  useSubscription(POLICY_UPDATED_SUBSCRIPTION, {
    variables: { tenantId: 'default-tenant' },
    onSubscriptionData: () => {
      refetch();
    }
  });

  const handlePolicySelect = (policyId) => {
    setSelectedPolicyId(policyId);
    setViewMode('view');
  };

  const handlePolicyEdit = (policyId) => {
    setSelectedPolicyId(policyId);
    setViewMode('edit');
  };

  const handlePolicyCreate = () => {
    setSelectedPolicyId(null);
    setViewMode('create');
  };

  const handlePolicyDelete = (policyId) => {
    // Handle policy deletion
    console.log('Delete policy:', policyId);
  };

  const handlePolicySave = (policyData) => {
    // Handle policy save
    console.log('Save policy:', policyData);
    setViewMode('list');
    refetch();
  };

  const handlePolicyCancel = () => {
    setViewMode('list');
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

  const selectedPolicy = data?.policies?.find(p => p.id === selectedPolicyId);

  // Render different views based on mode
  if (viewMode === 'create') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Create Policy
          </h1>
          <button
            onClick={handlePolicyCancel}
            className="flex items-center space-x-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            Cancel
          </button>
        </div>
        <PolicyForm
          onSave={handlePolicySave}
          onCancel={handlePolicyCancel}
        />
      </div>
    );
  }

  if (viewMode === 'edit' && selectedPolicy) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Edit Policy: {selectedPolicy.name}
          </h1>
          <button
            onClick={handlePolicyCancel}
            className="flex items-center space-x-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            Cancel
          </button>
        </div>
        <PolicyForm
          policy={selectedPolicy}
          onSave={handlePolicySave}
          onCancel={handlePolicyCancel}
        />
      </div>
    );
  }

  if (viewMode === 'view' && selectedPolicy) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Policy: {selectedPolicy.name}
          </h1>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => handlePolicyEdit(selectedPolicy.id)}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Edit
            </button>
            <button
              onClick={handlePolicyCancel}
              className="flex items-center space-x-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Back
            </button>
          </div>
        </div>
        <PolicyEditor
          policy={selectedPolicy}
          onSave={handlePolicySave}
          onCancel={handlePolicyCancel}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Security Policies
        </h1>
        <button
          onClick={handlePolicyCreate}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <FiPlus size={16} />
          Create Policy
        </button>
      </div>

      {/* Search and Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
        <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
          {/* Search */}
          <div className="relative">
            <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="Search policies..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Category Filter */}
          <select
            value={filters.category}
            onChange={(e) => handleFilterChange({ category: e.target.value })}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Categories</option>
            <option value="SECURITY">Security</option>
            <option value="COMPLIANCE">Compliance</option>
            <option value="COST">Cost</option>
            <option value="OPERATIONS">Operations</option>
            <option value="GOVERNANCE">Governance</option>
          </select>

          {/* Severity Filter */}
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

          {/* Cloud Provider Filter */}
          <select
            value={filters.cloudProvider}
            onChange={(e) => handleFilterChange({ cloudProvider: e.target.value })}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Clouds</option>
            <option value="AWS">AWS</option>
            <option value="AZURE">Azure</option>
            <option value="GCP">GCP</option>
            <option value="KUBERNETES">Kubernetes</option>
          </select>

          {/* Enabled Filter */}
          <select
            value={filters.enabled}
            onChange={(e) => handleFilterChange({ enabled: e.target.value })}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Status</option>
            <option value="true">Enabled</option>
            <option value="false">Disabled</option>
          </select>

          {/* ML Enhanced Filter */}
          <select
            value={filters.mlEnhanced}
            onChange={(e) => handleFilterChange({ mlEnhanced: e.target.value })}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Policies</option>
            <option value="true">ML Enhanced</option>
            <option value="false">Traditional</option>
          </select>
        </div>
      </div>

      {/* Policies List */}
      {loading ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-12">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </div>
      ) : error ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-12">
          <div className="text-center">
            <FiShield className="mx-auto text-gray-400 text-4xl mb-4" />
            <p className="text-gray-500 dark:text-gray-400">Error loading policies</p>
            <button
              onClick={handleRefresh}
              className="mt-4 flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <FiRefreshCw size={16} />
              Retry
            </button>
          </div>
        </div>
      ) : (
        <PolicyList
          policies={data?.policies || []}
          onEdit={handlePolicyEdit}
          onDelete={handlePolicyDelete}
          onCreate={handlePolicyCreate}
          onFilter={handleFilterChange}
        />
      )}
    </div>
  );
};

export default Policies;
