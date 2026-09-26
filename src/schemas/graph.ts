import { z } from 'zod';
import { GraphEdgeSchema, GraphNodeSchema } from './chat';

export const FullGraphResponseSchema = z.object({
  nodes: z.array(GraphNodeSchema).default([]),
  edges: z.array(GraphEdgeSchema).default([]),
  total_nodes: z.number().int().optional(),
  total_edges: z.number().int().optional(),
});

export type FullGraphResponse = z.infer<typeof FullGraphResponseSchema>;

export const SearchRequestSchema = z.object({
  query: z.string().min(1, 'Search query cannot be empty'),
  limit: z.number().int().min(1).max(20).default(5),
});

export type SearchRequest = z.infer<typeof SearchRequestSchema>;

export const SearchResultItemSchema = z.object({
  chunk_id: z.string(),
  text: z.string(),
  similarity: z.number().default(0),
  metadata: z.record(z.any()).default({}),
});

export type SearchResultItem = z.infer<typeof SearchResultItemSchema>;

export const SearchResponseSchema = z.array(SearchResultItemSchema).or(
  z.object({
    results: z.array(SearchResultItemSchema).default([]),
  })
);

export type SearchResponse = z.infer<typeof SearchResponseSchema>;
