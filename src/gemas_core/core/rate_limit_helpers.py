"""aiohttp integration layer for :class:`RateLimiter`.

The pure-Python :class:`RateLimiter` (v1.3.0) is framework-agnostic.
This module provides the *glue* for aiohttp apps: a request key
extractor, a 429 response builder, a WebSocket message gate, and a
middleware factory.

Why a separate module:

  - Keeps the core rate limiter stdlib-only and framework-free
    (so it can be unit-tested without aiohttp and reused outside
    web servers).
  - aiohttp is a *heavy* dependency. Importing it is done lazily
    here so that projects that only need the rate limiter don't
    pay the import cost.

Usage in an aiohttp handler::

    from gemas_core import RateLimiter
    from gemas_core.core.rate_limit_helpers import check_http, client_key

    chat_limiter = RateLimiter(max_requests=60, window_seconds=60)

    async def handle_chat(request):
        denied = check_http(chat_limiter, client_key(request))
        if denied is not None:
            return denied
        ...

Usage inside a WebSocket message loop::

    from gemas_core.core.rate_limit_helpers import check_ws

    async for msg in ws:
        if not await check_ws(rcon_limiter, ws, f"{client_ip}:{server}"):
            return ws  # check_ws already closed the socket
        ...

Usage as middleware::

    from gemas_core.core.rate_limit_helpers import rate_limit_middleware

    app = web.Application(
        middlewares=[
            rate_limit_middleware(
                limiter,
                key_fn=lambda r: f"chat:{client_key(r)}",
            ),
        ]
    )

The middleware variant is convenient for blanket protection of a
whole app, but the per-handler variants let you use different
limiters (and different limits) per route — the recommended
approach for endpoints with very different cost profiles.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

from .rate_limiter import RateLimiter

__all__ = [
    "client_key",
    "check_http",
    "check_ws",
    "rate_limit_middleware",
]


def _import_aiohttp_web():
    """Lazy aiohttp.web import.

    aiohttp is a heavy dep. Importing it lazily keeps gemas_core
    importable in environments where aiohttp isn't installed (e.g.
    gemas_client_overrides that don't need web glue, or test
    runners that mock the import).
    """
    from aiohttp import web  # type: ignore[import-not-found]
    return web


def client_key(request: Any, *, prefix: str = "") -> str:
    """Extract a stable rate-limit key from a request.

    Order:
      1. ``X-Forwarded-For`` header (leftmost hop = original client).
         This is what apps behind a reverse proxy see.
      2. ``request.remote`` (direct connection).
      3. ``"unknown"`` (no remote — e.g. test client).

    The ``prefix`` lets callers namespace their keys, so a chat
    limiter and an RCON limiter can run side by side without
    sharing buckets when they happen to use the same key.
    """
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        # ``X-Forwarded-For`` can be a chain: "client, proxy1, proxy2"
        key = xff.split(",", 1)[0].strip()
    else:
        key = getattr(request, "remote", None) or "unknown"
    return f"{prefix}:{key}" if prefix else key


def _denied_response(web: Any, key: str, limiter: RateLimiter) -> Any:
    """Build a 429 ``web.json_response`` with ``Retry-After`` header."""
    return web.json_response(
        {"error": "rate_limit_exceeded", "key": key},
        status=429,
        headers={"Retry-After": str(int(limiter.window))},
    )


def check_http(
    limiter: RateLimiter, key: str
) -> Optional[Any]:
    """Return a 429 response if *key* is rate-limited, else ``None``.

    Handlers should short-circuit on a non-``None`` return::

        denied = check_http(limiter, client_key(request))
        if denied is not None:
            return denied

    This is the recommended pattern when you want per-handler
    control of which routes get rate-limited and with what limits.
    """
    if limiter.check(key):
        return None
    web = _import_aiohttp_web()
    return _denied_response(web, key, limiter)


async def check_ws(
    limiter: RateLimiter, ws: Any, key: str
) -> bool:
    """Gate a WebSocket message against the limiter.

    Returns ``True`` if the message is allowed. Returns ``False``
    and sends a JSON error frame + closes the socket with code
    1008 (policy violation) if the key is blocked.

    WebSockets can't return a 429 — once the upgrade has
    happened, the only signals we have are message frames and
    close codes. 1008 is the standard "policy violation" close
    code; the JSON frame gives the client a structured reason.
    """
    if limiter.check(key):
        return True
    try:
        await ws.send_json({"type": "error", "text": "rate limit exceeded"})
    except Exception:
        # If the socket is already half-closed, just close.
        pass
    try:
        await ws.close(code=1008)
    except Exception:
        pass
    return False


def rate_limit_middleware(
    limiter: RateLimiter,
    *,
    key_fn: Optional[Callable[[Any], str]] = None,
) -> Any:
    """Build an aiohttp middleware that rate-limits every request.

    ``key_fn`` defaults to :func:`client_key` (i.e. uses the request
    remote / X-Forwarded-For). Override it to add a route-specific
    prefix, switch to a user-id when authenticated, or to apply
    different keys to different paths.

    Usage::

        app = web.Application(
            middlewares=[rate_limit_middleware(limiter)]
        )

    Note: the middleware protects HTTP routes only. WebSocket
    messages are not gated by it (the WebSocket upgrade is, but
    per-message handling lives inside the handler and needs
    :func:`check_ws`).
    """
    web = _import_aiohttp_web()

    if key_fn is None:
        def key_fn(request: Any) -> str:
            return client_key(request)

    @web.middleware
    async def _middleware(
        request: Any,
        handler: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        key = key_fn(request)
        if not limiter.check(key):
            return _denied_response(web, key, limiter)
        return await handler(request)

    return _middleware
