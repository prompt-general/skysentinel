import React, { useEffect, useRef, useState } from 'react';
import { DataSet, Network } from 'vis-network/standalone';
import 'vis-network/styles/vis-network.css';
import {
  Box,
  Paper,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  IconButton,
  Tooltip,
  Slider,
  Switch,
  FormControlLabel,
  Chip,
  CircularProgress,
  Alert,
  Divider
} from '@mui/material';
import {
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  CenterFocusStrong as CenterIcon,
  FilterList as FilterIcon,
  Search as SearchIcon,
  Layers as LayersIcon
} from '@mui/icons-material';

interface ResourceGraphProps {
  tenantId: string;
  initialFilters?: GraphFilters;
  onNodeClick?: (node: GraphNode) => void;
  onEdgeClick?: (edge: GraphEdge) => void;
}

interface GraphFilters {
  cloudProviders?: string[];
  resourceTypes?: string[];
  severity?: string[];
  showViolationsOnly?: boolean;
}

interface GraphNode {
  id: string;
  label: string;
  type: string;
  cloud: string;
  group: string;
  shape: string;
  color: string;
  size: number;
  title: string;
  violations?: number;
}

interface GraphEdge {
  id: string;
  from: string;
  to: string;
  label: string;
  arrows: string;
  color: string;
  width: number;
}

const ResourceGraph: React.FC<ResourceGraphProps> = ({
  tenantId,
  initialFilters = {},
  onNodeClick,
  onEdgeClick
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  
  const [nodes, setNodes] = useState<DataSet<GraphNode>>(new DataSet());
  const [edges, setEdges] = useState<DataSet<GraphEdge>>(new DataSet());
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<GraphFilters>(initialFilters);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [showLabels, setShowLabels] = useState<boolean>(true);
  const [layout, setLayout] = useState<string>('hierarchical');
  
  // Fetch graph data
  useEffect(() => {
    const fetchGraphData = async () => {
      try {
        setLoading(true);
        
        // In production, this would be a GraphQL query
        const response = await fetch(`/api/graph/${tenantId}/resources`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filters })
        });
        
        if (!response.ok) {
          throw new Error('Failed to fetch graph data');
        }
        
        const data = await response.json();
        
        // Transform data for vis-network
        const graphNodes = data.nodes.map((node: any) => ({
          id: node.id,
          label: showLabels ? node.name : '',
          type: node.type,
          cloud: node.cloud,
          group: node.cloud,
          shape: getNodeShape(node.type),
          color: getNodeColor(node.cloud, node.violations),
          size: calculateNodeSize(node.type, node.violations),
          title: generateNodeTooltip(node),
          violations: node.violations,
          font: {
            size: 14,
            color: '#333',
            face: 'Roboto',
            strokeWidth: 2,
            strokeColor: '#ffffff'
          }
        }));
        
        const graphEdges = data.edges.map((edge: any, index: number) => ({
          id: `edge-${index}`,
          from: edge.source,
          to: edge.target,
          label: edge.type,
          arrows: 'to',
          color: getEdgeColor(edge.type),
          width: calculateEdgeWidth(edge.strength),
          dashes: edge.type === 'DEPENDS_ON',
          title: edge.type
        }));
        
        setNodes(new DataSet(graphNodes));
        setEdges(new DataSet(graphEdges));
        setLoading(false);
        
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };
    
    fetchGraphData();
  }, [tenantId, filters, showLabels]);
  
  // Initialize network
  useEffect(() => {
    if (!containerRef.current || nodes.length === 0) return;
    
    const options = {
      nodes: {
        shape: 'dot',
        scaling: {
          min: 10,
          max: 30,
          label: {
            enabled: true,
            min: 14,
            max: 30
          }
        },
        shadow: true,
        font: {
          size: 14,
          face: 'Roboto'
        }
      },
      edges: {
        arrows: {
          to: { enabled: true, scaleFactor: 0.5 }
        },
        smooth: {
          type: 'dynamic',
          roundness: 0.5
        },
        color: {
          color: '#97C2FC',
          highlight: '#FFA500',
          hover: '#FFA500'
        },
        width: 2,
        selectionWidth: 3
      },
      physics: {
        enabled: true,
        stabilization: {
          enabled: true,
          iterations: 1000,
          updateInterval: 100
        },
        hierarchicalRepulsion: {
          centralGravity: 0.0,
          springLength: 100,
          springConstant: 0.01,
          nodeDistance: 120,
          damping: 0.09
        },
        solver: layout === 'hierarchical' ? 'hierarchicalRepulsion' : 'forceAtlas2Based',
        timestep: 0.5
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        hideEdgesOnDrag: true,
        hideEdgesOnZoom: true
      },
      layout: {
        hierarchical: {
          enabled: layout === 'hierarchical',
          direction: 'UD',
          sortMethod: 'directed',
          levelSeparation: 150,
          nodeSpacing: 100
        }
      }
    };
    
    networkRef.current = new Network(
      containerRef.current,
      { nodes, edges },
      options
    );
    
    // Event handlers
    networkRef.current.on('click', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const node = nodes.get(nodeId) as GraphNode;
        onNodeClick?.(node);
      } else if (params.edges.length > 0) {
        const edgeId = params.edges[0];
        const edge = edges.get(edgeId) as GraphEdge;
        onEdgeClick?.(edge);
      }
    });
    
    networkRef.current.on('zoom', (params) => {
      setZoomLevel(params.scale);
    });
    
    // Cleanup
    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
      }
    };
  }, [nodes, edges, layout, onNodeClick, onEdgeClick]);
  
  // Helper functions
  const getNodeShape = (type: string): string => {
    if (type.includes('database')) return 'database';
    if (type.includes('storage')) return 'box';
    if (type.includes('compute')) return 'circle';
    if (type.includes('network')) return 'triangle';
    if (type.includes('security')) return 'star';
    return 'dot';
  };
  
  const getNodeColor = (cloud: string, violations: number = 0): string => {
    if (violations > 0) {
      if (violations > 5) return '#f44336'; // Red for high violations
      if (violations > 2) return '#ff9800'; // Orange for medium violations
      return '#ffeb3b'; // Yellow for low violations
    }
    
    // Colors by cloud provider
    const colors: Record<string, string> = {
      aws: '#FF9900',
      azure: '#0078D4',
      gcp: '#4285F4',
      kubernetes: '#326CE5'
    };
    
    return colors[cloud.toLowerCase()] || '#9E9E9E';
  };
  
  const calculateNodeSize = (type: string, violations: number = 0): number => {
    let size = 20;
    if (type.includes('database')) size = 30;
    if (type.includes('compute')) size = 25;
    if (violations > 0) size += violations * 2;
    return Math.min(size, 50);
  };
  
  const generateNodeTooltip = (node: any): string => {
    return `
      <div style="padding: 8px; max-width: 300px;">
        <strong>${node.name}</strong><br/>
        <small>${node.type}</small><br/>
        <hr style="margin: 4px 0"/>
        Cloud: ${node.cloud}<br/>
        Region: ${node.region}<br/>
        ${node.violations ? `Violations: ${node.violations}` : 'No violations'}
      </div>
    `;
  };
  
  const getEdgeColor = (type: string): string => {
    const colors: Record<string, string> = {
      CONNECTED_TO: '#4CAF50',
      DEPENDS_ON: '#2196F3',
      CAN_ACCESS: '#FF5722',
      OWNS: '#9C27B0'
    };
    return colors[type] || '#757575';
  };
  
  const calculateEdgeWidth = (strength: number = 1): number => {
    return Math.min(strength * 2, 5);
  };
  
  // Control handlers
  const handleZoomIn = () => {
    if (networkRef.current) {
      networkRef.current.moveTo({ scale: zoomLevel * 1.2 });
    }
  };
  
  const handleZoomOut = () => {
    if (networkRef.current) {
      networkRef.current.moveTo({ scale: zoomLevel * 0.8 });
    }
  };
  
  const handleCenterView = () => {
    if (networkRef.current) {
      networkRef.current.fit();
    }
  };
  
  const handleSearch = () => {
    if (networkRef.current && searchTerm) {
      const matchingNodes = nodes.get({
        filter: (node) => 
          node.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
          node.type.toLowerCase().includes(searchTerm.toLowerCase())
      });
      
      if (matchingNodes.length > 0) {
        networkRef.current.selectNodes(matchingNodes.map(n => n.id));
        networkRef.current.focus(matchingNodes[0].id, { scale: 1.5 });
      }
    }
  };
  
  return (
    <Paper sx={{ height: '600px', position: 'relative' }}>
      {/* Loading overlay */}
      {loading && (
        <Box
          position="absolute"
          top={0}
          left={0}
          right={0}
          bottom={0}
          display="flex"
          alignItems="center"
          justifyContent="center"
          bgcolor="rgba(255, 255, 255, 0.8)"
          zIndex={1000}
        >
          <CircularProgress />
        </Box>
      )}
      
      {/* Error overlay */}
      {error && (
        <Box
          position="absolute"
          top={0}
          left={0}
          right={0}
          bottom={0}
          display="flex"
          alignItems="center"
          justifyContent="center"
          bgcolor="rgba(255, 255, 255, 0.9)"
          zIndex={1000}
        >
          <Alert severity="error">
            {error}
          </Alert>
        </Box>
      )}
      
      {/* Graph container */}
      <Box
        ref={containerRef}
        sx={{
          width: '100%',
          height: '100%',
          border: '1px solid #e0e0e0',
          borderRadius: 1
        }}
      />
      
      {/* Controls overlay */}
      <Box
        position="absolute"
        top={16}
        left={16}
        right={16}
        display="flex"
        justifyContent="space-between"
        zIndex={100}
      >
        {/* Left controls */}
        <Paper sx={{ p: 1, display: 'flex', gap: 1 }}>
          <Tooltip title="Zoom In">
            <IconButton size="small" onClick={handleZoomIn}>
              <ZoomInIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Zoom Out">
            <IconButton size="small" onClick={handleZoomOut}>
              <ZoomOutIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Center View">
            <IconButton size="small" onClick={handleCenterView}>
              <CenterIcon />
            </IconButton>
          </Tooltip>
          
          <Divider orientation="vertical" flexItem sx={{ mx: 1 }} />
          
          <TextField
            size="small"
            placeholder="Search resources..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            sx={{ width: 200 }}
            InputProps={{
              endAdornment: (
                <IconButton size="small" onClick={handleSearch}>
                  <SearchIcon />
                </IconButton>
              )
            }}
          />
        </Paper>
        
        {/* Right controls */}
        <Paper sx={{ p: 1, display: 'flex', gap: 1, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Layout</InputLabel>
            <Select
              value={layout}
              label="Layout"
              onChange={(e) => setLayout(e.target.value)}
            >
              <MenuItem value="hierarchical">Hierarchical</MenuItem>
              <MenuItem value="force">Force-directed</MenuItem>
              <MenuItem value="circular">Circular</MenuItem>
            </Select>
          </FormControl>
          
          <Tooltip title="Show Labels">
            <FormControlLabel
              control={
                <Switch
                  size="small"
                  checked={showLabels}
                  onChange={(e) => setShowLabels(e.target.checked)}
                />
              }
              label="Labels"
            />
          </Tooltip>
        </Paper>
      </Box>
      
      {/* Legend */}
      <Box position="absolute" bottom={16} left={16} zIndex={100}>
        <Paper sx={{ p: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Legend
          </Typography>
          <Box display="flex" flexWrap="wrap" gap={1}>
            <Chip 
              size="small" 
              label="AWS" 
              sx={{ bgcolor: '#FF9900', color: 'white' }}
            />
            <Chip 
              size="small" 
              label="Azure" 
              sx={{ bgcolor: '#0078D4', color: 'white' }}
            />
            <Chip 
              size="small" 
              label="GCP" 
              sx={{ bgcolor: '#4285F4', color: 'white' }}
            />
            <Chip 
              size="small" 
              label="Violations" 
              sx={{ bgcolor: '#f44336', color: 'white' }}
            />
          </Box>
        </Paper>
      </Box>
      
      {/* Zoom level indicator */}
      <Box position="absolute" bottom={16} right={16} zIndex={100}>
        <Paper sx={{ p: 1 }}>
          <Typography variant="caption">
            Zoom: {(zoomLevel * 100).toFixed(0)}%
          </Typography>
        </Paper>
      </Box>
    </Paper>
  );
};

export default ResourceGraph;
