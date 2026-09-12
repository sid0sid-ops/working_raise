import graphragSuccessFixture from './fixtures/graphrag_success_xyma.json';
import emptyWorkspaceFixture from './fixtures/empty_workspace.json';
import unableToVerifyFixture from './fixtures/unable_to_verify_refusal.json';
import documentsListFixture from './fixtures/documents_list.json';
import uploadSuccessFixture from './fixtures/upload_success.json';
import deleteSuccessFixture from './fixtures/delete_success.json';
import systemTelemetryFixture from './fixtures/system_telemetry.json';
import neo4jDegradedFixture from './fixtures/neo4j_degraded.json';
import vllmUnavailableFixture from './fixtures/vllm_unavailable.json';
import chromadbLockedFixture from './fixtures/chromadb_locked.json';
import backendUnreachableFixture from './fixtures/backend_unreachable.json';
import schemaMismatchFixture from './fixtures/schema_mismatch.json';
import futureSseStreamFixture from './fixtures/future_sse_stream.json';
import futureAbortFixture from './fixtures/future_abort_response.json';
import knowledgeGraphFullFixture from './fixtures/knowledge_graph_full.json';
import { ENDPOINTS } from '../api/endpoints';

export interface MockScenarioOptions {
  forceRefusal?: boolean;
  forceEmptyWorkspace?: boolean;
  forceNeo4jDegraded?: boolean;
  forceVllmOffline?: boolean;
  forceTimeout?: boolean;
  forceSchemaMismatch?: boolean;
}

class MockAdapter {
  private options: MockScenarioOptions = {};
  private activeDocuments = [...documentsListFixture.documents];

  // Per-document simulated ingestion progress (docId → creation timestamp)
  private ingestStartTimes: Map<string, number> = new Map();

  // In-memory PostgreSQL chat_sessions store
  private mockChatSessions: Map<string, any> = new Map([
    [
      'session-xyma-faculty',
      {
        id: 'session-xyma-faculty',
        thread_id: 'session-xyma-faculty',
        session_id: 'session-xyma-faculty',
        username: 'Operator',
        title: 'XYMA Analytics Faculty & Sensors',
        timestamp: 'Today, 2:15 PM',
        created_at: new Date(Date.now() - 3600000).toISOString(),
        updated_at: new Date().toISOString(),
        messages: [
          {
            role: 'user',
            text: 'Which faculty member co-founded XYMA Analytics and what sensors were deployed?',
            timestamp: '2:15 PM',
          },
          {
            role: 'assistant',
            text: 'XYMA Analytics was co-founded by **Prof. Krishnan Balasubramanian** and **Prof. Prabhu Rajagopal** from the Centre for Nondestructive Evaluation (CNDE) at IIT Madras.\n\nThey developed and deployed **$\\mu$MAP and TMAP high-temperature ultrasonic waveguide sensors** capable of continuous temperature profiling up to 1400°C in industrial assets like the Reliance Industries ROGC and Emirates Global Aluminium.',
            timestamp: '2:15 PM',
            response: graphragSuccessFixture,
          },
        ],
        sources: [
          {
            id: 'doc-iitmrp',
            name: 'IITMRP Annual Report.pdf',
            size: '12.4 MB',
            pages: 48,
            selected: true,
            color: 'indigo',
            status: 'ready',
          },
        ],
        selectedSourceIds: ['doc-iitmrp'],
      },
    ],
  ]);

  public setScenario(options: MockScenarioOptions) {
    this.options = { ...this.options, ...options };
  }

  public resetScenario() {
    this.options = {};
    this.activeDocuments = [...documentsListFixture.documents];
    this.mockChatSessions = new Map([
      [
        'session-xyma-faculty',
        {
          id: 'session-xyma-faculty',
          thread_id: 'session-xyma-faculty',
          session_id: 'session-xyma-faculty',
          username: 'Operator',
          title: 'XYMA Analytics Faculty & Sensors',
          timestamp: 'Today, 2:15 PM',
          created_at: new Date(Date.now() - 3600000).toISOString(),
          updated_at: new Date().toISOString(),
          messages: [
            {
              role: 'user',
              text: 'Which faculty member co-founded XYMA Analytics and what sensors were deployed?',
              timestamp: '2:15 PM',
            },
            {
              role: 'assistant',
              text: 'XYMA Analytics was co-founded by **Prof. Krishnan Balasubramanian** and **Prof. Prabhu Rajagopal** from the Centre for Nondestructive Evaluation (CNDE) at IIT Madras.\n\nThey developed and deployed **$\\mu$MAP and TMAP high-temperature ultrasonic waveguide sensors** capable of continuous temperature profiling up to 1400°C in industrial assets like the Reliance Industries ROGC and Emirates Global Aluminium.',
              timestamp: '2:15 PM',
              response: graphragSuccessFixture,
            },
          ],
          sources: [
            {
              id: 'doc-iitmrp',
              name: 'IITMRP Annual Report.pdf',
              size: '12.4 MB',
              pages: 48,
              selected: true,
              color: 'indigo',
              status: 'ready',
            },
          ],
          selectedSourceIds: ['doc-iitmrp'],
        },
      ],
    ]);
  }

  public getOptions(): MockScenarioOptions {
    return { ...this.options };
  }

  public async handleRequest(endpoint: string, options: RequestInit = {}): Promise<any> {
    // Simulate lightweight network traversal delay
    await new Promise((resolve) => setTimeout(resolve, 350));

    if (this.options.forceTimeout) {
      throw new Error('MOCK_TIMEOUT: Request timed out after 30000ms');
    }

    if (this.options.forceSchemaMismatch && endpoint === ENDPOINTS.SUBGRAPH_QUERY) {
      return schemaMismatchFixture;
    }

    // 1. GraphRAG Subgraph Query
    if (endpoint === ENDPOINTS.SUBGRAPH_QUERY || endpoint === ENDPOINTS.AGENT_QUERY) {
      if (this.options.forceEmptyWorkspace || this.activeDocuments.length === 0) {
        return emptyWorkspaceFixture;
      }
      if (this.options.forceRefusal) {
        return unableToVerifyFixture;
      }
      if (this.options.forceVllmOffline) {
        throw new Error('MOCK_ERROR: vLLM connection refused on port 8002');
      }

      // Check incoming query content if available
      if (options.body && typeof options.body === 'string') {
        try {
          const parsed = JSON.parse(options.body);
          if (parsed.query && parsed.query.toLowerCase().includes('refuse')) {
            return unableToVerifyFixture;
          }
          if (parsed.query && parsed.query.toLowerCase().includes('empty')) {
            return emptyWorkspaceFixture;
          }
          const rawQ = (parsed.query || '').trim().toLowerCase();
          if (['hi', 'hello', 'hey', 'greetings', 'hi raise'].includes(rawQ)) {
            return {
              ...graphragSuccessFixture,
              grounded_answer: "Hello! I am Raise Intelligence, your AI research assistant. I am ready to help you analyze your academic and institutional records. What research topic would you like to explore?",
              citations: [],
              subgraph: { nodes: [], edges: [] },
              routed_agent: 'ConversationalRouter',
              quality_gate_decision: 'pass',
            };
          }
        } catch {
          // ignore
        }
      }

      return graphragSuccessFixture;
    }

    // 2. Documents Listing
    if (endpoint === ENDPOINTS.DOCUMENTS || endpoint === ENDPOINTS.DOCUMENTS_MANIFEST) {
      if (this.options.forceEmptyWorkspace) {
        return { documents: [], total_count: 0 };
      }
      return {
        documents: [...this.activeDocuments],
        total_count: this.activeDocuments.length,
      };
    }

    // 3. Upload PDFs
    if (endpoint === ENDPOINTS.UPLOAD || endpoint === ENDPOINTS.UPLOAD_ACADEMIC_PDFS) {
      // Simulate adding a document and seed its ingestion timer
      const newDocId = 'uploaded_' + Date.now();
      this.ingestStartTimes.set(newDocId, Date.now());
      const newDoc = {
        id: newDocId,
        doc_id: newDocId,
        filename: 'Uploaded_Report_' + Date.now() + '.pdf',
        pages: 30,
        size_mb: 12.4,
        chunks_count: 50,
        status: 'processing',
        phase: 'uploading',
        is_protected: false,
        can_delete: true,
        deletable: true,
        owner: 'user',
      };
      this.activeDocuments.unshift(newDoc);
      return { ...uploadSuccessFixture, doc_id: newDocId };
    }

    // 3b. Document Status Polling (GET /api/documents/{id}/status)
    if (endpoint.startsWith('/api/documents/') && endpoint.endsWith('/status')) {
      const docId = endpoint.split('/api/documents/')[1].replace('/status', '');
      // Seed if unknown (handles pre-existing docs)
      if (!this.ingestStartTimes.has(docId)) {
        this.ingestStartTimes.set(docId, Date.now());
      }
      const elapsed = Date.now() - this.ingestStartTimes.get(docId)!;
      // Phase schedule (ms):  uploading 0-4s | parsing 4-9s | chunking 9-14s | embedding 14-20s | ready 20s+
      const phases: Array<{ phase: string; start: number; end: number }> = [
        { phase: 'uploading',  start: 0,     end: 4000  },
        { phase: 'parsing',    start: 4000,  end: 9000  },
        { phase: 'chunking',   start: 9000,  end: 14000 },
        { phase: 'embedding',  start: 14000, end: 20000 },
        { phase: 'ready',      start: 20000, end: Infinity },
      ];
      const current = phases.find((p) => elapsed >= p.start && elapsed < p.end) ?? phases[phases.length - 1];
      const phaseDetails: Record<string, string> = {
        uploading: 'Receiving file stream into temporary vault storage',
        parsing: 'IBM Docling executing layout extraction and reading order',
        chunking: 'Generating semantic text chunks and identifying domain entities',
        embedding: 'Generating 1024-dim BGE-Large embeddings and committing Neo4j triples',
        ready: 'Document ingestion complete and graph synchronized',
      };

      const phaseDuration = current.end === Infinity ? 1 : current.end - current.start;
      const phaseElapsed = elapsed - current.start;
      const percent =
        current.phase === 'ready'
          ? 100
          : Math.min(99, Math.round((phaseElapsed / phaseDuration) * 100));

      if (current.phase === 'ready') {
        const found = this.activeDocuments.find((d) => d.status === 'processing');
        if (found) found.status = 'ready';
      }

      return {
        phase: current.phase,
        percent,
        status: current.phase === 'ready' ? 'ready' : 'processing',
        detail: phaseDetails[current.phase] || '',
      };
    }

    // 4. Delete Document
    if (endpoint === ENDPOINTS.DELETE_DOCUMENT || (options.method === 'DELETE' && endpoint.startsWith('/api/documents/'))) {
      let targetFile = 'IITMRP Annual Report.pdf';
      if (options.method === 'DELETE' && endpoint.startsWith('/api/documents/')) {
        const rawId = endpoint.replace('/api/documents/', '');
        targetFile = decodeURIComponent(rawId);
      } else if (options.body && typeof options.body === 'string') {
        try {
          const body = JSON.parse(options.body);
          if (body.filename) targetFile = body.filename;
          else if (body.id) targetFile = body.id;
        } catch {
          // ignore
        }
      }

      // Check if target document is protected
      const matched = this.activeDocuments.find(
        (d: any) => d.filename === targetFile || d.id === targetFile || d.doc_id === targetFile
      );
      if (matched && (matched.is_protected || matched.can_delete === false || matched.deletable === false)) {
        throw new Error(`HTTP 403 Forbidden: Document '${matched.filename}' is pre-baked and protected. It cannot be deleted.`);
      }

      this.activeDocuments = this.activeDocuments.filter(
        (d: any) => d.filename !== targetFile && d.id !== targetFile && d.doc_id !== targetFile
      );
      return {
        status: 'success',
        filename: targetFile,
        documents: [...this.activeDocuments],
        total_count: this.activeDocuments.length,
      };
    }

    // 5. Full Graph
    if (endpoint === ENDPOINTS.GRAPH) {
      return knowledgeGraphFullFixture;
    }

    // 6. Subgraph by Node ID
    if (endpoint.startsWith('/api/subgraph/')) {
      return {
        nodes: knowledgeGraphFullFixture.nodes.slice(0, 3),
        edges: knowledgeGraphFullFixture.edges.slice(0, 1),
      };
    }

    // 7. Search
    if (endpoint === ENDPOINTS.SEARCH) {
      return graphragSuccessFixture.top_chunks;
    }

    // 8. Neo4j Status
    if (endpoint === ENDPOINTS.NEO4J_STATUS) {
      if (this.options.forceNeo4jDegraded) {
        return neo4jDegradedFixture;
      }
      return systemTelemetryFixture.neo4j;
    }

    // 9. Hardware Telemetry
    if (endpoint === ENDPOINTS.HARDWARE_TELEMETRY) {
      return systemTelemetryFixture.telemetry;
    }

    // 10. Chat Abort
    if (
      endpoint === ENDPOINTS.CHAT_ABORT ||
      endpoint === '/api/chat/abort'
    ) {
      let reqId = 'req-' + Date.now();
      let sessId = 'session-default';
      if (options.body && typeof options.body === 'string') {
        try {
          const parsed = JSON.parse(options.body);
          if (parsed.request_id) reqId = parsed.request_id;
          if (parsed.session_id || parsed.chat_id) sessId = parsed.session_id || parsed.chat_id;
        } catch {
          // ignore
        }
      }
      return {
        ...futureAbortFixture,
        status: 'aborted',
        request_id: reqId,
        session_id: sessId,
        message: `Inference job for request ${reqId} successfully terminated on vLLM server.`,
      };
    }

    // 10b. Dynamic Graph-Grounded Suggestions
    if (endpoint.startsWith('/api/suggestions')) {
      const url = new URL(endpoint, 'http://localhost');
      const activeDocs = url.searchParams.get('active_docs') || url.searchParams.get('drawer');
      // When 0 documents are uploaded / attached, return [] (clean chat interface)
      if (!activeDocs || activeDocs.trim() === '' || this.options.forceEmptyWorkspace) {
        return [];
      }
      return [
        {
          query: 'What leadership role does Dr. Shrikumar Suryanarayan hold in the institute?',
          category: 'Governance & Leadership',
          grounding_confidence: '100%',
        },
        {
          query: 'What collaborative research initiatives and industry-aligned mandates are driven through Institute Centres?',
          category: 'Interdisciplinary Centres & R&D',
          grounding_confidence: '100%',
        },
        {
          query: 'What specialized academic and interdisciplinary research activities are conducted under Energy Science?',
          category: 'Departmental Research Operations',
          grounding_confidence: '100%',
        },
      ];
    }

    // 11. Chat History & Cross-Session Persistence (PostgreSQL Simulation)
    if (endpoint.startsWith('/api/chat/history')) {
      const url = new URL(endpoint, 'http://localhost');
      const sessionId = url.searchParams.get('session_id') || url.searchParams.get('thread_id');
      const method = (options.method || 'GET').toUpperCase();

      if (method === 'GET') {
        if (sessionId && this.mockChatSessions.has(sessionId)) {
          return this.mockChatSessions.get(sessionId);
        }
        if (sessionId) {
          return {
            thread_id: sessionId,
            session_id: sessionId,
            username: 'Operator',
            title: 'New Chat',
            messages: [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          };
        }
        return Array.from(this.mockChatSessions.values());
      }

      if (method === 'POST') {
        let payload: any = {};
        if (options.body && typeof options.body === 'string') {
          try {
            payload = JSON.parse(options.body);
          } catch {}
        }
        const threadId = payload.thread_id || payload.session_id || `session-${Date.now()}`;
        const existing = this.mockChatSessions.get(threadId) || {};
        const savedSession = {
          ...existing,
          ...payload,
          id: threadId,
          thread_id: threadId,
          session_id: threadId,
          username: payload.username || existing.username || 'Operator',
          title: payload.title || existing.title || 'New Chat',
          messages: payload.messages || existing.messages || [],
          updated_at: new Date().toISOString(),
        };
        this.mockChatSessions.set(threadId, savedSession);
        return {
          status: 'success',
          thread_id: threadId,
          session_id: threadId,
          is_saved: Boolean(savedSession.is_saved),
          message: 'Session persisted to PostgreSQL chat_sessions table',
        };
      }

      if (method === 'DELETE') {
        if (sessionId) {
          this.mockChatSessions.delete(sessionId);
        }
        return { status: 'success', session_id: sessionId, message: 'Session deleted' };
      }
    }

    // 12. Chat Sessions List & Session Drawer
    if (endpoint.startsWith('/api/chat/sessions')) {
      const method = (options.method || 'GET').toUpperCase();

      // Dedicated Drawer Attach: POST /api/chat/sessions/:id/drawer/attach
      if (method === 'POST' && endpoint.endsWith('/drawer/attach')) {
        const parts = endpoint.split('/');
        const id = parts[parts.length - 3];
        let payload: any = {};
        if (options.body && typeof options.body === 'string') {
          try {
            payload = JSON.parse(options.body);
          } catch {}
        }
        const targetDoc = payload.filename || payload.document_id || payload.document || '';
        const session = this.mockChatSessions.get(id) || {
          id,
          thread_id: id,
          session_id: id,
          username: 'Operator',
          title: 'Chat Session',
          messages: [],
          attached_docs: [],
        };
        const currentList: string[] = [...(session.attached_docs || [])];
        if (targetDoc && !currentList.includes(targetDoc)) {
          currentList.push(targetDoc);
        }
        session.attached_docs = currentList;
        this.mockChatSessions.set(id, session);
        return {
          status: 'success',
          action: 'attach',
          session_id: id,
          attached_document: targetDoc,
          attached_docs: currentList,
          active_docs: currentList,
          count: currentList.length,
        };
      }

      // Dedicated Drawer Remove: POST /api/chat/sessions/:id/drawer/remove
      if (method === 'POST' && endpoint.endsWith('/drawer/remove')) {
        const parts = endpoint.split('/');
        const id = parts[parts.length - 3];
        let payload: any = {};
        if (options.body && typeof options.body === 'string') {
          try {
            payload = JSON.parse(options.body);
          } catch {}
        }
        const targetDoc = payload.filename || payload.document_id || payload.document || '';
        const session = this.mockChatSessions.get(id);
        let currentList: string[] = [...(session?.attached_docs || [])];
        currentList = currentList.filter((d: string) => d !== targetDoc);
        if (session) {
          session.attached_docs = currentList;
        }
        return {
          status: 'success',
          action: 'remove',
          session_id: id,
          removed_document: targetDoc,
          attached_docs: currentList,
          active_docs: currentList,
          count: currentList.length,
        };
      }

      // Dedicated Drawer GET: GET /api/chat/sessions/:id/drawer
      if (method === 'GET' && endpoint.endsWith('/drawer')) {
        const parts = endpoint.split('/');
        const id = parts[parts.length - 2];
        const session = this.mockChatSessions.get(id);
        const attached: string[] = session?.attached_docs || (session?.selectedSourceIds && session.sources ? session.sources.filter((s: any) => s.selected).map((s: any) => s.name) : []);
        const enriched = attached.map((docName: string) => {
          const matched = this.activeDocuments.find((d: any) => d.filename === docName || d.id === docName);
          return matched || {
            id: `doc-${docName}`,
            filename: docName,
            status: 'ready',
            pages: 1,
            size_mb: 1.0,
            chunks_count: 10,
          };
        });
        return {
          status: 'success',
          session_id: id,
          attached_docs: attached,
          active_docs: attached,
          documents: enriched,
          count: attached.length,
        };
      }

      // Session Drawer PATCH: PATCH /api/chat/sessions/:id/drawer
      if (method === 'PATCH' && endpoint.endsWith('/drawer')) {
        const parts = endpoint.split('/');
        const id = parts[parts.length - 2];
        let payload: any = {};
        if (options.body && typeof options.body === 'string') {
          try {
            payload = JSON.parse(options.body);
          } catch {}
        }
        const activeDocs = payload.active_docs || payload.attached_docs || [];
        const session = this.mockChatSessions.get(id);
        if (session) {
          session.attached_docs = activeDocs;
        }
        return { status: 'success', session_id: id, attached_docs: activeDocs, active_docs: activeDocs };
      }

      if (method === 'GET') {
        return Array.from(this.mockChatSessions.values());
      }
      if (method === 'DELETE') {
        const parts = endpoint.split('/');
        const id = parts[parts.length - 1];
        if (id && id !== 'sessions') {
          this.mockChatSessions.delete(id);
        }
        return { status: 'success', message: 'Session deleted' };
      }
    }

    // 13. Clear All Chats / Clear Session
    if (endpoint === '/api/chat/clear' || endpoint === '/api/chat/delete' || endpoint === ENDPOINTS.CLEAR_CHAT) {
      let payload: any = {};
      if (options.body && typeof options.body === 'string') {
        try {
          payload = JSON.parse(options.body);
        } catch {}
      }
      const threadId = payload.thread_id || payload.session_id;
      if (threadId) {
        const session = this.mockChatSessions.get(threadId);
        if (session) {
          session.messages = [];
        }
        return { status: 'success', thread_id: threadId, message: 'Chat session cleared' };
      } else {
        this.mockChatSessions.clear();
        return { status: 'success', message: 'All chat sessions cleared successfully' };
      }
    }

    // Default fallback
    return { status: 'mock_ok', endpoint };
  }

  // Direct fixture access for testing
  public getFixtures() {
    return {
      graphragSuccess: graphragSuccessFixture,
      emptyWorkspace: emptyWorkspaceFixture,
      unableToVerify: unableToVerifyFixture,
      documentsList: documentsListFixture,
      uploadSuccess: uploadSuccessFixture,
      deleteSuccess: deleteSuccessFixture,
      systemTelemetry: systemTelemetryFixture,
      neo4jDegraded: neo4jDegradedFixture,
      vllmUnavailable: vllmUnavailableFixture,
      chromadbLocked: chromadbLockedFixture,
      backendUnreachable: backendUnreachableFixture,
      schemaMismatch: schemaMismatchFixture,
      futureSseStream: futureSseStreamFixture,
      futureAbort: futureAbortFixture,
      knowledgeGraphFull: knowledgeGraphFullFixture,
    };
  }
}

export const mockAdapter = new MockAdapter();
