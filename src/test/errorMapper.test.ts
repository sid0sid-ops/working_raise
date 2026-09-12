import { describe, it, expect } from 'vitest';
import { normalizeError } from '../utils/errorMapper';
import { z } from 'zod';

describe('Error Mapping & Diagnostics', () => {
  it('maps connection refused / TypeError fetch to BACKEND_UNREACHABLE', () => {
    const fetchErr = new TypeError('Failed to fetch');
    const norm = normalizeError(fetchErr, '/api/documents', 0);

    expect(norm.code).toBe('BACKEND_UNREACHABLE');
    expect(norm.status).toBe(0);
    expect(norm.endpoint).toBe('/api/documents');
    expect(norm.retryable).toBe(true);
    expect(norm.likelyCause).toContain('Windows Firewall');
    expect(norm.recommendedAction).toContain('FastAPI');
  });

  it('maps DOMException AbortError to CLIENT_REQUEST_CANCELLED', () => {
    const abortErr = new DOMException('The user aborted a request.', 'AbortError');
    const norm = normalizeError(abortErr, '/api/graphrag/subgraph-query', 0);

    expect(norm.code).toBe('CLIENT_REQUEST_CANCELLED');
    expect(norm.message).toContain('Note: Server-side GPU inference on Windows may continue');
    expect(norm.retryable).toBe(true);
  });

  it('maps ZodError to SCHEMA_VALIDATION_FAILED with issue details', () => {
    const testSchema = z.object({ count: z.number() });
    const parseResult = testSchema.safeParse({ count: 'invalid' });

    expect(parseResult.success).toBe(false);
    if (!parseResult.success) {
      const norm = normalizeError(parseResult.error, '/api/test', 200);
      expect(norm.code).toBe('SCHEMA_VALIDATION_FAILED');
      expect(norm.details).toBeDefined();
      expect(norm.details[0].path).toBe('count');
    }
  });

  it('maps HTTP 404 to ENDPOINT_NOT_FOUND', () => {
    const norm = normalizeError('Not Found', '/api/sources/1/status', 404);
    expect(norm.code).toBe('ENDPOINT_NOT_FOUND');
    expect(norm.status).toBe(404);
    expect(norm.likelyCause).toContain('future unreleased route');
  });

  it('maps HTTP 500 to GATEWAY_INTERNAL_ERROR', () => {
    const norm = normalizeError('Internal Server Error', '/api/graphrag/subgraph-query', 500);
    expect(norm.code).toBe('GATEWAY_INTERNAL_ERROR');
    expect(norm.status).toBe(500);
    expect(norm.retryable).toBe(true);
    expect(norm.recommendedAction).toContain('Docker logs');
  });
});
