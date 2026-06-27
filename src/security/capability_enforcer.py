"""
capability_enforcer — Opt-in gating for declared gema capabilities.

Pattern (openfang CapabilityManager, MVP enforcement step).

State today: capabilities are DECLARED via MANIFEST['capabilities']
(see src/plugins/manifest.py:GemaPlugin.has_capability). This module adds
the gate so the declaration becomes an actual security boundary — only
when the operator opts in.

Activation:
    NEXUS_ENFORCE_CAPS=1   enforce; missing cap → deny + emit SEC event
    NEXUS_ENFORCE_CAPS=0   (default) declarative only — log + permit

Tool → required capability mapping is opinionated and conservative. New
tools default to NO required cap (permitted) until the operator adds
them to the table here. This keeps the gate behavioral-additive: we
never *suddenly* break a tool we haven't classified yet.

Usage:

    from src.security.capability_enforcer import check_call

    verdict = check_call(gema_name="code", tool_name="shell_exec", gemas=gemas)
    if not verdict.allowed:
        return {"error": verdict.reason, "denied_by": "capability_enforcer"}

`verdict.required_cap` and `verdict.declared_caps` are exposed so the
caller can present a useful error to the user / model.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from src.plugins.manifest import GemaPlugin

logger = logging.getLogger(__name__)


# Tool prefix → required capability. Most-specific match wins (longest
# prefix). Empty string means "no required cap" (always allowed).
#
# Vocabulary deliberately overlaps with src/plugins/manifest.py docstring.
TOOL_CAP_MAP: Dict[str, str] = {
    # File system
    "read_file":          "fs.read.user",
    "list_files":         "fs.read.user",
    "search_code":        "fs.read.user",
    "write_file":         "fs.write.user",
    "edit_file":          "fs.write.user",
    "delete_file":        "fs.write.user",
    # Shell
    "execute_command":    "shell.exec",
    "shell_exec":         "shell.exec",
    "subprocess":         "shell.exec",
    # Network
    "web_search":         "net.fetch",
    "web_fetch":          "net.fetch",
    "web_navigate":       "net.fetch",
    "fetch":              "net.fetch",
    # Browser (heavier — both net + shell-ish)
    "browser":            "net.fetch",
    "browser_snapshot":   "net.fetch",
    "browser_interact":   "net.fetch",
    # MCP
    "mcp_call":           "mcp.call",
    "list_mcp_tools":     "mcp.call",
    # Memory persistence
    "add_observation":    "memory.write",
    "add_episode":        "memory.write",
    "delete_observation": "memory.write",
    # Cloud LLM (cost-bearing)
    "ai_call_cloud":      "llm.cloud",
}


@dataclass(frozen=True)
class Verdict:
    allowed: bool
    reason: str
    required_cap: Optional[str] = None
    declared_caps: tuple = ()
    enforced: bool = False  # True if NEXUS_ENFORCE_CAPS=1 was active


def enforcement_active() -> bool:
    """Read the env flag fresh each call so flipping the toggle takes
    effect without restart in unit tests / runtime adjustments."""
    return os.environ.get("NEXUS_ENFORCE_CAPS", "0") == "1"


def required_capability(tool_name: str) -> Optional[str]:
    """Look up the required cap for a tool. Longest-prefix match.
    Returns None when the tool has no declared requirement (permitted).
    """
    if not tool_name:
        return None
    # Exact match wins
    if tool_name in TOOL_CAP_MAP:
        return TOOL_CAP_MAP[tool_name] or None
    # Prefix match (e.g. 'browser_take_screenshot' → 'browser_')
    best_key = ""
    for key in TOOL_CAP_MAP:
        if tool_name.startswith(key) and len(key) > len(best_key):
            best_key = key
    if best_key:
        return TOOL_CAP_MAP[best_key] or None
    return None


def check_call(
    gema_name: str,
    tool_name: str,
    gemas: Dict[str, "GemaPlugin"],
    *,
    request_id: Optional[str] = None,
) -> Verdict:
    """Decide whether `gema_name` can call `tool_name`.

    - If the tool has no required cap → allow.
    - If gema has the cap declared (prefix-aware) → allow.
    - Otherwise: enforcement_active() determines outcome.

    Emits SEC_INJECTION_BLOCKED on the event bus when a call is DENIED
    (only when enforcement is active — declarative-only mode just logs).
    """
    cap = required_capability(tool_name)
    if cap is None:
        return Verdict(allowed=True, reason="no_required_capability", enforced=False)

    gema = gemas.get(gema_name) if gemas else None
    declared = tuple(getattr(gema, "capabilities", []) or [])

    has = bool(gema and gema.has_capability(cap)) if gema else False

    if has:
        return Verdict(
            allowed=True, reason="capability_declared",
            required_cap=cap, declared_caps=declared, enforced=enforcement_active(),
        )

    # Missing capability
    enforced = enforcement_active()
    reason = f"gema '{gema_name}' lacks required capability '{cap}'"
    if enforced:
        try:
            from src.observability.event_stream import emit, EventType
            emit(EventType.SEC_INJECTION_BLOCKED,
                 data={"gema": gema_name, "tool": tool_name,
                       "required_cap": cap, "declared_caps": list(declared),
                       "mode": "enforced"},
                 request_id=request_id, source="capability_enforcer")
        except Exception:
            pass
        logger.warning(f"capability_enforcer DENY: {reason}")
        return Verdict(
            allowed=False, reason=reason, required_cap=cap,
            declared_caps=declared, enforced=True,
        )
    else:
        logger.info(f"capability_enforcer would-deny (declarative-only): {reason}")
        return Verdict(
            allowed=True, reason=f"{reason} (declarative_only — not enforced)",
            required_cap=cap, declared_caps=declared, enforced=False,
        )


def audit_all(gemas: Dict[str, "GemaPlugin"]) -> Dict[str, List[str]]:
    """For each gema, return the list of TOOL_CAP_MAP tools it CAN'T call
    given its current declared caps. Useful for the UI / a doctor check
    before flipping enforcement on globally."""
    out: Dict[str, List[str]] = {}
    if not gemas:
        return out
    for name, g in gemas.items():
        missing: List[str] = []
        for tool, cap in TOOL_CAP_MAP.items():
            if not cap:
                continue
            if not g.has_capability(cap):
                missing.append(tool)
        if missing:
            out[name] = sorted(missing)
    return out
