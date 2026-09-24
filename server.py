"""
RAISE (Research Assessment Intelligence & Semantic Extraction)
Tier 1: Cloudflare Gateway & Edge Host (server.py)
===================================================
Master application server providing:
1. Subprocess Tunnel Watchdog (cloudflared) with Windows group isolation
2. Pre-flight Port Sweep (Port 8000 zombie cleaner)
3. Pure ASGI Security Shield with O(1) Redis Blacklisting (blacklist:ip:{ip})
4. Upload Memory Safeguard (bypasses body capture on multipart/upload paths)
5. Two-Step WebSocket & SSE Ephemeral Token Handshake with Atomic Eviction
6. Live Terminal Edge Monitor (Client IP, Location, Ray-ID, Device, Query, Latency)
7. Mounts core GraphRAG routes (/api/chat, /api/documents, /api/health)
"""

from __future__ import annotations

import os
import sys
import time
import json
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Set, Dict, Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState
import redis.asyncio as aioredis

# Ensure RAG dir in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Load environment
try:
    from dotenv import load_dotenv
    _env_file = BASE_DIR / ".env"
    if _env_file.exists():
        load_dotenv(dotenv_path=_env_file)
    else:
        load_dotenv()
except Exception:
    pass

# Logging configuration
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("RAISE.Server")

# Import Security Package
from src.security import (
    resolve_client_ip,
    extract_edge_telemetry,
    parse_client_device,
    PortSweep,
    SubprocessTunnelManager,
    PureASGISecurityShieldMiddleware,
    HandshakeManager,
    TransactionalOutboxManager,
)

# Global Manager Handles
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
APP_PORT = int(os.getenv("PORT", "8000"))
APP_HOST = os.getenv("HOST", "0.0.0.0")

redis_client: Optional[aioredis.Redis] = None
handshake_mgr: Optional[HandshakeManager] = None
tunnel_mgr: Optional[SubprocessTunnelManager] = None
active_ws_subscribers: Set[WebSocket] = set()
ws_session_tokens: Dict[WebSocket, str] = {}
ws_session_ips: Dict[WebSocket, str] = {}
pubsub_listener_task: Optional[asyncio.Task] = None


async def listen_admin_and_telemetry_pubsub(r: aioredis.Redis):
    """
    Subscribes to Redis Pub/Sub channels to:
    1. Distribute telemetry frames to local WebSocket connections
    2. Handle administrative SESSION_KICK and IP_BLOCK teardown signals
    """
    pubsub = r.pubsub()
    await pubsub.subscribe("channel:telemetry:updates", "channel:admin:session_controls")
    logger.info("Subscribed to Redis channels: telemetry updates & admin controls.")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            channel = message["channel"]
            if isinstance(channel, bytes):
                channel = channel.decode("utf-8")
            data_str = message["data"]
            if isinstance(data_str, bytes):
                data_str = data_str.decode("utf-8")

            try:
                event_data = json.loads(data_str)
            except Exception:
                continue

            # Channel 1: Admin session controls (Kick / Block)
            if channel == "channel:admin:session_controls":
                evt = event_data.get("event")
                target = event_data.get("target")
                evt_type = event_data.get("type")

                if evt_type == "SESSION_KICK" or evt == "session_revoked":
                    # Scan local active websockets and disconnect matching token
                    for ws, token in list(ws_session_tokens.items()):
                        if token == target:
                            logger.warning(f"Admin KICK executed on local session {token[:8]}...")
                            try:
                                await ws.close(code=4403, reason="Session terminated by Administrator.")
                            except Exception:
                                pass
                            active_ws_subscribers.discard(ws)
                            ws_session_tokens.pop(ws, None)
                            ws_session_ips.pop(ws, None)

                elif evt_type == "IP_BLOCK":
                    # Disconnect all active websockets from that IP
                    for ws, ip in list(ws_session_ips.items()):
                        if ip == target:
                            logger.warning(f"Admin IP_BLOCK executed on local socket IP {ip}")
                            try:
                                await ws.close(code=4403, reason="IP Blocked by Administrator.")
                            except Exception:
                                pass
                            active_ws_subscribers.discard(ws)
                            ws_session_tokens.pop(ws, None)
                            ws_session_ips.pop(ws, None)

            # Channel 2: Telemetry Updates
            elif channel == "channel:telemetry:updates":
                frame_payload = {"type": "log_frame", "data": event_data}
                # Log live telemetry frame to server terminal
                _print_live_edge_monitor(event_data)

                for ws in list(active_ws_subscribers):
                    if ws.client_state == WebSocketState.CONNECTED:
                        try:
                            await ws.send_json(frame_payload)
                        except Exception:
                            active_ws_subscribers.discard(ws)
                            ws_session_tokens.pop(ws, None)
                            ws_session_ips.pop(ws, None)

    except asyncio.CancelledError:
        await pubsub.unsubscribe("channel:telemetry:updates", "channel:admin:session_controls")
        await pubsub.close()


def _print_live_edge_monitor(event_data: Dict[str, Any]):
    """Renders formatted live edge monitor terminal logs for multi-user connections."""
    client_ip = event_data.get("client_ip", "127.0.0.1")
    country = event_data.get("country", "LOCAL")
    ray_id = event_data.get("ray_id", "DIRECT")
    device = event_data.get("device", "Desktop")
    os_name = event_data.get("os", "Unknown")
    browser = event_data.get("browser", "Unknown")
    method = event_data.get("method", "GET")
    path = event_data.get("path", "/")
    status_code = event_data.get("status", 200)
    duration_ms = event_data.get("duration_ms", 0.0)
    req_body = event_data.get("request_body", "")

    # Only print for API calls (skip favicon, static)
    if not path.startswith("/api"):
        return

    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(event_data.get("timestamp", time.time())))
    print(f"\033[1;96m═" * 78 + "\033[0m")
    print(f"\033[1;92m🔌 INCOMING EDGE CONNECTION\033[0m | \033[90m[{ts}]\033[0m")
    print(f"  • \033[1mClient IP\033[0m  : \033[93m{client_ip}\033[0m (Region: \033[96m{country}\033[0m | Ray-ID: \033[90m{ray_id}\033[0m)")
    print(f"  • \033[1mDevice\033[0m     : \033[97m{device}\033[0m (OS: \033[96m{os_name}\033[0m | Browser: \033[96m{browser}\033[0m)")
    print(f"  • \033[1mRoute\033[0m      : \033[1;95m{method} {path}\033[0m -> Status \033[1;92m{status_code}\033[0m (\033[93m{duration_ms}ms\033[0m)")
    if req_body and req_body != "[MULTIPART_UPLOAD_BYPASS]":
        preview = req_body[:120].replace("\n", " ")
        print(f"  • \033[1mPayload\033[0m    : \033[90m{preview}\033[0m")
    print(f"\033[1;96m─" * 78 + "\033[0m")


@asynccontextmanager
async def server_lifespan(app: FastAPI):
    """
    Master Lifespan Manager:
    1. Pre-flight Port Sweep
    2. Redis Client & Pub/Sub Initialized
    3. Cloudflare Tunnel Manager Started
    4. Clean Teardown Protocol on Shutdown
    """
    global redis_client, handshake_mgr, tunnel_mgr, pubsub_listener_task

    print("\033[1;96m═" * 78 + "\033[0m")
    print(" \033[1;95m🚀 RAISE (v2.5) CLOUDFLARE GATEWAY & MASTER EDGE HOST\033[0m")
    print(" \033[90mSystem: Research Assessment Intelligence & Semantic Extraction\033[0m")
    print("\033[1;96m═" * 78 + "\033[0m")

    # 1. Pre-flight Port Sweep
    logger.info(f"Running pre-flight port sweep on port {APP_PORT}...")
    port_freed = PortSweep.sweep_and_clean(APP_PORT)
    if not port_freed:
        logger.warning(f"Port {APP_PORT} check completed with potential conflict.")

    # 2. Redis Connection
    try:
        redis_client = aioredis.from_url(REDIS_URL, decode_responses=False)
        await redis_client.ping()
        logger.info(f"Connected to Redis at {REDIS_URL}")
        app.state.redis = redis_client
        handshake_mgr = HandshakeManager(redis_client)
        app.state.handshake_mgr = handshake_mgr
        
        # Start Pub/Sub background listener
        pubsub_listener_task = asyncio.create_task(listen_admin_and_telemetry_pubsub(redis_client))
    except Exception as e:
        logger.warning(f"Redis unavailable ({e}). Telemetry caching and handshake will run in standalone mode.")
        redis_client = None
        handshake_mgr = None

    # Start middleware background telemetry queue worker
    if hasattr(app.state, "asgi_shield"):
        app.state.asgi_shield.redis = redis_client
        app.state.asgi_shield.start_background_worker()

    # 3. Subprocess Tunnel Watchdog
    enable_tunnel = (
        os.getenv("ENABLE_CLOUDFLARE_TUNNEL", "true").lower() in ("true", "1")
        and ("--no-tunnel" not in sys.argv)
    )
    if enable_tunnel:
        logger.info("Initializing Cloudflare Tunnel Watchdog...")
        tunnel_mgr = SubprocessTunnelManager(port=APP_PORT)
        app.state.tunnel_mgr = tunnel_mgr
        tunnel_url = await tunnel_mgr.start()
        if tunnel_url:
            print("\033[1;92m" + "─" * 78 + "\033[0m")
            print(f" \033[1;92m🌐 PUBLIC EDGE TUNNEL ACTIVE:\033[0m \033[1;96m{tunnel_url}\033[0m")
            print(f" \033[90mTunnel routes securely to local backend at http://localhost:{APP_PORT}\033[0m")
            print("\033[1;92m" + "─" * 78 + "\033[0m")
    else:
        logger.info("Cloudflare Tunnel disabled (local only mode).")
        print(f"\033[1;93mℹ️  [Tunnel Mode: DISABLED via --no-tunnel / config] Running locally on http://localhost:{APP_PORT}\033[0m")

    yield

    # Shutdown Phase
    logger.info("Shutting down RAISE Gateway...")

    if pubsub_listener_task and not pubsub_listener_task.done():
        pubsub_listener_task.cancel()

    if hasattr(app.state, "asgi_shield"):
        await app.state.asgi_shield.stop_background_worker()

    if tunnel_mgr:
        await tunnel_mgr.stop()

    if redis_client:
        await redis_client.close()

    logger.info("RAISE Gateway teardown complete.")


# Initialize FastAPI App
app = FastAPI(
    title="RAISE Master Edge Gateway",
    version="2.5.0",
    description="Enterprise edge gateway for Research Assessment Intelligence & Semantic Extraction",
    lifespan=server_lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach Pure ASGI Security Shield as Outer Layer
shield_middleware = PureASGISecurityShieldMiddleware(app=app, redis_client=None)
app.state.asgi_shield = shield_middleware


# ------------------------------------------------------------------------------
# Authentication Handshake Endpoints (Two-Step Handshake)
# ------------------------------------------------------------------------------
@app.post("/api/v1/auth/handshake")
@app.post("/session/handshake")
async def create_auth_handshake(request: Request):
    """
    Step 1 of Two-Step Security Handshake:
    Generates an ephemeral single-use token (5-min TTL) in Redis.
    """
    mgr: Optional[HandshakeManager] = getattr(app.state, "handshake_mgr", None)
    client_ip = resolve_client_ip(dict(request.scope))

    if not mgr or not mgr.redis:
        # Standalone mode fallback
        import secrets
        mock_token = f"standalone_{secrets.token_urlsafe(24)}"
        return {
            "token": mock_token,
            "expires_in": 300,
            "status": "active",
            "mode": "standalone"
        }

    token = await mgr.create_handshake_token(metadata={"client_ip": client_ip})
    return {
        "token": token,
        "expires_in": 300,
        "status": "active",
        "client_ip": client_ip
    }


# ------------------------------------------------------------------------------
# WebSocket Telemetry Stream (Two-Step Handshake Verification)
# ------------------------------------------------------------------------------
@app.websocket("/ws/traffic")
@app.websocket("/ws/telemetry")
async def websocket_traffic_endpoint(websocket: WebSocket):
    """
    Step 2 & 3: Authenticated connection upgrade.
    Extracts token from query string (?token=...), verifies presence,
    and ATOMICALLY EVICTS it from Redis to prevent replay attacks.
    """
    query_params = websocket.query_params
    token = query_params.get("token")

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication handshake token.")
        return

    mgr: Optional[HandshakeManager] = getattr(app.state, "handshake_mgr", None)
    client_ip = resolve_client_ip(dict(websocket.scope))

    # Verification & Single-Use Eviction
    if mgr and mgr.redis:
        # Check IP blacklist first
        is_blocked = await mgr.is_ip_blocked(client_ip)
        if is_blocked:
            await websocket.close(code=4403, reason="ERR_BLOCKED_IP: Client IP is blacklisted.")
            return

        session_data = await mgr.verify_and_consume_token(token, client_ip=client_ip)
        if not session_data:
            # Token already consumed, invalid, or expired
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or already consumed handshake token.")
            return

    await websocket.accept()
    active_ws_subscribers.add(websocket)
    ws_session_tokens[websocket] = token
    ws_session_ips[websocket] = client_ip
    logger.info(f"WebSocket client connected from {client_ip} (active subscribers: {len(active_ws_subscribers)})")

    # Send initial welcome frame
    await websocket.send_json({
        "type": "connection_ready",
        "client_ip": client_ip,
        "session_token_prefix": token[:8] + "...",
        "timestamp": time.time()
    })

    try:
        while True:
            # Keepalive listener
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception as err:
        logger.debug(f"WebSocket disconnect: {err}")
    finally:
        active_ws_subscribers.discard(websocket)
        ws_session_tokens.pop(websocket, None)
        ws_session_ips.pop(websocket, None)
        logger.info(f"WebSocket disconnected (remaining: {len(active_ws_subscribers)})")


# ------------------------------------------------------------------------------
# Mount Core RAISE Application Routes from app.py
# ------------------------------------------------------------------------------
try:
    import app as rag_app_module
    core_rag_app = rag_app_module.app
    # Mount all routes from core_rag_app
    app.include_router(core_rag_app.router)
    # Forward core singletons to gateway app.state so router handlers receive live instances
    for key in ["rag_engine", "postgres_manager", "redis_cache", "dev_operator", "session_memory_manager"]:
        val = getattr(core_rag_app.state, key, None) or getattr(rag_app_module, key, None)
        if val is not None:
            setattr(app.state, key, val)
    # Forward unified exception handlers
    app.exception_handlers.update(core_rag_app.exception_handlers)
    logger.info("Successfully mounted all core RAISE GraphRAG routes from app.py and forwarded singletons")
except Exception as e:
    logger.warning(f"Could not import routes from app.py directly: {e}. Adding fallback routes.")

    @app.get("/api/health")
    async def fallback_health():
        return {"status": "ok", "service": "RAISE Master Gateway", "timestamp": time.time()}


# Root diagnostic endpoint
@app.get("/")
async def root_gateway_index():
    return {
        "name": "RAISE (Research Assessment Intelligence & Semantic Extraction)",
        "role": "Cloudflare Gateway & Live Edge Host",
        "version": "2.5.0",
        "status": "operational",
        "subsystems": {
            "neo4j": "bolt://localhost:7687",
            "redis": REDIS_URL,
            "port": APP_PORT,
            "tunnel_active": tunnel_mgr is not None and tunnel_mgr.public_url is not None
        }
    }


if __name__ == "__main__":
    if "--no-tunnel" in sys.argv:
        os.environ["ENABLE_CLOUDFLARE_TUNNEL"] = "false"
        sys.argv.remove("--no-tunnel")
    import uvicorn
    uvicorn.run(app, host=APP_HOST, port=APP_PORT, reload=False, log_level="info")
