import type React from 'react';
import { useState } from 'react';

export interface GraphNode {
  id: string;
  label?: string;
  type?: string;
  color?: string;
  page?: number;
  properties?: Record<string, any>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship?: string;
  label?: string;
}

export interface ActiveSubgraphCardProps {
  nodes?: GraphNode[];
  edges?: GraphEdge[];
  queryType?: string | null;
  cypherStatus?: string | null;
  traceabilityScore?: number | null;
  onSelectNode?: (node: GraphNode) => void;
  className?: string;
}

export const ActiveSubgraphCard: React.FC<ActiveSubgraphCardProps> = ({
  nodes = [],
  edges = [],
  queryType,
  cypherStatus,
  traceabilityScore,
  onSelectNode,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  if (nodes.length === 0 && edges.length === 0 && !queryType) {
    return null;
  }

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);

  return (
    <div
      data-testid="active-subgraph-card"
      className={`rounded-xl border border-indigo-200/80 dark:border-indigo-500/20 bg-indigo-50/40 dark:bg-indigo-950/20 p-3 text-xs transition-all ${className}`}
    >
      {/* Header Bar */}
      <div className="flex items-center justify-between gap-2 select-none">
        <div className="flex items-center gap-2 min-w-0">
          <span className="w-2 h-2 rounded-full bg-indigo-500 shrink-0" />
          <span className="font-semibold text-slate-800 dark:text-slate-200">
            GraphRAG Knowledge Subgraph
          </span>
          <span className="text-[11px] px-2 py-0.5 rounded-md bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 font-mono">
            {nodes.length} nodes • {edges.length} edges
          </span>
        </div>

        <button
          type="button"
          onClick={() => setIsExpanded((prev) => !prev)}
          className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline font-medium cursor-pointer shrink-0"
        >
          {isExpanded ? 'Collapse' : 'Explore Subgraph'}
        </button>
      </div>

      {/* Metadata metrics pills */}
      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
        {queryType && (
          <span className="px-2 py-0.5 rounded bg-slate-200/70 dark:bg-white/10 text-slate-700 dark:text-slate-300">
            Intent: <strong className="font-medium">{queryType}</strong>
          </span>
        )}
        {cypherStatus && (
          <span className="px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300">
            Cypher: {cypherStatus}
          </span>
        )}
        {typeof traceabilityScore === 'number' && (
          <span className="px-2 py-0.5 rounded bg-indigo-100/80 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300">
            Traceability: {Math.round(traceabilityScore * 100)}%
          </span>
        )}
      </div>

      {/* Expanded Entity List / Node chips */}
      {isExpanded && (
        <div className="mt-3 space-y-2 pt-2 border-t border-indigo-200/60 dark:border-indigo-500/20 animate-in fade-in duration-150">
          <div className="text-[11px] font-medium text-slate-600 dark:text-slate-400">
            Traversed Entities:
          </div>
          <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto pr-1">
            {nodes.map((node) => {
              const isSelected = selectedNodeId === node.id;
              return (
                <button
                  key={node.id}
                  type="button"
                  onClick={() => {
                    setSelectedNodeId(isSelected ? null : node.id);
                    if (onSelectNode) onSelectNode(node);
                  }}
                  className={`px-2 py-1 rounded-lg text-[11px] transition-all cursor-pointer border ${
                    isSelected
                      ? 'bg-indigo-600 text-white border-indigo-700 shadow-xs'
                      : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:border-indigo-400'
                  }`}
                >
                  <span className="font-medium">{node.label || node.id}</span>
                  {node.type && <span className="ml-1 opacity-70 text-[10px]">({node.type})</span>}
                </button>
              );
            })}
          </div>

          {/* Node detail inspector */}
          {selectedNode && (
            <div className="mt-2 p-2.5 rounded-lg bg-white dark:bg-[#12141d] border border-indigo-200 dark:border-indigo-900/50 text-[11px] space-y-1">
              <div className="font-semibold text-slate-900 dark:text-white">
                {selectedNode.label || selectedNode.id}
              </div>
              {selectedNode.properties?.text_preview && (
                <p className="text-slate-600 dark:text-slate-400 italic line-clamp-3">
                  "{selectedNode.properties.text_preview}"
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
