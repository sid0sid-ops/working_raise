import React from 'react';
import { useModeStore } from '../../stores/modeStore';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Check, X, RefreshCw, AlertCircle, Clock, Sparkles, Laptop } from 'lucide-react';

export const CapabilityMatrix: React.FC = () => {
  const { capabilities, isProbing, runCapabilityProbe, apiBaseUrl, appMode } = useModeStore();

  let gatewayPort = '';
  try {
    const u = new URL(apiBaseUrl);
    gatewayPort = u.port ? `Port ${u.port}` : u.protocol === 'https:' ? 'HTTPS' : 'HTTP';
  } catch {
    gatewayPort = 'Gateway';
  }

  const capabilityItems = [
    { name: `FastAPI Gateway (${gatewayPort})`, available: capabilities?.apiReachable, note: 'Primary HTTP API boundary' },
    { name: 'OpenAPI 3.1 Specification', available: capabilities?.openApiReachable, note: 'GET /openapi.json' },
    { name: 'GraphRAG 15-Node StateGraph', available: capabilities?.chatAvailable, note: 'POST /api/graphrag/subgraph-query' },
    { name: 'Autonomous Agent Router', available: capabilities?.chatAvailable, note: 'POST /api/agent/query' },
    { name: 'Dense Vector Search', available: capabilities?.searchAvailable, note: 'POST /api/search (Vector Substrate)' },
    { name: 'Document Vault / Manifest', available: capabilities?.documentsAvailable, note: 'GET /api/documents' },
    { name: 'Academic PDF Upload', available: capabilities?.documentsAvailable, note: 'POST /api/upload-academic-pdfs' },
    { name: 'Document Pruning / Delete', available: capabilities?.documentsAvailable, note: 'POST /api/documents/delete' },
    { name: 'Relational Graph Canvas', available: capabilities?.graphAvailable, note: 'GET /api/graph' },
    { name: 'Neo4j Bolt Subgraph Traversal', available: capabilities?.neo4jStatusAvailable, note: 'Bolt Protocol / Knowledge Graph' },
    { name: 'Hardware Telemetry & Acceleration', available: capabilities?.hardwareTelemetryAvailable, note: 'GET /api/hardware-telemetry' },
    { name: 'Server-Sent Events (SSE Streaming)', available: false, isFuture: true, note: 'FUTURE / NOT IMPLEMENTED' },
    { name: 'Server-Side Task Cancellation', available: false, isFuture: true, note: 'FUTURE / NOT IMPLEMENTED' },
    { name: 'Async Ingestion Job Polling', available: false, isFuture: true, note: 'FUTURE / NOT IMPLEMENTED' },
  ];

  const isMock = appMode === 'mock';

  return (
    <div className="space-y-4">
      {/* Header Info Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-slate-900 border border-slate-800 rounded-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-semibold text-slate-200">Backend Capability Matrix</h4>
            <Badge variant={appMode === 'connected' ? 'success' : appMode === 'mock' ? 'warning' : 'danger'}>
              {appMode.toUpperCase()}
            </Badge>
          </div>
          <p className="text-xs text-slate-400 font-mono flex items-center gap-2">
            <span>Target Gateway: {apiBaseUrl}</span>
            {isMock ? (
              <span className="text-amber-400/90">(Disconnected — Running Offline Mock Fixtures)</span>
            ) : capabilities?.latencyMs ? (
              <span>({capabilities.latencyMs}ms latency)</span>
            ) : null}
          </p>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={runCapabilityProbe}
          loading={isProbing}
          className="gap-1.5"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Re-Probe Gateway
        </Button>
      </div>

      {/* Capabilities Table */}
      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/70 shadow-md">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-900/80 text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
              <th className="py-2.5 px-4">Subsystem / Capability</th>
              <th className="py-2.5 px-4 w-36">Status</th>
              <th className="py-2.5 px-4">Endpoint / Architectural Role</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/80">
            {capabilityItems.map((item, idx) => (
              <tr key={idx} className="hover:bg-slate-900/30 transition-colors">
                <td className="py-2.5 px-4 font-medium text-slate-200">
                  {item.name}
                </td>
                <td className="py-2.5 px-4">
                  {item.isFuture ? (
                    <Badge variant="outline" className="text-slate-500 border-slate-800 gap-1 font-mono text-[10px]">
                      <Clock className="w-3 h-3" /> Future
                    </Badge>
                  ) : isMock ? (
                    <Badge variant="outline" className="border-amber-700/80 text-amber-400 gap-1 font-mono text-[10px]">
                      <Sparkles className="w-3 h-3" /> Simulated
                    </Badge>
                  ) : item.available ? (
                    <Badge variant="success" className="gap-1 font-mono text-[10px]">
                      <Check className="w-3 h-3" /> Live
                    </Badge>
                  ) : (
                    <Badge variant="danger" className="gap-1 font-mono text-[10px]">
                      <X className="w-3 h-3" /> Offline
                    </Badge>
                  )}
                </td>
                <td className="py-2.5 px-4 font-mono text-[11px] text-slate-400">
                  {item.note}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="p-3 bg-slate-900/50 rounded-lg border border-slate-800 text-slate-400 text-xs flex items-center gap-2">
        <AlertCircle className="w-4 h-4 text-sky-400 shrink-0" />
        <span>
          {isMock ? (
            <span className="flex items-center gap-1.5">
              <Laptop className="w-3.5 h-3.5 text-sky-400 inline" />
              <strong>Offline Simulation Mode:</strong> Currently operating in local offline mode. Statuses are simulated using fixtures so that the UI can be operated and verified without requiring the live backend host.
            </span>
          ) : (
            `Capabilities are probed live against the configured FastAPI Gateway at ${apiBaseUrl}. Unimplemented future features are strictly marked and never faked.`
          )}
        </span>
      </div>
    </div>
  );
};
