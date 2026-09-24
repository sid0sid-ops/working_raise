"""
High-Performance Python Bridge to the Native Rust RAISE Acceleration Engine (raise_engine).
Coordinates FFI interoperability via ctypes, providing zero-overhead execution of:
- GGAHC Multi-Signal Boundary Scoring
- Temporary Graph Construction & Community Detection
- Hierarchical Parent-Child Assembly
- Compact BM25 Lexical Retrieval
- High-Throughput QuickSelect Top-K Candidate Pre-Ranking
- Reciprocal Rank Fusion (RRF)
- Text Normalization & PDF Hyphen Repair

Features graceful fallback to pure Python algorithms if the compiled library is unavailable.
"""

from __future__ import annotations

import ctypes
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Engine Initialization & Discovery
# ---------------------------------------------------------------------------
_PYO3_ENGINE: Any = None
_CTYPES_ENGINE: Optional[ctypes.CDLL] = None
_INIT_ATTEMPTED: bool = False


def _ensure_search_paths() -> None:
    """Ensures repository bin/ and release/ directories are in sys.path and DLL search paths."""
    current_file = Path(__file__).resolve()
    repo_root = current_file.parents[3]  # root / raise
    rag_root = current_file.parents[2]   # root / raise / RAG

    candidate_dirs = [
        repo_root / "bin",
        repo_root / "rust" / "raise_engine" / "target" / "release",
        current_file.parent,
        rag_root / "bin",
        rag_root / "rust" / "raise_engine" / "target" / "release",
        Path("/app/bin"),
        Path("/usr/local/lib"),
    ]

    for d in candidate_dirs:
        if d.exists():
            d_str = str(d)
            if d_str not in sys.path:
                sys.path.insert(0, d_str)
            if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(d_str)
                except Exception:
                    pass


def _init_engines() -> None:
    """Initializes Tier 1 (PyO3) or Tier 2 (ctypes) acceleration engines."""
    global _PYO3_ENGINE, _CTYPES_ENGINE, _INIT_ATTEMPTED
    if _INIT_ATTEMPTED:
        return
    _INIT_ATTEMPTED = True

    _ensure_search_paths()

    # Tier 1: Try importing native PyO3 module directly
    try:
        import raise_engine
        _PYO3_ENGINE = raise_engine
        return
    except ImportError:
        _PYO3_ENGINE = None
    except Exception:
        _PYO3_ENGINE = None

    # Tier 2: Try loading dynamic library via ctypes C-ABI
    lib_path = _find_raise_engine_library()
    if lib_path and lib_path.exists():
        try:
            lib = ctypes.CDLL(str(lib_path))
            lib.raise_free_string.argtypes = [ctypes.c_void_p]
            lib.raise_free_string.restype = None

            for func_name in [
                "raise_evaluate_boundaries",
                "raise_assemble_hierarchy",
                "raise_reciprocal_rank_fusion",
                "raise_bm25_search",
                "raise_rank_candidates",
                "raise_normalize_text",
            ]:
                if hasattr(lib, func_name):
                    func = getattr(lib, func_name)
                    func.argtypes = [ctypes.c_char_p]
                    func.restype = ctypes.c_void_p

            _CTYPES_ENGINE = lib
        except Exception:
            _CTYPES_ENGINE = None


def _find_raise_engine_library() -> Optional[Path]:
    """Locates the compiled raise_engine dynamic library."""
    current_file = Path(__file__).resolve()
    repo_root = current_file.parents[3]
    rag_root = current_file.parents[2]
    dll_name = "raise_engine.dll" if sys.platform == "win32" else ("libraise_engine.so" if sys.platform == "linux" else "libraise_engine.dylib")

    search_locations = [
        repo_root / "bin" / dll_name,
        repo_root / "rust" / "raise_engine" / "target" / "release" / dll_name,
        repo_root / "rust" / "raise_engine" / "target" / "debug" / dll_name,
        rag_root / "bin" / dll_name,
        rag_root / "rust" / "raise_engine" / "target" / "release" / dll_name,
        Path("/app/bin") / dll_name,
        Path("/usr/local/lib") / dll_name,
        Path("/app") / dll_name,
        Path.cwd() / "bin" / dll_name,
        Path.cwd() / dll_name,
    ]

    for loc in search_locations:
        if loc.exists():
            return loc
    return None


def get_rust_backend_type() -> str:
    """Returns 'pyo3', 'ctypes', or 'python' indicating active execution engine."""
    _init_engines()
    if _PYO3_ENGINE is not None:
        return "pyo3"
    if _CTYPES_ENGINE is not None:
        return "ctypes"
    return "python"


def is_rust_engine_available() -> bool:
    """Returns True if either PyO3 or ctypes Rust acceleration is active."""
    return get_rust_backend_type() in ("pyo3", "ctypes")


def get_rust_engine() -> Optional[ctypes.CDLL]:
    """Backward compatibility: returns ctypes CDLL if loaded."""
    _init_engines()
    return _CTYPES_ENGINE


# ---------------------------------------------------------------------------
# C-ABI Helper (Tier 2 Fallback)
# ---------------------------------------------------------------------------
def _call_rust_ffi(func_name: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Helper to execute JSON-based C-ABI calls into Rust via ctypes."""
    _init_engines()
    if not _CTYPES_ENGINE or not hasattr(_CTYPES_ENGINE, func_name):
        return None

    try:
        func = getattr(_CTYPES_ENGINE, func_name)
        input_bytes = json.dumps(payload).encode("utf-8")
        raw_ptr = func(input_bytes)
        if not raw_ptr:
            return None

        res_str = ctypes.string_at(raw_ptr).decode("utf-8")
        _CTYPES_ENGINE.raise_free_string(raw_ptr)

        parsed = json.loads(res_str)
        if isinstance(parsed, dict) and "error" in parsed:
            return None
        return parsed
    except Exception:
        return None


# ---------------------------------------------------------------------------
# High-Level Acceleration Functions
# ---------------------------------------------------------------------------

def evaluate_boundaries_rust(
    candidates: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> Optional[Tuple[List[Dict[str, Any]], Dict[str, str]]]:
    """
    Evaluates candidate boundaries in Rust.
    Returns: (list_of_boundary_decisions, dict_of_node_communities) or None.
    """
    _init_engines()

    # Tier 1: PyO3
    if _PYO3_ENGINE is not None and hasattr(_PYO3_ENGINE, "evaluate_boundaries"):
        try:
            cand_json = json.dumps(candidates)
            conf_json = json.dumps(config) if config else "{}"
            raw = _PYO3_ENGINE.evaluate_boundaries(cand_json, conf_json)
            parsed = json.loads(raw)
            if "decisions" in parsed:
                return parsed["decisions"], parsed.get("communities", {})
        except Exception:
            pass

    # Tier 2: ctypes
    res = _call_rust_ffi("raise_evaluate_boundaries", {
        "candidates": candidates,
        "config": config,
    })
    if res and "decisions" in res:
        return res["decisions"], res.get("communities", {})

    return None


def evaluate_boundaries_compact_rust(
    features_flat: List[float],
    config_json: Optional[str] = None,
) -> Optional[List[Tuple[int, float, float]]]:
    """
    Evaluates boundary decisions using compact numeric feature buffer in Rust (Pattern 2).
    Zero-JSON, zero-string allocations across the FFI boundary.
    Input: Flat list of floats where each row has 11 values:
           [tokens_a, tokens_b, is_table_or_figure, structural_strength, semantic_discontinuity,
            topic_transition, entity_continuity, relationship_continuity, graph_connectivity,
            community_continuity, cross_section].
    Returns: List of (decision_code, boundary_score, confidence) tuples:
             decision_code: 0 = MERGE, 1 = SPLIT, 2 = PRESERVE.
    """
    _init_engines()

    if _PYO3_ENGINE is not None and hasattr(_PYO3_ENGINE, "evaluate_boundaries_compact"):
        try:
            return _PYO3_ENGINE.evaluate_boundaries_compact(features_flat, config_json)
        except Exception:
            pass

    return None



def assemble_hierarchy_rust(
    candidates: List[Dict[str, Any]],
    decisions: List[Dict[str, Any]],
    document_id: str,
    university: str,
    filename: str,
    config: Dict[str, Any],
) -> Optional[Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]]:
    """
    Assembles parent/child chunks and propositions in Rust.
    Returns: (child_chunks, parent_chunks, propositions) or None.
    """
    _init_engines()

    # Tier 1: PyO3
    if _PYO3_ENGINE is not None and hasattr(_PYO3_ENGINE, "assemble_hierarchy"):
        try:
            cand_json = json.dumps(candidates)
            dec_json = json.dumps(decisions)
            conf_json = json.dumps(config) if config else "{}"
            raw = _PYO3_ENGINE.assemble_hierarchy(
                cand_json, dec_json, document_id, university, filename, conf_json
            )
            parsed = json.loads(raw)
            if "child_chunks" in parsed:
                return parsed["child_chunks"], parsed.get("parent_chunks", []), parsed.get("propositions", [])
        except Exception:
            pass

    # Tier 2: ctypes
    res = _call_rust_ffi("raise_assemble_hierarchy", {
        "candidates": candidates,
        "decisions": decisions,
        "document_id": document_id,
        "university": university,
        "filename": filename,
        "config": config,
    })
    if res and "child_chunks" in res:
        return res["child_chunks"], res.get("parent_chunks", []), res.get("propositions", [])

    return None


def reciprocal_rank_fusion_rust(
    ranked_channels: List[List[str]],
    k: int = 60,
) -> Optional[List[Dict[str, Any]]]:
    """
    Executes Reciprocal Rank Fusion in Rust.
    """
    _init_engines()

    # Tier 1: PyO3
    if _PYO3_ENGINE is not None and hasattr(_PYO3_ENGINE, "reciprocal_rank_fusion"):
        try:
            ch_json = json.dumps(ranked_channels)
            raw = _PYO3_ENGINE.reciprocal_rank_fusion(ch_json, k)
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                # Ensure dual id and chunk_id compatibility
                for item in parsed:
                    if "id" in item and "chunk_id" not in item:
                        item["chunk_id"] = item["id"]
                return parsed
        except Exception:
            pass

    # Tier 2: ctypes
    res = _call_rust_ffi("raise_reciprocal_rank_fusion", {
        "ranked_channels": ranked_channels,
        "k": k,
    })
    if res and "results" in res:
        results = res["results"]
        for item in results:
            if "id" in item and "chunk_id" not in item:
                item["chunk_id"] = item["id"]
        return results

    return None


def bm25_search_rust(
    docs: List[Tuple[str, str]],
    query: str,
    top_k: int = 10,
    k1: float = 1.2,
    b: float = 0.75,
) -> Optional[List[Tuple[str, float]]]:
    """
    Searches in-memory documents with compact Okapi BM25 in Rust.
    """
    _init_engines()

    # Tier 1: PyO3
    if _PYO3_ENGINE is not None and hasattr(_PYO3_ENGINE, "bm25_search"):
        try:
            docs_json = json.dumps(docs)
            raw = _PYO3_ENGINE.bm25_search(docs_json, query, top_k, float(k1), float(b))
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [tuple(r) for r in parsed]
        except Exception:
            pass

    # Tier 2: ctypes
    res = _call_rust_ffi("raise_bm25_search", {
        "docs": docs,
        "query": query,
        "top_k": top_k,
        "k1": k1,
        "b": b,
    })
    if res and "results" in res:
        return [tuple(r) for r in res["results"]]

    return None


def rank_candidates_rust(
    candidates: List[Dict[str, Any]],
    top_k: int = 100,
) -> Optional[List[Dict[str, Any]]]:
    """
    Filters and ranks candidates using O(N) QuickSelect in Rust.
    """
    _init_engines()

    # Tier 1: PyO3
    if _PYO3_ENGINE is not None and hasattr(_PYO3_ENGINE, "rank_candidates"):
        try:
            cand_json = json.dumps(candidates)
            raw = _PYO3_ENGINE.rank_candidates(cand_json, top_k)
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass

    # Tier 2: ctypes
    res = _call_rust_ffi("raise_rank_candidates", {
        "candidates": candidates,
        "top_k": top_k,
    })
    if res and "results" in res:
        return res["results"]

    return None


def normalize_text_rust(text: str) -> Optional[str]:
    """
    Runs high-speed Unicode and whitespace normalization and hyphen repair in Rust.
    """
    _init_engines()

    # Tier 1: PyO3
    if _PYO3_ENGINE is not None and hasattr(_PYO3_ENGINE, "clean_text"):
        try:
            return _PYO3_ENGINE.clean_text(text)
        except Exception:
            pass

    # Tier 2: ctypes
    res = _call_rust_ffi("raise_normalize_text", {
        "text": text,
    })
    if res and "cleaned_text" in res:
        return res["cleaned_text"]

    return None


def claim_fingerprint_rust(claim_text: str, doc_id: str, page: int) -> Optional[str]:
    """
    Computes deterministic SHA-256 fingerprint for claims in Rust.
    """
    _init_engines()

    if _PYO3_ENGINE is not None and hasattr(_PYO3_ENGINE, "claim_fingerprint"):
        try:
            return _PYO3_ENGINE.claim_fingerprint(claim_text, doc_id, page)
        except Exception:
            pass

    return None

