import React from 'react';
import { Grid, Paper, Typography, Box, CircularProgress, Alert } from '@mui/material';
import { useQuery } from '@apollo/client';
import { OVERVIEW_QUERY } from '../services/queries';
import MetricsChart from '../components/dashboard/MetricsChart';
import RecentViolations from '../components/dashboard/RecentViolations';
import RecentEvaluations from '../components/dashboard/RecentEvaluations';
import OverviewCards from '../components/dashboard/OverviewCards';

const Dashboard = () => {
  const { loading, error, data } = useQuery(OVERVIEW_QUERY, {
    variables: {
      input: {
        tenantId: 'default-tenant',
        timeframe: 'LAST_30_DAYS'
      }
    },
    pollInterval: 30000, // Refresh every 30 seconds
    errorPolicy: 'all'
  });

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress size={40} />
        <Typography variant="h6" sx={{ ml: 2 }}>
          Loading dashboard...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        Error loading dashboard: {error.message}
      </Alert>
    );
  }

  const overview = data?.overview;

  if (!overview) {
    return (
      <Alert severity="warning" sx={{ mb: 2 }}>
        No overview data available
      </Alert>
    );
  }

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold', mb: 3 }}>
        Security Dashboard
      </Typography>

      {/* Summary Cards */}
      <OverviewCards overview={overview} />

      {/* Charts and Recent Activity */}
      <Grid container spacing={3} sx={{ mt: 2 }}>
        {/* Violations Chart */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'medium' }}>
              Violations Trend
            </Typography>
            <MetricsChart 
              data={overview.trends} 
              type="violations"
              title="Violations Over Time"
            />
          </Paper>
        </Grid>

        {/* Recent Violations */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: 400, overflow: 'hidden' }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'medium' }}>
              Recent Violations
            </Typography>
            <RecentViolations 
              violations={overview.recentViolations}
              maxHeight={320}
            />
          </Paper>
        </Grid>

        {/* Risk Score Chart */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: 350 }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'medium' }}>
              Risk Score Trend
            </Typography>
            <MetricsChart 
              data={overview.trends} 
              type="riskScore"
              title="Risk Score Over Time"
            />
          </Paper>
        </Grid>

        {/* Compliance Score Chart */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: 350 }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'medium' }}>
              Compliance Score Trend
            </Typography>
            <MetricsChart 
              data={overview.trends} 
              type="compliance"
              title="Compliance Score Over Time"
            />
          </Paper>
        </Grid>

        {/* Recent Evaluations */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'medium' }}>
              Recent CI/CD Evaluations
            </Typography>
            <RecentEvaluations evaluations={overview.recentEvaluations} />
          </Paper>
        </Grid>

        {/* Critical Violations Summary */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'medium' }}>
              Critical Violations by Category
            </Typography>
            {/* Component for critical violations breakdown */}
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
              <Typography variant="body2" color="text.secondary">
                Critical violations chart component
              </Typography>
            </Box>
          </Paper>
        </Grid>

        {/* Resource Distribution */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'medium' }}>
              Resource Distribution by Cloud
            </Typography>
            {/* Component for resource distribution */}
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
              <Typography variant="body2" color="text.secondary">
                Resource distribution chart component
              </Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
