import React, { useState, useEffect } from 'react';
import { FiAlertTriangle, FiCheckCircle, FiClock, FiFilter, FiExternalLink, FiRefreshCw, FiSearch, FiDownload, FiEye, FiEdit, FiTrash2 } from 'react-icons/fi';
import { formatDistanceToNow } from 'date-fns';

const ViolationList = ({ violations, onFilter, onRefresh, onView, onEdit, onDelete }) => {
  const [filteredViolations, setFilteredViolations] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [cloudFilter, setCloudFilter] = useState('all');
  const [sortBy, setSortBy] = useState('timestamp');
  const [sortOrder, setSortOrder] = useState('desc');
  const [selectedViolations, setSelectedViolations] = useState([]);

  useEffect(() => {
    filterViolations();
  }, [violations, searchQuery, severityFilter, statusFilter, cloudFilter, sortBy, sortOrder]);

  const filterViolations = () => {
    let filtered = violations || [];

    // Apply search filter
    if (searchQuery) {
      filtered = filtered.filter(violation =>
        violation.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        violation.resource.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        violation.policy.name.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Apply severity filter
    if (severityFilter !== 'all') {
      filtered = filtered.filter(violation => violation.severity === severityFilter);
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(violation => violation.status === statusFilter);
    }

    // Apply cloud filter
    if (cloudFilter !== 'all') {
      filtered = filtered.filter(violation => violation.resource.cloud === cloudFilter);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aValue = a[sortBy];
      let bValue = b[sortBy];

      if (sortBy === 'timestamp') {
        aValue = new Date(aValue);
        bValue = new Date(bValue);
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    setFilteredViolations(filtered);
  };

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

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const handleSelectViolation = (violationId) => {
    setSelectedViolations(prev =>
      prev.includes(violationId)
        ? prev.filter(id => id !== violationId)
        : [...prev, violationId]
    );
  };

  const handleSelectAll = () => {
    if (selectedViolations.length === filteredViolations.length) {
      setSelectedViolations([]);
    } else {
      setSelectedViolations(filteredViolations.map(v => v.id));
    }
  };

  const handleBulkAction = (action) => {
    // Handle bulk actions (resolve, ignore, delete)
    onFilter({ action, violations: selectedViolations });
    setSelectedViolations([]);
  };

  const exportViolations = () => {
    const csv = [
      ['ID', 'Policy', 'Resource', 'Severity', 'Status', 'Description', 'Timestamp'],
      ...filteredViolations.map(v => [
        v.id,
        v.policy.name,
        v.resource.name,
        v.severity,
        v.status,
        v.description,
        v.timestamp
      ])
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'violations.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Violations ({filteredViolations.length})
          </h2>
          <div className="flex items-center space-x-3">
            <button
              onClick={exportViolations}
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

      {/* Filters */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search */}
          <div className="relative">
            <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search violations..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Severity Filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Statuses</option>
            <option value="OPEN">Open</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="RESOLVED">Resolved</option>
            <option value="IGNORED">Ignored</option>
          </select>

          {/* Cloud Filter */}
          <select
            value={cloudFilter}
            onChange={(e) => setCloudFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Clouds</option>
            <option value="AWS">AWS</option>
            <option value="AZURE">Azure</option>
            <option value="GCP">GCP</option>
            <option value="KUBERNETES">Kubernetes</option>
          </select>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedViolations.length > 0 && (
        <div className="px-6 py-3 bg-blue-50 dark:bg-blue-900 border-b border-blue-200 dark:border-blue-700">
          <div className="flex items-center justify-between">
            <span className="text-sm text-blue-800 dark:text-blue-200">
              {selectedViolations.length} violations selected
            </span>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleBulkAction('resolve')}
                className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 transition-colors text-sm"
              >
                Resolve
              </button>
              <button
                onClick={() => handleBulkAction('ignore')}
                className="px-3 py-1 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors text-sm"
              >
                Ignore
              </button>
              <button
                onClick={() => handleBulkAction('delete')}
                className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 transition-colors text-sm"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Violations Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left">
                <input
                  type="checkbox"
                  checked={selectedViolations.length === filteredViolations.length}
                  onChange={handleSelectAll}
                  className="rounded border-gray-300 dark:border-gray-600"
                />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('severity')}
                  className="flex items-center space-x-1 hover:text-gray-700 dark:hover:text-gray-300"
                >
                  <span>Severity</span>
                </button>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Policy
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Resource
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Description
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('status')}
                  className="flex items-center space-x-1 hover:text-gray-700 dark:hover:text-gray-300"
                >
                  <span>Status</span>
                </button>
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
            {filteredViolations.map((violation) => (
              <tr key={violation.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                <td className="px-6 py-4">
                  <input
                    type="checkbox"
                    checked={selectedViolations.includes(violation.id)}
                    onChange={() => handleSelectViolation(violation.id)}
                    className="rounded border-gray-300 dark:border-gray-600"
                  />
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${getSeverityColor(violation.severity)}`}>
                    {violation.severity}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-900 dark:text-white">
                    {violation.policy.name}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {violation.policy.category}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-900 dark:text-white">
                    {violation.resource.name}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {violation.resource.type} • {violation.resource.cloud}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-900 dark:text-white max-w-xs truncate">
                    {violation.description}
                  </div>
                  {violation.mlPrediction && (
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      ML: {Math.round(violation.mlPrediction.confidence * 100)}% confidence
                    </div>
                  )}
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center space-x-2">
                    {getStatusIcon(violation.status)}
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(violation.status)}`}>
                      {violation.status}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-900 dark:text-white">
                    {formatDistanceToNow(new Date(violation.timestamp), { addSuffix: true })}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => onView(violation.id)}
                      className="text-blue-600 hover:text-blue-800 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900 rounded p-1"
                    >
                      <FiEye size={16} />
                    </button>
                    <button
                      onClick={() => onEdit(violation.id)}
                      className="text-green-600 hover:text-green-800 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900 rounded p-1"
                    >
                      <FiEdit size={16} />
                    </button>
                    <button
                      onClick={() => onDelete(violation.id)}
                      className="text-red-600 hover:text-red-800 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900 rounded p-1"
                    >
                      <FiTrash2 size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Empty State */}
      {filteredViolations.length === 0 && (
        <div className="text-center py-12">
          <FiAlertTriangle className="mx-auto text-gray-400 text-4xl mb-4" />
          <p className="text-gray-500 dark:text-gray-400">No violations found</p>
          <p className="text-sm text-gray-400 dark:text-gray-500">
            Try adjusting your filters or search criteria
          </p>
        </div>
      )}
    </div>
  );
};

export default ViolationList;
