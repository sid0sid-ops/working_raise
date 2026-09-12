import React, { useEffect, useState } from 'react';

/**
 * Mapping table from backend stages to user-friendly thoughts.
 */
export const STAGE_THOUGHT_MAP: Record<string, string> = {
  RECEIVED: 'Analyzing your question...',
  ROUTING: 'Analyzing your question...',
  QUERY_DECOMPOSITION: 'Structuring research topics...',
  VECTOR_RETRIEVAL: 'Searching attached documents...',
  GRAPH_RETRIEVAL: 'Exploring concept relationships in knowledge graph...',
  FUSION: 'Finding the most relevant evidence...',
  RERANKING: 'Finding the most relevant evidence...',
  SYNTHESIS: 'Synthesizing research findings...',
};

export const RESEARCH_STEPS = [
  { key: 'ROUTING', label: 'Analyzing your question...' },
  { key: 'QUERY_DECOMPOSITION', label: 'Structuring research topics...' },
  { key: 'VECTOR_RETRIEVAL', label: 'Searching attached documents...' },
  { key: 'GRAPH_RETRIEVAL', label: 'Exploring concept relationships in knowledge graph...' },
  { key: 'FUSION', label: 'Finding the most relevant evidence...' },
  { key: 'SYNTHESIS', label: 'Synthesizing research findings...' },
];

export interface QueryLifecycleTrackerProps {
  query?: string;
  stage?: string;
  onAbort?: () => void;
  decomposedQueries?: string[];
  isComplete?: boolean;
  durationSec?: number;
}

/**
 * Resolves the active friendly status phrase from either an explicit stage
 * or the elapsed time during autonomous pipeline execution.
 */
export function getFriendlyThought(stage?: string, elapsedSec = 0): string {
  if (stage) {
    const normalized = stage.toUpperCase().trim();
    if (STAGE_THOUGHT_MAP[normalized]) {
      return STAGE_THOUGHT_MAP[normalized];
    }
  }

  if (elapsedSec >= 3.5) {
    return STAGE_THOUGHT_MAP.SYNTHESIS;
  }
  if (elapsedSec >= 2.8) {
    return STAGE_THOUGHT_MAP.FUSION;
  }
  if (elapsedSec >= 2.1) {
    return STAGE_THOUGHT_MAP.GRAPH_RETRIEVAL;
  }
  if (elapsedSec >= 1.4) {
    return STAGE_THOUGHT_MAP.VECTOR_RETRIEVAL;
  }
  if (elapsedSec >= 0.7) {
    return STAGE_THOUGHT_MAP.QUERY_DECOMPOSITION;
  }
  return STAGE_THOUGHT_MAP.ROUTING;
}

/**
 * Active Thinking UI:
 * Subtle, pulsing status indicator with active friendly phrase without technical jargon prefixes.
 * E.g. `✦ Exploring concept relationships in knowledge graph... (0.4s)`
 */
export const QueryLifecycleTracker: React.FC<QueryLifecycleTrackerProps> = ({
  query,
  stage,
  onAbort: _onAbort,
  decomposedQueries: _decomposedQueries,
  isComplete,
  durationSec,
}) => {
  const [elapsedSec, setElapsedSec] = useState<number>(0);

  useEffect(() => {
    if (isComplete) return;

    const startTime = Date.now();
    const timer = setInterval(() => {
      const elapsed = (Date.now() - startTime) / 1000;
      setElapsedSec(parseFloat(elapsed.toFixed(1)));
    }, 100);

    return () => clearInterval(timer);
  }, [isComplete]);

  if (isComplete) {
    return <ResearchStepsAccordion executionTimeSec={durationSec ?? elapsedSec} />;
  }

  const activeThought = getFriendlyThought(stage, elapsedSec);

  return (
    <div
      className="query-lifecycle-tracker inline-flex items-center gap-2 py-1 px-1 text-xs text-slate-500 dark:text-slate-400 select-none animate-in fade-in duration-200"
      data-testid="query-lifecycle-tracker"
      role="status"
      aria-live="polite"
    >
      {/* Subtle pulsing status glyph */}
      <span
        className="text-indigo-600 dark:text-indigo-400 animate-pulse text-sm font-semibold select-none shrink-0"
        aria-hidden="true"
      >
        ✦
      </span>

      {/* Active human-readable thought label */}
      <span className="font-medium text-slate-700 dark:text-slate-200 tracking-tight">
        {activeThought}
      </span>

      {/* Elapsed seconds timer */}
      <span className="text-slate-400 dark:text-slate-500 font-mono text-[11px] shrink-0">
        ({elapsedSec.toFixed(1)}s)
      </span>

      {/* Screen-reader accessible context */}
      <div className="sr-only">
        {query && <span>Query: {query}. </span>}
        <span>Current research step: {activeThought}</span>
      </div>
    </div>
  );
};

/**
 * Formats elapsed duration into human-readable seconds or milliseconds:
 * - When < 1s and > 0, outputs e.g. "450ms"
 * - When >= 1s, outputs e.g. "1.8s"
 */
export function formatThoughtDuration(durationSec: number): string {
  if (typeof durationSec !== 'number' || isNaN(durationSec) || durationSec <= 0) {
    return '0.0s';
  }
  if (durationSec < 1) {
    return `${Math.round(durationSec * 1000)}ms`;
  }
  return `${durationSec.toFixed(1)}s`;
}

export interface ThoughtDurationProps {
  executionTimeSec: number;
  className?: string;
}

/**
 * Clean completed thinking indicator:
 * Once the answer is received from the backend, shows only the execution time.
 * No "View research steps" or "Hide research steps" buttons or expandable dropdowns.
 */
export const ThoughtDuration: React.FC<ThoughtDurationProps> = ({
  executionTimeSec,
  className = '',
}) => {
  const formattedTime = formatThoughtDuration(executionTimeSec);

  return (
    <div
      className={`thought-duration flex items-center gap-1.5 mb-2 ml-0.5 text-xs text-slate-500 dark:text-slate-400 select-none animate-in fade-in duration-200 ${className}`}
      data-testid="thought-duration"
    >
      <span className="text-indigo-500 dark:text-indigo-400 text-xs shrink-0" aria-hidden="true">
        ✦
      </span>
      <span className="font-medium text-slate-600 dark:text-slate-300">
        Thought for {formattedTime}
      </span>
    </div>
  );
};

// Aliases for backwards compatibility
export const ResearchStepsAccordion = ThoughtDuration;
export const ThoughtDurationIndicator = ThoughtDuration;
