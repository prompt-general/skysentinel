import React, { useState, useEffect } from 'react';
import { FiTrendingUp, FiTrendingDown, FiActivity, FiAlertTriangle, FiCheckCircle, FiShield, FiDatabase } from 'react-icons/fi';

const Overview = ({ data }) => {
  const [timeRange, setTimeRange] = useState('24h');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate data loading
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="bg-white dark:bg-gray-800 rounded-lg p-6 animate-pulse">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded mb-2"></div>
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded"></div>
          </div>
        ))}
      </div>
    );
  }

  const stats = data?.overview || {
    totalResources: 1250,
    totalViolations: 45,
    criticalViolations: 8,
    highViolations: 12,
    riskScore: 0.65,
    complianceScore: 0.78,
    activePolicies: 24,
    lastScan: new Date().toISOString(),
    trends: {
      violations: [
        { date: '2024-01-15', value: 42 },
        { date: '2024-01-16', value: 45 },
        { date: '2024-01-17', value: 43 },
        { date: '2024-01-18', value: 45 },
        { date: '2024-01-19', value: 48 }
      ],
      riskScore: [
        { date: '2024-01-15', value: 0.62 },
        { date: '2024-01-16', value: 0.65 },
        { date: '2024-01-17', value: 0.64 },
        { date: '2024-01-18', value: 0.66 },
        { date: '2024-01-19', value: 0.65 }
      ],
      compliance: [
        { date: '2024-01-15', value: 0.75 },
        { date: '2024-01-16', value: 0.78 },
        { date: '2024-01-17', value: 0.77 },
        { date: '2024-01-18', value: 0.78 },
        {date: '2024-01-19', value: 0.76 }
      ]
    }
  };

  const getTrendIcon = (trend) => {
    if (trend > 0) return <FiTrendingUp className="text-green-500" />;
    if (trend < 0) return <FiTrendingDown className="text-red-500" />;
    return <FiActivity className="text-gray-500" />;
  };

  const getTrendColor = (trend) => {
    if (trend > 0) return 'text-green-600';
    if (trend < 0) return 'text-red-600';
    return 'text-gray-600';
  };

  const calculateTrend = (data) => {
    if (data.length < 2) return 0;
    const latest = data[data.length - 1].value;
    const previous = data[data.length - 2].value;
    return ((latest - previous) / previous) * 100;
  };

  const formatNumber = (num) => {
    return num.toLocaleString();
  };

  const formatPercentage = (num) => {
    return `${(num * 100).toFixed(1)}%`;
  };

  return (
    <div className="space-y-6">
      {/* Time Range Selector */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Security Overview</h2>
        <div className="flex space-x-2">
          {['24h', '7d', '30d', '90d'].map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                timeRange === range
                  ? 'bg-blue-600 text-white'
                  : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Total Resources */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Resources</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatNumber(stats.totalResources)}
              </p>
            </div>
            <div className="p-3 bg-blue-100 dark:bg-blue-900 rounded-lg">
              <FiDatabase className="text-blue-600 dark:text-blue-400 text-xl" />
            </div>
          </div>
        </div>

        {/* Total Violations */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Violations</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatNumber(stats.totalViolations)}
              </p>
              <div className="flex items-center space-x-1 mt-1">
                {getTrendIcon(calculateTrend(stats.trends.violations))}
                <span className={`text-sm font-medium ${getTrendColor(calculateTrend(stats.trends.violations))}`}>
                  {Math.abs(calculateTrend(stats.trends.violations)).toFixed(1)}%
                </span>
              </div>
            </div>
            <div className="p-3 bg-red-100 dark:bg-red-900 rounded-lg">
              <FiAlertTriangle className="text-red-600 dark:text-red-400 text-xl" />
            </div>
          </div>
        </div>

        {/* Risk Score */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Risk Score</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatPercentage(stats.riskScore)}
              </p>
              <div className="flex items-center space-x-1 mt-1">
                {getTrendIcon(calculateTrend(stats.trends.riskScore))}
                <span className={`text-sm font-medium ${getTrendColor(calculateTrend(stats.trends.riskScore))}`}>
                  {Math.abs(calculateTrend(stats.trends.riskScore)).toFixed(1)}%
                </span>
              </div>
            </div>
            <div className="p-3 bg-orange-100 dark:bg-orange-900 rounded-lg">
              <FiShield className="text-orange-600 dark:text-orange-400 text-xl" />
            </div>
          </div>
        </div>

        {/* Compliance Score */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Compliance Score</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatPercentage(stats.complianceScore)}
              </p>
              <div className="flex items-center space-x-1 mt-1">
                {getTrendIcon(calculateTrend(stats.trends.compliance))}
                <span className={`text-sm font-medium ${getTrendColor(calculateTrend(stats.trends.compliance))}`}>
                  {Math.abs(calculateTrend(stats.trends.compliance)).toFixed(1)}%
                </span>
              </div>
            </div>
            <div className="p-3 bg-green-100 dark:bg-green-900 rounded-lg">
              <FiCheckCircle className="text-green-600 dark:text-green-400 text-xl" />
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Critical Violations */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Critical Violations</h3>
            <span className="px-2 py-1 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 text-xs font-medium rounded-full">
              {stats.criticalViolations}
            </span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">This week</span>
              <span className="text-sm font-medium text-gray-900 dark:text-white">+2</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">Last week</span>
              <span className="text-sm font-medium text-gray-900 dark:text-white">+5</span>
            </div>
          </div>
        </div>

        {/* High Violations */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">High Violations</h3>
            <span className="px-2 py-1 bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200 text-xs font-medium rounded-full">
              {stats.highViolations}
            </span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">This week</span>
              <span className="text-sm font-medium text-gray-900 dark:text-white">+3</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">Last week</span>
              <span className="text-sm font-medium text-gray-900 dark:text-white">+7</span>
            </div>
          </div>
        </div>

        {/* Active Policies */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Active Policies</h3>
            <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 text-xs font-medium rounded-full">
              {stats.activePolicies}
            </span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">Security</span>
              <span className="text-sm font-medium text-gray-900 dark:text-white">12</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">Compliance</span>
              <span className="text-sm font-medium text-gray-900 dark:text-white">8</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">Cost</span>
              <span className="text-sm font-medium text-gray-900 dark:text-white">4</span>
            </div>
          </div>
        </div>
      </div>

      {/* Last Scan Info */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Last Scan</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {new Date(stats.lastScan).toLocaleString()}
            </p>
          </div>
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            Scan Now
          </button>
        </div>
      </div>
    </div>
  );
};

export default Overview;
