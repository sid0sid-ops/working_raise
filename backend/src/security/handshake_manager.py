"""
RAISE (Research Assessment Intelligence & Semantic Extraction)
Security Subsystem — Two-Step Ephemeral Handshake & Session Revocation
Generates single-use short-lived tokens in Redis with atomic eviction,
and registers active 24-hour sessions with client metadata.
"""

import time
import secrets
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("RAISE.HandshakeManager")

TOKEN_TTL_SECONDS = 300       # 5 minutes for handshake token
SESSION_TTL_SECONDS = 86400   # 24 hours for active session


class HandshakeManager:
    """Manages ephemeral handshake tokens and active session lifecycles in Redis."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def create_handshake_token(self, metadata: Optional[Dict[str, str]] = None) -> str:
        """
        Generates a 32-byte cryptographic token with a 5-minute TTL.
        """
        token = secrets.token_urlsafe(32)
        payload = metadata or {}
        payload["created_at"] = str(time.time())
        key = f"handshake:token:{token}"

        await self.redis.hset(key, mapping=payload)
        await self.redis.expire(key, TOKEN_TTL_SECONDS)
        return token

    async def verify_and_consume_token(self, token: str, client_ip: str = "127.0.0.1") -> Optional[Dict[str, str]]:
        """
        Atomically checks and consumes the ephemeral token (Single-Use Guarantee).
        If valid, registers an active 24-hour session in Redis.
        Returns the token metadata if valid, or None if invalid/expired/replayed.
        """
        if not token:
            return None

        key = f"handshake:token:{token}"

        # Atomic transaction: read metadata and delete token immediately
        pipe = self.redis.pipeline()
        pipe.hgetall(key)
        pipe.delete(key)
        results = await pipe.execute()

        meta = results[0]
        if not meta:
            return None

        # Convert bytes keys/values to str if needed
        clean_meta = {
            (k.decode("utf-8") if isinstance(k, bytes) else str(k)):
            (v.decode("utf-8") if isinstance(v, bytes) else str(v))
            for k, v in meta.items()
        }

        # Register active session
        session_id = token
        session_key = f"active_session:{session_id}"
        session_data = {
            "ip": client_ip,
            "connected_at": str(time.time()),
            **clean_meta
        }
        await self.redis.hset(session_key, mapping=session_data)
        await self.redis.expire(session_key, SESSION_TTL_SECONDS)

        return session_data

    async def revoke_session(self, session_id: str) -> bool:
        """Revokes an active session from Redis."""
        key = f"active_session:{session_id}"
        deleted = await self.redis.delete(key)
        return deleted > 0

    async def block_ip(self, ip_address: str, reason: str = "Administrative block") -> bool:
        """Sets an IP in the permanent blacklist."""
        key = f"blacklist:ip:{ip_address}"
        await self.redis.set(key, reason)
        return True

    async def unblock_ip(self, ip_address: str) -> bool:
        """Removes an IP from the blacklist."""
        key = f"blacklist:ip:{ip_address}"
        deleted = await self.redis.delete(key)
        return deleted > 0

    async def is_ip_blocked(self, ip_address: str) -> bool:
        """Checks if an IP is in the blacklist."""
        key = f"blacklist:ip:{ip_address}"
        return bool(await self.redis.exists(key))
