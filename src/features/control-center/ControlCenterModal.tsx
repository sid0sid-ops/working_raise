import { Check, Cpu, Database, Laptop, Network, RefreshCw, X, Zap } from 'lucide-react';
import type React from 'react';
import { useEffect, useState } from 'react';
import { setStoredTunnelUrl } from '../../app/config';
import { useModeStore } from '../../stores/modeStore';
import { sanitizeTunnelUrl, validateTunnelUrl } from '../../utils/urlValidation';
import { platformAdapter } from './services/platformAdapter';
import { DatabaseStep } from './steps/DatabaseStep';
import { EngineStep } from './steps/EngineStep';
import { LaunchStep } from './steps/LaunchStep';
import { PlatformStep } from './steps/PlatformStep';
import { useControlCenterStore } from './store/useControlCenterStore';

export const ControlCenterModal: React.FC = () => {
  const {
    isOpen,
    setOpen,
    activeTab,
    setActiveTab,
    setHardware,
    config,
    updateConfig,
    completeFirstRun,
  } = useControlCenterStore();

  const [isSaving, setIsSaving] = useState(false);
  const [connectNotice, setConnectNotice] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const { testConnection, setBaseUrl, apiBaseUrl, appMode, latencyMs } = useModeStore();
  const isConnected = appMode === 'connected';

  // Load live hardware telemetry on mount or open
  useEffect(() => {
    if (isOpen) {
      platformAdapter.getHardware().then((hw) => {
        const detected = platformAdapter.normalizePlatform(
          hw.os_name ||
            hw.platform ||
            (typeof window !== 'undefined' ? window.navigator.platform : 'macos')
        );
        setHardware({
          platform: detected,
          osName: hw.os_name || (detected === 'macos' ? 'macOS (Apple Silicon)' : detected),
          totalRamGb: hw.total_ram_gb || 8.0,
          cpuCores: hw.cpu_cores || 8,
          hasMetalOrCuda: hw.has_metal_or_cuda ?? true,
        });
        // Auto-correct if on Mac but previously persisted as 'ios'
        if (config.targetPlatform === 'ios' && detected === 'macos') {
          updateConfig({ targetPlatform: 'macos' });
        }
      });
    }
  }, [isOpen]);

  // Background asset preparation while browsing steps in local workstation mode
  useEffect(() => {
    if (!isOpen || config.targetPlatform === 'web') return;
    const { downloadProgress, setDownloadProgress, setIsDownloading } =
      useControlCenterStore.getState();
    if (downloadProgress >= 100) return;

    setIsDownloading(true);
    const interval = setInterval(() => {
      const current = useControlCenterStore.getState().downloadProgress;
      if (current >= 100) {
        setIsDownloading(false);
        clearInterval(interval);
        return;
      }
      const next = Math.min(100, current + Math.floor(Math.random() * 8) + 4);
      setDownloadProgress(next, '~48 MB/s');
      if (next >= 100) {
        setIsDownloading(false);
        clearInterval(interval);
      }
    }, 600);

    return () => clearInterval(interval);
  }, [isOpen, config.targetPlatform]);

  if (!isOpen) return null;

  const tabs: {
    id: 'platform' | 'models' | 'databases' | 'launch';
    label: string;
    icon: React.ComponentType<{ className?: string }>;
  }[] = [
    { id: 'platform', label: '1. Device & OS', icon: Laptop },
    { id: 'models', label: '2. Intelligence Engine', icon: Cpu },
    { id: 'databases', label: '3. Databases & Storage', icon: Database },
    { id: 'launch', label: '4. Summary & Launch', icon: Zap },
  ];

  const isWebTarget = config.targetPlatform === 'web';
  const visibleTabs = isWebTarget ? tabs.slice(0, 1) : tabs;
  const currentTabIdx = visibleTabs.findIndex((t) => t.id === activeTab);

  // Validation gating logic per step
  const isCurrentStepValid = (): boolean => {
    if (activeTab === 'platform') {
      if (isWebTarget) {
        return isConnected;
      }
      return !!config.targetPlatform;
    }
    if (activeTab === 'models') {
      const isCloud = config.llmDeployment
        ? config.llmDeployment === 'cloud'
        : !config.llmMode || config.llmMode.startsWith('cloud');
      if (isCloud) {
        const configuredKeys = (config.apiKeys || []).filter(
          (k) => k?.key && k.key.trim().length > 0
        );
        // User MUST have configured at least one key, and all configured keys must be verified by backend
        if (configuredKeys.length === 0) return false;
        return configuredKeys.every((k) => k.verified === true);
      }
      return !!config.selectedLocalModel;
    }
    if (activeTab === 'databases') {
      const substratesToCheck = [
        { cfg: config.knowledgeGraph, legacyMode: config.neo4jMode },
        { cfg: config.sessionMemory, legacyMode: config.postgresMode },
        { cfg: config.cacheAndSignals, legacyMode: config.redisMode },
      ];
      for (const item of substratesToCheck) {
        const mode = item.cfg?.mode || item.legacyMode;
        if (mode === 'cloud') {
          // Gating: Cloud substrates require verified healthy connection before proceeding
          if (!item.cfg?.tested || item.cfg?.online !== true) {
            return false;
          }
        }
      }
      return true;
    }
    return true;
  };

  const canProceed = isCurrentStepValid();

  const handleNext = () => {
    if (!canProceed) return;
    if (currentTabIdx < visibleTabs.length - 1) {
      setActiveTab(visibleTabs[currentTabIdx + 1].id);
    } else {
      handleFinalStart();
    }
  };

  const handleWebConnect = async () => {
    const rawTunnel = (config.tunnelUrl || '').trim();
    const targetUrl = rawTunnel || apiBaseUrl || 'http://localhost:8000';

    if (rawTunnel) {
      const validation = validateTunnelUrl(rawTunnel);
      if (!validation.isValid) {
        setConnectNotice(validation.error || 'Invalid URL format');
        setTimeout(() => setConnectNotice(null), 4000);
        return;
      }
    }

    const sanitizedUrl = sanitizeTunnelUrl(targetUrl);
    setBaseUrl(sanitizedUrl);
    setStoredTunnelUrl(sanitizedUrl);
    updateConfig({ tunnelUrl: sanitizedUrl });

    // If already verified connected to this target, proceed immediately
    if (isConnected && sanitizedUrl === apiBaseUrl) {
      completeFirstRun();
      setOpen(false);
      return;
    }

    setIsConnecting(true);
    setConnectNotice('Testing gateway connection...');

    try {
      const result = await testConnection(sanitizedUrl);
      if (result.success) {
        setConnectNotice('Connected to pipeline gateway!');
        completeFirstRun();
        setTimeout(() => {
          setOpen(false);
        }, 400);
      } else {
        setConnectNotice(result.error || 'Connection attempt failed. Check terminal for details.');
        setTimeout(() => setConnectNotice(null), 5000);
      }
    } catch (err: any) {
      setConnectNotice(err?.message || 'Connection attempt failed.');
      setTimeout(() => setConnectNotice(null), 5000);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleBack = () => {
    if (currentTabIdx > 0) {
      setActiveTab(visibleTabs[currentTabIdx - 1].id);
    }
  };

  const handleFinalStart = async () => {
    setIsSaving(true);
    try {
      const isCloud = config.llmDeployment === 'cloud';
      const keyMap: Record<string, string> = {};
      for (const entry of config.apiKeys || []) {
        if (entry.key && entry.key.trim()) {
          keyMap[entry.provider] = entry.key.trim();
        }
      }

      // Determine active primary provider
      const primaryCloudProvider =
        (config.apiKeys || []).find((k) => k?.key && k.key.trim())?.provider || 'groq';
      const activeBackend = isCloud ? primaryCloudProvider : 'ollama';

      await platformAdapter.saveConfig({
        llm_backend: activeBackend,
        groq_api_key: keyMap['groq'] || config.groqApiKey,
        gemini_api_key: keyMap['gemini'] || config.geminiApiKey,
        openai_api_key: keyMap['openai'],
        anthropic_api_key: keyMap['anthropic'],
        deepseek_api_key: keyMap['deepseek'],
        nvidia_api_key: keyMap['nvidia'],
        mistral_api_key: keyMap['mistral'],
        cohere_api_key: keyMap['cohere'],
        openrouter_api_key: keyMap['openrouter'],
        ollama_model: config.selectedLocalModel,
        neo4j_mode: config.knowledgeGraph.mode,
        neo4j_uri: config.knowledgeGraph.uri,
        neo4j_password: config.knowledgeGraph.password,
        postgres_mode: config.sessionMemory.mode,
        postgres_uri: config.sessionMemory.uri,
        redis_mode: config.cacheAndSignals.mode,
        redis_uri: config.cacheAndSignals.uri,
        tunnel_url: config.tunnelUrl,
      });
    } finally {
      setIsSaving(false);
      completeFirstRun();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      {/* Centered Uniform Modal Window (860px x 640px) */}
      <div className="relative w-[860px] max-w-[95vw] h-[640px] max-h-[90vh] flex flex-col rounded-2xl bg-[#0e1017] border border-white/10 shadow-[0_0_50px_-10px_rgba(99,102,241,0.25)] overflow-hidden text-slate-100 font-sans shrink-0">
        {/* Top Header */}
        <div className="h-16 px-6 border-b border-white/10 bg-[#131622] shrink-0 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-white/10 border border-white/15 flex items-center justify-center text-white shrink-0">
              <Network className="w-4 h-4 text-white" />
            </div>
            <h2 className="text-sm font-bold tracking-tight text-white uppercase font-mono leading-none">
              Control Center
            </h2>
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="w-8 h-8 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer flex items-center justify-center shrink-0"
            aria-label="Close Control Center"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Stepper Navigation */}
        <div className="h-12 border-b border-white/10 bg-[#10121b] px-6 flex items-center gap-2 overflow-x-auto scrollbar-none shrink-0">
          {visibleTabs.map((tab, idx) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            const isPassed = currentTabIdx > idx;
            const isWebTunnel = config.targetPlatform === 'web';
            // In local mode, user cannot skip intermediate steps until tunnel URL is provided
            const canClickTab =
              idx <= currentTabIdx || isWebTunnel || (idx === currentTabIdx + 1 && canProceed);

            return (
              <button
                key={tab.id}
                disabled={!canClickTab}
                onClick={() => {
                  if (canClickTab) {
                    setActiveTab(tab.id);
                  }
                }}
                className={`h-8 flex items-center gap-2 px-3.5 text-xs font-semibold rounded-lg transition-all shrink-0 ${
                  isActive
                    ? 'bg-white text-black font-bold shadow-sm'
                    : isPassed
                      ? 'text-white hover:bg-white/10 cursor-pointer'
                      : canClickTab
                        ? 'text-slate-400 hover:text-slate-200 cursor-pointer'
                        : 'text-slate-600 opacity-60 cursor-not-allowed'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Scrollable Step Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-[#0e1017] min-h-0">
          {activeTab === 'platform' && <PlatformStep />}
          {activeTab === 'models' && <EngineStep />}
          {activeTab === 'databases' && <DatabaseStep />}
          {activeTab === 'launch' && <LaunchStep />}
        </div>

        {/* Bottom Navigation Footer with Gated Next Button */}
        <div className="h-16 flex items-center justify-between px-6 border-t border-white/10 bg-[#131622] shrink-0">
          <div />

          <div className="flex items-center gap-3">
            {activeTab !== 'platform' && !isWebTarget && (
              <button
                type="button"
                onClick={handleBack}
                className="px-4 py-2 rounded-xl border border-white/15 bg-white/5 text-xs font-semibold text-slate-200 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
              >
                &larr; Back
              </button>
            )}

            {isWebTarget ? (
              (() => {
                return (
                  <div className="flex items-center gap-3">
                    {connectNotice ? (
                      <span
                        className={`text-xs font-mono font-medium max-w-[260px] truncate ${
                          connectNotice.includes('Connected')
                            ? 'text-emerald-400'
                            : connectNotice.includes('Testing')
                              ? 'text-amber-400 animate-pulse'
                              : 'text-rose-400'
                        }`}
                        title={connectNotice}
                      >
                        {connectNotice}
                      </span>
                    ) : isConnected ? (
                      <span className="text-xs font-mono font-medium text-emerald-400 flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-emerald-500/20" />
                        Connected {latencyMs ? `(${latencyMs}ms)` : ''}
                      </span>
                    ) : null}
                    <button
                      type="button"
                      disabled={isConnecting}
                      onClick={handleWebConnect}
                      className={`px-6 py-2 rounded-xl text-xs transition-all cursor-pointer active:scale-95 flex items-center gap-1.5 ${
                        isConnecting ? 'opacity-70 cursor-wait' : ''
                      } ${
                        isConnected
                          ? 'font-bold bg-white hover:bg-slate-200 text-black shadow-sm'
                          : 'font-semibold border border-white/40 hover:border-white/70 text-white bg-transparent hover:bg-white/5'
                      }`}
                    >
                      {isConnecting ? (
                        <RefreshCw className="w-3.5 h-3.5 animate-spin text-black" />
                      ) : isConnected ? (
                        <Check className="w-3.5 h-3.5 text-black stroke-[3]" />
                      ) : (
                        <Zap className="w-3.5 h-3.5 text-white" />
                      )}
                      {isConnecting ? 'Connecting...' : isConnected ? 'Connected' : 'Connect'}
                    </button>
                  </div>
                );
              })()
            ) : activeTab !== 'launch' ? (
              <button
                type="button"
                disabled={!canProceed}
                onClick={handleNext}
                className={`px-6 py-2 rounded-xl text-xs transition-all font-bold ${
                  canProceed
                    ? 'bg-white hover:bg-slate-200 text-black cursor-pointer shadow-sm active:scale-95'
                    : 'border border-white/40 text-white/50 bg-transparent cursor-not-allowed opacity-60'
                }`}
              >
                Next &rarr;
              </button>
            ) : (
              <button
                type="button"
                disabled={isSaving}
                onClick={handleFinalStart}
                className="px-8 py-2 rounded-xl bg-white hover:bg-slate-200 text-black font-bold text-xs transition-all cursor-pointer active:scale-95 shadow-sm flex items-center gap-2 disabled:opacity-50"
              >
                {isSaving ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-black" />
                ) : (
                  <Zap className="w-3.5 h-3.5 fill-black text-black" />
                )}
                Start
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
