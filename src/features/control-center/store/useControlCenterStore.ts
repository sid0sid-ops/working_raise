import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { detectProviderFromKey } from '../services/keyDetector';
import type {
  CloudApiKeyEntry,
  ControlCenterConfig,
  SubstrateConfig,
  SystemHardwareInfo,
  TargetPlatform,
} from '../types';

interface ControlCenterState {
  isOpen: boolean;
  activeTab: 'platform' | 'models' | 'databases' | 'launch';
  hardware: SystemHardwareInfo | null;
  config: ControlCenterConfig;
  downloadProgress: number; // 0 - 100
  downloadSpeed: string;
  isDownloading: boolean;
  statusMessage: string | null;

  setOpen: (open: boolean) => void;
  setActiveTab: (tab: 'platform' | 'models' | 'databases' | 'launch') => void;
  updateConfig: (patch: Partial<ControlCenterConfig>) => void;
  setHardware: (info: SystemHardwareInfo) => void;
  setDownloadProgress: (percent: number, speed: string) => void;
  setIsDownloading: (downloading: boolean) => void;
  setStatusMessage: (msg: string | null) => void;
  completeFirstRun: () => void;

  // Granular actions for API keys and substrates
  addApiKey: (initialKey?: string) => void;
  updateApiKey: (id: string, key: string) => void;
  removeApiKey: (id: string) => void;
  setKeyVerification: (id: string, verified: boolean, latencyMs?: number, error?: string) => void;
  updateSubstrate: (
    type: 'knowledgeGraph' | 'sessionMemory' | 'cacheAndSignals',
    patch: Partial<SubstrateConfig>
  ) => void;
}

const detectDefaultPlatform = (): TargetPlatform => {
  if (typeof window === 'undefined') return 'macos';
  const ua = window.navigator.userAgent.toLowerCase();
  const platform = (window.navigator.platform || '').toLowerCase();

  // Distinguish iPad from MacBook:
  // iPadOS Safari sends 'MacIntel' with maxTouchPoints > 1, but lacks physical keyboard/trackpad profile
  // MacBook Air has maxTouchPoints === 0 (or 1 on trackpad) and contains 'macintosh' / 'mac os x'
  const isTouchDevice =
    typeof window !== 'undefined' &&
    'ontouchstart' in window &&
    window.navigator.maxTouchPoints > 1;
  const isIPad =
    /ipad/.test(ua) || (platform === 'macintel' && isTouchDevice && !ua.includes('macintosh'));
  const isIPhone = /iphone|ipod/.test(ua);
  if (isIPad || isIPhone) return 'ios';
  if (/android/.test(ua)) return 'android';
  if (/macintosh|mac os x|macintel|darwin/.test(ua) || /mac|darwin/.test(platform)) return 'macos';
  if (/win/.test(platform) || /windows/.test(ua)) return 'windows';
  if (/linux/.test(platform) || /linux/.test(ua)) return 'linux';
  return 'macos';
};

const defaultPlatform = detectDefaultPlatform();

export const useControlCenterStore = create<ControlCenterState>()(
  persist(
    (set) => ({
      isOpen: false,
      activeTab: 'platform',
      hardware: {
        platform: defaultPlatform,
        osName: typeof window !== 'undefined' ? window.navigator.userAgent : 'Unknown OS',
        totalRamGb: 8.0,
        cpuCores: typeof window !== 'undefined' ? window.navigator.hardwareConcurrency || 8 : 8,
        hasMetalOrCuda: true,
      },
      downloadProgress: 0,
      downloadSpeed: '',
      isDownloading: false,
      statusMessage: null,
      config: {
        firstRunCompleted: typeof process !== 'undefined' && process.env.NODE_ENV === 'test',
        targetPlatform: defaultPlatform,
        llmDeployment: 'cloud',
        apiKeys: [
          {
            id: 'key-1',
            key: '',
            provider: 'unknown',
            providerName: 'Unconfigured Key',
            verified: null,
          },
        ],
        selectedLocalModel: 'llama3.2:3b',
        tunnelUrl: '',

        knowledgeGraph: {
          mode: 'local',
          uri: 'bolt://localhost:7687',
          password: '',
        },
        sessionMemory: {
          mode: 'in_memory_fallback',
        },
        cacheAndSignals: {
          mode: 'in_memory_fallback',
        },

        // Backward compatibility getters
        llmMode: 'cloud_groq',
        groqApiKey: '',
        geminiApiKey: '',
        neo4jMode: 'local',
        neo4jUri: 'bolt://localhost:7687',
        neo4jPassword: '',
        postgresMode: 'in_memory_fallback',
        redisMode: 'in_memory_fallback',
      },

      setOpen: (open) => set({ isOpen: open }),
      setActiveTab: (tab) => set({ activeTab: tab }),

      updateConfig: (patch) =>
        set((s) => {
          const updated = { ...s.config, ...patch };
          // Sync backward compatible fields
          if (patch.llmDeployment) {
            updated.llmMode = patch.llmDeployment === 'local' ? 'local_ollama' : 'cloud_groq';
          }
          if (patch.knowledgeGraph?.mode) {
            updated.neo4jMode = patch.knowledgeGraph.mode;
          }
          if (patch.sessionMemory?.mode) {
            updated.postgresMode = patch.sessionMemory.mode;
          }
          if (patch.cacheAndSignals?.mode) {
            updated.redisMode = patch.cacheAndSignals.mode;
          }
          return { config: updated };
        }),

      setHardware: (hardware) => set({ hardware }),
      setDownloadProgress: (percent, speed) =>
        set({ downloadProgress: percent, downloadSpeed: speed }),
      setIsDownloading: (isDownloading) => set({ isDownloading }),
      setStatusMessage: (statusMessage) => set({ statusMessage }),
      completeFirstRun: () =>
        set((s) => ({
          config: { ...s.config, firstRunCompleted: true },
          isOpen: false,
        })),

      addApiKey: (initialKey = '') => {
        const id = `key-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
        const detection = detectProviderFromKey(initialKey);
        const newEntry: CloudApiKeyEntry = {
          id,
          key: initialKey,
          provider: detection.provider,
          providerName: detection.displayName,
          verified: null,
        };
        set((s) => {
          const currentKeys = Array.isArray(s.config?.apiKeys) ? s.config.apiKeys : [];
          return {
            config: {
              ...s.config,
              apiKeys: [...currentKeys, newEntry],
            },
          };
        });
      },

      updateApiKey: (id, key) => {
        const detection = detectProviderFromKey(key);
        set((s) => {
          const currentKeys: CloudApiKeyEntry[] = Array.isArray(s.config?.apiKeys)
            ? s.config.apiKeys
            : [];
          const apiKeys = currentKeys.map((k: CloudApiKeyEntry) =>
            k.id === id
              ? {
                  ...k,
                  key,
                  provider: detection.provider,
                  providerName: detection.displayName,
                  verified: null,
                  latencyMs: undefined,
                  error: undefined,
                }
              : k
          );
          // Sync backward-compatible keys
          const groq = apiKeys.find((k: CloudApiKeyEntry) => k.provider === 'groq')?.key || '';
          const gemini = apiKeys.find((k: CloudApiKeyEntry) => k.provider === 'gemini')?.key || '';
          return {
            config: {
              ...s.config,
              apiKeys,
              groqApiKey: groq || s.config.groqApiKey,
              geminiApiKey: gemini || s.config.geminiApiKey,
            },
          };
        });
      },

      removeApiKey: (id) => {
        set((s) => {
          const currentKeys: CloudApiKeyEntry[] = Array.isArray(s.config?.apiKeys)
            ? s.config.apiKeys
            : [];
          const filtered = currentKeys.filter((k: CloudApiKeyEntry) => k.id !== id);
          return {
            config: {
              ...s.config,
              apiKeys:
                filtered.length > 0
                  ? filtered
                  : [
                      {
                        id: `key-${Date.now()}`,
                        key: '',
                        provider: 'unknown',
                        providerName: 'Unconfigured Key',
                        verified: null,
                      },
                    ],
            },
          };
        });
      },

      setKeyVerification: (id, verified, latencyMs, error) => {
        set((s) => {
          const currentKeys: CloudApiKeyEntry[] = Array.isArray(s.config?.apiKeys)
            ? s.config.apiKeys
            : [];
          return {
            config: {
              ...s.config,
              apiKeys: currentKeys.map((k: CloudApiKeyEntry) =>
                k.id === id ? { ...k, verified, latencyMs, error, isTesting: false } : k
              ),
            },
          };
        });
      },

      updateSubstrate: (type, patch) => {
        set((s) => {
          const current = s.config[type] || { mode: 'in_memory_fallback' };
          const updatedSub = { ...current, ...patch };
          const updatedConfig: ControlCenterConfig = {
            ...s.config,
            [type]: updatedSub,
          };
          if (type === 'knowledgeGraph' && patch.mode) {
            updatedConfig.neo4jMode = patch.mode;
          }
          if (type === 'sessionMemory' && patch.mode) {
            updatedConfig.postgresMode = patch.mode;
          }
          if (type === 'cacheAndSignals' && patch.mode) {
            updatedConfig.redisMode = patch.mode;
          }
          return { config: updatedConfig };
        });
      },
    }),
    {
      name: 'raise-control-center-storage',
      partialize: (state) => ({ config: state.config }),
      merge: (persistedState: any, currentState: ControlCenterState) => {
        const mergedConfig = {
          ...currentState.config,
          ...(persistedState?.config || {}),
        };
        // Clean out stale hardcoded temporary tunnel urls
        if (
          mergedConfig.tunnelUrl &&
          mergedConfig.tunnelUrl.includes('estimates-racial-aud-strap')
        ) {
          mergedConfig.tunnelUrl = '';
        }
        if (!Array.isArray(mergedConfig.apiKeys) || mergedConfig.apiKeys.length === 0) {
          mergedConfig.apiKeys = [
            {
              id: 'key-1',
              key: mergedConfig.groqApiKey || '',
              provider: mergedConfig.groqApiKey ? 'groq' : 'unknown',
              providerName: mergedConfig.groqApiKey ? 'Groq' : 'Unconfigured Key',
              verified: null,
            },
          ];
        }
        return {
          ...currentState,
          config: mergedConfig,
        };
      },
    }
  )
);
