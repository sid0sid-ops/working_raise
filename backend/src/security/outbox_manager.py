"""
RAISE (Research Assessment Intelligence & Semantic Extraction)
Security Subsystem — Decoupled Transactional Outbox Manager
Decouples short relational DB transactions from high-latency external model inference.
Prevents PostgreSQL connection pool exhaustion.
"""

import time
import logging
from typing import Optional, Dict, Any, Callable, Awaitable

logger = logging.getLogger("RAISE.OutboxManager")


class TransactionalOutboxManager:
    """
    Ensures relational database operations complete and release connections (<5ms)
    prior to invoking slow inference (vLLM takes 1.5s - 15s).
    """

    def __init__(self, db_engine: Optional[Any] = None):
        self.db_engine = db_engine

    async def execute_decoupled_inference(
        self,
        record_pre_inference_tx: Callable[[], Awaitable[Any]],
        run_inference: Callable[[], Awaitable[Any]],
        record_post_inference_tx: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        """
        Executes the three-phase decoupled inference lifecycle:
        Phase 1: Fast database write / state lock (<5ms) -> Commit & Release connection socket.
        Phase 2: High-latency inference (1.5s - 15s) -> DB connection is NOT held.
        Phase 3: Fast database commit of final answers and citations (<5ms) -> Release connection.
        """
        # Phase 1: Pre-inference fast transaction
        t0 = time.perf_counter()
        pre_state = await record_pre_inference_tx()
        t_pre = (time.perf_counter() - t0) * 1000.0
        logger.debug(f"Pre-inference DB write committed in {t_pre:.2f}ms. Socket released.")

        # Phase 2: Inference outside any DB transaction scope
        inference_result = await run_inference()

        # Phase 3: Post-inference fast transaction
        t1 = time.perf_counter()
        final_state = await record_post_inference_tx(inference_result)
        t_post = (time.perf_counter() - t1) * 1000.0
        logger.debug(f"Post-inference DB write committed in {t_post:.2f}ms. Socket released.")

        return inference_result
