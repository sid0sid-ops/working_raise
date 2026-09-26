import { z } from 'zod';

export const ApiErrorSchema = z.object({
  code: z.string(),
  message: z.string(),
  status: z.number().int(),
  endpoint: z.string(),
  retryable: z.boolean(),
  likelyCause: z.string().optional(),
  recommendedAction: z.string().optional(),
  details: z.any().optional(),
  timestamp: z.string().default(() => new Date().toISOString()),
});

export type ApiError = z.infer<typeof ApiErrorSchema>;
