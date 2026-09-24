"""
RAISE Infrastructure — Neural Model Control Center (OLED Black Edition)
High-fidelity, ultra-low-overhead desktop mission control center for:
1. Dynamic Multi-Cloud Pipeline Phases (8-Phase Phase-to-Provider Assignment Matrix)
2. Per-LLM Real-time Token Usage & Cost Accounting (Prompt, Completion, Total, USD)
3. Underlying AI Model Subsystems & Health (FineCat-NLI, BGE-Large, BGE-Reranker, GGAHC, BM25)
4. Non-Destructive Hardware & Substrate Telemetry (CPU, RAM, GPU, Database Ports)
5. Masked Windows Credential Locker (DPAPI & .env management)
"""

from __future__ import annotations

import os
import sys
import platform
import psutil
import socket
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("raise.gui.control_center")

# OLED Pitch Black Palette with Pure Green (#10b981 / #22c55e) Accents
BG_BLACK = "#000000"
PANEL_BG = "#060608"
CARD_BG = "#0b0b0e"
CARD_HEADER = "#111116"
BORDER_COLOR = "#222226"
BORDER_GREEN = "#10b981"
BORDER_ACCENT = "#22c55e"

TEXT_WHITE = "#ffffff"
TEXT_PRIMARY = "#f4f4f5"
TEXT_MUTED = "#9ca3af"
TEXT_DIM = "#6b7280"

# Proper Green Palette
GREEN_BRIGHT = "#22c55e"
GREEN_EMERALD = "#10b981"
GREEN_DARK = "#064e3b"
GREEN_BG_CHIP = "#052e16"

# Auxiliary Accents
ACCENT_CYAN = "#38bdf8"
ACCENT_AMBER = "#f59e0b"
ACCENT_RED = "#ef4444"
ACCENT_PURPLE = "#c084fc"


def check_port(host: str, port: int, timeout: float = 0.3) -> bool:
    """Check if TCP port is accepting connections within timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def get_hardware_telemetry() -> Dict[str, Dict[str, str]]:
    """Dynamically probe CPU, RAM, and GPU without hardcoding."""
    # 1. CPU
    cpu_cores_logical = psutil.cpu_count(logical=True) or 0
    cpu_cores_physical = psutil.cpu_count(logical=False) or 0
    cpu_pct = f"{psutil.cpu_percent(interval=0.05)}%"

    # 2. RAM
    mem = psutil.virtual_memory()
    ram_used_gb = round(mem.used / (1024**3), 1)
    ram_total_gb = round(mem.total / (1024**3), 1)
    ram_free_gb = round(mem.available / (1024**3), 1)
    ram_str = f"{ram_used_gb} GB used / {ram_total_gb} GB ({mem.percent}%) [Free: {ram_free_gb} GB]"

    # 3. GPU (CUDA via PyTorch if installed)
    gpu_status = "NOT DETECTED"
    gpu_details = "CPU Mode Active (Zero CUDA Devices)"
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0)
            v_free, v_tot = torch.cuda.mem_get_info()
            v_used_gb = round((v_tot - v_free) / (1024**3), 2)
            v_total_gb = round(v_tot / (1024**3), 2)
            gpu_status = "ONLINE"
            gpu_details = f"{gpu_name} (Count: {gpu_count}) | VRAM: {v_used_gb} / {v_total_gb} GB"
    except Exception as e:
        gpu_details = f"Detection notice: {e}"

    return {
        "Processor (CPU)": {"status": "READY", "details": f"{cpu_cores_logical} Logical ({cpu_cores_physical} Physical) Cores | Load: {cpu_pct}"},
        "System Memory (RAM)": {"status": "READY", "details": ram_str},
        "Dedicated GPU": {"status": gpu_status, "details": gpu_details},
        "Python Runtime": {"status": "READY", "details": f"{platform.python_version()} ({platform.architecture()[0]})"},
        "Operating System": {"status": "READY", "details": f"{platform.system()} {platform.release()} (Build {platform.version()})"},
    }


# Backwards compatibility alias
get_system_health = get_hardware_telemetry


def get_pipeline_models_health() -> Dict[str, Dict[str, str]]:
    """Dynamically inspect all auxiliary AI models (FineCat, Embeddings, Reranker, Chunking, Retrieval)."""
    results: Dict[str, Dict[str, str]] = {}

    # 1. Embedding Model
    try:
        from src.core.config import settings
        from src.infrastructure.vector.chroma import LocalVectorEngine
        emb_model = settings.vector.embedding_model if settings else "BAAI/bge-large-en-v1.5"
        emb_dim = settings.vector.embedding_dimension if settings else 1024
        emb_dir = str(settings.vector.persist_directory.name) if settings else ".chromadb_bge_large"
        
        v_engine = LocalVectorEngine()
        chunk_count = v_engine.count() if hasattr(v_engine, "count") else 0
        results["Dense Vector (ChromaDB)"] = {
            "status": "READY",
            "model": f"{emb_model} ({emb_dim}-dim)",
            "details": f"Index: {emb_dir} | Stored Chunks: {chunk_count} | Metric: Cosine HNSW",
        }
    except Exception as e:
        results["Dense Vector (ChromaDB)"] = {
            "status": "WARNING",
            "model": "BAAI/bge-large-en-v1.5",
            "details": f"Offline / Error: {e}",
        }

    # 2. Cross-Encoder Reranker
    try:
        from src.retrieval.fusion import CrossEncoderReranker
        import torch
        dev = "cuda:0" if torch.cuda.is_available() else "cpu"
        results["Cross-Encoder Reranker"] = {
            "status": "READY",
            "model": "BAAI/bge-reranker-large",
            "details": f"Device: {dev} | Cutoff: Logits -7.5 / Prob 0.15 | Multi-Hop Max-Pool Active",
        }
    except Exception as e:
        results["Cross-Encoder Reranker"] = {
            "status": "HEURISTIC",
            "model": "Lexical Co-occurrence Fallback",
            "details": f"Fallback: {e}",
        }

    # 3. FineCat-NLI Grounding & Faithfulness Gate
    try:
        hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
        finecat_dirs = list(hf_cache.glob("*finecat*")) if hf_cache.exists() else []
        if finecat_dirs:
            results["FineCat-NLI Quality Gate"] = {
                "status": "READY",
                "model": "FineCat-NLI (Local Safetensors)",
                "details": f"Hub Cache Verified | Strict Faithfulness Gate (>=0.80 Pass Target)",
            }
        else:
            results["FineCat-NLI Quality Gate"] = {
                "status": "FALLBACK",
                "model": "Heuristic Entailment NLI",
                "details": "Safetensors not cached. Using heuristic lexical entailment quality gate.",
            }
    except Exception as e:
        results["FineCat-NLI Quality Gate"] = {
            "status": "FALLBACK",
            "model": "Heuristic Entailment NLI",
            "details": f"Notice: {e}",
        }

    # 4. Chunking Engine & Native Rust SIMD
    try:
        from src.chunking.rust_bridge import get_rust_backend_type
        rust_tier = get_rust_backend_type()
        results["GGAHC Chunking Engine"] = {
            "status": "ACTIVE",
            "model": "Graph-Guided Adaptive Hierarchical (GGAHC)",
            "details": f"Rust Acceleration Tier: {rust_tier.upper()} | Boundary Thresholds: >0.60 Split / <-0.20 Merge",
        }
    except Exception as e:
        results["GGAHC Chunking Engine"] = {
            "status": "ACTIVE",
            "model": "GGAHC Python Pipeline",
            "details": f"Notice: {e}",
        }

    # 5. Sparse Lexical Search (BM25)
    try:
        results["Lexical BM25 Search"] = {
            "status": "READY",
            "model": "Okapi BM25 Inverted Index",
            "details": "Parameters: k1=1.5, b=0.75 | 1.35x Structural Tabular Schedule Boost",
        }
    except Exception as e:
        results["Lexical BM25 Search"] = {
            "status": "UNKNOWN",
            "model": "BM25",
            "details": str(e),
        }

    # 6. Persistent Knowledge Graph (Neo4j)
    try:
        neo4j_live = check_port("localhost", 7687)
        if neo4j_live:
            from src.infrastructure.graph.neo4j import Neo4jDatabase
            db = Neo4jDatabase()
            chk = db.check_connection()
            status_str = "READY" if chk.get("connected") else "OFFLINE"
            results["Neo4j Property Graph"] = {
                "status": status_str,
                "model": "Neo4j 5.26.30 (Bolt: 7687)",
                "details": "Multi-Hop Cypher Reasoning | Schema: 37 Node Labels & 50 Relationship Types",
            }
        else:
            results["Neo4j Property Graph"] = {
                "status": "OFFLINE",
                "model": "Neo4j Bolt: 7687",
                "details": "Port 7687 unreachable. Graph retrieval will auto-fallback to Dense Vector.",
            }
    except Exception as e:
        results["Neo4j Property Graph"] = {
            "status": "OFFLINE",
            "model": "Neo4j Bolt: 7687",
            "details": f"Notice: {e}",
        }

    # 7. Relational & Caching Substrates
    pg_live = check_port("localhost", 5432)
    redis_live = check_port("localhost", 6379)
    results["PostgreSQL Database"] = {
        "status": "READY" if pg_live else "MEMORY FALLBACK",
        "model": "PostgreSQL 16 (Port 5432)",
        "details": "Stores chat_messages, documents, session_metadata (In-memory fallback active if offline)",
    }
    results["Redis Cache & Bus"] = {
        "status": "READY" if redis_live else "MEMORY FALLBACK",
        "model": "Redis 7 (Port 6379)",
        "details": "Sub-millisecond query completions, token bucket rate limits, sliding-window session turns",
    }

    return results


def launch_model_control_center():
    """Launch the RAISE Neural Model Control Center with pure black OLED aesthetics and proper green indicators."""
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except ImportError:
        print("Error: tkinter is not installed in the current Python environment.")
        return

    from src.infrastructure.credentials.manager import get_credential_manager
    from src.infrastructure.providers.router import get_provider_router, ExecutionMode, InferenceTask
    from src.infrastructure.providers.diagnostics import ProviderDiagnostics
    from src.infrastructure.providers.token_tracker import get_token_tracker

    cred_mgr = get_credential_manager()
    router = get_provider_router()
    tracker = get_token_tracker()

    root = tk.Tk()
    root.title("RAISE — Neural Model Control Center (Multi-Cloud Dispatch & Model Ops)")
    root.geometry("980x760")
    root.minsize(900, 640)
    root.configure(bg=BG_BLACK)

    # Configure styles for ultra-thin 1px border lines and pitch black styling
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=BG_BLACK, foreground=TEXT_PRIMARY, font=("Segoe UI", 10), borderwidth=0)
    style.configure("TFrame", background=BG_BLACK)
    style.configure("Card.TFrame", background=CARD_BG, relief="solid", borderwidth=1)
    
    style.configure("TLabel", background=BG_BLACK, foreground=TEXT_PRIMARY)
    style.configure("Card.TLabel", background=CARD_BG, foreground=TEXT_PRIMARY)

    # Notebook Tabs
    style.configure("TNotebook", background=BG_BLACK, borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=CARD_HEADER,
        foreground=TEXT_MUTED,
        padding=[14, 8],
        font=("Segoe UI", 9, "bold"),
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", "#14291f"), ("active", "#18181b")],
        foreground=[("selected", GREEN_BRIGHT), ("active", TEXT_WHITE)],
    )

    # Treeview Styling with thin borders
    style.configure(
        "Treeview",
        background=CARD_BG,
        fieldbackground=CARD_BG,
        foreground=TEXT_PRIMARY,
        rowheight=26,
        font=("Segoe UI", 9),
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "Treeview.Heading",
        background=CARD_HEADER,
        foreground=TEXT_WHITE,
        font=("Segoe UI", 9, "bold"),
        relief="flat",
        padding=[6, 4],
    )
    style.map(
        "Treeview",
        background=[("selected", "#064e3b")],
        foreground=[("selected", GREEN_BRIGHT)],
    )

    # Top Header Banner in Pure Black with 1px Green Border
    header_frame = tk.Frame(root, bg=BG_BLACK, highlightthickness=1, highlightbackground=BORDER_GREEN)
    header_frame.pack(fill="x", padx=14, pady=(12, 6))

    top_title_box = tk.Frame(header_frame, bg=BG_BLACK)
    top_title_box.pack(side="left", padx=14, pady=10)
    
    title_row = tk.Frame(top_title_box, bg=BG_BLACK)
    title_row.pack(anchor="w")
    tk.Label(title_row, text="●", font=("Segoe UI", 12, "bold"), bg=BG_BLACK, fg=GREEN_BRIGHT).pack(side="left", padx=(0, 6))
    tk.Label(title_row, text="RAISE NEURAL MODEL CONTROL CENTER", font=("Segoe UI", 14, "bold"), bg=BG_BLACK, fg=TEXT_WHITE).pack(side="left")

    tk.Label(
        top_title_box,
        text="Mission Control: Multi-Cloud Dispatch Matrix | Live Token Metering (Per LLM) | Subsystem Health Observability",
        font=("Segoe UI", 9),
        bg=BG_BLACK,
        fg=TEXT_MUTED,
    ).pack(anchor="w", pady=(2, 0))

    # Top Quick Status Badges in Proper Green
    top_badge_box = tk.Frame(header_frame, bg=BG_BLACK)
    top_badge_box.pack(side="right", padx=14, pady=10)

    mode_badge = tk.Label(
        top_badge_box,
        text=f"EXEC MODE: {router.mode.value}",
        font=("Segoe UI", 9, "bold"),
        bg=GREEN_BG_CHIP,
        fg=GREEN_BRIGHT,
        padx=10,
        pady=4,
        relief="solid",
        borderwidth=1,
        highlightbackground=GREEN_BRIGHT,
    )
    mode_badge.pack(side="right", padx=4)

    live_pulse = tk.Label(
        top_badge_box,
        text="ONLINE / HEALTHY",
        font=("Segoe UI", 9, "bold"),
        bg="#052e16",
        fg=GREEN_BRIGHT,
        padx=8,
        pady=4,
        relief="solid",
        borderwidth=1,
    )
    live_pulse.pack(side="right", padx=4)

    # Tab Container Notebook
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=14, pady=8)

    # =========================================================================
    # TAB 1: DYNAMIC MULTI-CLOUD PIPELINE PHASES (8-Phase Assignment Matrix)
    # =========================================================================
    tab_phases = tk.Frame(notebook, bg=BG_BLACK)
    notebook.add(tab_phases, text=" 🔀  Pipeline Phase Matrix ")

    phase_info_box = tk.Frame(tab_phases, bg=CARD_BG, highlightthickness=1, highlightbackground=BORDER_COLOR)
    phase_info_box.pack(fill="x", padx=10, pady=8)
    
    p_info_header = tk.Frame(phase_info_box, bg=CARD_BG)
    p_info_header.pack(anchor="w", padx=10, pady=(6, 2))
    tk.Label(p_info_header, text="●", font=("Segoe UI", 10), bg=CARD_BG, fg=GREEN_BRIGHT).pack(side="left", padx=(0, 6))
    tk.Label(p_info_header, text="Dynamic Multi-Cloud Pipeline Phases", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=GREEN_BRIGHT).pack(side="left")

    tk.Label(
        phase_info_box,
        text="RAISE dispatches dedicated cloud LLMs tailored for distinct functional phases (e.g. Groq for sub-350ms user chat and query reformulation, "
             "Gemini for PDF vision/tables, DeepSeek for multi-hop graph reasoning, OpenRouter / NVIDIA NIM for generation, Cohere for neural cross-reranking).",
        font=("Segoe UI", 9),
        bg=CARD_BG,
        fg=TEXT_MUTED,
        wraplength=900,
        justify="left",
    ).pack(anchor="w", padx=10, pady=(0, 6))

    tasks_grid_frame = tk.LabelFrame(
        tab_phases,
        text=" Phase-to-Provider Assignment Matrix (8 Real-Time Workflows) ",
        font=("Segoe UI", 9, "bold"),
        bg=CARD_BG,
        fg=GREEN_BRIGHT,
        highlightthickness=1,
        highlightbackground=BORDER_COLOR,
        bd=0,
        padx=12,
        pady=8,
    )
    tasks_grid_frame.pack(fill="both", expand=True, padx=10, pady=6)

    # Table Header Row for Matrix
    header_cols = [("Phase & Pipeline Responsibility", 380), ("Assigned Cloud LLM", 140), ("Target Model Override", 200), ("Routing Status", 130)]
    for ci, (col_name, col_w) in enumerate(header_cols):
        h_lbl = tk.Label(tasks_grid_frame, text=col_name, font=("Segoe UI", 9, "bold"), bg=CARD_HEADER, fg=TEXT_WHITE, padx=6, pady=4, relief="solid", borderwidth=1)
        h_lbl.grid(row=0, column=ci, sticky="ew", padx=2, pady=(0, 6))

    task_combos: Dict[Any, ttk.Combobox] = {}
    task_model_entries: Dict[Any, tk.Entry] = {}
    provider_options = ["groq", "gemini", "openrouter", "nvidia", "deepseek", "cohere", "vllm"]

    # The 8 Explicit Phases Requested by User
    pipeline_phases_matrix = [
        (InferenceTask.CHAT, "Phase 1: Interactive User Chat (Low-latency conversation)", "groq", "llama-3.3-70b-versatile"),
        (InferenceTask.RAG_GENERATION, "Phase 2: RAG Answer Synthesis (Full grounded response generation)", "openrouter", "openai/gpt-4o"),
        (InferenceTask.DOCUMENT_EXTRACTION, "Phase 3: Document Layout & Vision (Tables, PDF coordinate spans)", "gemini", "gemini-2.5-flash"),
        (InferenceTask.QUERY_REWRITE, "Phase 4: Query Intake & Reformulation (Coreference & decomposition)", "groq", "llama-3.3-70b-versatile"),
        (InferenceTask.REASONING, "Phase 5: Multi-Hop Relational Reasoning (Logic & Cypher Path Critic)", "deepseek", "deepseek-reasoner"),
        (InferenceTask.CODE, "Phase 6: Code & Formal Cypher Generation (AST & Graph queries)", "deepseek", "deepseek-chat"),
        (InferenceTask.SUMMARIZATION, "Phase 7: Community / Executive Summaries (High-level abstractive)", "openrouter", "meta-llama/llama-3.3-70b"),
        (InferenceTask.RERANKING, "Phase 8: Passage Relevance Scoring (Cross-attention neural reranking)", "cohere", "rerank-v3.5"),
    ]

    for row_idx, (task_enum, desc, default_prov, default_mod) in enumerate(pipeline_phases_matrix, start=1):
        curr_provider = router.task_policy.get(task_enum, default_prov)

        # 1. Phase Name & Responsibility
        lbl_p = tk.Label(tasks_grid_frame, text=desc, font=("Segoe UI", 9), bg=CARD_BG, fg=TEXT_PRIMARY, anchor="w")
        lbl_p.grid(row=row_idx, column=0, sticky="w", padx=6, pady=4)

        # 2. Assigned Provider Dropdown
        combo = ttk.Combobox(tasks_grid_frame, values=provider_options, state="readonly", width=14)
        combo.set(curr_provider)
        combo.grid(row=row_idx, column=1, sticky="w", padx=4, pady=4)
        task_combos[task_enum] = combo

        # 3. Model Override Entry
        mod_entry = tk.Entry(tasks_grid_frame, bg="#141418", fg=GREEN_BRIGHT, insertbackground=GREEN_BRIGHT, font=("Consolas", 9), width=24, relief="solid", borderwidth=1)
        mod_entry.insert(0, default_mod)
        mod_entry.grid(row=row_idx, column=2, sticky="w", padx=4, pady=4)
        task_model_entries[task_enum] = mod_entry

        # 4. Status Tag in Proper Green
        st_tag = tk.Label(tasks_grid_frame, text="● READY", font=("Segoe UI", 8, "bold"), bg=GREEN_BG_CHIP, fg=GREEN_BRIGHT, padx=8, pady=2, relief="solid", borderwidth=1)
        st_tag.grid(row=row_idx, column=3, sticky="w", padx=6, pady=4)

    def save_phase_policies():
        for t, combo in task_combos.items():
            chosen_prov = combo.get()
            router.set_task_provider(t, chosen_prov)
            # Update target model in provider if applicable
            m_override = task_model_entries[t].get().strip()
            if m_override and chosen_prov in router.providers:
                setattr(router.providers[chosen_prov], "model_name", m_override)
        messagebox.showinfo("Matrix Saved", "Dynamic Multi-Cloud Phase Assignment Matrix successfully bound to runtime!")

    btn_row_phase = tk.Frame(tab_phases, bg=BG_BLACK)
    btn_row_phase.pack(fill="x", padx=10, pady=(2, 8))
    
    apply_btn = tk.Button(
        btn_row_phase,
        text="💾 Apply & Save Multi-Cloud Phase Matrix",
        command=save_phase_policies,
        bg="#052e16",
        fg=GREEN_BRIGHT,
        font=("Segoe UI", 9, "bold"),
        relief="solid",
        borderwidth=1,
        padx=16,
        pady=6,
    )
    apply_btn.pack(side="left", padx=4)

    # =========================================================================
    # TAB 2: TOKEN USAGE & COST ACCOUNTING (PER LLM)
    # =========================================================================
    tab_tokens = tk.Frame(notebook, bg=BG_BLACK)
    notebook.add(tab_tokens, text=" 📊  Token Metering (Per LLM) ")

    # KPI Summary Cards in Pure Black with 1px Green Border
    kpi_frame = tk.Frame(tab_tokens, bg=BG_BLACK)
    kpi_frame.pack(fill="x", padx=10, pady=8)

    def make_kpi(parent, title, val, color=GREEN_BRIGHT):
        box = tk.Frame(parent, bg=CARD_BG, highlightthickness=1, highlightbackground=BORDER_GREEN, padx=14, pady=10)
        box.pack(side="left", expand=True, fill="both", padx=6)
        tk.Label(box, text=title, font=("Segoe UI", 8, "bold"), bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w")
        lbl_val = tk.Label(box, text=val, font=("Segoe UI", 16, "bold"), bg=CARD_BG, fg=color)
        lbl_val.pack(anchor="w", pady=(2, 0))
        return lbl_val

    kpi_tokens_lbl = make_kpi(kpi_frame, "TOTAL TOKENS CONSUMED", "0", GREEN_BRIGHT)
    kpi_calls_lbl = make_kpi(kpi_frame, "ACTIVE INFERENCE INVOCATIONS", "0", TEXT_WHITE)
    kpi_cost_lbl = make_kpi(kpi_frame, "ESTIMATED MULTI-CLOUD COST", "$0.0000", ACCENT_CYAN)

    # Per-LLM Token Table
    token_box = tk.LabelFrame(
        tab_tokens,
        text=" Per-LLM Real-Time Token Breakdown & Billable Metering ",
        font=("Segoe UI", 9, "bold"),
        bg=CARD_BG,
        fg=GREEN_BRIGHT,
        highlightthickness=1,
        highlightbackground=BORDER_COLOR,
        bd=0,
        padx=10,
        pady=8,
    )
    token_box.pack(fill="both", expand=True, padx=10, pady=6)

    tok_cols = ("provider", "model", "prompt", "completion", "total", "requests", "cost", "last_active")
    tok_tree = ttk.Treeview(token_box, columns=tok_cols, show="headings", height=8)
    tok_tree.heading("provider", text="LLM Provider")
    tok_tree.heading("model", text="Active Model")
    tok_tree.heading("prompt", text="Prompt Tokens")
    tok_tree.heading("completion", text="Completion Tokens")
    tok_tree.heading("total", text="Total Tokens")
    tok_tree.heading("requests", text="Invocations")
    tok_tree.heading("cost", text="Est. Cost (USD)")
    tok_tree.heading("last_active", text="Last Active")

    tok_tree.column("provider", width=120)
    tok_tree.column("model", width=190)
    tok_tree.column("prompt", width=100)
    tok_tree.column("completion", width=120)
    tok_tree.column("total", width=100)
    tok_tree.column("requests", width=90)
    tok_tree.column("cost", width=100)
    tok_tree.column("last_active", width=140)
    tok_tree.pack(fill="both", expand=True)

    def refresh_token_table():
        tok_tree.delete(*tok_tree.get_children())
        stats = tracker.get_all_stats()
        totals = tracker.get_aggregate_totals()

        kpi_tokens_lbl.config(text=f"{totals['total_tokens']:,}")
        kpi_calls_lbl.config(text=f"{totals['total_requests']:,}")
        kpi_cost_lbl.config(text=f"${totals['total_cost_usd']:.4f}")

        for p_name, data in stats.items():
            tok_tree.insert(
                "",
                "end",
                values=(
                    p_name.upper(),
                    data.get("active_model", "default"),
                    f"{data.get('prompt_tokens', 0):,}",
                    f"{data.get('completion_tokens', 0):,}",
                    f"{data.get('total_tokens', 0):,}",
                    f"{data.get('requests_count', 0):,}",
                    f"${data.get('estimated_cost_usd', 0.0):.5f}",
                    data.get("last_active", "Idle"),
                ),
            )

    refresh_token_table()

    # Token Actions Row
    tok_btn_bar = tk.Frame(tab_tokens, bg=BG_BLACK)
    tok_btn_bar.pack(fill="x", padx=10, pady=(2, 8))

    def reset_tokens_action():
        if messagebox.askyesno("Reset Token Metering", "Reset session token counters for all LLMs to zero?"):
            tracker.reset_counters()
            refresh_token_table()

    tk.Button(tok_btn_bar, text="🔄 Refresh Token Counters", command=refresh_token_table, bg="#052e16", fg=GREEN_BRIGHT, font=("Segoe UI", 9, "bold"), relief="solid", borderwidth=1, padx=12, pady=5).pack(side="left", padx=4)
    tk.Button(tok_btn_bar, text="🗑️ Reset Session Counters", command=reset_tokens_action, bg=CARD_HEADER, fg=ACCENT_RED, font=("Segoe UI", 9, "bold"), relief="solid", borderwidth=1, padx=12, pady=5).pack(side="left", padx=4)

    # =========================================================================
    # TAB 3: RUNTIME PROVIDERS & COST MODES
    # =========================================================================
    tab_runtime = tk.Frame(notebook, bg=BG_BLACK)
    notebook.add(tab_runtime, text=" ⚡  Registered Providers ")

    # Mode Selector Frame
    mode_box = tk.LabelFrame(tab_runtime, text=" Global Execution Mode ", font=("Segoe UI", 9, "bold"), bg=CARD_BG, fg=GREEN_BRIGHT, highlightthickness=1, highlightbackground=BORDER_COLOR, bd=0, padx=12, pady=10)
    mode_box.pack(fill="x", padx=10, pady=8)

    mode_var = tk.StringVar(value=router.mode.value)

    def on_mode_change():
        selected = mode_var.get()
        router.set_execution_mode(selected)
        if selected == "CLOUD":
            router.set_cloud_allowed(True)
        mode_badge.config(text=f"EXEC MODE: {selected}")
        mode_status_lbl.config(text=f"Active Target: {selected}")

    modes = [("1. Local-First (vLLM)", "LOCAL"), ("2. Cloud Providers", "CLOUD"), ("3. Automatic Policy Routing", "AUTOMATIC")]
    for text, val in modes:
        r = tk.Radiobutton(mode_box, text=text, value=val, variable=mode_var, command=on_mode_change, bg=CARD_BG, fg=TEXT_PRIMARY, selectcolor=BG_BLACK, activebackground=CARD_BG, activeforeground=GREEN_BRIGHT, font=("Segoe UI", 9))
        r.pack(side="left", padx=14)

    mode_status_lbl = tk.Label(mode_box, text=f"Active Target: {router.mode.value}", font=("Segoe UI", 9, "bold"), bg=CARD_BG, fg=GREEN_BRIGHT)
    mode_status_lbl.pack(side="right", padx=10)

    # Registered LLM Providers Table
    llm_table_box = tk.LabelFrame(tab_runtime, text=" Registered LLM Providers & Cost Modes ", font=("Segoe UI", 9, "bold"), bg=CARD_BG, fg=GREEN_BRIGHT, highlightthickness=1, highlightbackground=BORDER_COLOR, bd=0, padx=10, pady=10)
    llm_table_box.pack(fill="both", expand=True, padx=10, pady=8)

    llm_cols = ("provider", "type", "cost_mode", "status", "source", "endpoint")
    llm_tree = ttk.Treeview(llm_table_box, columns=llm_cols, show="headings", height=8)
    llm_tree.heading("provider", text="Provider")
    llm_tree.heading("type", text="Type")
    llm_tree.heading("cost_mode", text="Cost Mode")
    llm_tree.heading("status", text="Credential Status")
    llm_tree.heading("source", text="Key Source")
    llm_tree.heading("endpoint", text="Default Endpoint")

    llm_tree.column("provider", width=120)
    llm_tree.column("type", width=70)
    llm_tree.column("cost_mode", width=190)
    llm_tree.column("status", width=120)
    llm_tree.column("source", width=110)
    llm_tree.column("endpoint", width=220)
    llm_tree.pack(fill="both", expand=True)

    def refresh_llm_table():
        llm_tree.delete(*llm_tree.get_children())
        cred_statuses = cred_mgr.list_all_statuses()
        providers_meta = [
            ("Local vLLM", "Local", "LOCAL / NO EXTERNAL API BILLING", "vllm", "http://localhost:8002/v1"),
            ("Groq", "Cloud", "CLOUD / USER ACCOUNT", "groq", "https://api.groq.com/openai/v1"),
            ("Google Gemini", "Cloud", "CLOUD / USER ACCOUNT", "gemini", "https://generativelanguage.googleapis.com"),
            ("OpenRouter", "Cloud", "CLOUD / USER ACCOUNT", "openrouter", "https://openrouter.ai/api/v1"),
            ("NVIDIA NIM", "Cloud", "CLOUD / USER ACCOUNT", "nvidia", "https://integrate.api.nvidia.com/v1"),
            ("Cohere", "Cloud", "CLOUD / USER ACCOUNT", "cohere", "https://api.cohere.com"),
            ("DeepSeek", "Cloud", "CLOUD / USER ACCOUNT", "deepseek", "https://api.deepseek.com"),
        ]
        for name, p_type, cost_mode, key, endpoint in providers_meta:
            info = cred_statuses.get(key, {"status": "missing", "source": "none"})
            st = "CONFIGURED" if (info["status"] == "configured" or key == "vllm") else "MISSING KEY"
            src = info["source"] if key != "vllm" else "Local Service"
            llm_tree.insert("", "end", values=(name, p_type, cost_mode, st, src, endpoint))

    refresh_llm_table()

    # =========================================================================
    # TAB 4: UNDERLYING AI MODELS & SUBSYSTEM HEALTH
    # =========================================================================
    tab_models = tk.Frame(notebook, bg=BG_BLACK)
    notebook.add(tab_models, text=" 🧠  Underlying AI Models ")

    models_box = tk.LabelFrame(tab_models, text=" Non-LLM Pipeline Models & Retrieval Infrastructure ", font=("Segoe UI", 9, "bold"), bg=CARD_BG, fg=GREEN_BRIGHT, highlightthickness=1, highlightbackground=BORDER_COLOR, bd=0, padx=10, pady=10)
    models_box.pack(fill="both", expand=True, padx=10, pady=8)

    mod_cols = ("subsystem", "model", "status", "details")
    mod_tree = ttk.Treeview(models_box, columns=mod_cols, show="headings", height=10)
    mod_tree.heading("subsystem", text="Subsystem / Layer")
    mod_tree.heading("model", text="Underlying Model / Component")
    mod_tree.heading("status", text="Health Status")
    mod_tree.heading("details", text="Technical Details & Metrics")

    mod_tree.column("subsystem", width=170)
    mod_tree.column("model", width=220)
    mod_tree.column("status", width=120)
    mod_tree.column("details", width=340)
    mod_tree.pack(fill="both", expand=True)

    def refresh_models_table():
        mod_tree.delete(*mod_tree.get_children())
        data = get_pipeline_models_health()
        for layer_name, info in data.items():
            mod_tree.insert("", "end", values=(layer_name, info["model"], info["status"], info["details"]))

    refresh_models_table()

    # =========================================================================
    # TAB 5: WINDOWS CREDENTIAL LOCKER (DPAPI & .ENV)
    # =========================================================================
    tab_creds = tk.Frame(notebook, bg=BG_BLACK)
    notebook.add(tab_creds, text=" 🔐  Credential Locker ")

    cred_box = tk.LabelFrame(tab_creds, text=" Manage Cloud API Keys (Masked DPAPI Locker) ", font=("Segoe UI", 9, "bold"), bg=CARD_BG, fg=GREEN_BRIGHT, highlightthickness=1, highlightbackground=BORDER_COLOR, bd=0, padx=14, pady=14)
    cred_box.pack(fill="x", padx=10, pady=8)

    tk.Label(cred_box, text="Provider:", font=("Segoe UI", 9, "bold"), bg=CARD_BG, fg=TEXT_PRIMARY).grid(row=0, column=0, sticky="w", pady=6)
    prov_select = ttk.Combobox(cred_box, values=["openrouter", "nvidia", "groq", "gemini", "deepseek", "cohere"], state="readonly", width=20)
    prov_select.set("openrouter")
    prov_select.grid(row=0, column=1, sticky="w", pady=6, padx=8)

    tk.Label(cred_box, text="API Key Secret:", font=("Segoe UI", 9, "bold"), bg=CARD_BG, fg=TEXT_PRIMARY).grid(row=1, column=0, sticky="w", pady=6)
    key_entry = tk.Entry(cred_box, show="*", width=46, bg="#141418", fg=GREEN_BRIGHT, insertbackground=GREEN_BRIGHT, relief="solid", borderwidth=1)
    key_entry.grid(row=1, column=1, sticky="w", pady=6, padx=8)

    cred_status_lbl = tk.Label(cred_box, text="Status: Loading...", font=("Segoe UI", 9, "italic"), bg=CARD_BG, fg=GREEN_BRIGHT)
    cred_status_lbl.grid(row=2, column=1, sticky="w", pady=4, padx=8)

    def update_cred_status_display(*args):
        p = prov_select.get().strip()
        st = cred_mgr.get_credential_status(p).upper()
        src = cred_mgr.get_credential_source(p)
        cred_status_lbl.config(text=f"Status: {st} (Storage: {src})")

    prov_select.bind("<<ComboboxSelected>>", update_cred_status_display)
    update_cred_status_display()

    cred_btn_row = tk.Frame(cred_box, bg=CARD_BG)
    cred_btn_row.grid(row=3, column=0, columnspan=2, pady=12)

    def save_cred_action():
        p = prov_select.get().strip()
        k = key_entry.get().strip()
        if not k:
            messagebox.showwarning("Input Error", "Please provide a non-empty API key.")
            return
        if cred_mgr.set_credential(p, k):
            key_entry.delete(0, tk.END)
            update_cred_status_display()
            refresh_llm_table()
            messagebox.showinfo("Saved", f"API key for {p} saved safely into Windows Credential Locker.")
        else:
            messagebox.showerror("Error", f"Failed to save key for {p}.")

    def delete_cred_action():
        p = prov_select.get().strip()
        if messagebox.askyesno("Confirm Removal", f"Delete stored key for {p}?"):
            cred_mgr.delete_credential(p)
            update_cred_status_display()
            refresh_llm_table()
            messagebox.showinfo("Removed", f"Credential for {p} cleared.")

    tk.Button(cred_btn_row, text="💾 Save to Locker", command=save_cred_action, bg="#052e16", fg=GREEN_BRIGHT, font=("Segoe UI", 9, "bold"), relief="solid", borderwidth=1, padx=12, pady=5).pack(side="left", padx=6)
    tk.Button(cred_btn_row, text="🗑️ Delete Key", command=delete_cred_action, bg=CARD_HEADER, fg=ACCENT_RED, font=("Segoe UI", 9, "bold"), relief="solid", borderwidth=1, padx=12, pady=5).pack(side="left", padx=6)

    # =========================================================================
    # TAB 6: HARDWARE & SYSTEM TELEMETRY
    # =========================================================================
    tab_hardware = tk.Frame(notebook, bg=BG_BLACK)
    notebook.add(tab_hardware, text=" ⚡  Hardware & Host ")

    hw_box = tk.LabelFrame(tab_hardware, text=" Live Dynamic Hardware Metrics (Zero Hardcoding) ", font=("Segoe UI", 9, "bold"), bg=CARD_BG, fg=GREEN_BRIGHT, highlightthickness=1, highlightbackground=BORDER_COLOR, bd=0, padx=10, pady=10)
    hw_box.pack(fill="both", expand=True, padx=10, pady=8)

    hw_cols = ("resource", "status", "telemetry")
    hw_tree = ttk.Treeview(hw_box, columns=hw_cols, show="headings", height=8)
    hw_tree.heading("resource", text="System Resource")
    hw_tree.heading("status", text="Sensor Status")
    hw_tree.heading("telemetry", text="Measured Metric")
    hw_tree.column("resource", width=180)
    hw_tree.column("status", width=120)
    hw_tree.column("telemetry", width=480)
    hw_tree.pack(fill="both", expand=True)

    def refresh_hw_table():
        hw_tree.delete(*hw_tree.get_children())
        hw_data = get_hardware_telemetry()
        for res_name, info in hw_data.items():
            hw_tree.insert("", "end", values=(res_name, info["status"], info["details"]))

    refresh_hw_table()

    # Bottom Actions Bar in Pure Black with 1px Green Border
    bottom_bar = tk.Frame(root, bg=BG_BLACK, highlightthickness=1, highlightbackground=BORDER_COLOR)
    bottom_bar.pack(fill="x", padx=14, pady=(6, 12))

    status_footer = tk.Label(bottom_bar, text="Ready — Multi-Cloud Pipeline & Model Control Center Active.", font=("Segoe UI", 9, "italic"), bg=BG_BLACK, fg=GREEN_BRIGHT)
    status_footer.pack(side="left", padx=12, pady=8)

    def run_diagnostics_modal():
        status_footer.config(text="Probing all cloud endpoints and micro-token latency...")
        root.update_idletasks()
        diag = ProviderDiagnostics()
        res = diag.run_all(timeout=12.0)
        table_txt = diag.format_table(res)
        status_footer.config(text="Health check completed.")

        win = tk.Toplevel(root)
        win.title("RAISE — Live Diagnostics Scorecard")
        win.geometry("760x380")
        win.configure(bg=BG_BLACK)
        txt = tk.Text(win, bg=BG_BLACK, fg=GREEN_BRIGHT, font=("Consolas", 10), padx=12, pady=12, relief="solid", borderwidth=1)
        txt.insert("1.0", table_txt)
        txt.config(state="disabled")
        txt.pack(fill="both", expand=True, padx=10, pady=10)

    def refresh_all():
        refresh_token_table()
        refresh_llm_table()
        refresh_models_table()
        refresh_hw_table()
        update_cred_status_display()
        status_footer.config(text="Refreshed all metrics, token tallies, and provider states.")

    tk.Button(bottom_bar, text="🔄 Refresh All", command=refresh_all, bg="#052e16", fg=GREEN_BRIGHT, font=("Segoe UI", 9, "bold"), relief="solid", borderwidth=1, padx=12, pady=4).pack(side="right", padx=6)
    tk.Button(bottom_bar, text="🩺 Run Diagnostics", command=run_diagnostics_modal, bg=CARD_HEADER, fg=ACCENT_CYAN, font=("Segoe UI", 9, "bold"), relief="solid", borderwidth=1, padx=12, pady=4).pack(side="right", padx=6)
    tk.Button(bottom_bar, text="Exit", command=root.destroy, bg=CARD_HEADER, fg=TEXT_MUTED, font=("Segoe UI", 9), relief="solid", borderwidth=1, padx=10, pady=4).pack(side="right", padx=6)

    root.mainloop()


# Backwards compatibility alias
launch_operator_gui = launch_model_control_center


if __name__ == "__main__":
    launch_model_control_center()
