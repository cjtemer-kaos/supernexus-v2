"""
F3: Checkpoint Recovery

Save state at each node, resume from checkpoint on crash.
Uses SQLite for persistence with automatic crash detection.
"""

import json
import logging
import sqlite3
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("nexus-checkpoint")


@dataclass
class Checkpoint:
    id: str
    run_id: str
    node_id: str
    state: Dict
    created_at: str = ""
    data_buffer: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class CheckpointStore:
    """Persistent checkpoint storage with crash recovery"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path.home() / ".nexus" / "brain" / "checkpoints.db")
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=5000")
        c.execute("""CREATE TABLE IF NOT EXISTS checkpoints (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            state TEXT NOT NULL,
            created_at TEXT NOT NULL,
            data_buffer TEXT DEFAULT ''
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS run_status (
            run_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            goal TEXT DEFAULT '',
            started_at TEXT NOT NULL,
            completed_at TEXT DEFAULT '',
            last_checkpoint_id TEXT DEFAULT ''
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_run ON checkpoints(run_id)")
        conn.commit()
        conn.close()

    def save_checkpoint(self, run_id: str, node_id: str, state: Dict, data_buffer: str = "") -> Checkpoint:
        import uuid
        cp = Checkpoint(
            id=str(uuid.uuid4())[:12],
            run_id=run_id,
            node_id=node_id,
            state=state,
            data_buffer=data_buffer,
        )
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""INSERT OR REPLACE INTO checkpoints (id, run_id, node_id, state, created_at, data_buffer)
            VALUES (?, ?, ?, ?, ?, ?)""", (
            cp.id, cp.run_id, cp.node_id,
            json.dumps(cp.state, ensure_ascii=False),
            cp.created_at, cp.data_buffer,
        ))
        c.execute("""INSERT OR REPLACE INTO run_status (run_id, status, started_at, last_checkpoint_id)
            VALUES (?, 'running', ?, ?)""", (run_id, datetime.now().isoformat(), cp.id))
        conn.commit()
        conn.close()
        logger.debug(f"Checkpoint saved: {cp.id} (run: {run_id}, node: {node_id})")
        return cp

    def mark_run_complete(self, run_id: str):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE run_status SET status = 'completed', completed_at = ? WHERE run_id = ?",
                  (datetime.now().isoformat(), run_id))
        conn.commit()
        conn.close()

    def get_incomplete_runs(self) -> List[Dict]:
        """Find runs that didn't complete (potential crashes)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM run_status WHERE status != 'completed' ORDER BY started_at DESC")
        runs = [dict(r) for r in c.fetchall()]
        conn.close()
        return runs

    def get_latest_checkpoint(self, run_id: str, node_id: str = None) -> Optional[Checkpoint]:
        """Get the latest checkpoint for a run (optionally for a specific node)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        if node_id:
            c.execute("SELECT * FROM checkpoints WHERE run_id = ? AND node_id = ? ORDER BY created_at DESC LIMIT 1",
                      (run_id, node_id))
        else:
            c.execute("SELECT * FROM checkpoints WHERE run_id = ? ORDER BY created_at DESC LIMIT 1", (run_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return None
        return Checkpoint(
            id=row["id"], run_id=row["run_id"], node_id=row["node_id"],
            state=json.loads(row["state"]), created_at=row["created_at"],
            data_buffer=row["data_buffer"],
        )

    def get_all_checkpoints(self, run_id: str) -> List[Checkpoint]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM checkpoints WHERE run_id = ? ORDER BY created_at", (run_id,))
        rows = c.fetchall()
        conn.close()
        return [
            Checkpoint(id=r["id"], run_id=r["run_id"], node_id=r["node_id"],
                      state=json.loads(r["state"]), created_at=r["created_at"],
                      data_buffer=r["data_buffer"])
            for r in rows
        ]

    def cleanup_old_checkpoints(self, max_age_hours: int = 24):
        """Remove checkpoints older than max_age_hours"""
        cutoff = (datetime.now().timestamp() - max_age_hours * 3600)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM checkpoints WHERE created_at < ?", (datetime.fromtimestamp(cutoff).isoformat(),))
        deleted = c.rowcount
        conn.commit()
        conn.close()
        if deleted:
            logger.info(f"Cleaned up {deleted} old checkpoints")
        return deleted

    def get_stats(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM checkpoints")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM run_status WHERE status = 'running'")
        running = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM run_status WHERE status = 'completed'")
        completed = c.fetchone()[0]
        conn.close()
        return {
            "total_checkpoints": total,
            "running_runs": running,
            "completed_runs": completed,
            "db_path": self.db_path,
        }

    def close(self):
        pass
