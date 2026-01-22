import React from 'react';
import { Grid, Paper, Typography, Box, Chip, TrendingUp, TrendingDown, TrendingFlat } from '@mui/material';
import { 
  Database, 
  AlertTriangle, 
  Security, 
  CheckCircle, 
  Warning, 
  Info 
} from '@mui/icons-material';
import { useTheme } from '@mui/material/styles';

const OverviewCards = ({ overview }) => {
  const theme = useTheme();

  const getTrendIcon = (trend) => {
    if (trend > 0) return <TrendingUp />;
    if (trend < 0) return <TrendingDown />;
    return <TrendingFlat />;
  };

  const getTrendColor = (trend) => {
    if (trend > 0) return theme.palette.success.main;
    if (trend < 0) return theme.palette.error.main;
    return theme.palette.grey[500];
  };

  const calculateTrend = (data) => {
    if (!data || data.length < 2) return 0;
    const latest = data[data.length - 1].value;
    const previous = data[data.length - 2].value;
    return previous !== 0 ? ((latest - previous) / previous) * 100 : 0;
  };

  const violationsTrend = calculateTrend(overview.trends?.violations || []);
  const riskScoreTrend = calculateTrend(overview.trends?.riskScore || []);
  const complianceTrend = calculateTrend(overview.trends?.compliance || []);

  const cards = [
    {
      title: 'Total Resources',
      value: overview.totalResources.toLocaleString(),
      icon: <Database />,
      color: theme.palette.primary.main,
      bgColor: theme.palette.primary.light,
      trend: null,
      subtitle: 'Across all clouds'
    },
    {
      title: 'Total Violations',
      value: overview.totalViolations.toLocaleString(),
      icon: <AlertTriangle />,
      color: theme.palette.error.main,
      bgColor: theme.palette.error.light,
      trend: violationsTrend,
      subtitle: 'Active violations',
      severity: overview.criticalViolations > 0 ? 'critical' : 'normal'
    },
    {
      title: 'Risk Score',
      value: `${(overview.riskScore * 100).toFixed(1)}%`,
      icon: <Security />,
      color: theme.palette.warning.main,
      bgColor: theme.palette.warning.light,
      trend: riskScoreTrend,
      subtitle: 'Overall risk level'
    },
    {
      title: 'Compliance Score',
      value: `${(overview.complianceScore * 100).toFixed(1)}%`,
      icon: <CheckCircle />,
      color: theme.palette.success.main,
      bgColor: theme.palette.success.light,
      trend: complianceTrend,
      subtitle: 'Compliance level'
    }
  ];

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical':
        return theme.palette.error.main;
      case 'high':
        return theme.palette.warning.main;
      case 'medium':
        return theme.palette.info.main;
      default:
        return theme.palette.grey[500];
    }
  };

  return (
    <Grid container spacing={3}>
      {cards.map((card, index) => (
        <Grid item xs={12} sm={6} md={3} key={index}>
          <Paper 
            sx={{ 
              p: 3, 
              height: 140,
              background: `linear-gradient(135deg, ${card.bgColor}15 0%, ${card.bgColor}05 100%)`,
              borderLeft: `4px solid ${card.color}`,
              position: 'relative',
              overflow: 'hidden',
              '&:hover': {
                boxShadow: theme.shadows[4],
                transform: 'translateY(-2px)',
                transition: 'all 0.3s ease-in-out'
              }
            }}
          >
            {/* Background Pattern */}
            <Box
              sx={{
                position: 'absolute',
                top: -20,
                right: -20,
                width: 80,
                height: 80,
                borderRadius: '50%',
                backgroundColor: card.bgColor,
                opacity: 0.1
              }}
            />

            {/* Icon */}
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                mb: 2,
                color: card.color
              }}
            >
              {card.icon}
            </Box>

            {/* Title */}
            <Typography 
              variant="body2" 
              color="text.secondary" 
              sx={{ mb: 1, fontWeight: 'medium' }}
            >
              {card.title}
            </Typography>

            {/* Value */}
            <Typography 
              variant="h4" 
              sx={{ 
                fontWeight: 'bold',
                color: card.severity ? getSeverityColor(card.severity) : 'text.primary',
                mb: 1
              }}
            >
              {card.value}
            </Typography>

            {/* Trend and Subtitle */}
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="caption" color="text.secondary">
                {card.subtitle}
              </Typography>
              
              {card.trend !== null && (
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  {getTrendIcon(card.trend)}
                  <Typography 
                    variant="caption" 
                    sx={{ 
                      ml: 0.5,
                      color: getTrendColor(card.trend),
                      fontWeight: 'medium'
                    }}
                  >
                    {Math.abs(card.trend).toFixed(1)}%
                  </Typography>
                </Box>
              )}
            </Box>

            {/* Critical Indicator */}
            {card.severity === 'critical' && (
              <Chip
                size="small"
                label="Critical"
                color="error"
                sx={{
                  position: 'absolute',
                  top: 8,
                  right: 8,
                  fontSize: '0.7rem',
                  height: 20
                }}
              />
            )}
          </Paper>
        </Grid>
      ))}

      {/* Additional Info Cards */}
      <Grid item xs={12} sm={6} md={3}>
        <Paper sx={{ p: 3, height: 140 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Critical Violations
          </Typography>
          <Typography variant="h4" sx={{ fontWeight: 'bold', color: 'error.main', mb: 1 }}>
            {overview.criticalViolations}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Requires immediate attention
          </Typography>
        </Paper>
      </Grid>

      <Grid item xs={12} sm={6} md={3}>
        <Paper sx={{ p: 3, height: 140 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            High Violations
          </Typography>
          <Typography variant="h4" sx={{ fontWeight: 'bold', color: 'warning.main', mb: 1 }}>
            {overview.highViolations}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Should be addressed soon
          </Typography>
        </Paper>
      </Grid>

      <Grid item xs={12} sm={6} md={3}>
        <Paper sx={{ p: 3, height: 140 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Active Policies
          </Typography>
          <Typography variant="h4" sx={{ fontWeight: 'bold', color: 'primary.main', mb: 1 }}>
            {overview.activePolicies}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Currently enforced
          </Typography>
        </Paper>
      </Grid>

      <Grid item xs={12} sm={6} md={3}>
        <Paper sx={{ p: 3, height: 140 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Last Scan
          </Typography>
          <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 1 }}>
            {new Date(overview.lastScan).toLocaleDateString()}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {new Date(overview.lastScan).toLocaleTimeString()}
          </Typography>
        </Paper>
      </Grid>
    </Grid>
  );
};

export default OverviewCards;
