#!/usr/bin/env python3
"""
Persistent Memory Skill - Memoria Persistente Avanzada para Nexus IA
Implementa el protocolo de memoria persistente con FTS5.
"""

import hashlib
import sqlite3
import json
from datetime import datetime
from pathlib import Path

# Point to the canonical project DB (same as mcp_bridge_server)
try:
    from src.bridges.mcp_bridge_server import _MEMORY_DB
    DB_PATH = Path(_MEMORY_DB)
except Exception:
    DB_PATH = Path.home() / ".nexus" / "brain" / "nexus_memory.db"


def _content_hash(content: str, category: str, project: str) -> str:
    h = hashlib.sha1()
    h.update(content.encode("utf-8", errors="replace"))
    h.update(b"|")
    h.update(category.encode("utf-8", errors="replace"))
    h.update(b"|")
    h.update(project.encode("utf-8", errors="replace"))
    return h.hexdigest()[:16]


class PersistentMemorySkill:
    def __init__(self):
        self.name = "persistent_memory"
        self.description = "Persistent memory for AI agents (Observations, Decisions, Preferences)"
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(DB_PATH), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with self._get_conn() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS observations "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, content TEXT, "
                "category TEXT, project TEXT, metadata TEXT)"
            )
            # Additive V2 migration (same columns as mcp_bridge_server)
            existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(observations)")}
            v2_cols = [
                ("topic_key", "TEXT"),
                ("deleted_at", "TEXT"),
                ("revision_count", "INTEGER DEFAULT 0"),
                ("updated_at", "TEXT"),
                ("content_hash", "TEXT"),
            ]
            for col_name, col_type in v2_cols:
                if col_name not in existing_cols:
                    conn.execute(f"ALTER TABLE observations ADD COLUMN {col_name} {col_type}")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_obs_topic ON observations(topic_key, project, category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_obs_deleted ON observations(deleted_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_obs_hash ON observations(content_hash, project, ts)")
            # FTS5
            try:
                conn.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts "
                    "USING fts5(content, category, project, content='observations', content_rowid='id')"
                )
                conn.execute("CREATE TRIGGER IF NOT EXISTS obs_ai AFTER INSERT ON observations BEGIN "
                             "INSERT INTO observations_fts(rowid, content, category, project) "
                             "VALUES (new.id, new.content, new.category, new.project); END")
            except sqlite3.OperationalError:
                pass
            conn.commit()

    def mem_save(self, content: str, category: str = "observation",
                 project: str = "nexus", metadata: dict = None,
                 topic_key: str = "") -> str:
        """Guarda una memoria en el sistema con UPSERT por topic_key."""
        ts = datetime.now().isoformat()
        meta_json = json.dumps(metadata or {})
        chash = _content_hash(content, category, project)
        with self._get_conn() as conn:
            cur = conn.cursor()
            if topic_key:
                cur.execute(
                    "SELECT id, revision_count FROM observations "
                    "WHERE topic_key=? AND project=? AND category=? AND deleted_at IS NULL "
                    "ORDER BY id DESC LIMIT 1",
                    (topic_key, project, category),
                )
                row = cur.fetchone()
                if row:
                    obs_id, rev = row[0], (row[1] or 0)
                    cur.execute(
                        "UPDATE observations SET content=?, metadata=?, updated_at=?, "
                        "revision_count=?, content_hash=? WHERE id=?",
                        (content, meta_json, ts, rev + 1, chash, obs_id),
                    )
                    conn.commit()
                    return f"[OK] Memoria UPSERTed en {category}/{topic_key} (rev {rev+1})"
            cur.execute(
                "INSERT INTO observations (ts, content, category, project, metadata, "
                "topic_key, content_hash, revision_count) VALUES (?,?,?,?,?,?,?,0)",
                (ts, content, category, project, meta_json,
                 topic_key or None, chash),
            )
            conn.commit()
        return f"[OK] Memoria guardada en {category}: {content[:50]}..."

    def mem_search(self, query: str, limit: int = 10, project: str = None):
        """Busca memorias relevantes usando FTS5 si está disponible, sino LIKE."""
        with self._get_conn() as conn:
            try:
                # Intentar búsqueda FTS5 (más rápida y precisa)
                sql = "SELECT ts, content, category, metadata FROM observations " \
                      "JOIN observations_fts ON observations.id = observations_fts.rowid " \
                      "WHERE observations_fts MATCH ? "
                params = [query]
                if project:
                    sql += " AND project = ?"
                    params.append(project)
                sql += " ORDER BY rank LIMIT ?"
                params.append(limit)
                rows = conn.execute(sql, params).fetchall()
            except sqlite3.OperationalError:
                # Fallback a LIKE
                sql = "SELECT ts, content, category, metadata FROM observations WHERE content LIKE ?"
                params = [f"%{query}%"]
                if project:
                    sql += " AND project = ?"
                    params.append(project)
                sql += " ORDER BY ts DESC LIMIT ?"
                params.append(limit)
                rows = conn.execute(sql, params).fetchall()
        
        results = []
        for r in rows:
            results.append({
                "timestamp": r[0],
                "content": r[1],
                "category": r[2],
                "metadata": json.loads(r[3])
            })
        return results

    def recall_context(self, task: str):
        """Recupera el contexto más relevante para una tarea."""
        # Búsqueda simple por palabras clave de la tarea
        keywords = task.split()[:3]
        results = []
        for kw in keywords:
            if len(kw) > 3:
                results.extend(self.mem_search(kw, limit=3))
        
        if not results:
            return "No se encontró contexto previo relevante."
            
        context = "\\n".join([f"- [{r['category']}] {r['content']}" for r in results])
        return f"### CONTEXTO RECUPERADO ###\\n{context}"

    def info(self):
        return {
            "skill": self.name,
            "description": self.description,
            "methods": ["mem_save(content, category, project)", "mem_search(query, limit)", "recall_context(task)"]
        }

if __name__ == "__main__":
    skill = PersistentMemorySkill()
    print(json.dumps(skill.info(), indent=2))
