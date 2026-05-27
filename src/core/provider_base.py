"""
Provider Base — Interfaz unificada de proveedores LLM.

Patrón: Pincer (frozen dataclasses + ABC limpio) + nanobot (fallback circuit breaker).
Todos los proveedores pueden intercambiarse sin cambiar el código que los usa.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable

logger = logging.getLogger("nexus-provider")


class MessageRole:
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolResult:
    role: str = "tool"
    tool_call_id: str = ""
    name: str = ""
    content: str = ""


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: MessageRole | str = "user"
    content: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str = ""


@dataclass(frozen=True, slots=True)
class LLMResponse:
    content: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    model: str = ""
    reasoning_content: str | None = None

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0

    @property
    def should_execute_tools(self) -> bool:
        return self.has_tool_calls and self.finish_reason in ("tool_calls", "stop")


@dataclass(frozen=True, slots=True)
class ModelInfo:
    name: str
    provider: str
    max_tokens: int = 4096
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    supports_streaming: bool = True
    supports_tools: bool = True
    context_window: int = 8192


class LLMProvider(ABC):
    """Provider abstracto. Cualquier modelo/proveedor implementa esto."""

    name: str = "base"
    supports_streaming: bool = True

    def __init__(self, model: str = "", name: str = ""):
        self.name = name or self.__class__.name
        self.model = model
        self._call_count = 0
        self._total_time = 0.0
        self._error_count = 0

    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        ...

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        on_content: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Default: fallback a chat() no-streaming."""
        resp = await self.chat(messages, tools, **kwargs)
        if on_content and resp.content:
            on_content(resp.content)
        return resp

    async def chat_with_retry(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> LLMResponse:
        for attempt in range(max_retries):
            resp = await self.chat(messages, tools, **kwargs)
            if resp.finish_reason != "error":
                return resp
            if attempt < max_retries - 1:
                delay = min(2 ** attempt, 10)
                logger.warning(
                    "Provider %s error (attempt %d/%d), retrying in %ds",
                    self.name, attempt + 1, max_retries, delay,
                )
                await asyncio.sleep(delay)
        return resp

    @abstractmethod
    def get_model_info(self) -> ModelInfo:
        ...

    def get_stats(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "model": self.model,
            "calls": self._call_count,
            "errors": self._error_count,
            "avg_time_ms": round((self._total_time / max(self._call_count, 1)) * 1000, 2),
        }


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434",
        name: str = "",
    ):
        super().__init__(model, name=name)
        self.base_url = base_url.rstrip("/")

    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        import httpx

        self._call_count += 1
        start = time.perf_counter()
        timeout = kwargs.get("timeout", 60.0)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": m.role.value if isinstance(m.role, MessageRole) else m.role,
                 "content": m.content or ""}
                for m in messages
            ],
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
        if kwargs.get("temperature"):
            payload["temperature"] = kwargs["temperature"]
        if kwargs.get("max_tokens"):
            payload["max_tokens"] = kwargs["max_tokens"]

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                self._total_time += time.perf_counter() - start
                resp.raise_for_status()
                data = resp.json()
                msg = data.get("message", {})

                tool_calls: list[ToolCall] = []
                for tc in msg.get("tool_calls", []):
                    fn = tc.get("function", {})
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        import json as _json
                        try:
                            args = _json.loads(args)
                        except _json.JSONDecodeError:
                            args = {}
                    tool_calls.append(ToolCall(
                        id=tc.get("id", fn.get("name", "")),
                        name=fn.get("name", ""),
                        arguments=args if isinstance(args, dict) else {},
                    ))

                return LLMResponse(
                    content=msg.get("content", ""),
                    tool_calls=tuple(tool_calls),
                    finish_reason=data.get("done_reason", "stop"),
                    usage={
                        "prompt_tokens": data.get("prompt_eval_count", 0),
                        "completion_tokens": data.get("eval_count", 0),
                    },
                    model=self.model,
                )
        except httpx.HTTPStatusError as e:
            self._error_count += 1
            logger.error("Ollama HTTP %d: %s", e.response.status_code, e)
            return LLMResponse(content=f"Error HTTP {e.response.status_code}", finish_reason="error", model=self.model)
        except httpx.RequestError as e:
            self._error_count += 1
            logger.error("Ollama connection error: %s", e)
            return LLMResponse(content=f"Conexion fallo: {e}", finish_reason="error", model=self.model)
        except Exception as e:
            self._error_count += 1
            logger.error("Ollama error: %s", e)
            return LLMResponse(content=f"Error: {e}", finish_reason="error", model=self.model)

    def get_model_info(self) -> ModelInfo:
        return ModelInfo(name=self.model, provider="ollama")

    def get_stats(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "model": self.model,
            "calls": self._call_count,
            "errors": self._error_count,
            "avg_time_ms": round((self._total_time / max(self._call_count, 1)) * 1000, 2),
        }


class OpenAIProvider(LLMProvider):
    """Proveedor OpenAI-compatible (OpenAI, LiteLLM, cualquier proxy)."""
    name = "openai"

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        name: str = "",
    ):
        super().__init__(model, name=name)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        import httpx

        self._call_count += 1
        start = time.perf_counter()

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": m.role.value if isinstance(m.role, MessageRole) else m.role,
                 "content": m.content or ""}
                for m in messages
            ],
        }
        if tools:
            payload["tools"] = tools
        if kwargs.get("temperature"):
            payload["temperature"] = kwargs["temperature"]
        if kwargs.get("max_tokens"):
            payload["max_tokens"] = kwargs["max_tokens"]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=kwargs.get("timeout", 60.0)) as client:
                resp = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                self._total_time += time.perf_counter() - start
                resp.raise_for_status()
                data = resp.json()
                choice = data.get("choices", [{}])[0]
                msg = choice.get("message", {})

                tool_calls: list[ToolCall] = []
                for tc in msg.get("tool_calls", []):
                    args = tc["function"].get("arguments", {})
                    if isinstance(args, str):
                        import json as _json
                        try:
                            args = _json.loads(args)
                        except _json.JSONDecodeError:
                            args = {}
                    tool_calls.append(ToolCall(
                        id=tc.get("id", ""),
                        name=tc["function"]["name"],
                        arguments=args if isinstance(args, dict) else {},
                    ))

                return LLMResponse(
                    content=msg.get("content", ""),
                    tool_calls=tuple(tool_calls),
                    finish_reason=choice.get("finish_reason", "stop"),
                    usage={
                        "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                        "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                    },
                    model=self.model,
                )
        except httpx.HTTPStatusError as e:
            self._error_count += 1
            logger.error("OpenAI HTTP %d: %s", e.response.status_code, e)
            return LLMResponse(content=f"Error HTTP {e.response.status_code}", finish_reason="error", model=self.model)
        except httpx.RequestError as e:
            self._error_count += 1
            logger.error("OpenAI connection error: %s", e)
            return LLMResponse(content=f"Conexion fallo: {e}", finish_reason="error", model=self.model)
        except Exception as e:
            self._error_count += 1
            logger.error("OpenAI error: %s", e)
            return LLMResponse(content=f"Error: {e}", finish_reason="error", model=self.model)

    def get_model_info(self) -> ModelInfo:
        return ModelInfo(name=self.model, provider="openai", cost_per_1k_input=0.01, cost_per_1k_output=0.03)


class AnthropicProvider(LLMProvider):
    """Proveedor Anthropic (Messages API). Convierte tool_calls al format Anthropic."""
    name = "anthropic"

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str = "",
        base_url: str = "https://api.anthropic.com/v1",
        name: str = "",
        max_tokens: int = 4096,
    ):
        super().__init__(model, name=name)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._max_tokens = max_tokens

    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        import httpx
        import json as _json

        self._call_count += 1
        start = time.perf_counter()

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
            "messages": self._convert_messages(messages),
        }
        if kwargs.get("temperature"):
            payload["temperature"] = kwargs["temperature"]
        if kwargs.get("system"):
            payload["system"] = kwargs["system"]

        anthropic_tools = self._convert_tools(tools) if tools else None
        if anthropic_tools:
            payload["tools"] = anthropic_tools

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=kwargs.get("timeout", 60.0)) as client:
                resp = await client.post(f"{self.base_url}/messages", json=payload, headers=headers)
                self._total_time += time.perf_counter() - start
                resp.raise_for_status()
                data = resp.json()

                content = ""
                tool_calls: list[ToolCall] = []
                for block in data.get("content", []):
                    if block["type"] == "text":
                        content = (content + " " + block["text"]).strip()
                    elif block["type"] == "tool_use":
                        args = block.get("input", {})
                        tool_calls.append(ToolCall(
                            id=block.get("id", ""),
                            name=block.get("name", ""),
                            arguments=args if isinstance(args, dict) else {},
                        ))

                usage = data.get("usage", {})
                finish = data.get("stop_reason", "end_turn")
                if finish == "tool_use":
                    finish = "tool_calls"

                return LLMResponse(
                    content=content or None,
                    tool_calls=tuple(tool_calls),
                    finish_reason=finish,
                    usage={
                        "prompt_tokens": usage.get("input_tokens", 0),
                        "completion_tokens": usage.get("output_tokens", 0),
                    },
                    model=self.model,
                )
        except httpx.HTTPStatusError as e:
            self._error_count += 1
            logger.error("Anthropic HTTP %d: %s", e.response.status_code, e)
            return LLMResponse(content=f"Error HTTP {e.response.status_code}", finish_reason="error", model=self.model)
        except httpx.RequestError as e:
            self._error_count += 1
            logger.error("Anthropic connection error: %s", e)
            return LLMResponse(content=f"Conexion fallo: {e}", finish_reason="error", model=self.model)
        except Exception as e:
            self._error_count += 1
            logger.error("Anthropic error: %s", e)
            return LLMResponse(content=f"Error: {e}", finish_reason="error", model=self.model)

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """Convierte LLMMessages al formato Anthropic Messages API."""
        result = []
        current_role = None
        current_content = []

        for m in messages:
            role = m.role.value if isinstance(m.role, MessageRole) else m.role
            if role == "tool":
                result.append({
                    "role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": m.tool_call_id, "content": m.content or ""}],
                })
                continue

            if role == "assistant" and m.tool_calls:
                blocks = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    blocks.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments})
                result.append({"role": "assistant", "content": blocks})
                continue

            if role != current_role:
                if current_content:
                    result.append({"role": current_role, "content": "".join(current_content)})
                current_role = role
                current_content = []
            current_content.append(m.content or "")

        if current_content:
            result.append({"role": current_role, "content": "".join(current_content)})
        return result

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """Convierte OpenAI tool schemas al formato Anthropic."""
        anthropic_tools = []
        for t in tools:
            fn = t.get("function", t)
            anthropic_tools.append({
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            })
        return anthropic_tools

    def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            name=self.model, provider="anthropic",
            cost_per_1k_input=0.003, cost_per_1k_output=0.015,
        )


class FallbackProvider(LLMProvider):
    """Circuit breaker: prueba primary, si falla N veces consecutivas prueba fallbacks."""

    name = "fallback"
    FALLBACK_KINDS = frozenset({"timeout", "connection", "server_error", "rate_limit"})

    def __init__(self, providers: list[LLMProvider], fallback_threshold: int = 3, cooldown_s: float = 60.0):
        super().__init__("fallback")
        self.providers = providers
        self.fallback_threshold = fallback_threshold
        self.cooldown_s = cooldown_s
        self._primary = providers[0] if providers else None
        self._fallbacks = providers[1:] if len(providers) > 1 else []
        self._consecutive_failures = 0
        self._tripped = False
        self._tripped_at = 0.0
        self._last_error_kind: str | None = None

    async def chat(self, messages: list[LLMMessage], tools: list[dict] | None = None, **kwargs: Any) -> LLMResponse:
        now = time.time()
        if self._tripped and (now - self._tripped_at) > self.cooldown_s:
            self._tripped = False
            self._consecutive_failures = 0
            logger.info("FallbackProvider: half-open, probing primary")

        if not self._tripped and self._primary:
            resp = await self._primary.chat(messages, tools, **kwargs)
            if resp.finish_reason != "error":
                self._consecutive_failures = 0
                return resp

            is_fallback_kind = resp.content and any(k in resp.content.lower() for k in self.FALLBACK_KINDS)
            if is_fallback_kind:
                self._consecutive_failures += 1
                if self._consecutive_failures >= self.fallback_threshold:
                    self._tripped = True
                    self._tripped_at = now
                    logger.warning("FallbackProvider: tripped after %d failures", self._consecutive_failures)
            elif not is_fallback_kind:
                self._consecutive_failures = 0

            if self._fallbacks:
                logger.info("Primary failed, trying fallbacks")
            else:
                return resp

        errors: list[str] = []
        for fb in self._fallbacks:
            logger.info("FallbackProvider: trying %s (%s)", fb.name, fb.model)
            resp = await fb.chat(messages, tools, **kwargs)
            if resp.finish_reason != "error":
                self._consecutive_failures = 0
                self._tripped = False
                return resp
            errors.append(f"{fb.name}: {resp.content}")

        return LLMResponse(
            content=f"Todos los proveedores fallaron: primary error + {'; '.join(errors)}" if errors else resp.content,
            finish_reason="error",
        )

    def get_model_info(self) -> ModelInfo:
        if self._primary:
            return self._primary.get_model_info()
        return ModelInfo(name="fallback", provider="fallback")

    def get_stats(self) -> dict[str, Any]:
        stats = {"fallback_type": "circuit_breaker", "primary": self._primary.model if self._primary else "none",
                 "tripped": self._tripped, "consecutive_failures": self._consecutive_failures}
        for i, prov in enumerate(self.providers):
            stats[f"provider_{i}"] = prov.get_stats()
        return stats


@dataclass
class ProviderProfile:
    """Perfil declarativo de un proveedor. Define qué modelo usar, cómo autenticarse y sus fallbacks."""
    name: str
    model: str
    provider_type: str = "ollama"
    base_url: str = "http://localhost:11434"
    api_key_env: str = ""
    temperature: float | None = None
    max_tokens: int | None = None
    fallbacks: list[str] = field(default_factory=list)
    fallback_threshold: int = 2
    cooldown_s: float = 60.0
    tags: list[str] = field(default_factory=list)
    description: str = ""


def create_provider_from_profile(profile: ProviderProfile) -> LLMProvider:
    """Crea un LLMProvider desde un ProviderProfile declarativo."""
    import os

    if profile.provider_type == "ollama":
        return OllamaProvider(model=profile.model, base_url=profile.base_url, name=profile.name)

    if profile.provider_type == "openai":
        api_key = os.environ.get(profile.api_key_env, "")
        return OpenAIProvider(model=profile.model, api_key=api_key, base_url=profile.base_url, name=profile.name)

    if profile.provider_type == "anthropic":
        api_key = os.environ.get(profile.api_key_env, "")
        return AnthropicProvider(model=profile.model, api_key=api_key, base_url=profile.base_url, name=profile.name)

    raise ValueError(f"Unknown provider type: {profile.provider_type}")


class ProviderRegistry:
    """Registro central de proveedores. Reemplaza el module-level dict."""

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}
        import threading
        self._lock = threading.Lock()

    def register(self, name: str, provider: LLMProvider) -> None:
        with self._lock:
            self._providers[name] = provider
            logger.info("Provider registered: %s (%s)", name, provider.model)

    def get(self, name: str | None = None) -> LLMProvider | None:
        with self._lock:
            if name:
                return self._providers.get(name)
            for p in self._providers.values():
                return p
            return None

    def get_or_fallback(self, name: str | None, fallback: str = "ollama") -> LLMProvider:
        p = self.get(name)
        if p:
            return p
        p = self.get(fallback)
        if p:
            return p
        p = self.get("ollama")
        if p:
            return p
        raise RuntimeError(f"No providers registered (looked for {name!r}, {fallback!r}, ollama)")

    def list(self) -> dict[str, LLMProvider]:
        with self._lock:
            return dict(self._providers)

    def register_profile(self, profile: ProviderProfile) -> LLMProvider:
        """Registra un proveedor desde un perfil declarativo.
        Si tiene fallbacks, crea un FallbackProvider automáticamente.
        """
        primary = create_provider_from_profile(profile)
        if profile.fallbacks:
            fallback_providers = [primary]
            for fb_name in profile.fallbacks:
                fb = self._providers.get(fb_name)
                if fb:
                    fallback_providers.append(fb)
            if len(fallback_providers) > 1:
                fb_provider = FallbackProvider(
                    providers=fallback_providers,
                    fallback_threshold=profile.fallback_threshold,
                    cooldown_s=profile.cooldown_s,
                )
                self.register(profile.name, fb_provider)
                return fb_provider
        self.register(profile.name, primary)
        return primary

    def configure(self, profiles: list[ProviderProfile]) -> None:
        """Registra múltiples proveedores desde una lista de perfiles.
        Los fallbacks se resuelven después de que todos los perfiles base están registrados.
        """
        for p in profiles:
            if not p.fallbacks:
                self.register_profile(p)
        for p in profiles:
            if p.fallbacks:
                self.register_profile(p)

    async def health_check(self) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        with self._lock:
            for name, prov in self._providers.items():
                results[name] = prov.get_stats()
        return results


class MockProvider(LLMProvider):
    """Para testing."""
    name = "mock"

    def __init__(self, responses: list[str] | None = None):
        super().__init__("mock")
        self.responses = responses or ["Mock response"]
        self._idx = 0

    async def chat(self, messages: list[LLMMessage], tools: list[dict] | None = None, **kwargs: Any) -> LLMResponse:
        self._call_count += 1
        resp = self.responses[self._idx % len(self.responses)]
        self._idx += 1
        return LLMResponse(content=resp, model="mock", finish_reason="stop")

    def get_model_info(self) -> ModelInfo:
        return ModelInfo(name="mock", provider="mock", max_tokens=999999)
