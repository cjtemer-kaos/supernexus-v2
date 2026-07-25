"""
Model Registry — gestión centralizada de providers y modelos.

Persiste en config/nexus_models.yaml. Auto-detecta Ollama.
El usuario elige qué modelo usar via UI, y el Director lo respeta.
"""
import os
import json
import yaml
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("nexus.model_registry")

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
MODELS_CONFIG = CONFIG_DIR / "nexus_models.yaml"


@dataclass
class ProviderConfig:
    """Un provider de modelos (Ollama local, OpenAI, OpenRouter, etc.)"""
    id: str
    name: str
    type: str  # "ollama" | "openai" | "custom"
    base_url: str
    api_key: str = ""
    enabled: bool = True
    models: List[str] = field(default_factory=list)
    # Metadata
    supports_tools: bool = True
    context_window: int = 128000
    is_free: bool = False
    last_probed: str = ""


@dataclass
class ModelRegistryConfig:
    """Configuración completa del model registry."""
    providers: List[Dict[str, Any]] = field(default_factory=list)
    active: Dict[str, str] = field(default_factory=lambda: {
        "provider_id": "",
        "model": "",
    })
    auxiliary: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        "vision": {"provider_id": "", "model": ""},
        "fast": {"provider_id": "", "model": ""},
        "embedding": {"provider_id": "", "model": ""},
    })


class ModelRegistry:
    """Registro central de providers y modelos."""

    def __init__(self):
        self.providers: Dict[str, ProviderConfig] = {}
        self.active_provider_id: str = ""
        self.active_model: str = ""
        self.auxiliary: Dict[str, Dict[str, str]] = {}
        self._loaded = False

    def load(self):
        """Carga config desde nexus_models.yaml."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        if MODELS_CONFIG.exists():
            try:
                with open(MODELS_CONFIG, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                for p_data in data.get("providers", []):
                    p = ProviderConfig(**{k: v for k, v in p_data.items() if k in ProviderConfig.__dataclass_fields__})
                    self.providers[p.id] = p
                active = data.get("active", {})
                self.active_provider_id = active.get("provider_id", "")
                self.active_model = active.get("model", "")
                self.auxiliary = data.get("auxiliary", {})
                logger.info(f"ModelRegistry loaded: {len(self.providers)} providers, active={self.active_model}")
            except Exception as e:
                logger.error(f"Failed to load models config: {e}")

        self._loaded = True

    def save(self):
        """Persiste config a nexus_models.yaml."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "providers": [asdict(p) for p in self.providers.values()],
            "active": {
                "provider_id": self.active_provider_id,
                "model": self.active_model,
            },
            "auxiliary": self.auxiliary,
        }
        with open(MODELS_CONFIG, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        logger.info(f"ModelRegistry saved: {len(self.providers)} providers")

    def add_provider(self, provider: ProviderConfig) -> ProviderConfig:
        """Agrega o actualiza un provider."""
        self.providers[provider.id] = provider
        self.save()
        return provider

    def remove_provider(self, provider_id: str) -> bool:
        """Elimina un provider."""
        if provider_id in self.providers:
            del self.providers[provider_id]
            if self.active_provider_id == provider_id:
                self.active_provider_id = ""
                self.active_model = ""
            self.save()
            return True
        return False

    def update_provider(self, provider_id: str, updates: Dict[str, Any]) -> Optional[ProviderConfig]:
        """Actualiza campos de un provider existente."""
        p = self.providers.get(provider_id)
        if not p:
            return None
        for k, v in updates.items():
            if hasattr(p, k) and k not in ("id",):
                setattr(p, k, v)
        self.save()
        return p

    def set_active(self, provider_id: str, model: str):
        """Cambia el modelo activo global."""
        self.active_provider_id = provider_id
        self.active_model = model
        self.save()
        logger.info(f"Active model changed: {provider_id}/{model}")

    def get_active(self) -> Dict[str, str]:
        """Retorna el modelo activo actual."""
        return {
            "provider_id": self.active_provider_id,
            "model": self.active_model,
        }

    def get_active_model_full(self) -> Optional[Dict[str, Any]]:
        """Retorna info completa del modelo activo (provider + model)."""
        if not self.active_provider_id or not self.active_model:
            return None
        p = self.providers.get(self.active_provider_id)
        if not p:
            return None
        return {
            "id": f"{p.id}::{self.active_model}",
            "name": self.active_model,
            "provider_id": p.id,
            "provider_name": p.name,
            "provider_type": p.type,
            "base_url": p.base_url,
            "api_key": p.api_key,
            "model": self.active_model,
        }

    def list_models(self) -> List[Dict[str, Any]]:
        """Lista todos los modelos disponibles de todos los providers activos."""
        models = []
        for p in self.providers.values():
            if not p.enabled:
                continue
            for m in p.models:
                models.append({
                    "id": f"{p.id}::{m}",
                    "name": m,
                    "provider_id": p.id,
                    "provider_name": p.name,
                    "provider_type": p.type,
                    "is_free": p.is_free,
                })
        return models

    def resolve_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Resuelve un model_id (formato 'provider_id::model_name') a info completa."""
        if "::" not in model_id:
            # Buscar por nombre en todos los providers
            for p in self.providers.values():
                if not p.enabled:
                    continue
                if model_id in p.models:
                    return {
                        "provider_id": p.id,
                        "provider_type": p.type,
                        "base_url": p.base_url,
                        "api_key": p.api_key,
                        "model": model_id,
                        "name": model_id,
                        "provider_name": p.name,
                    }
            return None

        provider_id, model_name = model_id.split("::", 1)
        p = self.providers.get(provider_id)
        if not p or not p.enabled:
            return None
        return {
            "provider_id": p.id,
            "provider_type": p.type,
            "base_url": p.base_url,
            "api_key": p.api_key,
            "model": model_name,
            "name": model_name,
            "provider_name": p.name,
        }

    async def probe_ollama(self, base_url: str = "http://localhost:11434") -> List[str]:
        """Auto-detecta modelos disponibles en un servidor Ollama."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    logger.info(f"Ollama probe: {len(models)} models at {base_url}")
                    return models
        except Exception as e:
            logger.warning(f"Ollama probe failed: {e}")
        return []

    async def probe_openai_compatible(self, base_url: str, api_key: str = "") -> List[str]:
        """Auto-detecta modelos en un endpoint OpenAI-compatible (/v1/models)."""
        try:
            import httpx
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{base_url}/v1/models", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m["id"] for m in data.get("data", [])]
                    logger.info(f"OpenAI-compatible probe: {len(models)} models at {base_url}")
                    return models
        except Exception as e:
            logger.warning(f"OpenAI-compatible probe failed: {e}")
        return []

    async def auto_detect_ollama(self):
        """Auto-detecta Ollama y registra si está disponible."""
        models = await self.probe_ollama()
        if models:
            ollama_id = "ollama-local"
            if ollama_id in self.providers:
                self.providers[ollama_id].models = models
            else:
                self.providers[ollama_id] = ProviderConfig(
                    id=ollama_id,
                    name="Ollama (Local)",
                    type="ollama",
                    base_url="http://localhost:11434",
                    enabled=True,
                    models=models,
                    is_free=True,
                )
            self.save()
            logger.info(f"Auto-detected Ollama: {len(models)} models")
        return models

    def to_api_response(self) -> Dict[str, Any]:
        """Serializa el estado completo para la API."""
        return {
            "providers": [asdict(p) for p in self.providers.values()],
            "active": self.get_active(),
            "models": self.list_models(),
            "auxiliary": self.auxiliary,
        }


# Singleton
_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
        _registry.load()
    return _registry


# ─── Compat stubs (used by execution_service.py) ───────────────────────────

from enum import Enum

class TaskType(Enum):
    CODE = "code"
    RESEARCH = "research"
    REASONING = "reasoning"
    VISION = "vision"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    CHAT = "chat"
    FAST = "fast"

TASK_KEYWORDS = {
    TaskType.CODE: ["programa", "codigo", "code", "python", "javascript", "typescript", "react", "bug", "debug", "refactor", "implementar", "api", "docker", "server", "deploy", "git"],
    TaskType.RESEARCH: ["investiga", "research", "busca", "web", "paper", "estudia", "documentacion", "tutorial", "que es", "como funciona", "explica"],
    TaskType.REASONING: ["razona", "piensa", "analiza", "por que", "causa", "solucion", "problema", "evalua", "compara", "decide", "estrategia"],
    TaskType.VISION: ["imagen", "captura", "screenshot", "foto", "video", "ocr", "que ves", "describe la imagen"],
    TaskType.CREATIVE: ["escribe", "cuento", "historia", "blog", "articulo", "contenido", "creativo", "narrativa", "copy", "marketing"],
    TaskType.ANALYSIS: ["analisis", "datos", "metricas", "estadistica", "reporte", "resumen", "evalua", "mide", "compara"],
    TaskType.FAST: ["rapido", "breve", "corto", "resumi", "dame un ejemplo"],
}

def classify_task_type(task: str) -> TaskType:
    lower = task.lower()
    scores = {t: 0 for t in TaskType}
    for tt, kws in TASK_KEYWORDS.items():
        for kw in kws:
            if kw in lower:
                scores[tt] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else TaskType.CHAT


def select_model(task: str, task_type=None, prefer_local=False, require_vision=False):
    """Select the best model for a task. Returns a ModelInfo-like object."""
    if task_type is None:
        task_type = classify_task_type(task)
    # Try registry first
    reg = get_model_registry()
    models = reg.list_models()
    if models:
        m = models[0]
        class _R:
            pass
        r = _R()
        r.id = m.get("id", "")
        r.name = m.get("name", "")
        r.provider = m.get("provider_name", "")
        r.description = m.get("name", "")
        return r
    # Fallback
    class _F:
        id = "deepseek-v4-flash-free"
        name = "DeepSeek V4 Flash Free"
        provider = "opencode-zen"
        description = "Fallback model"
    return _F()

