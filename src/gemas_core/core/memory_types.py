"""v1.7.0 — memory_types: MemoryType + AccessLevel + DistanceMetric enums.

Ports the protocol-contract subset of RUFLO v3's
`@claude-flow/memory/src/types.ts` to gemas_core. These enums are
the taxonomy that backends and consumers agree on; they don't
introduce any new runtime, they just name the values.

Cross-version constraint: NEVER replace existing
hierarchical_memory tiers — these enums are ADDITIVE and used for
external API contracts (e.g. a memory entry's claimed
`memory_type` field); internal storage stays as it is.
"""
from __future__ import annotations

from enum import Enum

try:
    from enum import StrEnum
except ImportError:  # Python < 3.11
    # Polyfill: str-valued enum. Members compare and serialize as
    # their string value. str + Enum (not IntEnum — can't mix two
    # data types in Python's enum machinery).
    class StrEnum(str, Enum):
        """str + Enum polyfill for Python < 3.11."""

        def __new__(cls, value):
            obj = str.__new__(cls, value)
            obj._value_ = value
            return obj

        def __str__(self) -> str:
            return self._value_


class MemoryType(StrEnum):
    """Taxonomy of memory entry kinds (RUFLO ADR-006)."""

    FACT = "fact"
    EPISODE = "episode"
    SKILL = "skill"
    PATTERN = "pattern"
    INTENT = "intent"
    OBSERVATION = "observation"
    PLAN = "plan"
    CHECKPOINT = "checkpoint"
    PREFERENCE = "preference"
    TASK_RESULT = "task_result"

    @classmethod
    def persistent(cls) -> tuple["MemoryType", ...]:
        """Memory types that should be persisted across sessions."""
        return (
            cls.FACT, cls.SKILL, cls.PATTERN, cls.PREFERENCE,
            cls.PLAN, cls.TASK_RESULT,
        )

    @classmethod
    def transient(cls) -> tuple["MemoryType", ...]:
        """Memory types that live only for the current session."""
        return (cls.EPISODE, cls.INTENT, cls.OBSERVATION, cls.CHECKPOINT)


class AccessLevel(StrEnum):
    """Visibility scope of a memory entry."""

    PRIVATE = "private"   # only the writing agent
    TEAM = "team"        # all agents in the same project
    PUBLIC = "public"    # all agents across projects
    SHARED = "shared"    # explicit peer allowlist

    @classmethod
    def ordered(cls) -> tuple["AccessLevel", ...]:
        """Return levels from most-restrictive to least-restrictive."""
        return (cls.PRIVATE, cls.TEAM, cls.SHARED, cls.PUBLIC)


class DistanceMetric(StrEnum):
    """Distance/similarity metric for vector recall."""

    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT = "dot"
    MANHATTAN = "manhattan"


__all__ = ["MemoryType", "AccessLevel", "DistanceMetric"]
