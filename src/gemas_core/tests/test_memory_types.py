"""v1.7.0 — memory_types: enum contract tests."""
import pytest

from gemas_core.core.memory_types import (
    AccessLevel,
    DistanceMetric,
    MemoryType,
)


class TestMemoryType:
    def test_count(self):
        assert len(MemoryType) == 10

    def test_values(self):
        assert MemoryType.FACT == "fact"
        assert MemoryType.EPISODE == "episode"
        assert MemoryType.SKILL == "skill"
        assert MemoryType.PATTERN == "pattern"
        assert MemoryType.INTENT == "intent"
        assert MemoryType.OBSERVATION == "observation"
        assert MemoryType.PLAN == "plan"
        assert MemoryType.CHECKPOINT == "checkpoint"
        assert MemoryType.PREFERENCE == "preference"
        assert MemoryType.TASK_RESULT == "task_result"

    def test_is_str_enum(self):
        # StrEnum members behave as their string value
        assert MemoryType.FACT == "fact"
        # The polyfill returns the string value for str(member)
        # (true stdlib StrEnum does the same in 3.11+).
        assert str(MemoryType.FACT) == "fact"
        # repr gives the enum-qualified name
        assert "FACT" in repr(MemoryType.FACT)

    def test_persistent(self):
        persistent = MemoryType.persistent()
        assert MemoryType.FACT in persistent
        assert MemoryType.SKILL in persistent
        assert MemoryType.PATTERN in persistent
        assert MemoryType.PREFERENCE in persistent
        assert MemoryType.PLAN in persistent
        assert MemoryType.TASK_RESULT in persistent
        assert MemoryType.EPISODE not in persistent
        assert len(persistent) == 6

    def test_transient(self):
        transient = MemoryType.transient()
        assert MemoryType.EPISODE in transient
        assert MemoryType.INTENT in transient
        assert MemoryType.OBSERVATION in transient
        assert MemoryType.CHECKPOINT in transient
        assert MemoryType.FACT not in transient
        assert len(transient) == 4

    def test_persistent_and_transient_disjoint(self):
        assert set(MemoryType.persistent()).isdisjoint(set(MemoryType.transient()))

    def test_persistent_and_transient_cover_all(self):
        all_types = set(MemoryType)
        assert set(MemoryType.persistent()) | set(MemoryType.transient()) == all_types

    def test_lookup_by_value(self):
        assert MemoryType("fact") is MemoryType.FACT

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            MemoryType("unknown_thing")


class TestAccessLevel:
    def test_count(self):
        assert len(AccessLevel) == 4

    def test_values(self):
        assert AccessLevel.PRIVATE == "private"
        assert AccessLevel.TEAM == "team"
        assert AccessLevel.PUBLIC == "public"
        assert AccessLevel.SHARED == "shared"

    def test_ordered_most_to_least_restrictive(self):
        ordered = AccessLevel.ordered()
        assert ordered[0] == AccessLevel.PRIVATE
        assert ordered[-1] == AccessLevel.PUBLIC

    def test_lookup_by_value(self):
        assert AccessLevel("public") is AccessLevel.PUBLIC


class TestDistanceMetric:
    def test_count(self):
        assert len(DistanceMetric) == 4

    def test_values(self):
        assert DistanceMetric.COSINE == "cosine"
        assert DistanceMetric.EUCLIDEAN == "euclidean"
        assert DistanceMetric.DOT == "dot"
        assert DistanceMetric.MANHATTAN == "manhattan"
