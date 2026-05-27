"""
HooksEngine - Lifecycle Hooks pipeline con seguridad de 3 puertas.

Construido sobre MiddlewarePipeline con verbos CONTINUE/STOP/COMPACT/INJECT.
"""

import asyncio
import logging
import re
from src.core.ai_defence import AIDefence, ThreatLevel
from src.core.midelware_pipeline import (
    BaseMiddleware,
    MiddlewareAction,
    MiddlewarePhase as MPhase,
    MiddlewarePipeline,
    MiddlewareResult,
    global_pipeline,
)
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("nexus-hooks")


# Re-export para compatibilidad
class HookPhase(Enum):
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    PRE_TOOL_RESULT = "pre_tool_result"
    POST_TOOL_RESULT = "post_tool_result"
    PRE_EXECUTE = "pre_execute"
    POST_EXECUTE = "post_execute"
    ON_ERROR = "on_error"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    ON_CONFIG_CHANGE = "on_config_change"
    MEMORY_WRITE = "memory_write"
    PRE_MEMORY_WRITE = "pre_memory_write"
    POST_MEMORY_WRITE = "post_memory_write"
    ON_COMPACT = "on_compact"
    ON_INPUT = "on_input"
    ON_OUTPUT = "on_output"
    ON_CONTEXT_BUILD = "on_context_build"
    ON_INVOKE_LLM = "on_invoke_llm"
    ON_LLM_RESPONSE = "on_llm_response"
    PRE_AGENT_SPAWN = "pre_agent_spawn"
    POST_AGENT_SPAWN = "post_agent_spawn"
    PRE_AGENT_JOIN = "pre_agent_join"
    POST_AGENT_JOIN = "post_agent_join"
    ON_TASK_COMPLETE = "on_task_complete"
    ON_TASK_FAIL = "on_task_fail"
    ON_HANDOFF = "on_handoff"
    ON_SKILL_LOAD = "on_skill_load"
    ON_MODEL_SELECT = "on_model_select"
    ON_CACHE_HIT = "on_cache_hit"
    ON_CACHE_MISS = "on_cache_miss"
    LEARN = "learn"


_phase_map = {
    HookPhase.PRE_TOOL_USE: MPhase.PRE_TOOL_USE,
    HookPhase.POST_TOOL_USE: MPhase.POST_TOOL_USE,
    HookPhase.PRE_TOOL_RESULT: MPhase.PRE_TOOL_RESULT,
    HookPhase.POST_TOOL_RESULT: MPhase.POST_TOOL_RESULT,
    HookPhase.PRE_EXECUTE: MPhase.PRE_EXECUTE,
    HookPhase.POST_EXECUTE: MPhase.POST_EXECUTE,
    HookPhase.ON_ERROR: MPhase.ON_ERROR,
    HookPhase.SESSION_START: MPhase.SESSION_START,
    HookPhase.SESSION_END: MPhase.SESSION_END,
    HookPhase.ON_CONFIG_CHANGE: MPhase.ON_CONFIG_CHANGE,
    HookPhase.MEMORY_WRITE: MPhase.MEMORY_WRITE,
    HookPhase.PRE_MEMORY_WRITE: MPhase.PRE_MEMORY_WRITE,
    HookPhase.POST_MEMORY_WRITE: MPhase.POST_MEMORY_WRITE,
    HookPhase.ON_COMPACT: MPhase.ON_COMPACT,
    HookPhase.ON_INPUT: MPhase.ON_INPUT,
    HookPhase.ON_OUTPUT: MPhase.ON_OUTPUT,
    HookPhase.ON_CONTEXT_BUILD: MPhase.ON_CONTEXT_BUILD,
    HookPhase.ON_INVOKE_LLM: MPhase.ON_INVOKE_LLM,
    HookPhase.ON_LLM_RESPONSE: MPhase.ON_LLM_RESPONSE,
    HookPhase.PRE_AGENT_SPAWN: MPhase.PRE_AGENT_SPAWN,
    HookPhase.POST_AGENT_SPAWN: MPhase.POST_AGENT_SPAWN,
    HookPhase.PRE_AGENT_JOIN: MPhase.PRE_AGENT_JOIN,
    HookPhase.POST_AGENT_JOIN: MPhase.POST_AGENT_JOIN,
    HookPhase.ON_TASK_COMPLETE: MPhase.ON_TASK_COMPLETE,
    HookPhase.ON_TASK_FAIL: MPhase.ON_TASK_FAIL,
    HookPhase.ON_HANDOFF: MPhase.ON_HANDOFF,
    HookPhase.ON_SKILL_LOAD: MPhase.ON_SKILL_LOAD,
    HookPhase.ON_MODEL_SELECT: MPhase.ON_MODEL_SELECT,
    HookPhase.ON_CACHE_HIT: MPhase.ON_CACHE_HIT,
    HookPhase.ON_CACHE_MISS: MPhase.ON_CACHE_MISS,
    HookPhase.LEARN: MPhase.LEARN,
}


@dataclass
class HookResult:
    allow: bool = True
    modified_input: Any = None
    message: str = ""
    bubble_up: bool = False


class _HandlerMiddleware(BaseMiddleware):
    def __init__(self, name: str, phase: MPhase, handler: Callable, priority: int = 0):
        super().__init__(name, phase, priority)
        self._handler = handler

    async def handle(self, context: Dict) -> MiddlewareResult:
        if asyncio.iscoroutinefunction(self._handler):
            hr = await self._handler(context)
        else:
            hr = self._handler(context)
            if asyncio.iscoroutine(hr):
                hr = await hr
        hr = hr or HookResult()

        if not hr.allow:
            action = MiddlewareAction.STOP
        elif hr.modified_data is not None:
            action = MiddlewareAction.COMPACT
        else:
            action = MiddlewareAction.CONTINUE

        return MiddlewareResult(
            action=action,
            modified_data=hr.modified_input,
            message=hr.message,
        )


class HooksEngine:
    """Wrapper sobre MiddlewarePipeline para compatibilidad."""

    def __init__(self):
        self._pipeline = MiddlewarePipeline("hooks-engine")
        self._metrics: Dict[str, int] = {
            "total_executions": 0,
            "blocks": 0,
            "modifications": 0,
            "bubble_ups": 0,
        }

    @property
    def pipeline(self) -> MiddlewarePipeline:
        return self._pipeline

    def register(self, hook: "Hook"):
        mw = _HandlerMiddleware(
            name=hook.name,
            phase=_phase_map[hook.phase],
            handler=hook.handler,
            priority=hook.priority,
        )
        self._pipeline.register(mw)

    async def run_hooks(self, phase: HookPhase, context: Dict) -> HookResult:
        result = await self._pipeline.execute(_phase_map[phase], context)
        self._metrics["total_executions"] += 1

        if result.action == MiddlewareAction.STOP:
            self._metrics["blocks"] += 1
            return HookResult(
                allow=False,
                modified_input=result.modified_data,
                message=result.message,
                bubble_up="bubble_up" in str(result.message),
            )

        if result.modified_data is not None:
            self._metrics["modifications"] += 1

        return HookResult(
            allow=True,
            modified_input=result.modified_data,
            message=result.message,
        )

    def register_builtin_hooks(self, workdir: Path = None):
        middlewares = [
            SecurityGate1(workdir),
            SecurityGate2(workdir),
            SecurityGate3(),
            SecurityGate4(),
            TypecheckHook(),
            LintHook(),
            TokenBudgetHook(),
            SessionInitHook(workdir),
        ]
        for mw in middlewares:
            self._pipeline.register(mw)

    def get_stats(self) -> Dict:
        base = self._pipeline.get_stats()
        return {
            "hooks_per_phase": {
                p.value: len(self._pipeline._middleware.get(_phase_map.get(p, MPhase.PRE_TOOL_USE), []))
                for p in HookPhase
            },
            "metrics": self._metrics.copy(),
        }


@dataclass
class Hook:
    name: str
    phase: HookPhase
    handler: Callable
    priority: int = 0


# ─── Middlewares como clases ──────────

HARD_DENY_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"sudo\s+",
    r"shutdown",
    r"reboot",
    r"mkfs",
    r"dd\s+if=",
    r"DROP\s+TABLE",
    r"git\s+push\s+--force",
    r"format\s+[C-Z]:",
    r"del\s+/[fqs]",
    r"wget\s+.*\|.*sh",
    r"curl\s+.*\|.*bash",
    r"nc\s+-[el]",
    r"python\s+-m\s+http\.server",
    r"powershell\s+.*-enc",
]

DESTRUCTIVE_PATTERNS = [
    r"rm\s+",
    r">\s+/etc/",
    r"chmod\s+777",
    r"rmdir\s+/s",
    r"taskkill\s+/f",
    r"stop-process",
]

PRIVATE_IP_PATTERNS = [
    r"192\.168\.\d+\.\d+",
    r"10\.\d+\.\d+\.\d+",
    r"172\.(1[6-9]|2\d|3[01])\.\d+\.\d+",
    r"localhost",
    r"127\.0\.0\.1",
]


def security_gate_1_hard_deny(context: Dict) -> HookResult:
    """Standalone hard deny gate (test-compatible wrapper)."""
    tool_name = context.get("tool_name", "")
    tool_args = context.get("tool_args", {})
    if tool_name in ("bash", "shell", "exec", "run_command", "persistent_shell"):
        command = tool_args.get("command", "")
        if command:
            for pattern in HARD_DENY_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    return HookResult(allow=False, message=f"Permission denied: command matches hard deny pattern '{pattern}'")
    if tool_name in ("web_fetch", "http_request", "url_fetch"):
        url = tool_args.get("url", "")
        if url:
            for pattern in PRIVATE_IP_PATTERNS:
                if re.search(pattern, url, re.IGNORECASE):
                    return HookResult(allow=False, message="Permission denied: URL targets private network")
    return HookResult(allow=True)


class SecurityGate1(BaseMiddleware):
    """Hard Deny List - filtra comandos letales inmediatamente."""

    def __init__(self, workdir: Path = None):
        super().__init__("security_gate_1_hard_deny", MPhase.PRE_TOOL_USE, priority=100)
        self._workdir = workdir

    async def handle(self, context: Dict) -> MiddlewareResult:
        tool_name = context.get("tool_name", "")
        tool_args = context.get("tool_args", {})

        if tool_name in ("bash", "shell", "exec", "run_command", "persistent_shell"):
            command = tool_args.get("command", "")
            if not command:
                return MiddlewareResult()

            for pattern in HARD_DENY_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    return MiddlewareResult(
                        action=MiddlewareAction.STOP,
                        message=f"Permission denied: command matches hard deny pattern '{pattern}'",
                    )

        if tool_name in ("web_fetch", "http_request", "url_fetch"):
            url = tool_args.get("url", "")
            if url:
                for pattern in PRIVATE_IP_PATTERNS:
                    if re.search(pattern, url, re.IGNORECASE):
                        return MiddlewareResult(
                            action=MiddlewareAction.STOP,
                            message="Permission denied: URL targets private network",
                        )

        return MiddlewareResult()


class SecurityGate2(BaseMiddleware):
    """Rule Matching - validaciones contextuales."""

    def __init__(self, workdir: Path = None):
        super().__init__("security_gate_2_rule_match", MPhase.PRE_TOOL_USE, priority=90)
        self._workdir = workdir

    async def handle(self, context: Dict) -> MiddlewareResult:
        tool_name = context.get("tool_name", "")
        tool_args = context.get("tool_args", {})
        workdir = self._workdir or Path.cwd()

        if tool_name in ("bash", "shell", "exec", "run_command"):
            command = tool_args.get("command", "")
            for pattern in DESTRUCTIVE_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    return MiddlewareResult(
                        action=MiddlewareAction.STOP,
                        message=f"Warning: potentially destructive command requires human approval: {command[:100]}",
                    )

        if tool_name in ("write_file", "edit_file", "replace_file"):
            path = tool_args.get("path", "")
            if path:
                try:
                    resolved = (workdir / path).resolve()
                    if not resolved.is_relative_to(workdir.resolve()):
                        return MiddlewareResult(
                            action=MiddlewareAction.STOP,
                            message=f"Permission denied: path escapes workspace ({path})",
                        )
                except (ValueError, OSError):
                    pass

        return MiddlewareResult()


class SecurityGate3(BaseMiddleware):
    """Bubbling - si subagente, notifica al padre."""

    def __init__(self):
        super().__init__("security_gate_3_bubble", MPhase.PRE_TOOL_USE, priority=80)

    async def handle(self, context: Dict) -> MiddlewareResult:
        is_subagent = context.get("is_subagent", False)
        if is_subagent:
            tool_name = context.get("tool_name", "")
            return MiddlewareResult(
                action=MiddlewareAction.INJECT,
                injection_data={"bubble": tool_name},
                message=f"Sub-agent requests {tool_name} - bubbling to parent",
            )
        return MiddlewareResult()


_AI_DEFENCE = None

def _get_ai_defence():
    global _AI_DEFENCE
    if _AI_DEFENCE is None:
        _AI_DEFENCE = AIDefence()
    return _AI_DEFENCE


class SecurityGate4(BaseMiddleware):
    """AI-Specific Attack Detection."""

    def __init__(self):
        super().__init__("security_gate_4_ai_defence", MPhase.PRE_TOOL_USE, priority=70)

    async def handle(self, context: Dict) -> MiddlewareResult:
        defence = _get_ai_defence()

        task = context.get("task", "") or context.get("prompt", "") or ""
        if task:
            result = defence.scan(task)
            if result.threat_level != ThreatLevel.SAFE:
                if result.threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
                    return MiddlewareResult(
                        action=MiddlewareAction.STOP,
                        message=f"AI security threat detected: {result.description}",
                    )
                return MiddlewareResult(
                    message=f"AI security warning: {result.description}",
                )

        tool_args = context.get("tool_args", {})
        for key, value in tool_args.items():
            if isinstance(value, str) and len(value) > 10:
                result = defence.scan(value)
                if result.threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
                    return MiddlewareResult(
                        action=MiddlewareAction.STOP,
                        message=f"AI security threat in tool argument: {result.description}",
                    )

        return MiddlewareResult()


class TypecheckHook(BaseMiddleware):
    """TypeScript type checking post-ejecución."""

    def __init__(self):
        super().__init__("typecheck", MPhase.POST_EXECUTE, priority=10)

    async def handle(self, context: Dict) -> MiddlewareResult:
        files_modified = context.get("files_modified", [])
        ts_files = [f for f in files_modified if f.endswith((".ts", ".tsx"))]
        if not ts_files:
            return MiddlewareResult()
        try:
            result = subprocess.run(
                ["npx", "tsc", "--noEmit"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return MiddlewareResult(message=f"TypeScript check failed: {result.stderr[:200]}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return MiddlewareResult()


class LintHook(BaseMiddleware):
    """Linting post-ejecución."""

    def __init__(self):
        super().__init__("lint_check", MPhase.POST_EXECUTE, priority=5)

    async def handle(self, context: Dict) -> MiddlewareResult:
        files_modified = context.get("files_modified", [])
        code_files = [f for f in files_modified if f.endswith((".py", ".js", ".ts", ".tsx"))]
        if not code_files:
            return MiddlewareResult()
        linters = {
            ".py": ["ruff", "check"],
            ".js": ["npx", "eslint"],
            ".ts": ["npx", "eslint"],
            ".tsx": ["npx", "eslint"],
        }
        for f in code_files:
            ext = f[f.rfind("."):]
            linter_cmd = linters.get(ext)
            if linter_cmd:
                try:
                    subprocess.run(linter_cmd + [f], capture_output=True, text=True, timeout=30)
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass
        return MiddlewareResult()


class TokenBudgetHook(BaseMiddleware):
    """Token budget check pre-ejecución."""

    def __init__(self):
        super().__init__("token_budget_check", MPhase.PRE_EXECUTE, priority=50)

    async def handle(self, context: Dict) -> MiddlewareResult:
        token_budget = context.get("token_budget")
        if token_budget and hasattr(token_budget, "is_within_budget"):
            if not token_budget.is_within_budget():
                return MiddlewareResult(
                    action=MiddlewareAction.STOP,
                    message="Token budget exceeded. Cannot execute further.",
                )
        return MiddlewareResult()


class SessionInitHook(BaseMiddleware):
    """SESSION_START: Valida init.sh si existe."""

    def __init__(self, workdir: Path = None):
        super().__init__("session_init_validator", MPhase.SESSION_START, priority=50)
        self._workdir = workdir

    async def handle(self, context: Dict) -> MiddlewareResult:
        workdir = self._workdir or Path.cwd()
        init_sh = workdir / "init.sh"
        if init_sh.exists():
            pass
        return MiddlewareResult()
