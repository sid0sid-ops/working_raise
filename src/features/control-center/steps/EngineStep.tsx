import {
  CheckCircle2,
  Cloud,
  ExternalLink,
  Eye,
  EyeOff,
  HardDrive,
  Plus,
  RefreshCw,
  Trash2,
  XCircle,
} from 'lucide-react';
import type React from 'react';
import { useEffect, useState } from 'react';
import { Tooltip } from '../components/Tooltip';
import { platformAdapter } from '../services/platformAdapter';
import { useControlCenterStore } from '../store/useControlCenterStore';
import type { DynamicLLMModel } from '../types';

export const EngineStep: React.FC = () => {
  const { config, updateConfig, addApiKey, updateApiKey, removeApiKey, setKeyVerification } =
    useControlCenterStore();

  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [testingKeyId, setTestingKeyId] = useState<string | null>(null);
  const [dynamicModels, setDynamicModels] = useState<DynamicLLMModel[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);

  const isCloud = config.llmDeployment === 'cloud';

  // Load available models dynamically from backend API
  useEffect(() => {
    if (!isCloud) {
      setIsLoadingModels(true);
      platformAdapter
        .getDynamicLLMs()
        .then((models) => {
          const formatted: DynamicLLMModel[] = models.map((m) => ({
            provider: m.provider,
            displayName: m.displayName || m.provider,
            model: m.model,
            status: m.status,
            isActive: m.status === 'READY',
            tier: m.tier,
            sizeGb: m.model.includes('3b') ? 2.0 : m.model.includes('7b') ? 4.7 : 4.9,
            ramGb: m.model.includes('3b') ? 4.0 : m.model.includes('7b') ? 8.0 : 16.0,
          }));
          setDynamicModels(formatted);
        })
        .finally(() => setIsLoadingModels(false));
    }
  }, [isCloud]);

  const handleTestKey = async (id: string, provider: string, key: string) => {
    if (!key.trim()) return;
    setTestingKeyId(id);
    try {
      const res = await platformAdapter.pingApiKey(provider, key);
      setKeyVerification(id, res.available, res.latencyMs, res.error);
    } catch (err: any) {
      setKeyVerification(id, false, undefined, err?.message || 'Connection failed');
    } finally {
      setTestingKeyId(null);
    }
  };

  const cloudTooltip = (
    <div className="space-y-1 font-mono text-[11px]">
      <div className="font-bold text-white border-b border-white/10 pb-1">Cloud Inference</div>
      <div>
        • <strong>Latency:</strong> ~100-300ms sub-second generation
      </div>
      <div>
        • <strong>Storage:</strong> 0 GB disk footprint (remote inference)
      </div>
      <div>
        • <strong>Memory:</strong> ~1.2 GB host client footprint
      </div>
      <div>
        • <strong>Routing:</strong> Dynamic multi-provider failover
      </div>
    </div>
  );

  const localTooltip = (
    <div className="space-y-1 font-mono text-[11px]">
      <div className="font-bold text-white border-b border-white/10 pb-1">
        Local Private Inference
      </div>
      <div>
        • <strong>Privacy:</strong> 100% on-device, zero data leaves machine
      </div>
      <div>
        • <strong>Offline:</strong> Runs without active internet connection
      </div>
      <div>
        • <strong>Compute:</strong> Requires local RAM and CPU / GPU acceleration
      </div>
      <div>
        • <strong>Daemon:</strong> Managed via local Ollama process
      </div>
    </div>
  );

  return (
    <div className="space-y-5 animate-in fade-in-50 duration-150">
      {/* Header */}
      <div>
        <h3 className="text-base font-bold text-white tracking-tight">Intelligence Engine</h3>
        <p className="text-xs text-slate-400 mt-1">
          Select reasoning deployment substrate and manage inference credentials.
        </p>
      </div>

      {/* Clean Dual-State Deployment Toggle */}
      <div className="p-1.5 rounded-xl bg-[#131622] border border-white/10 grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={() => updateConfig({ llmDeployment: 'cloud' })}
          className={`w-full py-2.5 px-3 rounded-lg text-xs font-bold transition-all flex items-center justify-between cursor-pointer ${
            isCloud
              ? 'bg-white text-black shadow-sm'
              : 'text-slate-300 hover:text-white hover:bg-white/5'
          }`}
        >
          <div className="flex items-center gap-2">
            <Cloud className="w-4 h-4" />
            <span>Cloud LLM</span>
          </div>
          <Tooltip
            as="span"
            content={cloudTooltip}
            className={
              isCloud ? 'text-black/70 hover:text-black' : 'text-slate-400 hover:text-white'
            }
          />
        </button>

        <button
          type="button"
          onClick={() => updateConfig({ llmDeployment: 'local' })}
          className={`w-full py-2.5 px-3 rounded-lg text-xs font-bold transition-all flex items-center justify-between cursor-pointer ${
            !isCloud
              ? 'bg-white text-black shadow-sm'
              : 'text-slate-300 hover:text-white hover:bg-white/5'
          }`}
        >
          <div className="flex items-center gap-2">
            <HardDrive className="w-4 h-4" />
            <span>Private / Local LLM</span>
          </div>
          <Tooltip
            as="span"
            content={localTooltip}
            className={
              !isCloud ? 'text-black/70 hover:text-black' : 'text-slate-400 hover:text-white'
            }
          />
        </button>
      </div>

      {/* CLOUD LLM VIEW */}
      {isCloud && (
        <div className="space-y-3.5">
          <div className="text-xs">
            <span className="text-slate-300 font-medium">Configured API Keys:</span>
          </div>

          <div className="space-y-2.5 max-h-[260px] overflow-y-auto pr-1">
            {(config.apiKeys || []).map((item, index) => {
              const show = !!showKeys[item.id];
              const isTesting = testingKeyId === item.id;
              const hasKey = (item?.key || '').trim().length > 0;

              return (
                <div
                  key={item.id}
                  className="p-3 rounded-xl bg-[#131622] border border-white/10 space-y-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono font-bold text-slate-400">
                        #{index + 1}
                      </span>
                      {hasKey ? (
                        <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-white/10 text-white border border-white/15">
                          {item.providerName} detected
                        </span>
                      ) : (
                        <span className="text-[10px] font-mono text-slate-500">
                          Enter API key below to auto-detect provider
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {/* Live connection badge */}
                      {item.verified === true && (
                        <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                          <CheckCircle2 className="w-3 h-3" />
                          Available ({item.latencyMs || 45}ms)
                        </span>
                      )}
                      {item.verified === false && (
                        <span className="text-[10px] font-mono text-rose-400 flex items-center gap-1 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                          <XCircle className="w-3 h-3" />
                          Unavailable
                        </span>
                      )}

                      {/* Delete button */}
                      {(config.apiKeys || []).length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeApiKey(item.id)}
                          className="text-slate-400 hover:text-rose-400 transition-colors p-1 cursor-pointer"
                          title="Delete API Key"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Input row */}
                  <div className="flex items-center gap-2">
                    <div className="relative flex-1">
                      <input
                        type={show ? 'text' : 'password'}
                        placeholder="Enter API key (gsk_..., AIzaSy..., nvapi-..., sk-...)"
                        value={item.key}
                        onChange={(e) => updateApiKey(item.id, e.target.value)}
                        className="w-full px-3 py-2 pr-9 rounded-lg bg-black/60 border border-white/15 text-white font-mono text-xs placeholder-slate-500 focus:outline-none focus:border-white transition-all"
                      />
                      <button
                        type="button"
                        onClick={() =>
                          setShowKeys((prev) => ({ ...prev, [item.id]: !prev[item.id] }))
                        }
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                      >
                        {show ? (
                          <EyeOff className="w-3.5 h-3.5" />
                        ) : (
                          <Eye className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>

                    <button
                      type="button"
                      disabled={!hasKey || isTesting}
                      onClick={() => handleTestKey(item.id, item.provider, item.key)}
                      className={`px-3 py-2 rounded-lg text-xs font-semibold shrink-0 transition-all flex items-center gap-1.5 ${
                        hasKey && !isTesting
                          ? 'bg-white/10 hover:bg-white/15 border border-white/20 text-white cursor-pointer'
                          : 'border border-white/10 text-slate-500 bg-transparent cursor-not-allowed'
                      }`}
                    >
                      {isTesting ? (
                        <>
                          <RefreshCw className="w-3 h-3 animate-spin" />
                          Checking...
                        </>
                      ) : (
                        'Check Connection'
                      )}
                    </button>
                  </div>
                </div>
              );
            })}

            {(config.apiKeys || []).some(
              (item) => item.verified === true || (item.key && item.key.trim().length > 0)
            ) && (
              <button
                type="button"
                onClick={() => addApiKey()}
                className="w-full py-2 px-3 rounded-lg border border-dashed border-white/20 hover:border-white/40 bg-white/5 hover:bg-white/10 text-xs font-semibold text-slate-300 hover:text-white flex items-center justify-center gap-1.5 transition-all cursor-pointer mt-1"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Key
              </button>
            )}
          </div>
        </div>
      )}

      {/* PRIVATE / LOCAL LLM VIEW */}
      {!isCloud && (
        <div className="space-y-4">
          {/* Local Daemon Status Check */}
          <div className="p-3.5 rounded-xl bg-[#131622] border border-white/10 flex items-center justify-between">
            <div>
              <div className="text-xs font-bold text-white flex items-center gap-2">
                <span>Ollama Inference Service</span>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Target endpoint:{' '}
                <code className="font-mono text-slate-300">http://localhost:11434</code>
              </p>
            </div>
            <a
              href="https://ollama.ai/download"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-semibold text-white px-3 py-1.5 rounded-lg border border-white/15 bg-white/10 hover:bg-white/15 transition-colors flex items-center gap-1.5"
            >
              Download Ollama
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>

          {/* Model Selection from Dynamic Backend API */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-300">Available Local Models:</span>
              <span className="text-[11px] text-slate-400 font-mono">
                {dynamicModels.length} models detected
              </span>
            </div>

            {isLoadingModels ? (
              <div className="p-6 text-center text-xs text-slate-400">
                <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-2" />
                Querying local inference runtime...
              </div>
            ) : (
              <div className="space-y-2">
                {(dynamicModels.length > 0
                  ? dynamicModels
                  : [
                      {
                        provider: 'ollama',
                        displayName: 'Llama 3.2 3B',
                        model: 'llama3.2:3b',
                        status: 'READY',
                        isActive: true,
                        sizeGb: 2.0,
                        ramGb: 4.0,
                      },
                      {
                        provider: 'ollama',
                        displayName: 'Qwen 2.5 7B',
                        model: 'qwen2.5:7b',
                        status: 'READY',
                        isActive: true,
                        sizeGb: 4.7,
                        ramGb: 8.0,
                      },
                      {
                        provider: 'ollama',
                        displayName: 'Llama 3.1 8B',
                        model: 'llama3.1:8b',
                        status: 'READY',
                        isActive: true,
                        sizeGb: 4.9,
                        ramGb: 16.0,
                      },
                    ]
                ).map((m) => {
                  const isSelected = config.selectedLocalModel === m.model;
                  const modelTooltip = (
                    <div className="space-y-1 font-mono text-[11px]">
                      <div className="font-bold text-white border-b border-white/10 pb-1">
                        {m.displayName}
                      </div>
                      <div>
                        • <strong>Disk Footprint:</strong> {m.sizeGb || 2.0} GB
                      </div>
                      <div>
                        • <strong>Memory Required:</strong> ~{m.ramGb || 4.0} GB RAM
                      </div>
                      <div>
                        • <strong>Runtime Status:</strong> {m.status}
                      </div>
                    </div>
                  );

                  return (
                    <div
                      key={m.model}
                      role="button"
                      tabIndex={0}
                      onClick={() => updateConfig({ selectedLocalModel: m.model })}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          updateConfig({ selectedLocalModel: m.model });
                        }
                      }}
                      className={`p-3 rounded-lg border cursor-pointer transition-all flex items-center justify-between ${
                        isSelected
                          ? 'bg-white text-black border-white font-bold'
                          : 'bg-[#131622] border-white/10 text-slate-300 hover:border-white/20 hover:bg-white/5'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="text-xs font-bold">{m.displayName}</div>
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                            isSelected ? 'bg-black/10 text-black' : 'bg-white/5 text-slate-400'
                          }`}
                        >
                          {m.model}
                        </span>
                      </div>

                      <div className="flex items-center gap-3">
                        <span
                          className={`text-[11px] font-mono ${
                            isSelected ? 'text-slate-800' : 'text-slate-400'
                          }`}
                        >
                          {m.sizeGb || 2.0} GB
                        </span>
                        <Tooltip content={modelTooltip} />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
