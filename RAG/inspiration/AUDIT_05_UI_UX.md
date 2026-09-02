# 🎨 AUDIT 05: UI/UX, COLOR HARMONY & AUDIO ASSETS

## Executive Summary
This document audits the visual color system, typography, unwanted UI elements, and existing local audio/TTS assets.

---

## 1. UI Color Harmony Audit

### ⚠️ Observed Issues:
* Overly stark contrast between deep black `#0b0d10` and purple accent `#7c3aed`.
* Inconsistent secondary text colors (`#a9b0ba` vs `#737b87`).
* Badges with red/coral tint (`--pdf-bg: #3c1f1e; --pdf-text: #f87171`) clash with the scientific dark palette.

### 🎨 Semantic Restrained Academic Palette:
```css
:root {
    /* Background & Surfaces */
    --bg-canvas: #0e1117;          /* Calm deep charcoal */
    --surface-card: #151921;       /* Floating card surface */
    --surface-elevated: #1b212c;   /* Elevated hover & active state */
    --surface-highest: #232b38;    /* Omnibar & popovers */
    --border-subtle: #222936;      /* Restrained card border */
    --border-focus: #3b82f6;       /* Clean academic blue focus ring */
    
    /* Academic Typography */
    --text-primary: #f0f3f8;       /* High contrast white */
    --text-secondary: #9ba3b0;     /* Readable gray */
    --text-muted: #626b7a;         /* Metadata gray */
    --accent-blue: #3b82f6;        /* Primary scientific blue */
    --accent-teal: #10b981;        /* Grounded verification green */
}
```

---

## 2. Unwanted UI Elements Identified for Removal

1. **Command Palette (`terminal` icon / `Ctrl+K`)**: Unnecessary cognitive overhead; user requested removal.
2. **Open Neo4j Browser (`hub` icon linking to 7474)**: Exposes internal developer tool to end-users; user requested removal.
3. **Sync Ingested Vault Button**: Redundant and throwing 422 errors; replace with automatic silent directory scan.

---

## 3. Audio & Voice Assets Investigation

### 📍 Local Audio Assets Found in Workspace:
* **Location**: `C:\Users\Siddharth Tripathi\OneDrive\Desktop\manga\Nakama o Mamotte Shindara 20-nengo no Onaji Sekai ni Umarekawatta Ken\`
* **Engine**: `qwen_tts` with `Qwen3-TTS-12Hz-1.7B-CustomVoice` running in WSL2 CUDA environment.
* **Capabilities**: Generates realistic neural audio waveforms (`.wav` / `.mp3`) from JSON narration scripts.
* **Integration Strategy**:
  1. For fast browser playback: Use optimized browser Web Speech API (`SpeechSynthesis`) with punctuation pauses.
  2. For high-fidelity offline narration: Provide optional hook to call local WSL2 Qwen-TTS service.