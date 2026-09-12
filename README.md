# RAISE : Research Assessment Intelligence & Semantic Extraction (Frontend)

Client-side research workstation for the RAISE platform.

---

## Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Start local development server
npm run dev
```

The application will launch at `http://localhost:5173`.

---

## Connecting to Backend

The frontend communicates with the FastAPI backend gateway (running by default on port `8000`).

You can connect using either method below:

### Option 1: Via Environment File (`.env`)

Create a `.env` file in the project root:

```env
# URL of the running FastAPI backend
VITE_API_BASE_URL=http://localhost:8000

# Operational mode: 'auto' | 'remote' | 'mock'
VITE_API_MODE=auto
```

Replace `http://localhost:8000` with your backend server's IP or Cloudflare tunnel URL if running remotely.

---

### Option 2: Directly in the UI (No restart needed)

1. Open the app in your browser.
2. Click the **Settings** (gear icon) in the bottom-left corner (or press `Cmd/Ctrl + /`).
3. Select the **Gateway** tab.
4. Enter your backend URL (e.g. `http://localhost:8000` or `https://your-backend-tunnel.trycloudflare.com`).
5. Click **Save & Test Connection**.
