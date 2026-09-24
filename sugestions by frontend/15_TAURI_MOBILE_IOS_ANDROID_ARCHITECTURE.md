# 15. Tauri 2.0 Mobile (iOS & Android) Architecture & Cloud Integration

This guide details how **Tauri 2.0** allows compiling the RAISE Research Workstation into native **iOS (.ipa)** and **Android (.apk)** mobile applications.

---

## 1. The Short Answer: YES! 📱

**Yes, absolutely!**  
With **Tauri 2.0** (which added official first-class mobile support), the exact same React 19 codebase running on your desktop can be compiled into an **iPhone, iPad, or Android native app**.

When users paste their free cloud API keys (Groq, Gemini, Neo4j AuraDB) into the mobile app:
* **The phone does ZERO heavy lifting**.
* It runs with **sub-second speed (~0.8s)** on 4G/5G/WiFi.
* Consumes **less than 80 MB of RAM** on the phone.
* Works seamlessly on **iPhones, iPads, Android phones, and Android tablets**.

---

## 2. How Mobile Works with Cloud APIs

Phones cannot run Python servers or 15 GB Docker containers. Instead, the mobile architecture operates in one of two modes:

```mermaid
flowchart TD
    Phone(["User's Phone\n(Tauri 2.0 iOS / Android App)"]) --> ChooseMode{"Select Mobile Architecture"}

    %% Mode A
    ChooseMode -->|Architecture A: Direct Cloud APIs\n(Zero Server Needed)| DirectCloud["Direct HTTPS / WSS to Cloud Providers\n• Groq LPU (Streaming AI Responses)\n• Neo4j AuraDB (HTTPS Transaction API)\n• Neon PostgreSQL (HTTP Serverless Driver)"]

    %% Mode B
    ChooseMode -->|Architecture B: Hosted FastAPI Gateway\n(Full 15-Node LangGraph)| HostedGateway["Hosted Free FastAPI Gateway\n(Deployed on Render.com / Fly.io / Cloudflare Tunnel)\n• Runs the full cyclical LangGraph pipeline\n• Streams tokens to the phone over SSE"]

    DirectCloud --> Result(["📱 Native Mobile Research Workstation\n• Touch-interactive Knowledge Graph\n• Voice & Text Streaming Chat\n• PDF Reading on iPad / Tablet"])
    HostedGateway --> Result
```

---

## 3. Architecture Comparison: Direct Cloud vs Hosted Gateway

| Feature | Architecture A: Direct Cloud API | Architecture B: Hosted Gateway (Recommended) |
| :--- | :--- | :--- |
| **Backend Server Needed?** | **No server at all** | Free cloud server (Render, Railway, or home laptop) |
| **How User Connects** | Pastes Groq + Neo4j keys directly in Mobile App Settings | Pastes their backend Gateway URL (e.g. `https://my-raise.fly.dev`) |
| **GraphRAG Reasoning** | Direct Cypher queries & LLM synthesis | Full 15-node cyclical LangGraph pipeline with quality gates |
| **Touch Knowledge Graph** | Works natively via Canvas/SVG | Works natively via Canvas/SVG |
| **Best For** | Ultra-light standalone mobile chat | Full academic multi-hop research on iPad / Tablet |

---

## 4. How to Build the Mobile App with Tauri 2.0

### Step 1: Install Tauri Mobile CLI
In your frontend directory:
```bash
npm install -D @tauri-apps/cli@latest
```

### Step 2: Initialize Mobile Targets
```bash
# For Android (requires Android Studio & Android NDK):
npm run tauri android init

# For iOS (requires macOS with Xcode installed):
npm run tauri ios init
```
This automatically generates:
* `src-tauri/gen/android` (Native Android Studio Kotlin/Gradle project)
* `src-tauri/gen/apple` (Native Xcode Swift project)

### Step 3: Run Live Mobile Simulator
```bash
# Test on connected Android device / emulator:
npm run tauri android dev

# Test on iOS Simulator (iPhone 16 Pro / iPad):
npm run tauri ios dev
```

### Step 4: Build Release Mobile Binaries
```bash
# Builds native Android APK / AAB for Google Play:
npm run tauri android build

# Builds native iOS IPA for TestFlight / App Store:
npm run tauri ios build
```

---

## 5. Mobile User Experience (What the User Sees)

1. **First Launch**:
   * The user opens the app on their iPhone or Android phone.
   * A clean onboarding screen asks:
     ```text
     ┌──────────────────────────────────────────────┐
     │ 🌐 RAISE Research Workstation                │
     │ Connect Your Cloud Intelligence              │
     │                                              │
     │ Groq API Key:     [ gsk_****************** ] │
     │ Neo4j AuraDB URI: [ neo4j+s://xxxx.io     ] │
     │ Aura Password:    [ ********************** ] │
     │                                              │
     │ [ 🚀 START RESEARCHING ]                    │
     └──────────────────────────────────────────────┘
     ```
2. **Interactive Research on Mobile**:
   * **Touch Knowledge Graph**: Pinch-to-zoom and drag nodes with your fingers using touch gestures on the 2D graph canvas.
   * **Streaming Chat**: Real-time word-by-word token streaming from Groq LPU at 500 tokens/sec.
   * **PDF Inspector**: Read research papers and jump directly to cited pages on an iPad or tablet.

---

## 6. Security on Mobile (Safe Key Storage)

When users paste their API keys on a mobile device, Tauri 2.0 protects them using the phone's native hardware security:
* **On iOS**: Keys are encrypted inside the **Apple Keychain** using the Secure Enclave.
* **On Android**: Keys are encrypted inside the **Android Keystore** with hardware-backed AES-256.
* Keys are **never** uploaded to any third party.

---

## 7. Strategic Roadmap

| Platform | Recommended Tech Stack | Status |
| :--- | :--- | :--- |
| **Desktop Quick Demo (Professor)** | Python + React 19 (`launch.bat` / `launch.sh`) | **Ready to use now** |
| **Desktop Commercial App** | Tauri 2.0 (Windows `.exe`, Mac `.dmg`, Linux `.AppImage`) | **Phase 2 Expansion** |
| **Mobile & Tablet** | Tauri 2.0 Mobile (iOS App Store & Android Google Play) | **Phase 3 Expansion** |
