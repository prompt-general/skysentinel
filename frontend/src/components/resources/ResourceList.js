import React, { useState, useEffect } from 'react';
import { FiDatabase, FiCloud, FiServer, FiFilter, FiRefreshCw, FiSearch, FiDownload, FiEye, FiEdit, FiActivity, FiShield, FiDollarSign, FiTrendingUp, FiMapPin } from 'react-icons/fi';
import { formatDistanceToNow } from 'date-fns';

const ResourceList = ({ resources, onFilter, onRefresh, onView, onEdit, onExport }) => {
  const [filteredResources, setFilteredResources] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [cloudFilter, setCloudFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [stateFilter, setStateFilter] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');
  const [sortBy, setSortBy] = useState('lastScanned');
  const [sortOrder, setSortOrder] = useState('desc');
  const [selectedResources, setSelectedResources] = useState([]);

  useEffect(() => {
    filterResources();
  }, [resources, searchQuery, cloudFilter, typeFilter, stateFilter, riskFilter, sortBy, sortOrder]);

  const filterResources = () => {
    let filtered = resources || [];

    // Apply search filter
    if (searchQuery) {
      filtered = filtered.filter(resource =>
        resource.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        resource.type.toLowerCase().includes(searchQuery.toLowerCase()) ||
        resource.region.toLowerCase().includes(searchQuery.toLowerCase()) ||
        resource.account.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Apply cloud filter
    if (cloudFilter !== 'all') {
      filtered = filtered.filter(resource => resource.cloud === cloudFilter);
    }

    // Apply type filter
    if (typeFilter !== 'all') {
      filtered = filtered.filter(resource => resource.type === typeFilter);
    }

    // Apply state filter
    if (stateFilter !== 'all') {
      filtered = filtered.filter(resource => resource.state === stateFilter);
    }

    // Apply risk filter
    if (riskFilter !== 'all') {
      filtered = filtered.filter(resource => {
        const riskLevel = getRiskLevel(resource.riskScore);
        return riskLevel === riskFilter;
      });
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aValue = a[sortBy];
      let bValue = b[sortBy];

      if (sortBy === 'lastScanned' || sortBy === 'createdAt' || sortBy === 'updatedAt') {
        aValue = new Date(aValue);
        bValue = new Date(bValue);
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    setFilteredResources(filtered);
  };

  const getRiskLevel = (riskScore) => {
    if (riskScore >= 0.8) return 'CRITICAL';
    if (riskScore >= 0.6) return 'HIGH';
    if (riskScore >= 0.4) return 'MEDIUM';
    return 'LOW';
  };

  const getRiskColor = (riskScore) => {
    if (riskScore >= 0.8) return 'text-red-600 bg-red-50 border-red-200';
    if (riskScore >= 0.6) return 'text-orange-600 bg-orange-50 border-orange-200';
    if (riskScore >= 0.4) return 'text-blue-600 bg-blue-50 border-blue-200';
    return 'text-green-600 bg-green-50 border-green-200';
  };

  const getStateColor = (state) => {
    switch (state) {
      case 'running':
        return 'bg-green-100 text-green-800';
      case 'stopped':
        return 'bg-gray-100 text-gray-800';
      case 'terminated':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getCloudIcon = (cloud) => {
    switch (cloud) {
      case 'AWS':
        return '🟧';
      case 'AZURE':
        return '🔵';
      case 'GCP':
        return '🟢';
      case 'KUBERNETES':
        return '⚓';
      default:
        return '☁️';
    }
  };

  const getTypeIcon = (type) => {
    if (type.includes('ec2') || type.includes('instance')) return '🖥️';
    if (type.includes('s3') || type.includes('bucket')) return '📦';
    if (type.includes('rds') || type.includes('database')) return '🗄️';
    if (type.includes('lambda') || type.includes('function')) return '⚡';
    if (type.includes('vpc') || type.includes('network')) return '🌐';
    if (type.includes('iam') || type.includes('role')) return '👤';
    if (type.includes('security') || type.includes('group')) return '🔒';
    if (type.includes('kubernetes') || type.includes('pod')) return '☸️';
    if (type.includes('container')) return '📦';
    if (type.includes('storage')) return '💾';
    return '🔧';
  };

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const handleSelectResource = (resourceId) => {
    setSelectedResources(prev =>
      prev.includes(resourceId)
        ? prev.filter(id => id !== resourceId)
        : [...prev, resourceId]
    );
  };

  const handleSelectAll = () => {
    if (selectedResources.length === filteredResources.length) {
      setSelectedResources([]);
    } else {
      setSelectedResources(filteredResources.map(r => r.id));
    }
  };

  const handleBulkAction = (action) => {
    onFilter({ action, resources: selectedResources });
    setSelectedResources([]);
  };

  const exportResources = () => {
    const data = {
      resources: filteredResources,
      exportedAt: new Date().toISOString(),
      filters: {
        searchQuery,
        cloudFilter,
        typeFilter,
        stateFilter,
        riskFilter
      }
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'resources.json';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const getUniqueClouds = () => {
    const clouds = new Set();
    filteredResources.forEach(resource => clouds.add(resource.cloud));
    return Array.from(clouds);
  };

  const getUniqueTypes = () => {
    const types = new Set();
    filteredResources.forEach(resource => types.add(resource.type));
    return Array.from(types);
  };

  const getUniqueStates = () => {
    const states = new Set();
    filteredResources.forEach(resource => states.add(resource.state));
    return Array.from(states);
  };

  const getResourceStats = () => {
    const stats = {
      total: filteredResources.length,
      byCloud: {},
      byState: {},
      byRisk: { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 },
      avgRiskScore: 0
    };

    filteredResources.forEach(resource => {
      // By cloud
      stats.byCloud[resource.cloud] = (stats.byCloud[resource.cloud] || 0) + 1;
      
      // By state
      stats.byState[resource.state] = (stats.byState[resource.state] || 0) + 1;
      
      // By risk
      const riskLevel = getRiskLevel(resource.riskScore);
      stats.byRisk[riskLevel]++;
      
      // Average risk score
      if (resource.riskScore !== undefined) {
        stats.avgRiskScore += resource.riskScore;
      }
    });

    if (filteredResources.length > 0) {
      stats.avgRiskScore = stats.avgRiskScore / filteredResources.length;
    }

    return stats;
  };

  const stats = getResourceStats();

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Resources ({filteredResources.length})
          </h2>
          <div className="flex items-center space-x-3">
            <button
              onClick={exportResources}
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
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{stats.total}</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Total Resources</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">{stats.byRisk.CRITICAL}</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Critical Risk</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{stats.byState.running || 0}</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Running</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">
              {Math.round(stats.avgRiskScore * 100)}%
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Avg Risk Score</div>
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
              placeholder="Search resources..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Cloud Filter */}
          <select
            value={cloudFilter}
            onChange={(e) => setCloudFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Clouds</option>
            {getUniqueClouds().map(cloud => (
              <option key={cloud} value={cloud}>{cloud}</option>
            ))}
          </select>

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

          {/* State Filter */}
          <select
            value={stateFilter}
            onChange={(e) => setStateFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All States</option>
            {getUniqueStates().map(state => (
              <option key={state} value={state}>{state}</option>
            ))}
          </select>

          {/* Risk Filter */}
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Risk Levels</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedResources.length > 0 && (
        <div className="px-6 py-3 bg-blue-50 dark:bg-blue-900 border-b border-blue-200 dark:border-blue-700">
          <div className="flex items-center justify-between">
            <span className="text-sm text-blue-800 dark:text-blue-200">
              {selectedResources.length} resources selected
            </span>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleBulkAction('scan')}
                className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm"
              >
                Scan
              </button>
              <button
                onClick={() => handleBulkAction('remediate')}
                className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 transition-colors text-sm"
              >
                Remediate
              </button>
              <button
                onClick={() => handleBulkAction('tag')}
                className="px-3 py-1 bg-purple-600 text-white rounded hover:bg-purple-700 transition-colors text-sm"
              >
                Tag
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Resources Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left">
                <input
                  type="checkbox"
                  checked={selectedResources.length === filteredResources.length}
                  onChange={handleSelectAll}
                  className="rounded border-gray-300 dark:border-gray-600"
                />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Resource
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Location
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                State
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Risk Score
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('lastScanned')}
                  className="flex items-center space-x-1 hover:text-gray-700 dark:hover:text-gray-300"
                >
                  <span>Last Scanned</span>
                </button>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {filteredResources.map((resource) => (
              <tr key={resource.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                <td className="px-6 py-4">
                  <input
                    type="checkbox"
                    checked={selectedResources.includes(resource.id)}
                    onChange={() => handleSelectResource(resource.id)}
                    className="rounded border-gray-300 dark:border-gray-600"
                  />
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center space-x-3">
                    <div className="text-2xl">{getCloudIcon(resource.cloud)}</div>
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {resource.name}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        ID: {resource.id}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center space-x-2">
                    <span className="text-lg">{getTypeIcon(resource.type)}</span>
                    <div>
                      <div className="text-sm text-gray-900 dark:text-white">
                        {resource.type}
                      </div>
                      {resource.owner && (
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          Owner: {resource.owner}
                        </div>
                      )}
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-900 dark:text-white">
                    <div className="flex items-center space-x-1">
                      <FiMapPin size={12} />
                      <span>{resource.region}</span>
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {resource.account}
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStateColor(resource.state)}`}>
                    {resource.state}
                  </span>
                </td>
                <td className="px-6 py-4">
                  {resource.riskScore !== undefined ? (
                    <div className="flex items-center space-x-2">
                      <div className="w-16 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div
                          className="h-2 rounded-full"
                          style={{ width: `${resource.riskScore * 100}%`, backgroundColor: getRiskColor(resource.riskScore).split(' ')[0] }}
                        />
                      </div>
                      <span className={`text-sm font-medium ${getRiskColor(resource.riskScore)}`}>
                        {Math.round(resource.riskScore * 100)}%
                      </span>
                    </div>
                  ) : (
                    <span className="text-sm text-gray-400">N/A</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-900 dark:text-white">
                    {resource.lastScanned ? (
                      <>
                        <div>{formatDistanceToNow(new Date(resource.lastScanned), { addSuffix: true })}</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(resource.lastScanned).toLocaleDateString()}
                        </div>
                      </>
                    ) : (
                      <span className="text-gray-400">Never</span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => onView(resource.id)}
                      className="text-blue-600 hover:text-blue-800 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900 rounded p-1"
                    >
                      <FiEye size={16} />
                    </button>
                    <button
                      onClick={() => onEdit(resource.id)}
                      className="text-green-600 hover:text-green-800 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900 rounded p-1"
                    >
                      <FiEdit size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Empty State */}
      {filteredResources.length === 0 && (
        <div className="text-center py-12">
          <FiDatabase className="mx-auto text-gray-400 text-4xl mb-4" />
          <p className="text-gray-500 dark:text-gray-400">No resources found</p>
          <p className="text-sm text-gray-400 dark:text-gray-500">
            Try adjusting your filters or search criteria
          </p>
        </div>
      )}
    </div>
  );
};

export default ResourceList;
