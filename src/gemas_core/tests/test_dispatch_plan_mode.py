"""Tests for plan_mode integration with dispatch_gema.

Verifies that ``plan_mode=True`` blocks mutator gemas before execution
and that the error returned is structured for the caller (e.g. an
LLM orchestrator) to react appropriately.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict


_RUN = lambda c: asyncio.new_event_loop().run_until_complete(c)

from gemas_core.agents.plan_mode import (
    PLAN_MODE_KNOWN_MUTATORS,
)
from gemas_core.base import GemaBase
from gemas_core.dispatch import dispatch_gema


class FakeMutatorGema(GemaBase):
    name = "fake_mutator"
    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        return {"success": True, "gema": "fake_mutator", "ran": True}


class FakeReadonlyGema(GemaBase):
    name = "fake_readonly"
    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        return {"success": True, "gema": "fake_readonly", "ran": True}


class TestDispatchPlanModeDefault:
    def test_plan_mode_default_off_allows_mutator(self) -> None:
        # Regression: existing callers don't pass plan_mode and shouldn't
        # see new behavior.
        gema = FakeMutatorGema()
        result = _RUN(dispatch_gema(gema, "do thing"))
        assert result["success"] is True
        assert result["ran"] is True

    def test_plan_mode_off_with_mutator_runs_normally(self) -> None:
        gema = FakeMutatorGema()
        result = _RUN(dispatch_gema(gema, "do thing", plan_mode=False))
        assert result["success"] is True


class TestDispatchPlanModeBlocksMutator:
    def test_known_mutator_blocked(self) -> None:
        # Use a real known mutator name so is_mutating_gema is the gate,
        # not our fake's class identity.
        for mutator_name in PLAN_MODE_KNOWN_MUTATORS:
            gema = type(mutator_name, (GemaBase,), {
                "name": mutator_name,
                "execute": lambda self, task, context="": {
                    "success": True, "gema": mutator_name, "ran": True
                },
            })()
            result = _RUN(dispatch_gema(gema, "do thing", plan_mode=True))
            assert result["success"] is False
            assert result["plan_mode_blocked"] is True
            assert "plan mode" in result["error"].lower()
            assert result["gema"] == mutator_name

    def test_fake_mutator_with_known_name_blocked(self) -> None:
        # Use a fake gema that *names itself* after a known mutator.
        # This validates the gate is name-based, not class-based.
        gema = FakeMutatorGema()
        gema.name = "code"  # mutator in the catalog
        result = _RUN(dispatch_gema(gema, "x", plan_mode=True))
        assert result["plan_mode_blocked"] is True

    def test_readonly_gema_runs_in_plan_mode(self) -> None:
        gema = type("scholar", (GemaBase,), {
            "name": "scholar",
            "execute": lambda self, task, context="": {
                "success": True, "gema": "scholar", "ran": True
            },
        })()
        result = _RUN(dispatch_gema(gema, "search for X", plan_mode=True))
        assert result["success"] is True
        assert result["ran"] is True

    def test_unknown_gema_name_blocked_by_default(self) -> None:
        # Fail-closed: a gema with a name not in either allowlist OR
        # the backstop mutator list is treated as a mutator.
        gema = type("mystery_xyz", (GemaBase,), {
            "name": "mystery_xyz",
            "execute": lambda self, task, context="": {
                "success": True, "gema": "mystery_xyz", "ran": True
            },
        })()
        result = _RUN(dispatch_gema(gema, "x", plan_mode=True))
        assert result["plan_mode_blocked"] is True


class TestDispatchDisabledGemasOverride:
    def test_custom_blocklist_overrides_plan_mode(self) -> None:
        # If the caller passes an explicit blocklist, plan_mode defaults
        # are bypassed (the caller is in charge).
        gema = FakeReadonlyGema()
        result = _RUN(dispatch_gema(
            gema, "x", plan_mode=False, disabled_gemas=frozenset({"fake_readonly"}))
        )
        assert result["plan_mode_blocked"] is True

    def test_empty_blocklist_disables_nothing(self) -> None:
        gema = FakeMutatorGema()
        result = _RUN(dispatch_gema(
            gema, "x", plan_mode=False, disabled_gemas=frozenset())
        )
        assert result["success"] is True

    def test_blocklist_takes_precedence_over_plan_mode_false(self) -> None:
        # Caller-supplied blocklist is honored even when plan_mode=False,
        # because it's the explicit override channel.
        gema = FakeMutatorGema()
        result = _RUN(dispatch_gema(
            gema, "x", plan_mode=False, disabled_gemas=frozenset({"fake_mutator"}))
        )
        assert result["plan_mode_blocked"] is True
        assert "blocklist" in result["error"].lower()


class TestDispatchPlanModeEndToEnd:
    def test_mutator_block_returns_full_structured_error(self) -> None:
        gema = FakeMutatorGema()
        gema.name = "code"
        result = _RUN(dispatch_gema(gema, "write a file", plan_mode=True))
        # Caller (orchestrator) needs these fields to react
        assert result["success"] is False
        assert result["gema"] == "code"
        assert result["plan_mode_blocked"] is True
        assert "plan mode" in result["error"].lower()
        # No "ran" field — execution never happened
        assert "ran" not in result
