"""
Event Bus + Message Queue - OpenSwarm pattern para SuperNEXUS v2.0

Comunicacion entre agentes con eventos, colas y handoffs.
"""

import asyncio
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class EventType(Enum):
    """Tipos de eventos en el sistema"""
    MESSAGE = "message"
    HANDOFF = "handoff"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    LEARNING = "learning"
    MEMORY_UPDATE = "memory_update"
    ENGINE_STATUS = "engine_status"
    USER_INPUT = "user_input"
    SYSTEM = "system"


@dataclass
class Message:
    """Mensaje entre agentes"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source: str = ""
    target: str = ""
    event_type: EventType = EventType.MESSAGE
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    priority: int = 3  # 1=highest, 5=lowest
    requires_response: bool = False
    parent_id: Optional[str] = None


@dataclass
class Handoff:
    """Handoff de un agente a otro"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    from_agent: str = ""
    to_agent: str = ""
    task: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class EventBus:
    """
    Bus de eventos para comunicacion entre agentes.
    Pattern: Publish-Subscribe con routing.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._history: List[Message] = []
        self._max_history = 1000

    def subscribe(self, event_type: str, callback: Callable):
        """Suscribe un callback a un tipo de evento"""
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        """Desuscribe un callback"""
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    async def publish(self, message: Message):
        """Publica un mensaje en el bus"""
        self._history.append(message)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Notificar suscriptores
        handlers = self._subscribers.get(message.event_type.value, [])
        handlers.extend(self._subscribers.get("*", []))  # Wildcard

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    async def enqueue(self, message: Message):
        """Encola un mensaje para procesamiento"""
        await self._message_queue.put(message)

    async def process_queue(self):
        """Procesa mensajes encolados"""
        self._running = True
        while self._running:
            try:
                message = await asyncio.wait_for(self._message_queue.get(), timeout=1.0)
                await self.publish(message)
                self._message_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Queue processing error: {e}")

    def stop(self):
        """Detiene el procesamiento"""
        self._running = False

    def get_history(self, limit: int = 50) -> List[Message]:
        """Obtiene historial de mensajes"""
        return self._history[-limit:]

    def get_stats(self) -> Dict:
        """Estadisticas del bus"""
        by_type = defaultdict(int)
        for msg in self._history:
            by_type[msg.event_type.value] += 1

        return {
            "total_messages": len(self._history),
            "queue_size": self._message_queue.qsize(),
            "subscribers": {k: len(v) for k, v in self._subscribers.items()},
            "by_type": dict(by_type),
        }


class MessageQueue:
    """
    Cola de mensajes con prioridades.
    Pattern: Priority Queue con retry.
    """

    def __init__(self, max_retries: int = 3):
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._max_retries = max_retries
        self._failed: List[Message] = []
        self._processed = 0

    async def put(self, message: Message):
        """Agrega mensaje a la cola"""
        # Priority queue: lower number = higher priority
        await self._queue.put((message.priority, message.id, message))

    async def get(self) -> Optional[Message]:
        """Obtiene siguiente mensaje"""
        try:
            _, _, message = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            return message
        except asyncio.TimeoutError:
            return None

    def mark_failed(self, message: Message):
        """Marca mensaje como fallido"""
        retries = message.metadata.get("retries", 0)
        if retries < self._max_retries:
            message.metadata["retries"] = retries + 1
            message.priority = max(1, message.priority - 1)  # Increase priority on retry
            asyncio.create_task(self._queue.put((message.priority, message.id, message)))
        else:
            self._failed.append(message)
            logger.warning(f"Message failed after {self._max_retries} retries: {message.id}")

    def get_stats(self) -> Dict:
        """Estadisticas de la cola"""
        return {
            "pending": self._queue.qsize(),
            "processed": self._processed,
            "failed": len(self._failed),
        }
