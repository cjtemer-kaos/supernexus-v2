"""
SageGem — Gema de persistencia de conocimiento (memoria).

Almacena observations en un SQLite con FTS5 (si está disponible) o
JSON-lines como fallback. Cada observation tiene:
  - id (auto)
  - content (texto)
  - category
  - project
  - metadata (dict JSON)
  - created_at (timestamp)

Métodos:
    remember(content, category, project, metadata) -> dict
    recall(query, limit, category, project) -> list
    execute(task) -> dict
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import GemaBase

logger = logging.getLogger("gemas-core.workers.sage")


class SageGem(GemaBase):
    """Gema de memoria y persistencia de conocimiento."""

    name = "sage"
    description = "Persistencia de conocimiento con búsqueda full-text"
    category = "data-ai"

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path.cwd() / "data" / "cerebro" / "sage_memory.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    project TEXT DEFAULT 'default',
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_obs_category ON observations(category)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_obs_project ON observations(project)"
            )
            conn.commit()

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        """Dispatch: si task empieza con 'recall:', busca; si no, almacena."""
        task_stripped = task.strip()
        if task_stripped.lower().startswith("recall:") or task_stripped.lower().startswith("buscar:"):
            query = task_stripped.split(":", 1)[1].strip()
            results = await self.recall(query, limit=10)
            return {
                "success": True,
                "gema": "sage",
                "action": "recall",
                "query": query,
                "results": results,
                "count": len(results),
            }
        return await self.remember(task_stripped)

    async def remember(
        self,
        content: str,
        category: str = "general",
        project: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Almacena una observation."""
        if not content or not content.strip():
            return {"success": False, "gema": "sage", "error": "content empty"}
        meta_json = json.dumps(metadata or {})
        ts = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO observations(content, category, project, metadata, created_at) "
                "VALUES(?, ?, ?, ?, ?)",
                (content, category, project, meta_json, ts),
            )
            conn.commit()
            obs_id = cur.lastrowid
        logger.info(f"SageGem remember id={obs_id} category={category}")
        return {
            "success": True,
            "gema": "sage",
            "action": "remember",
            "id": obs_id,
            "category": category,
            "project": project,
        }

    async def recall(
        self,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
        project: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Búsqueda full-text simple (LIKE). FTS5 es client-overridable."""
        if not query or not query.strip():
            return []
        like = f"%{query}%"
        sql = (
            "SELECT id, content, category, project, metadata, created_at "
            "FROM observations WHERE content LIKE ?"
        )
        params: List[Any] = [like]
        if category:
            sql += " AND category = ?"
            params.append(category)
        if project:
            sql += " AND project = ?"
            params.append(project)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            try:
                meta = json.loads(r[4]) if r[4] else {}
            except json.JSONDecodeError:
                meta = {}
            out.append({
                "id": r[0],
                "content": r[1],
                "category": r[2],
                "project": r[3],
                "metadata": meta,
                "created_at": r[5],
            })
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": "sage",
            "name": "SAGE",
            "description": self.description,
            "category": self.category,
            "type": "dedicated",
            "db_path": str(self.db_path),
        }
