"""
taint — Lightweight taint labels for tracking sensitive data flow.

Pattern (openfang TaintLabel/TaintSet): every chunk of data the agent
handles can carry labels indicating its sensitivity. When a labeled
chunk reaches a sink (cloud LLM, outbound HTTP, untrusted gema), the
sink-check refuses or warns.

Lite version: ContextVar-backed set of active labels. The agent loop
sets labels on input from sensitive sources (user_pii, secret_env,
private_repo). Sinks check before allowing the operation.

Labels (extensible, plain strings):
    user_pii          personally identifiable info from the user
    secret_env        loaded from env vars / .env
    private_repo      file content from a private repo
    medical, legal    domain-specific sensitive categories
    untrusted_input   web fetch result, unparsed file, MCP tool output

Use:
    from src.security.taint import current_taints, add_taint, requires_clean

    add_taint("secret_env")
    requires_clean("llm.cloud")  # raises TaintViolation if any label set
"""
from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import FrozenSet, Iterable

logger = logging.getLogger(__name__)


# Per-task taint set. ContextVar so it inherits across asyncio tasks.
_taints: ContextVar[FrozenSet[str]] = ContextVar("nexus_taints", default=frozenset())


class TaintViolation(Exception):
    """Raised by requires_clean when a sink is reached with active taints."""


# Sink → labels that block it. None = block ALL labels (any taint = denied).
SINK_POLICY = {
    "llm.cloud":       None,  # never let any user_pii / secret_env leave
    "net.fetch":       {"secret_env", "user_pii"},
    "memory.write":    set(),  # writes OK — those are local sqlite anyway
    "shell.exec":      {"untrusted_input"},  # don't shell-exec random web text
    "mcp.call":        {"secret_env"},
}


def add_taint(label: str) -> FrozenSet[str]:
    cur = _taints.get()
    new = cur | {label.lower()}
    _taints.set(new)
    return new


def add_taints(labels: Iterable[str]) -> FrozenSet[str]:
    cur = _taints.get()
    new = cur | {label.lower() for label in labels if label}
    _taints.set(new)
    return new


def current_taints() -> FrozenSet[str]:
    return _taints.get()


def clear_taints() -> None:
    _taints.set(frozenset())


def requires_clean(sink: str) -> None:
    """Raise TaintViolation if the current task has taints that block `sink`.
    Sinks not in SINK_POLICY are permissive (no taint check). Emits SEC
    event on every block so audit picks it up."""
    cur = _taints.get()
    if not cur:
        return
    policy = SINK_POLICY.get(sink)
    if policy is None and sink in SINK_POLICY:
        # explicit "block all"
        violating = cur
    elif policy is None:
        return  # unknown sink → permissive
    else:
        violating = cur & policy
    if not violating:
        return
    try:
        from src.observability.event_stream import emit, EventType
        from src.observability.context import current_session_id, current_request_id
        emit(EventType.SEC_INJECTION_BLOCKED,
             data={"kind": "taint", "sink": sink,
                   "active_taints": sorted(cur),
                   "violating": sorted(violating)},
             session_id=current_session_id(),
             request_id=current_request_id(),
             source="taint")
    except Exception:
        pass
    logger.warning(f"taint block: sink={sink} active={sorted(cur)} violating={sorted(violating)}")
    raise TaintViolation(
        f"sink '{sink}' blocked by active taints: {sorted(violating)}"
    )


def with_taints(labels: Iterable[str]):
    """Decorator: ensure `labels` are added to the taint set inside the
    decorated function. Useful for wrapping ingesters of sensitive data
    (web_fetch result -> add untrusted_input, etc.)."""
    labels = list(labels)
    def deco(fn):
        import functools
        @functools.wraps(fn)
        async def aw(*a, **kw):
            add_taints(labels)
            return await fn(*a, **kw)
        @functools.wraps(fn)
        def sw(*a, **kw):
            add_taints(labels)
            return fn(*a, **kw)
        import inspect
        return aw if inspect.iscoroutinefunction(fn) else sw
    return deco
