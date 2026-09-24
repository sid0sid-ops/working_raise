"""
RAISE (Research Assessment Intelligence & Semantic Extraction)
Security Subsystem — User-Agent Device, OS, and Browser Parser
Zero-dependency, high-speed token scanner for incoming client telemetry.
"""

from typing import Dict


def parse_client_device(user_agent_str: str) -> Dict[str, str]:
    """
    Parses a raw User-Agent string into device category, OS name, and browser.
    """
    if not user_agent_str:
        return {"device": "Unknown Device", "os": "Unknown OS", "browser": "Unknown Browser"}

    ua = user_agent_str.lower()
    device = "Desktop"
    os_name = "Unknown OS"
    browser = "Unknown Browser"

    # OS & Device Identification (Mobile/Tablet prioritized before desktop macOS)
    if "ipad" in ua:
        os_name = "iOS"
        device = "Tablet"
    elif "iphone" in ua:
        os_name = "iOS"
        device = "Mobile"
    elif "android" in ua:
        os_name = "Android"
        device = "Tablet" if "tablet" in ua else "Mobile"
    elif "windows" in ua:
        os_name = "Windows"
        device = "Desktop"
    elif "macintosh" in ua or "mac os" in ua:
        os_name = "macOS"
        device = "Desktop"
    elif "linux" in ua:
        os_name = "Linux"
        device = "Desktop"

    # Secondary hints
    if "tablet" in ua:
        device = "Tablet"
    elif "mobile" in ua and device == "Desktop":
        device = "Mobile"

    # Browser Identification (order matters due to user agent token cascades)
    if "edg" in ua or "edge" in ua:
        browser = "Edge"
    elif "chrome" in ua and "safari" in ua and "opr" not in ua and "edg" not in ua:
        browser = "Chrome"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "opr" in ua or "opera" in ua:
        browser = "Opera"
    elif "curl" in ua:
        browser = "cURL"
    elif "python" in ua or "httpx" in ua or "requests" in ua:
        browser = "Python Client"

    return {
        "device": device,
        "os": os_name,
        "browser": browser
    }
