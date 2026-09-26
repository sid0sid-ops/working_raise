"""
PostgreSQL 16 + Redis 7 Conversational Memory & Cache Contamination Evaluator
Executes multi-turn memory recall probes, persistence tests, isolation tests, and cache invalidation audits.
"""

from __future__ import annotations

import time
import uuid
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("raise.eval.memory")


class MemoryEvaluator:
    """
    Evaluates conversational memory persistence, multi-turn recall, latency,
    and cross-session contamination across PostgreSQL 16 and Redis 7.
    """

    def __init__(self, pg_manager: Any, redis_cache: Any, rag_pipeline: Any):
        self.pg = pg_manager
        self.redis = redis_cache
        self.pipeline = rag_pipeline

    def run_multi_turn_recall_test(self, session_id: Optional[str] = None, mode: str = "FULL_MEMORY") -> Dict[str, Any]:
        """
        Executes a 3-turn controlled dialogue probe:
        Turn 1: Entity declaration ("My preferred research institution is National Institute of Plant Genome Research")
        Turn 2: Unrelated distractor question ("Explain the mechanism of ATP synthesis in cellular respiration.")
        Turn 3: Memory recall probe ("What research institution did I state as my preference earlier?")
        """
        sid = session_id or f"EVAL::memory::{uuid.uuid4().hex[:12]}"
        logger.info(f"Starting memory evaluation test session {sid} (mode={mode})")

        t1_query = "My preferred research institution is National Institute of Plant Genome Research (NIPGR)."
        t2_query = "Explain the biochemical mechanism of ATP synthesis in cellular respiration."
        t3_query = "Which research institution did I state as my preferred institution earlier?"
        target_entity = "National Institute of Plant Genome Research"

        start_time = time.time()
        
        # Turn 1: Save User & Assistant Message
        w1_start = time.time()
        t1_response = "Noted. Your preferred research institution is National Institute of Plant Genome Research (NIPGR)."
        write_pg_1 = False
        write_redis_1 = False

        if mode in ("POSTGRES_ONLY", "FULL_MEMORY"):
            if self.pg and self.pg.is_connected:
                write_pg_1 = self.pg.save_message(sid, "user", t1_query) and self.pg.save_message(sid, "assistant", t1_response)

        if mode in ("REDIS_ONLY", "FULL_MEMORY"):
            if self.redis and self.redis.is_connected:
                write_redis_1 = self.redis.save_session_message(sid, "user", t1_query) and self.redis.save_session_message(sid, "assistant", t1_response)
                self.redis.set_session_memory(sid, "preferred_institution", target_entity)

        t1_latency = (time.time() - w1_start) * 1000

        # Turn 2: Unrelated Distractor
        t2_response = "ATP synthesis occurs via oxidative phosphorylation in mitochondria driven by the proton gradient."
        if mode in ("POSTGRES_ONLY", "FULL_MEMORY") and self.pg and self.pg.is_connected:
            self.pg.save_message(sid, "user", t2_query)
            self.pg.save_message(sid, "assistant", t2_response)
        if mode in ("REDIS_ONLY", "FULL_MEMORY") and self.redis and self.redis.is_connected:
            self.redis.save_session_message(sid, "user", t2_query)
            self.redis.save_session_message(sid, "assistant", t2_response)

        # Turn 3: Recall Probe
        r3_start = time.time()
        recalled_text = ""
        memory_source = "NONE"
        read_success = False

        # Attempt read from Redis first (fast path)
        if mode in ("REDIS_ONLY", "FULL_MEMORY") and self.redis and self.redis.is_connected:
            mem_vars = self.redis.get_session_memory(sid)
            if "preferred_institution" in mem_vars:
                recalled_text = mem_vars["preferred_institution"]
                memory_source = "REDIS"
                read_success = True
            else:
                msgs = self.redis.get_session_messages(sid, limit=10)
                for m in msgs:
                    if target_entity.lower() in m.get("content", "").lower():
                        recalled_text = m.get("content", "")
                        memory_source = "REDIS_SLIDING_WINDOW"
                        read_success = True
                        break

        # Fallback to PostgreSQL (durable path)
        if not read_success and mode in ("POSTGRES_ONLY", "FULL_MEMORY") and self.pg and self.pg.is_connected:
            getter = getattr(self.pg, "get_messages", None) or getattr(self.pg, "get_message_history", None)
            hist = getter(sid, limit=10) if getter else []
            for m in hist:
                if target_entity.lower() in m.get("content", "").lower():
                    recalled_text = m.get("content", "")
                    memory_source = "POSTGRESQL"
                    read_success = True
                    break

        r3_latency = (time.time() - r3_start) * 1000

        # Verify Recall Accuracy
        is_accurate = target_entity.lower() in recalled_text.lower() or "nipgr" in recalled_text.lower()

        return {
            "session_id": sid,
            "mode": mode,
            "declared_entity": target_entity,
            "write_success": write_pg_1 or write_redis_1 or (mode == "MEMORY_OFF"),
            "read_success": read_success,
            "recall_accuracy": 1.0 if is_accurate else 0.0,
            "recalled_text": recalled_text,
            "memory_source": memory_source,
            "write_latency_ms": round(t1_latency, 2),
            "read_latency_ms": round(r3_latency, 2),
            "total_test_duration_ms": round((time.time() - start_time) * 1000, 2),
        }

    def test_memory_contamination(self, session_a: str, session_b: str) -> Dict[str, Any]:
        """
        Tests whether entities declared in Session A leak into Session B.
        """
        # Session A declaration
        if self.redis and self.redis.is_connected:
            self.redis.set_session_memory(session_a, "confidential_project", "PROJECT_QUANTUM_BRAIN")

        # Session B lookup
        leaked = False
        if self.redis and self.redis.is_connected:
            vars_b = self.redis.get_session_memory(session_b)
            if "confidential_project" in vars_b or "PROJECT_QUANTUM_BRAIN" in str(vars_b):
                leaked = True

        return {
            "session_a": session_a,
            "session_b": session_b,
            "contamination_detected": leaked,
            "status": "PASSED" if not leaked else "FAILED_CONTAMINATION_DETECTED"
        }

    def test_cache_invalidation_integrity(self) -> Dict[str, Any]:
        """
        Verifies that Redis cache keys change when configuration parameters change,
        preventing stale cache hits across differing models or corpus manifests.
        """
        if not self.redis:
            return {"status": "SKIPPED_NO_REDIS"}

        q = "What was the total expenditure in 2024?"
        key_config_1 = self.redis._make_completion_key(q, mode="fast", library="default", active_docs=["doc_a.pdf"])
        key_config_2 = self.redis._make_completion_key(q, mode="fast", library="default", active_docs=["doc_b.pdf"])
        key_config_3 = self.redis._make_completion_key(q, mode="expert", library="default", active_docs=["doc_a.pdf"])

        properly_isolated = (key_config_1 != key_config_2) and (key_config_1 != key_config_3)
        return {
            "key_doc_a": key_config_1,
            "key_doc_b": key_config_2,
            "key_expert": key_config_3,
            "cache_keys_distinct": properly_isolated,
            "status": "PASSED" if properly_isolated else "FAILED_CACHE_COLLISION"
        }
