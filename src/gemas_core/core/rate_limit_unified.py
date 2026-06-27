"""Unified rate-limiting facade for backend servers.

Wraps :class:`gemas_core.core.rate_limiter.RateLimiter` (v1.3.0)
into a single drop-in class that backend services can plug into
their existing ``backend.safety.check_rate_limit(client_id)``
API without rewriting every call site.

Why this exists
---------------

Two of the three projects in the SuperNEXUS family
(``supernexus-v2`` and ``sfdx``) already have a
``RateLimiter`` inside ``optimization/api_safety.py`` — a
port of the odysseus pattern that returns
``(allowed: bool, info: dict)``. That signature is a
contract several handlers depend on. The third project
(``latamrust-nexus``) was migrated in v1.4.0 to use the
gemas_core ``RateLimiter`` + ``check_http`` helpers
directly, but the other two were left alone because
refactoring every call site was deemed out of scope.

This module unifies the underlying limiter without
forcing a rewrite of the call sites:

  - The same ``RateLimiter`` class is the single source
    of truth (and is also the one used by the v1.10.0
    Redis backend).
  - The same ``check(client_id, *, purpose)`` signature
    is preserved — back-compat for existing handlers.
  - New helper methods (``check_request``,
    ``check_request_or_429``, ``gate_request``) make
    it ergonomic to migrate handlers one at a time.

Usage
-----

    from gemas_core import SafetyLimiter

    safety = SafetyLimiter(default={"max_requests": 100, "window_seconds": 60})

    # Legacy call-site shape (unchanged):
    allowed, info = safety.check(client_ip, purpose="default")
    if not allowed:
        return 429 response with info["reason"], info["retry_after"]

    # New request-aware shape (recommended for new handlers):
    denied = safety.gate_request(request, purpose="chat")
    if denied is not None:
        return denied
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple

from .rate_limiter import RateLimiter


def _build_limiter(backend: str, *, max_requests: int, window_seconds: int, **kwargs):
    """Construct an in-process or Redis-backed RateLimiter.

    ``backend`` is one of:
      - ``"memory"`` (default) — use the in-process :class:`RateLimiter`.
      - ``"redis"`` — use :class:`RedisRateLimiter` for shared state.
    """
    if backend == "memory":
        return RateLimiter(max_requests, window_seconds)
    if backend == "redis":
        from .rate_limiter_redis import RedisRateLimiter
        return RedisRateLimiter(
            max_requests=max_requests,
            window_seconds=window_seconds,
            **kwargs,
        )
    raise ValueError(
        f"unknown backend {backend!r}; expected 'memory' or 'redis'"
    )

__all__ = ["SafetyLimiter", "DEFAULT_PURPOSE"]


DEFAULT_PURPOSE = "default"


class SafetyLimiter:
    """Multi-purpose rate-limiting facade.

    Owns one :class:`RateLimiter` per *purpose* (route bucket). All
    purposes are constructed up-front so a misconfigured purpose
    surfaces at startup rather than at the first request.

    Parameters
    ----------
    default, chat, rcon, vision, **extra
        Keyword arguments map purpose name → ``{"max_requests": int,
        "window_seconds": int}`` (memory backend) or to a
        pre-built limiter instance. Any purpose not passed falls
        back to the ``default`` config. ``default`` itself defaults
        to 100 req / 60 s.
    backend
        ``"memory"`` (default) or ``"redis"``. If ``"redis"`` is
        chosen, all purposes share a single ``key_prefix`` and
        ``redis_url`` (see ``redis_kwargs``).
    redis_kwargs
        Forwarded to :class:`RedisRateLimiter` only when
        ``backend="redis"`` (e.g. ``redis_url``, ``key_prefix``).
    """

    def __init__(
        self,
        *,
        backend: str = "memory",
        redis_kwargs: Optional[Mapping[str, Any]] = None,
        **configs: Any,
    ):
        # Provide a sane default so callers can ``SafetyLimiter()``
        # and get something usable.
        if DEFAULT_PURPOSE not in configs:
            configs = {DEFAULT_PURPOSE: {"max_requests": 100, "window_seconds": 60}, **configs}
        else:
            configs = dict(configs)
            configs.setdefault(DEFAULT_PURPOSE, {"max_requests": 100, "window_seconds": 60})
        self.backend = backend
        self.redis_kwargs: Dict[str, Any] = dict(redis_kwargs or {})
        self._configs: Dict[str, Dict[str, int]] = {}
        self._limiters: Dict[str, Any] = {}
        for purpose, cfg in configs.items():
            if isinstance(cfg, RateLimiter) or (
                hasattr(cfg, "check") and hasattr(cfg, "max_requests")
            ):
                # Pre-built limiter (e.g. caller constructed a RedisRateLimiter)
                self._limiters[purpose] = cfg
                self._configs[purpose] = {
                    "max_requests": cfg.max_requests,
                    "window_seconds": int(cfg.window),
                }
            else:
                cfg = dict(cfg)
                self._configs[purpose] = {"max_requests": int(cfg["max_requests"]), "window_seconds": int(cfg["window_seconds"])}
                self._limiters[purpose] = _build_limiter(
                    backend,
                    max_requests=self._configs[purpose]["max_requests"],
                    window_seconds=self._configs[purpose]["window_seconds"],
                    **self.redis_kwargs,
                )
        self._known_purposes: Tuple[str, ...] = tuple(self._limiters.keys())

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @property
    def purposes(self) -> Tuple[str, ...]:
        """Read-only tuple of configured purpose names."""
        return self._known_purposes

    def config_for(self, purpose: str) -> Dict[str, int]:
        return dict(self._configs.get(purpose, self._configs[DEFAULT_PURPOSE]))

    def add_purpose(self, purpose: str, *, max_requests: int, window_seconds: int) -> None:
        """Register a new purpose after construction.

        Intended for plugins / dynamic config. If *purpose* is
        already known this is a no-op (idempotent).
        """
        if purpose in self._limiters:
            return
        self._configs[purpose] = {"max_requests": max_requests, "window_seconds": window_seconds}
        self._limiters[purpose] = _build_limiter(
            self.backend,
            max_requests=max_requests,
            window_seconds=window_seconds,
            **self.redis_kwargs,
        )
        self._known_purposes = tuple(self._limiters.keys())

    # ------------------------------------------------------------------
    # Core check API
    # ------------------------------------------------------------------

    def _resolve_purpose(self, purpose: Optional[str]) -> str:
        if not purpose:
            return DEFAULT_PURPOSE
        if purpose in self._limiters:
            return purpose
        return DEFAULT_PURPOSE

    def check(
        self,
        client_id: str,
        *,
        purpose: Optional[str] = DEFAULT_PURPOSE,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check a client_id against the limiter for *purpose*.

        Returns the legacy ``(allowed, info)`` tuple shape:
          - ``allowed`` is True if the request fits in the window.
          - ``info`` always has ``"purpose"``; on denial it also
            carries ``"reason"`` and ``"retry_after_seconds"`` so
            handlers can build a 429 response.
        """
        purpose_name = self._resolve_purpose(purpose)
        limiter = self._limiters[purpose_name]
        allowed = limiter.check(client_id)
        info: Dict[str, Any] = {"purpose": purpose_name}
        if not allowed:
            info["reason"] = "rate_limit_exceeded"
            info["retry_after"] = int(limiter.window)
            info["retry_after_seconds"] = int(limiter.window)
            info["max_requests"] = limiter.max_requests
            info["window_seconds"] = int(limiter.window)
        return allowed, info

    # ------------------------------------------------------------------
    # Request-aware helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_client_id(request: Any, *, prefix: str = "") -> str:
        """Extract a client identifier from an aiohttp-style request.

        Mirrors the order in :func:`gemas_core.core.rate_limit_helpers.client_key`
        but is duplicated here so this module stays stdlib-only at
        import time and doesn't pull aiohttp.

        The ``prefix`` lets callers namespace their keys, so a chat
        limiter and an RCON limiter can run side by side without
        sharing buckets.
        """
        try:
            headers = request.headers
            xff = headers.get("X-Forwarded-For")
        except AttributeError:
            xff = None
        if xff:
            client = xff.split(",", 1)[0].strip()
        else:
            client = getattr(request, "remote", None) or "unknown"
        return f"{prefix}:{client}" if prefix else client

    def check_request(
        self,
        request: Any,
        *,
        purpose: Optional[str] = DEFAULT_PURPOSE,
        prefix: str = "",
    ) -> Tuple[bool, Dict[str, Any]]:
        """Convenience wrapper: extract client_id then ``check``.

        Use this from aiohttp handlers where the request object is
        available.
        """
        client_id = self._extract_client_id(request, prefix=prefix)
        return self.check(client_id, purpose=purpose)

    def check_request_or_429(
        self,
        request: Any,
        *,
        purpose: Optional[str] = DEFAULT_PURPOSE,
        prefix: str = "",
    ) -> Optional[Any]:
        """Return a 429 aiohttp response if blocked, else None.

        For handlers that want a single-line gate::

            denied = safety.check_request_or_429(request, purpose="chat")
            if denied is not None:
                return denied
        """
        allowed, info = self.check_request(request, purpose=purpose, prefix=prefix)
        if allowed:
            return None
        return self._build_429(info)

    def gate_request(
        self,
        request: Any,
        *,
        purpose: Optional[str] = DEFAULT_PURPOSE,
        prefix: str = "",
    ) -> Optional[Any]:
        """Alias for :meth:`check_request_or_429` (shorter, common verb)."""
        return self.check_request_or_429(request, purpose=purpose, prefix=prefix)

    @staticmethod
    def _build_429(info: Dict[str, Any]) -> Any:
        """Build a 429 ``web.json_response``.

        Lazy aiohttp import — this module is otherwise stdlib-only.
        """
        from aiohttp import web  # type: ignore[import-not-found]
        return web.json_response(
            {
                "error": info.get("reason", "rate_limit_exceeded"),
                "reason": info.get("reason", "rate_limit_exceeded"),
                "retry_after": info.get("retry_after_seconds", info.get("retry_after", 1)),
                "purpose": info.get("purpose", DEFAULT_PURPOSE),
            },
            status=429,
            headers={"Retry-After": str(int(info.get("retry_after_seconds", info.get("retry_after", 1))))},
        )

    # ------------------------------------------------------------------
    # Admin / observability
    # ------------------------------------------------------------------

    def reset(self, client_id: Optional[str] = None, *, purpose: Optional[str] = None) -> None:
        """Clear limiter state.

          - ``reset(client_id)`` clears that client across all purposes.
          - ``reset(client_id, purpose=...)`` clears for one purpose only.
          - ``reset()`` (no args) clears everything for all purposes.
        """
        if client_id is None and purpose is None:
            for limiter in self._limiters.values():
                limiter.reset_all()
            return
        if client_id is None:
            self._limiters[self._resolve_purpose(purpose)].reset_all()
            return
        purposes_to_clear = (self._resolve_purpose(purpose),) if purpose else self._known_purposes
        for p in purposes_to_clear:
            self._limiters[p].reset(client_id)

    def status(self) -> Dict[str, Any]:
        """Observability dump: per-purpose config + live bucket sizes."""
        out: Dict[str, Any] = {}
        for purpose in self._known_purposes:
            limiter = self._limiters[purpose]
            out[purpose] = {
                "max_requests": limiter.max_requests,
                "window_seconds": int(limiter.window),
                "active_keys": len(limiter.snapshot()),
                "total_recorded": sum(limiter.snapshot().values()),
            }
        return out
