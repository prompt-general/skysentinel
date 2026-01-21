import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { FiTrendingUp, FiTrendingDown, FiActivity } from 'react-icons/fi';

const MetricsChart = ({ data, type = 'violations', timeRange = '24h' }) => {
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Process data for chart
    const processedData = data?.trends?.violations || [];
    const processedData = data?.trends?.riskScore || [];
    const processedData = data?.trends?.compliance || [];

    let trendData = [];
    
    switch (type) {
      case 'violations':
        trendData = processedData.map(item => ({
          date: item.date,
          value: item.value,
          type: 'violations'
        }));
        break;
      case 'riskScore':
        trendData = processedData.map(item => ({
          date: item.date,
          value: item.value * 100, // Convert to percentage
          type: 'riskScore'
        }));
        break;
      case 'compliance':
        trendData = processedData.map(item => ({
          date: item.date,
          value: item.value * 100, // Convert to percentage
          type: 'compliance'
        }));
        break;
      default:
        trendData = processedData;
    }

    setChartData(trendData);
    setLoading(false);
  }, [data, type]);

  const getTrendIcon = (data) => {
    if (data.length < 2) return <FiActivity className="text-gray-500" />;
    const latest = data[data.length - 1].value;
    const previous = data[data.length - 2].value;
    if (latest > previous) return <FiTrendingUp className="text-green-500" />;
    if (latest < previous) return <FiTrendingDown className="text-red-500" />;
    return <FiActivity className="text-gray-500" />;
  };

  const getTrendColor = (data) => {
    if (data.length < 2) return 'text-gray-600';
    const latest = data[data.length - 1].value;
    const previous = data[data.length - 2].value;
    if (latest > previous) return 'text-green-600';
    if (latest < previous) return 'text-red-600';
    return 'text-gray-600';
  };

  const calculateTrend = (data) => {
    if (data.length < 2) return 0;
    const latest = data[data.length - 1].value;
    const previous = data[data.length - 2].value;
    return ((latest - previous) / previous) * 100;
  };

  const formatTooltipValue = (value, type) => {
    if (type === 'riskScore' || type === 'compliance') {
      return `${value.toFixed(1)}%`;
    }
    return value;
  };

  const getChartColor = (type) => {
    switch (type) {
      case 'violations':
        return '#ef4444';
      case 'riskScore':
        return '#f59e0b';
      case 'compliance':
        return '#10b981';
      default:
        return '#6b7280';
    }
  };

  const getChartConfig = (type) => {
    switch (type) {
      case 'violations':
        return {
          stroke: '#ef4444',
          fill: '#ef4444',
          fillOpacity: 0.1
        };
      case 'riskScore':
        return {
          stroke: '#f59e0b',
          fill: '#f59e0b',
          fillOpacity: 0.1
        };
      case 'compliance':
        return {
          stroke: '#10b981',
          fill: '#10b981',
          fillOpacity: 0.1
        };
      default:
        return {
          stroke: '#6b7280',
          fill: '#6b7280',
          fillOpacity: 0.1
        };
    }
  };

  const chartConfig = getChartConfig(type);

  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center bg-white dark:bg-gray-800 rounded-lg">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-300 dark:border-gray-600"></div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white capitalize">
          {type.replace(/([A-Z])/g, ' $1')} Metrics
        </h3>
        <div className="flex items-center space-x-2">
          {getTrendIcon(chartData)}
          <span className={`text-sm font-medium ${getTrendColor(chartData)}`}>
            {Math.abs(calculateTrend(chartData)).toFixed(1)}%
          </span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={250}>
        <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={`colorGradient-${type}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={chartConfig.stroke} stopOpacity={0.8} />
              <stop offset="95%" stopColor={chartConfig.stroke} stopOpacity={0.1} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.1} />
          <XAxis 
            dataKey="date" 
            stroke="#9CA3AF" 
            tick={{ fontSize: 12 }}
            tickLine={false}
          />
          <YAxis 
            tick={{ fontSize: 12 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip 
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload;
                return (
                  <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {data.date}
                    </p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {formatTooltipValue(data.value, type)}
                    </p>
                  </div>
                );
              }
              return null;
            }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={chartConfig.stroke}
            fill={`url(#colorGradient-${type})`}
            strokeWidth={2}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default MetricsChart;
