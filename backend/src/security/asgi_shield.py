"""
RAISE (Research Assessment Intelligence & Semantic Extraction)
Security Subsystem — Pure ASGI Security Shield Middleware
Interception layer with:
- Sub-microsecond O(1) Redis IP blacklist checks (blacklist:ip:{client_ip})
- Immediate 403 (HTTP) / 4403 (WebSocket) rejection
- Large payload memory safeguard: bypasses body capture on multipart/upload paths
- Capped 4KB text payload buffer with truncation indicator
- Non-blocking telemetry queue dispatch (asyncio.Queue maxsize=1000)
"""

import time
import json
import asyncio
import logging
from typing import Dict, Any, Callable, Awaitable, Optional

from .ip_resolver import resolve_client_ip, extract_edge_telemetry
from .device_parser import parse_client_device

logger = logging.getLogger("RAISE.ASGIShield")

Scope = Dict[str, Any]
Receive = Callable[[], Awaitable[Dict[str, Any]]]
Send = Callable[[Dict[str, Any]], Awaitable[None]]

MAX_CAPTURE_BYTES = 4096  # 4 KB payload capture limit


class PureASGISecurityShieldMiddleware:
    """
    Pure ASGI middleware without BaseHTTPMiddleware task-spawning overhead.
    Provides sub-microsecond IP blacklisting, upload body bypass, and telemetry capture.
    """

    def __init__(self, app: Any, redis_client: Optional[Any] = None):
        self.app = app
        self.redis = redis_client
        self.telemetry_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._worker_task: Optional[asyncio.Task] = None

    def start_background_worker(self) -> None:
        """Starts background worker draining telemetry queue and broadcasting to Redis."""
        if not self._worker_task or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._telemetry_worker())

    async def stop_background_worker(self) -> None:
        """Cancels and joins the background telemetry worker."""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def _telemetry_worker(self) -> None:
        """Drains frames and publishes to Redis Pub/Sub channel:telemetry:updates."""
        while True:
            try:
                frame = await self.telemetry_queue.get()
                if self.redis:
                    try:
                        await self.redis.publish("channel:telemetry:updates", json.dumps(frame))
                    except Exception:
                        pass
                self.telemetry_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Telemetry queue worker error: {e}")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope_type = scope.get("type")
        if scope_type not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers_dict = {
            k.decode("latin-1").lower(): v.decode("latin-1")
            for k, v in scope.get("headers", [])
        }

        # 1. Resolve real client IP and edge headers
        client_ip = resolve_client_ip(scope, headers_dict)
        edge_meta = extract_edge_telemetry(headers_dict)
        device_meta = parse_client_device(headers_dict.get("user-agent", ""))

        # Store resolved client details on scope for downstream handlers
        scope["state"] = scope.get("state", {})
        scope["state"]["client_ip"] = client_ip
        scope["state"]["edge_meta"] = edge_meta
        scope["state"]["device_meta"] = device_meta

        # 2. O(1) Redis Blacklist Check
        if self.redis:
            try:
                is_blacklisted = await self.redis.exists(f"blacklist:ip:{client_ip}")
                if is_blacklisted:
                    if scope_type == "http":
                        await self._reject_http(send, 403, "ERR_BLOCKED_IP: Your IP has been blocked by administrator.")
                    else:
                        await self._reject_websocket(send, 4403, "Session terminated by Administrator.")
                    return
            except Exception as err:
                logger.debug(f"Redis blacklist check skipped: {err}")

        # Bypass telemetry interception on static or WebSocket routes
        path = scope.get("path", "")
        if path.startswith("/ws") or path.startswith("/static") or scope_type == "websocket":
            await self.app(scope, receive, send)
            return

        # 3. Request Body Buffering with Large Upload Bypass Safeguard
        content_type = headers_dict.get("content-type", "").lower()
        is_upload = (
            "multipart/form-data" in content_type
            or path.endswith("/upload")
            or path.startswith("/api/documents/upload")
        )

        req_body_chunks = []
        captured_bytes = [0]

        async def intercepted_receive() -> Dict[str, Any]:
            message = await receive()
            if not is_upload and message.get("type") == "http.request":
                chunk = message.get("body", b"")
                if chunk and captured_bytes[0] < MAX_CAPTURE_BYTES:
                    remaining = MAX_CAPTURE_BYTES - captured_bytes[0]
                    slice_chunk = chunk[:remaining]
                    req_body_chunks.append(slice_chunk)
                    captured_bytes[0] += len(slice_chunk)
            return message

        resp_status = [200]
        resp_body_chunks = []
        resp_captured_bytes = [0]

        async def intercepted_send(message: Dict[str, Any]) -> None:
            if message.get("type") == "http.response.start":
                resp_status[0] = message.get("status", 200)
            elif message.get("type") == "http.response.body":
                chunk = message.get("body", b"")
                if chunk and resp_captured_bytes[0] < MAX_CAPTURE_BYTES:
                    remaining = MAX_CAPTURE_BYTES - resp_captured_bytes[0]
                    slice_chunk = chunk[:remaining]
                    resp_body_chunks.append(slice_chunk)
                    resp_captured_bytes[0] += len(slice_chunk)
            await send(message)

        start_time = time.perf_counter()
        try:
            await self.app(scope, intercepted_receive, intercepted_send)
        finally:
            duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            req_text = (
                "[MULTIPART_UPLOAD_BYPASS]"
                if is_upload
                else b"".join(req_body_chunks).decode("utf-8", errors="replace")
            )
            if captured_bytes[0] >= MAX_CAPTURE_BYTES:
                req_text += " [truncated at 4KB]"

            resp_text = b"".join(resp_body_chunks).decode("utf-8", errors="replace")
            if resp_captured_bytes[0] >= MAX_CAPTURE_BYTES:
                resp_text += " [truncated at 4KB]"

            frame = {
                "timestamp": time.time(),
                "client_ip": client_ip,
                "country": edge_meta["country"],
                "ray_id": edge_meta["ray_id"],
                "device": device_meta["device"],
                "os": device_meta["os"],
                "browser": device_meta["browser"],
                "method": scope.get("method", "GET"),
                "path": path,
                "status": resp_status[0],
                "duration_ms": duration_ms,
                "request_body": req_text,
                "response_body": resp_text,
            }

            try:
                self.telemetry_queue.put_nowait(frame)
            except asyncio.QueueFull:
                pass  # Non-blocking drop under backpressure to protect memory boundary

    @staticmethod
    async def _reject_http(send: Send, status_code: int, detail: str) -> None:
        body = json.dumps({"error": detail, "code": status_code}).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("latin-1")),
            ]
        })
        await send({
            "type": "http.response.body",
            "body": body,
            "more_body": False
        })

    @staticmethod
    async def _reject_websocket(send: Send, code: int, reason: str) -> None:
        await send({
            "type": "websocket.close",
            "code": code,
            "reason": reason
        })
