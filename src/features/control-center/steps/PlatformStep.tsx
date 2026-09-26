import {
  Check,
  ChevronDown,
  ChevronUp,
  Copy,
  Globe,
  Laptop,
  Smartphone,
  Terminal,
  X,
} from 'lucide-react';
import type React from 'react';
import { useEffect, useState } from 'react';
import { getStoredTunnelUrl, setStoredTunnelUrl } from '../../../app/config';
import { useModeStore } from '../../../stores/modeStore';
import { Tooltip } from '../components/Tooltip';
import { useControlCenterStore } from '../store/useControlCenterStore';
import type { TargetPlatform } from '../types';

export const PlatformStep: React.FC = () => {
  const { hardware, config, updateConfig } = useControlCenterStore();
  const { appMode, isProbing, latencyMs } = useModeStore();
  const isConnected = appMode === 'connected';
  const [isSelectorOpen, setIsSelectorOpen] = useState(false);

  // Tunnel state
  const defaultTunnel = config.tunnelUrl || getStoredTunnelUrl() || '';
  const [tunnelInput, setTunnelInput] = useState(defaultTunnel);
  const [copied, setCopied] = useState(false);

  // Dynamic local time formatting (e.g., 7:25 PM)
  const [currentTime, setCurrentTime] = useState('');
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(
        now.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true })
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 30000);
    return () => clearInterval(interval);
  }, []);

  const clientOSLabel =
    hardware?.platform === 'macos'
      ? 'Mac'
      : hardware?.platform === 'windows'
        ? 'Windows'
        : hardware?.platform === 'linux'
          ? 'Linux'
          : 'Device';

  const platforms: {
    id: TargetPlatform;
    label: string;
    sub: string;
    icon: React.ComponentType<{ className?: string }>;
  }[] = [
    {
      id: 'macos',
      label: 'macOS',
      sub: 'Desktop Workstation (Local Metal acceleration)',
      icon: Laptop,
    },
    {
      id: 'web',
      label: 'Web Client',
      sub: 'Browser & Remote Cloudflare Tunnel Gateway (Zero Local Download)',
      icon: Globe,
    },
    {
      id: 'windows',
      label: 'Windows',
      sub: 'Desktop Workstation (Local DirectML / CUDA acceleration)',
      icon: Laptop,
    },
    {
      id: 'linux',
      label: 'Linux',
      sub: 'Desktop Workstation (Local CUDA / ROCm)',
      icon: Terminal,
    },
    {
      id: 'android',
      label: 'Android APK',
      sub: 'Mobile & Tablet Native Build',
      icon: Smartphone,
    },
    {
      id: 'ios',
      label: 'iOS / iPadOS',
      sub: 'iPhone & iPad Swift Native Build',
      icon: Smartphone,
    },
  ];

  const currentPlatform = platforms.find((p) => p.id === config.targetPlatform) || platforms[0];
  const CurrentIcon = currentPlatform.icon;

  const handleTunnelChange = (val: string) => {
    setTunnelInput(val);
    const cleaned = val.trim().replace(/\/+$/, '');
    updateConfig({ tunnelUrl: cleaned });
    if (cleaned) {
      setStoredTunnelUrl(cleaned);
    }
  };

  const handleCopyUrl = async () => {
    if (!tunnelInput) return;
    try {
      await navigator.clipboard.writeText(tunnelInput);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  const handleClearUrl = () => {
    setTunnelInput('');
    setStoredTunnelUrl('');
    updateConfig({ tunnelUrl: '' });
  };

  return (
    <div className="space-y-4 animate-in fade-in-50 duration-150">
      <div>
        <h3 className="text-base font-bold text-white tracking-tight">Device & Operating System</h3>
        <p className="text-xs text-slate-400 mt-0.5">
          Auto-detected system configuration. Select Web Client to connect via remote tunnel with
          zero downloads.
        </p>
      </div>

      {/* Single Configuration Box with Dropdown Toggle */}
      <div className="rounded-xl bg-[#131622] border border-white/10 overflow-hidden">
        <div
          role="button"
          tabIndex={0}
          onClick={() => setIsSelectorOpen(!isSelectorOpen)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              setIsSelectorOpen(!isSelectorOpen);
            }
          }}
          className="p-3.5 flex items-center justify-between cursor-pointer hover:bg-white/5 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-white/10 border border-white/15 flex items-center justify-center text-white shrink-0">
              <CurrentIcon className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400 font-mono">Active Target:</span>
                <span className="text-xs font-bold text-white">{currentPlatform.label}</span>
                <Tooltip
                  content={
                    <div className="space-y-1 font-mono text-[11px]">
                      <div className="font-bold text-white text-xs border-b border-white/10 pb-1">
                        {currentPlatform.label} Target
                      </div>
                      <div className="text-slate-300">{currentPlatform.sub}</div>
                    </div>
                  }
                />
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              className="text-xs font-semibold px-2.5 py-1 rounded-md border border-white/20 bg-white/10 hover:bg-white/15 text-white transition-all cursor-pointer"
            >
              {isSelectorOpen ? 'Close' : 'Change Target'}
            </button>
            {isSelectorOpen ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </div>
        </div>

        {/* Vertical Layers Selection Drawer */}
        {isSelectorOpen && (
          <div className="border-t border-white/10 bg-[#0e1017] p-2.5 space-y-1.5 animate-in slide-in-from-top-2 duration-150">
            <div className="text-[11px] font-mono text-slate-400 px-2 pb-1">
              Select deployment environment:
            </div>
            {platforms.map((p) => {
              const Icon = p.icon;
              const isSelected = config.targetPlatform === p.id;
              return (
                <div
                  key={p.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => {
                    updateConfig({ targetPlatform: p.id });
                    setIsSelectorOpen(false);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      updateConfig({ targetPlatform: p.id });
                      setIsSelectorOpen(false);
                    }
                  }}
                  className={`p-2.5 rounded-lg border transition-all cursor-pointer flex items-center justify-between ${
                    isSelected
                      ? 'bg-white text-black border-white font-bold'
                      : 'bg-white/5 border-white/10 text-slate-300 hover:border-white/20 hover:bg-white/10'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className={`w-4 h-4 ${isSelected ? 'text-black' : 'text-slate-300'}`} />
                    <div>
                      <div className="text-xs font-bold">{p.label}</div>
                      <div
                        className={`text-[10px] ${isSelected ? 'text-slate-800' : 'text-slate-400'}`}
                      >
                        {p.sub}
                      </div>
                    </div>
                  </div>

                  {isSelected && <Check className="w-4 h-4 text-black stroke-[3]" />}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* WEB / GATEWAY TUNNEL CONFIGURATION SECTION */}
      {config.targetPlatform === 'web' && (
        <div className="p-4 rounded-xl bg-[#131622] border border-white/10 space-y-3 animate-in fade-in duration-150">
          {/* Status Header */}
          <div className="flex items-center justify-between border-b border-white/10 pb-2.5">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-white">Pipeline Tunnel & Gateway</span>
              <span
                data-testid="connection-status-dot"
                className={`relative inline-flex rounded-full h-2 w-2 shrink-0 transition-colors ${
                  isConnected
                    ? 'bg-emerald-500 ring-2 ring-emerald-500/20'
                    : isProbing
                      ? 'bg-amber-500 animate-pulse ring-2 ring-amber-500/20'
                      : 'bg-rose-500 ring-2 ring-rose-500/20'
                }`}
              />
              {isConnected && (
                <span className="text-[11px] font-mono font-medium text-emerald-400">
                  • Connected {latencyMs ? `(${latencyMs}ms)` : ''}
                </span>
              )}
              <Tooltip
                content={
                  <div className="space-y-1 font-mono text-[11px]">
                    <div className="font-bold text-white text-xs border-b border-white/10 pb-1">
                      Remote Cloudflare Tunnel
                    </div>
                    <div className="text-slate-300">
                      Connect to your remote FastAPI, LangGraph, and vector store gateway with zero
                      local downloads or GPU requirements.
                    </div>
                  </div>
                }
              />
            </div>
          </div>

          {/* Pipeline Tunnel URL Input */}
          <div className="space-y-1.5">
            <label
              htmlFor="pipeline-tunnel-url-input"
              className="text-xs font-semibold text-slate-200 block"
            >
              Pipeline Tunnel URL
            </label>
            <div className="relative">
              <input
                id="pipeline-tunnel-url-input"
                type="text"
                value={tunnelInput}
                onChange={(e) => handleTunnelChange(e.target.value)}
                placeholder="https://your-tunnel-name.trycloudflare.com"
                className="w-full px-3 py-2 pr-9 rounded-lg bg-black/60 border border-white/15 text-white font-mono text-xs placeholder-slate-500 focus:outline-none focus:border-white transition-all"
              />
              {tunnelInput.length > 0 && (
                <button
                  type="button"
                  onClick={handleClearUrl}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white cursor-pointer"
                  title="Clear input"
                  aria-label="Clear input"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Secondary Info: Copy URL + Client System & Time */}
          <div className="flex flex-wrap items-center justify-between text-xs text-slate-400 pt-0.5">
            <Tooltip as="span" size="sm" content={copied ? 'Copied!' : 'Copy URL'}>
              <button
                type="button"
                onClick={handleCopyUrl}
                disabled={!tunnelInput}
                className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
                aria-label="Copy URL"
                title={copied ? 'Copied!' : 'Copy URL'}
              >
                {copied ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
              </button>
            </Tooltip>

            <div className="font-mono text-[11px] text-slate-300">
              <span className="text-slate-400">Client System & Time: </span>
              <strong>
                {clientOSLabel} • {currentTime || '7:25 PM'}
              </strong>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
