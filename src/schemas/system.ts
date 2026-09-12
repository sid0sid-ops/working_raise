import { z } from 'zod';

export const HardwareTelemetrySchema = z.object({
  gpu_model: z.string().default('Unknown GPU'),
  ram_total_gb: z.number().default(0),
  ram_available_gb: z.number().default(0),
  ram_percent: z.number().default(0),
  embedding_model: z.string().default('BAAI/bge-large-en-v1.5'),
  neo4j_endpoint: z.string().default('bolt://localhost:7687'),
});

export type HardwareTelemetry = z.infer<typeof HardwareTelemetrySchema>;

export const Neo4jStatusSchema = z.object({
  connected: z.boolean().default(false),
  uri: z.string().default('bolt://localhost:7687'),
  user: z.string().optional(),
  database: z.string().optional(),
  total_nodes: z.number().int().optional(),
  error: z.string().optional(),
  hint: z.string().optional(),
});

export type Neo4jStatus = z.infer<typeof Neo4jStatusSchema>;

export const BackendCapabilitiesSchema = z.object({
  apiReachable: z.boolean().default(false),
  openApiReachable: z.boolean().default(false),
  chatAvailable: z.boolean().default(false),
  documentsAvailable: z.boolean().default(false),
  graphAvailable: z.boolean().default(false),
  searchAvailable: z.boolean().default(false),
  hardwareTelemetryAvailable: z.boolean().default(false),
  neo4jStatusAvailable: z.boolean().default(false),
  sseStreamingAvailable: z.boolean().default(false), // STRICTLY FALSE (Current limitation)
  serverAbortAvailable: z.boolean().default(false), // STRICTLY FALSE (Current limitation)
  asyncSourceStatusAvailable: z.boolean().default(false), // STRICTLY FALSE (Current limitation)
  lastProbeTime: z.string().optional(),
  latencyMs: z.number().default(0),
});

export type BackendCapabilities = z.infer<typeof BackendCapabilitiesSchema>;
