"""
permission_manager — 3-level permission gating (goose PermissionManager pattern).

Levels:
    allow   → always permitted (no confirmation)
    ask     → requires HITL confirmation via ConfirmationGate
    never   → always denied

SAFE_DEFAULTS are merged on every load so even a corrupted / missing
permissions.json is fail-closed: unknown actions get the most restrictive
reasonable default.

Persistence: ~/.nexus/permissions.json via atomic_write_json (tempfile+rename).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from src.security.atomic_io import atomic_write_json
from src.security.confirmation_gate import gate as confirmation_gate

logger = logging.getLogger(__name__)

PERMISSIONS_PATH = Path.home() / ".nexus" / "permissions.json"

LEVELS = {"allow", "ask", "never"}

# Actions known to the system. Each maps to its SAFE_DEFAULT.
# When adding a new action ADD it here so PermissionManager knows
# the safe default instead of silently allowing.
KNOWN_ACTIONS: Dict[str, str] = {
    # LatamRust: RCON server commands
    "rcon.wipe":                 "never",
    "rcon.ban":                  "ask",
    "rcon.kick":                 "ask",
    "rcon.unban":                "ask",
    "rcon.list_players":         "allow",
    "rcon.server_info":          "allow",
    "rcon.message":              "allow",
    "rcon.save":                 "allow",
    "rcon.restart":              "ask",
    "rcon.stop":                 "ask",
    # LatamRust: Discord
    "discord.post":              "allow",
    "discord.delete_message":    "ask",
    "discord.ban_member":        "ask",
    "discord.kick_member":       "ask",
    "discord.mute":              "ask",
    # LatamRust: Tebex (transactions)
    "tebex.view_orders":         "allow",
    "tebex.refund":              "ask",
    "tebex.grant_package":       "ask",
    "tebex.revoke_package":      "ask",
    # Memory
    "memory.hard_delete":        "ask",
    "memory.purge_archived":     "ask",
    "memory.purge_all":          "never",
    # Setup
    "setup.reset":               "ask",
    # Shell
    "shell.exec":                "ask",
    # AI (cost-bearing)
    "ai.cloud_call":             "ask",
}


@dataclass(frozen=True)
class PermissionVerdict:
    level: str           # "allow" | "ask" | "never"
    action: str
    from_safe_default: bool = False
    via_override: bool = False
    pending_token: str = ""
    reason: str = ""


class PermissionManager:
    def __init__(self):
        self._rules: Dict[str, Dict[str, str]] = {}
        self._dirty = False
        self._load()

    def _path(self) -> Path:
        return PERMISSIONS_PATH

    def _load(self):
        p = self._path()
        if not p.exists():
            logger.info("permission_manager: no permissions.json yet, using safe defaults")
            self._rules = {}
            return
        try:
            raw = p.read_text("utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("permissions.json root must be a dict")
            validated: Dict[str, Dict[str, str]] = {}
            for gema, actions in data.items():
                if not isinstance(gema, str) or not isinstance(actions, dict):
                    continue
                validated[gema] = {}
                for action, level in actions.items():
                    if isinstance(action, str) and isinstance(level, str) and level in LEVELS:
                        validated[gema][action] = level
            self._rules = validated
            logger.info(f"permission_manager: loaded {sum(len(v) for v in validated.values())} rules")
        except (json.JSONDecodeError, ValueError, OSError) as e:
            # Fail-closed: corrupted JSON → safe defaults only
            logger.error(f"permission_manager: CORRUPTED permissions.json ({e}), using safe defaults only")
            self._rules = {}
            self._dirty = False  # Don't overwrite the corrupt file; user may want to inspect

    def save(self):
        atomic_write_json(self._path(), self._rules)
        logger.info(f"permission_manager: saved {sum(len(v) for v in self._rules.values())} rules")

    def _safe_default(self, action: str) -> str:
        return KNOWN_ACTIONS.get(action, "ask")  # unknown actions default to "ask"

    def check(self, gema: str, action: str) -> PermissionVerdict:
        gema_rules = self._rules.get(gema, {})
        level = gema_rules.get(action)
        if level is not None:
            return PermissionVerdict(
                level=level, action=action,
                via_override=True,
                reason=f"override: {gema}.{action}={level}",
            )
        # Fall back to safe default
        safe = self._safe_default(action)
        return PermissionVerdict(
            level=safe, action=action,
            from_safe_default=True,
            reason=f"safe_default: {action}={safe}",
        )

    def check_and_request(self, gema: str, action: str,
                          context: Optional[dict] = None) -> PermissionVerdict:
        verdict = self.check(gema, action)
        if verdict.level == "allow":
            return verdict
        if verdict.level == "never":
            return PermissionVerdict(
                level="never", action=action,
                from_safe_default=verdict.from_safe_default,
                via_override=verdict.via_override,
                reason=f"blocked: {gema}.{action}=never",
            )
        # level == "ask" → request HITL
        result = confirmation_gate.request(
            op=f"{gema}.{action}",
            payload={"gema": gema, "action": action, **(context or {})},
        )
        if result.get("auto_approved"):
            return PermissionVerdict(
                level="allow", action=action,
                reason="auto_approved (NEXUS_CONFIRM_DISABLED)",
            )
        return PermissionVerdict(
            level="ask", action=action,
            pending_token=result.get("token", ""),
            reason=f"pending confirmation: {result.get('token', '?')[:12]}...",
        )

    def set_rule(self, gema: str, action: str, level: str) -> bool:
        if level not in LEVELS:
            return False
        if action not in KNOWN_ACTIONS:
            # Allow setting rules for unknown actions (future-proof)
            pass
        self._rules.setdefault(gema, {})[action] = level
        self._dirty = True
        return True

    def remove_rule(self, gema: str, action: str) -> bool:
        gema_rules = self._rules.get(gema, {})
        if action not in gema_rules:
            return False
        del gema_rules[action]
        if not gema_rules:
            self._rules.pop(gema, None)
        self._dirty = True
        return True

    def get_rules(self) -> Dict[str, Dict[str, str]]:
        return dict(self._rules)

    def get_known_actions(self) -> Dict[str, str]:
        return dict(KNOWN_ACTIONS)

    def pending(self) -> list:
        return confirmation_gate.pending_list()

    def resolve(self, token: str, approve: bool) -> Dict:
        return confirmation_gate.respond(token, approve)

    @property
    def is_dirty(self) -> bool:
        return self._dirty


manager = PermissionManager()
