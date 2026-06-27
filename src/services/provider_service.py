"""ProviderService — ProviderRegistry + Orchestrator setup.

Inspirado en openhuman/src/openhuman/inference/provider/catalog.
Usa src/core/provider_catalog.py con 25+ providers preconfigurados.
"""
from __future__ import annotations
import json
import logging
import os
from pathlib import Path

from src.core.provider_base import ProviderRegistry, ProviderProfile
from src.core.orchestrator import NexusOrchestrator, OrchestratorConfig
from src.core.provider_catalog import PROVIDER_CATALOG

logger = logging.getLogger(__name__)

_NEXUS_HOME = Path(os.environ.get("NEXUS_HOME", str(Path.home() / ".nexus")))


def _load_cloud_providers() -> list[dict]:
    """Load user-managed cloud providers from persistent JSON."""
    p = _NEXUS_HOME / "cloud_providers.json"
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def _load_persisted_default_model() -> str:
    """Load saved default model choice (survives restarts)."""
    p = _NEXUS_HOME / "default_model.json"
    if not p.exists():
        return ""
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("default_model", "")
    except Exception:
        return ""


def _save_persisted_default_model(model: str) -> None:
    """Persist the default model so it survives restarts."""
    p = _NEXUS_HOME / "default_model.json"
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"default_model": model}, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Could not persist default_model: {e}")


class ProviderService:

    @staticmethod
    def init_providers(director):
        director.provider_registry = ProviderRegistry()

        _raw = os.environ.get("OLLAMA_HOST", os.environ.get("OLLAMA_URL", "http://localhost:11434"))
        _ollama_url = ("http://" + _raw) if (_raw and not _raw.startswith("http://") and not _raw.startswith("https://")) else (_raw or "http://localhost:11434")

        PROFILES = []

        # 1. Perfil principal con fallback — Zen free primero, Ollama como respaldo
        # Read zen API key from cloud_providers.json if not in env
        _zen_api_key = os.environ.get("OPENCODE_API_KEY", "")
        if not _zen_api_key:
            for cp in _load_cloud_providers():
                if "zen" in cp.get("id", "").lower() or "zen" in cp.get("name", "").lower():
                    _zen_api_key = cp.get("api_key", "")
                    if _zen_api_key:
                        break
            # Set env var so other modules (opencode_client, ai_tools, vision) can use it
            if _zen_api_key:
                os.environ["OPENCODE_API_KEY"] = _zen_api_key
        PROFILES.append(ProviderProfile(
            name="gema-con-fallback", model="deepseek-v4-flash-free",
            base_url="https://opencode.ai/zen/v1", provider_type="openai",
            api_key=_zen_api_key,
            fallbacks=["ollama", "ollama-fallback"],
            fallback_threshold=2, cooldown_s=30,
            description="Gema con fallback: OpenCode Zen (free) → Ollama → tiny",
            tags=["gema", "fallback-chain", "primary"],
        ))

        # 2. Perfiles legacy ollama (backward-compat y fallback)
        for pname, model, tags, desc in [
            ("ollama", "qwen2.5-coder:7b", ["gema", "fallback"], "Fallback generico para GemaActors"),
            ("ollama-gema", "nexus-coder", ["gema", "primary"], "Gema principal (nexus-coder)"),
            ("ollama-fallback", "qwen2.5:0.5b", ["tiny", "last-resort"], "Tiny para fallback extremo"),
        ]:
            PROFILES.append(ProviderProfile(
                name=pname, model=model, base_url=_ollama_url, description=desc, tags=tags))

        # 3. Providers del catalogo (25+ preconfigurados)
        # Solo registramos los que tienen API key disponible en env.
        for entry in PROVIDER_CATALOG:
            api_key = os.environ.get(entry.get("api_key_env", ""), "") if entry.get("api_key_env") else ""
            base_url = entry["base_url"]

            # Ollama usa la URL local detectada
            if entry["id"] == "ollama":
                base_url = _ollama_url

            # Solo registrar si tiene key (excepto ollama local)
            if not api_key and entry.get("api_key_env"):
                continue

            PROFILES.append(ProviderProfile(
                name=entry["id"],
                model=entry["default_model"],
                base_url=base_url,
                api_key_env=entry.get("api_key_env", ""),
                provider_type="anthropic" if entry.get("auth_style") == "anthropic" else "openai",
                description=entry["description"],
                tags=entry.get("tags", []),
            ))

        # 4. Garantizar cloud-zen presente incluso sin key (se detecta en runtime)
        if not any(p.name == "cloud-zen" for p in PROFILES):
            PROFILES.append(ProviderProfile(
                name="cloud-zen", model="deepseek-v4-flash-free", provider_type="openai",
                base_url="https://opencode.ai/zen/v1",
                api_key=_zen_api_key,
                description="Cloud rapido via OpenCode Zen (deepseek-v4-flash-free).",
                tags=["cloud", "fast", "primary", "free"],
            ))

        # 5. Cargar cloud_providers.json (persistidos via UI/API)
        cloud_providers = _load_cloud_providers()
        for cp in cloud_providers:
            pid = cp.get("id", "")
            if not pid or any(p.name == pid for p in PROFILES):
                continue
            api_key = cp.get("api_key", "")
            if not api_key:
                continue
            base_url = cp.get("base_url", "")
            model = cp.get("default_model", "deepseek-v4-flash-free")
            if not base_url:
                continue
            PROFILES.append(ProviderProfile(
                name=pid,
                model=model,
                base_url=base_url,
                api_key=api_key,
                provider_type=cp.get("provider_type", "openai"),
                description=cp.get("name", pid),
                tags=["cloud", "user-managed"],
            ))

        # 6. Cargar default_model persistido (sobrescribe hardcodeo si existe)
        persisted_model = _load_persisted_default_model()
        if persisted_model:
            director._persisted_default_model = persisted_model
            logger.info(f"Persisted default_model loaded: {persisted_model}")
        else:
            director._persisted_default_model = ""

        director.provider_registry.configure(PROFILES)

        # Stats: cuantos providers quedaron activos
        active = sum(1 for p in PROFILES if not getattr(p, 'api_key_env', '') or os.environ.get(getattr(p, 'api_key_env', ''), ''))
        available = sum(1 for p in PROVIDER_CATALOG if (not p.get('api_key_env')) or os.environ.get(p.get('api_key_env', ''), ''))
        logger.info(f"ProviderRegistry initialized: {len(PROFILES)} profiles, {active} activos, {available} disponibles del catalogo de {len(PROVIDER_CATALOG)}")

        async def tool_executor(name: str, args: dict) -> str:
            caller = director.tool_caller
            if hasattr(caller, 'execute_tool'):
                return await caller.execute_tool(name, args)
            if hasattr(caller, '_tools') and name in caller._tools:
                return await caller._tools[name].handler(**args)
            return f"Tool '{name}' not found"
        director._multi_motor_tool_executor = tool_executor

        director.orchestrator = NexusOrchestrator(OrchestratorConfig(
            provider_registry=director.provider_registry,
            tool_executor=tool_executor,
            get_tool_schemas=lambda: director.tool_caller.get_tool_schemas() if hasattr(director, 'tool_caller') else [],
            max_iterations_per_task=5,
            max_concurrent_tasks=3,
            coordinator_provider="gema-con-fallback",
        ))

        logger.info("ProviderRegistry + AgentRunner + Orchestrator initialized (Orquestador Multi-Motor)")

    @staticmethod
    def list_available_providers() -> list[dict]:
        """Lista los providers con API key disponible."""
        result = []
        for entry in PROVIDER_CATALOG:
            api_key = ""
            if entry.get("api_key_env"):
                api_key = os.environ.get(entry["api_key_env"], "")
                if not api_key:
                    continue
            result.append({**entry, "available": bool(api_key or not entry.get("api_key_env"))})
        return result
