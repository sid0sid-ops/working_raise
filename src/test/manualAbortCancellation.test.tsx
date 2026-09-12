import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ResponseStoppedBanner, BackendErrorCard, BackendErrorDetails } from '../components/chat/BackendErrorCard';
import RaisePage from '../features/raise/RaisePage';
import { chatService } from '../services/ChatService';
import { mockAdapter } from '../mocks/mockAdapter';
import { setApiMode } from '../app/config';

describe('Manual Query Abort & Cancellation Handling', () => {
  beforeEach(() => {
    mockAdapter.resetScenario();
    setApiMode('mock');
    vi.clearAllMocks();
  });

  describe('ResponseStoppedBanner & BackendErrorCard Abort Mapping', () => {
    it('renders clean "Response stopped." state with retry button and no critical error artifacts', () => {
      const handleRetry = vi.fn();
      render(<ResponseStoppedBanner onRetry={handleRetry} />);

      // Friendly label is shown
      expect(screen.getByText('Response stopped.')).toBeInTheDocument();
      // Retry button is available and works
      const retryBtn = screen.getByRole('button', { name: /retry/i });
      expect(retryBtn).toBeInTheDocument();
      fireEvent.click(retryBtn);
      expect(handleRetry).toHaveBeenCalledTimes(1);

      // Critical error terminology is completely absent
      expect(screen.queryByText(/offline/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/query execution aborted/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/configure gateway/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/full error payload/i)).not.toBeInTheDocument();
    });

    it('BackendErrorCard maps client abort to ResponseStoppedBanner without displaying OFFLINE or gateway settings', () => {
      const abortError: BackendErrorDetails = {
        title: 'Response stopped',
        message: 'Response stopped.',
        isAborted: true,
        isOffline: false,
      };

      const handleRetry = vi.fn();
      const handleOpenSettings = vi.fn();

      render(
        <BackendErrorCard
          error={abortError}
          targetUrl="http://localhost:8000"
          onRetry={handleRetry}
          onOpenSettings={handleOpenSettings}
        />
      );

      // Must display Response stopped.
      expect(screen.getByText('Response stopped.')).toBeInTheDocument();

      // Must NOT display OFFLINE badge or Configure Gateway button
      expect(screen.queryByText('OFFLINE')).not.toBeInTheDocument();
      expect(screen.queryByText(/configure gateway & tunnel/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/full error payload/i)).not.toBeInTheDocument();

      // Retry button still functions
      const retryBtn = screen.getByRole('button', { name: /retry/i });
      fireEvent.click(retryBtn);
      expect(handleRetry).toHaveBeenCalledTimes(1);
    });

    it('BackendErrorCard still displays full diagnostic error for real network/server failures', () => {
      const realNetworkError: BackendErrorDetails = {
        title: 'FastAPI Gateway Unreachable (Port 8000)',
        message: 'Failed to connect to RAISE Gateway at http://localhost:8000/query_subgraph.',
        cause: 'Windows workstation is offline, FastAPI is stopped, or Windows Firewall is blocking port 8000.',
        action: 'Start the backend on Windows: uvicorn app:app --host 0.0.0.0 --port 8000.',
        isOffline: true,
        isAborted: false,
      };

      const handleRetry = vi.fn();
      const handleOpenSettings = vi.fn();

      render(
        <BackendErrorCard
          error={realNetworkError}
          targetUrl="http://localhost:8000"
          onRetry={handleRetry}
          onOpenSettings={handleOpenSettings}
        />
      );

      // Must display the real error UI
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('FastAPI Gateway Unreachable (Port 8000)')).toBeInTheDocument();
      expect(screen.getByText('OFFLINE')).toBeInTheDocument();
      expect(screen.getByText(/Windows workstation is offline/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /configure gateway & tunnel/i })).toBeInTheDocument();
    });
  });

  describe('RaisePage Stop Button & Active Stream Cancellation', () => {
    it('shows "Response stopped." state and retains partial streamed tokens when user clicks Stop', async () => {
      // Mock streaming query that hangs until aborted
      vi.spyOn(chatService, 'querySubgraph').mockImplementation((_payload, signal, streamCb) => {
        return new Promise((_resolve, reject) => {
          // Stream some partial text
          if (streamCb) {
            streamCb('Partial answer received', 'Partial answer received before stop.');
          }

          if (signal?.aborted) {
            const abortErr = new DOMException('The user aborted a request.', 'AbortError');
            reject(abortErr);
            return;
          }

          signal?.addEventListener('abort', () => {
            const abortErr = new DOMException('The user aborted a request.', 'AbortError');
            reject(abortErr);
          });
        });
      });

      render(<RaisePage />);

      // Type a query using combobox role
      const textarea = screen.getByRole('combobox');
      fireEvent.change(textarea, { target: { value: 'Explain XYMA sensor architecture' } });

      // Click Send button
      const sendButton = screen.getByRole('button', { name: /execute rag query/i });
      fireEvent.click(sendButton);

      // Verify that send button changes to Stop button while loading
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /stop generating query process/i })).toBeInTheDocument();
      });

      // User clicks Stop/Abort button
      const stopButton = screen.getByRole('button', { name: /stop generating query process/i });
      fireEvent.click(stopButton);

      // Verify user sees "Response stopped." rather than a critical error state
      await waitFor(() => {
        expect(screen.getByText('Response stopped.')).toBeInTheDocument();
      });

      // Verify partial streamed text is retained in the UI
      expect(screen.getByText(/Partial answer received before stop\./i)).toBeInTheDocument();

      // Verify NO critical error, OFFLINE, or Gateway settings button is displayed
      expect(screen.queryByText(/offline/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Query Execution Aborted/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/configure gateway & tunnel/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/full error payload/i)).not.toBeInTheDocument();

      // Verify "Retry" button is available in the stopped banner
      expect(screen.getByRole('button', { name: /retry response/i })).toBeInTheDocument();
    });
  });
});
