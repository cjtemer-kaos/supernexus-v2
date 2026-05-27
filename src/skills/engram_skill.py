#!/usr/bin/env python3
"""
Persistent Memory Skill - Memoria Persistente Avanzada para Nexus IA
Implementa el protocolo de memoria persistente con FTS5.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

# DB Path (Alineado con el cerebro central unificado)
DB_PATH = Path.home() / ".nexus" / "brain" / "nexus_memory.db"

class PersistentMemorySkill:
    def __init__(self):
        self.name = "persistent_memory"
        self.description = "Persistent memory for AI agents (Observations, Decisions, Preferences)"
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with self._get_conn() as conn:
            # Tabla principal para persistencia
            conn.execute(
                "CREATE TABLE IF NOT EXISTS observations "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, content TEXT, category TEXT, project TEXT, metadata TEXT)"
            )
            # Tabla FTS5 para búsqueda rápida
            try:
                conn.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts USING fts5(content, category, project, content='observations', content_rowid='id')"
                )
                # Triggers para mantener sincronizada la tabla FTS
                conn.execute("CREATE TRIGGER IF NOT EXISTS obs_ai AFTER INSERT ON observations BEGIN "
                             "INSERT INTO observations_fts(rowid, content, category, project) VALUES (new.id, new.content, new.category, new.project); END")
            except sqlite3.OperationalError:
                # Si FTS5 no está disponible, el sistema sigue funcionando con la tabla normal
                pass
            conn.commit()

    def mem_save(self, content: str, category: str = "observation", project: str = "nexus", metadata: dict = None):
        """Guarda una memoria en el sistema."""
        ts = datetime.now().isoformat()
        meta_json = json.dumps(metadata or {})
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO observations (ts, content, category, project, metadata) VALUES (?,?,?,?,?)",
                (ts, content, category, project, meta_json)
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
