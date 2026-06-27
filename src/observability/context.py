"""
context — Request-scoped ContextVars for observability.

Pattern: aden-hive uses an OpenTelemetry context for trace/span/session
correlation. We do the same with stdlib `contextvars` — zero deps, works
across asyncio tasks (each task inherits the current context).

Producers (request handlers, hooks) call `set_session_id(...)` and
`set_request_id(...)`. Consumers (event emitters, LLM provider) call
`current_session_id()` / `current_request_id()` to get whatever was
set by the calling chain.

If nothing was set, getters return None — safe default for places that
shouldn't be tied to a session.
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

_session_id: ContextVar[Optional[str]] = ContextVar("nexus_session_id", default=None)
_request_id: ContextVar[Optional[str]] = ContextVar("nexus_request_id", default=None)
_gema:       ContextVar[Optional[str]] = ContextVar("nexus_current_gema", default=None)


def set_session_id(sid: Optional[str]) -> None:
    _session_id.set(sid or None)


def current_session_id() -> Optional[str]:
    return _session_id.get()


def set_request_id(rid: Optional[str]) -> None:
    _request_id.set(rid or None)


def current_request_id() -> Optional[str]:
    return _request_id.get()


def set_current_gema(name: Optional[str]) -> None:
    _gema.set(name or None)


def current_gema() -> Optional[str]:
    return _gema.get()
