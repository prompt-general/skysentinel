import React, { useState, useEffect } from 'react';
import { FiTarget, FiShield, FiAlertTriangle, FiActivity, FiFilter, FiRefreshCw, FiSearch, FiEye, FiDownload, FiTrendingUp, FiClock, FiZap } from 'react-icons/fi';
import { formatDistanceToNow } from 'date-fns';

const AttackPathList = ({ attackPaths, onFilter, onRefresh, onView, onExport }) => {
  const [filteredAttackPaths, setFilteredAttackPaths] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [exploitabilityFilter, setExploitabilityFilter] = useState('all');
  const [sortBy, setSortBy] = useState('riskScore');
  const [sortOrder, setSortOrder] = useState('desc');
  const [selectedPaths, setSelectedPaths] = useState([]);

  useEffect(() => {
    filterAttackPaths();
  }, [attackPaths, searchQuery, riskFilter, exploitabilityFilter, sortBy, sortOrder]);

  const filterAttackPaths = () => {
    let filtered = attackPaths || [];

    // Apply search filter
    if (searchQuery) {
      filtered = filtered.filter(path =>
        path.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        path.path?.some(node => node.name?.toLowerCase().includes(searchQuery.toLowerCase())) ||
        path.techniques?.some(tech => tech.name?.toLowerCase().includes(searchQuery.toLowerCase()))
      );
    }

    // Apply risk filter
    if (riskFilter !== 'all') {
      filtered = filtered.filter(path => {
        const risk = path.riskScore;
        switch (riskFilter) {
          case 'critical':
            return risk >= 0.8;
          case 'high':
            return risk >= 0.6 && risk < 0.8;
          case 'medium':
            return risk >= 0.4 && risk < 0.6;
          case 'low':
            return risk < 0.4;
          default:
            return true;
        }
      });
    }

    // Apply exploitability filter
    if (exploitabilityFilter !== 'all') {
      filtered = filtered.filter(path => path.exploitability === exploitabilityFilter);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aValue = a[sortBy];
      let bValue = b[sortBy];

      if (sortBy === 'detectedAt') {
        aValue = new Date(aValue);
        bValue = new Date(bValue);
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    setFilteredAttackPaths(filtered);
  };

  const getRiskColor = (riskScore) => {
    if (riskScore >= 0.8) return 'text-red-600 bg-red-50 border-red-200';
    if (riskScore >= 0.6) return 'text-orange-600 bg-orange-50 border-orange-200';
    if (riskScore >= 0.4) return 'text-blue-600 bg-blue-50 border-blue-200';
    return 'text-green-600 bg-green-50 border-green-200';
  };

  const getRiskLabel = (riskScore) => {
    if (riskScore >= 0.8) return 'CRITICAL';
    if (riskScore >= 0.6) return 'HIGH';
    if (riskScore >= 0.4) return 'MEDIUM';
    return 'LOW';
  };

  const getExploitabilityIcon = (exploitability) => {
    switch (exploitability) {
      case 'HIGH':
        return <FiZap className="text-red-500" />;
      case 'MEDIUM':
        return <FiAlertTriangle className="text-orange-500" />;
      case 'LOW':
        return <FiShield className="text-blue-500" />;
      default:
        return <FiActivity className="text-gray-500" />;
    }
  };

  const getExploitabilityColor = (exploitability) => {
    switch (exploitability) {
      case 'HIGH':
        return 'bg-red-100 text-red-800';
      case 'MEDIUM':
        return 'bg-orange-100 text-orange-800';
      case 'LOW':
        return 'bg-blue-100 text-blue-800';
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

  const handleSelectPath = (pathId) => {
    setSelectedPaths(prev =>
      prev.includes(pathId)
        ? prev.filter(id => id !== pathId)
        : [...prev, pathId]
    );
  };

  const handleSelectAll = () => {
    if (selectedPaths.length === filteredAttackPaths.length) {
      setSelectedPaths([]);
    } else {
      setSelectedPaths(filteredAttackPaths.map(p => p.id));
    }
  };

  const handleBulkAction = (action) => {
    onFilter({ action, paths: selectedPaths });
    setSelectedPaths([]);
  };

  const exportPaths = () => {
    const data = {
      attackPaths: filteredAttackPaths,
      exportedAt: new Date().toISOString(),
      filters: {
        searchQuery,
        riskFilter,
        exploitabilityFilter
      }
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'attack-paths.json';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const getCriticalAssets = (path) => {
    return path.criticalAssets?.map(asset => asset.name || asset.type).join(', ') || 'None';
  };

  const getEntryPoints = (path) => {
    return path.entryPoints?.map(asset => asset.name || asset.type).join(', ') || 'None';
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Attack Paths ({filteredAttackPaths.length})
          </h2>
          <div className="flex items-center space-x-3">
            <button
              onClick={exportPaths}
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
              placeholder="Search attack paths..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Risk Filter */}
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Risk Levels</option>
            <option value="critical">Critical (80%+)</option>
            <option value="high">High (60-80%)</option>
            <option value="medium">Medium (40-60%)</option>
            <option value="low">Low (&lt;40%)</option>
          </select>

          {/* Exploitability Filter */}
          <select
            value={exploitabilityFilter}
            onChange={(e) => setExploitabilityFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Exploitability</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          {/* Sort */}
          <select
            value={`${sortBy}-${sortOrder}`}
            onChange={(e) => {
              const [field, order] = e.target.value.split('-');
              setSortBy(field);
              setSortOrder(order);
            }}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="riskScore-desc">Risk Score (High to Low)</option>
            <option value="riskScore-asc">Risk Score (Low to High)</option>
            <option value="detectedAt-desc">Detected (Newest First)</option>
            <option value="detectedAt-asc">Detected (Oldest First)</option>
            <option value="length-desc">Path Length (Longest First)</option>
            <option value="length-asc">Path Length (Shortest First)</option>
          </select>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedPaths.length > 0 && (
        <div className="px-6 py-3 bg-blue-50 dark:bg-blue-900 border-b border-blue-200 dark:border-blue-700">
          <div className="flex items-center justify-between">
            <span className="text-sm text-blue-800 dark:text-blue-200">
              {selectedPaths.length} attack paths selected
            </span>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleBulkAction('mitigate')}
                className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 transition-colors text-sm"
              >
                Mitigate
              </button>
              <button
                onClick={() => handleBulkAction('analyze')}
                className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm"
              >
                Analyze
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

      {/* Attack Paths List */}
      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {filteredAttackPaths.map((path) => (
          <div key={path.id} className="p-6 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-4 flex-1">
                {/* Checkbox */}
                <input
                  type="checkbox"
                  checked={selectedPaths.includes(path.id)}
                  onChange={() => handleSelectPath(path.id)}
                  className="mt-1 rounded border-gray-300 dark:border-gray-600"
                />

                {/* Main Content */}
                <div className="flex-1">
                  {/* Header */}
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                      Attack Path #{path.id}
                    </h3>
                    <div className="flex items-center space-x-2">
                      {/* Risk Score */}
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${getRiskColor(path.riskScore)}`}>
                        {getRiskLabel(path.riskScore)} ({Math.round(path.riskScore * 100)}%)
                      </span>
                      {/* Exploitability */}
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getExploitabilityColor(path.exploitability)}`}>
                        {getExploitabilityIcon(path.exploitability)}
                        <span className="ml-1">{path.exploitability}</span>
                      </span>
                    </div>
                  </div>

                  {/* Description */}
                  <p className="text-gray-600 dark:text-gray-400 mb-3">
                    {path.description}
                  </p>

                  {/* Path Summary */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                        Path Length
                      </label>
                      <p className="text-sm text-gray-900 dark:text-white">
                        {path.length || path.path?.length || 0} nodes
                      </p>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                        Entry Points
                      </label>
                      <p className="text-sm text-gray-900 dark:text-white truncate">
                        {getEntryPoints(path)}
                      </p>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                        Critical Assets
                      </label>
                      <p className="text-sm text-gray-900 dark:text-white truncate">
                        {getCriticalAssets(path)}
                      </p>
                    </div>
                  </div>

                  {/* Attack Techniques */}
                  {path.techniques && path.techniques.length > 0 && (
                    <div className="mb-3">
                      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                        Attack Techniques
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {path.techniques.slice(0, 3).map((technique, index) => (
                          <span
                            key={index}
                            className="inline-flex items-center px-2 py-1 rounded text-xs bg-red-100 text-red-800"
                          >
                            {technique.name}
                          </span>
                        ))}
                        {path.techniques.length > 3 && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            +{path.techniques.length - 3} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Mitigations */}
                  {path.mitigations && path.mitigations.length > 0 && (
                    <div className="mb-3">
                      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                        Recommended Mitigations
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {path.mitigations.slice(0, 2).map((mitigation, index) => (
                          <span
                            key={index}
                            className={`inline-flex items-center px-2 py-1 rounded text-xs ${
                              mitigation.automated
                                ? 'bg-blue-100 text-blue-800'
                                : 'bg-gray-100 text-gray-800'
                            }`}
                          >
                            {mitigation.name}
                          </span>
                        ))}
                        {path.mitigations.length > 2 && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            +{path.mitigations.length - 2} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Timeline */}
                  <div className="flex items-center space-x-4 text-xs text-gray-500 dark:text-gray-400">
                    <div className="flex items-center space-x-1">
                      <FiClock size={12} />
                      <span>Detected {formatDistanceToNow(new Date(path.detectedAt), { addSuffix: true })}</span>
                    </div>
                    {path.confidence && (
                      <div className="flex items-center space-x-1">
                        <FiTrendingUp size={12} />
                        <span>{Math.round(path.confidence * 100)}% confidence</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center space-x-2 ml-4">
                <button
                  onClick={() => onView(path.id)}
                  className="p-2 text-blue-600 hover:text-blue-800 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900 rounded transition-colors"
                >
                  <FiEye size={16} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Empty State */}
      {filteredAttackPaths.length === 0 && (
        <div className="text-center py-12">
          <FiTarget className="mx-auto text-gray-400 text-4xl mb-4" />
          <p className="text-gray-500 dark:text-gray-400">No attack paths found</p>
          <p className="text-sm text-gray-400 dark:text-gray-500">
            Try adjusting your filters or search criteria
          </p>
        </div>
      )}
    </div>
  );
};

export default AttackPathList;
