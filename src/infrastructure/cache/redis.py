from __future__ import annotations
import os
import json
import time
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from src.storage.interfaces import ISessionStore, ICacheStore

logger = logging.getLogger("raise.infrastructure.cache.redis")

class RedisCacheManager(ICacheStore):
    """
    Sub-millisecond query response cache using Redis.
    Accelerates repeated user questions across Fast and Expert modes.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: int = 0
    ):
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = int(port or os.getenv("REDIS_PORT", "6379"))
        self.db = db
        self.is_connected = False
        self._client = None
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._memory_session_msgs: Dict[str, List[Dict[str, Any]]] = {}
        self._memory_session_vars: Dict[str, Dict[str, str]] = {}
        
        self._connect()

    def _connect(self):
        try:
            import redis
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                socket_timeout=2
            )
            self._client.ping()
            self.is_connected = True
            logger.info(f"Connected to Redis at {self.host}:{self.port}/{self.db}")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory cache.")
            self.is_connected = False
            self._client = None

    def _make_completion_key(self, query: str, mode: str, library: Optional[str] = None, active_docs: Optional[List[str]] = None) -> str:
        q_norm = query.strip().lower()
        lib_tag = f":{library}" if library else ""
        doc_tag = f":{','.join(sorted(active_docs))}" if active_docs else ":empty"
        import hashlib
        q_hash = hashlib.sha256(f"{q_norm}{doc_tag}".encode("utf-8")).hexdigest()[:16]
        return f"cache:completion:{mode}{lib_tag}:{q_hash}"

    def _make_vector_key(self, vector_id: str) -> str:
        return f"cache:vector:{vector_id}"

    def _make_rate_key(self, ip_address: str) -> str:
        return f"rate:bucket:{ip_address}"

    def _make_job_key(self, job_id: str) -> str:
        return f"job:status:{job_id}"

    def _make_key(self, query: str, mode: str, library: Optional[str] = None, active_docs: Optional[List[str]] = None) -> str:
        # Default alias for completions matching system-architecture.md
        return self._make_completion_key(query, mode, library, active_docs=active_docs)

    def get(self, query: str, mode: str, library: Optional[str] = None, active_docs: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        return self.get_completion(query, mode, library, active_docs=active_docs)

    def get_completion(self, query: str, mode: str, library: Optional[str] = None, active_docs: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        key = self._make_completion_key(query, mode, library, active_docs=active_docs)
        if not self.is_connected or not self._client:
            item = self._memory_cache.get(key)
            if item and item.get("expires_at", 0) > time.time():
                return item.get("data")
            return None

        try:
            cached_val = self._client.get(key)
            if cached_val:
                return json.loads(cached_val.decode("utf-8"))
        except Exception as e:
            logger.error(f"Redis get error for {key}: {e}")
        return None

    def set(self, query: str, mode: str, result: Dict[str, Any], library: Optional[str] = None, active_docs: Optional[List[str]] = None, ttl: int = 86400) -> bool:
        return self.set_completion(query, mode, result, library, active_docs=active_docs, ttl=ttl)

    def set_completion(self, query: str, mode: str, result: Dict[str, Any], library: Optional[str] = None, active_docs: Optional[List[str]] = None, ttl: int = 86400) -> bool:
        key = self._make_completion_key(query, mode, library, active_docs=active_docs)
        if not self.is_connected or not self._client:
            self._memory_cache[key] = {
                "data": result,
                "expires_at": time.time() + ttl
            }
            return True

        try:
            payload = json.dumps(result)
            self._client.set(key, payload, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Redis set error for {key}: {e}")
            return False

    def semantic_get(
        self,
        query: str,
        mode: str,
        embedding: Optional[List[float]],
        threshold: float = 0.95,
        library: Optional[str] = None,
        active_docs: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached response by exact match first, then by embedding cosine similarity (> threshold).
        Returns matching cached payload or None.
        """
        # 1. Exact match check
        exact = self.get_completion(query, mode=mode, library=library, active_docs=active_docs)
        if exact:
            return exact

        if not embedding:
            return None

        candidates = []
        if self.is_connected and self._client:
            try:
                keys = self._client.smembers("cache:semantic:keys")
                if keys:
                    for k in list(keys)[-100:]:
                        k_str = k.decode("utf-8") if isinstance(k, bytes) else k
                        val = self._client.get(k_str)
                        if val:
                            try:
                                candidates.append(json.loads(val.decode("utf-8")))
                            except Exception:
                                pass
            except Exception as e:
                logger.debug(f"Redis semantic get lookup error: {e}")

        if not candidates and hasattr(self, "_memory_semantic_cache"):
            candidates = list(self._memory_semantic_cache.values())

        if not candidates:
            return None

        # Dot-product similarity across unit-normalized embeddings
        best_score = -1.0
        best_match = None

        def dot_product(v1, v2):
            return sum(a * b for a, b in zip(v1, v2))

        for cand in candidates:
            if cand.get("mode") != mode:
                continue
            cand_emb = cand.get("embedding")
            if not cand_emb or len(cand_emb) != len(embedding):
                continue
            sim = dot_product(embedding, cand_emb)
            if sim > best_score:
                best_score = sim
                best_match = cand

        if best_score >= threshold and best_match:
            logger.info(f"Redis Semantic Cache HIT (similarity: {best_score:.4f} >= {threshold}) for '{query[:40]}'")
            return best_match.get("data")

        return None

    def semantic_set(
        self,
        query: str,
        mode: str,
        result: Dict[str, Any],
        embedding: Optional[List[float]],
        library: Optional[str] = None,
        active_docs: Optional[List[str]] = None,
        ttl: int = 86400,
    ) -> bool:
        """
        Stores response in both exact key cache and semantic similarity candidate index.
        """
        # Exact match cache
        self.set_completion(query, mode, result, library=library, active_docs=active_docs, ttl=ttl)

        if not embedding:
            return True

        if not hasattr(self, "_memory_semantic_cache"):
            self._memory_semantic_cache = {}

        import hashlib
        q_hash = hashlib.sha256(f"{query.strip().lower()}:{mode}".encode("utf-8")).hexdigest()[:16]
        entry = {
            "query": query,
            "mode": mode,
            "embedding": embedding,
            "library": library,
            "active_docs": active_docs or [],
            "data": result,
            "created_at": time.time(),
        }

        # Memory fallback (bounded to 200 items)
        if len(self._memory_semantic_cache) > 200:
            oldest_k = next(iter(self._memory_semantic_cache))
            self._memory_semantic_cache.pop(oldest_k, None)
        self._memory_semantic_cache[q_hash] = entry

        if self.is_connected and self._client:
            try:
                sem_key = f"cache:semantic:{mode}:{q_hash}"
                self._client.set(sem_key, json.dumps(entry), ex=ttl)
                self._client.sadd("cache:semantic:keys", sem_key)
            except Exception as e:
                logger.debug(f"Redis semantic set error: {e}")

        return True

    def publish_abort(self, session_id: Optional[str], request_id: Optional[str] = None) -> bool:
        """
        Publishes chat cancellation signal across all worker processes via Redis Pub/Sub.
        """
        payload = json.dumps({"session_id": session_id, "request_id": request_id, "timestamp": time.time()})
        if self.is_connected and self._client:
            try:
                self._client.publish("channel:chat:abort", payload)
                return True
            except Exception as e:
                logger.debug(f"Redis publish abort error: {e}")
        return False

    def get_vector(self, vector_id: str) -> Optional[List[float]]:
        key = self._make_vector_key(vector_id)
        if not self.is_connected or not self._client:
            item = self._memory_cache.get(key)
            if item and item.get("expires_at", 0) > time.time():
                return item.get("data")
            return None
        try:
            val = self._client.get(key)
            if val:
                return json.loads(val.decode("utf-8"))
        except Exception as e:
            logger.error(f"Redis vector get error: {e}")
        return None

    def set_vector(self, vector_id: str, vector: List[float], ttl: int = 604800) -> bool:
        key = self._make_vector_key(vector_id)
        if not self.is_connected or not self._client:
            self._memory_cache[key] = {"data": vector, "expires_at": time.time() + ttl}
            return True
        try:
            self._client.set(key, json.dumps(vector), ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Redis vector set error: {e}")
            return False

    def check_rate_limit(self, ip_address: str, max_tokens: int = 60, refill_per_sec: float = 1.0) -> tuple[bool, int]:
        """
        Token Bucket rate-limiting algorithm per system-architecture.md Section 4.1.
        Returns (is_allowed, remaining_tokens).
        """
        key = self._make_rate_key(ip_address)
        now = time.time()

        if not self.is_connected or not self._client:
            # In-memory Token Bucket fallback
            bucket = self._memory_cache.get(key)
            if not bucket or not isinstance(bucket.get("data"), dict):
                bucket = {"data": {"tokens": max_tokens, "last_updated": now}, "expires_at": now + 3600}
                self._memory_cache[key] = bucket

            data = bucket["data"]
            elapsed = now - data.get("last_updated", now)
            tokens = min(max_tokens, data.get("tokens", max_tokens) + elapsed * refill_per_sec)
            data["last_updated"] = now

            if tokens >= 1.0:
                data["tokens"] = tokens - 1.0
                return True, int(data["tokens"])
            else:
                data["tokens"] = tokens
                return False, 0

        try:
            # Atomic evaluation via Redis hash
            pipe = self._client.pipeline()
            pipe.hgetall(key)
            results = pipe.execute()
            data = results[0] or {}

            last_updated = float(data.get(b"last_updated", now))
            tokens = float(data.get(b"tokens", max_tokens))

            elapsed = now - last_updated
            tokens = min(max_tokens, tokens + elapsed * refill_per_sec)

            if tokens >= 1.0:
                new_tokens = tokens - 1.0
                p2 = self._client.pipeline()
                p2.hset(key, mapping={"tokens": str(new_tokens), "last_updated": str(now)})
                p2.expire(key, 3600)
                p2.execute()
                return True, int(new_tokens)
            else:
                p2 = self._client.pipeline()
                p2.hset(key, mapping={"tokens": str(tokens), "last_updated": str(now)})
                p2.expire(key, 3600)
                p2.execute()
                return False, 0
        except Exception as e:
            logger.error(f"Rate limiting check error: {e}")
            return True, max_tokens

    def set_job_status(self, job_id: str, status_data: Dict[str, Any], ttl: int = 10800) -> bool:
        key = self._make_job_key(job_id)
        if not self.is_connected or not self._client:
            self._memory_cache[key] = {"data": status_data, "expires_at": time.time() + ttl}
            return True
        try:
            self._client.set(key, json.dumps(status_data), ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Redis set job status error: {e}")
            return False

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        key = self._make_job_key(job_id)
        if not self.is_connected or not self._client:
            item = self._memory_cache.get(key)
            if item and item.get("expires_at", 0) > time.time():
                return item.get("data")
            return None
        try:
            val = self._client.get(key)
            if val:
                return json.loads(val.decode("utf-8"))
        except Exception as e:
            logger.error(f"Redis get job status error: {e}")
        return None

    def clear(self) -> bool:
        self._memory_cache.clear()
        self._memory_session_msgs.clear()
        self._memory_session_vars.clear()
        if not self.is_connected or not self._client:
            return True
        try:
            self._client.flushdb()
            return True
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False

    def _make_session_messages_key(self, session_id: str) -> str:
        return f"session:{session_id}:messages"

    def _make_session_memory_key(self, session_id: str) -> str:
        return f"session:{session_id}:memory"

    def get_session_messages(self, session_id: str, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
        """
        Ultra-fast retrieval of active conversation turns from Redis bounded list.
        """
        key = self._make_session_messages_key(session_id)
        if not self.is_connected or not self._client:
            msgs = self._memory_session_msgs.get(session_id, [])
            return msgs[-limit:] if msgs else []

        try:
            raw_items = self._client.lrange(key, -limit, -1)
            if not raw_items:
                return []
            return [json.loads(item.decode("utf-8")) for item in raw_items]
        except Exception as e:
            logger.error(f"Redis get_session_messages error: {e}")
            return []

    def save_session_message(
        self,
        session_id: str,
        role: str,
        content: str,
        mode: str = "fast",
        sources: Optional[List[str]] = None,
        max_turns: int = 20,
        ttl: int = 86400
    ) -> bool:
        """
        Atomic push of turn into Redis session cache with bounded size (LTRIM) and 24h TTL.
        """
        msg_payload = {
            "role": role,
            "content": content,
            "mode": mode,
            "sources": sources or [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        key = self._make_session_messages_key(session_id)
        if not self.is_connected or not self._client:
            self._memory_session_msgs.setdefault(session_id, []).append(msg_payload)
            if len(self._memory_session_msgs[session_id]) > max_turns:
                self._memory_session_msgs[session_id] = self._memory_session_msgs[session_id][-max_turns:]
            return True

        try:
            pipe = self._client.pipeline()
            pipe.rpush(key, json.dumps(msg_payload))
            pipe.ltrim(key, -max_turns, -1)
            pipe.expire(key, ttl)
            pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Redis save_session_message error: {e}")
            return False

    def get_session_memory(self, session_id: str) -> Dict[str, str]:
        """
        Retrieve session entity facts (e.g. user_name, user_role) from Redis hash.
        """
        key = self._make_session_memory_key(session_id)
        if not self.is_connected or not self._client:
            return self._memory_session_vars.get(session_id, {})

        try:
            raw_vars = self._client.hgetall(key)
            if not raw_vars:
                return {}
            return {k.decode("utf-8"): v.decode("utf-8") for k, v in raw_vars.items()}
        except Exception as e:
            logger.error(f"Redis get_session_memory error: {e}")
            return {}

    def set_session_memory(self, session_id: str, key: str, value: Any, ttl: int = 86400) -> bool:
        """
        Store session entity facts (e.g. user_name) in Redis hash with 24h TTL.
        """
        redis_key = self._make_session_memory_key(session_id)
        val_str = str(value)
        if not self.is_connected or not self._client:
            self._memory_session_vars.setdefault(session_id, {})[key] = val_str
            return True

        try:
            pipe = self._client.pipeline()
            pipe.hset(redis_key, key, val_str)
            pipe.expire(redis_key, ttl)
            pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Redis set_session_memory error: {e}")
            return False

    def clear_session_messages(self, session_id: str) -> bool:
        """
        Purge session cache and entity memory from Redis.
        """
        self._memory_session_msgs.pop(session_id, None)
        self._memory_session_vars.pop(session_id, None)
        if not self.is_connected or not self._client:
            return True

        try:
            k1 = self._make_session_messages_key(session_id)
            k2 = self._make_session_memory_key(session_id)
            self._client.delete(k1, k2)
            return True
        except Exception as e:
            logger.error(f"Redis clear_session_messages error: {e}")
            return False


# -----------------------------------------------------------------------------
# 3. Asynchronous Database Configuration (SQLModel + asyncpg)
# Specified in system-architecture.md Section 5
# -----------------------------------------------------------------------------
try:
    from sqlmodel import SQLModel, Field, Relationship
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.orm import sessionmaker
    from sqlmodel.ext.asyncio.session import AsyncSession
    HAS_ASYNC_DB = True
except ImportError:
    HAS_ASYNC_DB = False
    SQLModel = object  # type: ignore

if HAS_ASYNC_DB:
    class SessionMetadata(SQLModel, table=True):
        """Stores user conversational session titles and configuration parameters."""
        __tablename__ = "session_metadata"

        id: str = Field(primary_key=True, index=True)
        title: str = Field(nullable=False)
        created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
        updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

        messages: List["MessageHistory"] = Relationship(back_populates="session")

    class MessageHistory(SQLModel, table=True):
        """Persists historical dialog sequences sequentially."""
        __tablename__ = "message_history"

        id: Optional[int] = Field(default=None, primary_key=True)
        session_id: str = Field(foreign_key="session_metadata.id", index=True)
        role: str = Field(nullable=False)  # 'user' or 'assistant'
        content: str = Field(nullable=False)
        timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

        session: Optional[SessionMetadata] = Relationship(back_populates="messages")


def get_async_engine(
    user: str = "raise_user",
    password: str = "raise_password",
    host: str = "localhost",
    port: int = 5432,
    dbname: str = "raise_db"
):
    """
    Creates an asynchronous engine using asyncpg per system-architecture.md Section 5.1.
    """
    if not HAS_ASYNC_DB:
        return None
    async_db_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"
    return create_async_engine(
        async_db_url,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )
