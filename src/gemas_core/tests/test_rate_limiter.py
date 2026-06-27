"""Tests for gemas_core.core.rate_limiter.

Pattern ported from pewdiepie-archdaemon/odysseus
(``src/rate_limiter.py``): generic in-memory sliding-window rate
limiter, keyed by an arbitrary string (typically an IP or user id).

The contract:
  - ``check(key)`` returns True if the request fits inside the
    current window, False otherwise.
  - When a request is allowed, its timestamp is recorded.
  - When a request is denied, no timestamp is recorded.
  - After ``window_seconds`` elapse, old timestamps drop out and
    the key becomes unblocked again.
  - Each key is independent (per-IP or per-user isolation).
  - Thread-safe via ``threading.Lock``.

Storage is in-process only — not shared across processes or
machines. That's fine for a single FastAPI worker; multi-worker
deployments need a Redis-backed limiter instead.
"""

from __future__ import annotations

import threading
import time
from unittest import mock

import pytest

from gemas_core.core.rate_limiter import RateLimiter


class TestRateLimiterBasic:
    def test_first_request_is_allowed(self) -> None:
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        assert limiter.check("ip-1") is True

    def test_requests_under_max_are_allowed(self) -> None:
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            assert limiter.check("ip-1") is True

    def test_request_over_max_is_denied(self) -> None:
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            assert limiter.check("ip-1") is True
        # 4th request is denied
        assert limiter.check("ip-1") is False

    def test_denied_request_does_not_record_timestamp(self) -> None:
        # If a denied request added a timestamp, it would extend the
        # block window indefinitely. Make sure we don't.
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        assert limiter.check("ip-1") is True
        for _ in range(5):
            assert limiter.check("ip-1") is False
        # After the window passes, the original allowed timestamp
        # should drop out, freeing the key.
        with mock.patch("time.monotonic", return_value=time.monotonic() + 61):
            assert limiter.check("ip-1") is True


class TestRateLimiterSlidingWindow:
    def test_window_expiry_releases_block(self) -> None:
        limiter = RateLimiter(max_requests=2, window_seconds=10)
        with mock.patch("time.monotonic", return_value=100.0):
            assert limiter.check("ip-1") is True
            assert limiter.check("ip-1") is True
            assert limiter.check("ip-1") is False
        # 11 seconds later, both old timestamps are out of window
        with mock.patch("time.monotonic", return_value=111.0):
            assert limiter.check("ip-1") is True

    def test_partial_window_expiry(self) -> None:
        # 3 requests allowed in 10s window. After 5s, the oldest
        # timestamp drops out, freeing one slot.
        limiter = RateLimiter(max_requests=3, window_seconds=10)
        with mock.patch("time.monotonic", return_value=100.0):
            limiter.check("ip-1")
        with mock.patch("time.monotonic", return_value=102.0):
            limiter.check("ip-1")
        with mock.patch("time.monotonic", return_value=104.0):
            limiter.check("ip-1")
            # At t=104: 3 timestamps, at t=104 cutoff=94, all 3 are >94
            assert limiter.check("ip-1") is False
        # At t=110: cutoff=100, only t=102 and t=104 are >100 → 2 timestamps
        with mock.patch("time.monotonic", return_value=110.0):
            assert limiter.check("ip-1") is True
            # Now 3 timestamps again (102, 104, 110), all >100
            assert limiter.check("ip-1") is False


class TestRateLimiterPerKey:
    def test_keys_are_independent(self) -> None:
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        assert limiter.check("ip-1") is True
        assert limiter.check("ip-1") is True
        assert limiter.check("ip-1") is False
        # ip-2 has its own bucket
        assert limiter.check("ip-2") is True
        assert limiter.check("ip-2") is True
        assert limiter.check("ip-2") is False

    def test_unknown_key_starts_empty(self) -> None:
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        # Brand new key should be allowed
        assert limiter.check("never-seen") is True


class TestRateLimiterReset:
    def test_reset_clears_single_key(self) -> None:
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        assert limiter.check("ip-1") is True
        assert limiter.check("ip-1") is False
        limiter.reset("ip-1")
        # After reset, the key is allowed again
        assert limiter.check("ip-1") is True

    def test_reset_does_not_affect_other_keys(self) -> None:
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        limiter.check("ip-1")
        limiter.check("ip-2")
        limiter.reset("ip-1")
        # ip-1 is fresh; ip-2 is still blocked
        assert limiter.check("ip-1") is True
        assert limiter.check("ip-2") is False

    def test_reset_unknown_key_is_noop(self) -> None:
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        # Should not raise
        limiter.reset("never-seen")

    def test_reset_all_clears_everything(self) -> None:
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        limiter.check("ip-1")
        limiter.check("ip-2")
        limiter.check("ip-3")
        limiter.reset_all()
        # All keys fresh
        assert limiter.check("ip-1") is True
        assert limiter.check("ip-2") is True
        assert limiter.check("ip-3") is True


class TestRateLimiterSnapshot:
    def test_snapshot_returns_counts(self) -> None:
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        limiter.check("ip-1")
        limiter.check("ip-1")
        limiter.check("ip-2")
        snap = limiter.snapshot()
        assert snap == {"ip-1": 2, "ip-2": 1}

    def test_snapshot_includes_denied_keys(self) -> None:
        # Even if all subsequent requests are denied, the timestamps
        # array (and the count) reflect the recorded attempts.
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        limiter.check("ip-1")
        limiter.check("ip-1")  # denied, no new timestamp
        snap = limiter.snapshot()
        assert snap["ip-1"] == 1

    def test_snapshot_empty_initially(self) -> None:
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        assert limiter.snapshot() == {}


class TestRateLimiterEdgeCases:
    def test_max_requests_zero_blocks_everything(self) -> None:
        limiter = RateLimiter(max_requests=0, window_seconds=60)
        assert limiter.check("ip-1") is False

    def test_max_requests_one_allows_then_blocks(self) -> None:
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        assert limiter.check("ip-1") is True
        assert limiter.check("ip-1") is False

    def test_negative_max_requests_treated_as_zero(self) -> None:
        # Defensive: bad config from the caller shouldn't crash.
        limiter = RateLimiter(max_requests=-1, window_seconds=60)
        assert limiter.check("ip-1") is False

    def test_empty_string_key_is_valid(self) -> None:
        # An empty key is unusual but not invalid — the limiter just
        # treats it as a normal bucket.
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        assert limiter.check("") is True
        assert limiter.check("") is False

    def test_negative_window_seconds_raises(self) -> None:
        # A negative window is nonsensical; reject loudly at construction.
        with pytest.raises(ValueError):
            RateLimiter(max_requests=5, window_seconds=-1)

    def test_zero_window_seconds_raises(self) -> None:
        # Zero window = "no time" = always stale = always allow, which
        # defeats the purpose. Reject loudly.
        with pytest.raises(ValueError):
            RateLimiter(max_requests=5, window_seconds=0)


class TestRateLimiterConcurrency:
    def test_concurrent_threads_obey_limit(self) -> None:
        # 50 threads racing for 10 slots in a 60s window — exactly 10
        # should be allowed. The lock prevents over-allowance.
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        allowed: list[bool] = []
        lock = threading.Lock()
        ready = threading.Barrier(50)

        def attempt() -> None:
            ready.wait()
            result = limiter.check("ip-1")
            with lock:
                allowed.append(result)

        threads = [threading.Thread(target=attempt) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(allowed) == 50
        assert sum(allowed) == 10  # exactly the limit
        # Internal state agrees
        assert limiter.snapshot()["ip-1"] == 10

    def test_per_thread_keys_dont_interfere(self) -> None:
        # 20 threads, each with its own key, each allowed 1 request.
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        ready = threading.Barrier(20)

        def attempt(i: int) -> None:
            ready.wait()
            assert limiter.check(f"ip-{i}") is True

        threads = [
            threading.Thread(target=attempt, args=(i,)) for i in range(20)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 20 distinct keys, each with 1 timestamp
        assert len(limiter.snapshot()) == 20


class TestRateLimiterCleanup:
    def test_stale_keys_removed_after_cleanup(self) -> None:
        # _maybe_cleanup purges keys whose last timestamp is older
        # than the window. We force cleanup by advancing time past
        # the cleanup interval. Note: __init__ captures the real
        # wall-clock for _last_cleanup, so we reset it explicitly
        # before mocking the clock — otherwise the difference is
        # negative and the cleanup is skipped.
        limiter = RateLimiter(max_requests=5, window_seconds=10)
        with mock.patch("time.monotonic", return_value=100.0):
            limiter.check("ip-1")
            limiter.check("ip-2")
            limiter._last_cleanup = 100.0  # reset for the mock
        # _cleanup_interval defaults to max(2*10, 120) = 120
        # Advance past that interval AND past the window
        with mock.patch("time.monotonic", return_value=300.0):
            limiter.check("ip-3")  # this triggers _maybe_cleanup
        # ip-1 and ip-2 had last timestamps at t=100, cutoff=290,
        # so they're stale. ip-3 is fresh.
        snap = limiter.snapshot()
        assert "ip-1" not in snap
        assert "ip-2" not in snap
        assert "ip-3" in snap
