"""Tests for gemas_core.core.rate_limiter_redis.

Uses a *real* local Redis on ``127.0.0.1:6379`` (the
project's docker-compose instance). Each test scopes itself
to a unique key prefix and cleans it up at the end so the
tests don't interfere with each other or with the dev
instance's data.

If Redis is not available, every test is ``pytest.skip``-ed
rather than failing the suite.
"""
import socket
import time
import uuid

import pytest

from gemas_core.core.rate_limiter_redis import RedisRateLimiter


REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379


def _redis_reachable() -> bool:
    try:
        s = socket.create_connection((REDIS_HOST, REDIS_PORT), timeout=0.5)
        s.close()
        return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(
    not _redis_reachable(),
    reason=f"Redis not reachable at {REDIS_HOST}:{REDIS_PORT}",
)


def _make(prefix: str | None = None) -> RedisRateLimiter:
    prefix = prefix or f"test:rl:{uuid.uuid4().hex[:8]}"
    return RedisRateLimiter(
        max_requests=3,
        window_seconds=2,
        key_prefix=prefix,
    )


def _cleanup(limiter: RedisRateLimiter) -> None:
    try:
        limiter.reset_all()
    except Exception:
        pass


# -------------------------------------------------------------------
# Basic semantics
# -------------------------------------------------------------------


def test_first_request_allowed():
    rl = _make()
    try:
        assert rl.check("k1") is True
    finally:
        _cleanup(rl)


def test_max_requests_respected():
    rl = _make()
    try:
        for _ in range(3):
            assert rl.check("k1") is True
        assert rl.check("k1") is False
    finally:
        _cleanup(rl)


def test_per_key_isolation():
    rl = _make()
    try:
        for _ in range(3):
            assert rl.check("alice") is True
        assert rl.check("alice") is False
        # Bob has his own bucket
        assert rl.check("bob") is True
    finally:
        _cleanup(rl)


def test_window_slides():
    """After the window elapses, requests are allowed again."""
    rl = _make()
    try:
        for _ in range(3):
            assert rl.check("k1") is True
        assert rl.check("k1") is False
        time.sleep(2.2)
        assert rl.check("k1") is True
    finally:
        _cleanup(rl)


def test_max_requests_zero_blocks_everything():
    rl = RedisRateLimiter(max_requests=0, window_seconds=2, key_prefix=f"test:rl:{uuid.uuid4().hex[:8]}")
    try:
        assert rl.check("k1") is False
    finally:
        _cleanup(rl)


def test_invalid_window_raises():
    with pytest.raises(ValueError):
        RedisRateLimiter(max_requests=1, window_seconds=0, key_prefix="test:rl:bogus")
    with pytest.raises(ValueError):
        RedisRateLimiter(max_requests=1, window_seconds=-1, key_prefix="test:rl:bogus")


# -------------------------------------------------------------------
# Admin / observability
# -------------------------------------------------------------------


def test_reset_specific_key():
    rl = _make()
    try:
        for _ in range(3):
            assert rl.check("k1") is True
        assert rl.check("k1") is False
        rl.reset("k1")
        # Next request should be allowed again
        assert rl.check("k1") is True
    finally:
        _cleanup(rl)


def test_reset_all_clears_everything_under_prefix():
    prefix = f"test:rl:{uuid.uuid4().hex[:8]}"
    rl1 = RedisRateLimiter(max_requests=1, window_seconds=5, key_prefix=prefix)
    rl2 = RedisRateLimiter(max_requests=1, window_seconds=5, key_prefix=prefix)
    try:
        rl1.check("a")
        rl2.check("b")
        assert rl1.check("a") is False
        assert rl2.check("b") is False
        rl1.reset_all()
        # Both buckets should be free again
        assert rl1.check("a") is True
        assert rl2.check("b") is True
    finally:
        _cleanup(rl1)
        _cleanup(rl2)


def test_snapshot_returns_counts():
    rl = _make()
    try:
        rl.check("alice")
        rl.check("alice")
        rl.check("bob")
        snap = rl.snapshot()
        # Keys include the prefix
        assert snap.get(f"{rl.key_prefix}:alice") == 2
        assert snap.get(f"{rl.key_prefix}:bob") == 1
    finally:
        _cleanup(rl)


# -------------------------------------------------------------------
# Cross-process behaviour
# -------------------------------------------------------------------


def test_shared_state_across_instances():
    """Two limiters with the same prefix + Redis share buckets.

    Simulates two API workers pointing at the same Redis:
    together they can't exceed ``max_requests``, even if each
    only saw half the requests.
    """
    prefix = f"test:rl:{uuid.uuid4().hex[:8]}"
    a = RedisRateLimiter(max_requests=3, window_seconds=2, key_prefix=prefix)
    b = RedisRateLimiter(max_requests=3, window_seconds=2, key_prefix=prefix)
    try:
        assert a.check("k1") is True
        assert b.check("k1") is True
        assert a.check("k1") is True
        # 4th across both should fail regardless of which instance
        assert b.check("k1") is False
        assert a.check("k1") is False
    finally:
        a.reset_all()


# -------------------------------------------------------------------
# Failure modes
# -------------------------------------------------------------------


def test_check_fails_open_when_redis_unreachable(monkeypatch):
    """If the connection to Redis is dropped, ``check`` returns
    True (fails open) rather than denying real users."""

    class _BrokenClient:
        def pipeline(self, *args, **kwargs):
            raise ConnectionError("redis down")

    rl = RedisRateLimiter(
        max_requests=1,
        window_seconds=1,
        key_prefix=f"test:rl:{uuid.uuid4().hex[:8]}",
        client=_BrokenClient(),
    )
    # First call also fails open
    assert rl.check("k1") is True
