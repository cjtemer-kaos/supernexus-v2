import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("nexus-event-store")


class EventKind:
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    MEMORY_WRITE = "memory_write"
    STATE_CHANGE = "state_change"
    HANDOFF = "handoff"
    CUSTOM = "custom"


@dataclass
class Event:
    kind: str
    data: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:32])
    conversation_id: str = ""
    timestamp: float = field(default_factory=time.time)
    parent_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class EventStore:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path.home() / ".nexus" / "brain" / "event_store.db")
        self.db_path = db_path
        self._callbacks: Dict[str, List[Callable]] = {}
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                conversation_id TEXT DEFAULT '',
                data TEXT DEFAULT '{}',
                timestamp REAL DEFAULT (strftime('%s', 'now')),
                parent_id TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}'
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_conv ON events(conversation_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp)")

    def append(self, event: Event) -> str:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO events (id, kind, conversation_id, data, timestamp, parent_id, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (event.id, event.kind, event.conversation_id, json.dumps(event.data),
                 event.timestamp, event.parent_id, json.dumps(event.metadata)))
        self._trigger_callbacks(event.kind, event)
        return event.id

    def replay(self, conversation_id: str, since: float = 0) -> List[Event]:
        events = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM events WHERE conversation_id = ? AND timestamp > ? ORDER BY timestamp ASC",
                (conversation_id, since)).fetchall()
            for r in rows:
                events.append(Event(
                    id=r["id"], kind=r["kind"], conversation_id=r["conversation_id"],
                    data=json.loads(r["data"]), timestamp=r["timestamp"],
                    parent_id=r["parent_id"], metadata=json.loads(r["metadata"])))
        return events

    def subscribe(self, kind: str, callback: Callable):
        if kind not in self._callbacks:
            self._callbacks[kind] = []
        self._callbacks[kind].append(callback)

    def _trigger_callbacks(self, kind: str, event: Event):
        for cb in self._callbacks.get(kind, []):
            try:
                cb(event)
            except Exception as e:
                logger.error(f"Event callback error for {kind}: {e}")

    def get_stats(self) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            by_kind = conn.execute("SELECT kind, COUNT(*) FROM events GROUP BY kind").fetchall()
            return {
                "total_events": total,
                "by_kind": {k: c for k, c in by_kind},
                "subscribers": {k: len(cbs) for k, cbs in self._callbacks.items()},
            }



