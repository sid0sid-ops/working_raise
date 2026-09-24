"""
RAISE (Research Assessment Intelligence & Semantic Extraction)
Security Subsystem — Real Client IP & Edge Header Resolver
Resolves real client WAN IPs and Cloudflare telemetry headers with defensive precedence.
"""

from typing import Dict, Any, Optional


def resolve_client_ip(scope: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> str:
    """
    Defensively extracts the real client IP address.
    Precedence:
    1. 'cf-connecting-ip' (Cloudflare Edge Verified WAN IP)
    2. 'x-forwarded-for' (First leftmost untrusted/trusted client IP)
    3. 'x-real-ip' (Standard reverse proxy IP)
    4. scope['client'][0] (Raw socket connection endpoint)
    Fallback: '127.0.0.1'
    """
    if headers is None:
        raw_headers = scope.get("headers", [])
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in raw_headers}

    # 1. Cloudflare WAN header
    cf_ip = headers.get("cf-connecting-ip")
    if cf_ip and cf_ip.strip():
        return cf_ip.strip()

    # 2. X-Forwarded-For (leftmost element)
    xff = headers.get("x-forwarded-for")
    if xff and xff.strip():
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[0]

    # 3. X-Real-IP
    x_real = headers.get("x-real-ip")
    if x_real and x_real.strip():
        return x_real.strip()

    # 4. Raw ASGI socket client tuple: (host, port)
    client = scope.get("client")
    if client and isinstance(client, (list, tuple)) and len(client) > 0 and client[0]:
        return str(client[0]).strip()

    return "127.0.0.1"


def extract_edge_telemetry(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Extracts Cloudflare edge telemetry headers for tracking and session identification.
    """
    return {
        "country": headers.get("cf-ipcountry", "LOCAL").strip().upper() or "LOCAL",
        "ray_id": headers.get("cf-ray", "LOCAL_DIRECT").strip() or "LOCAL_DIRECT",
        "platform_hint": headers.get("sec-ch-ua-platform", "").strip().replace('"', ""),
    }
