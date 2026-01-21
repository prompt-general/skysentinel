import React, { useState, useEffect } from 'react';
import { FiShield, FiEdit, FiTrash2, FiPlus, FiFilter, FiChevronDown, FiCheckCircle, FiXCircle, FiAlertTriangle, FiDollarSign, FiSettings } from 'react-icons/fi';

const PolicyList = ({ policies, onEdit, onDelete, onCreate }) => {
  const [filteredPolicies, setFilteredPolicies] = useState([]);
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('name');
  const [sortOrder, setSortOrder] = useState('asc');

  useEffect(() => {
    let filtered = policies || [];

    // Apply search filter
    if (searchQuery) {
      filtered = filtered.filter(policy =>
        policy.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        policy.description.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Apply category filter
    if (categoryFilter !== 'all') {
      filtered = filtered.filter(policy => policy.category === categoryFilter);
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(policy => policy.enabled === (statusFilter === 'enabled'));
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let comparison = 0;
      switch (sortBy) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'category':
          comparison = a.category.localeCompare(b.category);
          break;
        case 'severity':
          const severityOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
          comparison = severityOrder[a.severity] - severityOrder[b.severity];
          break;
        case 'updated_at':
          comparison = new Date(b.updatedAt) - new Date(a.updatedAt);
          break;
        default:
          comparison = 0;
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });

    setFilteredPolicies(filtered);
  }, [policies, searchQuery, categoryFilter, statusFilter, sortBy, sortOrder]);

  const getStatusIcon = (enabled) => {
    return enabled ? <FiCheckCircle className="text-green-500" /> : <FiXCircle className="text-gray-400" />;
  };

  const getStatusColor = (enabled) => {
    return enabled ? 'text-green-600' : 'text-gray-400';
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'CRITICAL':
        return 'text-red-600';
      case 'HIGH':
        return 'text-orange-600';
      case 'MEDIUM':
        return 'text-yellow-600';
      case 'LOW':
        return 'text-blue-600';
      default:
        return 'text-gray-600';
    }
  };

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'SECURITY':
        return <FiShield className="text-blue-600" />;
      case 'COMPLIANCE':
        return <FiCheckCircle className="text-green-600" />;
      case 'COST':
        return <FiDollarSign className="text-purple-600" />;
      default:
        return <FiSettings className="text-gray-600" />;
    }
  };

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    }
    setSortBy(field);
  };

  const handleDelete = async (policyId) => {
    if (window.confirm('Are you sure you want to delete this policy? This action cannot be undone.')) {
      await onDelete(policyId);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Policies</h2>
          <button
            onClick={onCreate}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <FiPlus size={16} />
            <span>Create Policy</span>
          </button>
        </div>

        {/* Filters */}
        <div className="px-6 pb-4 flex flex-wrap gap-4">
          {/* Search */}
          <div className="flex-1 min-w-64">
            <div className="relative">
              <input
                type="text"
                placeholder="Search policies..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <FiFilter className="text-gray-400" size={20} />
              </div>
            </div>
          </div>

          {/* Category Filter */}
          <div className="relative">
            <button
              onClick={() => setCategoryFilter(categoryFilter === 'all' ? '' : categoryFilter)}
              className="flex items-center space-x-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              {getCategoryIcon(categoryFilter === 'all' ? 'SECURITY' : categoryFilter)}
              <span className="text-sm text-gray-700 dark:text-gray-300">
                {categoryFilter === 'all' ? 'All Categories' : categoryFilter}
              </span>
              <FiChevronDown size={16} className="text-gray-400" />
            </button>

            {categoryFilter !== 'all' && (
              <div className="absolute top-full left-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-10">
              {['all', 'SECURITY', 'COMPLIANCE', 'COST', 'OPERATIONS', 'GOVERNANCE'].map((category) => (
                <button
                  key={category}
                  onClick={() => setCategoryFilter(category === 'all' ? '' : category)}
                  className={`block w-full text-left px-4 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 ${
                    categoryFilter === category || categoryFilter === 'all'
                      ? 'bg-blue-50 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                      : 'text-gray-700 dark:text-gray-300'
                  }`}
                >
                  {category === 'all' ? 'All Categories' : category}
                </button>
              ))}
            </div>
            )}
          </div>

          {/* Status Filter */}
          <div className="relative">
            <button
              onClick={() => setStatusFilter(statusFilter === 'all' ? '' : statusFilter)}
              className="flex items-center space-x-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              {getStatusIcon(statusFilter === 'all' ? 'enabled' : statusFilter)}
              <span className="text-sm text-gray-700 dark:text-gray-300">
                {statusFilter === 'all' ? 'All Status' : statusFilter}
              </span>
              <FiChevronDown size={16} className="text-gray-400" />
            </button>

            {statusFilter !== 'all' && (
              <div className="absolute top-full left-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-10">
              {['all', 'enabled', 'disabled'].map((status) => (
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

          {/* Sort */}
          <div className="relative">
            <button
              onClick={() => handleSort('name')}
              className="flex items-center space-x-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Sort by {sortBy}
              </span>
              <FiChevronDown size={16} className="text-gray-400" />
            </button>

            {sortBy !== 'name' && (
              <div className="absolute top-full left-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-10">
              {['name', 'category', 'severity', 'updated_at'].map((field) => (
                <button
                  key={field}
                  onClick={() => handleSort(field)}
                  className={`block w-full text-left px-4 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 ${
                    sortBy === field
                      ? 'bg-blue-50 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                      : 'text-gray-700 dark:text-gray-300'
                  }`}
                >
                  {field}
                </button>
              ))}
            </div>
            )}
          </div>
        </div>
      </div>

      {/* Policies List */}
      <div className="px-6">
        {filteredPolicies.length === 0 ? (
          <div className="text-center py-12">
            <FiShield className="mx-auto text-gray-400 text-4xl mb-4" />
            <p className="text-gray-500 dark:text-gray-400">No policies found</p>
            <p className="text-sm text-gray-400 dark:text-gray-500">
              Create your first policy to get started.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredPolicies.map((policy) => (
              <div
                key={policy.id}
                className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4 flex-1">
                    <div className={`p-2 rounded-lg ${getCategoryColor(policy.category)}`}>
                      {getCategoryIcon(policy.category)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium text-gray-900 dark:text-white">
                          {policy.name}
                        </h4>
                        <div className="flex items-center space-x-2">
                          <span className={`text-xs px-2 py-1 rounded-full ${getSeverityColor(policy.severity)}`}>
                            {policy.severity}
                          </span>
                          <span className={`text-xs px-2 py-1 rounded-full ${getStatusColor(policy.enabled)}`}>
                            {policy.enabled ? 'Enabled' : 'Disabled'}
                          </span>
                        </div>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                        {policy.description}
                      </p>
                      <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                        <span>Category: {policy.category}</span>
                        <span>•</span>
                        <span>Cloud: {policy.cloudProvider}</span>
                        <span>•</span>
                        <span>Type: {policy.resourceType}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => onEdit(policy.id)}
                      className="p-2 text-blue-600 hover:text-blue-800 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900 rounded transition-colors"
                    >
                      <FiEdit size={16} />
                    </button>
                    <button
                      onClick={() => handleDelete(policy.id)}
                      className="p-2 text-red-600 hover:text-red-800 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900 rounded transition-colors"
                    >
                      <FiTrash2 size={16} />
                    </button>
                  </div>
                </div>

                {/* Metadata */}
                <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span>Created: {new Date(policy.createdAt).toLocaleDateString()}</span>
                    <span>•</span>
                    <span>Updated: {new Date(policy.updatedAt).toLocaleDateString()}</span>
                    <span>•</span>
                    <span>By: {policy.createdBy}</span>
                  </div>
                  
                  <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500 dark:text-gray-400">
                    <span>ML Enhanced: {policy.mlEnhanced ? 'Yes' : 'No'}</span>
                    {policy.mlEnhanced && (
                      <>
                        <span>•</span>
                        <span>Threshold: {policy.mlThreshold}</span>
                        <span>•</span>
                        <span>Weight: {policy.mlWeight}</span>
                      </>
                    )}
                  </div>

                  {/* Tags */}
                  {policy.tags && policy.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {policy.tags.map((tag) => (
                        <span
                          key={tag}
                          className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs rounded-full"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PolicyList;
