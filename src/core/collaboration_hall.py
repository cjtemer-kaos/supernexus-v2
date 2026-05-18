"""
F13: Hall Collaboration Timeline

Multi-agent discussion timeline with handoff and evidence threads.
"""

import logging
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from src.core.bounded_history import BoundedHistory

logger = logging.getLogger("nexus-hall")


class EventType(Enum):
    MESSAGE = "message"
    HANDOFF = "handoff"
    EVIDENCE = "evidence"
    DECISION = "decision"
    QUESTION = "question"
    ANSWER = "answer"


@dataclass
class TimelineEvent:
    id: str
    timestamp: float
    agent: str
    event_type: EventType
    content: str
    thread_id: str = ""
    references: List[str] = field(default_factory=list)


@dataclass
class DiscussionRoom:
    id: str
    topic: str
    agents: List[str] = field(default_factory=list)
    events: List[TimelineEvent] = field(default_factory=lambda: [])
    status: str = "active"
    created_at: str = ""
    max_turns: int = 5
    current_turn: int = 0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class CollaborationHall:
    """Manages multi-agent collaboration discussions"""

    def __init__(self):
        self._rooms: Dict[str, DiscussionRoom] = {}
        self._threads: Dict[str, BoundedHistory] = {}

    def create_room(self, topic: str, agents: List[str], room_id: str = None) -> DiscussionRoom:
        import uuid
        rid = room_id or str(uuid.uuid4())[:8]
        room = DiscussionRoom(id=rid, topic=topic, agents=agents)
        self._rooms[rid] = room
        logger.info(f"Collaboration room created: {rid} - {topic} (agents: {agents})")
        return room

    def add_event(self, room_id: str, agent: str, event_type: EventType, content: str, thread_id: str = "", references: List[str] = None) -> TimelineEvent:
        room = self._rooms.get(room_id)
        if not room:
            raise ValueError(f"Room not found: {room_id}")

        import uuid
        event = TimelineEvent(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            agent=agent,
            event_type=event_type,
            content=content,
            thread_id=thread_id,
            references=references or [],
        )
        room.events.append(event)

        # Track threads
        if thread_id:
            if thread_id not in self._threads:
                self._threads[thread_id] = BoundedHistory(maxlen=500)
            self._threads[thread_id].append(event)

        # Increment turn on message
        if event_type == EventType.MESSAGE:
            room.current_turn += 1
            if room.current_turn >= room.max_turns:
                room.status = "converged"
                logger.info(f"Room {room_id} converged after {room.max_turns} turns")

        return event

    def handoff(self, room_id: str, from_agent: str, to_agent: str, context: str) -> TimelineEvent:
        return self.add_event(room_id, from_agent, EventType.HANDOFF,
                            f"Handoff to {to_agent}: {context}")

    def add_evidence(self, room_id: str, agent: str, evidence: str, thread_id: str = "") -> TimelineEvent:
        return self.add_event(room_id, agent, EventType.EVIDENCE, evidence, thread_id)

    def get_timeline(self, room_id: str) -> List[Dict]:
        room = self._rooms.get(room_id)
        if not room:
            return []
        return [
            {
                "id": e.id,
                "timestamp": datetime.fromtimestamp(e.timestamp).isoformat(),
                "agent": e.agent,
                "type": e.event_type.value,
                "content": e.content[:200],
                "thread_id": e.thread_id,
            }
            for e in room.events
        ]

    def get_thread(self, thread_id: str) -> List[Dict]:
        events = self._threads.get(thread_id, BoundedHistory(maxlen=500)).get_all()
        return [
            {
                "id": e.id,
                "agent": e.agent,
                "type": e.event_type.value,
                "content": e.content[:200],
            }
            for e in events
        ]

    def list_rooms(self) -> List[Dict]:
        return [
            {
                "id": r.id,
                "topic": r.topic,
                "agents": r.agents,
                "status": r.status,
                "events": len(r.events),
                "turns": f"{r.current_turn}/{r.max_turns}",
            }
            for r in self._rooms.values()
        ]

    def get_event_count(self, room_id: str) -> int:
        room = self._rooms.get(room_id)
        return len(room.events) if room else 0

    def get_stats(self) -> Dict:
        total_events = sum(len(r.events) for r in self._rooms.values())
        return {
            "total_rooms": len(self._rooms),
            "active_rooms": sum(1 for r in self._rooms.values() if r.status == "active"),
            "converged_rooms": sum(1 for r in self._rooms.values() if r.status == "converged"),
            "total_events": total_events,
            "total_threads": len(self._threads),
        }
