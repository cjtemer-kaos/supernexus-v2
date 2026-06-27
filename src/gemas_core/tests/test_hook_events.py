"""v1.7.0 — hook_events: enum contract tests."""
import pytest

from gemas_core.core.hook_events import HookEvent, HookPriority


class TestHookEvent:
    def test_count_is_19(self):
        assert len(HookEvent) == 19

    def test_lifecycle_events(self):
        assert HookEvent.SESSION_START == "session_start"
        assert HookEvent.SESSION_END == "session_end"
        assert HookEvent.SESSION_RESUME == "session_resume"

    def test_agent_events(self):
        assert HookEvent.AGENT_INIT == "agent_init"
        assert HookEvent.AGENT_TERMINATE == "agent_terminate"
        assert HookEvent.TASK_START == "task_start"
        assert HookEvent.TASK_END == "task_end"
        assert HookEvent.TASK_ERROR == "task_error"

    def test_tool_events(self):
        assert HookEvent.TOOL_PRE == "tool_pre"
        assert HookEvent.TOOL_POST == "tool_post"
        assert HookEvent.TOOL_ERROR == "tool_error"

    def test_memory_events(self):
        assert HookEvent.MEMORY_READ == "memory_read"
        assert HookEvent.MEMORY_WRITE == "memory_write"

    def test_coordination_events(self):
        assert HookEvent.PEER_MESSAGE == "peer_message"
        assert HookEvent.PLAN_PROPOSED == "plan_proposed"
        assert HookEvent.PLAN_APPROVED == "plan_approved"
        assert HookEvent.PLAN_REJECTED == "plan_rejected"

    def test_safety_events(self):
        assert HookEvent.SECURITY_VIOLATION == "security_violation"
        assert HookEvent.RATE_LIMIT_HIT == "rate_limit_hit"

    def test_total_counts_per_category(self):
        lifecycle = ["SESSION_START", "SESSION_END", "SESSION_RESUME"]
        agent = ["AGENT_INIT", "AGENT_TERMINATE", "TASK_START", "TASK_END", "TASK_ERROR"]
        tool = ["TOOL_PRE", "TOOL_POST", "TOOL_ERROR"]
        memory = ["MEMORY_READ", "MEMORY_WRITE"]
        coord = ["PEER_MESSAGE", "PLAN_PROPOSED", "PLAN_APPROVED", "PLAN_REJECTED"]
        safety = ["SECURITY_VIOLATION", "RATE_LIMIT_HIT"]
        total = sum(len(c) for c in [lifecycle, agent, tool, memory, coord, safety])
        assert total == 19
        assert total == len(HookEvent)

    def test_lookup_by_value(self):
        assert HookEvent("session_start") is HookEvent.SESSION_START

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            HookEvent("not_a_real_event")


class TestHookPriority:
    def test_count_is_5(self):
        assert len(HookPriority) == 5

    def test_values_are_zero_indexed(self):
        assert HookPriority.CRITICAL == 0
        assert HookPriority.HIGH == 1
        assert HookPriority.NORMAL == 2
        assert HookPriority.LOW == 3
        assert HookPriority.DEFERRED == 4

    def test_blocking_returns_high_priority(self):
        blocking = HookPriority.blocking()
        assert HookPriority.CRITICAL in blocking
        assert HookPriority.HIGH in blocking
        assert HookPriority.NORMAL not in blocking
        assert HookPriority.LOW not in blocking
        assert HookPriority.DEFERRED not in blocking
        assert len(blocking) == 2

    def test_lower_number_means_higher_priority(self):
        assert HookPriority.CRITICAL < HookPriority.HIGH
        assert HookPriority.HIGH < HookPriority.NORMAL
        assert HookPriority.NORMAL < HookPriority.LOW
        assert HookPriority.LOW < HookPriority.DEFERRED

    def test_int_enum(self):
        # IntEnum members behave as ints
        assert int(HookPriority.CRITICAL) == 0
        assert HookPriority.CRITICAL + 1 == HookPriority.HIGH
