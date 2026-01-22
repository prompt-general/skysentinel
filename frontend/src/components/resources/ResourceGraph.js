import React, { useState, useEffect, useRef } from 'react';
import { FiDatabase, FiCloud, FiServer, FiHardDrive, FiShield, FiActivity, FiZoomIn, FiZoomOut, FiMaximize, FiDownload, FiFilter, FiRefreshCw } from 'react-icons/fi';

const ResourceGraph = ({ resources, connections, selectedResource, onResourceSelect, onFilter, onRefresh }) => {
  const canvasRef = useRef(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [hoveredResource, setHoveredResource] = useState(null);
  const [filter, setFilter] = useState({
    cloud: 'all',
    type: 'all',
    state: 'all',
    riskLevel: 'all'
  });

  useEffect(() => {
    if (resources && resources.length > 0) {
      drawGraph();
    }
  }, [resources, connections, zoom, pan, hoveredResource, filter]);

  const drawGraph = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Set canvas size
    canvas.width = width;
    canvas.height = height;

    // Apply transformations
    ctx.save();
    ctx.translate(pan.x, pan.y);
    ctx.scale(zoom, zoom);

    // Draw grid
    drawGrid(ctx, width, height);

    // Filter resources
    const filteredResources = filterResources(resources);
    
    // Filter connections
    const filteredConnections = filterConnections(connections, filteredResources);

    // Calculate positions
    const positions = calculateResourcePositions(filteredResources);

    // Draw connections
    drawConnections(ctx, filteredConnections, positions);

    // Draw resources
    drawResources(ctx, filteredResources, positions);

    ctx.restore();
  };

  const filterResources = (resources) => {
    return resources.filter(resource => {
      if (filter.cloud !== 'all' && resource.cloud !== filter.cloud) return false;
      if (filter.type !== 'all' && resource.type !== filter.type) return false;
      if (filter.state !== 'all' && resource.state !== filter.state) return false;
      if (filter.riskLevel !== 'all') {
        const riskLevel = getRiskLevel(resource.riskScore);
        if (riskLevel !== filter.riskLevel) return false;
      }
      return true;
    });
  };

  const filterConnections = (connections, filteredResources) => {
    if (!connections) return [];
    
    const resourceIds = new Set(filteredResources.map(r => r.id));
    return connections.filter(conn => 
      resourceIds.has(conn.source.id) && resourceIds.has(conn.target.id)
    );
  };

  const calculateResourcePositions = (resources) => {
    const positions = {};
    const canvas = canvasRef.current;
    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;

    // Group resources by cloud
    const cloudGroups = {};
    resources.forEach(resource => {
      if (!cloudGroups[resource.cloud]) {
        cloudGroups[resource.cloud] = [];
      }
      cloudGroups[resource.cloud].push(resource);
    });

    // Calculate positions for each cloud group
    const cloudAngles = Object.keys(cloudGroups).length > 1 
      ? (2 * Math.PI) / Object.keys(cloudGroups).length 
      : 0;

    Object.keys(cloudGroups).forEach((cloud, cloudIndex) => {
      const cloudResources = cloudGroups[cloud];
      const cloudAngle = cloudIndex * cloudAngles;
      const cloudRadius = Math.min(width, height) * 0.3;
      
      const cloudCenterX = centerX + Math.cos(cloudAngle) * cloudRadius;
      const cloudCenterY = centerY + Math.sin(cloudAngle) * cloudRadius;

      // Position resources within cloud group
      const resourceAngleStep = cloudResources.length > 1 
        ? (2 * Math.PI) / cloudResources.length 
        : 0;

      cloudResources.forEach((resource, resourceIndex) => {
        const resourceAngle = resourceIndex * resourceAngleStep;
        const resourceRadius = Math.min(width, height) * 0.15;
        
        const x = cloudCenterX + Math.cos(resourceAngle) * resourceRadius;
        const y = cloudCenterY + Math.sin(resourceAngle) * resourceRadius;
        
        positions[resource.id] = { x, y };
      });
    });

    return positions;
  };

  const drawGrid = (ctx, width, height) => {
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 1;

    const gridSize = 50;
    for (let x = 0; x <= width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }

    for (let y = 0; y <= height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
  };

  const drawConnections = (ctx, connections, positions) => {
    connections.forEach(connection => {
      const sourcePos = positions[connection.source.id];
      const targetPos = positions[connection.target.id];

      if (sourcePos && targetPos) {
        // Draw connection line
        ctx.beginPath();
        ctx.moveTo(sourcePos.x, sourcePos.y);
        ctx.lineTo(targetPos.x, targetPos.y);

        // Set line style based on connection type
        switch (connection.type) {
          case 'DEPENDS_ON':
            ctx.strokeStyle = '#3b82f6';
            ctx.lineWidth = 2;
            break;
          case 'CONNECTS_TO':
            ctx.strokeStyle = '#10b981';
            ctx.lineWidth = 1;
            break;
          case 'AFFECTS':
            ctx.strokeStyle = '#f59e0b';
            ctx.lineWidth = 2;
            break;
          case 'MANAGES':
            ctx.strokeStyle = '#8b5cf6';
            ctx.lineWidth = 2;
            break;
          default:
            ctx.strokeStyle = '#6b7280';
            ctx.lineWidth = 1;
        }

        ctx.stroke();

        // Draw connection strength indicator
        if (connection.strength) {
          const midX = (sourcePos.x + targetPos.x) / 2;
          const midY = (sourcePos.y + targetPos.y) / 2;
          
          ctx.beginPath();
          ctx.arc(midX, midY, 3, 0, 2 * Math.PI);
          ctx.fillStyle = connection.strength > 0.7 ? '#10b981' : connection.strength > 0.3 ? '#f59e0b' : '#ef4444';
          ctx.fill();
        }

        // Draw arrow for directional connections
        if (!connection.bidirectional) {
          drawArrow(ctx, sourcePos, targetPos);
        }
      }
    });
  };

  const drawResources = (ctx, resources, positions) => {
    resources.forEach(resource => {
      const position = positions[resource.id];
      if (position) {
        drawResource(ctx, resource, position);
      }
    });
  };

  const drawResource = (ctx, resource, position) => {
    const radius = 25;
    const isSelected = selectedResource?.id === resource.id;
    const isHovered = hoveredResource === resource.id;

    // Resource circle
    ctx.beginPath();
    ctx.arc(position.x, position.y, radius, 0, 2 * Math.PI);

    // Set color based on resource type and state
    let fillColor = '#3b82f6'; // Default blue
    if (resource.state === 'terminated') {
      fillColor = '#6b7280'; // Gray for terminated
    } else if (resource.state === 'pending') {
      fillColor = '#f59e0b'; // Orange for pending
    } else if (resource.state === 'running') {
      fillColor = '#10b981'; // Green for running
    }

    // Apply risk level coloring
    const riskLevel = getRiskLevel(resource.riskScore);
    if (riskLevel === 'CRITICAL') {
      fillColor = '#ef4444';
    } else if (riskLevel === 'HIGH') {
      fillColor = '#f59e0b';
    }

    ctx.fillStyle = fillColor;
    ctx.fill();

    // Border
    ctx.strokeStyle = isSelected ? '#fbbf24' : isHovered ? '#3b82f6' : '#1f2937';
    ctx.lineWidth = isSelected ? 3 : isHovered ? 2 : 1;
    ctx.stroke();

    // Resource icon
    ctx.fillStyle = '#ffffff';
    ctx.font = '16px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    const icon = getResourceIcon(resource.type);
    ctx.fillText(icon, position.x, position.y);

    // Resource name
    ctx.fillStyle = '#1f2937';
    ctx.font = '12px Arial';
    ctx.fillText(resource.name || resource.type, position.x, position.y + radius + 15);

    // Risk indicator
    if (resource.riskScore !== undefined) {
      const riskX = position.x + radius - 5;
      const riskY = position.y - radius + 5;
      
      ctx.beginPath();
      ctx.arc(riskX, riskY, 4, 0, 2 * Math.PI);
      ctx.fillStyle = getRiskColor(resource.riskScore);
      ctx.fill();
    }
  };

  const drawArrow = (ctx, start, end) => {
    const headLength = 8;
    const angle = Math.atan2(end.y - start.y, end.x - start.x);

    // Adjust end position to account for node radius
    const adjustedEndX = end.x - Math.cos(angle) * 25;
    const adjustedEndY = end.y - Math.sin(angle) * 25;

    ctx.beginPath();
    ctx.moveTo(adjustedEndX, adjustedEndY);
    ctx.lineTo(
      adjustedEndX - headLength * Math.cos(angle - Math.PI / 6),
      adjustedEndY - headLength * Math.sin(angle - Math.PI / 6)
    );
    ctx.moveTo(adjustedEndX, adjustedEndY);
    ctx.lineTo(
      adjustedEndX - headLength * Math.cos(angle + Math.PI / 6),
      adjustedEndY - headLength * Math.sin(angle + Math.PI / 6)
    );
    ctx.stroke();
  };

  const getResourceIcon = (type) => {
    if (type.includes('ec2') || type.includes('instance')) return '🖥️';
    if (type.includes('s3') || type.includes('bucket')) return '📦';
    if (type.includes('rds') || type.includes('database')) return '🗄️';
    if (type.includes('lambda') || type.includes('function')) return '⚡';
    if (type.includes('vpc') || type.includes('network')) return '🌐';
    if (type.includes('iam') || type.includes('role')) return '👤';
    if (type.includes('security') || type.includes('group')) return '🔒';
    if (type.includes('kubernetes') || type.includes('pod')) return '☸️';
    if (type.includes('container')) return '📦';
    if (type.includes('storage')) return '💾';
    return '🔧';
  };

  const getRiskLevel = (riskScore) => {
    if (riskScore >= 0.8) return 'CRITICAL';
    if (riskScore >= 0.6) return 'HIGH';
    if (riskScore >= 0.4) return 'MEDIUM';
    return 'LOW';
  };

  const getRiskColor = (riskScore) => {
    if (riskScore >= 0.8) return '#ef4444';
    if (riskScore >= 0.6) return '#f59e0b';
    if (riskScore >= 0.4) return '#3b82f6';
    return '#10b981';
  };

  const handleCanvasClick = (event) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = (event.clientX - rect.left - pan.x) / zoom;
    const y = (event.clientY - rect.top - pan.y) / zoom;

    // Check if click is on a resource
    const filteredResources = filterResources(resources);
    const positions = calculateResourcePositions(filteredResources);

    for (const resource of filteredResources) {
      const position = positions[resource.id];
      const distance = Math.sqrt(Math.pow(x - position.x, 2) + Math.pow(y - position.y, 2));

      if (distance <= 25) {
        onResourceSelect && onResourceSelect(resource);
        return;
      }
    }

    // Click on empty space deselects
    onResourceSelect && onResourceSelect(null);
  };

  const handleCanvasMouseMove = (event) => {
    if (isDragging) {
      const deltaX = event.clientX - dragStart.x;
      const deltaY = event.clientY - dragStart.y;
      setPan({ x: pan.x + deltaX, y: pan.y + deltaY });
      setDragStart({ x: event.clientX, y: event.clientY });
    } else {
      const canvas = canvasRef.current;
      const rect = canvas.getBoundingClientRect();
      const x = (event.clientX - rect.left - pan.x) / zoom;
      const y = (event.clientY - rect.top - pan.y) / zoom;

      // Check if hover is on a resource
      const filteredResources = filterResources(resources);
      const positions = calculateResourcePositions(filteredResources);

      let hoveredResourceFound = null;
      for (const resource of filteredResources) {
        const position = positions[resource.id];
        const distance = Math.sqrt(Math.pow(x - position.x, 2) + Math.pow(y - position.y, 2));

        if (distance <= 25) {
          hoveredResourceFound = resource.id;
          break;
        }
      }

      setHoveredResource(hoveredResourceFound);
    }
  };

  const handleCanvasMouseDown = (event) => {
    setIsDragging(true);
    setDragStart({ x: event.clientX, y: event.clientY });
  };

  const handleCanvasMouseUp = () => {
    setIsDragging(false);
  };

  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev * 1.2, 3));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev / 1.2, 0.5));
  };

  const handleReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const exportGraph = () => {
    const canvas = canvasRef.current;
    const link = document.createElement('a');
    link.download = 'resource-graph.png';
    link.href = canvas.toDataURL();
    link.click();
  };

  const getUniqueClouds = () => {
    const clouds = new Set();
    resources.forEach(resource => clouds.add(resource.cloud));
    return Array.from(clouds);
  };

  const getUniqueTypes = () => {
    const types = new Set();
    resources.forEach(resource => types.add(resource.type));
    return Array.from(types);
  };

  const getUniqueStates = () => {
    const states = new Set();
    resources.forEach(resource => states.add(resource.state));
    return Array.from(states);
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Resource Graph ({resources?.length || 0})
          </h2>
          <div className="flex items-center space-x-3">
            <button
              onClick={exportGraph}
              className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <FiDownload size={16} />
            </button>
            <button
              onClick={onRefresh}
              className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <FiRefreshCw size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Cloud Filter */}
          <select
            value={filter.cloud}
            onChange={(e) => setFilter({ ...filter, cloud: e.target.value })}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Clouds</option>
            {getUniqueClouds().map(cloud => (
              <option key={cloud} value={cloud}>{cloud}</option>
            ))}
          </select>

          {/* Type Filter */}
          <select
            value={filter.type}
            onChange={(e) => setFilter({ ...filter, type: e.target.value })}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Types</option>
            {getUniqueTypes().map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>

          {/* State Filter */}
          <select
            value={filter.state}
            onChange={(e) => setFilter({ ...filter, state: e.target.value })}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All States</option>
            {getUniqueStates().map(state => (
              <option key={state} value={state}>{state}</option>
            ))}
          </select>

          {/* Risk Level Filter */}
          <select
            value={filter.riskLevel}
            onChange={(e) => setFilter({ ...filter, riskLevel: e.target.value })}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Risk Levels</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>
      </div>

      {/* Controls */}
      <div className="px-6 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <button
              onClick={handleZoomIn}
              className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <FiZoomIn size={16} />
            </button>
            <button
              onClick={handleZoomOut}
              className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <FiZoomOut size={16} />
            </button>
            <button
              onClick={handleReset}
              className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <FiMaximize size={16} />
            </button>
          </div>
          
          <div className="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
            <span>Zoom: {Math.round(zoom * 100)}%</span>
            <span>Resources: {filterResources(resources).length}</span>
          </div>
        </div>
      </div>

      {/* Graph Canvas */}
      <div className="relative">
        <canvas
          ref={canvasRef}
          width={800}
          height={600}
          className="w-full border-b border-gray-200 dark:border-gray-700 cursor-move"
          onClick={handleCanvasClick}
          onMouseMove={handleCanvasMouseMove}
          onMouseDown={handleCanvasMouseDown}
          onMouseUp={handleCanvasMouseUp}
          onMouseLeave={handleCanvasMouseUp}
        />

        {/* Legend */}
        <div className="absolute bottom-4 left-4 bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Connection Types</h4>
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <div className="w-4 h-1 bg-blue-500"></div>
              <span className="text-xs text-gray-600 dark:text-gray-400">Depends On</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-1 bg-green-500"></div>
              <span className="text-xs text-gray-600 dark:text-gray-400">Connects To</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-1 bg-orange-500"></div>
              <span className="text-xs text-gray-600 dark:text-gray-400">Affects</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-1 bg-purple-500"></div>
              <span className="text-xs text-gray-600 dark:text-gray-400">Manages</span>
            </div>
          </div>
        </div>
      </div>

      {/* Selected Resource Details */}
      {selectedResource && (
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Selected Resource
          </h3>
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Name
                </label>
                <p className="text-sm text-gray-900 dark:text-white">{selectedResource.name}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Type
                </label>
                <p className="text-sm text-gray-900 dark:text-white">{selectedResource.type}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Cloud Provider
                </label>
                <p className="text-sm text-gray-900 dark:text-white">{selectedResource.cloud}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Region
                </label>
                <p className="text-sm text-gray-900 dark:text-white">{selectedResource.region}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  State
                </label>
                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                  selectedResource.state === 'running' ? 'bg-green-100 text-green-800' :
                  selectedResource.state === 'terminated' ? 'bg-red-100 text-red-800' :
                  'bg-yellow-100 text-yellow-800'
                }`}>
                  {selectedResource.state}
                </span>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Risk Score
                </label>
                <div className="flex items-center space-x-2">
                  <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                    <div
                      className="h-2 rounded-full"
                      style={{ width: `${(selectedResource.riskScore || 0) * 100}%`, backgroundColor: getRiskColor(selectedResource.riskScore) }}
                    />
                  </div>
                  <span className="text-sm text-gray-900 dark:text-white">
                    {Math.round((selectedResource.riskScore || 0) * 100)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!resources || resources.length === 0 ? (
        <div className="text-center py-12">
          <FiDatabase className="mx-auto text-gray-400 text-4xl mb-4" />
          <p className="text-gray-500 dark:text-gray-400">No resources found</p>
          <p className="text-sm text-gray-400 dark:text-gray-500">
            Resources will appear when they are discovered
          </p>
        </div>
      ) : null}
    </div>
  );
};

export default ResourceGraph;
