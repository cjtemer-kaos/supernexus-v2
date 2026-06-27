"""Tests for gemas_core.core.rate_limit_unified."""
import pytest
from gemas_core.core.rate_limit_unified import SafetyLimiter, DEFAULT_PURPOSE


def _stub_request(*, remote="1.2.3.4", xff=None):
    """Build a minimal request stub that matches the duck-typed interface
    used by ``SafetyLimiter._extract_client_id``."""

    class _Hdrs:
        def __init__(self, xff):
            self._xff = xff

        def get(self, k, default=None):
            if k == "X-Forwarded-For":
                return self._xff
            return default

    class _Req:
        def __init__(self):
            self.headers = _Hdrs(xff)
            self.remote = remote

    return _Req()


# -------------------------------------------------------------------
# Construction
# -------------------------------------------------------------------


def test_default_construction_uses_default_purpose():
    s = SafetyLimiter()
    assert DEFAULT_PURPOSE in s.purposes
    assert s.config_for("default") == {"max_requests": 100, "window_seconds": 60}


def test_multiple_purposes():
    s = SafetyLimiter(
        default={"max_requests": 100, "window_seconds": 60},
        chat={"max_requests": 60, "window_seconds": 60},
        rcon={"max_requests": 30, "window_seconds": 60},
    )
    assert set(s.purposes) == {"default", "chat", "rcon"}
    assert s.config_for("chat") == {"max_requests": 60, "window_seconds": 60}
    assert s.config_for("rcon") == {"max_requests": 30, "window_seconds": 60}


def test_unknown_purpose_falls_back_to_default():
    s = SafetyLimiter(default={"max_requests": 5, "window_seconds": 60})
    # First 5 should pass for "bogus" (mapped to default)
    for _ in range(5):
        allowed, _ = s.check("ip", purpose="bogus")
        assert allowed
    # 6th should be denied
    allowed, info = s.check("ip", purpose="bogus")
    assert not allowed
    assert info["purpose"] == "default"  # mapped to default


# -------------------------------------------------------------------
# Legacy check() shape
# -------------------------------------------------------------------


def test_check_returns_legacy_tuple():
    s = SafetyLimiter(default={"max_requests": 2, "window_seconds": 60})
    allowed, info = s.check("ip1", purpose="default")
    assert allowed is True
    assert info["purpose"] == "default"
    # No "reason" key when allowed
    assert "reason" not in info


def test_check_denied_shape():
    s = SafetyLimiter(default={"max_requests": 1, "window_seconds": 60})
    s.check("ip", purpose="default")
    allowed, info = s.check("ip", purpose="default")
    assert allowed is False
    assert info["reason"] == "rate_limit_exceeded"
    assert info["retry_after"] == 60
    assert info["retry_after_seconds"] == 60
    assert info["max_requests"] == 1
    assert info["window_seconds"] == 60


def test_check_per_purpose_isolation():
    s = SafetyLimiter(
        default={"max_requests": 1, "window_seconds": 60},
        chat={"max_requests": 1, "window_seconds": 60},
    )
    # Exhaust chat
    assert s.check("ip", purpose="chat")[0] is True
    assert s.check("ip", purpose="chat")[0] is False
    # default has its own bucket
    assert s.check("ip", purpose="default")[0] is True


def test_check_per_client_isolation():
    s = SafetyLimiter(default={"max_requests": 1, "window_seconds": 60})
    assert s.check("a")[0] is True
    assert s.check("a")[0] is False
    assert s.check("b")[0] is True


# -------------------------------------------------------------------
# Request-aware helpers
# -------------------------------------------------------------------


def test_check_request_extracts_remote():
    s = SafetyLimiter(default={"max_requests": 1, "window_seconds": 60})
    req = _stub_request(remote="10.0.0.1")
    assert s.check_request(req)[0] is True
    assert s.check_request(req)[0] is False


def test_check_request_prefers_xff():
    s = SafetyLimiter(default={"max_requests": 1, "window_seconds": 60})
    req1 = _stub_request(remote="proxy", xff="1.1.1.1")
    req2 = _stub_request(remote="proxy", xff="2.2.2.2")
    assert s.check_request(req1)[0] is True
    # Different XFF → different bucket
    assert s.check_request(req2)[0] is True
    # Same XFF → exhausted
    assert s.check_request(req1)[0] is False


def test_check_request_prefix_namespaces():
    s = SafetyLimiter(default={"max_requests": 1, "window_seconds": 60})
    req = _stub_request(remote="1.1.1.1")
    # Without prefix
    assert s.check_request(req)[0] is True
    # With prefix — new bucket
    assert s.check_request(req, prefix="chat")[0] is True
    # Both exhausted
    assert s.check_request(req)[0] is False
    assert s.check_request(req, prefix="chat")[0] is False


def test_check_request_or_429_returns_none_when_allowed():
    s = SafetyLimiter(default={"max_requests": 1, "window_seconds": 60})
    req = _stub_request()
    assert s.check_request_or_429(req) is None


def test_check_request_or_429_returns_response_when_denied():
    s = SafetyLimiter(default={"max_requests": 1, "window_seconds": 60})
    req = _stub_request(remote="1.1.1.1")
    s.check_request(req)  # exhaust
    resp = s.check_request_or_429(req)
    assert resp is not None
    # aiohttp.web.json_response stores status + body
    assert resp.status == 429
    import json
    body = json.loads(resp.body.decode("utf-8"))
    assert body["error"] == "rate_limit_exceeded"
    assert body["purpose"] == "default"
    assert body["retry_after"] == 60
    assert resp.headers.get("Retry-After") == "60"


def test_gate_request_alias():
    s = SafetyLimiter(default={"max_requests": 1, "window_seconds": 60})
    req = _stub_request()
    s.gate_request(req)  # exhaust
    assert s.gate_request(req) is not None  # denied


def test_extract_client_id_handles_missing_remote():
    """A request with no ``remote`` attr and no XFF should not crash."""

    class _Bare:
        headers = type("H", (), {"get": lambda self, k, default=None: None})()
        remote = None

    s = SafetyLimiter(default={"max_requests": 5, "window_seconds": 60})
    allowed, _ = s.check_request(_Bare())
    assert allowed is True


def test_extract_client_id_with_prefix():
    s = SafetyLimiter()
    req = _stub_request(remote="1.1.1.1")
    cid = s._extract_client_id(req, prefix="chat")
    assert cid == "chat:1.1.1.1"
    cid2 = s._extract_client_id(req, prefix="")
    assert cid2 == "1.1.1.1"


# -------------------------------------------------------------------
# Admin / observability
# -------------------------------------------------------------------


def test_reset_specific_client_one_purpose():
    s = SafetyLimiter(
        default={"max_requests": 1, "window_seconds": 60},
        chat={"max_requests": 1, "window_seconds": 60},
    )
    s.check("a", purpose="default")
    s.check("a", purpose="chat")
    assert s.check("a", purpose="default")[0] is False
    assert s.check("a", purpose="chat")[0] is False
    # Reset "a" only on default
    s.reset("a", purpose="default")
    assert s.check("a", purpose="default")[0] is True
    # chat still blocked
    assert s.check("a", purpose="chat")[0] is False


def test_reset_specific_client_all_purposes():
    s = SafetyLimiter(
        default={"max_requests": 1, "window_seconds": 60},
        chat={"max_requests": 1, "window_seconds": 60},
    )
    s.check("a", purpose="default")
    s.check("a", purpose="chat")
    s.reset("a")
    assert s.check("a", purpose="default")[0] is True
    assert s.check("a", purpose="chat")[0] is True


def test_reset_all():
    s = SafetyLimiter(default={"max_requests": 1, "window_seconds": 60})
    s.check("a")
    s.check("b")
    s.reset()
    assert s.check("a")[0] is True
    assert s.check("b")[0] is True


def test_reset_all_purposes_for_one():
    s = SafetyLimiter(
        default={"max_requests": 1, "window_seconds": 60},
        chat={"max_requests": 1, "window_seconds": 60},
    )
    s.check("a", purpose="default")
    s.check("a", purpose="chat")
    s.reset(purpose="default")
    assert s.check("a", purpose="default")[0] is True
    # chat unaffected
    assert s.check("a", purpose="chat")[0] is False


def test_status_reports_config_and_live_state():
    s = SafetyLimiter(
        default={"max_requests": 5, "window_seconds": 60},
        chat={"max_requests": 60, "window_seconds": 60},
    )
    s.check("a")
    s.check("b", purpose="chat")
    s.check("c", purpose="chat")
    st = s.status()
    assert st["default"]["max_requests"] == 5
    assert st["default"]["window_seconds"] == 60
    assert st["default"]["total_recorded"] == 1
    assert st["chat"]["max_requests"] == 60
    assert st["chat"]["total_recorded"] == 2


def test_add_purpose_dynamic():
    s = SafetyLimiter()
    assert "vision" not in s.purposes
    s.add_purpose("vision", max_requests=10, window_seconds=30)
    assert "vision" in s.purposes
    # Idempotent
    s.add_purpose("vision", max_requests=999, window_seconds=999)
    assert s.config_for("vision") == {"max_requests": 10, "window_seconds": 30}


# -------------------------------------------------------------------
# Redis backend
# -------------------------------------------------------------------


import socket
import uuid


def _redis_reachable() -> bool:
    try:
        s = socket.create_connection(("127.0.0.1", 6379), timeout=0.5)
        s.close()
        return True
    except OSError:
        return False


_redis_required = pytest.mark.skipif(
    not _redis_reachable(), reason="Redis not reachable at 127.0.0.1:6379"
)


@_redis_required
def test_redis_backend_default():
    """``backend='redis'`` wires every purpose through Redis."""
    from gemas_core.core.rate_limiter_redis import RedisRateLimiter
    prefix = f"test:safety:{uuid.uuid4().hex[:8]}"
    s = SafetyLimiter(
        backend="redis",
        redis_kwargs={"redis_url": "redis://127.0.0.1:6379/0", "key_prefix": prefix},
        default={"max_requests": 3, "window_seconds": 2},
    )
    try:
        for _ in range(3):
            assert s.check("ip")[0]
        assert s.check("ip")[0] is False
        # Limiter is a Redis instance, not the in-process one
        for purpose in s.purposes:
            assert isinstance(s._limiters[purpose], RedisRateLimiter)
    finally:
        s.reset()


@_redis_required
def test_redis_backend_shared_state():
    """Two ``SafetyLimiter`` instances pointing at the same Redis
    share buckets — the whole point of going to Redis."""
    prefix = f"test:safety:{uuid.uuid4().hex[:8]}"
    a = SafetyLimiter(
        backend="redis",
        redis_kwargs={"redis_url": "redis://127.0.0.1:6379/0", "key_prefix": prefix},
        default={"max_requests": 2, "window_seconds": 5},
    )
    b = SafetyLimiter(
        backend="redis",
        redis_kwargs={"redis_url": "redis://127.0.0.1:6379/0", "key_prefix": prefix},
        default={"max_requests": 2, "window_seconds": 5},
    )
    try:
        assert a.check("ip")[0]
        assert b.check("ip")[0]
        # 3rd must fail on either
        assert a.check("ip")[0] is False
        assert b.check("ip")[0] is False
    finally:
        a.reset()


@_redis_required
def test_redis_backend_add_purpose():
    prefix = f"test:safety:{uuid.uuid4().hex[:8]}"
    s = SafetyLimiter(
        backend="redis",
        redis_kwargs={"redis_url": "redis://127.0.0.1:6379/0", "key_prefix": prefix},
    )
    try:
        s.add_purpose("vision", max_requests=5, window_seconds=5)
        assert "vision" in s.purposes
        # Uses the same Redis backend
        from gemas_core.core.rate_limiter_redis import RedisRateLimiter
        assert isinstance(s._limiters["vision"], RedisRateLimiter)
    finally:
        s.reset()


def test_invalid_backend_raises():
    with pytest.raises(ValueError):
        SafetyLimiter(backend="bogus", default={"max_requests": 1, "window_seconds": 1})


def test_pre_built_limiter_accepted():
    """A pre-built limiter (e.g. RedisRateLimiter with a custom
    client) can be passed directly instead of a config dict."""
    from gemas_core.core.rate_limiter import RateLimiter
    custom = RateLimiter(max_requests=7, window_seconds=30)
    s = SafetyLimiter(default=custom)
    assert s.config_for("default") == {"max_requests": 7, "window_seconds": 30}
    # The exact instance is reused (so we can attach behaviour to it)
    assert s._limiters["default"] is custom
