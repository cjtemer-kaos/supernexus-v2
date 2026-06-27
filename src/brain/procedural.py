"""
procedural — Skill invocation memory (engram pattern).

Tracks which (skill, context_hash) combinations succeeded so the agent
can re-use proven patterns instead of re-discovering them.

Schema (added on first use to nexus_memory.db):
    skill_invocations(id, skill, context_hash, context_excerpt,
                       outcome, ts, gem, duration_ms, error)

API:
    record_invocation(skill, context, outcome, ...)  log one call
    suggest_skill(context)                            ranked similar past
    skill_success_rate(skill)                         success/total
"""
from __future__ import annotations

import hashlib
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _db_path() -> Path:
    try:
        from src.bridges.mcp_bridge_server import _MEMORY_DB
        return Path(_MEMORY_DB)
    except Exception:
        return Path.home() / ".nexus" / "brain" / "nexus_memory.db"


def _ctx_hash(context: str) -> str:
    return hashlib.sha1((context or "").encode("utf-8", errors="replace")).hexdigest()[:16]


def _ensure_table(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS skill_invocations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        skill TEXT NOT NULL,
        context_hash TEXT NOT NULL,
        context_excerpt TEXT,
        outcome TEXT NOT NULL,
        ts TEXT NOT NULL,
        gem TEXT DEFAULT '',
        duration_ms INTEGER DEFAULT 0,
        error TEXT DEFAULT ''
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sk_hash ON skill_invocations(context_hash, outcome)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sk_name ON skill_invocations(skill, outcome)")


def _conn() -> Optional[sqlite3.Connection]:
    p = _db_path()
    if not p.parent.exists():
        return None
    c = sqlite3.connect(str(p), timeout=10)
    c.execute("PRAGMA journal_mode=WAL")
    _ensure_table(c)
    return c


def record_invocation(skill: str, context: str, outcome: str,
                      gem: str = "", duration_ms: int = 0,
                      error: str = "") -> Dict:
    """Log one skill invocation. outcome ∈ {success, failure, partial}."""
    conn = _conn()
    if conn is None:
        return {"ok": False, "error": "db unavailable"}
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO skill_invocations (skill, context_hash, context_excerpt, "
            "outcome, ts, gem, duration_ms, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (skill, _ctx_hash(context), (context or "")[:240],
             outcome, datetime.now().isoformat(), gem, duration_ms, error),
        )
        conn.commit()
        return {"ok": True, "id": c.lastrowid}
    finally:
        conn.close()


def suggest_skill(context: str, limit: int = 5) -> List[Dict]:
    """Return skills that previously succeeded on a similar context.
    Ranking: matching context_hash > same-gem success rate > recency."""
    conn = _conn()
    if conn is None:
        return []
    try:
        c = conn.cursor()
        h = _ctx_hash(context)
        # Exact context-hash matches first
        c.execute("""
            SELECT skill, COUNT(*) AS picks,
                   SUM(CASE WHEN outcome='success' THEN 1 ELSE 0 END) AS succ,
                   MAX(ts) AS last_ts
            FROM skill_invocations
            WHERE context_hash=?
            GROUP BY skill ORDER BY succ DESC, picks DESC LIMIT ?
        """, (h, limit))
        rows = c.fetchall()
        out = [{"skill": r[0], "picks": r[1], "successes": r[2],
                "success_rate": round(r[2] / r[1], 3) if r[1] else 0,
                "last_ts": r[3], "match": "exact_context"} for r in rows]
        if len(out) >= limit:
            return out
        # Fallback: global skill success rates for any other skills
        c.execute("""
            SELECT skill, COUNT(*) AS picks,
                   SUM(CASE WHEN outcome='success' THEN 1 ELSE 0 END) AS succ,
                   MAX(ts) AS last_ts
            FROM skill_invocations
            WHERE skill NOT IN ({})
            GROUP BY skill HAVING succ > 0
            ORDER BY succ * 1.0 / picks DESC, picks DESC LIMIT ?
        """.format(",".join("?" * len(out)) or "''"),
        ([r["skill"] for r in out] + [limit - len(out)]))
        rows = c.fetchall()
        out.extend([{"skill": r[0], "picks": r[1], "successes": r[2],
                     "success_rate": round(r[2] / r[1], 3) if r[1] else 0,
                     "last_ts": r[3], "match": "global"} for r in rows])
        return out
    finally:
        conn.close()


def skill_success_rate(skill: str) -> Dict:
    conn = _conn()
    if conn is None:
        return {}
    try:
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*), SUM(CASE WHEN outcome='success' THEN 1 ELSE 0 END)
            FROM skill_invocations WHERE skill=?
        """, (skill,))
        picks, succ = c.fetchone()
        picks = picks or 0
        succ = succ or 0
        return {"skill": skill, "picks": picks, "successes": succ,
                "success_rate": round(succ / picks, 3) if picks else 0.0}
    finally:
        conn.close()
