import React, { useState, useEffect, useRef } from 'react';
import { FiTarget, FiShield, FiAlertTriangle, FiActivity, FiZoomIn, FiZoomOut, FiMaximize, FiDownload } from 'react-icons/fi';

const AttackPathGraph = ({ attackPaths, selectedPath, onPathSelect, onNodeClick }) => {
  const canvasRef = useRef(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [hoveredNode, setHoveredNode] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    if (attackPaths && attackPaths.length > 0) {
      drawGraph();
    }
  }, [attackPaths, zoom, pan, hoveredNode, selectedNode]);

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

    // Draw attack paths
    if (selectedPath) {
      drawAttackPath(ctx, selectedPath);
    } else if (attackPaths && attackPaths.length > 0) {
      // Draw all paths
      attackPaths.forEach(path => drawAttackPath(ctx, path));
    }

    ctx.restore();
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

  const drawAttackPath = (ctx, attackPath) => {
    if (!attackPath.path || attackPath.path.length === 0) return;

    const nodes = attackPath.path;
    const nodePositions = calculateNodePositions(nodes);

    // Draw connections
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);

    for (let i = 0; i < nodes.length - 1; i++) {
      const start = nodePositions[i];
      const end = nodePositions[i + 1];

      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      ctx.stroke();

      // Draw arrow
      drawArrow(ctx, start, end);
    }

    ctx.setLineDash([]);

    // Draw nodes
    nodes.forEach((node, index) => {
      const position = nodePositions[index];
      drawNode(ctx, node, position, index === 0, index === nodes.length - 1);
    });
  };

  const calculateNodePositions = (nodes) => {
    const positions = [];
    const canvas = canvasRef.current;
    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.3;

    nodes.forEach((node, index) => {
      const angle = (index / (nodes.length - 1)) * Math.PI;
      const x = centerX + Math.cos(angle) * radius;
      const y = centerY + Math.sin(angle) * radius;
      positions.push({ x, y });
    });

    return positions;
  };

  const drawNode = (ctx, node, position, isEntryPoint, isCriticalAsset) => {
    const radius = 30;

    // Node background
    ctx.beginPath();
    ctx.arc(position.x, position.y, radius, 0, 2 * Math.PI);

    if (isEntryPoint) {
      ctx.fillStyle = '#10b981';
    } else if (isCriticalAsset) {
      ctx.fillStyle = '#ef4444';
    } else {
      ctx.fillStyle = '#3b82f6';
    }

    ctx.fill();

    // Node border
    ctx.strokeStyle = hoveredNode === node.id ? '#fbbf24' : '#1f2937';
    ctx.lineWidth = hoveredNode === node.id ? 3 : 2;
    ctx.stroke();

    // Node icon
    ctx.fillStyle = '#ffffff';
    ctx.font = '16px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    let icon = '🔒';
    if (isEntryPoint) icon = '🚪';
    else if (isCriticalAsset) icon = '💎';
    else if (node.type === 'aws:s3:bucket') icon = '📦';
    else if (node.type === 'aws:ec2:instance') icon = '🖥️';
    else if (node.type === 'aws:iam:role') icon = '👤';
    else if (node.type.includes('database')) icon = '🗄️';
    else if (node.type.includes('network')) icon = '🌐';

    ctx.fillText(icon, position.x, position.y);

    // Node label
    ctx.fillStyle = '#1f2937';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(node.name || node.type, position.x, position.y + radius + 15);
  };

  const drawArrow = (ctx, start, end) => {
    const headLength = 10;
    const angle = Math.atan2(end.y - start.y, end.x - start.x);

    ctx.beginPath();
    ctx.moveTo(end.x, end.y);
    ctx.lineTo(
      end.x - headLength * Math.cos(angle - Math.PI / 6),
      end.y - headLength * Math.sin(angle - Math.PI / 6)
    );
    ctx.moveTo(end.x, end.y);
    ctx.lineTo(
      end.x - headLength * Math.cos(angle + Math.PI / 6),
      end.y - headLength * Math.sin(angle + Math.PI / 6)
    );
    ctx.stroke();
  };

  const handleCanvasClick = (event) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = (event.clientX - rect.left - pan.x) / zoom;
    const y = (event.clientY - rect.top - pan.y) / zoom;

    // Check if click is on a node
    if (selectedPath) {
      const nodes = selectedPath.path;
      const nodePositions = calculateNodePositions(nodes);

      for (let i = 0; i < nodes.length; i++) {
        const position = nodePositions[i];
        const distance = Math.sqrt(Math.pow(x - position.x, 2) + Math.pow(y - position.y, 2));

        if (distance <= 30) {
          setSelectedNode(nodes[i]);
          onNodeClick && onNodeClick(nodes[i]);
          return;
        }
      }
    }

    setSelectedNode(null);
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

      // Check if hover is on a node
      if (selectedPath) {
        const nodes = selectedPath.path;
        const nodePositions = calculateNodePositions(nodes);

        let hoveredNodeFound = null;
        for (let i = 0; i < nodes.length; i++) {
          const position = nodePositions[i];
          const distance = Math.sqrt(Math.pow(x - position.x, 2) + Math.pow(y - position.y, 2));

          if (distance <= 30) {
            hoveredNodeFound = nodes[i];
            break;
          }
        }

        setHoveredNode(hoveredNodeFound);
      }
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
    link.download = 'attack-path-graph.png';
    link.href = canvas.toDataURL();
    link.click();
  };

  const getRiskColor = (riskScore) => {
    if (riskScore >= 0.8) return '#ef4444';
    if (riskScore >= 0.6) return '#f59e0b';
    if (riskScore >= 0.4) return '#3b82f6';
    return '#10b981';
  };

  const getExploitabilityIcon = (exploitability) => {
    switch (exploitability) {
      case 'HIGH': return '🔥';
      case 'MEDIUM': return '⚠️';
      case 'LOW': return '🔒';
      default: return '❓';
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Attack Path Visualization
          </h2>
          <div className="flex items-center space-x-3">
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
            <button
              onClick={exportGraph}
              className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <FiDownload size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Attack Path Selector */}
      {attackPaths && attackPaths.length > 1 && (
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {attackPaths.map((path, index) => (
              <div
                key={path.id}
                onClick={() => onPathSelect && onPathSelect(path)}
                className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                  selectedPath?.id === path.id
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900'
                    : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium text-gray-900 dark:text-white">
                    Attack Path {index + 1}
                  </h3>
                  <span
                    className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium"
                    style={{ backgroundColor: getRiskColor(path.riskScore) + '20', color: getRiskColor(path.riskScore) }}
                  >
                    {Math.round(path.riskScore * 100)}% Risk
                  </span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                  {path.description}
                </p>
                <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>{path.path?.length || 0} nodes</span>
                  <span>{getExploitabilityIcon(path.exploitability)} {path.exploitability}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

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

        {/* Zoom Indicator */}
        <div className="absolute bottom-4 right-4 bg-white dark:bg-gray-800 px-3 py-1 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {Math.round(zoom * 100)}%
          </span>
        </div>
      </div>

      {/* Selected Path Details */}
      {selectedPath && (
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Attack Path Details
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Risk Score
              </label>
              <div className="flex items-center space-x-2">
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className="h-2 rounded-full"
                    style={{ width: `${selectedPath.riskScore * 100}%`, backgroundColor: getRiskColor(selectedPath.riskScore) }}
                  />
                </div>
                <span className="text-sm text-gray-900 dark:text-white">
                  {Math.round(selectedPath.riskScore * 100)}%
                </span>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Exploitability
              </label>
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-orange-100 text-orange-800">
                {getExploitabilityIcon(selectedPath.exploitability)} {selectedPath.exploitability}
              </span>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Path Length
              </label>
              <p className="text-sm text-gray-900 dark:text-white">
                {selectedPath.path?.length || 0} nodes
              </p>
            </div>
          </div>

          {/* Attack Techniques */}
          {selectedPath.techniques && selectedPath.techniques.length > 0 && (
            <div className="mt-4">
              <h4 className="text-md font-medium text-gray-900 dark:text-white mb-2">
                Attack Techniques
              </h4>
              <div className="space-y-2">
                {selectedPath.techniques.map((technique, index) => (
                  <div key={index} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {technique.name}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {technique.tactic} • {technique.techniqueId}
                        </p>
                      </div>
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        technique.severity === 'HIGH' ? 'bg-red-100 text-red-800' :
                        technique.severity === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {technique.severity}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Mitigations */}
          {selectedPath.mitigations && selectedPath.mitigations.length > 0 && (
            <div className="mt-4">
              <h4 className="text-md font-medium text-gray-900 dark:text-white mb-2">
                Recommended Mitigations
              </h4>
              <div className="space-y-2">
                {selectedPath.mitigations.map((mitigation, index) => (
                  <div key={index} className="bg-green-50 dark:bg-green-900 rounded-lg p-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {mitigation.name}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {mitigation.type} • {Math.round(mitigation.effectiveness * 100)}% effective
                        </p>
                      </div>
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        mitigation.automated ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {mitigation.automated ? 'Automated' : 'Manual'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Selected Node Details */}
      {selectedNode && (
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
                <p className="text-sm text-gray-900 dark:text-white">{selectedNode.name}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Type
                </label>
                <p className="text-sm text-gray-900 dark:text-white">{selectedNode.type}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Cloud Provider
                </label>
                <p className="text-sm text-gray-900 dark:text-white">{selectedNode.cloud}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Region
                </label>
                <p className="text-sm text-gray-900 dark:text-white">{selectedNode.region}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!attackPaths || attackPaths.length === 0 ? (
        <div className="text-center py-12">
          <FiTarget className="mx-auto text-gray-400 text-4xl mb-4" />
          <p className="text-gray-500 dark:text-gray-400">No attack paths found</p>
          <p className="text-sm text-gray-400 dark:text-gray-500">
            Attack paths will appear when vulnerabilities are detected
          </p>
        </div>
      ) : !selectedPath ? (
        <div className="text-center py-12">
          <FiActivity className="mx-auto text-gray-400 text-4xl mb-4" />
          <p className="text-gray-500 dark:text-gray-400">Select an attack path to visualize</p>
        </div>
      ) : null}
    </div>
  );
};

export default AttackPathGraph;
