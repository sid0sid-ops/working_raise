import { describe, it, expect, beforeEach } from 'vitest';
import { chatService } from '../services/ChatService';
import { mockAdapter } from '../mocks/mockAdapter';
import { ENDPOINTS } from '../api/endpoints';
import { setApiMode } from '../app/config';

describe('Server-Side Query Cancellation (Priority 1.3)', () => {
  beforeEach(() => {
    mockAdapter.resetScenario();
    setApiMode('mock');
  });

  it('verifies CHAT_ABORT endpoint is /api/chat/abort', () => {
    expect(ENDPOINTS.CHAT_ABORT).toBe('/api/chat/abort');
  });

  it('chatService.abortChat sends POST /api/chat/abort with { request_id, session_id }', async () => {
    const testReqId = 'req-test-12345';
    const testSessionId = 'sess-test-67890';

    const res = await chatService.abortChat({
      request_id: testReqId,
      session_id: testSessionId,
    });

    expect(res.error).toBeNull();
    expect(res.status).toBe(200);
    expect(res.data).toBeDefined();
    expect(res.data?.status).toBe('aborted');
    expect(res.data?.request_id).toBe(testReqId);
    expect((res.data as any)?.session_id).toBe(testSessionId);
    expect(res.data?.message).toContain('terminated on vLLM server');
  });

  it('chatService.abortChat supports backward-compatible positional arguments', async () => {
    const testChatId = 'chat-legacy-999';
    const testReqId = 'req-legacy-888';

    const res = await chatService.abortChat(testChatId, testReqId);

    expect(res.error).toBeNull();
    expect(res.status).toBe(200);
    expect(res.data?.status).toBe('aborted');
    expect(res.data?.request_id).toBe(testReqId);
  });
});
