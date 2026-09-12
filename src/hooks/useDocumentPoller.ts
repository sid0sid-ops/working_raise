import { useCallback, useEffect, useRef, useState } from 'react';
import { sourceService } from '../services/SourceService';
import { DocumentIngestionPhase, DocumentStatusResponse } from '../types';

export interface DocumentPollState {
  phase: DocumentIngestionPhase;
  percent: number;
  detail?: string;
  isPolling: boolean;
  isError: boolean;
}

const TERMINAL_PHASES: DocumentIngestionPhase[] = ['ready', 'error'];

/**
 * Polls GET /api/documents/{id}/status every `intervalMs` milliseconds.
 *
 * - Starts polling when `docId` is non-null.
 * - Stops automatically when phase reaches 'ready' or 'error'.
 * - Cancels cleanly on unmount via AbortController.
 * - `onComplete` fires once when the terminal phase is reached.
 *
 * @param docId        The document ID returned by the upload POST.  Pass `null` to skip.
 * @param intervalMs   Poll cadence in ms (default 2500).
 * @param onComplete   Optional callback invoked with the final status.
 */
export function useDocumentPoller(
  docId: string | null,
  intervalMs = 2500,
  onComplete?: (final: DocumentStatusResponse) => void
): DocumentPollState {
  const [state, setState] = useState<DocumentPollState>({
    phase: 'uploading',
    percent: 0,
    detail: undefined,
    isPolling: false,
    isError: false,
  });

  // Stable ref so the interval closure always sees the latest callback
  const onCompleteRef = useRef(onComplete);
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  const stopRef = useRef(false);

  const startPolling = useCallback(
    (id: string) => {
      stopRef.current = false;
      const abortCtrl = new AbortController();

      setState({ phase: 'uploading', percent: 0, detail: undefined, isPolling: true, isError: false });

      let timerId: ReturnType<typeof setInterval> | undefined;

      const tick = async () => {
        if (stopRef.current) return;

        const res = await sourceService.getDocumentStatus(id, abortCtrl.signal);

        if (abortCtrl.signal.aborted || stopRef.current) return;

        if (res.error || !res.data) {
          // On network error keep the previous state and retry next tick
          return;
        }

        const data = res.data;

        setState({
          phase: data.phase,
          percent: data.percent,
          detail: data.detail,
          isPolling: !TERMINAL_PHASES.includes(data.phase),
          isError: data.phase === 'error',
        });

        if (TERMINAL_PHASES.includes(data.phase)) {
          stopRef.current = true;
          if (timerId !== undefined) clearInterval(timerId);
          onCompleteRef.current?.(data);
        }
      };

      // Fire immediately on start, then on interval
      tick();
      timerId = setInterval(tick, intervalMs);

      return () => {
        stopRef.current = true;
        if (timerId !== undefined) clearInterval(timerId);
        abortCtrl.abort();
      };
    },
    [intervalMs]
  );

  useEffect(() => {
    if (!docId) {
      setState({ phase: 'uploading', percent: 0, detail: undefined, isPolling: false, isError: false });
      return;
    }
    const cleanup = startPolling(docId);
    return () => {
      stopRef.current = true;
      cleanup?.();
    };
  }, [docId, startPolling]);

  return state;
}
