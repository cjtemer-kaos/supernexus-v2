"""
LLM Provider - Pasarela unificada de inferencia multi-proveedor

Unifica todas las inferencias bajo un formato estandar (OpenAI-compatible).
Detecta automaticamente si redirige a Ollama (local) o APIs cloud.
Formatea mensajes de forma transparente segun el proveedor.

Patrones integrados:
- CredentialPool failover (multi-endpoint con retry)
- SchemaSanitizer (JSON Schema 2020-12 → OpenAPI 3.0)
- SequenceScrubber (turn alignment para Gemini/Ollama)
- Multi-Endpoint Failover (Ollama → Cloud automatico)

Proveedores soportados:
- Ollama (local, prioritario)
- OpenAI / OpenRouter (cloud)
- Anthropic (cloud)
- Google Gemini (cloud)
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from src.core.credential_pool import CredentialPool, STRATEGY_ROUND_ROBIN
from src.core.schema_sanitizer import SchemaSanitizer
from src.core.session_manager import SequenceScrubber

logger = logging.getLogger("nexus-llm-provider")


@dataclass
class LLMResponse:
    """Respuesta estandarizada de cualquier proveedor"""
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    tokens_prompt: int = 0
    tokens_completion: int = 0
    duration_ms: float = 0
    finish_reason: str = "stop"
    raw_response: Optional[Dict] = None


@dataclass
class LLMRequest:
    """Peticion estandarizada para cualquier proveedor"""
    messages: List[Dict[str, str]]
    model: str
    provider: str = "ollama"
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    tools: Optional[List[Dict]] = None
    tool_choice: str = "auto"
    stop_sequences: Optional[List[str]] = None
    timeout_seconds: float = 120
    images: Optional[List[str]] = None  # Base64 o URLs


class LLMProvider:
    """
    Pasarela unificada de inferencia multi-proveedor.

    Uso:
        provider = LLMProvider()
        response = await provider.chat(
            messages=[{"role": "user", "content": "Hola"}],
            model="qwen2.5-coder:7b",
            provider="ollama",
        )
    """

    # Endpoints por proveedor
    PROVIDER_ENDPOINTS = {
        "ollama": {
            "base_url": os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
            "chat_path": "/api/chat",
            "generate_path": "/api/generate",
        },
        "openai": {
            "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com"),
            "chat_path": "/v1/chat/completions",
        },
        "openrouter": {
            "base_url": "https://openrouter.ai/api",
            "chat_path": "/v1/chat/completions",
        },
        "anthropic": {
            "base_url": "https://api.anthropic.com",
            "chat_path": "/v1/messages",
        },
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com",
            "chat_path": "/v1beta/openai/chat/completions",  # OpenAI-compatible
        },
    }

    def __init__(self, credential_pool: CredentialPool = None):
        self.credential_pool = credential_pool or CredentialPool()
        self._client = httpx.AsyncClient(timeout=120.0)
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "failovers": 0,
            "provider_stats": {},
        }

    async def chat(self, request: LLMRequest) -> LLMResponse:
        """
        Envio principal con failover automatico.

        Si el proveedor falla, intenta failover en orden:
        Ollama → OpenRouter → Gemini → Anthropic
        """
        start = time.time()
        self._stats["total_requests"] += 1

        # Preparar mensajes con SequenceScrubber
        scrubbed_messages = SequenceScrubber.scrub(request.messages)

        # Si hay system prompt, insertarlo al inicio
        if request.system_prompt:
            if not scrubbed_messages or scrubbed_messages[0].get("role") != "system":
                scrubbed_messages.insert(0, {"role": "system", "content": request.system_prompt})

        # Sanitizar schemas de herramientas si hay
        tools = request.tools
        if tools:
            tools = SchemaSanitizer.sanitize_tool_definitions(tools, provider=request.provider)

        # Intentar con el proveedor principal
        last_error = None
        providers_to_try = self._get_failover_chain(request.provider)

        for provider in providers_to_try:
            try:
                response = await self._call_provider(
                    provider=provider,
                    messages=scrubbed_messages,
                    model=request.model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    top_p=request.top_p,
                    tools=tools,
                    tool_choice=request.tool_choice,
                    stop_sequences=request.stop_sequences,
                    timeout_seconds=request.timeout_seconds,
                    images=request.images,
                )

                response.duration_ms = (time.time() - start) * 1000
                response.provider = provider

                self._stats["successful_requests"] += 1
                self._stats["total_tokens"] += response.tokens_used
                self._update_provider_stats(provider, True)

                if provider != request.provider:
                    self._stats["failovers"] += 1
                    logger.info(f"Failover: {request.provider} → {provider}")

                return response

            except Exception as e:
                last_error = e
                self._update_provider_stats(provider, False)
                logger.warning(f"Provider {provider} failed: {e}")

                # Marcar credencial en cooldown si aplica
                self.credential_pool.mark_error(provider, str(e))

        # Todos los proveedores fallaron
        self._stats["failed_requests"] += 1
        raise RuntimeError(
            f"All providers failed. Last error: {last_error}. "
            f"Attempted: {providers_to_try}"
        )

    async def _call_provider(
        self,
        provider: str,
        messages: List[Dict],
        model: str,
        temperature: float,
        max_tokens: int,
        top_p: float,
        tools: Optional[List[Dict]],
        tool_choice: str,
        stop_sequences: Optional[List[str]],
        timeout_seconds: float,
        images: Optional[List[str]],
    ) -> LLMResponse:
        """Llama a un proveedor especifico"""
        if provider == "ollama":
            return await self._call_ollama(messages, model, temperature, max_tokens, top_p, tools, timeout_seconds, images)
        elif provider in ("openai", "openrouter"):
            return await self._call_openai_compatible(provider, messages, model, temperature, max_tokens, top_p, tools, tool_choice, stop_sequences, timeout_seconds)
        elif provider == "anthropic":
            return await self._call_anthropic(messages, model, temperature, max_tokens, tools, stop_sequences, timeout_seconds)
        elif provider == "gemini":
            return await self._call_gemini(messages, model, temperature, max_tokens, tools, timeout_seconds)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def _call_ollama(
        self,
        messages: List[Dict],
        model: str,
        temperature: float,
        max_tokens: int,
        top_p: float,
        tools: Optional[List[Dict]],
        timeout_seconds: float,
        images: Optional[List[str]],
    ) -> LLMResponse:
        """Llama a Ollama local"""
        endpoint = self.PROVIDER_ENDPOINTS["ollama"]
        url = f"{endpoint['base_url']}{endpoint['chat_path']}"

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": top_p,
            },
        }

        if tools:
            payload["tools"] = tools

        # Agregar imagenes al ultimo mensaje user
        if images:
            last_user_msg = None
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    last_user_msg = msg
                    break
            if last_user_msg:
                content = last_user_msg.get("content", "")
                last_user_msg["images"] = images

        response = await self._client.post(url, json=payload, timeout=timeout_seconds)
        response.raise_for_status()
        data = response.json()

        message = data.get("message", {})
        content = message.get("content", "")

        return LLMResponse(
            content=content,
            model=model,
            provider="ollama",
            tokens_used=data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
            tokens_prompt=data.get("prompt_eval_count", 0),
            tokens_completion=data.get("eval_count", 0),
            raw_response=data,
        )

    async def _call_openai_compatible(
        self,
        provider: str,
        messages: List[Dict],
        model: str,
        temperature: float,
        max_tokens: int,
        top_p: float,
        tools: Optional[List[Dict]],
        tool_choice: str,
        stop_sequences: Optional[List[str]],
        timeout_seconds: float,
    ) -> LLMResponse:
        """Llama a OpenAI o OpenRouter"""
        endpoint = self.PROVIDER_ENDPOINTS[provider]
        url = f"{endpoint['base_url']}{endpoint['chat_path']}"

        # Obtener API key del credential pool
        cred = self.credential_pool.get_credential(provider)
        api_key = cred.key if cred else os.environ.get(f"{provider.upper()}_API_KEY", "")

        if not api_key:
            raise ValueError(f"No API key available for {provider}")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://supernexus.local"
            headers["X-Title"] = "SuperNEXUS v2"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        if stop_sequences:
            payload["stop"] = stop_sequences

        response = await self._client.post(url, json=payload, headers=headers, timeout=timeout_seconds)

        if response.status_code == 429:
            self.credential_pool.mark_cooldown(cred, 429)
            raise RuntimeError(f"Rate limited by {provider}")
        elif response.status_code == 401:
            self.credential_pool.mark_cooldown(cred, 401)
            raise RuntimeError(f"Auth failed for {provider}")

        response.raise_for_status()
        data = response.json()

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = data.get("usage", {})

        return LLMResponse(
            content=message.get("content", ""),
            model=model,
            provider=provider,
            tokens_used=usage.get("total_tokens", 0),
            tokens_prompt=usage.get("prompt_tokens", 0),
            tokens_completion=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
            raw_response=data,
        )

    async def _call_anthropic(
        self,
        messages: List[Dict],
        model: str,
        temperature: float,
        max_tokens: int,
        tools: Optional[List[Dict]],
        stop_sequences: Optional[List[str]],
        timeout_seconds: float,
    ) -> LLMResponse:
        """Llama a Anthropic Claude"""
        endpoint = self.PROVIDER_ENDPOINTS["anthropic"]
        url = f"{endpoint['base_url']}{endpoint['chat_path']}"

        cred = self.credential_pool.get_credential("anthropic")
        api_key = cred.key if cred else os.environ.get("ANTHROPIC_API_KEY", "")

        if not api_key:
            raise ValueError("No API key available for anthropic")

        # Anthropic requiere system prompt separado
        system_prompt = ""
        filtered_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_prompt = msg.get("content", "")
            else:
                filtered_messages.append(msg)

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": model,
            "messages": filtered_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system_prompt:
            payload["system"] = system_prompt

        if tools:
            # Anthropic usa formato diferente para herramientas
            payload["tools"] = [
                {
                    "name": t.get("function", {}).get("name", ""),
                    "description": t.get("function", {}).get("description", ""),
                    "input_schema": SchemaSanitizer.sanitize(
                        t.get("function", {}).get("parameters", {}),
                        provider="anthropic",
                    ),
                }
                for t in tools
            ]

        if stop_sequences:
            payload["stop_sequences"] = stop_sequences

        response = await self._client.post(url, json=payload, headers=headers, timeout=timeout_seconds)

        if response.status_code == 429:
            self.credential_pool.mark_cooldown(cred, 429)
            raise RuntimeError("Rate limited by Anthropic")

        response.raise_for_status()
        data = response.json()

        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")

        usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            model=model,
            provider="anthropic",
            tokens_used=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            tokens_prompt=usage.get("input_tokens", 0),
            tokens_completion=usage.get("output_tokens", 0),
            raw_response=data,
        )

    async def _call_gemini(
        self,
        messages: List[Dict],
        model: str,
        temperature: float,
        max_tokens: int,
        tools: Optional[List[Dict]],
        timeout_seconds: float,
    ) -> LLMResponse:
        """Llama a Google Gemini via OpenAI-compatible endpoint"""
        return await self._call_openai_compatible(
            provider="gemini",
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=1.0,
            tools=tools,
            tool_choice="auto",
            stop_sequences=None,
            timeout_seconds=timeout_seconds,
        )

    def _get_failover_chain(self, primary_provider: str) -> List[str]:
        """Retorna cadena de failover comenzando por el proveedor principal"""
        chain = [primary_provider]
        failover_order = ["ollama", "openrouter", "gemini", "anthropic", "openai"]

        for p in failover_order:
            if p != primary_provider and p not in chain:
                chain.append(p)

        return chain

    def _update_provider_stats(self, provider: str, success: bool):
        """Actualiza estadisticas por proveedor"""
        if provider not in self._stats["provider_stats"]:
            self._stats["provider_stats"][provider] = {"success": 0, "failed": 0}

        if success:
            self._stats["provider_stats"][provider]["success"] += 1
        else:
            self._stats["provider_stats"][provider]["failed"] += 1

    def get_stats(self) -> Dict:
        return self._stats.copy()

    async def close(self):
        await self._client.aclose()
