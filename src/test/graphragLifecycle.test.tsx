import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryLifecycleTracker, ThoughtDuration } from '../components/chat/QueryLifecycleTracker';
import { BackendErrorCard, BackendErrorDetails } from '../components/chat/BackendErrorCard';
import { QueryTraceViewer } from '../components/chat/QueryTraceViewer';
import { SubgraphQueryResponse } from '../types';

describe('GraphRAG Lifecycle UI & Diagnostic Components', () => {
  describe('QueryLifecycleTracker', () => {
    it('renders clean, human-readable status indicator and eliminates CS jargon', () => {
      render(
        <QueryLifecycleTracker
          query="What ultrasonic waveguide sensors did XYMA develop?"
          stage="GRAPH_RETRIEVAL"
        />
      );

      // Verify human-friendly thought indicator
      expect(screen.getByRole('status')).toHaveTextContent('Exploring concept relationships in knowledge graph...');
      // Verify NO hardcoded computer science jargon or "Stage 1", "Stage 2", "Node 4" prefixes
      expect(screen.queryByText(/Stage 1/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Stage 2/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Query Decomposition & Splitting/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Multi-Substrate/i)).not.toBeInTheDocument();
    });

    it('does NOT render a duplicate stop button near searching/thought (delegates to question box button)', () => {
      render(
        <QueryLifecycleTracker
          query="Test query"
          onAbort={vi.fn()}
        />
      );

      const abortButton = screen.queryByRole('button', { name: /stop/i });
      expect(abortButton).not.toBeInTheDocument();
    });

    it('renders subtle pulsing indicator with active friendly phrase and timer', () => {
      const { container } = render(
        <QueryLifecycleTracker
          query="hello"
          stage="VECTOR_RETRIEVAL"
        />
      );

      expect(screen.getByRole('status')).toHaveTextContent('Searching attached documents...');
      expect(container.querySelector('.animate-pulse')).toBeInTheDocument();

      const tracker = container.querySelector('.query-lifecycle-tracker');
      expect(tracker).toBeInTheDocument();
      expect(tracker?.classList.contains('text-slate-500')).toBe(true);
      expect(container.querySelector('.animate-spin')).toBeNull();
    });

    it('only shows "Thought for __ s" (or ms) when complete, and removes View/Hide research steps button', () => {
      const { rerender } = render(<ThoughtDuration executionTimeSec={2.4} />);

      // Shows thought for duration in seconds
      expect(screen.getByText(/Thought for 2\.4s/i)).toBeInTheDocument();

      // Verifies NO "View research steps" or "Hide research steps" button
      expect(screen.queryByText(/View research steps/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Hide research steps/i)).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /research steps/i })).not.toBeInTheDocument();

      // Verifies NO stage labels shown when complete
      expect(screen.queryByText('Structuring research topics...')).not.toBeInTheDocument();
      expect(screen.queryByText('Exploring concept relationships in knowledge graph...')).not.toBeInTheDocument();

      // Test millisecond formatting for < 1s
      rerender(<ThoughtDuration executionTimeSec={0.45} />);
      expect(screen.getByText(/Thought for 450ms/i)).toBeInTheDocument();
    });
  });

  describe('BackendErrorCard', () => {
    it('renders offline diagnostic error details with actionable checklist', () => {
      const error: BackendErrorDetails = {
        title: 'FastAPI Gateway Unreachable (Port 8000)',
        message: 'Failed to connect to RAISE Gateway at http://localhost:8000/query_subgraph.',
        cause: 'Windows workstation is offline, FastAPI is stopped, or Windows Firewall is blocking port 8000.',
        action: 'Start the backend on Windows: uvicorn app:app --host 0.0.0.0 --port 8000.',
        isOffline: true,
      };

      const handleRetry = vi.fn();
      const handleOpenSettings = vi.fn();

      render(
        <BackendErrorCard
          error={error}
          targetUrl="http://localhost:8000"
          onRetry={handleRetry}
          onOpenSettings={handleOpenSettings}
        />
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('FastAPI Gateway Unreachable (Port 8000)')).toBeInTheDocument();
      expect(screen.getByText(/Windows workstation is offline/i)).toBeInTheDocument();
      expect(screen.getByText(/Start the backend on Windows/i)).toBeInTheDocument();

      const retryBtn = screen.getByRole('button', { name: /retry query/i });
      fireEvent.click(retryBtn);
      expect(handleRetry).toHaveBeenCalledTimes(1);

      const settingsBtn = screen.getByRole('button', { name: /configure gateway/i });
      fireEvent.click(settingsBtn);
      expect(handleOpenSettings).toHaveBeenCalledTimes(1);
    });

    it('renders client abort notification cleanly', () => {
      const error: BackendErrorDetails = {
        title: 'Query Execution Aborted',
        message: 'Request was cancelled locally in the browser.',
        isAborted: true,
      };

      const onRetry = vi.fn();
      render(
        <BackendErrorCard
          error={error}
          targetUrl="http://localhost:8000"
          onRetry={onRetry}
        />
      );

      // Verify friendly "Response stopped." state
      expect(screen.getByText('Response stopped.')).toBeInTheDocument();
      // Verify NO critical error, OFFLINE badge, or Gateway configuration button
      expect(screen.queryByText('Query Execution Aborted')).not.toBeInTheDocument();
      expect(screen.queryByText(/OFFLINE/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Configure Gateway/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Full error payload/i)).not.toBeInTheDocument();

      // Verify Retry button is present and works
      const retryBtn = screen.getByRole('button', { name: /retry/i });
      expect(retryBtn).toBeInTheDocument();
      fireEvent.click(retryBtn);
      expect(onRetry).toHaveBeenCalledTimes(1);
    });
  });

  describe('QueryTraceViewer', () => {
    it('displays telemetry, decomposed sub-queries, and substrate counts', () => {
      const mockResponse: Partial<SubgraphQueryResponse> = {
        grounded_answer: 'Test grounded answer',
        intent_route: 'multi_hop_graph_rag',
        standalone_query: 'What sensors did XYMA develop at IIT Madras?',
        decomposed_queries: [
          'XYMA sensors developed at IIT Madras',
          'Prof. Krishnan Balasubramanian and Prof. Prabhu Rajagopal waveguide sensor patents',
        ],
        latency_sec: 3.4,
        subgraph: {
          nodes: [
            { id: 'n1', label: 'Company', name: 'XYMA Analytics', type: 'Entity', provenance: {} },
            { id: 'n2', label: 'Person', name: 'Prof. Krishnan Balasubramanian', type: 'Entity', provenance: {} },
          ],
          edges: [
            { relationship: 'FOUNDED_BY', source: 'n1', target: 'n2', provenance: {} },
          ],
        },
        top_chunks: [
          {
            chunk_id: 'c1',
            text: 'XYMA analytics sensors',
            similarity: 0.94,
            metadata: {},
          },
        ],
      };

      render(<QueryTraceViewer response={mockResponse} />);

      // Collapsible header should show route and latency
      expect(screen.getByText(/multi_hop_graph_rag/i)).toBeInTheDocument();
      expect(screen.getByText(/3\.4s/i)).toBeInTheDocument();

      // Open collapsible details
      const toggleBtn = screen.getByRole('button', { name: /toggle query trace details/i });
      fireEvent.click(toggleBtn);

      // Verify Node 2 Standalone Query
      expect(screen.getByText('What sensors did XYMA develop at IIT Madras?')).toBeInTheDocument();

      // Verify Node 3 Decomposed Queries
      expect(screen.getByText('XYMA sensors developed at IIT Madras')).toBeInTheDocument();

      // Verify Node 4 Substrates hit count chips
      expect(screen.getByText(/2 nodes • 1 edges/i)).toBeInTheDocument();
      expect(screen.getByText(/1 vector chunks/i)).toBeInTheDocument();
    });
  });
});
