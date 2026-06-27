"""
NexusHive Bridge — Canonical SQLite message board bridge

Single source of truth for colmena messaging.
WAL mode set once in _init_db(), not re-applied per call.
"""

import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict


class NexusHiveBridge:
    def __init__(self, agent_name: str, db_path: Optional[str] = None):
        self.agent_name = agent_name
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.brain_dir = Path(os.path.expanduser("~/.nexus/brain"))
            self.db_path = self.brain_dir / "message_board.db"
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            sender TEXT NOT NULL,
            target TEXT DEFAULT '*',
            channel TEXT DEFAULT 'general',
            content TEXT NOT NULL,
            msg_type TEXT DEFAULT 'chat',
            metadata TEXT DEFAULT '{}'
        )''')
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_target ON messages(target, channel, timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender, channel, timestamp)")
        conn.commit()
        conn.close()

    def send_message(self, target: str, content: str, msg_type: str = "chat",
                     channel: str = "general", metadata: Optional[Dict] = None):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute('''INSERT INTO messages (timestamp, sender, target, channel, content, msg_type, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (datetime.now().isoformat(), self.agent_name, target, channel, content, msg_type,
                 json.dumps(metadata or {})))
            conn.commit()
        finally:
            conn.close()

    def read_messages(self, limit: int = 10) -> List[Dict]:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        msgs = conn.execute('''SELECT * FROM messages WHERE (target=? OR target='*') AND sender!=?
            ORDER BY id DESC LIMIT ?''', (self.agent_name, self.agent_name, limit)).fetchall()
        result = [dict(m) for m in msgs]
        conn.close()
        return result

    def get_all_messages(self, limit: int = 30) -> List[Dict]:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        msgs = conn.execute('SELECT * FROM messages ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        result = [dict(m) for m in msgs]
        conn.close()
        return result
