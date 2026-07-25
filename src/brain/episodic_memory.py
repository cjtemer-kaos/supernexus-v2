"""
Episodic Memory — Engram-inspired structured episodic memory system.

Inspired by Lethe/engram patterns: each episode captures what happened,
why it happened, where it occurred, and what was learned — preserving
causality, not just facts.

Schema (SQLite + FTS5):
    episodes(id, what, why, where, learned, category, importance,
             access_count, last_accessed, created_at, tags, topic_key)

    episodes_fts(what, why, where, learned, tags) — FTS5 virtual table

Singleton access via EpisodicMemory.instance().
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Defaults ────────────────────────────────────────────────────────────

NEXUS_BRAIN_DIR: Path = Path(
    os.environ.get("NEXUS_BRAIN", str(Path.home() / ".nexus" / "brain"))
)
EPISODES_DB: Path = NEXUS_BRAIN_DIR / "episodes.db"


class Category(str, Enum):
    """Episode storage categories."""
    WORK = "work"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    SENSORY = "sensory"
    SCRATCHPAD = "scratchpad"


@dataclass
class Episode:
    """Structured episodic memory unit."""
    id: int = 0
    what: str = ""
    why: str = ""
    where: str = ""
    learned: str = ""
    category: Category = Category.EPISODIC
    importance: float = 0.5
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)
    topic_key: str = ""

    # ── Serialisation helpers ────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Convert to plain dict for JSON / API consumption."""
        d = asdict(self)
        d["category"] = self.category.value
        d["last_accessed"] = self.last_accessed.isoformat()
        d["created_at"] = self.created_at.isoformat()
        d["tags"] = self.tags
        return d

    @classmethod
    def from_row(cls, row: tuple, tags: List[str] | None = None) -> "Episode":
        """Reconstruct an Episode from a SQLite row.

        Expected row order:
            id, what, why, where, learned, category, importance,
            access_count, last_accessed, created_at, topic_key
        """
        return cls(
            id=row[0],
            what=row[1] or "",
            why=row[2] or "",
            where=row[3] or "",
            learned=row[4] or "",
            category=Category(row[5]) if row[5] else Category.EPISODIC,
            importance=row[6] if row[6] is not None else 0.5,
            access_count=row[7] if row[7] is not None else 0,
            last_accessed=_parse_dt(row[8]),
            created_at=_parse_dt(row[9]),
            topic_key=row[10] or "",
            tags=tags or [],
        )


# ── Helpers ─────────────────────────────────────────────────────────────

def _parse_dt(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except Exception:
            pass
    return datetime.utcnow()


def _dt_iso(dt: datetime) -> str:
    return dt.isoformat()


# ── Database layer ──────────────────────────────────────────────────────

class _DB:
    """Thin SQLite wrapper — WAL, busy_timeout, table creation."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_tables()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), timeout=30)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _ensure_tables(self):
        conn = self._get_conn()
        c = conn.cursor()

        # Main episodes table
        c.execute("""CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            what TEXT NOT NULL DEFAULT '',
            why TEXT NOT NULL DEFAULT '',
            where_ TEXT NOT NULL DEFAULT '',
            learned TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT 'episodic',
            importance REAL NOT NULL DEFAULT 0.5,
            access_count INTEGER NOT NULL DEFAULT 0,
            last_accessed TEXT NOT NULL,
            created_at TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '[]',
            topic_key TEXT NOT NULL DEFAULT ''
        )""")

        # Indexes for common lookups
        c.execute("CREATE INDEX IF NOT EXISTS idx_ep_category ON episodes(category)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ep_importance ON episodes(importance DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ep_topic ON episodes(topic_key)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ep_created ON episodes(created_at DESC)")

        conn.commit()

        # FTS5 virtual table (created outside transaction)
        self._ensure_fts()

    def _ensure_fts(self):
        """Create FTS5 virtual table for full-text search."""
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(
                    what, why, where_col, learned, tags,
                    content='episodes',
                    content_rowid='id',
                    tokenize='porter unicode61'
                )
            """)
            conn.commit()
        except Exception as e:
            # FTS5 might already exist with different schema — log and continue
            logger.debug(f"FTS5 table creation note: {e}")

    def _rebuild_fts(self):
        """Rebuild FTS index from episodes table."""
        conn = self._get_conn()
        try:
            conn.execute("INSERT INTO episodes_fts(episodes_fts) VALUES('rebuild')")
            conn.commit()
        except Exception as e:
            logger.debug(f"FTS5 rebuild note: {e}")

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


# ── Singleton ───────────────────────────────────────────────────────────

class EpisodicMemory:
    """Engram-inspired episodic memory backed by SQLite + FTS5.

    Usage:
        mem = EpisodicMemory.instance()
        ep = mem.create_episode(what="Fixed auth bug", why="Login failing", ...)
        results = mem.search_episodes("auth bug")
    """

    _instance: Optional["EpisodicMemory"] = None

    def __init__(self, db_path: Optional[Path] = None):
        self._db = _DB(db_path or EPISODES_DB)

    @classmethod
    def instance(cls, db_path: Optional[Path] = None) -> "EpisodicMemory":
        """Return the singleton (creates on first call)."""
        if cls._instance is None:
            cls._instance = cls(db_path)
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton (useful for testing)."""
        if cls._instance:
            cls._instance._db.close()
            cls._instance = None

    # ── CRUD ────────────────────────────────────────────────────────

    def create_episode(
        self,
        what: str,
        why: str = "",
        where: str = "",
        learned: str = "",
        category: Category | str = Category.EPISODIC,
        importance: float = 0.5,
        tags: List[str] | None = None,
        topic_key: str = "",
    ) -> Episode:
        """Create and persist a new episode. Returns the created Episode."""
        if isinstance(category, str):
            try:
                category = Category(category)
            except ValueError:
                category = Category.EPISODIC

        importance = max(0.0, min(1.0, importance))
        tags = tags or []
        now = _dt_iso(datetime.utcnow())

        conn = self._db._get_conn()
        c = conn.cursor()
        c.execute(
            """INSERT INTO episodes
               (what, why, where_, learned, category, importance,
                access_count, last_accessed, created_at, tags, topic_key)
               VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)""",
            (what, why, where, learned, category.value,
             importance, now, now, json.dumps(tags), topic_key),
        )
        row_id = c.lastrowid
        conn.commit()

        # Insert into FTS
        self._fts_upsert(row_id, what, why, where, learned, tags)

        ep = Episode(
            id=row_id, what=what, why=why, where=where, learned=learned,
            category=category, importance=importance, access_count=0,
            last_accessed=datetime.utcnow(), created_at=datetime.utcnow(),
            tags=tags, topic_key=topic_key,
        )
        logger.debug(f"Created episode #{row_id}: {what[:60]}")
        return ep

    def get_episode(self, episode_id: int) -> Optional[Episode]:
        """Fetch a single episode by ID. Bumps access_count."""
        conn = self._db._get_conn()
        c = conn.cursor()
        c.execute(
            "SELECT id, what, why, where_, learned, category, importance, "
            "access_count, last_accessed, created_at, topic_key "
            "FROM episodes WHERE id = ?",
            (episode_id,),
        )
        row = c.fetchone()
        if not row:
            return None

        # Parse tags
        c.execute("SELECT tags FROM episodes WHERE id = ?", (episode_id,))
        tags_row = c.fetchone()
        tags = json.loads(tags_row[0]) if tags_row and tags_row[0] else []

        # Bump access_count + update last_accessed
        now = _dt_iso(datetime.utcnow())
        c.execute(
            "UPDATE episodes SET access_count = access_count + 1, "
            "last_accessed = ? WHERE id = ?",
            (now, episode_id),
        )
        conn.commit()

        ep = Episode.from_row(row, tags=tags)
        ep.access_count += 1
        ep.last_accessed = datetime.utcnow()
        return ep

    def update_episode(self, episode_id: int, **fields) -> Optional[Episode]:
        """Update specific fields on an episode. Returns updated Episode or None."""
        allowed = {"what", "why", "where", "learned", "category",
                    "importance", "tags", "topic_key"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get_episode(episode_id)

        conn = self._db._get_conn()
        c = conn.cursor()

        # Check exists
        c.execute("SELECT id FROM episodes WHERE id = ?", (episode_id,))
        if not c.fetchone():
            return None

        set_clauses = []
        values = []
        for k, v in updates.items():
            col = "where_" if k == "where" else k
            if k == "category" and isinstance(v, str):
                try:
                    v = Category(v).value
                except ValueError:
                    pass
            if k == "tags" and isinstance(v, list):
                v = json.dumps(v)
            if k == "importance":
                v = max(0.0, min(1.0, v))
            set_clauses.append(f"{col} = ?")
            values.append(v)

        values.append(episode_id)
        c.execute(
            f"UPDATE episodes SET {', '.join(set_clauses)} WHERE id = ?",
            tuple(values),
        )
        conn.commit()

        # Rebuild FTS for this row
        row = c.execute(
            "SELECT what, why, where_, learned, tags FROM episodes WHERE id = ?",
            (episode_id,),
        ).fetchone()
        if row:
            tags = json.loads(row[4]) if row[4] else []
            self._fts_upsert(episode_id, row[0], row[1], row[2], row[3], tags)

        return self.get_episode(episode_id)

    def upsert_by_topic(self, topic_key: str, episode: Episode) -> Episode:
        """Upsert: if an episode with this topic_key exists, update it;
        otherwise create a new one with that topic_key."""
        conn = self._db._get_conn()
        c = conn.cursor()
        c.execute(
            "SELECT id FROM episodes WHERE topic_key = ? ORDER BY id DESC LIMIT 1",
            (topic_key,),
        )
        row = c.fetchone()

        if row:
            # Update existing
            self.update_episode(
                row[0],
                what=episode.what,
                why=episode.why,
                where=episode.where,
                learned=episode.learned,
                category=episode.category,
                importance=episode.importance,
                tags=episode.tags,
            )
            return self.get_episode(row[0])
        else:
            # Create new with the given topic_key
            return self.create_episode(
                what=episode.what,
                why=episode.why,
                where=episode.where,
                learned=episode.learned,
                category=episode.category,
                importance=episode.importance,
                tags=episode.tags,
                topic_key=topic_key,
            )

    def delete_episode(self, episode_id: int) -> bool:
        """Hard-delete an episode by ID."""
        conn = self._db._get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM episodes WHERE id = ?", (episode_id,))
        deleted = c.rowcount > 0
        if deleted:
            try:
                c.execute(
                    "DELETE FROM episodes_fts WHERE rowid = ?", (episode_id,)
                )
            except Exception:
                pass
        conn.commit()
        return deleted

    # ── Search ──────────────────────────────────────────────────────

    def search_episodes(
        self,
        query: str,
        category: Category | str | None = None,
        min_importance: float = 0,
        limit: int = 10,
    ) -> List[Episode]:
        """Full-text search via FTS5 with optional category / importance filters.

        Falls back to LIKE-based search if FTS5 is unavailable.
        """
        conn = self._db._get_conn()
        c = conn.cursor()

        results: List[Episode] = []

        # Try FTS5 first
        try:
            fts_query = self._build_fts_query(query)
            sql = (
                "SELECT e.id, e.what, e.why, e.where_, e.learned, e.category, "
                "e.importance, e.access_count, e.last_accessed, e.created_at, "
                "e.topic_key, e.tags "
                "FROM episodes e "
                "JOIN episodes_fts f ON e.id = f.rowid "
                "WHERE episodes_fts MATCH ? "
                "AND e.importance >= ? "
            )
            params: list = [fts_query, min_importance]

            if category:
                cat_val = category.value if isinstance(category, Category) else category
                sql += "AND e.category = ? "
                params.append(cat_val)

            sql += "ORDER BY rank LIMIT ?"
            params.append(limit)

            c.execute(sql, tuple(params))
            rows = c.fetchall()
            for r in rows:
                tags = json.loads(r[11]) if r[11] else []
                ep = Episode.from_row(r[:11], tags=tags)
                results.append(ep)
        except Exception as e:
            logger.debug(f"FTS5 search failed, falling back to LIKE: {e}")

        # Fallback: LIKE-based search
        if not results:
            sql = (
                "SELECT id, what, why, where_, learned, category, importance, "
                "access_count, last_accessed, created_at, topic_key "
                "FROM episodes "
                "WHERE (what LIKE ? OR why LIKE ? OR where_ LIKE ? OR learned LIKE ?) "
                "AND importance >= ? "
            )
            like = f"%{query}%"
            params = [like, like, like, like, min_importance]

            if category:
                cat_val = category.value if isinstance(category, Category) else category
                sql += "AND category = ? "
                params.append(cat_val)

            sql += "ORDER BY importance DESC, created_at DESC LIMIT ?"
            params.append(limit)

            c.execute(sql, tuple(params))
            rows = c.fetchall()
            for r in rows:
                # Fetch tags separately
                c2 = conn.cursor()
                c2.execute("SELECT tags FROM episodes WHERE id = ?", (r[0],))
                tags_row = c2.fetchone()
                tags = json.loads(tags_row[0]) if tags_row and tags_row[0] else []
                ep = Episode.from_row(r, tags=tags)
                results.append(ep)

        return results

    def _build_fts_query(self, query: str) -> str:
        """Build an FTS5 MATCH query from user input.

        Handles quoted phrases, simple terms, and falls back gracefully.
        """
        query = query.strip()
        if not query:
            return '""'
        # If already has quotes, use as-is
        if '"' in query:
            return query
        # Split into terms, join with implicit AND
        terms = query.split()
        if len(terms) == 1:
            return f'"{terms[0]}"'
        return " ".join(f'"{t}"' for t in terms)

    def _fts_upsert(
        self, row_id: int, what: str, why: str, where: str,
        learned: str, tags: List[str],
    ):
        """Insert or replace into the FTS5 index."""
        conn = self._db._get_conn()
        try:
            # Delete old FTS entry if exists
            conn.execute(
                "DELETE FROM episodes_fts WHERE rowid = ?", (row_id,)
            )
            conn.execute(
                "INSERT INTO episodes_fts(rowid, what, why, where_col, learned, tags) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (row_id, what or "", why or "", where or "",
                 learned or "", " ".join(tags)),
            )
            conn.commit()
        except Exception as e:
            logger.debug(f"FTS upsert for row {row_id}: {e}")

    # ── Importance decay ────────────────────────────────────────────

    def decay_importance(self, decay_rate: float = 0.95, min_floor: float = 0.05):
        """Apply exponential decay to importance scores.

        Recently-accessed episodes decay slower (their access_count acts
        as a freshness signal). Called periodically to simulate forgetting.
        """
        conn = self._db._get_conn()
        c = conn.cursor()

        # Episodes accessed in the last 24h get a bonus (decay less)
        recent_cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()

        # Decay recent: multiply by decay_rate^0.5 (slower)
        c.execute(
            "UPDATE episodes SET importance = MAX(?, importance * ?) "
            "WHERE last_accessed >= ?",
            (min_floor, decay_rate ** 0.5, recent_cutoff),
        )
        recent_affected = c.rowcount

        # Decay old: multiply by decay_rate (full)
        c.execute(
            "UPDATE episodes SET importance = MAX(?, importance * ?) "
            "WHERE last_accessed < ?",
            (min_floor, decay_rate, recent_cutoff),
        )
        old_affected = c.rowcount

        conn.commit()
        logger.debug(
            f"Importance decay applied: {recent_affected} recent, "
            f"{old_affected} old episodes"
        )
        return {"recent_affected": recent_affected, "old_affected": old_affected}

    # ── Stats ───────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Return statistics about the episodic memory store."""
        conn = self._db._get_conn()
        c = conn.cursor()

        stats: Dict[str, Any] = {}

        c.execute("SELECT COUNT(*) FROM episodes")
        stats["total_episodes"] = c.fetchone()[0]

        c.execute("SELECT category, COUNT(*) FROM episodes GROUP BY category")
        stats["by_category"] = {row[0]: row[1] for row in c.fetchall()}

        c.execute("SELECT AVG(importance), MIN(importance), MAX(importance) FROM episodes")
        row = c.fetchone()
        stats["avg_importance"] = round(row[0], 3) if row[0] else 0
        stats["min_importance"] = row[1] if row[1] is not None else 0
        stats["max_importance"] = row[2] if row[2] is not None else 0

        c.execute("SELECT SUM(access_count) FROM episodes")
        stats["total_accesses"] = c.fetchone()[0] or 0

        c.execute("SELECT COUNT(*) FROM episodes WHERE access_count > 0")
        stats["accessed_at_least_once"] = c.fetchone()[0]

        c.execute(
            "SELECT COUNT(*) FROM episodes WHERE last_accessed >= ?",
            ((datetime.utcnow() - timedelta(hours=24)).isoformat(),),
        )
        stats["accessed_last_24h"] = c.fetchone()[0]

        c.execute(
            "SELECT COUNT(*) FROM episodes WHERE last_accessed >= ?",
            ((datetime.utcnow() - timedelta(days=7)).isoformat(),),
        )
        stats["accessed_last_7d"] = c.fetchone()[0]

        # Distinct tags count
        c.execute("SELECT tags FROM episodes WHERE tags != '[]' AND tags != ''")
        all_tags: set = set()
        for row in c.fetchall():
            try:
                all_tags.update(json.loads(row[0]))
            except Exception:
                pass
        stats["unique_tags"] = len(all_tags)

        return stats

    # ── Bulk / maintenance ──────────────────────────────────────────

    def list_episodes(
        self,
        category: Category | str | None = None,
        order_by: str = "created_at DESC",
        limit: int = 50,
        offset: int = 0,
    ) -> List[Episode]:
        """List episodes with optional category filter and pagination."""
        conn = self._db._get_conn()
        c = conn.cursor()

        # Validate order_by to prevent injection
        allowed_orders = {
            "created_at DESC", "created_at ASC",
            "importance DESC", "importance ASC",
            "last_accessed DESC", "last_accessed ASC",
            "access_count DESC", "access_count ASC",
        }
        if order_by not in allowed_orders:
            order_by = "created_at DESC"

        sql = (
            "SELECT id, what, why, where_, learned, category, importance, "
            "access_count, last_accessed, created_at, topic_key "
            "FROM episodes "
        )
        params: list = []

        if category:
            cat_val = category.value if isinstance(category, Category) else category
            sql += "WHERE category = ? "
            params.append(cat_val)

        sql += f"ORDER BY {order_by} LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        c.execute(sql, tuple(params))
        rows = c.fetchall()
        results = []
        for r in rows:
            c2 = conn.cursor()
            c2.execute("SELECT tags FROM episodes WHERE id = ?", (r[0],))
            tags_row = c2.fetchone()
            tags = json.loads(tags_row[0]) if tags_row and tags_row[0] else []
            results.append(Episode.from_row(r, tags=tags))
        return results

    def rebuild_fts_index(self):
        """Force a full FTS5 rebuild from the episodes table."""
        self._db._rebuild_fts()
        logger.info("FTS5 index rebuilt")

    def close(self):
        """Close the underlying DB connection."""
        self._db.close()
