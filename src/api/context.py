"""
RAISE API Context & State Utilities
Manifest tracking, active drawer parsing, client IP resolution,
telemetry tracking, and real-time cancellation tokens.
"""

from __future__ import annotations

import json
import logging
import os
import re
import socket
import time
import urllib.parse
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from fastapi import Request

from src.core.config import settings

logger = logging.getLogger("raise.api.context")

# Document Directories and Manifest
DOCUMENTS_DIR = settings.documents_dir
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOAD_DIR = DOCUMENTS_DIR  # Compatibility alias
MANIFEST_FILE = settings.processed_dir / "ingested_manifest.json"

# Active Abort & Cancellation Token Registry (bounded in-memory)
ACTIVE_ABORTS: Set[str] = set()

# System Telemetry & Operational Metrics Tracker
SYSTEM_START_TIME = time.time()
SYSTEM_METRICS: Dict[str, Any] = {
    "total_queries": 0,
    "successful_queries": 0,
    "failed_queries": 0,
    "latencies": deque(maxlen=500),
}


def record_query_metric(latency: float, success: bool = True):
    SYSTEM_METRICS["total_queries"] += 1
    if success:
        SYSTEM_METRICS["successful_queries"] += 1
    else:
        SYSTEM_METRICS["failed_queries"] += 1
    SYSTEM_METRICS["latencies"].append(round(latency, 3))


def is_aborted(session_id: Optional[str], request_id: Optional[str] = None, redis_client: Any = None) -> bool:
    if session_id and session_id in ACTIVE_ABORTS:
        return True
    if request_id and request_id in ACTIVE_ABORTS:
        return True
    if redis_client:
        try:
            if session_id and redis_client.get(f"abort:{session_id}"):
                return True
            if request_id and redis_client.get(f"abort:{request_id}"):
                return True
        except Exception:
            pass
    return False


def record_abort(session_id: Optional[str], request_id: Optional[str] = None, redis_mgr: Any = None):
    # Bound memory set size
    if len(ACTIVE_ABORTS) > 1000:
        ACTIVE_ABORTS.clear()
    if session_id:
        ACTIVE_ABORTS.add(session_id)
        if redis_mgr and redis_mgr.is_connected and redis_mgr._client:
            try:
                redis_mgr._client.setex(f"abort:{session_id}", 60, "1")
            except Exception:
                pass
    if request_id:
        ACTIVE_ABORTS.add(request_id)
        if redis_mgr and redis_mgr.is_connected and redis_mgr._client:
            try:
                redis_mgr._client.setex(f"abort:{request_id}", 60, "1")
            except Exception:
                pass
    if redis_mgr:
        try:
            redis_mgr.publish_abort(session_id, request_id)
        except Exception:
            pass


def get_lan_ip() -> str:
    """Discover host machine LAN IPv4 address for remote cross-device communication."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def get_authentic_client_ip(request: Request) -> str:
    """
    Extract authentic remote client IP across Cloudflare tunnels, reverse proxies, and Docker bridges.
    Safely resolves X-Forwarded-For and X-Real-IP headers to prevent proxy rate-limiting bypasses.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
        for ip in ips:
            if ip not in ("127.0.0.1", "localhost", "::1"):
                return ip
        if ips:
            return ips[0]
    real_ip = request.headers.get("CF-Connecting-IP") or request.headers.get("X-Real-IP")
    if real_ip and real_ip.strip():
        return real_ip.strip()
    return request.client.host if (request and request.client) else "127.0.0.1"


def get_ready_documents_list() -> List[Dict[str, Any]]:
    """Retrieve list of actively confirmed ready documents from authoritative manifest.
    Does NOT auto-scan or auto-register external PDFs without explicit user upload."""
    if MANIFEST_FILE.exists():
        try:
            data = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
            return data.get("ready_documents", [])
        except Exception:
            return []
    return []


def record_ready_document(
    filename: str,
    pages: int,
    size_mb: float,
    chunks_count: int,
    is_protected: bool = False,
    uploaded_by: str = "user"
):
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"ready_documents": [], "deleted_documents": []}
    if MANIFEST_FILE.exists():
        try:
            manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        except Exception:
            manifest = {"ready_documents": [], "deleted_documents": []}

    deleted = [f for f in manifest.get("deleted_documents", []) if f != filename]
    manifest["deleted_documents"] = deleted

    docs = manifest.get("ready_documents", [])
    updated = False
    for d in docs:
        if d.get("filename") == filename:
            d["pages"] = pages
            d["size_mb"] = size_mb
            d["chunks_count"] = chunks_count
            d["status"] = "ready"
            d["is_protected"] = is_protected if is_protected is not None else d.get("is_protected", False)
            d["uploaded_by"] = uploaded_by or d.get("uploaded_by", "user")
            updated = True
            break
    if not updated:
        docs.append({
            "filename": filename,
            "pages": pages,
            "size_mb": size_mb,
            "chunks_count": chunks_count,
            "status": "ready",
            "is_protected": is_protected,
            "uploaded_by": uploaded_by
        })
    manifest["ready_documents"] = docs
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def remove_ready_document(filename: str) -> bool:
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"ready_documents": [], "deleted_documents": []}
    if MANIFEST_FILE.exists():
        try:
            manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        except Exception:
            manifest = {"ready_documents": [], "deleted_documents": []}

    deleted = manifest.get("deleted_documents", [])
    if filename not in deleted:
        deleted.append(filename)

    docs = manifest.get("ready_documents", [])
    new_docs = [d for d in docs if d.get("filename") != filename]

    manifest["ready_documents"] = new_docs
    manifest["deleted_documents"] = deleted
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return True


def purge_all_ready_documents() -> bool:
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"ready_documents": [], "deleted_documents": []}
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return True


def _parse_drawer_active_docs(raw_val: Any) -> Optional[List[str]]:
    """
    Parse, normalize, and unquote active drawer documents from:
    1. Repeated query params (?active_docs=doc1.pdf&active_docs=doc2.pdf)
    2. Comma-separated query strings (?active_docs=doc1.pdf,doc2.pdf)
    3. JSON array strings (?active_docs=["doc1.pdf", "doc2.pdf"])
    4. URL-encoded spaces and special characters via urllib.parse.unquote_plus
       (e.g., Annual+Report+2024-25+final+upload.pdf or Annual%20Report%202024.pdf)
    """
    if raw_val is None:
        return None

    raw_list = raw_val if isinstance(raw_val, (list, tuple, set)) else [raw_val]
    items_to_process: List[str] = []

    for entry in raw_list:
        if entry is None:
            continue
        raw_str = str(entry).strip()
        if not raw_str or raw_str.lower() in ("[]", "null", "none"):
            continue
        if raw_str.startswith("[") and raw_str.endswith("]"):
            try:
                parsed = json.loads(raw_str)
                if isinstance(parsed, list):
                    for p in parsed:
                        if p is not None and str(p).strip() and str(p).strip().lower() not in ("[]", "null", "none"):
                            items_to_process.append(str(p).strip())
                    continue
            except Exception:
                pass
        items_to_process.append(raw_str)

    cleaned_docs: List[str] = []
    for item in items_to_process:
        tokens = item.split(",") if "," in item else [item]
        for tok in tokens:
            unquoted = urllib.parse.unquote_plus(tok.strip()).strip("\"'")
            if unquoted and unquoted.lower() not in ("[]", "null", "none") and unquoted not in cleaned_docs:
                cleaned_docs.append(unquoted)

    return cleaned_docs


def is_conversational_or_memory_query(query: str) -> bool:
    """
    Detects if a query is a greeting, introduction, memory recall, or general assistant dialogue.
    These queries bypass the document drawer check completely.
    """
    q_clean = query.strip()
    q_lower = q_clean.lower()
    patterns = [
        r"^(he|hi|hello|hey|greetings|howdy)\b",
        r"^good\s+(morning|afternoon|evening|day)\b",
        r"\b(?:my\s+name\s+is|call\s+me)\b",
        r"\b(?:do\s+you\s+know|what\s+is|what's)\s+my\s+name\b",
        r"\bwho\s+am\s+i\b",
        r"\bdo\s+you\s+remember\b",
        r"\b(?:what\s+is|what's)\s+your\s+name\b",
        r"\bwho\s+are\s+you\b",
        r"\bwhat\s+can\s+you\s+do\b",
        r"\bhow\s+are\s+you\b",
        r"\b(?:thank\s+you|thanks|nice\s+to\s+meet\s+you)\b",
        r"\b(?:what\s+did\s+i\s+(?:just\s+)?(?:say|ask))\b",
        r"^(test|hello\s+test|ping)\b",
    ]
    for pat in patterns:
        if re.search(pat, q_clean, re.IGNORECASE):
            return True
    if len(q_clean.split()) <= 6:
        if any(w in q_lower for w in ["who are you", "who r u", "whats your name", "what is your name", "my name", "your name"]):
            return True
    return False


def get_library_documents(postgres_mgr: Any = None) -> Dict[str, Any]:
    """
    Consolidated reader for all confirmed ready documents across manifest and PostgreSQL.
    """
    ready_docs = get_ready_documents_list()
    pg_docs = postgres_mgr.list_documents() if postgres_mgr and hasattr(postgres_mgr, "list_documents") else []

    result_docs = []
    seen = set()

    for r in ready_docs:
        fn = r.get("filename")
        if fn and fn not in seen:
            seen.add(fn)
            clean_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", Path(fn).stem)[:40]
            is_prot = bool(r.get("is_protected", False))
            can_del = not is_prot
            owner_val = r.get("uploaded_by", "system" if is_prot else "user")
            result_docs.append({
                "id": f"doc_{clean_stem}",
                "doc_id": f"doc_{clean_stem}",
                "filename": fn,
                "pages": r.get("pages", 1),
                "size_mb": r.get("size_mb", 1.0),
                "chunks_count": r.get("chunks_count", 0),
                "chunks": r.get("chunks_count", 0),
                "status": "ready",
                "phase": "ready",
                "is_protected": is_prot,
                "can_delete": can_del,
                "deletable": can_del,
                "owner": owner_val,
                "uploaded_at": r.get("processed_at") or "2026-09-05T00:00:00",
                "library": "default"
            })

    for d in pg_docs:
        fn = d.get("filename")
        if fn and fn not in seen:
            seen.add(fn)
            is_prot = bool(d.get("is_protected", False))
            can_del = bool(d.get("can_delete", not is_prot))
            owner_val = d.get("owner", "user")
            result_docs.append({
                "id": d.get("id"),
                "doc_id": d.get("id"),
                "filename": fn,
                "pages": d.get("pages_processed", 1),
                "size_mb": round(d.get("file_size_bytes", 1024 * 1024) / (1024 * 1024), 2),
                "chunks_count": d.get("chunks", 0),
                "chunks": d.get("chunks", 0),
                "status": "ready",
                "phase": "ready",
                "is_protected": is_prot,
                "can_delete": can_del,
                "deletable": can_del,
                "owner": owner_val,
                "uploaded_at": d.get("uploaded_at"),
                "library": d.get("library", "default")
            })

    return {"documents": result_docs, "total_count": len(result_docs)}

