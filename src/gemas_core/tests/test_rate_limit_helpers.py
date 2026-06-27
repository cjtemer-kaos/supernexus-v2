"""Tests for gemas_core.core.rate_limit_helpers.

The helpers are an aiohttp integration layer over the pure-Python
``RateLimiter`` (v1.3.0). They provide:

  - ``client_key(request, *, prefix="")`` — extract a stable rate-limit
    key from a request (X-Forwarded-For first, then remote).
  - ``check_http(limiter, key)`` — returns a 429 ``web.Response`` if
    the key is blocked, else ``None``. Caller short-circuits the
    handler on 429.
  - ``check_ws(limiter, ws, key)`` — for WebSocket message loops.
    Sends a JSON error frame, closes the socket, and returns False
    when the key is blocked. Returns True when allowed.
  - ``rate_limit_middleware(limiter, *, key_fn=None)`` — aiohttp
    middleware factory that calls ``check_http`` automatically.

We don't spin up a real aiohttp server in these tests — that would
be a real integration test, not a unit test. Instead, we mock the
minimum aiohttp surface (``web.Response``, ``WSMsgType``, etc.) and
verify the contract: status code, body shape, headers, and the
``Retry-After`` value. The contract is what callers depend on; the
real aiohttp integration is covered by ``tests/test_*.py`` in
each project that uses the helpers.
"""

from __future__ import annotations

from typing import Any, Optional
from unittest import mock

import pytest

from gemas_core.core.rate_limiter import RateLimiter


# ----- minimal aiohttp fakes --------------------------------------------------

class FakeWebException(Exception):
    pass


class FakeResponse:
    def __init__(self, *, text: Optional[str] = None, body: Any = None,
                 status: int = 200, headers: Optional[dict] = None,
                 content_type: str = "application/json"):
        self.text = text
        self.body = body
        self.status = status
        self.headers = headers or {}
        self.content_type = content_type


class FakeRequest:
    def __init__(self, *, remote: str = "127.0.0.1",
                 headers: Optional[dict] = None):
        self.remote = remote
        self.headers = headers or {}


class FakeWebSocket:
    def __init__(self):
        self.sent: list[Any] = []
        self.closed_with: Optional[int] = None
        self.close_message: Optional[str] = None

    async def send_json(self, payload: Any) -> None:
        self.sent.append(payload)

    async def close(self, code: int = 1000, message: Optional[str] = None) -> None:
        self.closed_with = code
        self.close_message = message


# ----- fixtures ---------------------------------------------------------------

@pytest.fixture
def aiohttp_fakes(monkeypatch):
    """Inject fake aiohttp modules so the helpers' lazy import succeeds.

    The helpers do ``from aiohttp import web``. For that to find our
    fake, both ``aiohttp`` and ``aiohttp.web`` must be in
    ``sys.modules``, AND ``aiohttp.web`` must be reachable as
    ``aiohttp.web`` (via the ``.web`` attribute on the aiohttp
    module). We satisfy all three with the cross-references below.
    """
    fake_aiohttp = mock.MagicMock()
    fake_module_web = mock.MagicMock()
    fake_module_web.Response = FakeResponse

    def fake_json_response(body, *, status=200, headers=None, **kwargs):
        return FakeResponse(body=body, status=status, headers=headers or {})

    fake_module_web.json_response = fake_json_response
    fake_module_web.WSMsgType = mock.MagicMock()

    def middleware_decorator(fn):
        return fn

    fake_module_web.middleware = middleware_decorator

    # Cross-reference: aiohttp.web is reachable via aiohttp.web
    fake_aiohttp.web = fake_module_web

    monkeypatch.setitem(__import__("sys").modules, "aiohttp", fake_aiohttp)
    monkeypatch.setitem(
        __import__("sys").modules, "aiohttp.web", fake_module_web
    )
    return fake_module_web


@pytest.fixture
def limiter() -> RateLimiter:
    return RateLimiter(max_requests=2, window_seconds=10)


# ----- tests ------------------------------------------------------------------

class TestClientKey:
    def test_returns_remote_when_no_forwarded_header(self, aiohttp_fakes) -> None:
        from gemas_core.core.rate_limit_helpers import client_key
        req = FakeRequest(remote="10.0.0.1")
        assert client_key(req) == "10.0.0.1"

    def test_returns_xff_first_when_present(self, aiohttp_fakes) -> None:
        from gemas_core.core.rate_limit_helpers import client_key
        req = FakeRequest(
            remote="10.0.0.1",
            headers={"X-Forwarded-For": "203.0.113.5, 10.0.0.1"},
        )
        # X-Forwarded-For can be a comma-separated chain; we take the
        # first (leftmost) hop, which is the original client.
        assert client_key(req) == "203.0.113.5"

    def test_falls_back_to_unknown_when_no_remote(self, aiohttp_fakes) -> None:
        from gemas_core.core.rate_limit_helpers import client_key
        req = FakeRequest(remote=None)
        assert client_key(req) == "unknown"

    def test_prefix_is_applied(self, aiohttp_fakes) -> None:
        from gemas_core.core.rate_limit_helpers import client_key
        req = FakeRequest(remote="10.0.0.1")
        assert client_key(req, prefix="chat") == "chat:10.0.0.1"


class TestCheckHttp:
    def test_returns_none_when_allowed(self, aiohttp_fakes, limiter) -> None:
        from gemas_core.core.rate_limit_helpers import check_http
        # 2 allowed, no 429 yet
        assert check_http(limiter, "ip-1") is None
        assert check_http(limiter, "ip-1") is None

    def test_returns_429_when_denied(self, aiohttp_fakes, limiter) -> None:
        from gemas_core.core.rate_limit_helpers import check_http
        # Use up the budget
        check_http(limiter, "ip-1")
        check_http(limiter, "ip-1")
        resp = check_http(limiter, "ip-1")
        assert resp is not None
        assert resp.status == 429

    def test_429_includes_retry_after_header(
        self, aiohttp_fakes, limiter
    ) -> None:
        from gemas_core.core.rate_limit_helpers import check_http
        check_http(limiter, "ip-1")
        check_http(limiter, "ip-1")
        resp = check_http(limiter, "ip-1")
        assert "Retry-After" in resp.headers
        # window_seconds is 10, so retry after 10s
        assert resp.headers["Retry-After"] == "10"

    def test_429_body_shape(self, aiohttp_fakes, limiter) -> None:
        from gemas_core.core.rate_limit_helpers import check_http
        check_http(limiter, "ip-1")
        check_http(limiter, "ip-1")
        resp = check_http(limiter, "ip-1")
        assert resp.body == {
            "error": "rate_limit_exceeded",
            "key": "ip-1",
        }

    def test_per_key_isolation(self, aiohttp_fakes, limiter) -> None:
        from gemas_core.core.rate_limit_helpers import check_http
        check_http(limiter, "ip-1")
        check_http(limiter, "ip-1")
        # ip-1 is blocked
        assert check_http(limiter, "ip-1") is not None
        # ip-2 has its own bucket
        assert check_http(limiter, "ip-2") is None


class TestCheckWs:
    @pytest.mark.asyncio
    async def test_returns_true_when_allowed(
        self, aiohttp_fakes, limiter
    ) -> None:
        from gemas_core.core.rate_limit_helpers import check_ws
        ws = FakeWebSocket()
        assert await check_ws(limiter, ws, "ip-1") is True
        assert ws.sent == []
        assert ws.closed_with is None

    @pytest.mark.asyncio
    async def test_returns_false_when_denied(
        self, aiohttp_fakes, limiter
    ) -> None:
        from gemas_core.core.rate_limit_helpers import check_ws
        ws = FakeWebSocket()
        await check_ws(limiter, ws, "ip-1")
        await check_ws(limiter, ws, "ip-1")
        # 3rd message is over budget
        assert await check_ws(limiter, ws, "ip-1") is False

    @pytest.mark.asyncio
    async def test_sends_error_frame_when_denied(
        self, aiohttp_fakes, limiter
    ) -> None:
        from gemas_core.core.rate_limit_helpers import check_ws
        ws = FakeWebSocket()
        await check_ws(limiter, ws, "ip-1")
        await check_ws(limiter, ws, "ip-1")
        await check_ws(limiter, ws, "ip-1")
        assert ws.sent == [{"type": "error", "text": "rate limit exceeded"}]

    @pytest.mark.asyncio
    async def test_closes_socket_with_1008_when_denied(
        self, aiohttp_fakes, limiter
    ) -> None:
        from gemas_core.core.rate_limit_helpers import check_ws
        ws = FakeWebSocket()
        await check_ws(limiter, ws, "ip-1")
        await check_ws(limiter, ws, "ip-1")
        await check_ws(limiter, ws, "ip-1")
        # 1008 = policy violation (WebSocket close code)
        assert ws.closed_with == 1008


class TestRateLimitMiddleware:
    @pytest.mark.asyncio
    async def test_allows_when_under_budget(
        self, aiohttp_fakes, limiter
    ) -> None:
        from gemas_core.core.rate_limit_helpers import rate_limit_middleware
        mw = rate_limit_middleware(limiter)
        req = FakeRequest(remote="10.0.0.1")
        async def handler(r):
            return FakeResponse(text="ok", status=200)
        resp = await mw(req, handler)
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_returns_429_when_over_budget(
        self, aiohttp_fakes, limiter
    ) -> None:
        from gemas_core.core.rate_limit_helpers import rate_limit_middleware
        mw = rate_limit_middleware(limiter)
        async def handler(r):
            return FakeResponse(text="ok", status=200)
        # 2 allowed, 3rd denied
        await mw(FakeRequest(remote="10.0.0.1"), handler)
        await mw(FakeRequest(remote="10.0.0.1"), handler)
        resp = await mw(FakeRequest(remote="10.0.0.1"), handler)
        assert resp.status == 429

    @pytest.mark.asyncio
    async def test_custom_key_fn(self, aiohttp_fakes, limiter) -> None:
        from gemas_core.core.rate_limit_helpers import rate_limit_middleware
        mw = rate_limit_middleware(
            limiter, key_fn=lambda r: f"user:{r.headers.get('X-User', 'anon')}"
        )
        async def handler(r):
            return FakeResponse(text="ok", status=200)
        req1 = FakeRequest(headers={"X-User": "alice"})
        req2 = FakeRequest(headers={"X-User": "bob"})
        # alice and bob have independent buckets
        await mw(req1, handler)
        await mw(req1, handler)
        # alice is now blocked
        resp = await mw(req1, handler)
        assert resp.status == 429
        # bob is fresh
        resp = await mw(req2, handler)
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_uses_client_key_by_default(
        self, aiohttp_fakes, limiter
    ) -> None:
        from gemas_core.core.rate_limit_helpers import rate_limit_middleware
        mw = rate_limit_middleware(limiter)
        async def handler(r):
            return FakeResponse(text="ok", status=200)
        # Two different remotes — independent buckets
        await mw(FakeRequest(remote="10.0.0.1"), handler)
        await mw(FakeRequest(remote="10.0.0.1"), handler)
        resp = await mw(FakeRequest(remote="10.0.0.1"), handler)
        assert resp.status == 429
        resp = await mw(FakeRequest(remote="10.0.0.2"), handler)
        assert resp.status == 200
