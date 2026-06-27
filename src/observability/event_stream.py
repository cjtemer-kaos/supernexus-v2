"""
event_stream — Async pub/sub formal event bus for NEXUS observability.

Pattern: aden-hive core/framework/host/event_bus.py (40+ enumerated types,
in-process broadcast, opt-in JSONL persistence, OTel-aligned fields).

Design constraints:
    - Non-blocking publishers: fire-and-forget; slow subscribers must
      not stall the main loop. Each subscriber has its own bounded queue.
    - Coexists with src/core/event_bus.py (legacy 9-type bus); does NOT
      replace it. New subsystems target this; legacy stays untouched
      until callers migrate.
    - Zero overhead when no subscribers + persist disabled.

Quickstart:

    from src.observability.event_stream import bus, EventType, emit

    # Subscribers (SSE, audit, dashboard):
    async for ev in bus.subscribe(types={EventType.LLM_REQUEST_FAILED}):
        ...

    # Producers (anywhere):
    emit(EventType.TOOL_CALL_STARTED,
         data={"name": "search", "args": args},
         request_id=request["request_id"])

Env vars:
    NEXUS_EVENT_LOG=1    Persist every event to ~/.nexus/events/<date>.jsonl
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Iterable, Optional, Set, List

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """40+ types organized by subsystem. Add new entries here as needed —
    string values are stable, the bus does not break if new types appear."""

    # === Lifecycle ===============================================
    SYSTEM_BOOT_START = "system.boot.start"
    SYSTEM_BOOT_READY = "system.boot.ready"
    SYSTEM_BOOT_FAILED = "system.boot.failed"
    SYSTEM_SHUTDOWN_START = "system.shutdown.start"
    SYSTEM_SHUTDOWN_DONE = "system.shutdown.done"

    # === Session / chat ==========================================
    CHAT_REQUEST_RECEIVED = "chat.request.received"
    CHAT_RESPONSE_SENT = "chat.response.sent"
    CHAT_ERROR = "chat.error"
    SESSION_CREATED = "session.created"
    SESSION_RESUMED = "session.resumed"
    SESSION_EXPIRED = "session.expired"

    # === Routing / gemas =========================================
    ROUTING_DECIDED = "routing.decided"
    ROUTING_FALLBACK = "routing.fallback"
    GEMA_LOADED = "gema.loaded"
    GEMA_LOAD_FAILED = "gema.load_failed"
    GEMA_LOAD_REFUSED_SCAN = "gema.load_refused_scan"
    GEMA_EXECUTED = "gema.executed"

    # === LLM provider ============================================
    LLM_REQUEST_STARTED = "llm.request.started"
    LLM_REQUEST_COMPLETED = "llm.request.completed"
    LLM_REQUEST_FAILED = "llm.request.failed"
    LLM_FAILOVER = "llm.failover"
    LLM_TOKEN_USAGE = "llm.token.usage"

    # === Tools / agent loop ======================================
    TOOL_CALL_STARTED = "tool.call.started"
    TOOL_CALL_COMPLETED = "tool.call.completed"
    TOOL_CALL_FAILED = "tool.call.failed"
    TOOL_LOOP_DETECTED = "tool.loop.detected"
    AGENT_ITERATION = "agent.iteration"
    AGENT_MAX_ITER_HIT = "agent.max_iter.hit"

    # === MCP =====================================================
    MCP_SERVER_REGISTERED = "mcp.server.registered"
    MCP_SERVER_STARTED = "mcp.server.started"
    MCP_SERVER_FAILED = "mcp.server.failed"
    MCP_TOOL_DISCOVERED = "mcp.tool.discovered"
    MCP_AUTODISCOVERED = "mcp.autodiscovered"

    # === Memory ==================================================
    MEMORY_OBSERVATION_ADDED = "memory.observation.added"
    MEMORY_OBSERVATION_UPSERTED = "memory.observation.upserted"
    MEMORY_OBSERVATION_DEDUPED = "memory.observation.deduped"
    MEMORY_OBSERVATION_DELETED = "memory.observation.deleted"
    MEMORY_EPISODE_ADDED = "memory.episode.added"
    MEMORY_COMPACTED = "memory.compacted"

    # === Health / supervision ====================================
    HEALTH_DEGRADED = "health.degraded"
    HEALTH_RECOVERED = "health.recovered"
    WORKER_STALLED = "worker.stalled"
    WORKER_RECOVERED = "worker.recovered"

    # === Security ================================================
    SEC_AUTH_FAILED = "sec.auth.failed"
    SEC_INJECTION_BLOCKED = "sec.injection.blocked"
    SEC_RATE_LIMITED = "sec.rate.limited"

    # === Custom / extension ======================================
    CUSTOM = "custom"


@dataclass(frozen=True)
class Event:
    """Immutable event record. request_id ties events across the request
    lifecycle (matches X-Request-Id middleware)."""
    id: str
    type: EventType
    ts: str
    data: Dict[str, Any]
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    source: Optional[str] = None  # subsystem name, free-form

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "ts": self.ts,
            "data": self.data,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "source": self.source,
        }


@dataclass
class _Subscriber:
    queue: asyncio.Queue
    types: Optional[Set[EventType]]  # None = all types
    label: str


class EventStream:
    """In-process pub/sub. One singleton instance per process (use `bus`)."""

    def __init__(self, queue_size: int = 1024):
        self._subs: List[_Subscriber] = []
        self._queue_size = queue_size
        self._counter = 0
        self._persist_path: Optional[Path] = None
        self._persist_fp = None
        self._lock = asyncio.Lock()
        # Honor env on first emit instead of __init__ to be safe in test envs.
        self._persist_checked = False

    # --- producer side ---------------------------------------------

    def _maybe_open_persist(self):
        if self._persist_checked:
            return
        self._persist_checked = True
        if os.environ.get("NEXUS_EVENT_LOG", "0") != "1":
            return
        try:
            today = datetime.now().strftime("%Y%m%d")
            d = Path.home() / ".nexus" / "events"
            d.mkdir(parents=True, exist_ok=True)
            self._persist_path = d / f"{today}.jsonl"
            # Append mode, line-buffered, utf-8
            self._persist_fp = open(self._persist_path, "a", encoding="utf-8", buffering=1)
            logger.info(f"event_stream: persisting to {self._persist_path}")
        except Exception as e:
            logger.warning(f"event_stream: persist setup failed: {e}")

    def emit(self, event_type: EventType, data: Optional[Dict[str, Any]] = None,
             *, request_id: Optional[str] = None,
             session_id: Optional[str] = None,
             source: Optional[str] = None) -> Event:
        """Synchronous fire-and-forget publish. Returns the constructed
        event for callers that want the id for correlation."""
        self._counter += 1
        self._maybe_open_persist()
        ev = Event(
            id=f"ev_{self._counter:08d}_{uuid.uuid4().hex[:6]}",
            type=event_type,
            ts=datetime.now().isoformat(),
            data=data or {},
            request_id=request_id,
            session_id=session_id,
            source=source,
        )
        # 1) persist (best-effort)
        if self._persist_fp is not None:
            try:
                self._persist_fp.write(json.dumps(ev.to_dict(), ensure_ascii=False) + "\n")
            except Exception:
                pass  # never break producer on persist failure

        # 2) deliver to subscribers (non-blocking)
        if not self._subs:
            return ev
        for sub in self._subs:
            if sub.types is not None and ev.type not in sub.types:
                continue
            try:
                sub.queue.put_nowait(ev)
            except asyncio.QueueFull:
                # Slow subscriber — drop, log once per minute would be nice
                logger.debug(f"event_stream: queue full for sub '{sub.label}', dropping")
        return ev

    # --- consumer side ---------------------------------------------

    async def subscribe(
        self,
        types: Optional[Iterable[EventType]] = None,
        *,
        label: str = "anonymous",
    ) -> AsyncIterator[Event]:
        """Async generator yielding Events. `types=None` yields all types.

        Usage:
            async for ev in bus.subscribe(types={EventType.CHAT_ERROR}):
                await ws.send_json(ev.to_dict())
        """
        sub = _Subscriber(
            queue=asyncio.Queue(maxsize=self._queue_size),
            types=set(types) if types else None,
            label=label,
        )
        async with self._lock:
            self._subs.append(sub)
        logger.debug(f"event_stream: subscribed '{label}' types={types}")
        try:
            while True:
                ev = await sub.queue.get()
                yield ev
        finally:
            async with self._lock:
                if sub in self._subs:
                    self._subs.remove(sub)
            logger.debug(f"event_stream: unsubscribed '{label}'")

    # --- introspection ---------------------------------------------

    def stats(self) -> Dict[str, Any]:
        return {
            "subscribers": len(self._subs),
            "events_emitted": self._counter,
            "persist_enabled": self._persist_path is not None,
            "persist_path": str(self._persist_path) if self._persist_path else None,
            "subscriber_labels": [s.label for s in self._subs],
        }


# Module-level singleton — import this, don't instantiate.
bus = EventStream()


def emit(event_type: EventType, data: Optional[Dict[str, Any]] = None,
         *, request_id: Optional[str] = None,
         session_id: Optional[str] = None,
         source: Optional[str] = None) -> Event:
    """Convenience top-level emit() that targets the singleton bus."""
    return bus.emit(event_type, data,
                    request_id=request_id, session_id=session_id, source=source)
