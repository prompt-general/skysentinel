import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import { FiTrendingUp, FiTrendingDown, FiActivity, FiCheckCircle, FiAlertTriangle, FiBarChart, FiPieChart, FiTarget } from 'react-icons/fi';

const ComplianceChart = ({ data, type = 'trend', timeframe = '30d', frameworks = [] }) => {
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    processChartData();
  }, [data, type, timeframe, frameworks]);

  const processChartData = () => {
    setLoading(true);
    
    let processedData = [];

    switch (type) {
      case 'trend':
        processedData = processTrendData();
        break;
      case 'framework':
        processedData = processFrameworkData();
        break;
      case 'severity':
        processedData = processSeverityData();
        break;
      case 'category':
        processedData = processCategoryData();
        break;
      case 'radar':
        processedData = processRadarData();
        break;
      case 'comparison':
        processedData = processComparisonData();
        break;
      default:
        processedData = processTrendData();
    }

    setChartData(processedData);
    setLoading(false);
  };

  const processTrendData = () => {
    if (!data || !data.trends) return [];

    return data.trends.map(item => ({
      date: new Date(item.timestamp).toLocaleDateString(),
      overallScore: item.overallScore || 0,
      ...item.frameworks?.reduce((acc, framework) => {
        acc[framework.framework] = framework.score;
        return acc;
      }, {})
    }));
  };

  const processFrameworkData = () => {
    if (!data || !data.frameworks) return [];

    return data.frameworks.map(framework => ({
      name: framework.framework,
      score: framework.score,
      status: framework.status,
      controls: framework.controls?.length || 0,
      gaps: framework.gaps?.length || 0,
      lastAssessed: framework.lastAssessed
    }));
  };

  const processSeverityData = () => {
    if (!data || !data.violations) return [];

    const severityData = data.violations.reduce((acc, violation) => {
      const severity = violation.severity || 'UNKNOWN';
      acc[severity] = (acc[severity] || 0) + 1;
      return acc;
    }, {});

    return Object.entries(severityData).map(([severity, count]) => ({
      severity,
      count,
      percentage: (count / data.violations.length) * 100
    }));
  };

  const processCategoryData = () => {
    if (!data || !data.categories) return [];

    return data.categories.map(category => ({
      name: category.name,
      score: category.score,
      controls: category.controls,
      gaps: category.gaps,
      trend: category.trend
    }));
  };

  const processRadarData = () => {
    if (!data || !data.frameworks) return [];

    return data.frameworks.map(framework => ({
      framework: framework.framework,
      score: framework.score,
      fullMark: 100
    }));
  };

  const processComparisonData = () => {
    if (!data || !data.comparison) return [];

    return data.comparison.map(item => ({
      period: item.period,
      current: item.currentScore,
      previous: item.previousScore,
      change: item.change
    }));
  };

  const getScoreColor = (score) => {
    if (score >= 90) return '#10b981';
    if (score >= 70) return '#3b82f6';
    if (score >= 50) return '#f59e0b';
    return '#ef4444';
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'COMPLIANT': return '#10b981';
      case 'NON_COMPLIANT': return '#ef4444';
      case 'PARTIALLY_COMPLIANT': return '#f59e0b';
      default: return '#6b7280';
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'CRITICAL': return '#ef4444';
      case 'HIGH': return '#f59e0b';
      case 'MEDIUM': return '#3b82f6';
      case 'LOW': return '#10b981';
      default: return '#6b7280';
    }
  };

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

  const renderTrendChart = () => (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis domain={[0, 100]} />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="overallScore" stroke="#3b82f6" strokeWidth={2} name="Overall Score" />
        {frameworks.map((framework, index) => (
          <Line
            key={framework}
            type="monotone"
            dataKey={framework}
            stroke={COLORS[index % COLORS.length]}
            strokeWidth={2}
            name={framework}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );

  const renderFrameworkChart = () => (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis domain={[0, 100]} />
        <Tooltip />
        <Legend />
        <Bar dataKey="score" fill="#3b82f6" name="Compliance Score" />
      </BarChart>
    </ResponsiveContainer>
  );

  const renderSeverityChart = () => (
    <ResponsiveContainer width="100%" height={400}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={({ severity, percentage }) => `${severity} (${percentage.toFixed(1)}%)`}
          outerRadius={120}
          fill="#8884d8"
          dataKey="count"
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={getSeverityColor(entry.severity)} />
          ))}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  );

  const renderCategoryChart = () => (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={chartData} layout="horizontal">
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" domain={[0, 100]} />
        <YAxis dataKey="name" type="category" width={100} />
        <Tooltip />
        <Legend />
        <Bar dataKey="score" fill="#3b82f6" name="Compliance Score" />
      </BarChart>
    </ResponsiveContainer>
  );

  const renderRadarChart = () => (
    <ResponsiveContainer width="100%" height={400}>
      <RadarChart data={chartData}>
        <PolarGrid />
        <PolarAngleAxis dataKey="framework" />
        <PolarRadiusAxis angle={90} domain={[0, 100]} />
        <Radar name="Compliance Score" dataKey="score" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.6} />
        <Tooltip />
      </RadarChart>
    </ResponsiveContainer>
  );

  const renderComparisonChart = () => (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="period" />
        <YAxis domain={[0, 100]} />
        <Tooltip />
        <Legend />
        <Bar dataKey="current" fill="#3b82f6" name="Current Period" />
        <Bar dataKey="previous" fill="#93c5fd" name="Previous Period" />
      </BarChart>
    </ResponsiveContainer>
  );

  const renderChart = () => {
    switch (type) {
      case 'trend':
        return renderTrendChart();
      case 'framework':
        return renderFrameworkChart();
      case 'severity':
        return renderSeverityChart();
      case 'category':
        return renderCategoryChart();
      case 'radar':
        return renderRadarChart();
      case 'comparison':
        return renderComparisonChart();
      default:
        return renderTrendChart();
    }
  };

  const getChartIcon = () => {
    switch (type) {
      case 'trend':
        return <FiTrendingUp className="text-blue-600" />;
      case 'framework':
        return <FiBarChart className="text-green-600" />;
      case 'severity':
        return <FiPieChart className="text-orange-600" />;
      case 'category':
        return <FiBarChart className="text-purple-600" />;
      case 'radar':
        return <FiTarget className="text-red-600" />;
      case 'comparison':
        return <FiActivity className="text-indigo-600" />;
      default:
        return <FiTrendingUp className="text-blue-600" />;
    }
  };

  const getChartTitle = () => {
    switch (type) {
      case 'trend':
        return 'Compliance Score Trends';
      case 'framework':
        return 'Compliance by Framework';
      case 'severity':
        return 'Violations by Severity';
      case 'category':
        return 'Compliance by Category';
      case 'radar':
        return 'Framework Compliance Radar';
      case 'comparison':
        return 'Period Comparison';
      default:
        return 'Compliance Overview';
    }
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {getChartIcon()}
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {getChartTitle()}
            </h3>
          </div>
          <div className="flex items-center space-x-2">
            <select
              value={timeframe}
              onChange={(e) => {
                // Handle timeframe change
              }}
              className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
              <option value="1y">Last year</option>
            </select>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="p-6">
        {chartData.length > 0 ? (
          renderChart()
        ) : (
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <FiActivity className="mx-auto text-gray-400 text-4xl mb-4" />
              <p className="text-gray-500 dark:text-gray-400">No data available</p>
              <p className="text-sm text-gray-400 dark:text-gray-500">
                Try adjusting the timeframe or filters
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Summary Stats */}
      {data && type === 'framework' && (
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {chartData.filter(f => f.status === 'COMPLIANT').length}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">Compliant</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">
                {chartData.filter(f => f.status === 'PARTIALLY_COMPLIANT').length}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">Partially Compliant</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">
                {chartData.filter(f => f.status === 'NON_COMPLIANT').length}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">Non-Compliant</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {chartData.length > 0 ? Math.round(chartData.reduce((sum, f) => sum + f.score, 0) / chartData.length) : 0}%
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">Average Score</div>
            </div>
          </div>
        </div>
      )}

      {/* Legend */}
      {type === 'severity' && (
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex flex-wrap justify-center gap-4">
            {chartData.map((item, index) => (
              <div key={index} className="flex items-center space-x-2">
                <div
                  className="w-4 h-4 rounded"
                  style={{ backgroundColor: getSeverityColor(item.severity) }}
                />
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {item.severity} ({item.count})
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ComplianceChart;
