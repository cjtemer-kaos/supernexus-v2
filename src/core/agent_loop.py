"""
Agent Loop — Think-Decide-Act-Observe pattern.
From: autonomous-agent-patterns skill (Cline/Codex inspired).

Used by DirectorNexus for complex multi-step tasks that require
iteration and self-correction.

Error Classification:
- RETRY: Transient errors (timeout, rate limit, network)
- SKIP: Non-critical errors (missing optional file, deprecated tool)
- REPLAN: Logic errors (wrong approach, bad parameters)
- ABORT: Fatal errors (permission denied, invalid state, corruption)
"""

import asyncio
import logging
import re
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorAction(Enum):
    """Error classification actions."""
    RETRY = "retry"      # Transient - try again
    SKIP = "skip"        # Non-critical - continue without
    REPLAN = "replan"    # Logic error - change approach
    ABORT = "abort"      # Fatal - stop immediately


@dataclass
class ToolResult:
    success: bool
    output: str = ""
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoopStep:
    iteration: int
    phase: str  # think, decide, act, observe
    content: str
    tool_used: Optional[str] = None
    result: Optional[ToolResult] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class AgentLoopResult:
    task: str
    success: bool
    final_output: str
    steps: List[LoopStep]
    iterations: int
    total_tokens: int = 0
    total_duration_ms: float = 0


class AgentLoop:
    """
    Think-Decide-Act-Observe loop for autonomous task execution.

    Multi-model routing:
    - fast (nemotron/qwen:0.5b): planning, classification
    - smart (deepseek-r1:8b): reasoning, analysis
    - code (qwen2.5-coder:7b): code generation

    Sprint Contract: Define done condition before loop starts.
    Takeover: Pause after 3 consecutive errors.
    Error Classification: RETRY/SKIP/REPLAN/ABORT.
    """

    MODEL_ROUTING = {
        "fast": "qwen2.5:0.5b",
        "smart": "deepseek-r1:8b",
        "code": "qwen2.5-coder:7b",
    }

    MAX_CONSECUTIVE_ERRORS = 3

    # Error classification patterns
    ERROR_PATTERNS = {
        ErrorAction.RETRY: [
            r"timeout",
            r"rate.?limit",
            r"too many requests",
            r"connection (refused|reset|closed)",
            r"network (error|unreachable)",
            r"temporary failure",
            r"service unavailable",
            r"5\d{2}",  # HTTP 5xx errors
        ],
        ErrorAction.SKIP: [
            r"file not found.*optional",
            r"deprecated",
            r"not implemented",
            r"skipping",
            r"optional.*not available",
            r"no such file.*continuing",
        ],
        ErrorAction.REPLAN: [
            r"invalid (parameter|argument|input)",
            r"wrong (approach|method|strategy)",
            r"cannot (process|handle|parse)",
            r"unexpected (format|type|value)",
            r"parsing? error",
            r"validation failed",
        ],
        ErrorAction.ABORT: [
            r"permission denied",
            r"access denied",
            r"unauthorized",
            r"forbidden",
            r"corrupt(ed)? (data|file|state)",
            r"fatal error",
            r"critical failure",
            r"out of memory",
            r"disk full",
            r"segfault",
            r"stack overflow",
        ],
    }

    def __init__(
        self,
        llm_fn: Callable,
        tools: Optional[Dict[str, Callable]] = None,
        max_iterations: int = 10,
        max_retries: int = 2,
        workdir: str = None,
    ):
        self.llm_fn = llm_fn
        self.tools = tools or {}
        self.max_iterations = max_iterations
        self.max_retries = max_retries
        self.workdir = workdir
        self._error_compactor = None

    def _get_error_compactor(self):
        if self._error_compactor is None:
            try:
                from src.core.error_compactor import ErrorCompactor
                self._error_compactor = ErrorCompactor()
            except Exception:
                pass
        return self._error_compactor

    def classify_error(self, error_message: str) -> ErrorAction:
        """
        Classify error using pattern matching.
        Returns RETRY/SKIP/REPLAN/ABORT action.
        """
        error_lower = error_message.lower()

        for action, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error_lower):
                    logger.info(f"Error classified as {action.value}: {error_message[:100]}")
                    return action

        # Default: RETRY for unknown errors
        logger.warning(f"Unknown error pattern, defaulting to RETRY: {error_message[:100]}")
        return ErrorAction.RETRY

    def handle_classified_error(
        self,
        action: ErrorAction,
        error_msg: str,
        consecutive_errors: int,
        retries: int,
    ) -> Dict[str, Any]:
        """
        Handle error based on classification.
        Returns dict with updated counters and next action.
        """
        if action == ErrorAction.RETRY:
            return {
                "consecutive_errors": consecutive_errors + 1,
                "retries": retries + 1,
                "next_action": "retry" if retries < self.max_retries else "replan",
                "message": f"Transient error, retrying ({retries + 1}/{self.max_retries})",
            }

        elif action == ErrorAction.SKIP:
            return {
                "consecutive_errors": 0,  # Reset - non-critical
                "retries": retries,
                "next_action": "continue",
                "message": f"Non-critical error skipped: {error_msg[:100]}",
            }

        elif action == ErrorAction.REPLAN:
            return {
                "consecutive_errors": consecutive_errors + 1,
                "retries": retries,
                "next_action": "replan",
                "message": f"Logic error, need to replan approach",
            }

        elif action == ErrorAction.ABORT:
            return {
                "consecutive_errors": self.MAX_CONSECUTIVE_ERRORS,  # Force takeover
                "retries": retries,
                "next_action": "abort",
                "message": f"Fatal error, aborting: {error_msg[:100]}",
            }

        return {
            "consecutive_errors": consecutive_errors + 1,
            "retries": retries + 1,
            "next_action": "retry",
            "message": "Unknown error handling, defaulting to retry",
        }

    async def run(self, task: str, context: str = "") -> AgentLoopResult:
        """Execute the TDAO loop for a task with Sprint Contract + Takeover."""
        steps: List[LoopStep] = []
        start = datetime.now()
        total_tokens = 0
        retries = 0
        consecutive_errors = 0

        # Sprint Contract: define done condition before loop
        done_condition = await self._generate_done_condition(task)
        steps.append(LoopStep(0, "contract", f"Done condition: {done_condition}"))
        logger.info(f"Sprint contract: {done_condition}")

        for i in range(self.max_iterations):
            # Takeover: pause after 3 consecutive errors
            if consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
                duration = (datetime.now() - start).total_seconds() * 1000
                self._save_ralph_loop(task, steps, "takeover")
                return AgentLoopResult(
                    task=task,
                    success=False,
                    final_output=f"TAKEOVER: {consecutive_errors} consecutive errors. Session paused for human review.",
                    steps=steps,
                    iterations=i + 1,
                    total_tokens=total_tokens,
                    total_duration_ms=duration,
                )

            # THINK
            think_prompt = self._build_think_prompt(task, context, steps)
            thought = await self.llm_fn(think_prompt, self.MODEL_ROUTING["smart"])
            steps.append(LoopStep(i, "think", thought))

            # DECIDE
            decision = await self._decide(thought, task, steps, done_condition)
            steps.append(LoopStep(i, "decide", decision["action"]))

            if decision["action"] == "complete":
                duration = (datetime.now() - start).total_seconds() * 1000
                self._save_ralph_loop(task, steps, "completed")
                return AgentLoopResult(
                    task=task,
                    success=True,
                    final_output=decision.get("output", thought),
                    steps=steps,
                    iterations=i + 1,
                    total_tokens=total_tokens,
                    total_duration_ms=duration,
                )

            if decision["action"] == "use_tool":
                tool_name = decision.get("tool", "")
                tool_args = decision.get("args", {})

                if tool_name in self.tools:
                    try:
                        result = await self._execute_tool(tool_name, tool_args)
                        steps.append(LoopStep(i, "act", f"tool:{tool_name}", tool_name, result))

                        observation = f"Tool '{tool_name}' {'succeeded' if result.success else 'failed'}: {result.output or result.error}"
                        steps.append(LoopStep(i, "observe", observation[:500]))

                        if result.success:
                            consecutive_errors = 0
                        else:
                            consecutive_errors += 1
                            retries += 1
                            if retries >= self.max_retries:
                                break
                    except Exception as e:
                        compactor = self._get_error_compactor()
                        error_msg = compactor.compact(str(e)) if compactor else str(e)
                        steps.append(LoopStep(i, "observe", f"Tool error: {error_msg}"))

                        # Classify error
                        error_action = self.classify_error(str(e))
                        error_handling = self.handle_classified_error(
                            error_action, error_msg, consecutive_errors, retries
                        )

                        consecutive_errors = error_handling["consecutive_errors"]
                        retries = error_handling["retries"]

                        if error_handling["next_action"] == "abort":
                            duration = (datetime.now() - start).total_seconds() * 1000
                            self._save_ralph_loop(task, steps, "aborted")
                            return AgentLoopResult(
                                task=task,
                                success=False,
                                final_output=f"ABORT: {error_handling['message']}",
                                steps=steps,
                                iterations=i + 1,
                                total_tokens=total_tokens,
                                total_duration_ms=duration,
                            )

                        elif error_handling["next_action"] == "replan":
                            steps.append(LoopStep(i, "decide", "REPLAN: Changing approach due to logic error"))
                            # Continue loop - next iteration will replan

                        elif error_handling["next_action"] == "continue":
                            consecutive_errors = 0  # Reset for SKIP
                            steps.append(LoopStep(i, "observe", f"SKIP: {error_handling['message']}"))
                else:
                    steps.append(LoopStep(i, "observe", f"Unknown tool: {tool_name}"))

            elif decision["action"] == "generate":
                model = self.MODEL_ROUTING.get(decision.get("model_type", "smart"), self.MODEL_ROUTING["smart"])
                gen_prompt = decision.get("prompt", task)
                output = await self.llm_fn(gen_prompt, model)
                steps.append(LoopStep(i, "act", f"generate:{model}"))
                steps.append(LoopStep(i, "observe", output[:500]))
                context += f"\n\nGenerated:\n{output[:1000]}"
                consecutive_errors = 0

        duration = (datetime.now() - start).total_seconds() * 1000
        last_output = steps[-1].content if steps else "No output"
        self._save_ralph_loop(task, steps, "max_iterations")
        return AgentLoopResult(
            task=task,
            success=False,
            final_output=last_output,
            steps=steps,
            iterations=self.max_iterations,
            total_tokens=total_tokens,
            total_duration_ms=duration,
        )

    def _build_think_prompt(self, task: str, context: str, steps: List[LoopStep]) -> str:
        """Build the thinking prompt with history."""
        history = ""
        if steps:
            recent = steps[-6:]  # Last 3 iterations
            history = "\n".join(f"[{s.phase}] {s.content[:200]}" for s in recent)

        recent_history = f"Historia reciente:\n{history}" if history else ""
        context_str = f"Contexto: {context[:500]}" if context else ""
        return (
            f"Tarea: {task}\n"
            f"{context_str}\n"
            f"{recent_history}\n\n"
            f"Analiza el estado actual. ¿Qué falta por hacer? ¿Hay errores que corregir? "
            f"Responde en máximo 3 líneas."
        )

    async def _generate_done_condition(self, task: str) -> str:
        """Generate done condition using fast model (Sprint Contract pattern)."""
        prompt = (
            f"Define en 1-2 líneas el criterio exacto para considerar esta tarea completada:\n"
            f"Tarea: {task}\n"
            f"Criterio:"
        )
        try:
            return await self.llm_fn(prompt, self.MODEL_ROUTING["fast"])
        except Exception:
            return f"Task '{task}' is completed when the user's request is fully addressed."

    def _save_ralph_loop(self, task: str, steps: List[LoopStep], status: str):
        """Persist state to .nexus/ralph-loop.local.md for pause/resume."""
        try:
            from pathlib import Path
            nexus_dir = Path.home() / ".nexus"
            nexus_dir.mkdir(parents=True, exist_ok=True)
            loop_file = nexus_dir / "ralph-loop.local.md"
            content = (
                f"# Ralph Loop State\n"
                f"Task: {task[:200]}\n"
                f"Status: {status}\n"
                f"Steps: {len(steps)}\n"
                f"Last step: {steps[-1].content[:200] if steps else 'none'}\n"
                f"Timestamp: {datetime.now().isoformat()}\n"
            )
            loop_file.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save ralph-loop state: {e}")

    async def _decide(self, thought: str, task: str, steps: List[LoopStep], done_condition: str = "") -> Dict[str, Any]:
        """Decide next action based on thinking using structured LLM call with a heuristic fallback."""
        import json
        import re

        # 1. Fallback heuristic logic in a local helper to keep it extremely clean
        def heuristic_fallback() -> Dict[str, Any]:
            logger.info("Using heuristic fallback for decision making")
            thought_lower = thought.lower()
            # Check against sprint contract
            if done_condition and done_condition.lower() in thought_lower:
                return {"action": "complete", "output": thought}
            complete_signals = ["completado", "listo", "done", "terminado", "no falta nada", "todo está"]
            if any(s in thought_lower for s in complete_signals):
                return {"action": "complete", "output": thought}
            code_signals = ["generar código", "escribir", "implementar", "crear función", "code"]
            if any(s in thought_lower for s in code_signals):
                return {"action": "generate", "model_type": "code", "prompt": task}
            for tool_name in self.tools:
                if tool_name.lower() in thought_lower:
                    return {"action": "use_tool", "tool": tool_name, "args": {"task": task}}
            return {"action": "generate", "model_type": "smart", "prompt": task}

        # 2. Attempt LLM-based structured decision
        tools_str = ", ".join(self.tools.keys()) if self.tools else "Ninguna herramienta disponible"
        prompt = (
            f"Determina la siguiente acción para resolver la tarea.\n"
            f"Tarea: {task}\n"
            f"Pensamiento actual del agente: {thought}\n"
            f"Herramientas disponibles: {tools_str}\n\n"
            f"Debes responder ÚNICAMENTE con un objeto JSON válido que siga este esquema exacto:\n"
            f"{{\n"
            f'  "action": "complete" | "use_tool" | "generate",\n'
            f'  "explanation": "Breve explicación de la decisión",\n'
            f'  "tool": "nombre_de_la_herramienta",\n'
            f'  "args": {{"arg_name": "arg_value"}},\n'
            f'  "model_type": "fast" | "smart" | "code",\n'
            f'  "prompt": "prompt_para_la_generacion"\n'
            f"}}\n\n"
            f"Reglas críticas:\n"
            f"1. Si la tarea está resuelta o el pensamiento indica que hemos terminado, usa la acción 'complete'.\n"
            f"2. Si necesitas usar una herramienta de la lista, usa 'use_tool' e incluye el nombre exacto en 'tool' y sus argumentos en 'args'.\n"
            f"3. Si necesitas generar código, texto o razonar más, usa 'generate' con el 'model_type' adecuado y formula el 'prompt'.\n"
            f"Responde SOLO con el JSON."
        )

        try:
            # We call the fast model for routing to keep it responsive.
            response_text = await self.llm_fn(prompt, self.MODEL_ROUTING["fast"])
            
            # Clean and parse response
            clean_text = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL).strip()
            
            # Extract JSON block or general braces
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean_text, flags=re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                json_match = re.search(r"(\{.*\})", clean_text, flags=re.DOTALL)
                json_str = json_match.group(1).strip() if json_match else clean_text
            
            decision = json.loads(json_str)
            action = decision.get("action")
            
            if action not in ["complete", "use_tool", "generate"]:
                raise ValueError(f"Invalid action: {action}")
                
            if action == "use_tool" and decision.get("tool") not in self.tools:
                raise ValueError(f"Selected tool '{decision.get('tool')}' is not available.")
                
            logger.info(f"Structured decision succeeded: {action} ({decision.get('explanation', '')})")
            return decision

        except Exception as e:
            logger.warning(f"Structured decision failed: {e}. Falling back to heuristic.")
            return heuristic_fallback()

    async def _execute_tool(self, name: str, args: Dict) -> ToolResult:
        """Execute a tool safely."""
        tool_fn = self.tools[name]
        try:
            result = await asyncio.wait_for(
                tool_fn(**args) if asyncio.iscoroutinefunction(tool_fn) else asyncio.to_thread(tool_fn, **args),
                timeout=30.0,
            )
            if isinstance(result, ToolResult):
                return result
            return ToolResult(success=True, output=str(result)[:2000])
        except asyncio.TimeoutError:
            return ToolResult(success=False, error="Tool execution timed out (30s)")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
