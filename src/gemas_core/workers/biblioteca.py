"""
BibliotecaGem — Gema de organización de knowledge base.

Almacena documentos (archivos, URLs, snippets) en un índice SQLite
y permite buscar, organizar por tags/categoría/proyecto, y export.

Métodos:
    index(source, title, category, project, tags) -> dict
    search(query, limit, category, project) -> list
    list_categories() -> list
    execute(task) -> dict
    search_as_chat_messages(query, ...) -> list

All retrieved document content is treated as UNTRUSTED — the LLM may
receive it only via ``search_as_chat_messages()``, which wraps each
result in a sentinel-bounded user-role message (see
:mod:`gemas_core.core.prompt_security`).
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import GemaBase
from ..core.prompt_security import untrusted_context_message

logger = logging.getLogger("gemas-core.workers.biblioteca")


class BibliotecaGem(GemaBase):
    """Gema de organización de knowledge base."""

    name = "biblioteca"
    description = "Organización de knowledge base con búsqueda e indexación"
    category = "data-ai"

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path.cwd() / "data" / "cerebro" / "biblioteca.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    title TEXT,
                    content TEXT,
                    category TEXT DEFAULT 'general',
                    project TEXT DEFAULT 'default',
                    tags TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_docs_category ON documents(category)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_docs_project ON documents(project)"
            )
            conn.commit()

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        """Dispatch por prefijo:
            'index: <source>' → index(source)
            'search: <query>' → search(query)
            'categorias' → list_categories()
        """
        task_stripped = task.strip()
        low = task_stripped.lower()
        if low.startswith("index:"):
            source = task_stripped.split(":", 1)[1].strip()
            return await self.index(source)
        if low.startswith("search:") or low.startswith("buscar:"):
            query = task_stripped.split(":", 1)[1].strip()
            results = await self.search(query, limit=10)
            return {
                "success": True,
                "gema": "biblioteca",
                "action": "search",
                "query": query,
                "results": results,
                "count": len(results),
            }
        if low in ("categorias", "categories", "list categories"):
            return {
                "success": True,
                "gema": "biblioteca",
                "action": "list_categories",
                "categories": self.list_categories(),
            }
        return {
            "success": False,
            "gema": "biblioteca",
            "error": (
                "use prefix: 'index: <source>', 'search: <query>', "
                "or 'categorias'"
            ),
        }

    async def index(
        self,
        source: str,
        title: Optional[str] = None,
        category: str = "general",
        project: str = "default",
        tags: Optional[List[str]] = None,
        content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Indexa un documento en la biblioteca."""
        if not source or not source.strip():
            return {"success": False, "gema": "biblioteca", "error": "source empty"}
        if content is None and source.startswith(("http://", "https://")):
            content = await self._fetch_url(source)
        if content is None:
            content = ""
        tags_json = json.dumps(tags or [])
        ts = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO documents(source, title, content, category, project, tags, created_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?)",
                (source, title or source, content, category, project, tags_json, ts),
            )
            conn.commit()
            doc_id = cur.lastrowid
        logger.info(f"BibliotecaGem index id={doc_id} source={source[:60]}")
        return {
            "success": True,
            "gema": "biblioteca",
            "action": "index",
            "id": doc_id,
            "source": source,
            "category": category,
        }

    async def search(
        self,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
        project: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Búsqueda por LIKE en source/title/content."""
        if not query or not query.strip():
            return []
        # Escapar caracteres especiales de LIKE
        safe_query = query.replace("%", "\\%").replace("_", "\\_")
        like = f"%{safe_query}%"
        sql = (
            "SELECT id, source, title, category, project, tags, created_at "
            "FROM documents WHERE (source LIKE ? OR title LIKE ? OR content LIKE ?)"
        )
        params: List[Any] = [like, like, like]
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
                tags = json.loads(r[5]) if r[5] else []
            except json.JSONDecodeError:
                tags = []
            out.append({
                "id": r[0],
                "source": r[1],
                "title": r[2],
                "category": r[3],
                "project": r[4],
                "tags": tags,
                "created_at": r[6],
            })
        return out

    def list_categories(self) -> List[Dict[str, Any]]:
        """Lista categorías con conteo de documentos."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT category, COUNT(*) FROM documents GROUP BY category ORDER BY 2 DESC"
            ).fetchall()
        return [{"category": r[0], "count": r[1]} for r in rows]

    @staticmethod
    async def _fetch_url(url: str) -> Optional[str]:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=15),
                    headers={"User-Agent": "Mozilla/5.0 NexusBiblioteca"},
                ) as resp:
                    if resp.status != 200:
                        return None
                    return (await resp.text())[:5000]
        except Exception as e:
            logger.debug(f"fetch failed for {url}: {e}")
            return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": "biblioteca",
            "name": "BIBLIOTECA",
            "description": self.description,
            "category": self.category,
            "type": "dedicated",
            "db_path": str(self.db_path),
        }

    async def search_as_chat_messages(
        self,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
        project: Optional[str] = None,
        label: str = "biblioteca",
        include_content: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search and wrap each result as an untrusted chat message.

        Each document becomes a separate ``role: user`` message with
        ``metadata.trusted = False`` and ``metadata.source =
        f"{label}[{i}].id={doc_id}"``. Returns an empty list if no
        results match.

        Unlike :meth:`search` (which returns metadata only), this
        method includes the document ``content`` in the wrapped
        payload so the LLM can actually use the retrieved body. This
        is the safe channel for feeding documents to the model — see
        :mod:`gemas_core.core.prompt_security`.

        Set ``include_content=False`` to wrap metadata-only (useful
        for title listings or UI previews).
        """
        if not query or not query.strip():
            return []
        like = f"%{query}%"
        if include_content:
            sql = (
                "SELECT id, source, title, content, category, project, tags, created_at "
                "FROM documents WHERE (source LIKE ? OR title LIKE ? OR content LIKE ?)"
            )
        else:
            sql = (
                "SELECT id, source, title, '' AS content, category, project, tags, created_at "
                "FROM documents WHERE (source LIKE ? OR title LIKE ?)"
            )
        params: List[Any] = [like, like, like]
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
        if not rows:
            return []
        out: List[Dict[str, Any]] = []
        for r in rows:
            try:
                tags = json.loads(r[6]) if r[6] else []
            except json.JSONDecodeError:
                tags = []
            payload: Dict[str, Any] = {
                "source": r[1],
                "title": r[2],
                "category": r[4],
                "project": r[5],
                "tags": tags,
                "created_at": r[7],
            }
            if include_content:
                payload["content"] = r[3] or ""
            out.append(
                untrusted_context_message(
                    f"{label}.id={r[0]}",
                    json.dumps(payload, ensure_ascii=False),
                )
            )
        return out
