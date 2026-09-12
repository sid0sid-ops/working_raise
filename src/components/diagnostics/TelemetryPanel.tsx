import React, { useEffect, useState } from 'react';
import { systemService } from '../../services/SystemService';
import { HardwareTelemetry, Neo4jStatus } from '../../types';
import { useModeStore } from '../../stores/modeStore';
import { Cpu, Database, ShieldCheck, ShieldAlert, AlertTriangle, WifiOff, Laptop, Server, CheckCircle2 } from 'lucide-react';
import { Badge } from '../ui/Badge';
import { formatMb } from '../../utils/formatters';

export const TelemetryPanel: React.FC = () => {
  const { appMode, apiBaseUrl } = useModeStore();
  const [telemetry, setTelemetry] = useState<HardwareTelemetry | null>(null);
  const [neo4j, setNeo4j] = useState<Neo4jStatus | null>(null);

  useEffect(() => {
    let isMounted = true;
    const loadStats = async () => {
      try {
        const [tRes, nRes] = await Promise.all([
          systemService.getHardwareTelemetry(),
          systemService.getNeo4jStatus(),
        ]);
        if (isMounted) {
          if (tRes.data) setTelemetry(tRes.data);
          if (nRes.data) setNeo4j(nRes.data);
        }
      } catch {
        // ignore
      }
    };

    loadStats();
    return () => {
      isMounted = false;
    };
  }, [appMode]);

  const isMock = appMode === 'mock';
  const isOffline = appMode === 'offline';
  const isConnected = appMode === 'connected';

  return (
    <div className="space-y-4 text-xs">
      {/* Topology Status Header */}
      {isMock && (
        <div className="p-3.5 bg-amber-950/40 border border-amber-800/70 rounded-xl text-amber-200 text-xs flex items-start gap-3 shadow-sm">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-amber-300">
                Simulated Workstation Telemetry (Offline Mock Mode)
              </span>
              <Badge variant="warning">MOCK DATA</Badge>
            </div>
            <p className="text-amber-400/90 text-[11px] leading-relaxed">
              The frontend is operating in offline/mock mode without a live connection to the remote backend.
              Hardware metrics displayed below are <strong>simulated fixtures</strong> for interface verification.
            </p>
            <div className="flex items-center gap-4 text-[11px] text-amber-300/80 pt-1 font-mono">
              <span className="flex items-center gap-1.5">
                <Laptop className="w-3.5 h-3.5 text-sky-400" /> Client: Web Client
              </span>
              <span>•</span>
              <span className="flex items-center gap-1.5">
                <Server className="w-3.5 h-3.5 text-amber-400" /> Backend Host: Not Connected
              </span>
            </div>
          </div>
        </div>
      )}

      {isOffline && (
        <div className="p-3.5 bg-rose-950/40 border border-rose-800/80 rounded-xl text-rose-200 text-xs flex items-start gap-3 shadow-sm">
          <WifiOff className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-rose-300">
                Backend Gateway Unreachable
              </span>
              <Badge variant="danger">DISCONNECTED</Badge>
            </div>
            <p className="text-rose-400/90 text-[11px] leading-relaxed">
              Cannot establish connection to FastAPI Gateway at <code className="font-mono bg-slate-900 px-1 py-0.5 rounded text-rose-200">{apiBaseUrl}</code>.
              Live GPU allocations and Neo4j status cannot be fetched. Please ensure the backend server is running and the tunnel/endpoint is accessible.
            </p>
          </div>
        </div>
      )}

      {isConnected && (
        <div className="p-3.5 bg-emerald-950/40 border border-emerald-800/80 rounded-xl text-emerald-200 text-xs flex items-start gap-3 shadow-sm">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-emerald-300">
                Live Backend Connection Active
              </span>
              <Badge variant="success">CONNECTED</Badge>
            </div>
            <p className="text-emerald-400/90 text-[11px] leading-relaxed">
              Streaming live telemetry from backend host via FastAPI Gateway at <code className="font-mono bg-slate-900 px-1 py-0.5 rounded text-emerald-200">{apiBaseUrl}</code>.
            </p>
          </div>
        </div>
      )}

      {/* Main Telemetry Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* GPU & Workstation Hardware */}
        <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-xl space-y-3 shadow-sm">
          <div className="flex items-center justify-between pb-2 border-b border-slate-900">
            <div className="flex items-center gap-2 text-slate-200 font-semibold">
              <Cpu className="w-4 h-4 text-sky-400" />
              <span>Inference Hardware & Host</span>
            </div>
            {isMock ? (
              <Badge variant="warning">Simulated</Badge>
            ) : isOffline ? (
              <Badge variant="danger">Host Offline</Badge>
            ) : (
              <Badge variant="info">Live</Badge>
            )}
          </div>

          <div className="space-y-2.5">
            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Inference Accelerator</span>
              <p className="font-semibold text-slate-200 font-sans">
                {isOffline ? 'Unavailable (Host Offline)' : telemetry?.gpu_model || (isMock ? 'Simulated Inference Accelerator' : 'Hardware Telemetry Unavailable')}
              </p>
            </div>

            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Host System RAM</span>
              {isOffline ? (
                <p className="text-slate-500 font-mono text-[11px]">Unreachable</p>
              ) : (
                <>
                  <div className="flex items-center justify-between mt-1 text-slate-300 font-mono">
                    <span>Total: {telemetry ? formatMb(telemetry.ram_total_gb * 1024) : 'N/A'}</span>
                    <span>Available: {telemetry ? formatMb(telemetry.ram_available_gb * 1024) : 'N/A'}</span>
                  </div>
                  <div className="w-full bg-slate-900 h-2 rounded-full mt-1.5 overflow-hidden">
                    <div
                      className="bg-sky-500 h-full rounded-full transition-all"
                      style={{ width: `${telemetry?.ram_percent || 0}%` }}
                    />
                  </div>
                </>
              )}
            </div>

            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Dense Embedding Engine</span>
              <p className="font-mono text-slate-300 text-[11px]">
                {isOffline ? 'Unavailable' : telemetry?.embedding_model || (isMock ? 'Simulated Embedding Model' : 'Telemetry Unavailable')}
              </p>
            </div>
          </div>
        </div>

        {/* Knowledge Substrates: Neo4j & ChromaDB */}
        <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-xl space-y-3 shadow-sm">
          <div className="flex items-center justify-between pb-2 border-b border-slate-900">
            <div className="flex items-center gap-2 text-slate-200 font-semibold">
              <Database className="w-4 h-4 text-emerald-400" />
              <span>Multi-Substrate State</span>
            </div>

            {isMock ? (
              <Badge variant="outline" className="border-amber-700/80 text-amber-400 gap-1 font-mono text-[10px]">
                <Database className="w-3 h-3" /> Neo4j (Simulated Fixture)
              </Badge>
            ) : isOffline ? (
              <Badge variant="danger" className="gap-1 font-mono text-[10px]">
                <ShieldAlert className="w-3 h-3" /> Neo4j Unreachable
              </Badge>
            ) : neo4j?.connected ? (
              <Badge variant="success" className="gap-1 font-mono text-[10px]">
                <ShieldCheck className="w-3 h-3" /> Neo4j Bolt Online (Live)
              </Badge>
            ) : (
              <Badge variant="danger" className="gap-1 font-mono text-[10px]">
                <ShieldAlert className="w-3 h-3" /> Neo4j Disconnected
              </Badge>
            )}
          </div>

          <div className="space-y-2.5">
            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Neo4j Bolt Endpoint</span>
              <p className="font-mono text-slate-300 text-[11px]">
                {isOffline ? 'bolt://<remote-host>:7687 (Unreachable)' : neo4j?.uri || 'bolt://localhost:7687'}
                {isMock && <span className="text-amber-500 ml-1.5">(Simulated Fixture)</span>}
              </p>
            </div>

            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Active Graph Entities</span>
              <p className="font-mono text-emerald-400 font-semibold">
                {isOffline
                  ? 'Unavailable'
                  : neo4j?.total_nodes !== undefined
                  ? `${neo4j.total_nodes} nodes indexed ${isMock ? '(Fixture)' : '(Live)'}`
                  : (isMock ? 'Indexed entities (Fixture)' : 'No graph node data')}
              </p>
            </div>

            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-bold">ChromaDB Vector Substrate</span>
              <p className="font-mono text-slate-300 text-[11px]">
                Persistent HNSW Cosine Vector Index ({telemetry?.embedding_model || 'ChromaDB Substrate'})
                {isMock && <span className="text-amber-500 ml-1.5">(Simulated Fixture)</span>}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
