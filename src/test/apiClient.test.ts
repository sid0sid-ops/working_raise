import { describe, it, expect, beforeEach } from 'vitest';
import { apiClient } from '../api/client';
import { ENDPOINTS } from '../api/endpoints';
import { setApiMode } from '../app/config';
import { SubgraphQueryResponseSchema } from '../schemas/chat';
import { DocumentListResponseSchema } from '../schemas/sources';
import { mockAdapter } from '../mocks/mockAdapter';

describe('API Client & Multi-Mode Operation', () => {
  beforeEach(() => {
    mockAdapter.resetScenario();
    setApiMode('mock');
  });

  it('successfully returns deterministic fixtures in mock mode', async () => {
    const res = await apiClient.request(
      ENDPOINTS.SUBGRAPH_QUERY,
      SubgraphQueryResponseSchema,
      { method: 'POST', body: JSON.stringify({ query: 'IIT Madras startups' }) }
    );

    expect(res.isMock).toBe(true);
    expect(res.error).toBeNull();
    expect(res.data).not.toBeNull();
    expect(res.data?.grounded_answer).toContain('XYMA Analytics');
  });

  it('returns empty workspace response when scenario is forced', async () => {
    mockAdapter.setScenario({ forceEmptyWorkspace: true });

    const res = await apiClient.request(
      ENDPOINTS.SUBGRAPH_QUERY,
      SubgraphQueryResponseSchema,
      { method: 'POST', body: JSON.stringify({ query: 'any question' }) }
    );

    expect(res.data?.quality_gate_decision).toBe('empty_workspace');
    expect(res.data?.grounded_answer).toContain('Please upload an academic PDF');
  });

  it('returns quality gate refusal response when refusal scenario is active', async () => {
    mockAdapter.setScenario({ forceRefusal: true });

    const res = await apiClient.request(
      ENDPOINTS.SUBGRAPH_QUERY,
      SubgraphQueryResponseSchema,
      { method: 'POST', body: JSON.stringify({ query: 'financials' }) }
    );

    expect(res.data?.quality_gate_decision).toBe('unable_to_verify');
    expect(res.data?.quality_gate_report?.faithfulness).toBe(0.45);
  });

  it('lists documents from mock data', async () => {
    const res = await apiClient.request(
      ENDPOINTS.DOCUMENTS,
      DocumentListResponseSchema,
      { method: 'GET' }
    );

    expect(res.error).toBeNull();
    expect(res.data?.total_count).toBeGreaterThan(0);
  });

  it('normalizes client-side AbortError cleanly', async () => {
    const controller = new AbortController();
    controller.abort();

    const res = await apiClient.request(
      ENDPOINTS.SUBGRAPH_QUERY,
      SubgraphQueryResponseSchema,
      { method: 'POST', signal: controller.signal }
    );

    expect(res.data).toBeNull();
    expect(res.error).not.toBeNull();
    expect(res.error?.code).toBe('CLIENT_REQUEST_CANCELLED');
    expect(res.error?.retryable).toBe(true);
  });
});
