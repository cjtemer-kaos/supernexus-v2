"""Tests for gemas_core.agents.plan_mode.

Pattern ported from pewdiepie-archdaemon/odysseus
(``src/agent_loop.py`` and ``src/tool_security.py``).

Plan mode: the agent may investigate (read-only) but must not
mutate. In the odysseus reference this is enforced via a tool
allowlist that intersects with an explicit mutator backstop, plus
a system directive that overrides everything else. In our gem-based
world, "tools" are gemas, and the same principle applies: a curated
allowlist of read-only gemas + a curated backstop of known mutator
gemas, with a system directive that frames the agent's response.

The "active plan" pattern complements plan mode: once the user
approves a plan, the approved checklist is re-injected into the
system prompt on every turn so a long plan on a weak model
survives history truncation.
"""

from __future__ import annotations


from gemas_core.agents.plan_mode import (
    PLAN_MODE_DIRECTIVE,
    PLAN_MODE_KNOWN_MUTATORS,
    PLAN_MODE_READONLY_GEMAS,
    PlanNote,
    build_active_plan_note,
    is_mutating_gema,
    parse_plan_checklist,
    plan_mode_disabled_gemas,
    update_plan,
)


class TestPlanModeDirective:
    def test_directive_is_nonempty_string(self) -> None:
        assert isinstance(PLAN_MODE_DIRECTIVE, str)
        assert len(PLAN_MODE_DIRECTIVE) > 100

    def test_directive_overrides_everything_else(self) -> None:
        # The directive starts by stating it overrides everything below it
        # — this is critical for the model to honor it when the rest of
        # the system prompt suggests otherwise.
        assert "OVERRIDES EVERYTHING" in PLAN_MODE_DIRECTIVE

    def test_directive_forbids_mutation(self) -> None:
        assert "DO NOT MUTATE" in PLAN_MODE_DIRECTIVE
        assert "do not" in PLAN_MODE_DIRECTIVE.lower()

    def test_directive_requires_checklist_output(self) -> None:
        # The output format is GitHub-style markdown checklist
        assert "checklist" in PLAN_MODE_DIRECTIVE.lower()
        assert "- [ ]" in PLAN_MODE_DIRECTIVE

    def test_directive_forbids_premature_done(self) -> None:
        # Common failure mode: model writes "Done" and stops. The
        # directive explicitly forbids that.
        assert "Done" in PLAN_MODE_DIRECTIVE or "do not end" in PLAN_MODE_DIRECTIVE.lower()


class TestReadonlyAndMutatorSets:
    def test_readonly_is_a_set(self) -> None:
        assert isinstance(PLAN_MODE_READONLY_GEMAS, frozenset)
        assert len(PLAN_MODE_READONLY_GEMAS) > 0

    def test_known_mutators_is_a_set(self) -> None:
        assert isinstance(PLAN_MODE_KNOWN_MUTATORS, frozenset)
        assert len(PLAN_MODE_KNOWN_MUTATORS) > 0

    def test_readonly_and_mutators_do_not_intersect(self) -> None:
        # A gema can't be both read-only and mutating
        assert (
            PLAN_MODE_READONLY_GEMAS & PLAN_MODE_KNOWN_MUTATORS
        ) == set()


class TestPlanModeDisabledGemas:
    def test_returns_frozenset(self) -> None:
        disabled = plan_mode_disabled_gemas()
        assert isinstance(disabled, frozenset)

    def test_mutators_are_disabled(self) -> None:
        disabled = plan_mode_disabled_gemas()
        # All known mutators MUST be disabled in plan mode
        for mutator in PLAN_MODE_KNOWN_MUTATORS:
            assert mutator in disabled, f"{mutator} not disabled in plan mode"

    def test_readonly_gemas_are_NOT_disabled(self) -> None:
        disabled = plan_mode_disabled_gemas()
        # Allowlist stays available — but ONLY for inspection
        for read in PLAN_MODE_READONLY_GEMAS:
            assert read not in disabled, f"{read} wrongly disabled in plan mode"


class TestIsMutatingGema:
    def test_known_mutator_returns_true(self) -> None:
        for mutator in PLAN_MODE_KNOWN_MUTATORS:
            assert is_mutating_gema(mutator) is True

    def test_readonly_returns_false(self) -> None:
        for read in PLAN_MODE_READONLY_GEMAS:
            assert is_mutating_gema(read) is False

    def test_unknown_defaults_to_true(self) -> None:
        # Fail CLOSED: an unknown gema name is treated as a mutator
        # (better to over-block than to allow an unknown tool to write)
        assert is_mutating_gema("totally_unknown_gema_xyz") is True

    def test_empty_string_defaults_to_true(self) -> None:
        assert is_mutating_gema("") is True

    def test_non_string_defaults_to_true(self) -> None:
        assert is_mutating_gema(None) is True  # type: ignore[arg-type]
        assert is_mutating_gema(42) is True  # type: ignore[arg-type]


class TestBuildActivePlanNote:
    def test_empty_plan_returns_empty_string(self) -> None:
        assert build_active_plan_note("") == ""
        assert build_active_plan_note("   \n  ") == ""

    def test_nonempty_plan_returns_header_plus_body(self) -> None:
        note = build_active_plan_note("- [ ] step 1\n- [ ] step 2")
        assert "ACTIVE PLAN" in note
        assert "- [ ] step 1" in note
        assert "- [ ] step 2" in note

    def test_header_includes_update_plan_instruction(self) -> None:
        # The note tells the model to call update_plan to report progress
        note = build_active_plan_note("- [ ] x")
        assert "update_plan" in note

    def test_strips_whitespace_around_plan(self) -> None:
        note = build_active_plan_note("  \n  - [ ] x  \n  ")
        # The plan is trimmed before insertion
        assert "- [ ] x" in note
        # No leading/trailing whitespace leak
        assert note.endswith("x") or note.endswith("x\n")

    def test_invariant_for_history_truncation(self) -> None:
        # The note must contain the FULL plan verbatim, not a summary,
        # so the model can re-read it after history truncation.
        plan = "- [ ] a\n- [ ] b\n- [ ] c\n- [ ] d\n- [ ] e"
        note = build_active_plan_note(plan)
        for line in plan.split("\n"):
            assert line in note


class TestParsePlanChecklist:
    def test_parses_simple_checklist(self) -> None:
        text = "- [ ] first\n- [ ] second\n- [ ] third"
        items = parse_plan_checklist(text)
        assert items == ["first", "second", "third"]

    def test_parses_mixed_checked_unchecked(self) -> None:
        text = "- [x] done\n- [ ] todo\n- [X] also done"
        items = parse_plan_checklist(text)
        assert items == ["done", "todo", "also done"]

    def test_ignores_non_checklist_lines(self) -> None:
        text = "Here is my plan:\n\n- [ ] one\n- [ ] two\n\nThat's it."
        items = parse_plan_checklist(text)
        assert items == ["one", "two"]

    def test_handles_no_checklist(self) -> None:
        text = "I'm thinking about it."
        assert parse_plan_checklist(text) == []

    def test_handles_empty_string(self) -> None:
        assert parse_plan_checklist("") == []

    def test_strips_checkbox_marker(self) -> None:
        items = parse_plan_checklist("- [ ]  extra spaces around  ")
        assert items == ["extra spaces around"]

    def test_tolerates_unicode(self) -> None:
        text = "- [ ] Escribir README en español\n- [ ] 添加测试"
        items = parse_plan_checklist(text)
        assert items == ["Escribir README en español", "添加测试"]


class TestUpdatePlan:
    def test_marks_indices_completed(self) -> None:
        items = ["a", "b", "c"]
        out = update_plan(items, completed=[1])
        assert "- [x] b" in out
        assert "- [ ] a" in out
        assert "- [ ] c" in out

    def test_marks_all_completed(self) -> None:
        items = ["x", "y"]
        out = update_plan(items, completed=[0, 1])
        assert "- [x] x" in out
        assert "- [x] y" in out
        # No unchecked items left
        assert "- [ ]" not in out

    def test_empty_completed_keeps_all_unchecked(self) -> None:
        items = ["a", "b"]
        out = update_plan(items, completed=[])
        assert "- [ ] a" in out
        assert "- [ ] b" in out

    def test_out_of_range_indices_ignored(self) -> None:
        items = ["a", "b"]
        out = update_plan(items, completed=[5, -1, 0])
        # Only index 0 is valid; 5 and -1 are out of range
        assert "- [x] a" in out
        assert "- [ ] b" in out

    def test_empty_items_returns_empty(self) -> None:
        assert update_plan([], completed=[]) == ""


class TestPlanNoteDataclass:
    def test_construction(self) -> None:
        note = PlanNote(approved_plan="- [ ] x", step_index=0, total_steps=3)
        assert note.approved_plan == "- [ ] x"
        assert note.step_index == 0
        assert note.total_steps == 3

    def test_to_system_prompt_includes_active_note(self) -> None:
        note = PlanNote(approved_plan="- [ ] do thing", step_index=1, total_steps=2)
        prompt = note.to_system_prompt()
        assert "ACTIVE PLAN" in prompt
        assert "do thing" in prompt

    def test_to_system_prompt_includes_progress(self) -> None:
        note = PlanNote(approved_plan="- [ ] x", step_index=2, total_steps=5)
        prompt = note.to_system_prompt()
        assert "2" in prompt  # step_index
        assert "5" in prompt  # total_steps

    def test_progress_fraction(self) -> None:
        note = PlanNote(approved_plan="x", step_index=1, total_steps=4)
        assert note.progress_fraction == 0.25
