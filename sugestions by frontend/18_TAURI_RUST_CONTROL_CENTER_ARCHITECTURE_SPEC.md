# 18. Tauri 2.0 Rust Control Center & First-Run Onboarding Architecture

This document provides the complete architecture and blueprint for the **RAISE Universal Control Center**.

It explains:
1. **Folder vs. Branch Strategy**: Why a dedicated **modular folder** (`src/features/control-center/`) sharing the existing Tailwind CSS tokens is far superior to a separate git branch.
2. **First-Run Onboarding Flow**: How the Control Center intercepts first-time users upon cloning the repository, guides them through configuration, downloads models with live progress, and launches the workstation.
3. **Core Reconfiguration Center**: How users can re-open this control center anytime from the top navigation to switch between Cloud vs. Local, rotate expired API keys, toggle databases, or select target platforms (macOS, Windows, Linux, iOS, Android).
4. **Tauri 2.0 Rust Bridge**: The exact Rust IPC commands and `tauri.conf.json` setup for the backend developer.

---

## 1. The Strategy: Dedicated Modular Folder vs. Git Branch

> **Recommendation: Use a Dedicated Modular Folder (`src/features/control-center/`) inside the main codebase, NOT a separate branch.**

### Why a Separate Git Branch Is a Trap:
* If you put the Control Center on a separate branch (e.g. `git checkout control-center`):
  * A professor or new user cloning the repository has to learn git commands just to switch branches.
  * Every time the UI theme or Tailwind styles are updated in `frontend`, the `control-center` branch falls out of sync and requires painful merge conflict resolution.
  * You cannot seamlessly transition the user from the Setup Wizard directly into the live Research Workstation in the same running window!

### Why a Modular Folder Is 10x Better:
* **Single Clone & Run**: When a user clones the repository and starts the app, the Control Center opens automatically as the **first-run onboarding screen**.
* **Shared Design System**: Reuses the exact same **OLED Black (`#000000`) & Emerald Green (`#10b981`) Tailwind CSS tokens**, Lucide icons, and responsive layouts.
* **Always Accessible**: Once the initial setup is finished, users can click a **"Control Center ⚙️"** button in the header anytime to change settings on the fly!

---

## 2. Directory Structure of the Modular Control Center

```text
src/features/control-center/
├── ControlCenterModal.tsx           # Full-screen modal / view with tabbed navigation
├── store/
│   └── useControlCenterStore.ts     # Zustand store tracking wizard state & hardware info
├── steps/
│   ├── Step1_PlatformDetection.tsx  # Detects OS (Mac/Win/Linux/iOS/Android) & RAM
│   ├── Step2_AIEngineSelection.tsx  # Cloud (Groq/Gemini) vs Local (Ollama Llama 3.2 3B)
│   ├── Step3_DatabaseMatrix.tsx     # Neo4j (Cloud vs Local vs Chroma Fallback), Postgres, Redis
│   ├── Step4_ModelDownload.tsx      # Real-time SSE / Tauri IPC model download progress bar
│   └── Step5_LaunchDashboard.tsx    # Summary scorecard & 1-click 'Launch Workstation'
└── types.ts                         # Strict TypeScript contracts for system configurations
```

---

## 3. The First-Run Detection Flow

When the app boots, the router checks whether the system has been configured:

```mermaid
flowchart TD
    AppStart(["User Starts App / Opens http://localhost:8000"]) --> CheckConfig{"Is System Configured?\n(Checks localStorage & backend .env)"}

    CheckConfig -->|No (First Run)| ShowWizard["Launch Control Center Onboarding\n(Full-Screen Step-by-Step Guide)"]
    CheckConfig -->|Yes| ShowWorkstation["Direct to Research Workstation\n(2D Knowledge Graph & Chat)"]

    ShowWizard --> Step1["Step 1: Detect Platform (Windows/Mac/Linux/iOS/Android & RAM)"]
    Step1 --> Step2["Step 2: Choose AI Engine (Cloud vs Local with download sizes)"]
    Step2 --> Step3["Step 3: Configure Databases (Cloud AuraDB vs Local vs Fallback)"]
    Step3 --> Step4["Step 4: Download Selected Models (Live % Progress Bar)"]
    Step4 --> Step5["Step 5: Write .env & Start Backend Engine"]
    Step5 --> Transition["🎉 Seamlessly Transition to Workstation!"]
    
    ShowWorkstation -.->|User clicks 'Control Center ⚙️' in Header| ShowWizard
```

---

## 4. Frontend Component Blueprint

### A. TypeScript Contracts (`src/features/control-center/types.ts`)

```typescript
export type TargetPlatform = 'macos' | 'windows' | 'linux' | 'ios' | 'android';
export type LLMMode = 'cloud_groq' | 'cloud_gemini' | 'local_ollama';
export type DatabaseMode = 'cloud' | 'local' | 'in_memory_fallback';

export interface SystemHardwareInfo {
  platform: TargetPlatform;
  osName: string;
  totalRamGb: number;
  cpuCores: number;
  gpuName?: string;
  hasMetalOrCuda: boolean;
}

export interface ControlCenterConfig {
  firstRunCompleted: boolean;
  llmMode: LLMMode;
  groqApiKey?: string;
  geminiApiKey?: string;
  selectedLocalModel: 'llama3.2:3b' | 'qwen2.5:7b' | 'llama3.1:8b';
  neo4jMode: DatabaseMode;
  neo4jUri?: string;
  neo4jPassword?: string;
  postgresMode: DatabaseMode;
  redisMode: DatabaseMode;
}
```

---

### B. Zustand State Store (`src/features/control-center/store/useControlCenterStore.ts`)

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ControlCenterConfig, SystemHardwareInfo } from '../types';

interface ControlCenterState {
  isOpen: boolean;
  currentStep: number;
  hardware: SystemHardwareInfo | null;
  config: ControlCenterConfig;
  downloadProgress: number; // 0 - 100
  downloadSpeed: string;
  isDownloading: boolean;

  setOpen: (open: boolean) => void;
  setStep: (step: number) => void;
  updateConfig: (patch: Partial<ControlCenterConfig>) => void;
  setHardware: (info: SystemHardwareInfo) => void;
  setDownloadProgress: (percent: number, speed: string) => void;
  completeFirstRun: () => void;
}

export const useControlCenterStore = create<ControlCenterState>()(
  persist(
    (set) => ({
      isOpen: false,
      currentStep: 1,
      hardware: null,
      downloadProgress: 0,
      downloadSpeed: '',
      isDownloading: false,
      config: {
        firstRunCompleted: false,
        llmMode: 'cloud_groq',
        selectedLocalModel: 'llama3.2:3b',
        neo4jMode: 'cloud',
        postgresMode: 'in_memory_fallback',
        redisMode: 'in_memory_fallback',
      },
      setOpen: (open) => set({ isOpen: open }),
      setStep: (step) => set({ currentStep: step }),
      updateConfig: (patch) => set((s) => ({ config: { ...s.config, ...patch } })),
      setHardware: (hardware) => set({ hardware }),
      setDownloadProgress: (percent, speed) =>
        set({ downloadProgress: percent, downloadSpeed: speed, isDownloading: percent < 100 }),
      completeFirstRun: () =>
        set((s) => ({ config: { ...s.config, firstRunCompleted: true }, isOpen: false })),
    }),
    { name: 'raise-control-center-store' }
  )
);
```

---

## 5. Tauri 2.0 Rust Architecture Specification (For Backend Dev)

The backend developer adds the `src-tauri` directory to package this into native **Windows (`.exe`)**, **macOS (`.dmg`)**, **Linux (`.AppImage`)**, and **Android/iOS apps**.

### A. Tauri Configuration: `src-tauri/tauri.conf.json`
```json
{
  "productName": "RAISE Research Workstation",
  "version": "1.0.0",
  "identifier": "org.raise.workstation",
  "build": {
    "frontendDist": "../dist",
    "devUrl": "http://localhost:5173",
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build"
  },
  "app": {
    "windows": [
      {
        "title": "RAISE AI Workstation",
        "width": 1280,
        "height": 850,
        "minWidth": 900,
        "minHeight": 650,
        "theme": "Dark",
        "decorations": true
      }
    ],
    "security": {
      "csp": null
    }
  }
}
```

---

### B. Rust IPC Bridge: `src-tauri/src/main.rs`

The Rust backend handles the heavy lifting: hardware probing, model downloading, and writing `.env`:

```rust
// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::fs::OpenOptions;
use std::io::Write;
use sysinfo::System;

#[derive(Serialize)]
pub struct HardwareTelemetry {
    pub platform: String,
    pub os_name: String,
    pub total_ram_gb: f32,
    pub cpu_cores: usize,
}

// 1. Hardware Detection Command
#[tauri::command]
fn get_system_hardware() -> HardwareTelemetry {
    let mut sys = System::new_all();
    sys.refresh_all();

    HardwareTelemetry {
        platform: std::env::consts::OS.to_string(),
        os_name: System::long_os_version().unwrap_or_default(),
        total_ram_gb: (sys.total_memory() as f32) / (1024.0 * 1024.0 * 1024.0),
        cpu_cores: sys.cpus().len(),
    }
}

// 2. Save Configuration to .env Command
#[tauri::command]
fn save_configuration(config_json: String) -> Result<String, String> {
    let mut file = OpenOptions::new()
        .write(true)
        .create(true)
        .truncate(true)
        .open(".env")
        .map_err(|e| e.to_string())?;

    // Writes configuration directly to .env
    writeln!(file, "# Auto-generated by RAISE Control Center").map_err(|e| e.to_string())?;
    Ok("Configuration saved successfully".into())
}

// 3. Model Download Progress Event Dispatcher
#[tauri::command]
async fn pull_local_model<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    model_name: String,
) -> Result<String, String> {
    // Calls Ollama API or downloads GGUF model asynchronously
    // Emits events to React frontend: app.emit("model-pull-progress", ...)
    Ok("Model download completed".into())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            get_system_hardware,
            save_configuration,
            pull_local_model
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

---

## 6. How the User Experiences It

1. **User clones repository and launches**:
   ```bash
   npm run dev    # For web dev
   # OR
   npm run tauri dev # For native desktop app
   ```
2. **Onboarding Pops Up Instantly**:
   * Inspects their hardware: *"Detected macOS Apple Silicon with 8GB RAM"*.
   * Suggests: *"Profile 1 (Cloud Groq) recommended for maximum speed"*.
3. **If user chooses Local AI**:
   * Shows: *"Llama 3.2 3B (2.0 GB Download)"*.
   * Clicking "Download" shows a smooth progress bar driven by Rust.
4. **Click "Launch Workstation"**:
   * The Control Center modal closes, and the full React 19 Research Workstation (2D Knowledge Graph, Chat, PDF Reader) comes to life!
5. **Reconfiguration Anytime**:
   * A user can click **`[ Control Center ⚙️ ]`** in the top navigation bar at any point in the future to change API keys, switch models, or reconfigure databases without restarting!
