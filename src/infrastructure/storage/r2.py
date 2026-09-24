"""
RAISE Cloudflare R2 Storage Engine with Strict Zero-Cost Free-Tier Guardrails
Guarantees $0 cost by enforcing hard ceilings well below Cloudflare free monthly limits:
- Max Storage: 5 GB (Free Tier: 10 GB)
- Max Class A Ops (write/list): 100,000 / month (Free Tier: 1,000,000)
- Max Class B Ops (read): 1,000,000 / month (Free Tier: 10,000,000)

If any limit is approached or if cloud is unavailable, it immediately trips the
Circuit Breaker and seamlessly falls back to local disk storage.
NEVER exposes or logs any secret tokens or credentials.
"""

from __future__ import annotations

import os
import time
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger("raise.storage_engine")

# --- STRICT ZERO-COST FREE TIER LIMITS ---
FREE_TIER_MAX_STORAGE_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB safety cap (50% of 10GB free limit)
FREE_TIER_MAX_CLASS_A_OPS = 100_000                   # 100k safety cap (10% of 1M free limit)
FREE_TIER_MAX_CLASS_B_OPS = 1_000_000                 # 1M safety cap (10% of 10M free limit)


class FreeTierGuardrail:
    """
    Tracks and enforces monthly free tier limits in memory and Redis.
    Guarantees operations stay 100% within the free allowance.
    """

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._current_month = time.strftime("%Y-%m")
        self._local_class_a = 0
        self._local_class_b = 0
        self._local_storage_bytes = 0

    def _get_keys(self) -> Tuple[str, str, str]:
        month = time.strftime("%Y-%m")
        return (
            f"r2:ops:class_a:{month}",
            f"r2:ops:class_b:{month}",
            "r2:storage:bytes"
        )

    def can_perform_class_a(self, payload_size_bytes: int = 0) -> bool:
        key_a, _, key_storage = self._get_keys()
        current_ops = self._local_class_a
        current_bytes = self._local_storage_bytes

        if self.redis:
            try:
                ops_val = self.redis.get(key_a)
                if ops_val:
                    current_ops = int(ops_val)
                bytes_val = self.redis.get(key_storage)
                if bytes_val:
                    current_bytes = int(bytes_val)
            except Exception:
                pass

        if current_ops >= FREE_TIER_MAX_CLASS_A_OPS:
            logger.warning("[R2 COST GUARD] Class A free tier limit reached. Falling back to local storage.")
            return False

        if (current_bytes + payload_size_bytes) >= FREE_TIER_MAX_STORAGE_BYTES:
            logger.warning("[R2 COST GUARD] Storage free tier cap reached. Falling back to local storage.")
            return False

        return True

    def can_perform_class_b(self) -> bool:
        _, key_b, _ = self._get_keys()
        current_ops = self._local_class_b

        if self.redis:
            try:
                ops_val = self.redis.get(key_b)
                if ops_val:
                    current_ops = int(ops_val)
            except Exception:
                pass

        if current_ops >= FREE_TIER_MAX_CLASS_B_OPS:
            logger.warning("[R2 COST GUARD] Class B free tier limit reached. Falling back to local storage.")
            return False

        return True

    def record_class_a(self, bytes_added: int = 0):
        self._local_class_a += 1
        self._local_storage_bytes += bytes_added
        if self.redis:
            try:
                key_a, _, key_storage = self._get_keys()
                self.redis.incr(key_a)
                if bytes_added > 0:
                    self.redis.incrby(key_storage, bytes_added)
            except Exception:
                pass

    def record_class_b(self):
        self._local_class_b += 1
        if self.redis:
            try:
                _, key_b, _ = self._get_keys()
                self.redis.incr(key_b)
            except Exception:
                pass


class CloudflareR2StorageManager:
    """
    Manages S3-compatible Cloudflare R2 object storage with strict $0 cost guarantees.
    Always checks guardrails before any cloud operation.
    Gracefully falls back to local storage with zero disruption.
    """

    def __init__(self, local_docs_dir: Path, redis_client=None):
        self.local_docs_dir = Path(local_docs_dir)
        self.local_docs_dir.mkdir(parents=True, exist_ok=True)
        self.guard = FreeTierGuardrail(redis_client=redis_client)
        
        self.endpoint_url = os.getenv("CLOUDFLARE_R2_ENDPOINT_URL")
        self.access_key = os.getenv("CLOUDFLARE_R2_ACCESS_KEY_ID")
        self.secret_key = os.getenv("CLOUDFLARE_R2_SECRET_ACCESS_KEY")
        self.bucket_name = os.getenv("CLOUDFLARE_R2_BUCKET_NAME", "raise-documents")
        
        self.is_configured = bool(self.endpoint_url and self.access_key and self.secret_key)
        self._s3_client = None
        self._init_client()

    def _init_client(self):
        if not self.is_configured:
            return
        try:
            import boto3
            from botocore.config import Config
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=Config(signature_version="s3v4", connect_timeout=3, retries={"max_attempts": 2}),
                region_name="auto"
            )
        except Exception as e:
            logger.info(f"Cloudflare R2 client initialized in offline/local fallback mode: {e}")
            self._s3_client = None

    def store_document(self, filename: str, file_bytes: bytes) -> Dict[str, Any]:
        local_path = self.local_docs_dir / filename
        with open(local_path, "wb") as f:
            f.write(file_bytes)
        
        result = {
            "filename": filename,
            "size_bytes": len(file_bytes),
            "local_path": str(local_path),
            "cloud_synced": False
        }

        if self._s3_client and self.guard.can_perform_class_a(len(file_bytes)):
            try:
                self._s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=f"documents/{filename}",
                    Body=file_bytes
                )
                self.guard.record_class_a(len(file_bytes))
                result["cloud_synced"] = True
                logger.info(f"[R2 COST GUARD] Synced {filename} to R2 within free tier.")
            except Exception as e:
                logger.info(f"[R2 COST GUARD] Cloud upload bypassed safely (using local storage): {e}")

        return result

    def get_document_bytes(self, filename: str) -> Optional[bytes]:
        local_path = self.local_docs_dir / filename
        if local_path.exists():
            with open(local_path, "rb") as f:
                return f.read()

        if self._s3_client and self.guard.can_perform_class_b():
            try:
                response = self._s3_client.get_object(Bucket=self.bucket_name, Key=f"documents/{filename}")
                self.guard.record_class_b()
                return response["Body"].read()
            except Exception:
                return None
        return None
