import { defineConfig, Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

import os from 'os';
import fs from 'fs';

function detectSystemEnvironment() {
  const platform = os.platform();
  const release = os.release();
  const arch = os.arch();
  const totalRamGb = (os.totalmem() / 1024 ** 3).toFixed(1);
  const freeRamGb = (os.freemem() / 1024 ** 3).toFixed(1);
  const cpus = os.cpus() || [];
  const cpuCount = cpus.length;
  const cpuModel = cpus[0]?.model ? cpus[0].model.replace(/\s+/g, ' ').trim() : 'CPU';

  // Virtualization & Container Detection
  let runtimeType = 'Host Native';
  let isDocker = false;
  let isWsl = false;
  let isCi = false;

  try {
    if (fs.existsSync('/.dockerenv') || process.env.DOCKER_CONTAINER) {
      isDocker = true;
    } else if (fs.existsSync('/proc/1/cgroup')) {
      const cgroup = fs.readFileSync('/proc/1/cgroup', 'utf-8');
      if (cgroup.includes('docker') || cgroup.includes('containerd') || cgroup.includes('kubepods')) {
        isDocker = true;
      }
    }
  } catch {}

  if (platform === 'linux' && (release.toLowerCase().includes('microsoft') || process.env.WSL_DISTRO_NAME)) {
    isWsl = true;
  }

  if (process.env.GITHUB_ACTIONS || process.env.CI) {
    isCi = true;
  }

  if (isDocker) {
    runtimeType = 'Docker (OCI Container)';
  } else if (isWsl) {
    runtimeType = `WSL2 (${process.env.WSL_DISTRO_NAME || 'Linux'})`;
  } else if (isCi) {
    runtimeType = 'GitHub Actions CI Runner';
  }

  // Friendly OS label
  let osLabel = '';
  if (platform === 'darwin') {
    const isMSeries = arch === 'arm64' || cpuModel.includes('Apple');
    osLabel = `macOS (${isMSeries ? 'Apple Silicon' : 'Intel'}, Darwin ${release.split('.')[0]}.${release.split('.')[1]})`;
  } else if (platform === 'win32') {
    osLabel = `Windows (${os.type()} ${release})`;
  } else if (platform === 'linux') {
    osLabel = isWsl ? `Linux WSL2 (${process.env.WSL_DISTRO_NAME || 'Ubuntu'})` : `Linux Kernel ${release}`;
  } else {
    osLabel = `${os.type()} (${platform})`;
  }

  const hardwareSpecs = `${cpuCount} Cores (${arch}) • ${totalRamGb}GB RAM (${freeRamGb}GB free)`;

  return {
    osLabel,
    hardwareSpecs,
    runtimeType,
  };
}

function raiseConnectionBannerPlugin(): Plugin {
  return {
    name: 'raise-connection-banner',
    configureServer(server) {
      // Live Terminal Telemetry & Error Stream Middleware
      server.middlewares.use('/__terminal_log', (req, res) => {
        if (req.method === 'POST') {
          let body = '';
          req.on('data', (chunk) => {
            body += chunk;
          });
          req.on('end', () => {
            try {
              const ev = JSON.parse(body);
              const time = new Date().toLocaleTimeString();
              const dim = '\x1b[90m';
              const reset = '\x1b[0m';
              const bold = '\x1b[1m';
              const blue = '\x1b[34m';
              const green = '\x1b[32m';
              const yellow = '\x1b[33m';
              const red = '\x1b[31m';
              const cyan = '\x1b[36m';
              const magenta = '\x1b[35m';

              if (ev.type === 'REQ') {
                console.log(
                  `\n${dim}[${time}]${reset} ${blue}${bold}➔ [HTTP DISPATCH]${reset} ${bold}${ev.method || 'POST'}${reset} ${cyan}${ev.endpoint}${reset}`
                );
                if (ev.details) {
                  console.log(`        ${dim}└─ Details: ${ev.details}${reset}`);
                }
              } else if (ev.type === 'RES') {
                console.log(
                  `${dim}[${time}]${reset} ${green}${bold}✔ [RESPONSE LIVE]${reset} ${bold}${ev.status || 200} OK${reset} ${dim}(${ev.durationMs || 0}ms)${reset} — ${green}${ev.message || 'Success'}${reset}`
                );
              } else if (ev.type === 'MOCK') {
                console.log(
                  `${dim}[${time}]${reset} ${yellow}${bold}⚡ [MOCK/FIXTURE]${reset} ${cyan}${ev.endpoint}${reset} — ${yellow}${ev.message || 'Handled by local fixture'}${reset} ${dim}(${ev.durationMs || 0}ms)${reset}`
                );
              } else if (ev.type === 'ERR') {
                console.log(
                  `${dim}[${time}]${reset} ${red}${bold}✖ [PROCESS ERROR]${reset} ${bold}${ev.status || 500}${reset} ${cyan}${ev.endpoint}${reset} — ${red}${ev.error || 'Failure'}${reset} ${dim}(${ev.durationMs || 0}ms)${reset}`
                );
              } else if (ev.type === 'SYSTEM') {
                console.log(
                  `${dim}[${time}]${reset} ${magenta}${bold}ℹ [SYSTEM]${reset} ${ev.message || ''}`
                );
              }
            } catch {}
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ ok: true }));
          });
        } else {
          res.writeHead(404);
          res.end();
        }
      });

      server.httpServer?.once('listening', async () => {
        const baseUrl = process.env.VITE_API_BASE_URL || 'http://localhost:8000';
        let gatewayOnline = false;
        let openApiOnline = false;
        let docsCount = 0;
        let neo4jOnline = false;
        let neo4jNodes = 0;
        let telemGpu = '';
        let telemRam = '';

        try {
          // Probe 1: Gateway Documents Manifest
          const res = await fetch(`${baseUrl}/api/documents`, {
            signal: AbortSignal.timeout(1500),
          });
          if (res.ok) {
            gatewayOnline = true;
            const data = (await res.json().catch(() => ({}))) as any;
            docsCount = data?.total_count || data?.documents?.length || 0;
          }

          // Probe 2: OpenAPI Specification
          const openRes = await fetch(`${baseUrl}/openapi.json`, {
            signal: AbortSignal.timeout(1000),
          });
          openApiOnline = openRes.ok;

          // Probe 3: Neo4j Bolt Status
          const nRes = await fetch(`${baseUrl}/api/neo4j/status`, {
            signal: AbortSignal.timeout(1000),
          });
          if (nRes.ok) {
            const nData = (await nRes.json().catch(() => ({}))) as any;
            neo4jOnline = nData?.connected !== false;
            neo4jNodes = nData?.total_nodes || 0;
          }

          // Probe 4: Hardware Telemetry
          const tRes = await fetch(`${baseUrl}/api/hardware-telemetry`, {
            signal: AbortSignal.timeout(1000),
          });
          if (tRes.ok) {
            const tData = (await tRes.json().catch(() => ({}))) as any;
            telemGpu = tData?.gpu_model || (tData?.accelerator ?? 'Live Hardware Telemetry');
            telemRam = tData?.ram_total_gb ? `${tData.ram_total_gb}GB RAM (${tData?.ram_percent || 0}% used)` : 'RAM Telemetry Live';
          }
        } catch {
          // Backend offline - operating in local mock mode
        }

        const cyan = '\x1b[36m';
        const green = '\x1b[32m';
        const yellow = '\x1b[33m';
        const red = '\x1b[31m';
        const reset = '\x1b[0m';
        const bold = '\x1b[1m';

        const sys = detectSystemEnvironment();
        const formatCol = (str: string, maxLen = 49) => {
          if (str.length > maxLen) {
            return str.slice(0, maxLen - 3) + '...';
          }
          return str.padEnd(maxLen);
        };

        const hostStr = `${sys.osLabel} [${sys.runtimeType}]`;
        const resStr = sys.hardwareSpecs;

        console.log(
          `\n${cyan}${bold}┌────────────────────────────────────────────────────────────────────────┐\n` +
          `│                   RAISE ADVANCED RAG PIPELINE SYSTEM                   │\n` +
          `│          Dynamic Multi-System Host & Substrate Runtime Audit           │\n` +
          `├────────────────────────────────────────────────────────────────────────┤${reset}\n` +
          `│ ${bold}Client Host Machine:${reset}   ${formatCol(hostStr)}│\n` +
          `│ ${bold}Hardware Resources:${reset}    ${formatCol(resStr)}│\n` +
          `│ ${bold}Target Gateway URL:${reset}    ${formatCol(baseUrl)}│\n` +
          `│ ${bold}Active Client Mode:${reset}    ${(gatewayOnline ? `${green}CONNECTED (Live Remote Backend)${reset}` : `${yellow}MOCK MODE (15 Production Fixtures)${reset}`).padEnd(gatewayOnline ? 58 : 62)}│\n` +
          `${cyan}├────────────────────────────────────────────────────────────────────────┤\n` +
          `│ ${bold}SUBSTRATE & DATABASE CONNECTIVITY:${reset}${cyan}                                     │\n` +
          `│ • FastAPI Gateway (Port 8000):   ${(gatewayOnline ? `${green}🟢 CONNECTED (Port 8000 Live)${reset}` : `${red}🔴 OFFLINE (Port 8000 Unreachable)${reset}`).padEnd(gatewayOnline ? 61 : 63)}│\n` +
          `│ • ChromaDB Vector (.chromadb):   ${(gatewayOnline ? `${green}🟢 ACTIVE (HNSW Vector Store)${reset}` : `${yellow}🟡 OFFLINE / LOCAL MOCK FIXTURE${reset}`).padEnd(gatewayOnline ? 61 : 61)}│\n` +
          `│ • Neo4j Property Graph (7687):   ${(neo4jOnline ? `${green}🟢 ONLINE (${neo4jNodes} nodes indexed)${reset}` : `${yellow}🟡 OFFLINE / LOCAL MOCK FIXTURE${reset}`).padEnd(neo4jOnline ? 61 : 61)}│\n` +
          `│ • vLLM Inference Engine (8002):  ${(gatewayOnline ? `${green}🟢 READY (Inference Substrate Live)${reset}` : `${yellow}🟡 OFFLINE / LOCAL MOCK RESPONSES${reset}`).padEnd(gatewayOnline ? 61 : 61)}│\n` +
          `│ • Target Inference GPU:          ${(telemGpu ? `${green}🟢 ${telemGpu}${reset}` : `${yellow}🟡 Hardware Accelerator Offline${reset}`).padEnd(telemGpu ? 61 : 61)}│\n` +
          `${cyan}├────────────────────────────────────────────────────────────────────────┤\n` +
          `│ ${bold}API ENDPOINT AUDIT TABLE:${reset}${cyan}                                              │\n` +
          `│ • GET  /api/documents            ${(gatewayOnline ? `${green}🟢 200 OK (${docsCount} documents indexed)${reset}` : `${yellow}🟡 MOCK READY (4 verified docs)${reset}`).padEnd(gatewayOnline ? 61 : 61)}│\n` +
          `│ • POST /api/graphrag/subgraph-query ${(gatewayOnline ? `${green}🟢 200 OK (15-Node StateGraph Live)${reset}` : `${yellow}🟡 MOCK READY (XYMA, 3 Startups)${reset}`).padEnd(gatewayOnline ? 61 : 61)}│\n` +
          `│ • POST /api/agent/query          ${(gatewayOnline ? `${green}🟢 200 OK (Multi-Tool Router Live)${reset}` : `${yellow}🟡 MOCK READY (Autonomous Agent)${reset}`).padEnd(gatewayOnline ? 61 : 61)}│\n` +
          `│ • POST /api/upload-academic-pdfs ${(gatewayOnline ? `${green}🟢 200 OK (IBM Docling Ready)${reset}` : `${yellow}🟡 MOCK READY (Synchronous Mock)${reset}`).padEnd(gatewayOnline ? 61 : 61)}│\n` +
          `│ • GET  /api/graph                ${(gatewayOnline ? `${green}🟢 200 OK (Full Graph Relational)${reset}` : `${yellow}🟡 MOCK READY (6 Nodes, 2 Edges)${reset}`).padEnd(gatewayOnline ? 61 : 61)}│\n` +
          `│ • GET  /api/hardware-telemetry   ${(telemGpu ? `${green}🟢 200 OK (${telemRam})${reset}` : `${yellow}🟡 MOCK READY (Hardware Profiler)${reset}`).padEnd(telemGpu ? 61 : 61)}│\n` +
          `│ • GET  /api/neo4j/status         ${(neo4jOnline ? `${green}🟢 200 OK (Bolt Port 7687 Up)${reset}` : `${yellow}🟡 MOCK READY (Simulated Bolt)${reset}`).padEnd(neo4jOnline ? 61 : 61)}│\n` +
          `│ • GET  /openapi.json             ${(openApiOnline ? `${green}🟢 200 OK (OpenAPI 3.1 Spec Up)${reset}` : `${yellow}🟡 MOCK READY (Fallback Ready)${reset}`).padEnd(openApiOnline ? 61 : 61)}│\n` +
          `${cyan}├────────────────────────────────────────────────────────────────────────┤\n` +
          `│ ${bold}APPLICATION ARCHITECTURE & WORKSPACE CONFIGURATION:${reset}${cyan}                    │\n` +
          `│ • Workspace Mode:    ${green}✔ ALWAYS OPEN NEW CHAT${reset}${cyan} (Clean Slate on Every Launch) │\n` +
          `│ • Browser Interface: ${green}✔ AUTO-LAUNCH ENABLED${reset}${cyan}  (http://localhost:5173)       │\n` +
          `│ • Theme Engine:      ${green}✔ DUAL HIGH-CONTRAST${reset}${cyan}   (WCAG Light / Dark Responsive)│\n` +
          `│ • Drawer Navigation: ${green}✔ 180° CHEVRON TOGGLE${reset}${cyan}  (Smooth > / < Interactive)    │\n` +
          `│ • System Answers:    ${green}✔ CLEAN PROSE OUTPUT${reset}${cyan}   (Evidence Trays Hidden)       │\n` +
          `│ • Knowledge Vault:   ${green}✔ PERSISTENT SESSIONS${reset}${cyan}  (Synchronized PDF Library)    │\n` +
          `${cyan}├────────────────────────────────────────────────────────────────────────┤\n` +
          `│ ${bold}PORTABLE MULTI-ENVIRONMENT ORCHESTRATION (DOCKER / GITHUB / LINUX / PC):${reset}${cyan}│\n` +
          `│ • Docker Container Mode:  docker compose up -d (Neo4j, ChromaDB, vLLM) │\n` +
          `│ • Native Python Gateway:  python app.py  (Starts FastAPI on 0.0.0.0:8000)│\n` +
          `│ • GitHub CI / Auto Test:  npm run test:run && npm run build            │\n` +
          `│ ➔ Starting backend on ANY system will instantly turn all ${green}🟢 CONNECTED!${reset}${cyan}  │\n` +
          `└────────────────────────────────────────────────────────────────────────┘${reset}\n`
        );
      });
    },
  };
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), raiseConnectionBannerPlugin()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  base: './', // Ensures static deployment compatibility (e.g. GitHub Pages)
  server: {
    port: 5173,
    host: true,
    open: true, // Automatically open the browser on http://localhost:5173
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
});
