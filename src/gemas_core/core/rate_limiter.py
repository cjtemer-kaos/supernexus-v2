"""Generic in-memory rate limiter — sliding window, keyed by string.

Pattern ported from pewdiepie-archdaemon/odysseus
(``src/rate_limiter.py``).

The contract:
  - ``check(key)`` returns True if the request fits inside the
    current window, False otherwise.
  - When a request is allowed, its timestamp is recorded.
  - When a request is denied, no timestamp is recorded (so a flood
    of denied requests doesn't extend the block window).
  - After ``window_seconds`` elapse, old timestamps drop out and
    the key becomes unblocked again.
  - Each key is independent (per-IP or per-user isolation).
  - Thread-safe via ``threading.Lock``.

Storage is in-process only — not shared across processes or
machines. That's fine for a single FastAPI worker; multi-worker
deployments need a Redis-backed limiter instead.

Usage
-----

.. code-block:: python

    limiter = RateLimiter(max_requests=10, window_seconds=60)

    @app.post("/api/chat")
    async def chat(request: Request, ...):
        if not limiter.check(request.client.host):
            raise HTTPException(429, "Too many requests")
        ...
"""

from __future__ import annotations

import threading
import time
from typing import Dict, List

__all__ = ["RateLimiter"]


class RateLimiter:
    """Sliding-window rate limiter, keyed by an arbitrary string.

    ``max_requests`` is clamped to ``>= 0`` (negative is treated as
    zero, i.e. block everything). ``window_seconds`` must be ``> 0``
    — a zero or negative window is nonsensical and raises at
    construction.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        if window_seconds <= 0:
            raise ValueError(
                f"window_seconds must be > 0, got {window_seconds}"
            )
        self.max_requests = max(0, max_requests)
        self.window: float = float(window_seconds)
        self._log: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
        self._last_cleanup: float = time.monotonic()
        # Cleanup at least every 2 windows, but no less often than 120s,
        # so a long window doesn't accumulate stale keys indefinitely.
        self._cleanup_interval: float = max(self.window * 2, 120.0)

    def check(self, key: str) -> bool:
        """Return True if the request is allowed, False if rate-limited.

        Allowed requests are timestamped. Denied requests are NOT
        timestamped — otherwise an attacker could extend the block
        window by sending a flood of denied requests.
        """
        now = time.monotonic()
        with self._lock:
            self._maybe_cleanup(now)
            timestamps = self._log.get(key, [])
            cutoff = now - self.window
            # Drop entries that have slid out of the window
            timestamps = [t for t in timestamps if t > cutoff]
            if len(timestamps) >= self.max_requests:
                # Persist the pruned list (it may be shorter now), but
                # don't add a new timestamp — we're denying.
                self._log[key] = timestamps
                return False
            timestamps.append(now)
            self._log[key] = timestamps
            return True

    def reset(self, key: str) -> None:
        """Clear the recorded timestamps for *key*.

        After ``reset``, the next ``check(key)`` is guaranteed to be
        allowed. Useful for tests, admin overrides, and
        post-authentication refresh.
        """
        with self._lock:
            self._log.pop(key, None)

    def reset_all(self) -> None:
        """Clear every recorded timestamp. Used by tests and admin tools."""
        with self._lock:
            self._log.clear()

    def snapshot(self) -> Dict[str, int]:
        """Return a copy of the current per-key timestamp counts.

        Useful for observability and admin dashboards. The returned
        dict is a snapshot — mutating it does not affect the limiter.
        """
        with self._lock:
            return {k: len(v) for k, v in self._log.items()}

    def _maybe_cleanup(self, now: float) -> None:
        """Periodically purge keys whose last timestamp is stale.

        This is the limiter's only background work; it's called
        inline from ``check`` rather than from a background thread,
        so there's no thread to start, stop, or leak.
        """
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        cutoff = now - self.window
        # A key is "stale" if its timestamp list is empty OR its most
        # recent timestamp has slid out of the window.
        stale = [
            k for k, v in self._log.items() if not v or v[-1] <= cutoff
        ]
        for k in stale:
            del self._log[k]
