"""
budget_tracker — Rolling per-session token + cost accounting.

Pattern: openfang MeteringEngine (cost accumulator) + aden-hive
LLMResponse.cost_usd. Builds on top of the LLM_TOKEN_USAGE events
(commit 446363b) and the L1 runtime summaries (commit b7be80c).

Two layers:
    1. SessionBudget — pure in-memory accumulator (per session_id).
       Cheap to instantiate; atomic increment, easy to query.

    2. Soft cap — when NEXUS_MAX_USD_PER_SESSION is set, the tracker
       exposes a `would_exceed()` predicate the LLM call site can
       check BEFORE the next request. (Not auto-aborting — keeps the
       budget cooperative; aggressive enforcement is the caller's call.)

Subscribes to the event bus on first use so any LLM_TOKEN_USAGE event
that carries session_id auto-credits the right bucket.
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class SessionBudget:
    session_id: str
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_update: str = ""
    request_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    # cost-cap state — only meaningful when NEXUS_MAX_USD_PER_SESSION set
    cap_usd: Optional[float] = None
    cap_exceeded: bool = False

    def credit(self, prompt: int, completion: int, cached: int,
               total: int, cost: float):
        self.request_count += 1
        self.prompt_tokens += int(prompt or 0)
        self.completion_tokens += int(completion or 0)
        self.cached_tokens += int(cached or 0)
        self.total_tokens += int(total or 0)
        self.cost_usd = round(self.cost_usd + float(cost or 0.0), 6)
        self.last_update = datetime.now().isoformat()
        if self.cap_usd is not None and self.cost_usd >= self.cap_usd:
            self.cap_exceeded = True

    def to_dict(self) -> Dict:
        return asdict(self)


class BudgetTracker:
    """Singleton holding per-session budgets. Subscribed once to the event
    bus; that subscription runs for the life of the process."""

    def __init__(self):
        self._sessions: Dict[str, SessionBudget] = {}
        self._lock = threading.Lock()
        self._subscriber_task: Optional[asyncio.Task] = None
        self._subscribed = False

    @staticmethod
    def _read_cap() -> Optional[float]:
        raw = os.environ.get("NEXUS_MAX_USD_PER_SESSION", "").strip()
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            logger.warning(f"NEXUS_MAX_USD_PER_SESSION invalid: {raw!r}")
            return None

    def get(self, session_id: str) -> SessionBudget:
        with self._lock:
            b = self._sessions.get(session_id)
            if b is None:
                b = SessionBudget(session_id=session_id, cap_usd=self._read_cap())
                self._sessions[session_id] = b
            return b

    def credit(self, session_id: str, *, prompt: int = 0, completion: int = 0,
               cached: int = 0, total: int = 0, cost: float = 0.0):
        if not session_id:
            return
        b = self.get(session_id)
        with self._lock:
            b.credit(prompt, completion, cached, total, cost)

    def would_exceed(self, session_id: str, extra_cost: float = 0.0) -> bool:
        """True if adding `extra_cost` would push the session over its cap.
        Always False when no cap is set."""
        cap = self._read_cap()
        if cap is None:
            return False
        b = self.get(session_id)
        return (b.cost_usd + max(0.0, extra_cost)) >= cap

    def snapshot(self) -> Dict[str, Dict]:
        with self._lock:
            return {sid: b.to_dict() for sid, b in self._sessions.items()}

    def session_snapshot(self, session_id: str) -> Optional[Dict]:
        with self._lock:
            b = self._sessions.get(session_id)
            return b.to_dict() if b else None

    # --- event-bus subscription ---

    async def _subscribe_loop(self):
        """Long-running consumer for LLM_TOKEN_USAGE events on the bus."""
        try:
            from src.observability.event_stream import bus, EventType
        except Exception as e:
            logger.warning(f"budget_tracker: event_stream unavailable: {e}")
            return
        async for ev in bus.subscribe(
            types={EventType.LLM_TOKEN_USAGE}, label="budget_tracker"
        ):
            sid = ev.session_id or (ev.data or {}).get("session_id")
            if not sid:
                continue
            d = ev.data or {}
            try:
                self.credit(
                    sid,
                    prompt=int(d.get("prompt_tokens") or 0),
                    completion=int(d.get("completion_tokens") or 0),
                    cached=int(d.get("cached_tokens") or 0),
                    total=int(d.get("total_tokens") or 0),
                    cost=float(d.get("cost_usd") or 0.0),
                )
            except Exception as e:
                logger.debug(f"budget_tracker credit failed for {sid}: {e}")

    def ensure_subscribed(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        """Spin up the subscriber task on the given loop (or running loop).
        Idempotent — second call is a no-op."""
        if self._subscribed:
            return
        try:
            lp = loop or asyncio.get_event_loop()
        except RuntimeError:
            return
        if not lp.is_running():
            return
        self._subscriber_task = lp.create_task(self._subscribe_loop())
        self._subscribed = True
        logger.info("budget_tracker: subscribed to LLM_TOKEN_USAGE")


# Module-level singleton
tracker = BudgetTracker()
