"""v1.7.0 — hook_events: 19-event HookEvent + 5-level HookPriority enums.

Ports the enum layer of RUFLO v3's
`@claude-flow/hooks/src/types.ts` to gemas_core. The full
EventEmitter-based hook *runtime* is NOT ported (that's
TypeScript-specific and would duplicate the existing
`plan_mode.py` blocklist logic). What IS ported is the
vocabulary — event names and priority levels — so that
configurations, logs, and external tools can speak the same
language as RUFLO without dragging in the Node.js runtime.

Wire-up:
  - `HookPriority` levels feed into `agents/plan_mode.py`'s
    blocklist (the existing module already uses an implicit
    "0 = allowed, >0 = blocked" model).
  - `HookEvent` is exposed for cross-system logging/metrics,
    not as a runtime dispatch target.
"""
from __future__ import annotations

from enum import Enum, IntEnum

try:
    from enum import StrEnum
except ImportError:  # Python < 3.11
    class StrEnum(str, Enum):
        """str + Enum polyfill for Python < 3.11."""

        def __new__(cls, value):
            obj = str.__new__(cls, value)
            obj._value_ = value
            return obj

        def __str__(self) -> str:
            return self._value_


class HookEvent(StrEnum):
    """The 19 hook events from RUFLO v3, names preserved verbatim."""

    # Lifecycle
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    SESSION_RESUME = "session_resume"

    # Agent / task
    AGENT_INIT = "agent_init"
    AGENT_TERMINATE = "agent_terminate"
    TASK_START = "task_start"
    TASK_END = "task_end"
    TASK_ERROR = "task_error"

    # Tools / MCP
    TOOL_PRE = "tool_pre"
    TOOL_POST = "tool_post"
    TOOL_ERROR = "tool_error"

    # Memory
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"

    # Coordination
    PEER_MESSAGE = "peer_message"
    PLAN_PROPOSED = "plan_proposed"
    PLAN_APPROVED = "plan_approved"
    PLAN_REJECTED = "plan_rejected"

    # Safety
    SECURITY_VIOLATION = "security_violation"
    RATE_LIMIT_HIT = "rate_limit_hit"


class HookPriority(IntEnum):
    """5-level priority (lower number = higher priority)."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    DEFERRED = 4

    @classmethod
    def blocking(cls) -> tuple["HookPriority", ...]:
        """Priorities that should block execution when triggered."""
        return (cls.CRITICAL, cls.HIGH)


__all__ = ["HookEvent", "HookPriority"]
