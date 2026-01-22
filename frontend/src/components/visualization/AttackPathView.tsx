import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Button,
  Chip,
  Alert,
  LinearProgress,
  Tooltip,
  IconButton,
  Card,
  CardContent,
  Grid
} from '@mui/material';
import {
  Warning as WarningIcon,
  Security as SecurityIcon,
  ArrowForward as ArrowIcon,
  Lock as LockIcon,
  Public as PublicIcon,
  Storage as StorageIcon,
  Cloud as CloudIcon,
  Timeline as TimelineIcon
} from '@mui/icons-material';
import { useQuery } from '@apollo/client';
import { ATTACK_PATHS_QUERY } from '../../services/api/graphql/queries';

interface AttackPathViewProps {
  tenantId: string;
  attackPathId?: string;
  maxDepth?: number;
}

interface AttackStep {
  step: number;
  from: AttackPathNode;
  to: AttackPathNode;
  via: string;
  risk: number;
  description: string;
  mitigation: string;
}

interface AttackPathNode {
  id: string;
  type: string;
  name: string;
  cloud: string;
  vulnerabilities: string[];
}

const AttackPathView: React.FC<AttackPathViewProps> = ({
  tenantId,
  attackPathId,
  maxDepth = 5
}) => {
  const [selectedPath, setSelectedPath] = useState<any>(null);
  const [activeStep, setActiveStep] = useState(0);
  
  // Fetch attack paths
  const { loading, error, data } = useQuery(ATTACK_PATHS_QUERY, {
    variables: {
      tenantId,
      maxDepth,
      from: attackPathId ? undefined : 'internet',
      to: attackPathId
    },
    skip: !tenantId
  });
  
  useEffect(() => {
    if (data?.attackPaths?.length > 0) {
      setSelectedPath(data.attackPaths[0]);
    }
  }, [data]);
  
  const handleNextStep = () => {
    setActiveStep((prevStep) => Math.min(prevStep + 1, selectedPath?.steps?.length - 1 || 0));
  };
  
  const handlePrevStep = () => {
    setActiveStep((prevStep) => Math.max(prevStep - 1, 0));
  };
  
  const handleReset = () => {
    setActiveStep(0);
  };
  
  const getStepIcon = (stepNumber: number) => {
    const icons = [
      <PublicIcon />,      // Internet
      <CloudIcon />,       // Cloud resources
      <StorageIcon />,     // Storage
      <LockIcon />,        // Security boundary
      <SecurityIcon />     // Target
    ];
    return icons[stepNumber % icons.length];
  };
  
  const getRiskColor = (risk: number) => {
    if (risk >= 0.8) return '#f44336';
    if (risk >= 0.6) return '#ff9800';
    if (risk >= 0.4) return '#ffeb3b';
    return '#4caf50';
  };
  
  if (loading) {
    return (
      <Box>
        <LinearProgress />
        <Typography variant="body2" color="text.secondary" align="center" mt={2}>
          Analyzing attack paths...
        </Typography>
      </Box>
    );
  }
  
  if (error) {
    return (
      <Alert severity="error">
        Failed to load attack paths: {error.message}
      </Alert>
    );
  }
  
  if (!selectedPath) {
    return (
      <Alert severity="info">
        No attack paths detected. Your infrastructure appears to be secure.
      </Alert>
    );
  }
  
  return (
    <Box>
      {/* Path Selection */}
      {data?.attackPaths?.length > 1 && (
        <Box mb={3}>
          <Typography variant="subtitle1" gutterBottom>
            Select Attack Path:
          </Typography>
          <Box display="flex" gap={1} flexWrap="wrap">
            {data.attackPaths.map((path: any, index: number) => (
              <Chip
                key={path.id}
                label={`Path ${index + 1} (Risk: ${(path.riskScore * 10).toFixed(1)})`}
                onClick={() => {
                  setSelectedPath(path);
                  setActiveStep(0);
                }}
                color={selectedPath.id === path.id ? 'primary' : 'default'}
                variant={selectedPath.id === path.id ? 'filled' : 'outlined'}
                icon={<WarningIcon />}
              />
            ))}
          </Box>
        </Box>
      )}
      
      {/* Path Summary */}
      <Card sx={{ mb: 3, bgcolor: 'warning.light' }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={8}>
              <Typography variant="h6" gutterBottom>
                {selectedPath.description}
              </Typography>
              <Box display="flex" alignItems="center" gap={2}>
                <Chip
                  label={`Risk Score: ${(selectedPath.riskScore * 10).toFixed(1)}/10`}
                  color="error"
                  size="small"
                />
                <Chip
                  label={`Severity: ${selectedPath.severity}`}
                  color={
                    selectedPath.severity === 'CRITICAL' ? 'error' :
                    selectedPath.severity === 'HIGH' ? 'warning' : 'info'
                  }
                  size="small"
                />
                <Chip
                  label={`Steps: ${selectedPath.steps.length}`}
                  variant="outlined"
                  size="small"
                />
              </Box>
            </Grid>
            <Grid item xs={12} md={4} textAlign="right">
              <Button
                variant="contained"
                color="error"
                startIcon={<SecurityIcon />}
                onClick={() => {/* Implement mitigation */}}
              >
                Apply Mitigations
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
      
      {/* Attack Path Stepper */}
      <Paper sx={{ p: 3 }}>
        <Stepper activeStep={activeStep} orientation="vertical">
          {selectedPath.steps.map((step: any, index: number) => (
            <Step key={index}>
              <StepLabel
                StepIconComponent={() => getStepIcon(index)}
                optional={
                  <Typography variant="caption" color="text.secondary">
                    Risk: {(step.risk * 100).toFixed(0)}%
                  </Typography>
                }
              >
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="subtitle1">
                    Step {index + 1}: {step.from.type} → {step.to.type}
                  </Typography>
                  <Box
                    sx={{
                      width: 16,
                      height: 16,
                      borderRadius: '50%',
                      bgcolor: getRiskColor(step.risk)
                    }}
                  />
                </Box>
              </StepLabel>
              <StepContent>
                <Box mt={1}>
                  {/* From Node */}
                  <Card variant="outlined" sx={{ mb: 2, p: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      From Resource
                    </Typography>
                    <Box display="flex" alignItems="center" gap={1}>
                      <CloudIcon fontSize="small" />
                      <Typography variant="body2">
                        {step.from.name} ({step.from.type})
                      </Typography>
                      <Chip
                        label={step.from.cloud}
                        size="small"
                        variant="outlined"
                      />
                    </Box>
                    {step.from.vulnerabilities?.length > 0 && (
                      <Box mt={1}>
                        <Typography variant="caption" color="error">
                          Vulnerabilities: {step.from.vulnerabilities.join(', ')}
                        </Typography>
                      </Box>
                    )}
                  </Card>
                  
                  {/* Connection */}
                  <Box display="flex" justifyContent="center" my={1}>
                    <ArrowIcon />
                    <Typography variant="caption" sx={{ ml: 1 }}>
                      via {step.via}
                    </Typography>
                  </Box>
                  
                  {/* To Node */}
                  <Card variant="outlined" sx={{ mb: 2, p: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      To Resource
                    </Typography>
                    <Box display="flex" alignItems="center" gap={1}>
                      <StorageIcon fontSize="small" />
                      <Typography variant="body2">
                        {step.to.name} ({step.to.type})
                      </Typography>
                      <Chip
                        label={step.to.cloud}
                        size="small"
                        variant="outlined"
                      />
                    </Box>
                  </Card>
                  
                  {/* Description */}
                  <Typography variant="body2" paragraph>
                    {step.description}
                  </Typography>
                  
                  {/* Mitigation */}
                  {step.mitigation && (
                    <Alert severity="warning" sx={{ mt: 2 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        Recommended Mitigation:
                      </Typography>
                      {step.mitigation}
                    </Alert>
                  )}
                </Box>
                
                {/* Navigation */}
                <Box sx={{ mb: 2, mt: 2 }}>
                  <Button
                    variant="contained"
                    onClick={index < selectedPath.steps.length - 1 ? handleNextStep : handleReset}
                    sx={{ mr: 1 }}
                  >
                    {index < selectedPath.steps.length - 1 ? 'Next Step' : 'Restart'}
                  </Button>
                  <Button
                    disabled={index === 0}
                    onClick={handlePrevStep}
                  >
                    Previous
                  </Button>
                </Box>
              </StepContent>
            </Step>
          ))}
        </Stepper>
        
        {/* Complete Path View */}
        {activeStep === selectedPath.steps.length && (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="h6" gutterBottom>
              Attack Path Analysis Complete
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              You've reviewed all steps in this attack path. Consider applying the recommended
              mitigations to reduce your risk exposure.
            </Typography>
            <Button variant="outlined" onClick={handleReset}>
              Review Again
            </Button>
          </Box>
        )}
      </Paper>
      
      {/* Mitigation Actions */}
      <Paper sx={{ mt: 3, p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Recommended Mitigations
        </Typography>
        <Grid container spacing={2}>
          {selectedPath.mitigations.map((mitigation: any, index: number) => (
            <Grid item xs={12} md={6} key={index}>
              <Card variant="outlined">
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="start">
                    <Box>
                      <Typography variant="subtitle1" gutterBottom>
                        {mitigation.resourceId}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {mitigation.description}
                      </Typography>
                    </Box>
                    <Chip
                      label={mitigation.priority}
                      color={
                        mitigation.priority === 'HIGH' ? 'error' :
                        mitigation.priority === 'MEDIUM' ? 'warning' : 'info'
                      }
                      size="small"
                    />
                  </Box>
                  <Box mt={2}>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => {/* Implement action */}}
                    >
                      Apply {mitigation.action}
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Paper>
    </Box>
  );
};

export default AttackPathView;
