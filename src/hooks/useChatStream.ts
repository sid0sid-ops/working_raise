import { useCallback, useEffect, useRef, useState } from 'react';
import { apiClient } from '../api/client';
import { ENDPOINTS } from '../api/endpoints';
import { Citation, SubgraphQueryResponse, SubgraphQueryRequest } from '../types';
import { getApiMode } from '../app/config';
import { chatService } from '../services/ChatService';

// ─── State machine ─────────────────────────────────────────────────────────────

export type ChatStreamPhase =
  | 'idle'        // nothing happening
  | 'thinking'    // waiting for first token (graph traversal)
  | 'streaming'   // tokens arriving
  | 'done'        // complete
  | 'error'       // terminal error
  | 'cancelled';  // aborted by user

export interface ChatStreamState {
  phase: ChatStreamPhase;
  /** Original user query submitted */
  query: string | null;
  /** Active backend request ID (X-Request-ID / request_id) */
  requestId: string | null;
  /** Active session / thread ID */
  sessionId: string | null;
  /** Accumulated answer text so far */
  text: string;
  /** Citations revealed so far (added progressively as they arrive) */
  citations: Citation[];
  /** Final complete response (set when phase = 'done') */
  finalResponse: SubgraphQueryResponse | null;
  /** Error message if phase = 'error' */
  errorMessage: string | null;
  /** Routing label emitted by backend e.g. "LOCAL_GRAPH_CYPHER" */
  routingStrategy: string | null;
  /** Elapsed ms since query submitted (updates every second while not done) */
  elapsedMs: number;
  /** Quality gate decision emitted by backend ('accept' | 'retry' | 'reject' | null) */
  qualityGateDecision: string | null;
  /** Whether the server-side abort POST is currently in flight */
  isAbortingServer: boolean;
  /** Confirmation flag that server terminated the inference job */
  abortConfirmed: boolean;
  /** Server abort message */
  abortMessage: string | null;
}

// ─── SSE event shapes from backend ────────────────────────────────────────────

interface SseStartEvent {
  event: 'start';
  data: {
    chat_id?: string;
    query?: string;
    request_id?: string;
    session_id?: string;
  };
}
interface SseRoutingEvent  { event: 'routing';      data: { strategy?: string; intent?: string } }
interface SseTokenEvent    { event: 'token';         data: { token: string } }
interface SseCitationEvent { event: 'citation';     data: { citations: Partial<Citation>[] } }
interface SseQGateEvent    { event: 'quality_gate'; data: { decision?: string; faithfulness?: number; numerical_mismatches?: number } }
interface SseDoneEvent     { event: 'done';         data: { execution_time?: number; traceability_score?: number; subgraph?: any; verified_claims?: any[]; top_chunks?: any[] } }
interface SseErrorEvent    { event: 'error';        data: { message?: string } }

type SseEvent =
  | SseStartEvent | SseRoutingEvent | SseTokenEvent | SseCitationEvent
  | SseQGateEvent | SseDoneEvent | SseErrorEvent;

// ─── Mock SSE token simulation ─────────────────────────────────────────────────

const MOCK_TOKENS = [
  'The ', 'retrieval-augmented ', 'generation ', 'pipeline ', 'synthesizes ', 'verified ',
  'knowledge ', 'from ', 'the ', 'indexed ', 'knowledge ', 'base ', '[1]', '. ',
  'Retrieved ', 'passages ', 'undergo ', 'subgraph ', 'traversal ', 'and ', 'cross-encoder ',
  'reranking ', 'to ', 'ensure ', 'grounded ', 'factual ', 'precision ', '[2]', '. ',
  'Attributed ', 'sources ', 'and ', 'verification ', 'traces ', 'are ', 'linked ',
  'directly ', 'to ', 'the ', 'citations ', '[3]', '.',
];

const MOCK_CITATIONS: Citation[] = [
  { citation_index: 1, chunk_id: 'c1', document_id: 'doc-1', pdf_filename: 'Knowledge Base Overview.pdf', primary_page: 1, heading: 'System Overview', plain_text: 'Knowledge synthesis is grounded in indexed reference documents.', university: 'Knowledge Substrate', similarity: 0.98 },
  { citation_index: 2, chunk_id: 'c2', document_id: 'doc-2', pdf_filename: 'Pipeline Architecture.pdf', primary_page: 4, heading: 'Subgraph Retrieval', plain_text: 'Subgraph traversal validates entity relationships across retrieved context.', university: 'Knowledge Substrate', similarity: 0.92 },
  { citation_index: 3, chunk_id: 'c3', document_id: 'doc-3', pdf_filename: 'Verification Framework.pdf', primary_page: 7, heading: 'Claim Verification', plain_text: 'Cross-encoder scoring verifies factual attribution against source passages.', university: 'Knowledge Substrate', similarity: 0.89 },
];

async function* mockSseStream(
  query: string,
  requestId: string,
  sessionId: string
): AsyncGenerator<SseEvent> {
  yield {
    event: 'start',
    data: {
      chat_id: sessionId,
      session_id: sessionId,
      request_id: requestId,
      query,
    },
  };
  await sleep(400);

  yield { event: 'routing', data: { strategy: 'LOCAL_GRAPH_CYPHER', intent: 'RELATIONSHIP_QUERY' } };
  // Simulate "thinking" time — no tokens yet
  await sleep(1200);

  for (const token of MOCK_TOKENS) {
    yield { event: 'token', data: { token } };
    // Reveal first citation badge right when [1] appears
    if (token === ' [1]') {
      await sleep(80);
      yield { event: 'citation', data: { citations: [MOCK_CITATIONS[0]] } };
    } else if (token === ' [2]') {
      await sleep(80);
      yield { event: 'citation', data: { citations: [MOCK_CITATIONS[1]] } };
    } else if (token === ' [3]') {
      await sleep(80);
      yield { event: 'citation', data: { citations: [MOCK_CITATIONS[2]] } };
    }
    await sleep(40 + Math.random() * 60);
  }

  yield { event: 'quality_gate', data: { decision: 'accept', faithfulness: 0.97, numerical_mismatches: 0 } };
  yield {
    event: 'done',
    data: { execution_time: 6.4, traceability_score: 0.96, subgraph: { nodes: [], edges: [] }, verified_claims: [], top_chunks: [] },
  };
}

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

// ─── Real SSE parser ───────────────────────────────────────────────────────────

/**
 * Turns raw SSE text (with "data: ..." lines) into typed SseEvent objects.
 * Handles partial chunks — accumulates until a double-newline.
 */
function parseSseChunk(raw: string, buffer: { buf: string }): SseEvent[] {
  buffer.buf += raw;
  const events: SseEvent[] = [];
  const blocks = buffer.buf.split(/\n\n+/);
  // Last block may be incomplete — keep it in buffer
  buffer.buf = blocks.pop() ?? '';

  for (const block of blocks) {
    let eventType = 'message';
    let dataStr = '';
    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) eventType = line.slice(6).trim();
      if (line.startsWith('data:'))  dataStr  = line.slice(5).trim();
    }
    if (!dataStr || dataStr === '[DONE]') continue;
    try {
      const parsed = JSON.parse(dataStr);
      events.push({ event: eventType as SseEvent['event'], data: parsed });
    } catch {
      // malformed chunk — skip
    }
  }
  return events;
}

// ─── Hook ──────────────────────────────────────────────────────────────────────

export interface UseChatStreamReturn {
  state: ChatStreamState;
  submit: (req: SubgraphQueryRequest) => void;
  abort: () => void;
  reset: () => void;
}

const INITIAL_STATE: ChatStreamState = {
  phase: 'idle',
  query: null,
  requestId: null,
  sessionId: null,
  text: '',
  citations: [],
  finalResponse: null,
  errorMessage: null,
  routingStrategy: null,
  elapsedMs: 0,
  qualityGateDecision: null,
  isAbortingServer: false,
  abortConfirmed: false,
  abortMessage: null,
};

export function useChatStream(): UseChatStreamReturn {
  const [state, setState] = useState<ChatStreamState>(INITIAL_STATE);
  const abortRef = useRef<AbortController | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startMsRef = useRef<number>(0);
  const currentRequestIdRef = useRef<string | null>(null);
  const currentSessionIdRef = useRef<string | null>(null);
  const currentQueryRef = useRef<string | null>(null);

  // ── Elapsed timer ──────────────────────────────────────────────────────────
  const startTimer = () => {
    startMsRef.current = Date.now();
    timerRef.current = setInterval(() => {
      setState((s) => ({ ...s, elapsedMs: Date.now() - startMsRef.current }));
    }, 500);
  };

  const stopTimer = () => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  };

  useEffect(() => () => { stopTimer(); abortRef.current?.abort(); }, []);

  // ── Abort ──────────────────────────────────────────────────────────────────
  const abort = useCallback(async () => {
    // 1. Abort local fetch immediately
    abortRef.current?.abort();
    stopTimer();

    const reqId = currentRequestIdRef.current;
    const sessId = currentSessionIdRef.current;

    setState((s) =>
      s.phase !== 'idle' && s.phase !== 'done'
        ? {
            ...s,
            phase: 'cancelled',
            isAbortingServer: Boolean(reqId),
            abortConfirmed: false,
          }
        : s
    );

    // 2. Send server-side cancellation POST /api/chat/abort with { request_id, session_id }
    if (reqId) {
      try {
        const abortRes = await chatService.abortChat({
          request_id: reqId,
          session_id: sessId || undefined,
        });

        setState((s) => ({
          ...s,
          isAbortingServer: false,
          abortConfirmed: abortRes.status >= 200 && abortRes.status < 300,
          abortMessage:
            abortRes.data?.message ||
            `Server inference job for ${reqId} successfully terminated.`,
        }));
      } catch (err: any) {
        setState((s) => ({
          ...s,
          isAbortingServer: false,
          abortConfirmed: false,
          abortMessage: err?.message || 'Server-side abort request failed.',
        }));
      }
    }
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    stopTimer();
    currentRequestIdRef.current = null;
    currentSessionIdRef.current = null;
    currentQueryRef.current = null;
    setState(INITIAL_STATE);
  }, []);

  // ── Submit ─────────────────────────────────────────────────────────────────
  const submit = useCallback((req: SubgraphQueryRequest) => {
    // Cancel previous in-flight request
    abortRef.current?.abort();
    stopTimer();

    const controller = new AbortController();
    abortRef.current = controller;

    const requestId = `req-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    const sessionId = req.thread_id || `sess-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    currentRequestIdRef.current = requestId;
    currentSessionIdRef.current = sessionId;
    currentQueryRef.current = req.query;

    setState({
      ...INITIAL_STATE,
      phase: 'thinking',
      query: req.query,
      requestId,
      sessionId,
      elapsedMs: 0,
    });
    startTimer();

    const run = async () => {
      try {
        const isMock = getApiMode() === 'mock';

        if (isMock) {
          // ── Mock path ──────────────────────────────────────────────────────
          for await (const evt of mockSseStream(req.query, requestId, sessionId)) {
            if (controller.signal.aborted) return;
            handleSseEvent(evt, controller.signal);
          }
        } else {
          // ── Real SSE path ──────────────────────────────────────────────────
          const effectiveMode = req.mode || (req.hops && req.hops > 1 ? 'expert' : 'fast');
          const buffer = { buf: '' };

          await apiClient.requestStream(
            ENDPOINTS.CHAT,
            {
              method: 'POST',
              headers: {
                'X-Request-ID': requestId,
              },
              body: JSON.stringify({
                message: req.query,
                query: req.query,
                request_id: requestId,
                session_id: sessionId,
                mode: effectiveMode,
                stream: true,
                chat_history: req.chat_history,
                hops: req.hops,
                top_k: req.top_k,
                active_docs: req.active_docs || [],
                format: 'raw',
                document_filter: req.document_filter,
              }),
              signal: controller.signal,
              timeoutMs: 90000,
            },
            (tokenChunk, fullAccumulated) => {
              // Try parsing as typed SSE events first (if raw SSE events are present)
              const events = parseSseChunk(tokenChunk, buffer);
              if (events.length > 0) {
                for (const evt of events) {
                  if (controller.signal.aborted) return;
                  handleSseEvent(evt, controller.signal);
                }
              } else if (tokenChunk && typeof tokenChunk === 'string') {
                // If already decoded token or plain chunk from apiClient.requestStream
                setState((s) => ({
                  ...s,
                  phase: 'streaming',
                  text: fullAccumulated || s.text + tokenChunk,
                }));
              }
            }
          );

          // If requestStream completed without a 'done' event, synthesise completion
          setState((s) => {
            if (s.phase === 'streaming' || s.phase === 'thinking') {
              stopTimer();
              const finalResponse = buildFinalResponse(req.query, s);
              return { ...s, phase: 'done', finalResponse };
            }
            return s;
          });
        }
      } catch (err: any) {
        if (controller.signal.aborted) return;
        stopTimer();
        setState((s) => ({
          ...s,
          phase: 'error',
          errorMessage: err?.message || 'Unknown streaming error',
        }));
      }
    };

    run();

    // ── SSE event handler (shared between mock and real) ─────────────────────
    function handleSseEvent(evt: SseEvent, signal: AbortSignal) {
      if (signal.aborted) return;

      switch (evt.event) {
        case 'start': {
          const sId = evt.data.session_id || evt.data.chat_id;
          const rId = evt.data.request_id;
          if (sId) currentSessionIdRef.current = sId;
          if (rId) currentRequestIdRef.current = rId;
          setState((s) => ({
            ...s,
            sessionId: sId || s.sessionId,
            requestId: rId || s.requestId,
          }));
          break;
        }

        case 'routing':
          setState((s) => ({ ...s, routingStrategy: evt.data.strategy ?? null }));
          break;

        case 'token':
          setState((s) => ({
            ...s,
            phase: 'streaming',
            text: s.text + (evt.data.token ?? ''),
          }));
          break;

        case 'citation': {
          const incoming = (evt.data.citations ?? []) as Partial<Citation>[];
          setState((s) => {
            const existing = new Set(s.citations.map((c) => c.citation_index));
            const newCitations = incoming
              .filter((c) => c.citation_index !== undefined && !existing.has(c.citation_index!))
              .map((c) => ({
                citation_index: c.citation_index!,
                chunk_id:       c.chunk_id        ?? `cit-${c.citation_index}`,
                document_id:    c.document_id     ?? '',
                pdf_filename:   c.pdf_filename     ?? '',
                primary_page:   c.primary_page     ?? 1,
                heading:        c.heading          ?? '',
                plain_text:     c.plain_text       ?? '',
                university:     c.university       ?? 'IIT Madras',
                similarity:     c.similarity       ?? 0,
              } as Citation));
            return { ...s, citations: [...s.citations, ...newCitations] };
          });
          break;
        }

        case 'quality_gate':
          setState((s) => ({
            ...s,
            qualityGateDecision: evt.data.decision ?? s.qualityGateDecision,
          }));
          break;

        case 'done': {
          stopTimer();
          setState((s) => {
            const finalResponse = buildFinalResponse(req.query, s, evt.data);
            return { ...s, phase: 'done', finalResponse };
          });
          break;
        }

        case 'error':
          stopTimer();
          setState((s) => ({
            ...s,
            phase: 'error',
            errorMessage: (evt.data as any).message ?? 'Backend streaming error',
          }));
          break;
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { state, submit, abort, reset };
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildFinalResponse(
  query: string,
  s: ChatStreamState,
  doneData?: SseDoneEvent['data']
): SubgraphQueryResponse {
  return {
    query,
    grounded_answer:      s.text,
    citations:            s.citations,
    latency_sec:          doneData?.execution_time ?? s.elapsedMs / 1000,
    execution_time:       doneData?.execution_time ?? s.elapsedMs / 1000,
    traceability_score:   doneData?.traceability_score ?? 0,
    subgraph:             doneData?.subgraph ?? { nodes: [], edges: [] },
    verified_claims:      doneData?.verified_claims ?? [],
    top_chunks:           doneData?.top_chunks ?? [],
    quality_gate_decision: (s.qualityGateDecision as any) || 'accept',
    selected_tools:       [],
    cypher_repair_count:  0,
    path_critic_expanded: false,
    retry_count:          0,
    decomposed_queries:   [],
    routing_strategy:     s.routingStrategy ?? undefined,
  };
}
