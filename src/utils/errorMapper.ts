import { ZodError } from 'zod';
import type { ApiError } from '../types';

export function normalizeError(error: unknown, endpoint: string, statusCode: number = 0): ApiError {
  const timestamp = new Date().toISOString();

  // 1. AbortError (Client-side cancellation)
  if (error instanceof DOMException && error.name === 'AbortError') {
    return {
      code: 'CLIENT_REQUEST_CANCELLED',
      message:
        'Request was cancelled locally in the browser. Note: Server-side GPU inference on Windows may continue.',
      status: 0,
      endpoint,
      retryable: true,
      likelyCause: 'User manually cancelled the query or navigated away.',
      recommendedAction: 'Resubmit the query if you still need the answer.',
      timestamp,
    };
  }

  // 2. Zod Schema Validation Error
  if (error instanceof ZodError) {
    const formattedIssues = error.issues.map((i) => ({
      path: i.path.join('.'),
      message: i.message,
    }));
    return {
      code: 'SCHEMA_VALIDATION_FAILED',
      message: `Backend response for ${endpoint} did not match expected contract.`,
      status: statusCode,
      endpoint,
      retryable: false,
      likelyCause: 'Backend returned an updated, missing, or mismatched field structure.',
      recommendedAction:
        'Inspect the Zod path in Diagnostics to adjust client schemas or check backend version.',
      details: formattedIssues,
      timestamp,
    };
  }

  // 3. Network / Connection Failures (Failed to fetch, connection refused)
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return {
      code: 'BACKEND_UNREACHABLE',
      message: `Failed to connect to RAISE Gateway at ${endpoint}.`,
      status: 0,
      endpoint,
      retryable: true,
      likelyCause:
        'Windows workstation is offline, FastAPI is stopped, or Windows Firewall is blocking TCP port 8000.',
      recommendedAction:
        'Ensure FastAPI is running on Windows (app.py) and firewall rule allows port 8000. Alternatively, toggle Mock Mode.',
      details: error.message,
      timestamp,
    };
  }

  // 4. HTTP Status Errors
  if (statusCode > 0) {
    if (statusCode === 404) {
      return {
        code: 'ENDPOINT_NOT_FOUND',
        message: `Endpoint ${endpoint} does not exist on the backend gateway (HTTP 404).`,
        status: 404,
        endpoint,
        retryable: false,
        likelyCause: 'Route is not registered in FastAPI app.py or is a future unreleased route.',
        recommendedAction: 'Verify route path in endpoints.ts against mother.md truth table.',
        timestamp,
      };
    }

    if (statusCode === 422) {
      return {
        code: 'UNPROCESSABLE_ENTITY',
        message: `FastAPI rejected payload validation for ${endpoint} (HTTP 422).`,
        status: 422,
        endpoint,
        retryable: false,
        likelyCause: 'Pydantic validation failed on the backend due to missing or invalid fields.',
        recommendedAction: 'Verify request payload keys match backend Pydantic model.',
        details: error,
        timestamp,
      };
    }

    if (statusCode === 503) {
      return {
        code: 'SERVICE_UNAVAILABLE',
        message: `Service or storage connection pool is temporarily reconnecting at ${endpoint} (HTTP 503).`,
        status: 503,
        endpoint,
        retryable: true,
        likelyCause:
          'PostgreSQL connection pool cycling, database reconnection, or temporary service warm-up.',
        recommendedAction:
          'Wait a few seconds for automatic reconnection. Cached local sessions and messages are preserved.',
        details: error,
        timestamp,
      };
    }

    if (statusCode === 500 || statusCode === 502) {
      return {
        code: 'GATEWAY_INTERNAL_ERROR',
        message: `Backend gateway encountered an internal failure while processing ${endpoint} (HTTP ${statusCode}).`,
        status: statusCode,
        endpoint,
        retryable: true,
        likelyCause:
          'A downstream container (vLLM, Neo4j, or ChromaDB) threw an exception or is unresponsive.',
        recommendedAction:
          'Check Windows workstation terminal or Docker logs (raise-vllm-prod, raise-neo4j-prod).',
        details: error,
        timestamp,
      };
    }

    return {
      code: `HTTP_${statusCode}`,
      message: `Request to ${endpoint} failed with HTTP status ${statusCode}.`,
      status: statusCode,
      endpoint,
      retryable: statusCode >= 500,
      details: error,
      timestamp,
    };
  }

  // 5. Generic / Unknown Error
  const msg = error instanceof Error ? error.message : String(error);
  return {
    code: 'UNKNOWN_ERROR',
    message: msg || 'An unknown network error occurred.',
    status: statusCode,
    endpoint,
    retryable: true,
    likelyCause: 'Unhandled client or runtime exception.',
    recommendedAction: 'Review browser console or developer diagnostics log.',
    details: msg,
    timestamp,
  };
}
