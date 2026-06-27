"""Plan mode and active-plan support for the agent loop.

Pattern ported from pewdiepie-archdaemon/odysseus
(``src/agent_loop.py`` and ``src/tool_security.py``).

Two related concepts live here:

1. **Plan mode** — a system-level switch that tells the agent to
   investigate read-only and propose a plan, without mutating. Enforced
   by an allowlist of read-only gemas intersected with an explicit
   backstop of known mutator gemas. Fails closed: an unknown gema
   defaults to *disabled in plan mode*.

2. **Active plan** — once the user approves a plan, the approved
   checklist is re-injected into the system prompt on every turn
   (``build_active_plan_note``). This survives history truncation on
   weak models — the agent can always re-read the plan from the system
   block, not from a possibly-cropped chat history.

The ``update_plan`` helper regenerates a markdown checklist with
``- [x]`` markers for completed steps, so a UI can render live progress
while the agent works.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import FrozenSet, List, Sequence

__all__ = [
    "PLAN_MODE_DIRECTIVE",
    "PLAN_MODE_READONLY_GEMAS",
    "PLAN_MODE_KNOWN_MUTATORS",
    "plan_mode_disabled_gemas",
    "is_mutating_gema",
    "build_active_plan_note",
    "PlanNote",
    "parse_plan_checklist",
    "update_plan",
]


PLAN_MODE_DIRECTIVE = (
    "## PLAN MODE — OVERRIDES EVERYTHING ELSE BELOW\n"
    "You are in PLAN MODE. Your ONLY job this turn is to PROPOSE a plan. You have "
    "NOT done anything yet. Do NOT claim you created, wrote, ran, sent, or changed "
    "anything — that would be a lie.\n"
    "\n"
    "ABSOLUTE RULE — DO NOT MUTATE ANYTHING. Every write/state-changing gema, "
    "including the shell-equivalent gemas, is disabled this turn and will be "
    "rejected — only read-only gemas remain available. Use the read-only gemas "
    "listed below to ground the plan. If the task is 'write a file', your plan is "
    "to DESCRIBE writing it — you do NOT write it now.\n"
    "\n"
    "OUTPUT: present the plan as a GitHub-style checklist, one concrete step per line:\n"
    "- [ ] first action you will take once approved\n"
    "- [ ] next action\n"
    "Each item = one concrete action (file to create/edit, command to run, side "
    "effect). Do not execute. Do not end with 'Done' or anything implying the work "
    "is finished. End your turn with the checklist."
)


# Read-only gemas available in plan mode for investigation.
PLAN_MODE_READONLY_GEMAS: FrozenSet[str] = frozenset({
    "scholar",        # web search / research
    "biblioteca",     # read-only search of indexed documents
    "sage",           # read-only SQLite memory inspection
    "prompter",       # prompt analysis (no LLM call without explicit ollama injection)
})


# Known mutator gemas. Backstop: in plan mode, an unknown gema is also
# treated as a mutator (fail closed). When a new mutating gema is added
# to gemas_core, register it here so plan mode blocks it explicitly
# rather than relying on the unknown-gema backstop alone.
PLAN_MODE_KNOWN_MUTATORS: FrozenSet[str] = frozenset({
    "ayuda",          # exposes the full system catalog (privacy)
    "code",           # code generation / file writes
    "engineer",       # engineering ops
    "devops",         # deployment / infrastructure
    "creative",       # file generation
    "music",          # media generation
    "vision",         # screenshot / screen control
    "design",         # UI/UX generation
    "trainer",        # state-mutating training jobs
    "producer",       # automation / scheduling (cron entries, etc.)
    "debugger",       # debug session (may write state)
})


def plan_mode_disabled_gemas() -> FrozenSet[str]:
    """Return the set of gemas to disable when plan mode is on.

    The contract is allowlist-based in odysseus, but we implement
    denylist-style for parity with the gemas dispatch layer
    (``dispatch_gema`` already iterates a disable list). Unknown
    gemas are NOT enumerated — they fail closed via
    :func:`is_mutating_gema` returning True.
    """
    return PLAN_MODE_KNOWN_MUTATORS


def is_mutating_gema(gema_name: object) -> bool:
    """Return True iff *gema_name* must not run in plan mode.

    Fails CLOSED: ``None``, empty string, non-string input, or any
    unknown name is treated as a mutator. The caller is responsible
    for filtering with this function before allowing execution.
    """
    if not isinstance(gema_name, str) or gema_name == "":
        return True
    if gema_name in PLAN_MODE_KNOWN_MUTATORS:
        return True
    if gema_name in PLAN_MODE_READONLY_GEMAS:
        return False
    # Unknown: fail closed
    return True


def build_active_plan_note(approved_plan: str) -> str:
    """System note that pins an approved plan during execution.

    Sent by the orchestrator on every turn so a long plan on a weak
    model survives history truncation — the agent can always re-read
    the full plan from the system block. Returns ``""`` for empty
    input.
    """
    if not approved_plan or not approved_plan.strip():
        return ""
    return (
        "## ACTIVE PLAN (approved — execute this)\n"
        "You are executing a plan the user already approved. THE FULL PLAN IS "
        "BELOW — it is always provided here every turn. Do NOT say you lost it, "
        "and do NOT look for it in tasks, notes, memory, files, or the API; just "
        "read it below. Work through it IN ORDER. After finishing each step, call "
        "the `update_plan` helper with the full checklist and that step marked "
        "`- [x]` so progress stays visible. If the user asks to change the plan, "
        "regenerate the revised checklist and call `update_plan`. Do the next "
        "unchecked item until all are done. Do not skip, reorder, or invent steps; "
        "if a step is genuinely impossible, say so and stop.\n\n"
        "Current plan:\n"
        + approved_plan.strip()
    )


# Matches a single checklist line: "- [ ] text" or "- [x] text" / "- [X] text".
# Captures the text portion (without the checkbox marker).
_CHECKLIST_RE = re.compile(r"^\s*-\s+\[(?:[ xX])\]\s+(.+?)\s*$", re.MULTILINE)


def parse_plan_checklist(text: str) -> List[str]:
    """Extract checklist items from markdown text.

    Returns the text portion of each ``- [ ] item`` or ``- [x] item``
    line, preserving order. Lines that don't match the checklist
    format are ignored. Returns an empty list if no checklist is found
    or the input is empty.
    """
    if not text:
        return []
    return [m.group(1) for m in _CHECKLIST_RE.finditer(text)]


def update_plan(
    items: Sequence[str], completed: Sequence[int]
) -> str:
    """Regenerate a markdown checklist with ``- [x]`` for completed indices.

    Indices in *completed* that fall outside ``range(len(items))`` are
    silently ignored. Returns an empty string if *items* is empty.
    """
    if not items:
        return ""
    completed_set = {i for i in completed if 0 <= i < len(items)}
    lines: List[str] = []
    for i, item in enumerate(items):
        marker = "x" if i in completed_set else " "
        lines.append(f"- [{marker}] {item}")
    return "\n".join(lines)


@dataclass
class PlanNote:
    """Lightweight container for an in-flight approved plan.

    Carries the approved plan text plus a step cursor so callers can
    render progress without re-parsing the checklist every turn.
    """

    approved_plan: str
    step_index: int = 0
    total_steps: int = 0

    def to_system_prompt(self) -> str:
        """Render the plan as a system-prompt block."""
        body = build_active_plan_note(self.approved_plan)
        if not body:
            return ""
        progress = (
            f"\nProgress: {self.step_index}/{self.total_steps} steps complete."
        )
        return body + progress

    @property
    def progress_fraction(self) -> float:
        """Return progress as a fraction in [0.0, 1.0] (0 if total_steps == 0)."""
        if self.total_steps <= 0:
            return 0.0
        return min(1.0, max(0.0, self.step_index / self.total_steps))
