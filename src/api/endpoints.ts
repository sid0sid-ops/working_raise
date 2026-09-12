export const ENDPOINTS = {
  // Documentation & Health Check
  INDEX: '/',
  HEALTH: '/api/health',
  HEALTH_ALT: '/health',
  OPENAPI: '/openapi.json',
  SWAGGER: '/docs',
  REDOC: '/redoc',

  // Core Chat & Retrieval (Standard Cloudflare Tunnel & GraphRAG)
  CHAT: '/api/chat',
  CHAT_ABORT: '/api/chat/abort',
  CLEAR_CHAT: '/api/chat/clear',
  CHAT_HISTORY: '/api/chat/history',
  CHAT_HISTORY_BY_SESSION: (sessionId: string) => `/api/chat/history?session_id=${encodeURIComponent(sessionId)}`,
  CHAT_SESSIONS: '/api/chat/sessions',
  CHAT_SESSION_BY_ID: (sessionId: string) => `/api/chat/sessions/${encodeURIComponent(sessionId)}`,
  CHAT_SESSIONS_BY_USER: (username: string) => `/api/chat/sessions?username=${encodeURIComponent(username)}`,
  DELETE_CHAT_SESSION: (sessionId: string) => `/api/chat/history?session_id=${encodeURIComponent(sessionId)}`,
  RENAME_CHAT_SESSION: (sessionId: string) => `/api/chat/sessions/${encodeURIComponent(sessionId)}/rename`,
  SESSION_DRAWER: (sessionId: string) => `/api/chat/sessions/${encodeURIComponent(sessionId)}/drawer`,
  SESSION_DRAWER_ATTACH: (sessionId: string) => `/api/chat/sessions/${encodeURIComponent(sessionId)}/drawer/attach`,
  SESSION_DRAWER_REMOVE: (sessionId: string) => `/api/chat/sessions/${encodeURIComponent(sessionId)}/drawer/remove`,
  SUBGRAPH_QUERY: '/api/graphrag/subgraph-query',
  AGENT_QUERY: '/api/agent/query',
  SEARCH: '/api/search',
  SUGGESTIONS: '/api/suggestions',

  // Document Management
  UPLOAD: '/api/upload',
  DOCUMENTS: '/api/documents',
  DOCUMENTS_MANIFEST: '/api/documents/manifest',
  UPLOAD_ACADEMIC_PDFS: '/api/upload-academic-pdfs',
  DELETE_DOCUMENT: '/api/documents/delete',
  DELETE_DOCUMENT_BY_ID: (id: string) => `/api/documents/${encodeURIComponent(id)}`,
  LOAD_VAULT_DEFAULTS: '/api/vault/load-defaults',
  PDF_VIEW: (filename: string) => `/api/pdf/${encodeURIComponent(filename)}`,

  // Graph & Subgraph
  GRAPH: '/api/graph',
  SUBGRAPH: (nodeId: string) => `/api/subgraph/${encodeURIComponent(nodeId)}`,

  // System & Telemetry
  NEO4J_STATUS: '/api/neo4j/status',
  HARDWARE_TELEMETRY: '/api/hardware-telemetry',

  // Document ingestion status polling (live) & real-time SSE stream
  DOCUMENT_STATUS: (id: string) => `/api/documents/${encodeURIComponent(id)}/status`,
  DOCUMENT_EVENTS: (id: string) => `/api/documents/${encodeURIComponent(id)}/events`,

  // Future backend abstractions
  FUTURE_CHAT_STREAM: '/api/chat/stream',
  FUTURE_SOURCE_STATUS: (id: string) => `/api/sources/${encodeURIComponent(id)}/status`,
  FUTURE_SYSTEM_STATUS: '/api/system/status',
} as const;
