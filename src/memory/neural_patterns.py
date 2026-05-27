"""
Neural Patterns - Capa 1 de Memoria (mejorada de neural_learning.py)

SQLite con patrones task_name -> data, accessed_count, learning feedback.
0-token recovery: acceso directo por nombre de tarea.
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class NeuralPatterns:
    """
    Sistema de memoria neural basado en SQLite.
    Almacena patrones de tareas ejecutadas para recuperacion 0-token.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent.parent / "data" / "base_memory" / "neural.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()
        logger.info(f"NeuralPatterns initialized: {db_path}")

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self):
        """Inicializa tablas de memoria neural"""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS neural_patterns (
                    id INTEGER PRIMARY KEY,
                    task_name TEXT UNIQUE,
                    data TEXT,
                    created_at TIMESTAMP,
                    accessed_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP,
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0,
                    tags TEXT DEFAULT '[]',
                    project TEXT DEFAULT 'default'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_feedback (
                    id INTEGER PRIMARY KEY,
                    task_name TEXT,
                    feedback_type TEXT,
                    feedback_data TEXT,
                    timestamp TIMESTAMP
                )
            """)
            conn.commit()

    def store(self, task_name: str, data: dict, project: str = "default", tags: List[str] = None) -> bool:
        """Almacena un patron de tarea"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO neural_patterns
                       (task_name, data, created_at, tags, project)
                       VALUES (?, ?, ?, ?, ?)""",
                    (task_name, json.dumps(data), datetime.now().isoformat(),
                     json.dumps(tags or []), project)
                )
                conn.commit()
            logger.info(f"Pattern stored: {task_name}")
            return True
        except Exception as e:
            logger.error(f"Error storing pattern: {e}")
            return False

    def retrieve(self, task_name: str) -> Optional[dict]:
        """Recupera un patron (0-token recovery)"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "SELECT data FROM neural_patterns WHERE task_name=?",
                    (task_name,)
                )
                row = cursor.fetchone()
                if row:
                    conn.execute(
                        """UPDATE neural_patterns
                           SET accessed_count=accessed_count+1, last_accessed=?
                           WHERE task_name=?""",
                        (datetime.now().isoformat(), task_name)
                    )
                    conn.commit()
                    return json.loads(row[0])
            return None
        except Exception as e:
            logger.error(f"Error retrieving pattern: {e}")
            return None

    def record_feedback(self, task_name: str, success: bool, feedback: dict = None):
        """Registra feedback de ejecucion para aprendizaje"""
        try:
            with self._get_conn() as conn:
                if success:
                    conn.execute(
                        "UPDATE neural_patterns SET success_count=success_count+1 WHERE task_name=?",
                        (task_name,)
                    )
                else:
                    conn.execute(
                        "UPDATE neural_patterns SET fail_count=fail_count+1 WHERE task_name=?",
                        (task_name,)
                    )
                if feedback:
                    conn.execute(
                        """INSERT INTO learning_feedback (task_name, feedback_type, feedback_data, timestamp)
                           VALUES (?, ?, ?, ?)""",
                        (task_name, "success" if success else "failure",
                         json.dumps(feedback), datetime.now().isoformat())
                    )
                conn.commit()
        except Exception as e:
            logger.error(f"Error recording feedback: {e}")

    def get_popular(self, limit: int = 20) -> List[dict]:
        """Retorna los patrones mas accedidos"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """SELECT task_name, data, accessed_count, success_count, fail_count
                       FROM neural_patterns ORDER BY accessed_count DESC LIMIT ?""",
                    (limit,)
                )
                return [
                    {
                        "task": row[0],
                        "data": json.loads(row[1]),
                        "accesses": row[2],
                        "successes": row[3],
                        "failures": row[4],
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Error getting popular patterns: {e}")
            return []

    def get_by_project(self, project: str) -> List[dict]:
        """Retorna patrones de un proyecto especifico"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """SELECT task_name, data, accessed_count FROM neural_patterns
                       WHERE project=? ORDER BY accessed_count DESC""",
                    (project,)
                )
                return [
                    {"task": row[0], "data": json.loads(row[1]), "accesses": row[2]}
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Error getting project patterns: {e}")
            return []

    def get_stats(self) -> dict:
        """Estadisticas de memoria neural"""
        try:
            with self._get_conn() as conn:
                total = conn.execute("SELECT COUNT(*) FROM neural_patterns").fetchone()[0]
                total_accesses = conn.execute("SELECT SUM(accessed_count) FROM neural_patterns").fetchone()[0] or 0
                total_success = conn.execute("SELECT SUM(success_count) FROM neural_patterns").fetchone()[0] or 0
                total_fail = conn.execute("SELECT SUM(fail_count) FROM neural_patterns").fetchone()[0] or 0
                return {
                    "total_patterns": total,
                    "total_accesses": total_accesses,
                    "total_successes": total_success,
                    "total_failures": total_fail,
                    "success_rate": total_success / (total_success + total_fail) if (total_success + total_fail) > 0 else 0,
                }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
