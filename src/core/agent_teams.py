import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("nexus-teams")


@dataclass
class Message:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    sender: str = ""
    target: str = ""
    msg_type: str = "request"
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    in_reply_to: str = ""
    status: str = "pending"


@dataclass
class AgentTeam:
    name: str
    members: List[str] = field(default_factory=list)
    description: str = ""


class MessageBus:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path.home() / ".nexus" / "brain" / "message_bus.db")
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._inboxes: Dict[str, List[Message]] = {}
        self._pending_callbacks: Dict[str, Callable] = {}
        self._init_db()

    def _init_db(self):
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                sender TEXT NOT NULL,
                target TEXT NOT NULL,
                msg_type TEXT DEFAULT 'request',
                content TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                timestamp REAL DEFAULT (strftime('%s', 'now')),
                in_reply_to TEXT DEFAULT '',
                status TEXT DEFAULT 'pending'
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS teams (
                name TEXT PRIMARY KEY,
                members TEXT DEFAULT '[]',
                description TEXT DEFAULT ''
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_target ON messages(target)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status)")

    def send(self, msg: Message) -> str:
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO messages (id, sender, target, msg_type, content, metadata, timestamp, in_reply_to, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (msg.id, msg.sender, msg.target, msg.msg_type, msg.content,
                 json.dumps(msg.metadata), msg.timestamp, msg.in_reply_to, msg.status))
        return msg.id

    def read(self, target: str, limit: int = 20, since: float = 0) -> List[Message]:
        import sqlite3
        messages = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM messages WHERE target = ? AND timestamp > ? ORDER BY timestamp DESC LIMIT ?",
                (target, since, limit)).fetchall()
            for r in rows:
                messages.append(Message(
                    id=r["id"], sender=r["sender"], target=r["target"],
                    msg_type=r["msg_type"], content=r["content"],
                    metadata=json.loads(r["metadata"]),
                    timestamp=r["timestamp"], in_reply_to=r["in_reply_to"],
                    status=r["status"]))
        return messages

    def mark_read(self, msg_id: str):
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE messages SET status = 'read' WHERE id = ?", (msg_id,))

    def reply(self, original: Message, content: str, sender: str) -> str:
        reply_msg = Message(
            sender=sender,
            target=original.sender,
            msg_type="response",
            content=content,
            in_reply_to=original.id,
            metadata={"original_type": original.msg_type},
        )
        return self.send(reply_msg)

    def register_team(self, team: AgentTeam):
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO teams (name, members, description) VALUES (?, ?, ?)",
                         (team.name, json.dumps(team.members), team.description))

    def get_team(self, name: str) -> Optional[AgentTeam]:
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM teams WHERE name = ?", (name,)).fetchone()
            if row:
                return AgentTeam(name=row["name"], members=json.loads(row["members"]),
                                 description=row["description"])
        return None

    def list_teams(self) -> List[AgentTeam]:
        import sqlite3
        teams = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            for r in conn.execute("SELECT * FROM teams").fetchall():
                teams.append(AgentTeam(name=r["name"], members=json.loads(r["members"]),
                                       description=r["description"]))
        return teams

    def request(self, target: str, content: str, sender: str, timeout: float = 30.0) -> Optional[Message]:
        msg = Message(sender=sender, target=target, msg_type="request", content=content)
        self.send(msg)
        deadline = time.time() + timeout
        while time.time() < deadline:
            responses = self.read(target=msg.id, since=msg.timestamp)
            responses = [m for m in responses if m.in_reply_to == msg.id and m.status != "read"]
            if responses:
                return responses[0]
            time.sleep(0.5)
        return None


class AgentTeamManager:
    def __init__(self, bus: MessageBus = None, agent_id: str = None):
        self.bus = bus or MessageBus()
        self.agent_id = agent_id or "agent-unknown"
        self._tasks: Dict[str, asyncio.Task] = {}

    async def listen_loop(self, handler: Callable, poll_interval: float = 1.0):
        last_poll = time.time()
        while True:
            try:
                messages = self.bus.read(target=self.agent_id, since=last_poll)
                for msg in messages:
                    if msg.status == "pending":
                        self.bus.mark_read(msg.id)
                        result = handler(msg)
                        if asyncio.iscoroutine(result):
                            await result
                last_poll = time.time()
            except Exception as e:
                logger.error(f"Listen loop error: {e}")
            await asyncio.sleep(poll_interval)

    async def claim_task(self, task_board: str = "tasks") -> Optional[Message]:
        pending = self.bus.read(target=task_board, limit=10)
        for msg in pending:
            if msg.status == "pending" and msg.msg_type == "task":
                self.bus.mark_read(msg.id)
                return msg
        return None

    def spawn_worker(self, name: str, coro):
        task = asyncio.create_task(coro)
        self._tasks[name] = task
        return task

    def cancel_worker(self, name: str):
        task = self._tasks.pop(name, None)
        if task:
            task.cancel()

    def get_workers_status(self) -> Dict:
        return {
            name: {
                "done": task.done(),
                "cancelled": task.cancelled() if task.done() else False,
            }
            for name, task in self._tasks.items()
        }


_default_bus = MessageBus()
_default_manager = AgentTeamManager(bus=_default_bus)
