"""
AgentRunner — Bucle de tool-calling reutilizable e independiente del modelo.

Patrón: nanobot AgentRunner + pircer LLMProvider + OpenAI-compatible spec.
Capa intermedia entre el Director y el LLM: el Director ya no llama al LLM directo.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from src.core.provider_base import (
    LLMProvider,
    LLMResponse,
    LLMMessage,
    MessageRole,
    ToolCall,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AgentRunSpec:
    messages: list[LLMMessage]
    tools_definitions: list[dict[str, Any]]
    model: str = ""
    max_iterations: int = 20
    max_tool_result_chars: int = 4000
    temperature: float | None = None
    max_tokens: int | None = None
    error_message: str = "Lo siento, ocurrio un error al procesar tu solicitud."
    fallback_models: list[str] = field(default_factory=list)
    context_window_tokens: int = 8192
    on_stream: Callable[[str], None] | None = None
    on_tool_start: Callable[[str, dict], None] | None = None
    on_tool_end: Callable[[str, Any], None] | None = None
    checkpoint_callback: Callable[[dict], None] | None = None


@dataclass(slots=True)
class AgentRunResult:
    content: str | None = None
    messages: list[LLMMessage] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    stop_reason: str = "completed"
    iterations: int = 0
    error: str | None = None


class AgentRunner:
    """Runner agnóstico: funciona con cualquier LLMProvider.

    Uso:
        runner = AgentRunner(provider)
        result = await runner.run(AgentRunSpec(
            messages=[LLMMessage(role="user", content="Hola")],
            tools_definitions=[...],
            model="qwen2.5:7b",
        ))

    tool_executor: callable opcional para ejecutar tools externamente.
        Firma: async (name: str, args: dict) -> Any
        Si no se provee, devuelve stub "tool not available".
    """

    def __init__(self, provider: LLMProvider, tool_executor: Callable[[str, dict], Awaitable[Any]] | None = None):
        self.provider = provider
        self._tool_executor = tool_executor

    async def run(self, spec: AgentRunSpec) -> AgentRunResult:
        messages = list(spec.messages)
        final_content: str | None = None
        tools_used: list[str] = []
        usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0}
        error: str | None = None
        stop_reason = "completed"

        for iteration in range(spec.max_iterations):
            if spec.on_tool_start:
                pass

            response = await self._request_model(spec, messages)

            self._accumulate_usage(usage, response.usage)

            if response.should_execute_tools:
                for tc in response.tool_calls:
                    tools_used.append(tc.name)

                assistant_msg = LLMMessage(
                    role=MessageRole.assistant,
                    content=response.content,
                    tool_calls=tuple(response.tool_calls),
                )
                messages.append(assistant_msg)

                if spec.on_tool_start:
                    for tc in response.tool_calls:
                        spec.on_tool_start(tc.name, tc.arguments)

                all_results = await self._execute_tools(spec, response.tool_calls)

                for tc, result in zip(response.tool_calls, all_results):
                    tool_msg = LLMMessage(
                        role=MessageRole.tool,
                        content=self._normalize_result(spec, result),
                        tool_call_id=tc.id,
                        name=tc.name,
                    )
                    messages.append(tool_msg)
                    if spec.on_tool_end:
                        spec.on_tool_end(tc.name, result)

                if spec.checkpoint_callback:
                    spec.checkpoint_callback({
                        "iteration": iteration,
                        "phase": "tools_completed",
                        "assistant_msg": assistant_msg,
                        "tool_results": [r for r in all_results],
                    })

                continue

            if response.has_tool_calls:
                logger.warning("Tool calls ignored under finish_reason=%s", response.finish_reason)

            if response.finish_reason == "error":
                error = response.content or spec.error_message
                final_content = error
                stop_reason = "error"
                break

            final_content = response.content
            messages.append(LLMMessage(
                role=MessageRole.assistant,
                content=final_content,
            ))
            if spec.on_stream and final_content:
                spec.on_stream(final_content)
            break
        else:
            stop_reason = "max_iterations"
            final_content = f"Maximo de {spec.max_iterations} iteraciones alcanzado."
            error = final_content

        usage["iterations"] = iteration + 1
        return AgentRunResult(
            content=final_content,
            messages=messages,
            tools_used=tools_used,
            usage=usage,
            stop_reason=stop_reason,
            iterations=iteration + 1,
            error=error,
        )

    async def _request_model(
        self,
        spec: AgentRunSpec,
        messages: list[LLMMessage],
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "messages": messages,
            "tools": spec.tools_definitions if spec.tools_definitions else None,
        }
        if spec.model:
            kwargs["model"] = spec.model
        if spec.temperature is not None:
            kwargs["temperature"] = spec.temperature
        if spec.max_tokens is not None:
            kwargs["max_tokens"] = spec.max_tokens

        if spec.on_stream and self.provider.supports_streaming:
            collected: list[str] = []
            def on_chunk(chunk: str) -> None:
                collected.append(chunk)
                spec.on_stream(chunk)
            kwargs["on_content"] = on_chunk
            return await self.provider.chat_stream(**kwargs)

        return await self.provider.chat_with_retry(**kwargs)

    async def _execute_tools(
        self,
        spec: AgentRunSpec,
        tool_calls: list[ToolCall],
    ) -> list[Any]:
        results: list[Any] = []
        for tc in tool_calls:
            result = await self._run_tool(spec, tc)
            results.append(result)
        return results

    async def _run_tool(self, spec: AgentRunSpec, tc: ToolCall) -> Any:
        if self._tool_executor:
            try:
                return await self._tool_executor(tc.name, tc.arguments)
            except Exception as e:
                logger.error("Tool %s error: %s", tc.name, e)
                return f"Error: {type(e).__name__}: {e}"
        return f"Tool '{tc.name}' not available (no tool_executor configured)"

    @staticmethod
    def _normalize_result(spec: AgentRunSpec, result: Any) -> str:
        if result is None:
            return "(empty)"
        text = str(result)
        if len(text) > spec.max_tool_result_chars:
            return text[:spec.max_tool_result_chars] + "\n...(truncated)"
        return text

    @staticmethod
    def _accumulate_usage(target: dict, addition: dict) -> None:
        for k, v in addition.items():
            if isinstance(v, (int, float)):
                target[k] = target.get(k, 0) + int(v)
