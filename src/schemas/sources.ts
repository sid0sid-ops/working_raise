import { z } from 'zod';

export const DocumentItemSchema = z
  .object({
    id: z.string().optional(),
    doc_id: z.string().optional(),
    filename: z.string(),
    name: z.string().optional(),
    pages: z.number().int().default(0),
    size_mb: z.number().default(0),
    chunks_count: z.number().int().default(0),
    chunks: z.number().int().optional(),
    status: z.string().default('ready'),
    phase: z.string().optional(),
    is_protected: z.boolean().optional(),
    can_delete: z.boolean().optional(),
    deletable: z.boolean().optional(),
    owner: z.string().optional(),
    uploaded_at: z.string().optional(),
    library: z.string().optional(),
  })
  .passthrough();

export type DocumentItem = z.infer<typeof DocumentItemSchema>;

export const DocumentListResponseSchema = z
  .object({
    documents: z.array(DocumentItemSchema).default([]),
    total_count: z.number().int().nullish().default(0),
  })
  .passthrough();

export type DocumentListResponse = z.infer<typeof DocumentListResponseSchema>;

export const UploadReportItemSchema = z
  .object({
    filename: z.string(),
    doc_id: z.string().optional(),
    document_id: z.string().optional(),
    status: z.string().optional(),
    pages_processed: z.number().int().default(0),
    chunks_extracted: z.number().int().default(0),
    facts_extracted: z.number().int().default(0),
    triples_extracted: z.number().int().default(0),
  })
  .passthrough();

export type UploadReportItem = z.infer<typeof UploadReportItemSchema>;

export const UploadResponseSchema = z.object({
  status: z.string(),
  uploaded_count: z.number().int().default(0),
  reports: z.array(UploadReportItemSchema).default([]),
  total_nodes: z.number().int().default(0),
  total_edges: z.number().int().default(0),
});

export type UploadResponse = z.infer<typeof UploadResponseSchema>;

export const DeleteDocumentRequestSchema = z.object({
  filename: z.string().min(1, 'Filename required'),
});

export type DeleteDocumentRequest = z.infer<typeof DeleteDocumentRequestSchema>;

export const DeleteDocumentResponseSchema = z.object({
  status: z.string(),
  filename: z.string(),
  documents: z.array(DocumentItemSchema).default([]),
  total_count: z.number().int().default(0),
});

export type DeleteDocumentResponse = z.infer<typeof DeleteDocumentResponseSchema>;

// ─── Document Ingestion Status ────────────────────────────────────────────────
// Matches: GET /api/documents/{id}/status
// Backend shape: { phase, percent, status?, detail? }

export const DocumentIngestionPhaseSchema = z.enum([
  'uploading',
  'parsing',
  'chunking',
  'embedding',
  'ready',
  'error',
]);

export type DocumentIngestionPhase = z.infer<typeof DocumentIngestionPhaseSchema>;

export const DocumentStatusResponseSchema = z.preprocess(
  (val: any) => {
    if (val && typeof val === 'object') {
      const normalized: any = { ...val };
      // Lowercase phase if backend returns uppercase
      if (typeof normalized.phase === 'string') {
        normalized.phase = normalized.phase.toLowerCase();
      }
      // Fallback progress_percent -> percent
      if (normalized.percent === undefined && typeof normalized.progress_percent === 'number') {
        normalized.percent = normalized.progress_percent;
      }
      return normalized;
    }
    return val;
  },
  z.object({
    /** Coarse pipeline stage */
    phase: DocumentIngestionPhaseSchema,
    /** 0–100 percentage complete within the current phase */
    percent: z.number().min(0).max(100).default(0),
    /** Optional human-readable detail from the backend */
    detail: z.string().optional(),
    /** Mirror of documents.status column – 'processing' | 'ready' | 'error' */
    status: z.string().optional(),
  })
);

export type DocumentStatusResponse = z.infer<typeof DocumentStatusResponseSchema>;
