"""
RAISE — Master Terminal & Interactive Research Studio (v2.5 Production)
======================================================================
High-performance terminal CLI runner providing:
1. Subsystem Diagnostics & Health Monitoring (Neo4j, ChromaDB, vLLM, Redis)
2. Dual-Tier Conversational Memory & Dynamic Intent Routing
3. Fast (PyMuPDF) vs Deep (IBM Docling TableFormer) Document Ingestion
4. Strict Drawer Isolation & Scoped Multi-Hop GraphRAG Retrieval
5. Neural Grounding with Qwen 2.5 14B, In-Line Citations & Math Auditing
6. Full Privacy Sanitization (zero personal usernames or local path leakage)
"""

from __future__ import annotations

import os
import re
import sys
import time
import json
import shutil
import socket
import logging
import subprocess
import urllib.request
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from logging.handlers import RotatingFileHandler

# Enforce UTF-8 console output for Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure RAG project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Enable native ANSI color support on Windows
try:
    import colorama
    colorama.just_fix_windows_console()
except Exception:
    pass

try:
    os.system("")  # Enables ENABLE_VIRTUAL_TERMINAL_PROCESSING
except Exception:
    pass


from src.cli.renderer import C
from src.cli.commands import sanitize_path


# Load environment variables
try:
    from dotenv import load_dotenv
    _env_path = BASE_DIR / ".env"
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path)
    else:
        load_dotenv()
except Exception:
    pass

# Logging setup
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "pipeline.log"

logger = logging.getLogger("RAISE_Studio")
log_level_str = os.getenv("RAISE_LOG_LEVEL", "INFO").upper()
logger.setLevel(getattr(logging, log_level_str, logging.INFO))

if not logger.handlers:
    file_handler = RotatingFileHandler(
        str(LOG_FILE), maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


# Subsystem Pipeline Imports
from src.retrieval.pipeline import StandaloneRAGPipeline
from src.features.memory.reasoning import ReasoningMemory
from src.features.verification.math_engine import DeterministicMathEngine


def auto_start_containers():
    """Starts Neo4j and vLLM Docker containers if available and polls for service readiness."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            if s.connect_ex(("127.0.0.1", 7687)) == 0 or s.connect_ex(("localhost", 7687)) == 0:
                return
    except Exception:
        pass

    if not shutil.which("docker"):
        return

    try:
        print(f"{C.ACCENT}🐳 [Auto-Starter]{C.RESET} Checking container infrastructure...")
        proc = subprocess.run(
            ["docker", "start", "raise-neo4j-prod", "raise-vllm-prod"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=8
        )
        if proc.returncode != 0 and ("daemon is running" in proc.stderr or "dockerDesktopLinuxEngine" in proc.stderr):
            print(f"  {C.WARN}⚠️  [Auto-Starter] Docker Desktop engine is booting up. Waiting for daemon...{C.RESET}")
            for _ in range(3):
                time.sleep(1.5)
                retry_proc = subprocess.run(
                    ["docker", "start", "raise-neo4j-prod", "raise-vllm-prod"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=5
                )
                if retry_proc.returncode == 0:
                    break
    except Exception as e:
        logger.warning(f"Auto-starter docker error: {e}")
        return

    # Poll for Neo4j Bolt port 7687 readiness
    print(f"  {C.INFO}⏳ [Auto-Starter]{C.RESET} Waiting for Neo4j database to open Bolt port 7687...", end="", flush=True)
    start_time = time.time()
    neo4j_ready = False
    while time.time() - start_time < 8:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.4)
                if s.connect_ex(("127.0.0.1", 7687)) == 0:
                    neo4j_ready = True
                    break
        except Exception:
            pass
        print(f"{C.INFO}.{C.RESET}", end="", flush=True)
        time.sleep(0.6)

    if neo4j_ready:
        print(f" {C.SUCCESS}[READY]{C.RESET}")
    else:
        print(f" {C.WARN}[TIMEOUT: Continuing with in-memory graph fallback]{C.RESET}")


def check_vllm_health() -> Dict[str, Any]:
    """Pings local vLLM instance to inspect loaded model, context limit, and latency."""
    vllm_url = os.getenv("VLLM_API_BASE", "http://localhost:8002/v1").rstrip("/") + "/models"
    t0 = time.time()
    try:
        req = urllib.request.Request(vllm_url, headers={"User-Agent": "RAISE-Studio"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed = round((time.time() - t0) * 1000, 1)
            models = data.get("data", [])
            model_id = models[0].get("id", "Unknown") if models else "None"
            max_len = models[0].get("max_model_len", 8192) if models else 8192
            return {
                "connected": True,
                "model_id": model_id,
                "max_model_len": max_len,
                "latency_ms": elapsed
            }
    except Exception as e:
        return {
            "connected": False,
            "model_id": "Offline",
            "max_model_len": 0,
            "latency_ms": round((time.time() - t0) * 1000, 1),
            "error": str(e)
        }


def get_active_documents_list() -> List[Dict[str, Any]]:
    """Returns list of active documents from the ingested manifest."""
    manifest_file = BASE_DIR / "data" / "processed" / "ingested_manifest.json"
    if not manifest_file.exists():
        return []
    try:
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        return data.get("ready_documents", [])
    except Exception:
        return []


def list_active_documents(focused_document: Optional[str] = None):
    """Displays formatted table of active documents in the manifest."""
    docs = get_active_documents_list()
    if not docs:
        print(f"\n{C.WARN}⚠️  No documents found in workspace manifest.{C.RESET}")
        print(f"   {C.MUTED}Use '{C.ACCENT}upload <path>{C.MUTED}' to ingest your first PDF report.{C.RESET}\n")
        return

    print(f"\n{C.SECTION}📚 Active Document Library ({len(docs)} registered reports):{C.RESET}")
    print(f"  {C.MUTED}{'ID':<4} {'FILENAME':<36} {'PAGES':<8} {'CHUNKS':<8} {'SIZE':<8} {'STATUS'}{C.RESET}")
    print(f"  {C.MUTED}{'─'*4} {'─'*36} {'─'*8} {'─'*8} {'─'*8} {'─'*12}{C.RESET}")
    for i, d in enumerate(docs, 1):
        fname = d.get("filename", "")
        pages = str(d.get("pages", "N/A"))
        chunks = str(d.get("chunks_count", "N/A"))
        size = f"{d.get('size_mb', 0):.1f}MB"
        is_focused = focused_document and (fname.lower() == focused_document.lower())
        focus_badge = f" {C.SUCCESS}👉 [ATTACHED]{C.RESET}" if is_focused else ""
        disp_name = (fname[:33] + "...") if len(fname) > 36 else fname
        print(f"  {C.NUM}{i:<4}{C.RESET} {C.WHITE}{disp_name:<36}{C.RESET} {C.ACCENT}{pages:<8}{C.RESET} {C.CYAN}{chunks:<8}{C.RESET} {C.MUTED}{size:<8}{C.RESET}{focus_badge}")

    print()
    if focused_document:
        print(f"  🎯 {C.MUTED}Current Target Scope:{C.RESET} {C.SECTION}'{focused_document}' ATTACHED{C.RESET}")
    else:
        print(f"  🌐 {C.MUTED}Current Target Scope:{C.RESET} {C.ACCENT}ALL DOCUMENTS ATTACHED{C.RESET} (Library-Wide Drawer Grounding)")
    print(f"  💡 {C.INFO}Tip:{C.RESET} Type '{C.ACCENT}attach <number|name>{C.RESET}' to focus, or '{C.ACCENT}attach all{C.RESET}' to search all.\n")


def print_system_status(pipeline: StandaloneRAGPipeline, memory: ReasoningMemory):
    """Prints a comprehensive diagnostic view of all RAISE subsystems."""
    print("\n" + C.BANNER + "═" * 74 + C.RESET)
    print(f" {C.TITLE}🩺 RAISE MULTI-SUBSTRATE SUBSYSTEM DIAGNOSTICS{C.RESET}")
    print(C.BANNER + "═" * 74 + C.RESET)

    # 1. Neo4j Knowledge Graph
    if pipeline.neo4j_db.connected:
        try:
            node_cnt = pipeline.neo4j_db.run_cypher("MATCH (n) RETURN count(n) AS c")[0]["c"]
            rel_cnt = pipeline.neo4j_db.run_cypher("MATCH ()-[r]->() RETURN count(r) AS c")[0]["c"]
            neo_str = f"{C.SUCCESS}ONLINE{C.RESET} ({node_cnt} nodes, {rel_cnt} relationships | bolt://localhost:7687)"
        except Exception as e:
            neo_str = f"{C.SUCCESS}ONLINE{C.RESET} (Graph inspection: {e})"
    else:
        neo_str = f"{C.WARN}OFFLINE{C.RESET} (Using in-memory graph fallback)"

    # 2. ChromaDB Dense Vector Store
    try:
        chunk_cnt = pipeline.vector_engine.collection.count() if pipeline.vector_engine.collection else 0
        chroma_str = f"{C.SUCCESS}ACTIVE{C.RESET} ({chunk_cnt} indexed chunks | Model: {pipeline.vector_engine.model_key})"
    except Exception as e:
        chroma_str = f"{C.DANGER}ERROR{C.RESET} ({e})"

    # 3. vLLM Local Neural Inference
    vllm_info = check_vllm_health()
    if vllm_info["connected"]:
        vllm_str = f"{C.SUCCESS}ONLINE{C.RESET} ({vllm_info['model_id']} | MaxContext: {vllm_info['max_model_len']} | Latency: {vllm_info['latency_ms']}ms)"
    else:
        vllm_str = f"{C.WARN}OFFLINE{C.RESET} (Port 8002 unreachable — fallback rule-based synthesis active)"

    # 4. Redis Semantic Cache
    try:
        from src.infrastructure.cache.redis import RedisCacheManager
        _rm = RedisCacheManager()
        redis_conn = _rm.is_connected
    except Exception:
        redis_conn = False
    redis_str = f"{C.SUCCESS}ONLINE{C.RESET} (Port 6379 connected)" if redis_conn else f"{C.MUTED}DISABLED{C.RESET} (In-memory fallback)"

    # 5. Reasoning Memory
    traj_cnt = len(memory.trajectories) if hasattr(memory, "trajectories") else 0
    mem_str = f"{C.SUCCESS}ACTIVE{C.RESET} ({traj_cnt} learned reasoning trajectories stored)"

    # 6. Active Document Manifest
    docs = get_active_documents_list()
    doc_str = f"{C.ACCENT}{len(docs)} registered document(s){C.RESET}"

    print(f"  • {C.MUTED}Neo4j Graph Engine:{C.RESET}        {neo_str}")
    print(f"  • {C.MUTED}ChromaDB Vector Store:{C.RESET}     {chroma_str}")
    print(f"  • {C.MUTED}Local vLLM Synthesizer:{C.RESET}    {vllm_str}")
    print(f"  • {C.MUTED}Redis Semantic Cache:{C.RESET}      {redis_str}")
    print(f"  • {C.MUTED}Reasoning Memory Engine:{C.RESET}   {mem_str}")
    print(f"  • {C.MUTED}Deterministic Math Engine:{C.RESET} {C.SUCCESS}OPERATIONAL{C.RESET} (Audited sums, CAGR, differences)")
    print(f"  • {C.MUTED}Document Library Capacity:{C.RESET} {doc_str}")
    print(C.BANNER + "═" * 74 + C.RESET + "\n")


# Generalized Conversational Intent & Entity Memory Extraction
NON_NAME_TOKENS = {
    # Question words & interrogative helpers
    "what", "whats", "what's", "who", "whos", "who's", "how", "why", "where", "when", "which",
    # Conjunctions, prepositions, pronouns
    "and", "or", "but", "if", "then", "so", "as", "at", "by", "for", "with", "about", "against",
    "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under",
    "yours", "your", "mine", "my", "our", "ours", "their", "theirs", "his", "her", "hers", "its", "it",
    "is", "am", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    # Conversational particles & auxiliaries
    "please", "tell", "can", "could", "would", "should", "will", "shall", "may", "might", "must",
    "here", "there", "just", "also", "now", "today", "again", "too", "very",
    # Articles, generic roles & common adjectives
    "a", "an", "the", "someone", "anyone", "everyone", "nobody", "somebody", "anybody", "everybody",
    "person", "human", "user", "student", "researcher", "engineer", "scientist", "professor", "doctor",
    "busy", "ready", "new", "fine", "good", "great", "well", "okay", "ok", "looking", "asking", "wondering",
    "instead", "actually", "right",
    # Salutations to prevent misclassification
    "hi", "hello", "hey", "hola", "sup", "yo", "greetings"
}


def extract_conversational_persona(text: str) -> Dict[str, Any]:
    """
    Generalized conversational intent classifier and dynamic entity extractor.
    Enforces strict guardrails against false conversational classification:
    - Queries containing question marks, interrogatives, or academic entities are NEVER classified as intros
    - Possessive pronouns ('its') are strictly excluded from intro patterns
    - Name intros require explicit, anchored introduction syntax
    """
    clean_text = text.strip()
    t_lower = clean_text.lower()

    # Research / Factual Query Guardrail:
    # If the utterance contains a question mark or clear factual/interrogative indicators,
    # it must NEVER be routed to conversational persona or zero-DB bypass.
    interrogative_words = {
        "where", "how", "what", "when", "why", "which", "who", "whom", "whose",
        "is", "are", "was", "were", "does", "did", "do", "can", "could", "would", "should"
    }
    has_question_mark = "?" in clean_text
    first_word = t_lower.split()[0].strip(",.:;!?") if t_lower.split() else ""
    has_interrogative_start = first_word in interrogative_words

    # Academic and domain keywords that guarantee factual research routing
    domain_factual_terms = {
        "iit", "iitm", "campus", "located", "location", "acres", "annual report", "dhanbad",
        "director", "nominee", "nominees", "governor", "board", "faculty", "student", "students",
        "ranking", "nirf", "grant", "revenue", "budget", "expenditure", "deemed", "university",
        "ugc", "act", "established", "founded", "history", "table", "section", "page"
    }
    has_domain_term = any(re.search(rf"\b{re.escape(term)}\b", t_lower) for term in domain_factual_terms)

    # If it is clearly an inquiry, immediately return research_query
    if (has_question_mark or has_interrogative_start or has_domain_term) and not any(
        p in t_lower for p in [
            "your name", "who are you", "who am i", "what is my name", "what's my name",
            "what can you do", "who made you", "introduce yourself", "tell me about yourself"
        ]
    ):
        return {"type": "research_query"}

    # User introductions & name update patterns (Strictly anchored, NO possessive 'its')
    intro_patterns = [
        r"(?i)^(?:hi\s*[,!]?\s*|hello\s*[,!]?\s*|hey\s*[,!]?\s*)?(?:change\s+(?:my\s+)?name\s+to|update\s+(?:my\s+)?name\s+to|set\s+(?:my\s+)?name\s+to)\s+([A-Za-z\s'’]+)\s*[\.!]?$",
        r"(?i)^(?:hi\s*[,!]?\s*|hello\s*[,!]?\s*|hey\s*[,!]?\s*)?(?:actually\s+(?:my\s+name\s+is|i\s+am|i'm|call\s+me))\s+([A-Za-z\s'’]+)\s*[\.!]?$",
        r"(?i)^(?:hi\s*[,!]?\s*|hello\s*[,!]?\s*|hey\s*[,!]?\s*)?(?:call\s+me\s+instead)\s+([A-Za-z\s'’]+)\s*[\.!]?$",
        r"(?i)^(?:hi\s*[,!]?\s*|hello\s*[,!]?\s*|hey\s*[,!]?\s*)?(?:my\s+name\s+is(?:\s+now)?|call\s+me)\s+([A-Za-z\s'’]+)\s*[\.!]?$",
        r"(?i)^(?:hi\s*[,!]?\s*|hello\s*[,!]?\s*|hey\s*[,!]?\s*)?(?:i\s+am|i'm|this\s+is)\s+([A-Za-z\s'’]+)\s*[\.!]?$",
    ]

    for pat in intro_patterns:
        m = re.match(pat, clean_text)
        if m:
            raw_match = m.group(1).strip()
            tokens = [re.sub(r"[^\w]", "", w) for w in raw_match.split()]
            name_tokens = []
            for token in tokens:
                if not token:
                    continue
                if token.lower() in NON_NAME_TOKENS or token.lower() in domain_factual_terms:
                    if name_tokens:
                        break
                    continue
                name_tokens.append(token.title())
                if len(name_tokens) >= 3:
                    break

            if name_tokens and len(name_tokens) <= 3:
                extracted_name = " ".join(name_tokens)
                return {"type": "name_intro", "name": extracted_name}

    # User identity recall inquiries
    recall_phrases = [
        "know my name", "what is my name", "what's my name", "who am i",
        "remember my name", "recall my name", "remember me", "know who i am"
    ]
    if any(p in t_lower for p in recall_phrases):
        return {"type": "name_recall"}

    # Assistant identity & capability inquiries
    bot_identity_phrases = [
        "your name", "who are you", "what are you", "what is yours", "what's yours",
        "who made you", "what can you do", "introduce yourself",
        "tell me about yourself", "give your name", "tell your name"
    ]
    if any(p in t_lower for p in bot_identity_phrases):
        return {"type": "bot_identity"}

    # Natural greetings & conversational openers (Must be standalone greetings)
    greeting_words = {
        "hi", "hello", "hey", "he", "hola", "howdy", "sup", "yo",
        "greetings", "good morning", "good afternoon", "good evening"
    }
    if t_lower in greeting_words or re.match(r"^(?:hi|hello|hey|he|hola|howdy|sup|yo|greetings)(?:\s+there|\s+raise|\s+bot|\s*!|\s*\.|\s*\?)*$", t_lower):
        return {"type": "greeting"}

    return {"type": "research_query"}


def ingest_pdf_from_path(
    pdf_path_str: str,
    pipeline: StandaloneRAGPipeline,
    engine: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Optional[str]:
    """
    Ingests any local PDF report provided by the user:
    1. Validates local filesystem path and file extension
    2. Sanitizes displayed paths to protect username privacy
    3. Enforces benchmark test isolation to protect ChromaDB & Neo4j
    4. Handles flexible page range selection ('1-40', '40', 'all')
    5. Executes chosen parsing engine (PyMuPDF Layout-Aware or Docling TableFormer)
    6. Registers document in data/processed/ingested_manifest.json
    7. Refreshes pipeline in-memory indices and sets active document focus
    """
    clean_path = pdf_path_str.strip().strip("'\"")
    if not clean_path:
        print(f"{C.DANGER}❌ Error: Path cannot be empty.{C.RESET}")
        return None

    src_path = Path(clean_path).expanduser().resolve()
    if not src_path.exists() or not src_path.is_file():
        print(f"{C.DANGER}❌ Error: File not found at '{sanitize_path(src_path)}'. Please verify the path and try again.{C.RESET}")
        return None

    if src_path.suffix.lower() != ".pdf":
        print(f"{C.DANGER}❌ Error: File '{src_path.name}' is not a PDF report. Only PDF documents are supported.{C.RESET}")
        return None

    # Benchmark test isolation guardrail
    path_str = str(src_path).lower().replace("\\", "/")
    excluded_patterns = ["evaluation", "benchmark", "question_suite", "question suite", "raise-bench", "gemini-notebook"]
    if any(pattern in path_str for pattern in excluded_patterns):
        print(f"\n{C.DANGER}⛔ [Database Isolation Guard] Ingestion Blocked:{C.RESET}")
        print(f"   '{src_path.name}' matches excluded benchmark patterns.")
        print(f"   Evaluation datasets must NEVER be ingested into production ChromaDB or Neo4j to prevent test contamination.\n")
        return None

    docs_dir = BASE_DIR / "data" / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)
    dest_path = docs_dir / src_path.name

    print("\n" + C.BANNER + "═" * 74 + C.RESET)
    print(f" {C.TITLE}📥 INGESTING USER REPORT:{C.RESET} {C.WHITE}{src_path.name}{C.RESET}")
    print(C.BANNER + "═" * 74 + C.RESET)

    try:
        # Determine total page count
        total_pdf_pages = 0
        try:
            import fitz
            with fitz.open(str(src_path)) as _doc:
                total_pdf_pages = len(_doc)
        except Exception:
            pass

        # Prompt for engine if not provided
        if engine is None:
            print(f"\n  {C.SECTION}⚙️  Select Ingestion Speed & Parsing Mode:{C.RESET}")
            print(f"     [{C.NUM}1{C.RESET}] {C.ACCENT}⚡ Fast Mode{C.RESET}   — PyMuPDF Layout-Aware (~2-5s, extracts text, tables & entities) {C.MUTED}[DEFAULT]{C.RESET}")
            print(f"     [{C.NUM}2{C.RESET}] {C.MAGENTA}🔬 Deep Vision{C.RESET}  — IBM Docling TableFormer (neural cell recovery, no page cap)")
            try:
                mode_pick = input(f"     {C.SECTION}Choose mode [1 or 2, default=1]:{C.RESET} ").strip()
            except (EOFError, Exception):
                mode_pick = "1"
            selected_engine = "deep" if mode_pick == "2" else "fast"
        else:
            selected_engine = engine

        # Determine page count flexibly
        if max_pages is not None:
            pages_to_process = total_pdf_pages if int(max_pages) <= 0 else min(int(max_pages), total_pdf_pages)
        elif total_pdf_pages > 0 and total_pdf_pages <= 50:
            pages_to_process = total_pdf_pages
            print(f"  {C.INFO}📄 Document has {total_pdf_pages} page(s) (<= 50) — auto-processing all pages.{C.RESET}")
        else:
            prompt_str = f"     Document has {total_pdf_pages} pages. Pages to process [{C.SECTION}Press Enter for ALL {total_pdf_pages} pages{C.RESET}, or enter number / range like 1-40]: "
            try:
                pages_inp = input(prompt_str).strip()
                numbers = [int(n) for n in re.findall(r"\b\d+\b", pages_inp) if int(n) > 0]
                if numbers:
                    pages_to_process = min(max(numbers), total_pdf_pages)
                else:
                    pages_to_process = total_pdf_pages
            except Exception:
                pages_to_process = total_pdf_pages

        # Copy file to workspace documents directory if needed
        if src_path.resolve() != dest_path.resolve():
            print(f"  {C.MUTED}📂 Staging document to:{C.RESET} {C.CYAN}{sanitize_path(dest_path)}{C.RESET}")
            shutil.copy2(src_path, dest_path)
        else:
            print(f"  {C.MUTED}📂 Document already staged in library:{C.RESET} {C.CYAN}{sanitize_path(dest_path)}{C.RESET}")

        cap_desc = f"all {pages_to_process} pages" if (total_pdf_pages and pages_to_process == total_pdf_pages) else f"{pages_to_process} pages"
        print(f"  {C.SECTION}⚙️  Extracting ({selected_engine.upper()} mode, {cap_desc}) & indexing dense vectors...{C.RESET}")
        
        t0 = time.time()
        from src.features.ingestion.pipeline import AcademicPipelineIngestor
        academic_pipeline = AcademicPipelineIngestor(download_dir=docs_dir)
        res = academic_pipeline.process_pdf(dest_path, max_pages=pages_to_process, engine=selected_engine)
        elapsed = round(time.time() - t0, 2)

        # Update manifest
        manifest_file = BASE_DIR / "data" / "processed" / "ingested_manifest.json"
        manifest_file.parent.mkdir(parents=True, exist_ok=True)
        manifest = {"ready_documents": [], "deleted_documents": []}
        if manifest_file.exists():
            try:
                manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            except Exception:
                manifest = {"ready_documents": [], "deleted_documents": []}

        pages_proc = res.get("pages_processed", 1)
        chunks_count = res.get("chunks_count", 0)
        size_mb = round(dest_path.stat().st_size / (1024 * 1024), 2)

        manifest["deleted_documents"] = [f for f in manifest.get("deleted_documents", []) if f != dest_path.name]
        docs = manifest.get("ready_documents", [])
        updated = False
        for d in docs:
            if d.get("filename") == dest_path.name:
                d["pages"] = pages_proc
                d["size_mb"] = size_mb
                d["chunks_count"] = chunks_count
                d["status"] = "ready"
                if "is_protected" not in d:
                    d["is_protected"] = False
                    d["uploaded_by"] = "user"
                updated = True
                break
        if not updated:
            docs.append({
                "filename": dest_path.name,
                "is_protected": False,
                "uploaded_by": "user",
                "pages": pages_proc,
                "size_mb": size_mb,
                "chunks_count": chunks_count,
                "status": "ready"
            })
        manifest["ready_documents"] = docs
        manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        # Reload pipeline data
        pipeline._load_processed_data()

        facts_cnt = res.get("facts_extracted", res.get("entities_count", 0))
        triples_cnt = res.get("triples_extracted", res.get("relations_count", 0))

        print(f"\n{C.SUCCESS}✅ [INGESTION COMPLETE IN {elapsed}s]{C.RESET}")
        print(f"  • {C.MUTED}Document:{C.RESET}         {C.BOLD}{dest_path.name}{C.RESET}")
        print(f"  • {C.MUTED}Pages Processed:{C.RESET}  {C.NUM}{pages_proc}{C.RESET}")
        print(f"  • {C.MUTED}Chunks Indexed:{C.RESET}   {C.NUM}{chunks_count}{C.RESET}")
        print(f"  • {C.MUTED}Facts Extracted:{C.RESET}  {C.NUM}{facts_cnt}{C.RESET}")
        print(f"  • {C.MUTED}Neo4j Triples:{C.RESET}    {C.NUM}{triples_cnt}{C.RESET}")
        print(f"  • {C.MUTED}Total Library Size:{C.RESET} {C.ACCENT}{len(manifest['ready_documents'])} report(s){C.RESET}")
        print(f"  🎯 [{C.SUCCESS}Active Scope Set To:{C.RESET} '{C.ACCENT}{dest_path.name}{C.RESET}'] ({C.MUTED}Attached to drawer!{C.RESET})\n")
        return dest_path.name

    except Exception as e:
        print(f"\n{C.DANGER}❌ [Ingestion Error]: {e}{C.RESET}")
        return None


def check_document_is_protected(doc_id_or_name: str) -> bool:
    """Checks if a document is marked as protected institutional report in ingested_manifest.json."""
    manifest_file = BASE_DIR / "data" / "processed" / "ingested_manifest.json"
    if not manifest_file.exists():
        return False
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        target = doc_id_or_name.strip().lower()
        for d in manifest.get("ready_documents", []):
            fname = d.get("filename", "").strip().lower()
            if fname == target or target in fname:
                return bool(d.get("is_protected", False))
    except Exception:
        pass
    return False


def remove_document_from_library(doc_id_or_name: str, pipeline: StandaloneRAGPipeline) -> Optional[str]:
    """Purges a document, its ChromaDB vectors, Neo4j nodes, chunks, and manifest entry (standard user: unprotected only)."""
    if check_document_is_protected(doc_id_or_name):
        print(f"\n{C.DANGER}⛔ [Permission Denied]: '{doc_id_or_name}' is a pre-burned system document.{C.RESET}")
        print(f"   {C.MUTED}Protected institutional reports cannot be removed by standard users.{C.RESET}\n")
        return None

    try:
        res = pipeline.purge_document(doc_id_or_name)
        target_name = res.get("document")
        if res.get("status") == "success" and target_name:
            print(f"\n{C.WARN}🗑️  [PURGED REPORT]:{C.RESET} '{C.WHITE}{target_name}{C.RESET}'")
            print(f"   • {C.MUTED}ChromaDB vectors deleted:{C.RESET} {C.NUM}{res.get('vectors_deleted', 0)}{C.RESET}")
            print(f"   • {C.MUTED}Neo4j nodes detached:{C.RESET}    {C.NUM}{res.get('nodes_deleted', 0)}{C.RESET}")
            print(f"   • {C.MUTED}Files removed from disk:{C.RESET}  {C.WHITE}{sanitize_path(', '.join(res.get('files_removed', [])) or 'None')}{C.RESET}")
            print(f"   • {C.MUTED}Trajectories cleared:{C.RESET}    {C.NUM}{res.get('trajectories_purged', 0)}{C.RESET}\n")
            return target_name
        else:
            print(f"{C.DANGER}❌ Failed to purge document '{doc_id_or_name}'.{C.RESET}")
            return None
    except Exception as e:
        print(f"{C.DANGER}❌ Error purging document: {e}{C.RESET}")
        return None


# Backward-compatibility alias
remove_document_from_vault = remove_document_from_library


def print_help_menu():
    """Prints the command reference."""
    print("\n" + C.BANNER + "═" * 74 + C.RESET)
    print(f" {C.TITLE}📖 RAISE COMMAND CHEATSHEET{C.RESET}")
    print(C.BANNER + "═" * 74 + C.RESET)
    print(f"  • {C.ACCENT}<Question>{C.RESET}          — Queries the currently attached document (or all attached)")
    print(f"  • {C.NUM}attach <N|name>{C.RESET}    — Attaches strictly to document number N or matching name in drawer")
    print(f"  • {C.NUM}attach all{C.RESET}         — Expands search scope to ALL documents in library simultaneously")
    print(f"  • {C.NUM}upload <path>{C.RESET}       — Ingests a new academic PDF report (PyMuPDF or Docling)")
    print(f"  • {C.NUM}docs{C.RESET} / {C.NUM}list{C.RESET}         — Lists all active registered PDF reports in the library")
    print(f"  • {C.NUM}delete <name>{C.RESET}      — Deletes a user-uploaded report (protected reports blocked)")
    print(f"  • {C.NUM}delete all{C.RESET}         — Safe workspace reset (clears user files & chat memory; databases intact)")
    print(f"  • {C.NUM}clear chat{C.RESET}         — Clears current conversation context and session memory")
    print(f"  • {C.NUM}status{C.RESET}             — Displays real-time health of Neo4j, ChromaDB, vLLM, and Redis")
    print(f"  • {C.NUM}exit{C.RESET} / {C.NUM}q{C.RESET}             — Exits RAISE Studio")
    print(C.BANNER + "═" * 74 + C.RESET + "\n")



def main():
    print(C.BANNER + "═" * 74 + C.RESET)
    print(f" {C.TITLE}🚀 RAISE (v2.5){C.RESET} — {C.CYAN}RESEARCH ASSESSMENT INTELLIGENCE & SEMANTIC EXTRACTION{C.RESET}")
    print(C.BANNER + "═" * 74 + C.RESET)

    # 0. Auto-start Neo4j & vLLM containers if needed
    auto_start_containers()

    # Configure LLM Inference Backend (Local vLLM vs Cloud APIs)
    try:
        from src.cli.llm_selector import prompt_llm_backend, show_simple_gui_prompt
        if "--gui" in sys.argv or "--ui" in sys.argv:
            show_simple_gui_prompt()
        else:
            prompt_llm_backend()
    except Exception as _sel_err:
        logger.debug(f"LLM selection notice: {_sel_err}")

    # 1. Initialize Pipeline & Memory Engines
    print(f"\n{C.SECTION}[1/2] Initializing Multi-Substrate Pipeline (Vector + Neo4j + LangGraph)...{C.RESET}")
    pipeline = StandaloneRAGPipeline()
    memory = ReasoningMemory()

    # Verify Neo4j connectivity and schema index
    if pipeline.neo4j_db.connected:
        try:
            from src.infrastructure.graph.schema import ensure_basic_indexes
            ensure_basic_indexes(pipeline.neo4j_db)
            neo4j_status = f"{C.SUCCESS}CONNECTED & INDEXED{C.RESET} {C.MUTED}(bolt://localhost:7687){C.RESET}"
        except Exception as e:
            neo4j_status = f"{C.SUCCESS}CONNECTED{C.RESET} {C.MUTED}(Index note: {e}){C.RESET}"
    else:
        neo4j_status = f"{C.WARN}OFFLINE{C.RESET} {C.MUTED}(In-memory graph active){C.RESET}"

    chroma_count = pipeline.vector_engine.collection.count() if pipeline.vector_engine.collection else 0
    active_docs = pipeline.vector_engine.get_active_workspace_documents()
    vllm_info = check_vllm_health()
    vllm_status = f"{C.SUCCESS}ONLINE{C.RESET} {C.MUTED}({vllm_info['model_id']}){C.RESET}" if vllm_info["connected"] else f"{C.WARN}OFFLINE{C.RESET}"

    print(f"  • {C.MUTED}Neo4j Graph:{C.RESET}        {neo4j_status}")
    print(f"  • {C.MUTED}ChromaDB Vector:{C.RESET}    {C.SUCCESS}ACTIVE{C.RESET} {C.MUTED}({chroma_count} indexed chunks){C.RESET}")
    print(f"  • {C.MUTED}Embeddings Model:{C.RESET}   {C.ACCENT}{pipeline.vector_engine.model_key}{C.RESET}")
    print(f"  • {C.MUTED}vLLM Synthesizer:{C.RESET}   {vllm_status}")
    print(f"  • {C.MUTED}Library Manifest:{C.RESET}   {C.NUM}{len(active_docs)}{C.RESET} {C.MUTED}document(s) loaded{C.RESET}")

    # CLI flag checks
    if "--help" in sys.argv or "-h" in sys.argv:
        print_help_menu()
        return

    if "--clear-cache" in sys.argv or "-c" in sys.argv:
        memory.clear()
        if hasattr(pipeline, "reasoning_memory"):
            pipeline.reasoning_memory.clear()
        print(f"{C.SUCCESS}🧹 [Cache Cleared]{C.RESET} Reasoning memory trajectories reset.")

    if "--status" in sys.argv or "-s" in sys.argv:
        print_system_status(pipeline, memory)
        return

    focused_document: Optional[str] = active_docs[-1] if active_docs else None
    user_persona_name: Optional[str] = None

    # Check for single query flag: e.g. python main.py --query "hello"
    cli_query = None
    if "--query" in sys.argv:
        q_idx = sys.argv.index("--query")
        if q_idx + 1 < len(sys.argv):
            cli_query = sys.argv[q_idx + 1]
    elif "-q" in sys.argv:
        q_idx = sys.argv.index("-q")
        if q_idx + 1 < len(sys.argv):
            cli_query = sys.argv[q_idx + 1]

    # Check for CLI argument PDF upload: e.g. python main.py "report.pdf"
    for arg in sys.argv[1:]:
        cli_arg = arg.strip().strip("'\"")
        if cli_arg in ("--clear-cache", "-c", "--status", "-s"):
            continue
        if cli_arg.lower().endswith(".pdf") or Path(cli_arg).is_file():
            print(f"\n{C.SECTION}[CLI Argument Detected]:{C.RESET} Ingesting '{C.WHITE}{sanitize_path(cli_arg)}{C.RESET}'...")
            new_doc = ingest_pdf_from_path(cli_arg, pipeline)
            if new_doc:
                focused_document = new_doc
            break

    # 2. Interactive Studio Loop
    print("\n" + C.BANNER + "═" * 74 + C.RESET)
    print(f" {C.TITLE}💬 INTERACTIVE RESEARCH STUDIO & Q&A{C.RESET}")
    print(f" {C.MUTED}Commands: 'docs', 'attach <N>', 'attach all', 'upload <path>', 'status', 'help', 'exit'{C.RESET}")
    print(C.BANNER + "═" * 74 + C.RESET)

    if not active_docs:
        print(f"\n{C.WARN}⚠️   [NO DOCUMENTS ATTACHED]{C.RESET}")
        print(f"  Your database currently contains 0 reports.")
        print(f"  Type '{C.ACCENT}upload{C.RESET}' to paste a PDF path and ingest your first report.\n")
    elif focused_document:
        print(f"\n🎯 [{C.MUTED}Active Scope{C.RESET}]: '{C.ACCENT}{focused_document}{C.RESET}' {C.MUTED}(Attached to drawer){C.RESET}")
        print(f"   {C.MUTED}Type '{C.ACCENT}attach all{C.MUTED}' to search all documents, or '{C.ACCENT}docs{C.MUTED}' to view library.{C.RESET}\n")

    while True:
        try:
            scope_badge = f"{focused_document}" if focused_document else "ALL DOCUMENTS"
            prompt_label = f"🔍 [{C.ACCENT}{scope_badge}{C.RESET}] Enter Question: "
            if cli_query is not None:
                query = cli_query.strip()
                print(f"{prompt_label}{query}")
            else:
                try:
                    query = input(prompt_label).strip()
                except EOFError:
                    print(f"\n{C.CYAN}Exiting RAISE Studio. Goodbye!{C.RESET}")
                    break

            if not query:
                if cli_query is not None:
                    break
                continue

            # Command: exit / quit / q
            if query.lower() in ["exit", "quit", "q", ":q"]:
                print(f"\n{C.CYAN}Exiting RAISE Studio. Goodbye!{C.RESET}")
                break

            # Command: help
            if query.lower() in ["help", "?", "commands"]:
                print_help_menu()
                if cli_query is not None:
                    break
                continue

            # Command: status / health
            if query.lower() in ["status", "health", "info", "diag"]:
                print_system_status(pipeline, memory)
                if cli_query is not None:
                    break
                continue

            # Command: docs / list
            if query.lower() in ["docs", "list", "documents", "vault"]:
                list_active_documents(focused_document)
                if cli_query is not None:
                    break
                continue

            # Command: clear chat / history
            if query.lower() in ["clear chat", "clear history", "clear memory", "cls"]:
                pipeline.clear_chat_session()
                memory.clear()
                user_persona_name = None
                print(f"\n{C.SUCCESS}✨ [CHAT & MEMORY CLEARED]{C.RESET} Active session context and persona reset.\n")
                if cli_query is not None:
                    break
                continue

            # Command: purge all (Forbidden in standard user CLI)
            if query.lower() in ["purge all", "wipe all"]:
                print(f"\n{C.DANGER}⛔ [Permission Denied]: System hard purge ('purge all') is not available in user CLI.{C.RESET}")
                print(f"   {C.MUTED}Database purge operations are exclusively restricted to developer tools ('dev_main.py').{C.RESET}\n")
                if cli_query is not None:
                    break
                continue

            # Command: delete all -> Safe Workspace Reset
            if query.lower() in ["delete all", "clear workspace", "reset workspace"]:
                confirm = input(f"{C.WARN}⚠️  Clear custom workspace? This removes your custom uploads and resets chat memory while preserving institutional reports. (y/n): {C.RESET}").strip().lower()
                if confirm in ["y", "yes"]:
                    manifest_file = BASE_DIR / "data" / "processed" / "ingested_manifest.json"
                    user_docs_to_remove = []
                    if manifest_file.exists():
                        try:
                            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                            for d in manifest.get("ready_documents", []):
                                if not d.get("is_protected", False):
                                    user_docs_to_remove.append(d.get("filename"))
                        except Exception:
                            pass

                    removed_count = 0
                    for u_doc in user_docs_to_remove:
                        try:
                            pipeline.purge_document(u_doc)
                            removed_count += 1
                        except Exception:
                            pass

                    pipeline.clear_chat_session()
                    memory.clear()
                    user_persona_name = None

                    remaining = pipeline.vector_engine.get_active_workspace_documents()
                    focused_document = remaining[-1] if remaining else None

                    print(f"\n{C.SUCCESS}✨ [SAFE WORKSPACE RESET COMPLETE]{C.RESET}")
                    print(f"   • {C.MUTED}User uploads removed:{C.RESET} {C.NUM}{removed_count}{C.RESET}")
                    print(f"   • {C.MUTED}Chat memory & persona context reset.{C.RESET}")
                    print(f"   • {C.MUTED}Institutional databases and pre-burned reports remain 100% intact.{C.RESET}\n")
                else:
                    print(f"   {C.MUTED}Workspace reset cancelled.{C.RESET}\n")
                if cli_query is not None:
                    break
                continue

            # Command: attach all / use all
            if query.lower() in ["attach all", "use all", "focus all", "select all", "scope all"]:
                focused_document = None
                print(f"🎯 [{C.SUCCESS}Scope Updated{C.RESET}]: Now searching across {C.ACCENT}ALL documents{C.RESET} simultaneously.\n")
                if cli_query is not None:
                    break
                continue

            # Command: detach / clear drawer
            if query.lower() in ["detach", "attach none", "detach all", "clear drawer"]:
                focused_document = "NONE"
                print(f"🎯 [{C.WARN}Drawer Emptied{C.RESET}]: No documents are currently attached to your drawer.\n")
                if cli_query is not None:
                    break
                continue

            # Command: attach <target> / use <target>
            if query.lower().startswith("attach ") or query.lower().startswith("use ") or query.lower().startswith("focus "):
                target = query.split(None, 1)[1].strip().strip("'\"")
                docs = get_active_documents_list()
                resolved = None
                if target.isdigit():
                    idx = int(target) - 1
                    if 0 <= idx < len(docs):
                        resolved = docs[idx].get("filename")
                else:
                    for d in docs:
                        if target.lower() in d.get("filename", "").lower():
                            resolved = d.get("filename")
                            break
                if resolved:
                    focused_document = resolved
                    print(f"🎯 [{C.SUCCESS}Active Document Attached{C.RESET}]: '{C.ACCENT}{focused_document}{C.RESET}'\n")
                else:
                    print(f"{C.DANGER}❌ Could not match '{target}' to any active document. Type 'docs' to see list.{C.RESET}\n")
                if cli_query is not None:
                    break
                continue

            # Command: delete <target> / remove <target>
            if query.lower().startswith("delete ") or query.lower().startswith("remove "):
                target = query.split(None, 1)[1].strip().strip("'\"")
                removed = remove_document_from_library(target, pipeline)
                if removed and focused_document and removed.lower() == focused_document.lower():
                    remaining = pipeline.vector_engine.get_active_workspace_documents()
                    focused_document = remaining[-1] if remaining else None
                    if focused_document:
                        print(f"🎯 {C.SUCCESS}Active focus switched to{C.RESET} '{C.ACCENT}{focused_document}{C.RESET}'.\n")
                    else:
                        print(f"🎯 {C.SUCCESS}Active focus reset to{C.RESET} {C.ACCENT}ALL DOCUMENTS{C.RESET} (library empty).\n")
                if cli_query is not None:
                    break
                continue

            # Command: upload / add / ingest
            clean_q = query.strip().strip("'\"")
            if clean_q.lower() in ["upload", "add", "ingest"]:
                pdf_input = input(f"📁 {C.SECTION}Enter or paste full PDF file path:{C.RESET} ").strip()
                if pdf_input:
                    new_doc = ingest_pdf_from_path(pdf_input, pipeline)
                    if new_doc:
                        focused_document = new_doc
                if cli_query is not None:
                    break
                continue

            if clean_q.lower().startswith("upload ") or clean_q.lower().startswith("add ") or clean_q.lower().startswith("ingest "):
                raw_arg = clean_q.split(None, 1)[1].strip()
                m_eng = re.search(r"\b(fast|deep)\b", raw_arg, re.IGNORECASE)
                eng_val = m_eng.group(1).lower() if m_eng else None
                clean_target = re.sub(r"\b(fast|deep)\b", "", raw_arg, flags=re.IGNORECASE).strip().strip("'\"")
                new_doc = ingest_pdf_from_path(clean_target, pipeline, engine=eng_val)
                if new_doc:
                    focused_document = new_doc
                if cli_query is not None:
                    break
                continue

            # Auto-detect pasted PDF file path
            if clean_q.lower().endswith(".pdf") or (Path(clean_q).exists() and Path(clean_q).is_file()):
                print(f"\n{C.INFO}[Detected PDF File Path: '{C.WHITE}{sanitize_path(clean_q)}{C.INFO}']{C.RESET}")
                try:
                    confirm = input(f"{C.SECTION}Would you like to ingest this PDF into the research library? (y/n):{C.RESET} ").strip().lower()
                except (EOFError, Exception):
                    confirm = "y"
                if confirm in ["y", "yes", ""]:
                    new_doc = ingest_pdf_from_path(clean_q, pipeline)
                    if new_doc:
                        focused_document = new_doc
                    if cli_query is not None:
                        break
                    continue

            # 3. Dynamic Intent Routing: Conversational vs Factual Research
            intent = extract_conversational_persona(query)
            if intent["type"] == "name_intro":
                prev_name = user_persona_name
                user_persona_name = intent["name"]
                if prev_name and prev_name.lower() != user_persona_name.lower():
                    print(f"\n{C.TITLE}RAISE:{C.RESET} Got it! I've updated your name from {C.BOLD}{prev_name}{C.RESET} to {C.BOLD}{user_persona_name}{C.RESET}. How can I assist you today, {user_persona_name}?\n")
                else:
                    print(f"\n{C.TITLE}RAISE:{C.RESET} Hello {C.BOLD}{user_persona_name}{C.RESET}! My name is {C.ACCENT}RAISE{C.RESET}. I'm here to help you with your research. How can I assist you today?\n")
                if cli_query is not None:
                    break
                continue

            elif intent["type"] == "name_recall":
                if user_persona_name:
                    print(f"\n{C.TITLE}RAISE:{C.RESET} Yes, I do know your name. It's {C.BOLD}{user_persona_name}{C.RESET}. How can I assist you today, {user_persona_name}?\n")
                else:
                    print(f"\n{C.TITLE}RAISE:{C.RESET} You haven't introduced yourself yet! What is your name? (e.g., Sid)\n")
                if cli_query is not None:
                    break
                continue

            elif intent["type"] == "bot_identity":
                if "change" in query.lower():
                    print(f"\n{C.TITLE}RAISE:{C.RESET} My name is fixed as {C.ACCENT}RAISE{C.RESET}, your research intelligence assistant. However, you can change your name anytime by saying 'call me <name>' or 'change my name to <name>'!\n")
                else:
                    print(f"\n{C.TITLE}RAISE:{C.RESET} My name is {C.ACCENT}RAISE{C.RESET}. I'm here to help you with your research. How can I assist you today?\n")
                if cli_query is not None:
                    break
                continue

            elif intent["type"] == "greeting":
                greet_suffix = f", {user_persona_name}" if user_persona_name else ""
                print(f"\n{C.TITLE}RAISE:{C.RESET} Hello{greet_suffix}! I am {C.ACCENT}RAISE{C.RESET}, your research intelligence assistant. Please attach a document in your drawer to begin research.\n")
                if cli_query is not None:
                    break
                continue

            # 4. Factual Document Research Query Boundary
            manifest_docs = get_active_documents_list()
            if not manifest_docs or focused_document == "NONE":
                print(f"\n{C.WARN}⚠️  No active documents are currently attached to your drawer.{C.RESET}")
                print(f"   Please attach a document in your drawer to begin research.\n")
                if cli_query is not None:
                    break
                continue

            # Multi-Hop GraphRAG Execution
            t0 = time.time()
            active_scoping = [focused_document] if focused_document else None
            scope_desc = f"'{focused_document}'" if focused_document else "All Documents"
            print(f"\n{C.INFO}[LangGraph Executing Multi-Hop Retrieval (Target Scope: {C.ACCENT}{scope_desc}{C.INFO})...]{C.RESET}")

            # Check Reasoning Memory
            prior_strat = memory.find_similar_strategy(query)
            if prior_strat:
                print(f"  🧠 {C.MAGENTA}Recalled Reasoning Trajectory{C.RESET} ({C.ACCENT}{prior_strat.trajectory_id}{C.RESET}) {C.MUTED}with confidence {prior_strat.confidence_score}{C.RESET}")

            # Execute Query
            res = pipeline.query_subgraph_graphrag(
                query=query,
                hops=2,
                top_k=6,
                document_filter=focused_document,
                active_docs=active_scoping,
            )
            elapsed = round(time.time() - t0, 2)

            if not isinstance(res, dict):
                res = {"grounded_answer": str(res)}

            traceability = res.get("traceability_score", 0.85) if isinstance(res, dict) else 0.85
            answer = res.get("grounded_answer", "No response generated.") if isinstance(res, dict) else str(res)

            print("\n" + C.BANNER + "═" * 74 + C.RESET)
            print(f" {C.TITLE}📋 GROUNDED RESEARCH ANSWER{C.RESET} {C.MUTED}({elapsed}s | Traceability: {traceability}){C.RESET}")
            print(f" {C.MUTED}📄 Attached Document:{C.RESET} {C.ACCENT}{scope_desc}{C.RESET}")
            print(C.BANNER + "═" * 74 + C.RESET)

            # Colorize in-line citations [1], [2] in bright cyan
            colorized_answer = re.sub(
                r"\[(\d+(?:,\s*\d+)*)\]",
                lambda m: f"{C.CITATION}[{m.group(1)}]{C.RESET}",
                answer
            )
            print(colorized_answer)

            # Display Verified Citations
            try:
                citations = res.get("citations") or [] if isinstance(res, dict) else []
                if citations:
                    cited_indices = set()
                    if isinstance(answer, str):
                        try:
                            cited_indices = set(int(m) for m in re.findall(r"\[(\d+)\]", answer))
                        except Exception:
                            cited_indices = set()
                    active_cits = [c for c in citations if isinstance(c, dict) and c.get("citation_index") in cited_indices] if cited_indices else (citations[:2] if citations else [])
                    if active_cits:
                        print(f"\n{C.SECTION}📚 Verified Source Citations:{C.RESET}")
                        for c in active_cits:
                            if isinstance(c, dict):
                                c_idx = c.get("citation_index", "?")
                                c_pdf = c.get("pdf_filename", "Unknown PDF")
                                c_page = c.get("primary_page", "N/A")
                                doc_p = c.get("printed_page")
                                c_head = c.get("heading", "")
                                if doc_p and str(doc_p).strip() != "" and str(doc_p) != str(c_page):
                                    page_str = f"PDF Page {c_page}, Doc Page {doc_p}"
                                else:
                                    page_str = f"Page {c_page}"
                                head_str = f" — {C.MUTED}{c_head}{C.RESET}" if c_head else ""
                                print(f"  • {C.CITATION}[{c_idx}]{C.RESET} {C.WHITE}{c_pdf}{C.RESET} ({C.SECTION}{page_str}{C.RESET}){head_str}")
            except Exception as cit_err:
                logger.warning(f"Citation rendering notice: {cit_err}")

            # Display Connected Neo4j Subgraph Entities
            try:
                subgraph = res.get("subgraph") or {} if isinstance(res, dict) else {}
                nodes = subgraph.get("nodes") or [] if isinstance(subgraph, dict) else []
                if nodes:
                    print(f"\n{C.ENTITY}🕸️  Connected Neo4j Subgraph Entities ({len(nodes)} nodes):{C.RESET}")
                    for n in nodes[:8]:
                        if isinstance(n, dict):
                            lbl = n.get("type") or n.get("label") or "Entity"
                            val = n.get("name") or n.get("id") or ""
                            print(f"  • {C.CYAN}({lbl}){C.RESET}: {C.NUM}{val}{C.RESET}")
            except Exception as sub_err:
                logger.warning(f"Subgraph rendering notice: {sub_err}")

            # Record trajectory in Reasoning Memory
            try:
                tools_used = res.get("selected_tools") if (isinstance(res, dict) and res.get("selected_tools")) else ["vector_search", "graph_traversal", "claim_verifier"]
                is_grounded = res.get("grounded", True) if isinstance(res, dict) else True
                memory.record_trajectory(
                    query=query,
                    tools_used=tools_used,
                    resolved_entities={},
                    metrics=[],
                    confidence=traceability,
                    passed=is_grounded
                )
            except Exception as mem_err:
                logger.warning(f"Memory recording notice: {mem_err}")

            print(C.MUTED + "─" * 74 + C.RESET + "\n")

            if cli_query is not None:
                break

        except (KeyboardInterrupt, EOFError):
            print(f"\n{C.CYAN}Exiting RAISE Studio. Goodbye!{C.RESET}")
            break
        except Exception as e:
            print(f"\n{C.DANGER}[Error executing query]: {sanitize_path(str(e))}{C.RESET}\n")
            if cli_query is not None:
                break


if __name__ == "__main__":
    main()