import { z } from 'zod';

export const SubgraphQueryRequestSchema = z.object({
  query: z.string().min(1, 'Query cannot be empty'),
  hops: z.number().int().min(1).max(3).default(2),
  top_k: z.number().int().min(1).max(10).default(4),
  mode: z.enum(['fast', 'expert']).optional(),
  stream: z.boolean().optional(),
  document_filter: z.string().nullable().optional(),
  active_docs: z.array(z.string()).optional(),
  format: z.string().optional(),
  thread_id: z.string().optional(),
  chat_history: z.array(z.object({ human: z.string(), ai: z.string() })).optional(),
  parser: z.string().optional(),
  full_potential: z.boolean().optional(),
});

export type SubgraphQueryRequest = z.infer<typeof SubgraphQueryRequestSchema>;

export const AgentQueryRequestSchema = z.object({
  query: z.string().min(1, 'Query cannot be empty'),
});

export type AgentQueryRequest = z.infer<typeof AgentQueryRequestSchema>;

export const CitationSchema = z.object({
  citation_index: z.number().int(),
  chunk_id: z.string(),
  document_id: z.string(),
  pdf_filename: z.string(),
  primary_page: z.number().int(),
  heading: z.string().default(''),
  plain_text: z.string(),
  university: z.string().default('IIT Madras'),
  similarity: z.number().default(0),
});

export type Citation = z.infer<typeof CitationSchema>;

export const VerifiedClaimSchema = z.object({
  claim_id: z.string(),
  text: z.string(),
  is_supported: z.boolean(),
  status: z
    .enum(['SUPPORTED', 'NUMERICAL_MISMATCH', 'ENTITY_MISMATCH', 'UNSUPPORTED', 'CITATION_INVALID'])
    .or(z.string()),
  extracted_numbers: z.array(z.string()).default([]),
  matched_numbers: z.array(z.string()).default([]),
  citations_found: z.array(z.number().int()).default([]),
  notes: z.array(z.string()).default([]),
});

export type VerifiedClaim = z.infer<typeof VerifiedClaimSchema>;

export const GraphNodeSchema = z.object({
  id: z.string(),
  name: z.string(),
  label: z.string().default(''),
  type: z.string().default('Entity'),
  color: z.string().optional(),
  provenance: z.record(z.any()).default({}),
});

export type GraphNode = z.infer<typeof GraphNodeSchema>;

export const GraphEdgeSchema = z.object({
  source: z.string(),
  target: z.string(),
  relationship: z.string(),
  provenance: z.record(z.any()).default({}),
});

export type GraphEdge = z.infer<typeof GraphEdgeSchema>;

export const SubgraphDataSchema = z.object({
  nodes: z.array(GraphNodeSchema).default([]),
  edges: z.array(GraphEdgeSchema).default([]),
});

export type SubgraphData = z.infer<typeof SubgraphDataSchema>;

export const TopChunkSchema = z.object({
  chunk_id: z.string(),
  text: z.string(),
  similarity: z.number().default(0),
  metadata: z.record(z.any()).default({}),
});

export type TopChunk = z.infer<typeof TopChunkSchema>;

export const QualityGateReportSchema = z.object({
  evaluator_type: z.string().default('LocalHeuristicEvaluator'),
  faithfulness: z.number().default(0),
  answer_relevance: z.number().optional().default(0),
  context_precision: z.number().optional().default(0),
  context_recall: z.number().optional().default(0),
  overall_score: z.number().optional().default(0),
  supported_claims_count: z.number().int().default(0),
  total_claims_count: z.number().int().default(0),
  numerical_mismatches: z.number().int().default(0),
  citation_errors: z.number().int().default(0),
  is_acceptable: z.boolean().default(true),
  rejection_reason: z.string().nullable().default(null),
  claims: z.array(z.any()).optional().default([]),
});

export type QualityGateReport = z.infer<typeof QualityGateReportSchema>;

export const QualityGateDecisionSchema = z.enum([
  'accept',
  'retry',
  'unable_to_verify',
  'empty_workspace',
]);

export type QualityGateDecision = z.infer<typeof QualityGateDecisionSchema>;

export const SubgraphQueryResponseSchema = z.object({
  query: z.string(),
  routing_strategy: z.string().optional(),
  query_type: z.string().optional(),
  selected_tools: z.array(z.string()).default([]),
  cypher_status: z.string().optional(),
  cypher_repair_count: z.number().int().default(0),
  path_critic_expanded: z.boolean().default(false),
  grounded_answer: z.string().default(''),
  traceability_score: z.number().default(0),
  verified_claims: z.array(VerifiedClaimSchema).default([]),
  citations: z.array(CitationSchema).default([]),
  answer_contract: z.record(z.any()).nullable().optional(),
  subgraph: SubgraphDataSchema.default({ nodes: [], edges: [] }),
  top_chunks: z.array(TopChunkSchema).default([]),
  quality_gate_decision: QualityGateDecisionSchema.default('accept'),
  quality_gate_report: QualityGateReportSchema.optional(),
  retry_count: z.number().int().default(0),
  execution_time: z.number().default(0),
  message: z.string().optional(),

  // Dynamic Follow-Up Inquiries & Suggestions from Gateway / LLM Node
  follow_up_inquiries: z.array(z.string()).optional(),
  suggestions: z.array(z.string()).optional(),

  // LangGraph Query Intake & Reformulation Pipeline State Fields
  standalone_query: z.string().optional(),
  decomposed_queries: z.array(z.string()).default([]),
  intent_route: z.string().optional(),
  latency_sec: z.number().optional(),
  error_log: z.string().nullable().optional(),
  thread_id: z.string().optional(),
  persisted: z.boolean().optional(),
  saved: z.boolean().optional(),
  persistence_status: z.string().optional(),
  persistence_error: z.string().nullable().optional(),
});

export type SubgraphQueryResponse = z.infer<typeof SubgraphQueryResponseSchema>;

export const AgentQueryResponseSchema = z.object({
  query: z.string(),
  query_type: z.string().optional(),
  selected_tools: z.array(z.string()).default([]),
  grounded_answer: z.string().default(''),
  traceability_score: z.number().default(0),
  verified_claims: z.array(VerifiedClaimSchema).default([]),
  citations: z.array(CitationSchema).default([]),
  answer_contract: z.record(z.any()).nullable().optional(),
});

export type AgentQueryResponse = z.infer<typeof AgentQueryResponseSchema>;

// ─── Cross-Session Chat Persistence Schemas ─────────────────────────────────

export const PersistedChatSessionSchema = z.object({
  thread_id: z.string(),
  session_id: z.string().optional(),
  username: z.string().default('Operator'),
  title: z.string().default('New Chat'),
  messages: z.array(z.any()).default([]),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
  selectedSourceIds: z.array(z.string()).optional(),
  sources: z.array(z.any()).optional(),
  attached_docs: z.array(z.string()).optional(),
  is_saved: z.boolean().optional().default(false),
});

export type PersistedChatSession = z.infer<typeof PersistedChatSessionSchema>;

export const ChatHistoryResponseSchema = z.object({
  thread_id: z.string(),
  session_id: z.string().optional(),
  username: z.string().optional().default('Operator'),
  title: z.string().optional().default('Chat Session'),
  messages: z.array(z.any()).default([]),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
  selectedSourceIds: z.array(z.string()).optional(),
  sources: z.array(z.any()).optional(),
  is_saved: z.boolean().optional().default(false),
});

export type ChatHistoryResponse = z.infer<typeof ChatHistoryResponseSchema>;

export const ChatSessionSummarySchema = z.object({
  id: z.string(),
  thread_id: z.string().optional(),
  session_id: z.string().optional(),
  username: z.string().optional().default('Operator'),
  title: z.string(),
  timestamp: z.string().optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
  is_saved: z.boolean().optional().default(false),
  message_count: z.number().int().optional(),
});

export type ChatSessionSummary = z.infer<typeof ChatSessionSummarySchema>;

// ─── Session Drawer Contracts ───────────────────────────────────────────────

export const SessionDrawerResponseSchema = z
  .object({
    status: z.string().default('success'),
    session_id: z.string(),
    attached_docs: z.array(z.string()).default([]),
    active_docs: z.array(z.string()).default([]),
    documents: z.array(z.any()).default([]),
    count: z.number().int().default(0),
  })
  .passthrough();

export type SessionDrawerResponse = z.infer<typeof SessionDrawerResponseSchema>;

export const SessionDrawerAttachResponseSchema = z
  .object({
    status: z.string().default('success'),
    action: z.string().optional().default('attach'),
    session_id: z.string(),
    attached_document: z.string().optional(),
    attached_docs: z.array(z.string()).default([]),
    active_docs: z.array(z.string()).default([]),
    count: z.number().int().default(0),
  })
  .passthrough();

export type SessionDrawerAttachResponse = z.infer<typeof SessionDrawerAttachResponseSchema>;

export const SessionDrawerRemoveResponseSchema = z
  .object({
    status: z.string().default('success'),
    action: z.string().optional().default('remove'),
    session_id: z.string(),
    removed_document: z.string().optional(),
    attached_docs: z.array(z.string()).default([]),
    active_docs: z.array(z.string()).default([]),
    count: z.number().int().default(0),
  })
  .passthrough();

export type SessionDrawerRemoveResponse = z.infer<typeof SessionDrawerRemoveResponseSchema>;

export const SessionDrawerUpdateResponseSchema = z
  .object({
    status: z.string().default('success'),
    session_id: z.string(),
    attached_docs: z.array(z.string()).default([]),
    active_docs: z.array(z.string()).default([]),
  })
  .passthrough();

export type SessionDrawerUpdateResponse = z.infer<typeof SessionDrawerUpdateResponseSchema>;

export const FeedbackStatsSchema = z
  .object({
    thumbs_up: z.number().int().default(0),
    thumbs_down: z.number().int().default(0),
    satisfaction_ratio: z.number().default(0),
    total_feedback: z.number().int().default(0),
  })
  .passthrough();

export type FeedbackStats = z.infer<typeof FeedbackStatsSchema>;
