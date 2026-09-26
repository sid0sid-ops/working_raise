import { create } from 'zustand';
import {
  config,
  getApiBaseUrl,
  getApiMode,
  getStoredApiKey,
  getStoredLastConnectedAt,
  getStoredTunnelUrl,
  getStoredUsername,
  setApiBaseUrl,
  setApiMode,
  setStoredApiKey,
  setStoredLastConnectedAt,
  setStoredTunnelUrl,
  setStoredUsername,
} from '../app/config';
import { systemService } from '../services/SystemService';
import type { AppMode, BackendCapabilities, ConfigMode } from '../types';
import { logToTerminal } from '../utils/terminalLogger';

interface ModeState {
  appMode: AppMode;
  configMode: ConfigMode;
  apiBaseUrl: string;
  gatewayUsername: string;
  apiKey: string;
  isTunnelConfigured: boolean;
  latencyMs: number;
  lastConnectedAt: number | null;
  capabilities: BackendCapabilities | null;
  isProbing: boolean;
  probeError: string | null;

  setConfigMode: (mode: ConfigMode) => void;
  setBaseUrl: (url: string) => void;
  setUsername: (name: string) => void;
  setApiKey: (key: string) => void;
  clearTunnelUrl: () => void;
  runCapabilityProbe: () => Promise<void>;
  testConnection: (customUrl?: string) => Promise<{
    success: boolean;
    status: number;
    latencyMs: number;
    endpoint: string;
    error?: string;
    isCorsIssue?: boolean;
  }>;
  setAppMode: (mode: AppMode) => void;
}

const resolveInitialTunnel = (): string => {
  if (typeof window !== 'undefined') {
    try {
      const searchParams = new URLSearchParams(window.location.search);
      const paramUrl = searchParams.get('tunnel') || searchParams.get('gateway');
      if (paramUrl && paramUrl.trim() && paramUrl.startsWith('http')) {
        const cleaned = paramUrl.trim().replace(/\/+$/, '');
        setStoredTunnelUrl(cleaned);
        setApiBaseUrl(cleaned);
        return cleaned;
      }
    } catch {}
  }
  const stored = getStoredTunnelUrl();
  if (stored && stored.trim() !== '') return stored.trim();
  if (
    config.apiBaseUrl &&
    config.apiBaseUrl.trim() !== '' &&
    !config.apiBaseUrl.includes('localhost')
  ) {
    return config.apiBaseUrl.trim();
  }
  return '';
};

const initialTunnel = resolveInitialTunnel();

export const useModeStore = create<ModeState>((set, get) => ({
  appMode: getApiMode() === 'mock' ? 'mock' : 'offline',
  configMode: getApiMode(),
  apiBaseUrl: getApiBaseUrl(),
  gatewayUsername: getStoredUsername(),
  apiKey: getStoredApiKey(),
  isTunnelConfigured: Boolean(initialTunnel && initialTunnel.trim() !== ''),
  latencyMs: 0,
  lastConnectedAt: getStoredLastConnectedAt(),
  capabilities: null,
  isProbing: false,
  probeError: null,

  setConfigMode: (mode: ConfigMode) => {
    setApiMode(mode);
    set({ configMode: mode });
    get().runCapabilityProbe();
  },

  setBaseUrl: (url: string) => {
    const cleaned = url.trim().replace(/\/+$/, '');
    setApiBaseUrl(cleaned);
    setStoredTunnelUrl(cleaned);
    set({
      apiBaseUrl: cleaned,
      isTunnelConfigured: Boolean(cleaned && cleaned.trim() !== ''),
    });
    get().runCapabilityProbe();
  },

  setUsername: (name: string) => {
    const cleanName = name.trim() || 'Operator';
    setStoredUsername(cleanName);
    set({ gatewayUsername: cleanName });
  },

  setApiKey: (key: string) => {
    setStoredApiKey(key);
    set({ apiKey: key.trim() });
  },

  clearTunnelUrl: () => {
    setStoredTunnelUrl('');
    setApiBaseUrl('http://localhost:8000', false);
    set({
      apiBaseUrl: 'http://localhost:8000',
      isTunnelConfigured: false,
      appMode: 'offline',
      capabilities: null,
      latencyMs: 0,
      probeError: null,
    });
  },

  setAppMode: (appMode: AppMode) => {
    set({ appMode });
  },

  testConnection: async (customUrl?: string) => {
    const target = customUrl || get().apiBaseUrl;
    set({ isProbing: true, probeError: null });
    logToTerminal({
      type: 'REQ',
      method: 'GET',
      endpoint: '/health',
      details: `Probing Pipeline Tunnel Gateway at: ${target}`,
    });
    const result = await systemService.testConnection(target);
    if (result.success) {
      logToTerminal({
        type: 'RES',
        method: 'GET',
        endpoint: result.endpoint,
        status: result.status,
        durationMs: result.latencyMs,
        details: `Pipeline Connected! (HTTP ${result.status}, ${result.latencyMs}ms)`,
      });
    } else {
      logToTerminal({
        type: 'ERR',
        method: 'GET',
        endpoint: result.endpoint,
        status: result.status,
        error: result.error || 'Pipeline Connection Failed',
        details: `Target was: ${target}`,
      });
    }
    if (result.success) {
      setStoredLastConnectedAt();
    }
    set({
      isProbing: false,
      latencyMs: result.latencyMs,
      appMode: result.success ? 'connected' : 'offline',
      probeError: result.error || null,
      lastConnectedAt: result.success ? Date.now() : get().lastConnectedAt,
    });
    return result;
  },

  runCapabilityProbe: async () => {
    const { configMode, isTunnelConfigured } = get();

    if (configMode === 'mock') {
      set({
        appMode: 'mock',
        latencyMs: 0,
        capabilities: {
          apiReachable: true,
          openApiReachable: true,
          chatAvailable: true,
          documentsAvailable: true,
          graphAvailable: true,
          searchAvailable: true,
          hardwareTelemetryAvailable: true,
          neo4jStatusAvailable: true,
          sseStreamingAvailable: false,
          serverAbortAvailable: false,
          asyncSourceStatusAvailable: false,
          lastProbeTime: new Date().toISOString(),
          latencyMs: 12,
        },
        isProbing: false,
        probeError: null,
      });
      return;
    }

    if (!isTunnelConfigured) {
      set({
        appMode: 'offline',
        capabilities: null,
        isProbing: false,
        probeError: null,
      });
      return;
    }

    set({ isProbing: true, probeError: null });

    try {
      const caps = await systemService.probeCapabilities();

      let computedMode: AppMode = 'offline';
      if (caps.apiReachable) {
        computedMode = 'connected';
        setStoredLastConnectedAt();
      } else {
        computedMode = 'offline';
      }

      set({
        capabilities: caps,
        appMode: computedMode,
        latencyMs: caps.latencyMs,
        isProbing: false,
        lastConnectedAt: caps.apiReachable ? Date.now() : get().lastConnectedAt,
      });
    } catch (err: any) {
      set({
        capabilities: null,
        appMode: 'offline',
        isProbing: false,
        probeError: err?.message || 'Capability probe failed',
      });
    }
  },
}));

// Automatically check connection on startup if tunnel URL is saved
if (typeof window !== 'undefined' && initialTunnel && initialTunnel.trim() !== '') {
  setTimeout(() => {
    useModeStore.getState().runCapabilityProbe();
  }, 100);
}
