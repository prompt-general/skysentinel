import React, { useState, useEffect } from 'react';
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  CardHeader,
  IconButton,
  CircularProgress,
  Alert,
  Chip,
  LinearProgress
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon
} from '@mui/icons-material';
import { useQuery, useSubscription } from '@apollo/client';
import { DASHBOARD_OVERVIEW_QUERY, VIOLATION_CREATED_SUBSCRIPTION } from '../../services/api/graphql/queries';
import {
  ComplianceGauge,
  ViolationTrendChart,
  ResourceHealthChart,
  AttackPathList,
  RecentViolations,
  MLInsightsCard
} from '../../components/dashboard';

const Dashboard: React.FC = () => {
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  
  // Fetch dashboard data
  const { loading, error, data, refetch } = useQuery(DASHBOARD_OVERVIEW_QUERY, {
    variables: { tenantId: 'default' },
    pollInterval: autoRefresh ? 30000 : 0, // Auto-refresh every 30 seconds
    fetchPolicy: 'cache-and-network'
  });
  
  // Subscribe to real-time violation updates
  const { data: subscriptionData } = useSubscription(VIOLATION_CREATED_SUBSCRIPTION, {
    variables: { tenantId: 'default' },
    onSubscriptionData: () => {
      // Refetch when new violation is created
      refetch();
    }
  });
  
  const handleRefresh = () => {
    refetch();
    setLastUpdated(new Date());
  };
  
  if (loading && !data) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }
  
  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        Error loading dashboard: {error.message}
      </Alert>
    );
  }
  
  const { metrics, recentViolations, complianceTrend, mlInsights } = data.dashboardOverview;
  
  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" gutterBottom>
            Security Dashboard
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Last updated: {lastUpdated.toLocaleTimeString()}
          </Typography>
        </Box>
        <Box>
          <IconButton onClick={handleRefresh} color="primary">
            <RefreshIcon />
          </IconButton>
        </Box>
      </Box>
      
      {/* Key Metrics Grid */}
      <Grid container spacing={3} mb={4}>
        {/* Total Resources */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Total Resources
              </Typography>
              <Typography variant="h4">
                {metrics.totalResources.toLocaleString()}
              </Typography>
              <Box display="flex" alignItems="center" mt={1}>
                <TrendingUpIcon color="success" fontSize="small" />
                <Typography variant="body2" color="success.main" ml={0.5}>
                  +12% from last week
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Total Violations */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Total Violations
              </Typography>
              <Typography variant="h4">
                {metrics.totalViolations.toLocaleString()}
              </Typography>
              <Box display="flex" alignItems="center" mt={1}>
                <TrendingDownIcon color={metrics.totalViolations > 0 ? 'error' : 'success'} fontSize="small" />
                <Typography 
                  variant="body2" 
                  color={metrics.totalViolations > 0 ? 'error.main' : 'success.main'} 
                  ml={0.5}
                >
                  {metrics.totalViolations > 0 ? 'Action required' : 'All clear'}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Critical Violations */}
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderLeft: '4px solid #f44336' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={1}>
                <ErrorIcon color="error" fontSize="small" />
                <Typography color="text.secondary" ml={1}>
                  Critical Violations
                </Typography>
              </Box>
              <Typography variant="h4" color="error.main">
                {metrics.criticalViolations}
              </Typography>
              {metrics.criticalViolations > 0 && (
                <Chip 
                  label="Immediate attention required" 
                  size="small" 
                  color="error" 
                  sx={{ mt: 1 }}
                />
              )}
            </CardContent>
          </Card>
        </Grid>
        
        {/* Compliance Score */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Compliance Score
              </Typography>
              <Box display="flex" alignItems="center">
                <Typography variant="h4">
                  {metrics.complianceScore.toFixed(1)}%
                </Typography>
                <ComplianceGauge 
                  value={metrics.complianceScore} 
                  size={60} 
                  sx={{ ml: 2 }}
                />
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={metrics.complianceScore} 
                sx={{ mt: 2, height: 8, borderRadius: 4 }}
                color={
                  metrics.complianceScore >= 90 ? 'success' :
                  metrics.complianceScore >= 70 ? 'warning' : 'error'
                }
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      
      {/* Charts and Details */}
      <Grid container spacing={3}>
        {/* Violation Trends */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardHeader 
              title="Violation Trends" 
              subheader="Last 30 days"
              action={
                <IconButton>
                  <TrendingUpIcon />
                </IconButton>
              }
            />
            <CardContent>
              <ViolationTrendChart data={complianceTrend} />
            </CardContent>
          </Card>
        </Grid>
        
        {/* Resource Health */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardHeader title="Resource Health" />
            <CardContent>
              <ResourceHealthChart data={metrics} />
            </CardContent>
          </Card>
        </Grid>
        
        {/* Recent Violations */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader 
              title="Recent Violations" 
              action={
                <Chip 
                  label={`${recentViolations.length} new`} 
                  color="primary" 
                  size="small"
                />
              }
            />
            <CardContent sx={{ maxHeight: 400, overflow: 'auto' }}>
              <RecentViolations violations={recentViolations} />
            </CardContent>
          </Card>
        </Grid>
        
        {/* ML Insights */}
        <Grid item xs={12} md={6}>
          <MLInsightsCard insights={mlInsights} />
        </Grid>
        
        {/* Attack Paths */}
        <Grid item xs={12}>
          <Card>
            <CardHeader 
              title="Top Attack Paths" 
              subheader={`${metrics.attackPathsCount} paths detected`}
            />
            <CardContent>
              <AttackPathList maxPaths={5} />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
