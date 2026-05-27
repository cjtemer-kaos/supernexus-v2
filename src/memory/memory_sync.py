"""
Memory Sync - Sincronizacion bidireccional de las 3 capas de memoria

Adaptado de memory_sync.py original. Sincroniza:
- Capa 1: Neural Patterns (SQLite)
- Capa 2: RAG Index (txtai)
- Capa 3: Knowledge Graph (Markdown notes)

Entre Windows y PC2 (y futuras maquinas via Tailscale).
"""

import asyncio
import json
import logging
import sqlite3
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import httpx

import os

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class MemorySync:
    """
    Sincroniza las 3 capas de memoria entre instancias de NEXUS.
    Bidireccional: Windows <-> PC2 <-> Tailscale nodes.
    """

    def __init__(self, local_db: Optional[str] = None, remote_url: Optional[str] = None):
        if local_db is None:
            local_db = str(Path(__file__).parent.parent.parent / "data" / "base_memory" / "neural.db")
        self.local_db = Path(local_db)
        self.remote_url = remote_url or f"http://{os.getenv('SUPER_NEXUS_PC2_IP', 'localhost')}:9000"
        self.knowledge_path = Path(__file__).parent.parent.parent / "data" / "knowledge"
        self.client = httpx.AsyncClient(timeout=10.0)
        self.sync_interval = 10  # seconds

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.local_db, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    async def sync_neural_patterns(self) -> Dict:
        """Sincroniza patrones neurales (Capa 1)"""
        result = {"pushed": 0, "pulled": 0, "merged": 0}

        try:
            # Push local patterns to remote
            local_patterns = self._get_local_patterns()
            if local_patterns:
                r = await self.client.post(
                    f"{self.remote_url}/api/memory/sync",
                    json={"action": "merge_patterns", "source": "windows", "patterns": local_patterns},
                )
                if r.status_code == 200:
                    result["pushed"] = len(local_patterns)

            # Pull remote patterns
            r = await self.client.get(f"{self.remote_url}/api/memory/patterns")
            if r.status_code == 200:
                remote_patterns = r.json()
                result["pulled"] = len(remote_patterns)
                result["merged"] = self._merge_patterns(remote_patterns)
        except Exception as e:
            logger.error(f"Neural sync error: {e}")

        return result

    async def sync_knowledge_graph(self) -> Dict:
        """Sincroniza grafo de conocimiento (Capa 3)"""
        result = {"synced": 0, "errors": 0}

        try:
            # For now, sync via file comparison
            # In production, use a proper sync protocol
            remote_knowledge = f"{self.remote_url}/api/knowledge"
            # This would require a knowledge sync endpoint on the remote
            logger.info("Knowledge graph sync: requires remote endpoint")
        except Exception as e:
            logger.error(f"Knowledge sync error: {e}")
            result["errors"] += 1

        return result

    async def sync_bidirectional(self) -> Dict:
        """Sincronizacion completa de todas las capas"""
        neural = await self.sync_neural_patterns()
        knowledge = await self.sync_knowledge_graph()

        return {
            "timestamp": datetime.now().isoformat(),
            "neural": neural,
            "knowledge": knowledge,
        }

    def _get_local_patterns(self) -> List[Dict]:
        """Obtiene patrones locales"""
        if not self.local_db.exists():
            return []

        try:
            conn = self._get_conn()
            cursor = conn.execute(
                "SELECT task_name, data, accessed_count FROM neural_patterns ORDER BY accessed_count DESC"
            )
            patterns = []
            for row in cursor.fetchall():
                patterns.append({
                    "task": row[0],
                    "data": json.loads(row[1]),
                    "accesses": row[2],
                })
            conn.close()
            return patterns
        except Exception as e:
            logger.error(f"Error getting local patterns: {e}")
            return []

    def _merge_patterns(self, remote_patterns: List[Dict]) -> int:
        """Fusiona patrones remotos con locales"""
        if not remote_patterns or not self.local_db.exists():
            return 0

        merged = 0
        try:
            conn = self._get_conn()
            for pattern in remote_patterns:
                cursor = conn.execute(
                    "SELECT accessed_count FROM neural_patterns WHERE task_name=?",
                    (pattern["task"],)
                )
                existing = cursor.fetchone()

                if existing:
                    local_accesses = existing[0]
                    remote_accesses = pattern.get("accesses", 0)
                    if remote_accesses > local_accesses:
                        conn.execute(
                            "UPDATE neural_patterns SET data=?, accessed_count=? WHERE task_name=?",
                            (json.dumps(pattern["data"]), remote_accesses, pattern["task"])
                        )
                        merged += 1
                else:
                    conn.execute(
                        "INSERT INTO neural_patterns (task_name, data, created_at, accessed_count) VALUES (?, ?, ?, ?)",
                        (pattern["task"], json.dumps(pattern["data"]), datetime.now().isoformat(), pattern.get("accesses", 0))
                    )
                    merged += 1

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error merging patterns: {e}")

        return merged

    async def close(self):
        await self.client.aclose()
