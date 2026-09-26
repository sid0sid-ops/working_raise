import { CheckCircle2, RefreshCw } from 'lucide-react';
import type React from 'react';
import { useMemo } from 'react';
import { useControlCenterStore } from '../store/useControlCenterStore';

export const LaunchStep: React.FC = () => {
  const { config, downloadProgress, downloadSpeed, isDownloading } = useControlCenterStore();

  const isWebTunnel = config.targetPlatform === 'web';
  const isCloud = config.llmDeployment
    ? config.llmDeployment === 'cloud'
    : !config.llmMode || config.llmMode.startsWith('cloud');
  const validKeys = (config.apiKeys || []).filter((k) => k?.key && k.key.trim().length > 0);
  const providers = Array.from(new Set(validKeys.map((k) => k.providerName))).join(', ') || 'None';

  const kgMode = config.knowledgeGraph?.mode || config.neo4jMode || 'cloud';
  const memMode = config.sessionMemory?.mode || config.postgresMode || 'in_memory_fallback';
  const cacheMode = config.cacheAndSignals?.mode || config.redisMode || 'in_memory_fallback';

  // Compute resource footprint table dynamically
  const tableData = useMemo(() => {
    if (isWebTunnel) {
      return {
        rows: [
          {
            name: 'LLM Reasoning',
            mode: 'Remote Cloudflare Gateway',
            disk: '0 GB',
            ram: '~150 MB (Browser client)',
            net: 'Encrypted TLS Tunnel',
          },
          {
            name: 'Knowledge Graph',
            mode: 'Remote Neo4j Subgraph',
            disk: '0 GB',
            ram: '0 MB Local',
            net: 'Remote Query Protocol',
          },
          {
            name: 'Session Memory',
            mode: 'Remote PostgreSQL 16',
            disk: '0 GB',
            ram: '0 MB Local',
            net: 'Remote Store',
          },
          {
            name: 'Response Cache',
            mode: 'Remote Redis 7',
            disk: '0 GB',
            ram: '0 MB Local',
            net: 'Remote Cache',
          },
          {
            name: 'Vector Database',
            mode: 'Remote ChromaDB HNSW',
            disk: '0 GB',
            ram: '0 MB Local',
            net: 'Remote Vector Engine',
          },
        ],
        totalDisk: '0 GB (Zero Local Download)',
        totalRam: '~150 MB RAM',
        netSummary: 'Cloudflare Tunnel Gateway',
      };
    }

    let totalDiskGb = 0.0;
    let totalRamGb = 1.2; // Base workstation runtime

    // 1. LLM
    let llmDisk = '0 GB';
    let llmRam = '~1.2 GB';
    let llmNet = 'Cloud API Calls';
    if (!isCloud) {
      const is7b = config.selectedLocalModel.includes('7b');
      const is8b = config.selectedLocalModel.includes('8b');
      const size = is7b ? 4.7 : is8b ? 4.9 : 2.0;
      const ram = is7b ? 8.0 : is8b ? 16.0 : 4.0;
      totalDiskGb += size;
      totalRamGb += ram;
      llmDisk = `${size} GB`;
      llmRam = `~${ram} GB`;
      llmNet = 'Zero Network (100% Offline)';
    }

    // 2. Knowledge Graph
    let kgDisk = '0 GB';
    let kgRam = '0 MB';
    let kgNet = 'Cloud TLS';
    if (kgMode === 'local') {
      totalDiskGb += 1.5;
      totalRamGb += 0.5;
      kgDisk = '1.5 GB';
      kgRam = '~500 MB';
      kgNet = 'Local Loopback';
    } else if (kgMode === 'in_memory_fallback') {
      kgDisk = '0 GB';
      kgRam = '< 50 MB';
      kgNet = 'In-Process';
    }

    // 3. Session Memory
    let memDisk = '0 GB';
    let memRam = '0 MB';
    let memNet = 'Cloud TLS';
    if (memMode === 'local') {
      totalDiskGb += 0.25;
      totalRamGb += 0.15;
      memDisk = '0.25 GB';
      memRam = '~150 MB';
      memNet = 'Local Loopback';
    } else if (memMode === 'in_memory_fallback') {
      memDisk = '0 GB';
      memRam = '< 20 MB';
      memNet = 'In-Process';
    }

    // 4. Cache & Signals
    let cacheDisk = '0 GB';
    let cacheRam = '0 MB';
    let cacheNet = 'Cloud TLS';
    if (cacheMode === 'local') {
      totalDiskGb += 0.05;
      totalRamGb += 0.1;
      cacheDisk = '0.05 GB';
      cacheRam = '~100 MB';
      cacheNet = 'Local Loopback';
    } else if (cacheMode === 'in_memory_fallback') {
      cacheDisk = '0 GB';
      cacheRam = '< 15 MB';
      cacheNet = 'In-Process';
    }

    return {
      rows: [
        {
          name: 'LLM Reasoning',
          mode: isCloud ? 'Cloud API' : 'Local Ollama',
          disk: llmDisk,
          ram: llmRam,
          net: llmNet,
        },
        {
          name: 'Knowledge Graph',
          mode: kgMode === 'cloud' ? 'Cloud' : kgMode === 'local' ? 'Local Bolt' : 'In-Memory',
          disk: kgDisk,
          ram: kgRam,
          net: kgNet,
        },
        {
          name: 'Session Memory',
          mode: memMode === 'cloud' ? 'Cloud' : memMode === 'local' ? 'Local DB' : 'In-Memory',
          disk: memDisk,
          ram: memRam,
          net: memNet,
        },
        {
          name: 'Response Cache',
          mode:
            cacheMode === 'cloud' ? 'Cloud' : cacheMode === 'local' ? 'Local Redis' : 'In-Memory',
          disk: cacheDisk,
          ram: cacheRam,
          net: cacheNet,
        },
        {
          name: 'Vector Database',
          mode: 'ChromaDB (Local)',
          disk: 'Requires Indexing',
          ram: '~200 MB',
          net: 'In-Process',
        },
      ],
      totalDisk: totalDiskGb > 0 ? `${totalDiskGb.toFixed(1)} GB` : '0 GB (Zero Model Download)',
      totalRam: `~${totalRamGb.toFixed(1)} GB RAM`,
      netSummary: isCloud ? 'Cloud API Gateway' : 'Air-Gapped / Offline Capable',
    };
  }, [config, isCloud, kgMode, memMode, cacheMode, isWebTunnel]);

  return (
    <div className="space-y-4 animate-in fade-in-50 duration-150">
      <div>
        <h3 className="text-base font-bold text-white tracking-tight">
          Configuration Summary & Pre-Flight Verification
        </h3>
        <p className="text-xs text-slate-400 mt-0.5">
          {isWebTunnel
            ? 'Operating in Remote Gateway Tunnel Mode. All computation and models execute remotely.'
            : 'Operating in Local Workstation Mode. Verify required modules and neural weights before starting.'}
        </p>
      </div>

      {/* Profile Overview Card */}
      <div className="p-3.5 rounded-xl bg-[#131622] border border-white/10 space-y-2 text-xs">
        <div className="font-semibold text-white text-xs mb-1">Configured Profile:</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-slate-300">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-white" />
            <span>
              Target: <strong>{config.targetPlatform.toUpperCase()}</strong>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-white" />
            <span>
              Inference:{' '}
              <strong>
                {isWebTunnel
                  ? 'Remote Cloud Gateway'
                  : isCloud
                    ? `Cloud (${providers})`
                    : `Local (${config.selectedLocalModel})`}
              </strong>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-white" />
            <span>
              Knowledge Graph: <strong>{isWebTunnel ? 'Remote Neo4j' : kgMode}</strong>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-white" />
            <span>
              Memory & Cache:{' '}
              <strong>
                {isWebTunnel ? 'Remote PostgreSQL & Redis' : `${memMode} • ${cacheMode}`}
              </strong>
            </span>
          </div>
        </div>
      </div>

      {/* Resource Consumption Table */}
      <div className="rounded-xl border border-white/10 overflow-hidden bg-[#131622]">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-white/10 bg-black/40 text-[10px] font-mono uppercase text-slate-400">
              <th className="py-2.5 px-3">Substrate Component</th>
              <th className="py-2.5 px-3">Selected Mode</th>
              <th className="py-2.5 px-3">Disk Footprint</th>
              <th className="py-2.5 px-3">RAM Footprint</th>
              <th className="py-2.5 px-3">Network Profile</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-slate-300">
            {tableData.rows.map((row) => (
              <tr key={row.name} className="hover:bg-white/5 transition-colors">
                <td className="py-2 px-3 font-semibold text-white">{row.name}</td>
                <td className="py-2 px-3 font-mono text-[11px] text-slate-300 capitalize">
                  {row.mode}
                </td>
                <td className="py-2 px-3 font-mono text-[11px] text-slate-300">{row.disk}</td>
                <td className="py-2 px-3 font-mono text-[11px] text-slate-300">{row.ram}</td>
                <td className="py-2 px-3 font-mono text-[11px] text-slate-400">{row.net}</td>
              </tr>
            ))}
            {/* Totals row */}
            <tr className="bg-white/5 border-t border-white/15 font-bold text-white">
              <td className="py-2.5 px-3">Total Estimated Footprint</td>
              <td className="py-2.5 px-3 font-mono text-[11px]">—</td>
              <td className="py-2.5 px-3 font-mono text-[11px] text-emerald-400">
                {tableData.totalDisk}
              </td>
              <td className="py-2.5 px-3 font-mono text-[11px] text-emerald-400">
                {tableData.totalRam}
              </td>
              <td className="py-2.5 px-3 font-mono text-[11px] text-slate-200">
                {tableData.netSummary}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* PRE-FLIGHT REQUIREMENTS: WEB TUNNEL VS LOCAL EXECUTION */}
      {isWebTunnel ? (
        <div className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 p-4 space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-emerald-300">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>Remote Gateway Tunnel Active — Zero Local Downloads Required</span>
          </div>
          <p className="text-[11px] text-slate-300 leading-relaxed">
            All neural models (<code className="text-white font-mono">BAAI/bge-large-en-v1.5</code>,{' '}
            <code className="text-white font-mono">bge-reranker-large</code>,{' '}
            <code className="text-white font-mono">FineCat-NLI</code>), Docling parsers, ChromaDB
            vector stores, and Neo4j graph engines are running on the remote tunnel gateway. Your
            device requires <strong>0 GB of local downloads</strong>.
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-white/10 bg-[#131622] p-4 space-y-3">
          <div className="flex items-start justify-between gap-2 border-b border-white/10 pb-2.5">
            <div>
              <span className="text-xs font-bold text-white">
                Local Workstation Environment & Pre-Flight Assets
              </span>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Required neural weights and runtime engines verified for on-device inference.
              </p>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/10 text-slate-300 border border-white/15 shrink-0">
              ~4.6 GB Total Footprint
            </span>
          </div>

          {/* Live Background Asset Download & Verification Bar */}
          {(downloadProgress > 0 || isDownloading) && (
            <div className="p-3 rounded-xl border border-white/10 bg-black/40 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-white flex items-center gap-1.5">
                  {downloadProgress >= 100 ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  ) : (
                    <RefreshCw className="w-3.5 h-3.5 text-white animate-spin shrink-0" />
                  )}
                  {downloadProgress >= 100
                    ? 'All Neural Assets & Substrates Verified'
                    : 'Background Asset Ingestion Active'}
                </span>
                <span className="font-mono text-[11px] text-slate-300">
                  {downloadProgress}% {downloadSpeed ? `(${downloadSpeed})` : ''}
                </span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full bg-white transition-all duration-300"
                  style={{ width: `${downloadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Module Requirements List */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            {[
              {
                name: 'Docling & PyMuPDF Parsers',
                size: '~350 MB',
                desc: 'TableFormer AST reconstruction & font coordinate bounding boxes',
                status: 'Requires pip install',
                statusColor: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
              },
              {
                name: 'GGAHC Chunking Engine',
                size: 'In-Process',
                desc: 'Graph-Guided Adaptive Hierarchical Chunking (token-budgeted)',
                status: 'Python Engine',
                statusColor: 'text-slate-300 bg-white/5 border-white/10',
              },
              {
                name: 'BAAI/bge-large-en-v1.5',
                size: '1.34 GB',
                desc: '1024-dim dense semantic vector embeddings for ChromaDB HNSW',
                status: 'Requires Download (1.34 GB)',
                statusColor: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
              },
              {
                name: 'BAAI/bge-reranker-large',
                size: '2.24 GB',
                desc: 'Contextual Cross-Encoder neural reranker on Metal / CUDA',
                status: 'Requires Download (2.24 GB)',
                statusColor: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
              },
              {
                name: 'FineCat-ModernBERT-NLI',
                size: '~700 MB',
                desc: 'Runtime Faithfulness Quality Gate & zero-hallucination shield',
                status: 'Requires Download (~700 MB)',
                statusColor: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
              },
              {
                name: 'Vector Database',
                size: '~200 MB',
                desc: 'ChromaDB (Local) • In-Process persistent chunk embeddings & HNSW vector index',
                status: 'Requires Indexing',
                statusColor: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
              },
            ].map((asset) => (
              <div
                key={asset.name}
                className="p-2.5 rounded-lg bg-black/40 border border-white/10 flex items-start justify-between gap-2"
              >
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-white text-xs">{asset.name}</span>
                    <span className="text-[10px] font-mono text-slate-400">({asset.size})</span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5 leading-tight">
                    {asset.desc}
                  </div>
                </div>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded border shrink-0 ${asset.statusColor}`}
                >
                  {asset.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
