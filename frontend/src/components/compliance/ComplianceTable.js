import React, { useState, useEffect } from 'react';
import { FiCheckCircle, FiAlertTriangle, FiXCircle, FiFilter, FiRefreshCw, FiSearch, FiDownload, FiEye, FiEdit, FiTrendingUp, FiTrendingDown, FiMinus, FiCalendar, FiClock } from 'react-icons/fi';
import { formatDistanceToNow } from 'date-fns';

const ComplianceTable = ({ data, frameworks, onFilter, onRefresh, onView, onExport }) => {
  const [filteredData, setFilteredData] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [frameworkFilter, setFrameworkFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [sortBy, setSortBy] = useState('lastAssessed');
  const [sortOrder, setSortOrder] = useState('desc');
  const [selectedItems, setSelectedItems] = useState([]);

  useEffect(() => {
    filterData();
  }, [data, frameworks, searchQuery, frameworkFilter, statusFilter, categoryFilter, sortBy, sortOrder]);

  const filterData = () => {
    let filtered = [];

    // Combine frameworks and controls data
    if (frameworks) {
      filtered = frameworks.map(framework => ({
        type: 'framework',
        id: framework.framework,
        name: framework.framework,
        version: framework.version,
        score: framework.score,
        status: framework.status,
        lastAssessed: framework.lastAssessed,
        controls: framework.controls?.length || 0,
        gaps: framework.gaps?.length || 0,
        category: 'Framework',
        requirements: framework.requirements?.length || 0,
        trend: framework.trend
      }));
    }

    if (data && data.controls) {
      const controls = data.controls.map(control => ({
        type: 'control',
        id: control.controlId,
        name: control.controlName,
        framework: control.framework,
        score: control.score,
        status: control.status,
        lastAssessed: control.lastTested,
        category: control.category,
        automated: control.automated,
        description: control.description,
        evidence: control.evidence?.length || 0,
        exceptions: control.exceptions?.length || 0
      }));
      filtered = [...filtered, ...controls];
    }

    // Apply search filter
    if (searchQuery) {
      filtered = filtered.filter(item =>
        item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.framework?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.category?.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Apply framework filter
    if (frameworkFilter !== 'all') {
      filtered = filtered.filter(item => item.framework === frameworkFilter);
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(item => item.status === statusFilter);
    }

    // Apply category filter
    if (categoryFilter !== 'all') {
      filtered = filtered.filter(item => item.category === categoryFilter);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aValue = a[sortBy];
      let bValue = b[sortBy];

      if (sortBy === 'lastAssessed' || sortBy === 'lastTested') {
        aValue = new Date(aValue);
        bValue = new Date(bValue);
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    setFilteredData(filtered);
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'COMPLIANT':
        return <FiCheckCircle className="text-green-500" />;
      case 'NON_COMPLIANT':
        return <FiXCircle className="text-red-500" />;
      case 'PARTIALLY_COMPLIANT':
        return <FiAlertTriangle className="text-orange-500" />;
      default:
        return <FiMinus className="text-gray-500" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'COMPLIANT':
        return 'bg-green-100 text-green-800';
      case 'NON_COMPLIANT':
        return 'bg-red-100 text-red-800';
      case 'PARTIALLY_COMPLIANT':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getScoreColor = (score) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-blue-600';
    if (score >= 50) return 'text-orange-600';
    return 'text-red-600';
  };

  const getTrendIcon = (trend) => {
    if (!trend) return <FiMinus className="text-gray-500" />;
    if (trend.change > 0) return <FiTrendingUp className="text-green-500" />;
    if (trend.change < 0) return <FiTrendingDown className="text-red-500" />;
    return <FiMinus className="text-gray-500" />;
  };

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const handleSelectItem = (itemId) => {
    setSelectedItems(prev =>
      prev.includes(itemId)
        ? prev.filter(id => id !== itemId)
        : [...prev, itemId]
    );
  };

  const handleSelectAll = () => {
    if (selectedItems.length === filteredData.length) {
      setSelectedItems([]);
    } else {
      setSelectedItems(filteredData.map(item => item.id));
    }
  };

  const handleBulkAction = (action) => {
    onFilter({ action, items: selectedItems });
    setSelectedItems([]);
  };

  const exportData = () => {
    const exportData = {
      compliance: filteredData,
      exportedAt: new Date().toISOString(),
      filters: {
        searchQuery,
        frameworkFilter,
        statusFilter,
        categoryFilter
      }
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'compliance-data.json';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const getUniqueFrameworks = () => {
    const frameworks = new Set();
    filteredData.forEach(item => {
      if (item.framework) frameworks.add(item.framework);
    });
    return Array.from(frameworks);
  };

  const getUniqueCategories = () => {
    const categories = new Set();
    filteredData.forEach(item => {
      if (item.category) categories.add(item.category);
    });
    return Array.from(categories);
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Compliance Data ({filteredData.length})
          </h2>
          <div className="flex items-center space-x-3">
            <button
              onClick={exportData}
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
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {/* Search */}
          <div className="relative">
            <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search compliance..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Framework Filter */}
          <select
            value={frameworkFilter}
            onChange={(e) => setFrameworkFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Frameworks</option>
            {getUniqueFrameworks().map(framework => (
              <option key={framework} value={framework}>{framework}</option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Statuses</option>
            <option value="COMPLIANT">Compliant</option>
            <option value="PARTIALLY_COMPLIANT">Partially Compliant</option>
            <option value="NON_COMPLIANT">Non-Compliant</option>
          </select>

          {/* Category Filter */}
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Categories</option>
            {getUniqueCategories().map(category => (
              <option key={category} value={category}>{category}</option>
            ))}
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
            <option value="lastAssessed-desc">Last Assessed (Newest)</option>
            <option value="lastAssessed-asc">Last Assessed (Oldest)</option>
            <option value="score-desc">Score (High to Low)</option>
            <option value="score-asc">Score (Low to High)</option>
            <option value="name-asc">Name (A-Z)</option>
            <option value="name-desc">Name (Z-A)</option>
          </select>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedItems.length > 0 && (
        <div className="px-6 py-3 bg-blue-50 dark:bg-blue-900 border-b border-blue-200 dark:border-blue-700">
          <div className="flex items-center justify-between">
            <span className="text-sm text-blue-800 dark:text-blue-200">
              {selectedItems.length} items selected
            </span>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleBulkAction('remediate')}
                className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 transition-colors text-sm"
              >
                Remediate
              </button>
              <button
                onClick={() => handleBulkAction('assess')}
                className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm"
              >
                Re-assess
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

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left">
                <input
                  type="checkbox"
                  checked={selectedItems.length === filteredData.length}
                  onChange={handleSelectAll}
                  className="rounded border-gray-300 dark:border-gray-600"
                />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Framework
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('score')}
                  className="flex items-center space-x-1 hover:text-gray-700 dark:hover:text-gray-300"
                >
                  <span>Score</span>
                </button>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('lastAssessed')}
                  className="flex items-center space-x-1 hover:text-gray-700 dark:hover:text-gray-300"
                >
                  <span>Last Assessed</span>
                </button>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {filteredData.map((item) => (
              <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                <td className="px-6 py-4">
                  <input
                    type="checkbox"
                    checked={selectedItems.includes(item.id)}
                    onChange={() => handleSelectItem(item.id)}
                    className="rounded border-gray-300 dark:border-gray-600"
                  />
                </td>
                <td className="px-6 py-4">
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {item.name}
                    </div>
                    {item.version && (
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        v{item.version}
                      </div>
                    )}
                    {item.description && (
                      <div className="text-xs text-gray-500 dark:text-gray-400 max-w-xs truncate">
                        {item.description}
                      </div>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    item.type === 'framework'
                      ? 'bg-purple-100 text-purple-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}>
                    {item.type}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-900 dark:text-white">
                    {item.framework || 'N/A'}
                  </div>
                  {item.category && (
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {item.category}
                    </div>
                  )}
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center space-x-2">
                    <span className={`text-sm font-medium ${getScoreColor(item.score)}`}>
                      {item.score}%
                    </span>
                    {item.trend && (
                      {getTrendIcon(item.trend)}
                    )}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center space-x-2">
                    {getStatusIcon(item.status)}
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(item.status)}`}>
                      {item.status}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-900 dark:text-white">
                    {item.lastAssessed || item.lastTested ? (
                      <>
                        <div>{formatDistanceToNow(new Date(item.lastAssessed || item.lastTested), { addSuffix: true })}</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(item.lastAssessed || item.lastTested).toLocaleDateString()}
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
                      onClick={() => onView(item.id)}
                      className="text-blue-600 hover:text-blue-800 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900 rounded p-1"
                    >
                      <FiEye size={16} />
                    </button>
                    {item.type === 'control' && (
                      <button
                        className="text-green-600 hover:text-green-800 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900 rounded p-1"
                      >
                        <FiEdit size={16} />
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
      {filteredData.length === 0 && (
        <div className="text-center py-12">
          <FiCheckCircle className="mx-auto text-gray-400 text-4xl mb-4" />
          <p className="text-gray-500 dark:text-gray-400">No compliance data found</p>
          <p className="text-sm text-gray-400 dark:text-gray-500">
            Try adjusting your filters or search criteria
          </p>
        </div>
      )}

      {/* Summary */}
      {filteredData.length > 0 && (
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {filteredData.filter(item => item.status === 'COMPLIANT').length}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">Compliant</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">
                {filteredData.filter(item => item.status === 'PARTIALLY_COMPLIANT').length}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">Partially Compliant</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">
                {filteredData.filter(item => item.status === 'NON_COMPLIANT').length}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">Non-Compliant</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {filteredData.length > 0 ? Math.round(filteredData.reduce((sum, item) => sum + item.score, 0) / filteredData.length) : 0}%
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">Average Score</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ComplianceTable;
