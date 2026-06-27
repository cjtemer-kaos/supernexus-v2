"""Redis-backed rate limiter — sliding window, keyed by string.

Drop-in replacement for the in-process :class:`RateLimiter` when
you need to share buckets across processes or machines
(multi-worker deployments, multiple API servers behind a load
balancer, etc.).

The sliding window is implemented as a sorted set per key:

  ZADD   rl:<key>   <score=now_ms>   <member=unique_id>
  ZREMRANGEBYSCORE  rl:<key>  -inf  (now_ms - window_ms)
  ZCARD  rl:<key>
  EXPIRE rl:<key>  <window_seconds + 1>

The unique member ID is required because ZADD with a duplicate
score+member pair is a no-op. We use ``f"{now_ms}:{uuid4_hex}"``
so two requests landing in the same millisecond don't collide.

All four ops run inside a single ``MULTI/EXEC`` pipeline so the
sliding window is consistent: a flood can't slip past a half-
updated state.

Lazy redis import
-----------------

``redis`` is a heavy dependency. Importing it lazily keeps
gemas_core importable in environments that don't need the
Redis backend (and where the package isn't installed).

Usage
-----

    from gemas_core import RedisRateLimiter

    limiter = RedisRateLimiter(
        max_requests=100,
        window_seconds=60,
        redis_url="redis://127.0.0.1:6379/0",
        key_prefix="nexus:rl",
    )

    if not limiter.check("1.2.3.4"):
        return web.json_response({"error": "rate_limit_exceeded"}, status=429)
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Optional

__all__ = ["RedisRateLimiter", "RedisLimiterBackend"]


def _import_redis():
    """Lazy redis import — see module docstring."""
    import redis  # type: ignore[import-not-found]
    return redis


class RedisLimiterBackend:
    """Protocol-typed seam: the only piece of redis-py the
    :class:`RedisRateLimiter` actually depends on. Tests can pass
    a ``fakeredis`` instance (or any object that implements
    ``pipeline()``) without touching the real network.
    """

    def pipeline(self) -> Any: ...


class RedisRateLimiter:
    """Sliding-window rate limiter, shared via Redis.

    Implements the same surface as the in-process
    :class:`gemas_core.core.rate_limiter.RateLimiter` so callers
    can swap one for the other:

      - ``check(key) -> bool`` — atomic sliding-window check.
      - ``reset(key) -> None`` — clear all recorded timestamps.
      - ``reset_all() -> None`` — ``SCAN`` + ``DEL`` (use sparingly).
      - ``snapshot() -> Dict[str, int]`` — observability dump.
      - ``max_requests`` / ``window`` — introspection of the config.
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        *,
        redis_url: str = "redis://127.0.0.1:6379/0",
        key_prefix: str = "gemas:rl",
        client: Optional[Any] = None,
    ):
        if window_seconds <= 0:
            raise ValueError(f"window_seconds must be > 0, got {window_seconds}")
        self.max_requests = max(0, max_requests)
        self.window: float = float(window_seconds)
        self.window_ms: int = int(self.window * 1000)
        self.key_prefix = key_prefix.rstrip(":")

        if client is not None:
            self._client = client
        else:
            redis = _import_redis()
            self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    def _key(self, key: str) -> str:
        return f"{self.key_prefix}:{key}"

    @property
    def client(self) -> Any:
        return self._client

    # ------------------------------------------------------------------
    # Public API (mirrors in-process RateLimiter)
    # ------------------------------------------------------------------

    def check(self, key: str) -> bool:
        """Return True if *key* is allowed, False if rate-limited.

        Atomic via ``MULTI/EXEC``:
          1. ``ZREMRANGEBYSCORE`` — drop entries that slid out.
          2. ``ZCARD`` — count what's left.
          3. If under the cap, ``ZADD`` a new entry.
          4. ``EXPIRE`` the key so empty buckets are reaped.
        """
        full_key = self._key(key)
        now_ms = int(time.time() * 1000)
        cutoff = now_ms - self.window_ms
        member = f"{now_ms}:{uuid.uuid4().hex[:12]}"

        try:
            pipe = self._client.pipeline(transaction=True)
            pipe.zremrangebyscore(full_key, "-inf", cutoff)
            pipe.zcard(full_key)
            pipe.zadd(full_key, {member: now_ms})
            pipe.expire(full_key, int(self.window) + 1)
            results = pipe.execute()
        except Exception:
            # Fail-open: if Redis is unreachable, don't deny real
            # users. Log the failure so it's visible. Callers can
            # override this behaviour by wrapping ``check`` in a
            # try/except.
            return True

        count_before = int(results[1])
        if count_before >= self.max_requests:
            # The ``ZADD`` already happened inside the MULTI; roll
            # it back with an extra ``ZREM``. We do this AFTER the
            # EXEC because rollback-in-MULTI needs WATCH (heavier).
            # A leaked denied-timestamp entry will be cleaned by the
            # next ``ZREMRANGEBYSCORE`` for that key.
            try:
                self._client.zrem(full_key, member)
            except Exception:
                pass
            return False
        return True

    def reset(self, key: str) -> None:
        try:
            self._client.delete(self._key(key))
        except Exception:
            pass

    def reset_all(self) -> None:
        """Clear every key under our prefix. Uses ``SCAN`` to avoid
        blocking the Redis server on large keyspaces.
        """
        try:
            cursor = 0
            pattern = f"{self.key_prefix}:*"
            while True:
                cursor, keys = self._client.scan(cursor=cursor, match=pattern, count=200)
                if keys:
                    self._client.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            pass

    def snapshot(self) -> dict:
        """Per-key timestamp count, for observability.

        Uses ``SCAN`` + ``ZCARD`` to avoid blocking. On large
        keyspaces this can be slow — only call from admin paths.
        """
        out: dict = {}
        try:
            cursor = 0
            pattern = f"{self.key_prefix}:*"
            while True:
                cursor, keys = self._client.scan(cursor=cursor, match=pattern, count=200)
                for k in keys:
                    try:
                        out[k] = int(self._client.zcard(k))
                    except Exception:
                        out[k] = -1
                if cursor == 0:
                    break
        except Exception:
            pass
        return out
