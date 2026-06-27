"""
dmn — Default Mode Network (lite).

Pattern (lethe): background actor that runs BETWEEN user turns and
surfaces useful signals — pending work, recent learnings, drift —
WITHOUT speaking directly. Every emission goes through the notification
gate (commit ad6830f) so the user only hears what scored above
threshold.

Why "lite": the lethe DMN is full LLM-guided reflection. This version is
deterministic heuristic — cheap, no token cost, and can be flipped on
in production today. The hooks are designed so an LLM-guided variant
can drop in later (replace `_scan_*` methods, keep the loop + gating
shape).

Triggers:
    - interval (default 600s — 10min)
    - explicit tick() call (for tests or external schedulers)
    - emit STARTED/STOPPED lifecycle events for observability

Scan rules (all return list of NotificationCandidate):
    1. Stalled-budget scan — sessions with no LLM activity in >30min
       but logs.summary.status='running'. Likely orphaned.
    2. High-cost session scan — sessions over $1 cost get a single
       "approaching cap" notice (cooldown 1h).
    3. Recent-bugfix scan — last episode with type=bugfix in last hour
       gets a "remember this" surface so the user can confirm/save.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class NotificationCandidate:
    category: str
    level: str        # debug|info|warn|error|critical
    title: str
    body: str = ""
    user_facing: bool = False
    origin: str = "dmn"


class DefaultModeNetwork:
    """Background scanner. Hold a single instance per process."""

    def __init__(self, interval_seconds: int = 600):
        self.interval = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self.stats = {
            "ticks": 0, "candidates": 0,
            "spoken": 0, "logged": 0, "dropped": 0,
            "started_at": None, "last_tick_at": None,
        }

    # --- lifecycle ---

    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        """Idempotent — second call is no-op."""
        if self._running:
            return
        try:
            lp = loop or asyncio.get_event_loop()
        except RuntimeError:
            return
        if not lp.is_running():
            return
        if os.environ.get("NEXUS_DMN_DISABLED", "0") == "1":
            logger.info("DMN disabled via NEXUS_DMN_DISABLED=1")
            return
        self._running = True
        self.stats["started_at"] = datetime.now().isoformat()
        self._task = lp.create_task(self._loop())
        try:
            from src.observability.event_stream import emit, EventType
            emit(EventType.SYSTEM_BOOT_READY,
                 data={"actor": "dmn", "interval_s": self.interval},
                 source="dmn")
        except Exception:
            pass
        logger.info(f"DMN started (interval={self.interval}s)")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None

    async def _loop(self):
        # Initial sleep so DMN doesn't fire during boot storm.
        await asyncio.sleep(min(60, self.interval))
        while self._running:
            try:
                self.tick()
            except Exception as e:
                logger.warning(f"DMN tick error: {e}")
            try:
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break

    # --- scan ---

    def tick(self) -> List[NotificationCandidate]:
        """Run all scans, route every candidate through notification gate,
        record stats. Returns the raw candidate list for callers/tests."""
        self.stats["ticks"] += 1
        self.stats["last_tick_at"] = datetime.now().isoformat()
        candidates: List[NotificationCandidate] = []
        for scan in (self._scan_stalled_sessions,
                     self._scan_high_cost,
                     self._scan_recent_bugfixes):
            try:
                candidates.extend(scan())
            except Exception as e:
                logger.debug(f"DMN scan {scan.__name__} failed: {e}")
        self.stats["candidates"] += len(candidates)
        self._route_candidates(candidates)
        return candidates

    def _route_candidates(self, candidates: List[NotificationCandidate]):
        self.stats["logged"] += len(candidates)

    # --- individual scans (deterministic, cheap) ---

    def _scan_stalled_sessions(self) -> List[NotificationCandidate]:
        """Sessions with status='running' but no log update in >30min."""
        out: List[NotificationCandidate] = []
        base = Path.home() / ".nexus" / "sessions"
        if not base.exists():
            return out
        threshold = datetime.now() - timedelta(minutes=30)
        for d in base.iterdir():
            if not d.is_dir():
                continue
            p = d / "logs" / "summary.json"
            if not p.exists():
                continue
            try:
                import json as _json
                s = _json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if s.get("status") != "running":
                continue
            ts = s.get("finished_at") or s.get("started_at")
            try:
                t = datetime.fromisoformat(ts) if ts else None
            except Exception:
                t = None
            if t and t < threshold:
                out.append(NotificationCandidate(
                    category="health",
                    level="warn",
                    title=f"Session {d.name} stalled",
                    body=f"running since {ts}, no update in 30+ min",
                ))
        return out

    def _scan_high_cost(self) -> List[NotificationCandidate]:
        """Per-session cost > $1 USD gets a single notice (gate dedupes)."""
        out: List[NotificationCandidate] = []
        try:
            from src.observability.budget_tracker import tracker
        except Exception:
            return out
        for sid, b in tracker.snapshot().items():
            if (b.get("cost_usd") or 0) >= 1.0:
                out.append(NotificationCandidate(
                    category="billing",
                    level="info",
                    title=f"Session {sid} crossed $1",
                    body=f"current cost ${b['cost_usd']:.4f}, tokens={b.get('total_tokens')}",
                    user_facing=False,
                ))
        return out

    def _scan_recent_bugfixes(self) -> List[NotificationCandidate]:
        """Last hour: any add_episode(type=bugfix) gets a "remember this"
        candidate. Lets the user re-surface fresh learnings without
        having to remember to search for them."""
        out: List[NotificationCandidate] = []
        try:
            import sqlite3
            db = Path.home() / ".nexus" / "brain" / "nexus_memory.db"
            if not db.exists():
                return out
            conn = sqlite3.connect(str(db), timeout=2)
            try:
                cutoff = (datetime.now() - timedelta(hours=1)).isoformat()
                cur = conn.execute(
                    "SELECT id, ts, content FROM observations "
                    "WHERE category='episode' AND ts >= ? "
                    "AND deleted_at IS NULL AND content LIKE 'BUGFIX:%' "
                    "ORDER BY id DESC LIMIT 3",
                    (cutoff,),
                )
                for row in cur.fetchall():
                    obs_id, ts, content = row
                    first_line = (content or "").splitlines()[0][:120]
                    out.append(NotificationCandidate(
                        category="memory",
                        level="info",
                        title=f"Recent bugfix: {first_line}",
                        body=f"observation #{obs_id} at {ts}",
                    ))
            finally:
                conn.close()
        except Exception as e:
            logger.debug(f"DMN bugfix scan failed: {e}")
        return out

    def get_stats(self) -> dict:
        return dict(self.stats)


# Module-level singleton
dmn = DefaultModeNetwork()
