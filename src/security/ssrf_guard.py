"""
ssrf_guard — Validate outbound URLs to block server-side request forgery.

Pattern (openfang web_fetch SSRF protection): an LLM-driven fetch tool
that doesn't validate URLs is a hole. Cloud-metadata endpoints, loopback,
private/link-local ranges → all forbidden by default.

Opt-out for trusted callers (e.g. internal Ollama probe):
    is_safe_url("http://localhost:11434", allow_loopback=True)

Use:
    from src.security.ssrf_guard import ensure_safe_url, SSRFBlocked
    try:
        ensure_safe_url(user_supplied_url)
    except SSRFBlocked as e:
        return {"error": str(e), "denied_by": "ssrf_guard"}
"""
from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Iterable, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class SSRFBlocked(Exception):
    pass


# Allowed schemes — everything else is blocked outright.
ALLOWED_SCHEMES = {"http", "https"}

# Hostnames hard-blocked regardless of resolution (defense in depth).
BLOCKED_HOSTNAMES = {
    "localhost", "ip6-localhost", "ip6-loopback",
    "<local_ip>",
    # AWS / GCP / Azure / DigitalOcean / Alibaba metadata endpoints
    "metadata.google.internal", "metadata.aws.cloud",
    "metadata.tencent.cloud",
}

# IP networks blocked unless explicitly allowed. RFC1918 + loopback + link-local
# + cloud-metadata + carrier-grade NAT + reserved/multicast/etc.
_BLOCKED_NETS = [
    ipaddress.ip_network("127.0.0.0/8"),      # loopback
    ipaddress.ip_network("10.0.0.0/8"),       # private
    ipaddress.ip_network("172.16.0.0/12"),    # private
    ipaddress.ip_network("192.168.0.0/16"),   # private
    ipaddress.ip_network("169.254.0.0/16"),   # link-local / metadata
    ipaddress.ip_network("100.64.0.0/10"),    # CGNAT
    ipaddress.ip_network("0.0.0.0/8"),        # reserved
    ipaddress.ip_network("224.0.0.0/4"),      # multicast
    ipaddress.ip_network("240.0.0.0/4"),      # reserved
    # IPv6
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),         # unique local
    ipaddress.ip_network("fe80::/10"),        # link-local
]


def _ip_blocked(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # Couldn't parse → block
    for net in _BLOCKED_NETS:
        if isinstance(ip, ipaddress.IPv4Address) and isinstance(net, ipaddress.IPv4Network):
            if ip in net:
                return True
        if isinstance(ip, ipaddress.IPv6Address) and isinstance(net, ipaddress.IPv6Network):
            if ip in net:
                return True
    return False


def is_safe_url(
    url: str,
    *,
    allow_loopback: bool = False,
    allow_private: bool = False,
    extra_allowed_hosts: Optional[Iterable[str]] = None,
) -> Optional[str]:
    """
    Returns None if the URL is safe to fetch, or a reason string if blocked.

    Args:
      allow_loopback: permit 127.0.0.0/8 + localhost (use for known-good
                       internal probes like Ollama)
      allow_private:  permit RFC1918 ranges (use sparingly)
      extra_allowed_hosts: additional hostnames to whitelist
    """
    if not url or not isinstance(url, str):
        return "url empty or not a string"
    try:
        p = urlparse(url)
    except Exception as e:
        return f"url parse failed: {e}"
    if p.scheme.lower() not in ALLOWED_SCHEMES:
        return f"scheme '{p.scheme}' not allowed (use http/https)"
    host = (p.hostname or "").lower()
    if not host:
        return "url has no host"

    allowed = set(extra_allowed_hosts or [])
    if host in allowed:
        return None
    if host in BLOCKED_HOSTNAMES:
        if allow_loopback and host in ("localhost", "ip6-localhost", "ip6-loopback", "<local_ip>"):
            return None
        if allow_private and host in ("<local_ip>",):
            return None
        return f"hostname '{host}' is blocked"

    # Resolve and check every A/AAAA. DNS-rebinding defense: a tricky
    # attacker can flip resolution between checks and fetches — for full
    # protection the caller should also pin the IP they fetch. Here we
    # at least refuse anything obvious.
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        return f"DNS resolution failed: {e}"
    for info in infos:
        ip_str = info[4][0]
        if _ip_blocked(ip_str):
            try:
                ip = ipaddress.ip_address(ip_str)
                is_lb = ip.is_loopback
                is_pr = ip.is_private
            except ValueError:
                is_lb = is_pr = False
            if allow_loopback and is_lb:
                continue
            if allow_private and is_pr:
                continue
            return f"resolved IP {ip_str} is in a blocked range"
    return None


def ensure_safe_url(url: str, **kwargs) -> None:
    """Raise SSRFBlocked if `url` fails the check. Logs the block + emits
    SEC event for observability."""
    reason = is_safe_url(url, **kwargs)
    if reason is None:
        return
    logger.warning(f"SSRF blocked: {url} — {reason}")
    try:
        from src.observability.event_stream import emit, EventType
        from src.observability.context import current_session_id, current_request_id
        emit(EventType.SEC_INJECTION_BLOCKED,
             data={"kind": "ssrf", "url": url[:200], "reason": reason},
             session_id=current_session_id(),
             request_id=current_request_id(),
             source="ssrf_guard")
    except Exception:
        pass
    raise SSRFBlocked(f"URL blocked by SSRF guard: {reason}")
