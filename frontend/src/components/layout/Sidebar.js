import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  FiHome,
  FiShield,
  FiAlertTriangle,
  FiActivity,
  FiDatabase,
  FiSettings,
  FiChevronDown,
  FiChevronRight,
  FiTarget,
  FiCheckSquare,
  FiGitBranch
  FiBarChart
  FiUsers
  FiLock
  FiCloud,
  FiMonitor,
  FiTrendingUp
} from 'react-icons/fi';

const Sidebar = ({ collapsed, onToggle }) => {
  const [expandedSections, setExpandedSections] = useState({
    dashboard: true,
    policies: false,
    violations: false,
    attackPaths: false,
    compliance: false,
    resources: false,
    cicd: false,
    monitoring: false
  });

  const location = useLocation();

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const menuItems = [
    {
      section: 'dashboard',
      title: 'Dashboard',
      icon: FiHome,
      path: '/dashboard',
      children: []
    },
    {
      section: 'policies',
      title: 'Policies',
      icon: FiShield,
      children: [
        { title: 'Policy List', path: '/policies' },
        { title: 'Create Policy', path: '/policies/create' },
        { title: 'Policy Templates', path: '/policies/templates' }
      ]
    },
    {
      section: 'violations',
      title: 'Violations',
      icon: FiAlertTriangle,
      children: [
        { title: 'All Violations', path: '/violations' },
        { title: 'Critical', path: '/violations?severity=CRITICAL' },
        { title: 'High Risk', path: '/violations?severity=HIGH' },
        { title: 'Resolved', path: '/violations?status=RESOLVED' }
      ]
    },
    {
      section: 'attackPaths',
      title: 'Attack Paths',
      icon: FiTarget,
      children: [
        { title: 'Attack Path Graph', path: '/attack-paths' },
        { title: 'Risk Analysis', path: '/attack-paths/analysis' },
        { title: 'Mitigation', path: '/attack-paths/mitigation' }
      ]
    },
    {
      section: 'compliance',
      title: 'Compliance',
      icon: FiCheckSquare,
      children: [
        { title: 'Compliance Dashboard', path: '/compliance' },
        { title: 'PCI DSS', path: '/compliance/pci-dss' },
        { title: 'SOC 2', path: '/compliance/soc2' },
        { title: 'GDPR', path: '/compliance/gdpr' },
        { title: 'HIPAA', path: '/compliance/hipaa' }
      ]
    },
    {
      section: 'resources',
      title: 'Resources',
      icon: FiDatabase,
      children: [
        { title: 'Resource Inventory', path: '/resources' },
        { title: 'Resource Graph', path: '/resources/graph' },
        { title: 'Cloud Accounts', path: '/resources/accounts' },
        { title: 'Resource Groups', path: '/resources/groups' }
      ]
    },
    {
      section: 'cicd',
      title: 'CI/CD',
      icon: FiGitBranch,
      children: [
        { title: 'Evaluations', path: '/cicd' },
        { title: 'Pipelines', path: '/cicd/pipelines' },
        { title: 'Integrations', path: '/cicd/integrations' },
        { title: 'ML Predictions', path: '/cicd/ml-predictions' }
      ]
    },
    {
      section: 'monitoring',
      title: 'Monitoring',
      icon: FiMonitor,
      children: [
        { title: 'Dashboard', path: '/monitoring' },
        { title: 'ML Models', path: '/monitoring/ml-models' },
        { title: 'Alerts', path: '/monitoring/alerts' },
        { title: 'Analytics', path: '/monitoring/analytics' }
      ]
    }
  ];

  const isActive = (path) => {
    return location.pathname === path || location.pathname.startsWith(path + '?');
  };

  if (collapsed) {
    return (
      <div className="w-16 bg-gray-900 h-full flex flex-col">
        <div className="p-4">
          <button
            onClick={onToggle}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <FiChevronRight size={20} />
          </button>
        </div>
        <nav className="flex-1 px-2">
          {menuItems.map((item) => (
            <NavLink
              key={item.section}
              to={item.children[0]?.path || item.path}
              className={({ isActive }) =>
                `flex items-center justify-center p-3 rounded-lg transition-colors ${
                  isActive(item.children[0]?.path || item.path)
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }`
              }
              title={item.title}
            >
              <item.icon size={20} />
            </NavLink>
          ))}
        </nav>
      </div>
    );
  }

  return (
    <div className="w-64 bg-gray-900 h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <FiLock size={16} className="text-white" />
            </div>
            <div>
              <h1 className="text-white font-bold text-lg">SkySentinel</h1>
              <p className="text-gray-400 text-xs">Security Platform</p>
            </div>
          </div>
          <button
            onClick={onToggle}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <FiChevronLeft size={20} />
          </button>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-4 space-y-2 overflow-y-auto">
        {menuItems.map((item) => (
          <div key={item.section}>
            <button
              onClick={() => toggleSection(item.section)}
              className={`w-full flex items-center justify-between p-3 rounded-lg transition-colors ${
                isActive(item.children[0]?.path || item.path)
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              <div className="flex items-center space-x-3">
                <item.icon size={20} />
                <span className="font-medium">{item.title}</span>
              </div>
              {item.children.length > 0 && (
                expandedSections[item.section] ? (
                  <FiChevronDown size={16} />
                ) : (
                  <FiChevronRight size={16} />
                )
              )}
            </button>

            {/* Submenu */}
            {item.children.length > 0 && expandedSections[item.section] && (
              <div className="ml-8 mt-1 space-y-1">
                {item.children.map((child) => (
                  <NavLink
                    key={child.path}
                    to={child.path}
                    className={({ isActive }) =>
                      `flex items-center p-2 rounded-md text-sm transition-colors ${
                        isActive(child.path)
                          ? 'text-blue-400 bg-gray-800'
                          : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
                      }`
                    >
                    {child.title}
                  </NavLink>
                ))}
              </div>
            )}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-800">
        <div className="space-y-2">
          <div className="flex items-center space-x-2 text-xs text-gray-500">
            <FiCloud size={14} />
            <span>Multi-Cloud</span>
          </div>
          <div className="flex items-center space-x-2 text-xs text-gray-500">
            <FiTrendingUp size={14} />
            <span>ML-Powered</span>
          </div>
          <div className="flex items-center space-x-2 text-xs text-gray-500">
            <FiUsers size={14} />
            <span>Team Plan</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
