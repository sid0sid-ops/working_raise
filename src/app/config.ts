import { ConfigMode } from '../types';

export interface AppConfig {
  apiBaseUrl: string;
  apiMode: ConfigMode;
  defaultTimeoutMs: number;
  uploadTimeoutMs: number;
  maxGraphHops: number;
  defaultTopK: number;
}

const envBaseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;
const envMode = import.meta.env.VITE_API_MODE as ConfigMode | undefined;

export const config: AppConfig = {
  apiBaseUrl: (envBaseUrl && envBaseUrl.trim() !== '') ? envBaseUrl.trim() : 'http://localhost:8000',
  apiMode: (envMode === 'mock' || envMode === 'remote' || envMode === 'auto') ? envMode : 'remote',
  defaultTimeoutMs: 30000,
  uploadTimeoutMs: 120000, // Large PDFs require 120s for synchronous IBM Docling parsing
  maxGraphHops: 3,
  defaultTopK: 4,
};

// Helper to read stored Cloudflare Tunnel URL from localStorage
export const getStoredTunnelUrl = (): string => {
  if (typeof window === 'undefined') return '';
  try {
    const tunnel = localStorage.getItem('raise_tunnel_url');
    if (tunnel && tunnel.trim() !== '' && !tunnel.includes('localhost') && !tunnel.includes('127.0.0.1')) {
      return tunnel.trim();
    }
    const gateway = localStorage.getItem('raise_gateway_url');
    if (gateway && gateway.trim() !== '' && !gateway.includes('localhost') && !gateway.includes('127.0.0.1')) {
      return gateway.trim();
    }
    return '';
  } catch {
    return '';
  }
};

export const setStoredTunnelUrl = (url: string) => {
  if (typeof window === 'undefined') return;
  try {
    const cleaned = url.trim().replace(/\/+$/, '');
    if (cleaned) {
      localStorage.setItem('raise_tunnel_url', cleaned);
      localStorage.setItem('raise_gateway_url', cleaned);
    } else {
      localStorage.removeItem('raise_tunnel_url');
      localStorage.removeItem('raise_gateway_url');
    }
  } catch {}
};

export const getStoredLastConnectedAt = (): number | null => {
  if (typeof window === 'undefined') return null;
  try {
    const val = localStorage.getItem('raise_last_connected_at');
    return val ? parseInt(val, 10) : null;
  } catch {
    return null;
  }
};

export const setStoredLastConnectedAt = (timestamp: number = Date.now()) => {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem('raise_last_connected_at', String(timestamp));
  } catch {}
};

export const getStoredUsername = (): string => {
  if (typeof window === 'undefined') return 'Operator';
  try {
    return localStorage.getItem('raise_gateway_username') || 'Operator';
  } catch {
    return 'Operator';
  }
};

export const setStoredUsername = (name: string) => {
  if (typeof window === 'undefined') return;
  try {
    const trimmed = name.trim();
    if (trimmed) {
      localStorage.setItem('raise_gateway_username', trimmed);
    } else {
      localStorage.removeItem('raise_gateway_username');
    }
  } catch {}
};

export const getStoredApiKey = (): string => {
  if (typeof window === 'undefined') return '';
  try {
    return localStorage.getItem('raise_api_key') || '';
  } catch {
    return '';
  }
};

export const setStoredApiKey = (key: string) => {
  if (typeof window === 'undefined') return;
  try {
    const trimmed = key.trim();
    if (trimmed) {
      localStorage.setItem('raise_api_key', trimmed);
    } else {
      localStorage.removeItem('raise_api_key');
    }
  } catch {}
};

// Allow runtime overrides for testing or user settings
const initialStoredUrl = getStoredTunnelUrl();
let runtimeBaseUrl = initialStoredUrl && initialStoredUrl.trim() !== '' ? initialStoredUrl.trim() : config.apiBaseUrl;
let runtimeMode = config.apiMode;

export const getApiBaseUrl = (): string => runtimeBaseUrl;
export const setApiBaseUrl = (url: string, persistTunnel: boolean = true) => {
  const cleaned = url.trim().replace(/\/+$/, '');
  runtimeBaseUrl = cleaned;
  if (persistTunnel) {
    setStoredTunnelUrl(cleaned);
  }
};

export const getApiMode = (): ConfigMode => runtimeMode;
export const setApiMode = (mode: ConfigMode) => {
  runtimeMode = mode;
};
