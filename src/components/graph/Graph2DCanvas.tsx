import React, { useState, useRef, useMemo } from 'react';
import { GraphNode, GraphEdge } from '../../types';
import { useUiStore } from '../../stores/uiStore';
import { ZoomIn, ZoomOut, RotateCcw, Filter, Eye } from 'lucide-react';

export interface Graph2DCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  height?: number;
  interactive?: boolean;
}

interface Point {
  x: number;
  y: number;
}

const TYPE_COLORS: Record<string, string> = {
  Startup: '#e11d48',
  CoE: '#0d9488',
  Institution: '#2563eb',
  Person: '#d97706',
  EcosystemEnabler: '#8b5cf6',
  Entity: '#64748b',
};

export const Graph2DCanvas: React.FC<Graph2DCanvasProps> = ({
  nodes,
  edges,
  height = 480,
  interactive = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { setSelectedNode } = useUiStore();

  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState<Point>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<Point>({ x: 0, y: 0 });
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<string | null>(null);

  // Available unique types
  const nodeTypes = useMemo(() => {
    const set = new Set<string>();
    nodes.forEach((n) => set.add(n.type || 'Entity'));
    return Array.from(set);
  }, [nodes]);

  // Filtered nodes and edges
  const filteredNodes = useMemo(() => {
    if (!selectedTypeFilter) return nodes;
    return nodes.filter((n) => n.type === selectedTypeFilter);
  }, [nodes, selectedTypeFilter]);

  const activeNodeIds = useMemo(() => {
    return new Set(filteredNodes.map((n) => n.id));
  }, [filteredNodes]);

  const filteredEdges = useMemo(() => {
    return edges.filter(
      (e) => activeNodeIds.has(e.source) && activeNodeIds.has(e.target)
    );
  }, [edges, activeNodeIds]);

  // Deterministic radial layout for clean rendering
  const nodePositions = useMemo(() => {
    const pos = new Map<string, Point>();
    const count = filteredNodes.length;
    if (count === 0) return pos;

    const width = 600;
    const canvasHeight = height;
    const centerX = width / 2;
    const centerY = canvasHeight / 2;

    if (count === 1) {
      pos.set(filteredNodes[0].id, { x: centerX, y: centerY });
      return pos;
    }

    const radius = Math.min(centerX, centerY) * 0.72;
    filteredNodes.forEach((node, idx) => {
      const angle = (idx / count) * 2 * Math.PI - Math.PI / 2;
      pos.set(node.id, {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      });
    });

    return pos;
  }, [filteredNodes, height]);

  // Mouse pan handling
  const handleMouseDown = (e: React.MouseEvent) => {
    if (!interactive) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setOffset({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => setIsDragging(false);

  // Wheel zoom
  const handleWheel = (e: React.WheelEvent) => {
    if (!interactive) return;
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoom((prev) => Math.min(Math.max(prev * zoomFactor, 0.4), 2.5));
  };

  const resetView = () => {
    setZoom(1);
    setOffset({ x: 0, y: 0 });
    setSelectedTypeFilter(null);
  };

  const handleNodeClick = (node: GraphNode, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedNode(node);
  };

  return (
    <div
      ref={containerRef}
      className="relative w-full bg-slate-950 rounded-xl border border-slate-800 overflow-hidden select-none"
      style={{ height }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
    >
      {/* Control Bar Overlay */}
      <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5 bg-slate-900/90 border border-slate-800 rounded-lg p-1 shadow-md">
        <button
          onClick={() => setZoom((z) => Math.min(z * 1.2, 2.5))}
          title="Zoom In"
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition-colors"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => setZoom((z) => Math.max(z * 0.8, 0.4))}
          title="Zoom Out"
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition-colors"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={resetView}
          title="Reset View"
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Type Filter Chips */}
      {nodeTypes.length > 1 && (
        <div className="absolute top-3 left-3 z-10 flex flex-wrap items-center gap-1.5 bg-slate-900/90 border border-slate-800 rounded-lg p-1.5 text-xs shadow-md">
          <span className="text-[10px] text-slate-500 uppercase font-bold flex items-center gap-1 px-1">
            <Filter className="w-3 h-3" /> Filter:
          </span>
          <button
            onClick={() => setSelectedTypeFilter(null)}
            className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
              selectedTypeFilter === null
                ? 'bg-sky-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            All ({nodes.length})
          </button>
          {nodeTypes.map((type) => (
            <button
              key={type}
              onClick={() => setSelectedTypeFilter(selectedTypeFilter === type ? null : type)}
              className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors flex items-center gap-1 ${
                selectedTypeFilter === type
                  ? 'bg-sky-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: TYPE_COLORS[type] || '#64748b' }}
              />
              {type}
            </button>
          ))}
        </div>
      )}

      {/* SVG Canvas Rendering Layer */}
      <svg
        className="w-full h-full cursor-grab active:cursor-grabbing"
        viewBox="0 0 600 480"
        preserveAspectRatio="xMidYMid meet"
      >
        <g
          transform={`translate(${offset.x}, ${offset.y}) scale(${zoom})`}
          style={{ transformOrigin: '300px 240px' }}
        >
          {/* Edges */}
          {filteredEdges.map((edge, idx) => {
            const p1 = nodePositions.get(edge.source);
            const p2 = nodePositions.get(edge.target);
            if (!p1 || !p2) return null;

            const midX = (p1.x + p2.x) / 2;
            const midY = (p1.y + p2.y) / 2;

            return (
              <g key={`edge-${idx}`}>
                <line
                  x1={p1.x}
                  y1={p1.y}
                  x2={p2.x}
                  y2={p2.y}
                  stroke="#334155"
                  strokeWidth={1.5}
                  strokeDasharray="4 2"
                />
                {edge.relationship && (
                  <text
                    x={midX}
                    y={midY - 4}
                    fill="#94a3b8"
                    fontSize={8}
                    textAnchor="middle"
                    className="font-mono font-semibold"
                  >
                    {edge.relationship}
                  </text>
                )}
              </g>
            );
          })}

          {/* Nodes */}
          {filteredNodes.map((node) => {
            const pos = nodePositions.get(node.id);
            if (!pos) return null;

            const isHovered = hoveredNodeId === node.id;
            const color = TYPE_COLORS[node.type] || node.color || '#64748b';

            return (
              <g
                key={node.id}
                transform={`translate(${pos.x}, ${pos.y})`}
                onMouseEnter={() => setHoveredNodeId(node.id)}
                onMouseLeave={() => setHoveredNodeId(null)}
                onClick={(e) => handleNodeClick(node, e)}
                className="cursor-pointer"
              >
                {/* Node Glow on Hover */}
                {isHovered && (
                  <circle
                    r={22}
                    fill={color}
                    opacity={0.25}
                    className="animate-pulse"
                  />
                )}

                {/* Main Node Circle */}
                <circle
                  r={isHovered ? 16 : 14}
                  fill={color}
                  stroke="#0f172a"
                  strokeWidth={2}
                  className="transition-all duration-150"
                />

                {/* Node Label */}
                <text
                  y={25}
                  textAnchor="middle"
                  fill="#f1f5f9"
                  fontSize={10}
                  fontWeight={isHovered ? 600 : 500}
                  className="font-sans"
                >
                  {node.label || node.name}
                </text>

                {/* Node Type Pill below label */}
                <text
                  y={35}
                  textAnchor="middle"
                  fill="#64748b"
                  fontSize={8}
                  className="font-mono uppercase tracking-wider"
                >
                  {node.type}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Node Count Footer */}
      <div className="absolute bottom-2 left-3 z-10 text-[10px] text-slate-500 font-mono flex items-center gap-2">
        <span>Nodes: {filteredNodes.length}</span>
        <span>•</span>
        <span>Edges: {filteredEdges.length}</span>
        <span>•</span>
        <span className="flex items-center gap-1">
          <Eye className="w-2.5 h-2.5" /> Click node to inspect
        </span>
      </div>
    </div>
  );
};
