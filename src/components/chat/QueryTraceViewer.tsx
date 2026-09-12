import React, { useState } from 'react';
import { SubgraphQueryResponse } from '../../types';

export interface QueryTraceViewerProps {
  response?: Partial<SubgraphQueryResponse>;
}

export const QueryTraceViewer: React.FC<QueryTraceViewerProps> = ({ response }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!response) return null;

  const {
    intent_route,
    routing_strategy,
    standalone_query,
    decomposed_queries,
    subgraph,
    top_chunks,
    traceability_score,
    execution_time,
    latency_sec,
    cypher_status,
  } = response;

  const totalLatency = latency_sec || execution_time || 0;
  const nodesCount = subgraph?.nodes?.length || 0;
  const edgesCount = subgraph?.edges?.length || 0;
  const chunksCount = top_chunks?.length || 0;

  return (
    <div className="query-trace-viewer mt-3 pt-2.5 border-t border-slate-200/60 dark:border-white/[0.05]">
      {/* Collapsible Trigger Button */}
      <button
        type="button"
        aria-label="Toggle query trace details"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center gap-2 text-xs font-medium text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 transition-colors cursor-pointer select-none"
      >
        <svg
          className={`w-3.5 h-3.5 transition-transform duration-200 ${isOpen ? 'rotate-90 text-indigo-600 dark:text-indigo-400' : ''}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
        <span>GraphRAG Pipeline Trace</span>
        {intent_route && (
          <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-indigo-50 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 border border-indigo-200/80 dark:border-indigo-500/30">
            {intent_route}
          </span>
        )}
        {totalLatency > 0 && (
          <span className="text-[10px] font-mono text-slate-400">
            • {totalLatency.toFixed(1)}s
          </span>
        )}
      </button>

      {/* Trace Details Drawer */}
      {isOpen && (
        <div className="mt-3 p-3 rounded-xl bg-slate-50/80 dark:bg-[#0f111a] border border-slate-200/80 dark:border-white/[0.08] text-xs space-y-3 animate-in fade-in-50">
          {/* Node 1 & 2: Routing & Coreference */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-[11px] font-semibold text-slate-700 dark:text-slate-300">
              <span>Node 1 & 2: Intent & Disambiguation</span>
              <span className="font-mono text-[10px] text-slate-500">
                Route: {intent_route || routing_strategy || 'Local Graph Cypher'}
              </span>
            </div>
            {standalone_query && (
              <div className="p-2 rounded bg-white dark:bg-[#151928] border border-slate-200 dark:border-white/10 text-slate-800 dark:text-slate-200 text-[11px]">
                <span className="text-slate-400 dark:text-slate-500 block text-[10px] uppercase font-mono">Standalone Query:</span>
                <p className="mt-0.5">{standalone_query}</p>
              </div>
            )}
          </div>

          {/* Node 3: Query Decomposer Sub-queries */}
          {decomposed_queries && decomposed_queries.length > 0 && (
            <div className="space-y-1">
              <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 block">
                Node 3: Decomposed Sub-Queries ({decomposed_queries.length})
              </span>
              <div className="space-y-1">
                {decomposed_queries.map((subQ, idx) => (
                  <div
                    key={idx}
                    className="p-1.5 rounded bg-white dark:bg-[#151928] border border-slate-200 dark:border-white/10 text-[11px] text-slate-800 dark:text-slate-200 flex items-start gap-2"
                  >
                    <span className="text-indigo-600 dark:text-indigo-400 font-mono text-[10px] mt-0.5">#{idx + 1}</span>
                    <span>{subQ}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Node 4: Parallel Substrates Evidence */}
          <div className="space-y-1">
            <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 block">
              Node 4: Parallel Storage Substrates
            </span>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <div className="p-2 rounded bg-white dark:bg-[#151928] border border-slate-200 dark:border-white/10">
                <span className="text-[10px] text-slate-500 font-mono block">ChromaDB BGE-Large</span>
                <span className="font-semibold text-slate-900 dark:text-slate-100">{chunksCount} vector chunks</span>
              </div>
              <div className="p-2 rounded bg-white dark:bg-[#151928] border border-slate-200 dark:border-white/10">
                <span className="text-[10px] text-slate-500 font-mono block">Neo4j Graph (bolt)</span>
                <span className="font-semibold text-slate-900 dark:text-slate-100">{nodesCount} nodes • {edgesCount} edges</span>
              </div>
              <div className="p-2 rounded bg-white dark:bg-[#151928] border border-slate-200 dark:border-white/10 col-span-2 sm:col-span-1">
                <span className="text-[10px] text-slate-500 font-mono block">Cypher Execution</span>
                <span className="font-semibold text-emerald-600 dark:text-emerald-400">{cypher_status || 'OPTIMIZED'}</span>
              </div>
            </div>
          </div>

          {/* Node 5: Synthesis Telemetry */}
          <div className="flex items-center justify-between pt-1 text-[11px] text-slate-500 dark:text-slate-400 font-mono border-t border-slate-200/60 dark:border-white/[0.05]">
            <span>Inference: {routing_strategy ? `${routing_strategy} (LLM)` : 'GraphRAG Synthesis'}</span>
            <span>Traceability: {Math.round((traceability_score || 0) * 100)}%</span>
          </div>
        </div>
      )}
    </div>
  );
};
