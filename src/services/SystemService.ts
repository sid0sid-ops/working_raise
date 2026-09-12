import { apiClient, ApiResponse } from '../api/client';
import { ENDPOINTS } from '../api/endpoints';
import { getApiBaseUrl } from '../app/config';
import {
  HardwareTelemetry,
  HardwareTelemetrySchema,
  Neo4jStatus,
  Neo4jStatusSchema,
  BackendCapabilities,
} from '../types';

export class SystemService {
  /**
   * Hardware telemetry (GPU VRAM, System RAM, active models)
   */
  public async getHardwareTelemetry(
    signal?: AbortSignal
  ): Promise<ApiResponse<HardwareTelemetry>> {
    return apiClient.request<HardwareTelemetry>(
      ENDPOINTS.HARDWARE_TELEMETRY,
      HardwareTelemetrySchema,
      {
        method: 'GET',
        signal,
      }
    );
  }

  /**
   * Neo4j Bolt connection status and node count
   */
  public async getNeo4jStatus(signal?: AbortSignal): Promise<ApiResponse<Neo4jStatus>> {
    return apiClient.request<Neo4jStatus>(
      ENDPOINTS.NEO4J_STATUS,
      Neo4jStatusSchema,
      {
        method: 'GET',
        signal,
      }
    );
  }

  /**
   * Centralized capability and health detection probe
   * Probes active endpoints to determine operational state
   */
  public async probeCapabilities(): Promise<BackendCapabilities> {
    const startTime = performance.now();
    const timestamp = new Date().toISOString();

    const capabilities: BackendCapabilities = {
      apiReachable: false,
      openApiReachable: false,
      chatAvailable: false,
      documentsAvailable: false,
      graphAvailable: false,
      searchAvailable: false,
      hardwareTelemetryAvailable: false,
      neo4jStatusAvailable: false,
      sseStreamingAvailable: false, // VERIFIED LIMITATION: FALSE
      serverAbortAvailable: false,  // VERIFIED LIMITATION: FALSE
      asyncSourceStatusAvailable: false, // VERIFIED LIMITATION: FALSE
      lastProbeTime: timestamp,
      latencyMs: 0,
    };

    try {
      // 1. Probe /api/health, /health, or / or /api/documents for connection alive check
      let aliveRes = await apiClient.request(ENDPOINTS.HEALTH, undefined, {
        method: 'GET',
        skipModeCheck: true,
        timeoutMs: 3000,
      });

      if (aliveRes.status !== 200) {
        aliveRes = await apiClient.request(ENDPOINTS.HEALTH_ALT, undefined, {
          method: 'GET',
          skipModeCheck: true,
          timeoutMs: 3000,
        });
      }

      if (aliveRes.status !== 200) {
        aliveRes = await apiClient.request(ENDPOINTS.INDEX, undefined, {
          method: 'GET',
          skipModeCheck: true,
          timeoutMs: 3000,
        });
      }

      if (aliveRes.status !== 200) {
        aliveRes = await apiClient.request(ENDPOINTS.DOCUMENTS, undefined, {
          method: 'GET',
          skipModeCheck: true,
          timeoutMs: 3000,
        });
      }

      const endTime = performance.now();
      capabilities.latencyMs = Math.round(endTime - startTime);

      if (aliveRes.status >= 200 && aliveRes.status < 400) {
        capabilities.apiReachable = true;
        capabilities.chatAvailable = true;
        capabilities.documentsAvailable = true;
        capabilities.searchAvailable = true;
      }

      // 2. Probe OpenAPI schema
      const openApiRes = await apiClient.request(ENDPOINTS.OPENAPI, undefined, {
        method: 'GET',
        skipModeCheck: true,
        timeoutMs: 3000,
      });
      if (openApiRes.status === 200) {
        capabilities.openApiReachable = true;
      }

      // 3. Probe Telemetry
      const telemRes = await apiClient.request(ENDPOINTS.HARDWARE_TELEMETRY, undefined, {
        method: 'GET',
        skipModeCheck: true,
        timeoutMs: 3000,
      });
      if (telemRes.status === 200) {
        capabilities.hardwareTelemetryAvailable = true;
      }

      // 4. Probe Neo4j
      const neo4jRes = await apiClient.request(ENDPOINTS.NEO4J_STATUS, undefined, {
        method: 'GET',
        skipModeCheck: true,
        timeoutMs: 3000,
      });
      if (neo4jRes.status === 200) {
        capabilities.neo4jStatusAvailable = true;
        if (neo4jRes.data && (neo4jRes.data as any).connected !== false) {
          capabilities.graphAvailable = true;
        }
      }
    } catch {
      // Ignore network errors in probe
    }

    return capabilities;
  }

  /**
   * Test Cloudflare Tunnel / Gateway connection directly
   * Probes /health, /, or /api/documents and returns diagnostic latency & error
   */
  public async testConnection(customUrl?: string): Promise<{
    success: boolean;
    status: number;
    latencyMs: number;
    endpoint: string;
    error?: string;
    isCorsIssue?: boolean;
  }> {
    const rawTarget = (customUrl || getApiBaseUrl()).trim().replace(/\/+$/, '');
    const startTime = performance.now();

    const testEndpoints = ['/api/health', '/health', '/', '/api/documents', '/docs'];

    for (const ep of testEndpoints) {
      const fullUrl = `${rawTarget}${ep}`;
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 6000);

      try {
        const res = await fetch(fullUrl, {
          method: 'GET',
          signal: controller.signal,
          headers: {
            'Accept': 'application/json, text/plain, */*',
          },
        });
        clearTimeout(timer);
        const latencyMs = Math.round(performance.now() - startTime);

        // 2xx, 3xx, or even 401/403 proves the backend is alive and responding
        if (res.status < 500) {
          return {
            success: true,
            status: res.status,
            latencyMs,
            endpoint: ep,
          };
        }
      } catch (err: any) {
        clearTimeout(timer);
        // If aborted due to timeout
        if (err.name === 'AbortError') {
          return {
            success: false,
            status: 0,
            latencyMs: 6000,
            endpoint: ep,
            error: `Connection timed out after 6 seconds reaching ${rawTarget}.`,
          };
        }

        const isCorsOrOffline =
          err instanceof TypeError &&
          (err.message.includes('fetch') || err.message.includes('NetworkError') || err.message.includes('Failed'));

        if (ep === testEndpoints[testEndpoints.length - 1]) {
          return {
            success: false,
            status: 0,
            latencyMs: Math.round(performance.now() - startTime),
            endpoint: ep,
            isCorsIssue: isCorsOrOffline,
            error: isCorsOrOffline
              ? `Cannot reach ${rawTarget}. Please verify that the backend server is running and accessible.`
              : err?.message || 'Network connection failed',
          };
        }
      }
    }

    return {
      success: false,
      status: 0,
      latencyMs: Math.round(performance.now() - startTime),
      endpoint: '/health',
      error: `Could not connect to ${rawTarget}.`,
    };
  }
}

export const systemService = new SystemService();
