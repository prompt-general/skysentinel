import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MockedProvider } from '@apollo/client/testing';
import { ThemeModeProvider } from '../../styles/theme';
import Dashboard from '../../pages/Dashboard/Dashboard';
import { DASHBOARD_OVERVIEW_QUERY } from '../../services/api/graphql/queries';

const mockDashboardData = {
  dashboardOverview: {
    metrics: {
      totalResources: 1250,
      totalViolations: 42,
      criticalViolations: 5,
      highViolations: 12,
      mediumViolations: 15,
      lowViolations: 10,
      complianceScore: 89.5,
      attackPathsCount: 8,
      avgRemediationTime: 120,
      costOptimization: {
        estimatedSavings: 12500,
        optimizationOpportunities: 15
      }
    },
    recentViolations: [
      {
        id: 'violation-1',
        policyName: 'No Public S3 Buckets',
        resourceName: 'prod-data-bucket',
        severity: 'CRITICAL',
        detectedAt: '2023-10-01T10:30:00Z'
      }
    ],
    complianceTrend: [
      { date: '2023-09-25', score: 85 },
      { date: '2023-09-26', score: 86 },
      { date: '2023-09-27', score: 87 },
      { date: '2023-09-28', score: 88 },
      { date: '2023-09-29', score: 89 },
      { date: '2023-09-30', score: 89.5 }
    ],
    mlInsights: {
      highRiskPredictions: 3,
      modelAccuracy: 0.92,
      driftDetected: false
    }
  }
};

const mocks = [
  {
    request: {
      query: DASHBOARD_OVERVIEW_QUERY,
      variables: { tenantId: 'default' }
    },
    result: {
      data: mockDashboardData
    }
  }
];

describe('DashboardOverview', () => {
  it('renders loading state initially', () => {
    render(
      <ThemeModeProvider>
        <MockedProvider mocks={[]} addTypename={false}>
          <Dashboard />
        </MockedProvider>
      </ThemeModeProvider>
    );
    
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });
  
  it('renders dashboard data correctly', async () => {
    render(
      <ThemeModeProvider>
        <MockedProvider mocks={mocks} addTypename={false}>
          <Dashboard />
        </MockedProvider>
      </ThemeModeProvider>
    );
    
    // Wait for data to load
    await waitFor(() => {
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });
    
    // Check metrics are displayed
    expect(screen.getByText('1,250')).toBeInTheDocument(); // Total Resources
    expect(screen.getByText('42')).toBeInTheDocument(); // Total Violations
    expect(screen.getByText('5')).toBeInTheDocument(); // Critical Violations
    expect(screen.getByText('89.5%')).toBeInTheDocument(); // Compliance Score
    
    // Check recent violations
    expect(screen.getByText('No Public S3 Buckets')).toBeInTheDocument();
    
    // Check charts are rendered
    expect(screen.getByText('Violation Trends')).toBeInTheDocument();
    expect(screen.getByText('Resource Health')).toBeInTheDocument();
  });
  
  it('handles error state', async () => {
    const errorMock = [
      {
        request: {
          query: DASHBOARD_OVERVIEW_QUERY,
          variables: { tenantId: 'default' }
        },
        error: new Error('Failed to fetch data')
      }
    ];
    
    render(
      <ThemeModeProvider>
        <MockedProvider mocks={errorMock} addTypename={false}>
          <Dashboard />
        </MockedProvider>
      </ThemeModeProvider>
    );
    
    await waitFor(() => {
      expect(screen.getByText(/Error loading dashboard/)).toBeInTheDocument();
    });
  });
});
