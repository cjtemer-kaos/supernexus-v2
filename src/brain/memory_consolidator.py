"""
memory_consolidator — Periodic compaction + soft-archive of old observations.

Pattern (engram daily_consolidator): un-bounded observation growth kills
search quality. Every N hours we:
  1. soft-delete obs > age_days old that have zero edges + zero revisions
     (orphan info nobody linked or upserted — usually noise)
  2. for the rest of old obs grouped by topic_key with > 1 revisions:
     keep the latest revision (already an upsert chain), soft-delete prior

Idempotent: re-running the same window doesn't double-process.
Reversible: ALL deletes are soft (deleted_at column). Hard-delete is
opt-in via a separate admin run.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Tunables (env-overridable)
import os
AGE_DAYS = int(os.environ.get("NEXUS_CONSOLIDATE_AGE_DAYS", "30"))
KEEP_NEWEST_PER_TOPIC = int(os.environ.get("NEXUS_CONSOLIDATE_KEEP_PER_TOPIC", "1"))


def _db_path() -> Path:
    """Resolve to the same DB used by mcp_bridge_server (single source of truth)."""
    try:
        from src.bridges.mcp_bridge_server import _MEMORY_DB
        return Path(_MEMORY_DB)
    except Exception:
        return Path.home() / ".nexus" / "brain" / "nexus_memory.db"


def _conn():
    p = _db_path()
    if not p.exists():
        return None
    # Force schema migration first (adds topic_key/deleted_at/edges if missing)
    try:
        from src.bridges import mcp_bridge_server  # noqa: F401
    except Exception:
        pass
    c = sqlite3.connect(str(p), timeout=10)
    c.execute("PRAGMA journal_mode=WAL")
    return c


def consolidate_now(*, age_days: Optional[int] = None) -> Dict:
    """Single consolidation pass. Returns counters.
    Safe to call from a scheduled worker or manually."""
    age = age_days if age_days is not None else AGE_DAYS
    cutoff = (datetime.now() - timedelta(days=age)).isoformat()
    conn = _conn()
    if conn is None:
        return {"ok": False, "error": "db not found"}
    out = {"ok": True, "cutoff": cutoff, "orphans_archived": 0,
           "topic_compressed": 0, "kept_per_topic": KEEP_NEWEST_PER_TOPIC}
    try:
        c = conn.cursor()
        # 1) Orphan archive: old, no topic_key, no edges, no revisions
        c.execute("""
            UPDATE observations
            SET deleted_at = ?
            WHERE deleted_at IS NULL
              AND ts < ?
              AND (topic_key IS NULL OR topic_key = '')
              AND COALESCE(revision_count, 0) = 0
              AND id NOT IN (SELECT DISTINCT from_obs FROM observation_edges)
              AND id NOT IN (SELECT DISTINCT to_obs FROM observation_edges)
        """, (datetime.now().isoformat(), cutoff))
        out["orphans_archived"] = c.rowcount

        # 2) Per topic_key: keep newest N, soft-delete the rest (only old ones)
        c.execute("""
            SELECT topic_key, COUNT(*)
            FROM observations
            WHERE deleted_at IS NULL
              AND topic_key IS NOT NULL AND topic_key != ''
              AND ts < ?
            GROUP BY topic_key
            HAVING COUNT(*) > ?
        """, (cutoff, KEEP_NEWEST_PER_TOPIC))
        crowded = c.fetchall()

        for topic_key, _cnt in crowded:
            c.execute("""
                UPDATE observations
                SET deleted_at = ?
                WHERE deleted_at IS NULL
                  AND topic_key = ?
                  AND ts < ?
                  AND id NOT IN (
                    SELECT id FROM observations
                    WHERE deleted_at IS NULL AND topic_key = ?
                    ORDER BY id DESC LIMIT ?
                  )
            """, (datetime.now().isoformat(), topic_key, cutoff,
                  topic_key, KEEP_NEWEST_PER_TOPIC))
            out["topic_compressed"] += c.rowcount

        conn.commit()
    finally:
        conn.close()

    # Emit observability event (best-effort)
    try:
        from src.observability.event_stream import emit, EventType
        emit(EventType.MEMORY_COMPACTED,
             data={"phase": "consolidator", **out},
             source="memory_consolidator")
    except Exception:
        pass

    logger.info(f"memory_consolidator: {out}")
    return out


def hard_purge_archived(*, older_than_days: int = 90) -> Dict:
    """Hard-delete observations that have been soft-deleted for >N days.
    Admin operation — call manually only. Returns count purged."""
    cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
    conn = _conn()
    if conn is None:
        return {"ok": False, "error": "db not found"}
    try:
        c = conn.cursor()
        c.execute("DELETE FROM observations WHERE deleted_at IS NOT NULL AND deleted_at < ?",
                  (cutoff,))
        n = c.rowcount
        # also clean orphan edges
        c.execute("""
            DELETE FROM observation_edges
            WHERE from_obs NOT IN (SELECT id FROM observations)
               OR to_obs NOT IN (SELECT id FROM observations)
        """)
        edges = c.rowcount
        conn.commit()
        return {"ok": True, "purged_obs": n, "purged_edges": edges, "cutoff": cutoff}
    finally:
        conn.close()
