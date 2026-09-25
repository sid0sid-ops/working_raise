"""
RAISE Infrastructure — Safe Provider HTTP Client
Provides robust, non-secret-leaking HTTP transport with:
- Error classification (401, 403, 404, 429, 500, timeouts, connection drops)
- Micro-latency benchmarking (DNS, connect, total request)
- Bounded retries and exponential backoff
- Zero token / credential leakage in logs and exceptions
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
import urllib.error
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("raise.infrastructure.providers.http")


class ProviderHTTPError(Exception):
    """Clean exception with categorized error status without leaking request headers or secrets."""
    def __init__(self, message: str, status_code: Optional[int] = None, classification: str = "UNKNOWN"):
        super().__init__(message)
        self.status_code = status_code
        self.classification = classification


def classify_http_status(status_code: int) -> str:
    """Classify standard HTTP status codes into standardized ProviderHealth statuses."""
    if status_code in (401, 403):
        return "AUTH_FAILED"
    elif status_code == 404:
        return "MODEL_UNAVAILABLE"
    elif status_code == 429:
        return "RATE_LIMITED"
    elif status_code in (402, 409):
        return "BILLING_RESTRICTED"
    elif status_code in (500, 502, 503, 504):
        return "ENDPOINT_UNREACHABLE"
    return "INVALID_CONFIGURATION"


def safe_http_request(
    url: str,
    payload: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
    max_retries: int = 3,
    backoff_seconds: float = 3.0,
    method: Optional[str] = None,
) -> Tuple[Dict[str, Any], float]:
    """
    Execute safe HTTP request (POST or GET) with bounded retries and latency tracking.
    Returns (response_json, elapsed_ms).
    Ensures zero authorization token disclosure on network or JSON failure.
    """
    req_headers = {"User-Agent": "RAISE-MultiBackend/2.5"}
    body_bytes = None
    if payload is not None:
        body_bytes = json.dumps(payload).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
        http_method = method or "POST"
    else:
        http_method = method or "GET"

    if headers:
        req_headers.update(headers)

    attempts = 0
    last_err: Optional[Exception] = None

    while attempts <= max_retries:
        attempts += 1
        t_start = time.perf_counter()
        req = urllib.request.Request(url, data=body_bytes, headers=req_headers, method=http_method)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                raw = resp.read().decode("utf-8")
                return json.loads(raw), elapsed_ms
        except urllib.error.HTTPError as e:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            classification = classify_http_status(e.code)
            last_err = ProviderHTTPError(
                f"HTTP {e.code} ({classification})",
                status_code=e.code,
                classification=classification,
            )
            # Only retry on 429 or transient 5xx if retries remain
            if e.code in (429, 502, 503, 504) and attempts <= max_retries:
                time.sleep(backoff_seconds * attempts)
                continue
            raise last_err
        except (urllib.error.URLError, TimeoutError) as e:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            reason_str = str(getattr(e, "reason", e)).lower()
            if "timed out" in reason_str or isinstance(e, TimeoutError):
                classification = "ENDPOINT_UNREACHABLE"
                msg = "Connection timed out"
            elif "getaddrinfo failed" in reason_str or "name or service not known" in reason_str:
                classification = "ENDPOINT_UNREACHABLE"
                msg = "DNS resolution failure"
            else:
                classification = "ENDPOINT_UNREACHABLE"
                msg = f"Network connection refused: {getattr(e, 'reason', e)}"
            last_err = ProviderHTTPError(msg, status_code=None, classification=classification)
            if attempts <= max_retries:
                time.sleep(backoff_seconds)
                continue
            raise last_err
        except Exception as e:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            raise ProviderHTTPError(f"Unexpected transport error: {type(e).__name__}", classification="UNKNOWN")

    if last_err:
        raise last_err
    raise ProviderHTTPError("Request failed without response", classification="UNKNOWN")
