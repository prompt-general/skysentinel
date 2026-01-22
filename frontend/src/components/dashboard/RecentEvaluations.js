import React from 'react';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Paper, 
  Typography, 
  Chip, 
  Box, 
  IconButton,
  Tooltip,
  Avatar
} from '@mui/material';
import { 
  Visibility, 
  GitHub, 
  Gitlab, 
  Bitbucket, 
  CheckCircle, 
  Warning, 
  Error, 
  Schedule 
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';

const RecentEvaluations = ({ evaluations = [] }) => {
  const getResultIcon = (result) => {
    switch (result) {
      case 'PASS':
        return <CheckCircle sx={{ color: 'success.main' }} />;
      case 'WARN':
        return <Warning sx={{ color: 'warning.main' }} />;
      case 'BLOCK':
        return <Error sx={{ color: 'error.main' }} />;
      case 'ERROR':
        return <Error sx={{ color: 'error.main' }} />;
      default:
        return <Schedule sx={{ color: 'grey.500' }} />;
    }
  };

  const getResultColor = (result) => {
    switch (result) {
      case 'PASS':
        return 'success';
      case 'WARN':
        return 'warning';
      case 'BLOCK':
        return 'error';
      case 'ERROR':
        return 'error';
      default:
        return 'default';
    }
  };

  const getIacIcon = (iacType) => {
    switch (iacType) {
      case 'TERRAFORM':
        return <GitHub />;
      case 'CLOUDFORMATION':
        return <Avatar sx={{ width: 24, height: 24, bgcolor: 'orange.500' }}>CF</Avatar>;
      case 'ARM':
        return <Avatar sx={{ width: 24, height: 24, bgcolor: 'blue.500' }}>ARM</Avatar>;
      case 'KUBERNETES':
        return <Avatar sx={{ width: 24, height: 24, bgcolor: 'primary.main' }}>K8s</Avatar>;
      default:
        return <Avatar sx={{ width: 24, height: 24 }}>?</Avatar>;
    }
  };

  const formatDuration = (duration) => {
    if (duration < 60) {
      return `${duration}s`;
    } else if (duration < 3600) {
      return `${Math.floor(duration / 60)}m ${duration % 60}s`;
    } else {
      return `${Math.floor(duration / 3600)}h ${Math.floor((duration % 3600) / 60)}m`;
    }
  };

  if (evaluations.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="body2" color="text.secondary">
          No recent evaluations found
        </Typography>
      </Box>
    );
  }

  return (
    <TableContainer>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Result</TableCell>
            <TableCell>IaC Type</TableCell>
            <TableCell>Repository</TableCell>
            <TableCell>Branch</TableCell>
            <TableCell>Resources</TableCell>
            <TableCell>Violations</TableCell>
            <TableCell>Duration</TableCell>
            <TableCell>Time</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {evaluations.map((evaluation) => (
            <TableRow 
              key={evaluation.id}
              hover
              sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
            >
              <TableCell>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  {getResultIcon(evaluation.result)}
                  <Chip
                    label={evaluation.result}
                    size="small"
                    color={getResultColor(evaluation.result)}
                    sx={{ ml: 1 }}
                  />
                </Box>
              </TableCell>
              <TableCell>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  {getIacIcon(evaluation.iacPlan?.type)}
                  <Typography variant="body2" sx={{ ml: 1 }}>
                    {evaluation.iacPlan?.type}
                  </Typography>
                </Box>
              </TableCell>
              <TableCell>
                <Typography variant="body2" noWrap sx={{ maxWidth: 150 }}>
                  {evaluation.iacPlan?.repository || 'Unknown'}
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="body2">
                  {evaluation.iacPlan?.branch || 'main'}
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="body2">
                  {evaluation.iacPlan?.resources || 0}
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="body2">
                  {evaluation.violations?.length || 0}
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="body2">
                  {formatDuration(evaluation.duration || 0)}
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="body2" color="text.secondary">
                  {formatDistanceToNow(new Date(evaluation.timestamp), { addSuffix: true })}
                </Typography>
              </TableCell>
              <TableCell>
                <Tooltip title="View Details">
                  <IconButton size="small">
                    <Visibility fontSize="small" />
                  </IconButton>
                </Tooltip>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default RecentEvaluations;
