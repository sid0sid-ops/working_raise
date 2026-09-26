import type { z } from 'zod';
import { config, getApiBaseUrl, getApiMode, getStoredApiKey } from '../app/config';
import type { ApiError } from '../types';
import { normalizeError } from '../utils/errorMapper';
import { sanitizeStreamText } from '../utils/sanitizeStreamText';
import { logToTerminal } from '../utils/terminalLogger';

export { sanitizeStreamText };

export interface RequestOptions extends RequestInit {
  timeoutMs?: number;
  skipModeCheck?: boolean; // Force real network call (used during capability probe)
}

export interface ApiResponse<T> {
  data: T | null;
  error: ApiError | null;
  isMock: boolean;
  status: number;
}

export interface StreamResult {
  text: string;
  error: ApiError | null;
  status: number;
  metadata?: Record<string, any>;
}

class ApiClient {
  public async request<T>(
    endpoint: string,
    schema?: z.ZodType<T, any, any>,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    const method = options.method || 'GET';
    const startTime = Date.now();

    // Summarize payload for terminal display
    let details: string | undefined;
    if (typeof options.body === 'string') {
      try {
        const parsed = JSON.parse(options.body) as Record<string, any>;
        details = parsed.query
          ? `Query: "${parsed.query.slice(0, 70)}${parsed.query.length > 70 ? '...' : ''}"`
          : parsed.message
            ? `Message: "${parsed.message.slice(0, 70)}${parsed.message.length > 70 ? '...' : ''}"`
            : options.body.slice(0, 100);
      } catch {
        details = options.body.slice(0, 100);
      }
    } else if (options.body instanceof FormData) {
      details = 'Multipart/form-data (Document Upload)';
    }

    logToTerminal({
      type: 'REQ',
      method,
      endpoint,
      details,
    });

    if (options.signal?.aborted) {
      const normErr = normalizeError(
        new DOMException('The user aborted a request.', 'AbortError'),
        endpoint,
        0
      );
      logToTerminal({
        type: 'ERR',
        method,
        endpoint,
        status: 0,
        durationMs: Date.now() - startTime,
        error: 'Request aborted by client signal',
      });
      return { data: null, error: normErr, isMock: getApiMode() === 'mock', status: 0 };
    }

    const currentMode = getApiMode();

    // 1. MOCK MODE
    if (currentMode === 'mock' && !options.skipModeCheck) {
      const normErr = normalizeError(
        new Error('Mock adapter is not included in production deployment build.'),
        endpoint,
        0
      );
      return { data: null, error: normErr, isMock: false, status: 0 };
    }

    // 2. REMOTE OR AUTO MODE
    const baseUrl = getApiBaseUrl();
    const url = endpoint.startsWith('http') ? endpoint : `${baseUrl}${endpoint}`;
    const timeoutMs =
      options.timeoutMs ||
      (endpoint.includes('upload') ? config.uploadTimeoutMs : config.defaultTimeoutMs);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    // Merge external signal if provided
    if (options.signal) {
      options.signal.addEventListener('abort', () => controller.abort());
    }

    const headers: Record<string, string> = {
      'X-Request-ID': `req-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      ...(options.headers as Record<string, string>),
    };

    // Attach optional API Key / Bearer token if configured
    const apiKey = getStoredApiKey();
    if (apiKey && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${apiKey}`;
      headers['X-API-Key'] = apiKey;
    }

    // If body is NOT FormData, default to application/json
    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (!response.ok) {
        let errJson: any = null;
        try {
          errJson = await response.json();
        } catch {
          errJson = await response.text();
        }
        const normErr = normalizeError(errJson || response.statusText, endpoint, response.status);
        logToTerminal({
          type: 'ERR',
          method,
          endpoint,
          status: response.status,
          durationMs: Date.now() - startTime,
          error: `Gateway HTTP ${response.status}: ${normErr.message}`,
        });
        return { data: null, error: normErr, isMock: false, status: response.status };
      }

      // Check content type for binary data (like PDF)
      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('application/pdf') || contentType.includes('octet-stream')) {
        const blob = await response.blob();
        logToTerminal({
          type: 'RES',
          method,
          endpoint,
          status: response.status,
          durationMs: Date.now() - startTime,
          message: `Binary PDF Stream Received (${blob.size} bytes)`,
        });
        return { data: blob as unknown as T, error: null, isMock: false, status: response.status };
      }

      const json = await response.json();

      if (schema) {
        const parseResult = schema.safeParse(json);
        if (!parseResult.success) {
          const normErr = normalizeError(parseResult.error, endpoint, response.status);
          logToTerminal({
            type: 'ERR',
            method,
            endpoint,
            status: response.status,
            durationMs: Date.now() - startTime,
            error: `Contract Violation: ${normErr.message}`,
          });
          return { data: null, error: normErr, isMock: false, status: response.status };
        }
        logToTerminal({
          type: 'RES',
          method,
          endpoint,
          status: response.status,
          durationMs: Date.now() - startTime,
          message: 'Live Gateway Response 200 OK (Validated)',
        });
        return { data: parseResult.data, error: null, isMock: false, status: response.status };
      }

      logToTerminal({
        type: 'RES',
        method,
        endpoint,
        status: response.status,
        durationMs: Date.now() - startTime,
        message: 'Live Gateway Response 200 OK',
      });
      return { data: json as T, error: null, isMock: false, status: response.status };
    } catch (err: any) {
      clearTimeout(timer);

      const isCorsOrOffline =
        err instanceof TypeError &&
        (err.message.includes('fetch') ||
          err.message.includes('NetworkError') ||
          err.message.includes('Failed'));

      const normErr = isCorsOrOffline
        ? {
            code: 'BACKEND_UNREACHABLE',
            message:
              'Unable to connect to the backend server. Please verify that the server is online.',
            status: 0,
            endpoint,
            retryable: true,
            timestamp: new Date().toISOString(),
          }
        : normalizeError(err, endpoint, 0);

      logToTerminal({
        type: 'ERR',
        method,
        endpoint,
        status: 0,
        durationMs: Date.now() - startTime,
        error: `Network Fetch Exception: ${normErr.message} (Target: ${url})`,
      });
      return { data: null, error: normErr, isMock: false, status: 0 };
    }
  }

  /**
   * Streaming support for LLM text responses (SSE or chunked transfer)
   */
  public async requestStream(
    endpoint: string,
    options: RequestOptions = {},
    onChunk?: (textChunk: string, fullAccumulatedText: string) => void
  ): Promise<StreamResult> {
    const baseUrl = getApiBaseUrl();
    const url = endpoint.startsWith('http') ? endpoint : `${baseUrl}${endpoint}`;
    const timeoutMs = options.timeoutMs || 90000;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    if (options.signal) {
      options.signal.addEventListener('abort', () => controller.abort());
    }

    const headers: Record<string, string> = {
      'X-Request-ID': `req-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      ...(options.headers as Record<string, string>),
    };

    const apiKey = getStoredApiKey();
    if (apiKey && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${apiKey}`;
      headers['X-API-Key'] = apiKey;
    }

    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const method = options.method || 'POST';
    const startTime = Date.now();
    logToTerminal({
      type: 'REQ',
      method,
      endpoint,
      details: `Streaming SSE request to ${url}`,
    });

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (!response.ok) {
        let errJson: any = null;
        try {
          errJson = await response.json();
        } catch {
          errJson = await response.text();
        }
        const normErr = normalizeError(errJson || response.statusText, endpoint, response.status);
        logToTerminal({
          type: 'ERR',
          method,
          endpoint,
          status: response.status,
          durationMs: Date.now() - startTime,
          error: `Stream error (HTTP ${response.status}): ${normErr.message}`,
        });
        return { text: '', error: normErr, status: response.status };
      }

      if (!response.body) {
        const text = await response.text();
        logToTerminal({
          type: 'RES',
          method,
          endpoint,
          status: response.status,
          durationMs: Date.now() - startTime,
          message: `Stream completed (static body)`,
        });
        return { text, error: null, status: response.status };
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = '';
      let buffer = '';
      let streamMetadata: Record<string, any> | undefined;

      const contentType = response.headers.get('content-type') || '';
      const isSse =
        contentType.includes('text/event-stream') || contentType.includes('application/x-ndjson');

      const processLine = (line: string) => {
        const trimmed = line.trim();
        // Ignore SSE comments/keepalives (e.g. ": keepalive")
        if (!trimmed || trimmed.startsWith(':')) {
          return;
        }

        // Ignore SSE event declaration lines (e.g. "event: ping", "event: stage")
        if (trimmed.startsWith('event:')) {
          return;
        }

        let payload = line;
        let isData = false;
        if (payload.startsWith('data:')) {
          isData = true;
          // Strip "data:" prefix and optional single leading space, but PRESERVE trailing spaces/newlines!
          payload = payload.slice(5).replace(/^[ \t]/, '');
        }

        if (!payload || payload.trim() === '[DONE]') {
          return;
        }

        // Handle JSON payloads: {"token": "..."} or {"text": "..."} or {"content": "..."}
        const trimmedPayload = payload.trim();
        if (trimmedPayload.startsWith('{') && trimmedPayload.endsWith('}')) {
          try {
            const parsed = JSON.parse(trimmedPayload) as Record<string, any>;
            const token =
              parsed.token ??
              parsed.text ??
              parsed.content ??
              parsed.response ??
              parsed.delta?.content ??
              parsed.reply ??
              null;
            if (typeof token === 'string') {
              if (token.length > 0) {
                fullText += token;
                onChunk?.(token, fullText);
              }
              return;
            }

            // Capture completion metadata (citations, subgraph, sources, status, etc.)
            if (
              parsed.citations ||
              parsed.subgraph ||
              parsed.status === 'completed' ||
              parsed.sources
            ) {
              streamMetadata = {
                ...streamMetadata,
                ...parsed,
              };
              return;
            }
          } catch {
            // Malformed JSON block: attempt unpacking via sanitizeStreamText
            const unpacked = sanitizeStreamText(trimmedPayload);
            if (unpacked && !unpacked.startsWith('{')) {
              fullText += unpacked;
              onChunk?.(unpacked, fullText);
              return;
            }
            return;
          }
        }

        // If it was an explicit SSE "data: ..." line that is plain text
        if (isData) {
          fullText += payload + '\n';
          onChunk?.(payload + '\n', fullText);
          return;
        }

        // If plain text line (not JSON)
        if (!trimmedPayload.startsWith('{') && !trimmedPayload.startsWith('[')) {
          fullText += line + '\n';
          onChunk?.(line + '\n', fullText);
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const raw = decoder.decode(value, { stream: true });
        buffer += raw;

        // Line-buffer whenever newlines or SSE markers are present
        if (buffer.includes('\n') || isSse || buffer.includes('data:')) {
          const lines = buffer.split('\n');
          // Incomplete trailing segment stays in buffer
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            processLine(line);
          }
        } else if (!isSse && !buffer.includes('data:') && !buffer.startsWith('{')) {
          fullText += buffer;
          onChunk?.(buffer, fullText);
          buffer = '';
        }
      }

      // Flush remaining bytes in decoder and buffer
      buffer += decoder.decode();
      if (buffer.trim()) {
        processLine(buffer);
      }

      // Final pass: ensure no residual JSON tokens or SSE markers remain
      fullText = sanitizeStreamText(fullText);

      logToTerminal({
        type: 'RES',
        method,
        endpoint,
        status: response.status,
        durationMs: Date.now() - startTime,
        message: `Stream completed successfully (${fullText.length} characters)`,
      });

      return { text: fullText, error: null, status: response.status, metadata: streamMetadata };
    } catch (err: any) {
      clearTimeout(timer);
      const isCorsOrOffline =
        err instanceof TypeError &&
        (err.message.includes('fetch') ||
          err.message.includes('NetworkError') ||
          err.message.includes('Failed'));
      const normErr = isCorsOrOffline
        ? {
            code: 'BACKEND_UNREACHABLE',
            message:
              'Unable to connect to the backend server. Please verify that the server is online.',
            status: 0,
            endpoint,
            retryable: true,
            timestamp: new Date().toISOString(),
          }
        : normalizeError(err?.message, endpoint, 0);
      logToTerminal({
        type: 'ERR',
        method,
        endpoint,
        status: 0,
        durationMs: Date.now() - startTime,
        error: `Stream exception: ${normErr.message} (Target: ${url})`,
      });
      return { text: '', error: normErr, status: 0 };
    }
  }
}

export const apiClient = new ApiClient();
