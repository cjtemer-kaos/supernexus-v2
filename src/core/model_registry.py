"""
Model Registry — Unified catalog of ALL available models with capabilities.

Inspired by openakita/llm/capabilities.py (869 lines) and 01_CORE/nexus_director.py.
Provides intelligent model selection based on task requirements.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class Capability(Enum):
    CHAT = "chat"
    CODE = "code"
    REASONING = "reasoning"
    RESEARCH = "research"
    VISION = "vision"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    FAST = "fast"
    EMBEDDING = "embedding"
    TOOLS = "tools"


@dataclass
class ModelInfo:
    id: str
    name: str
    provider: str  # "ollama" | "opencode-zen"
    capabilities: list[Capability]
    context_window: int = 8192
    speed_tps: float = 25.0
    quality: float = 5.0  # 1-10
    cost: float = 0.0  # per 1k tokens
    description: str = ""

    def supports(self, cap: Capability) -> bool:
        return cap in self.capabilities


# ── Unified Model Catalog ────────────────────────────────────────────────────

MODEL_CATALOG: list[ModelInfo] = [
    # === OpenCode Zen (Cloud, Free) ===
    ModelInfo(
        id="deepseek-v4-flash-free",
        name="DeepSeek V4 Flash Free",
        provider="opencode-zen",
        capabilities=[Capability.CHAT, Capability.REASONING, Capability.RESEARCH, Capability.TOOLS],
        context_window=128000,
        speed_tps=60,
        quality=8,
        cost=0,
        description="Rapido, razonamiento, proposito general. Bueno para la mayoria de tareas.",
    ),
    ModelInfo(
        id="mimo-v2.5-free",
        name="MiMo V2.5 Free",
        provider="opencode-zen",
        capabilities=[Capability.CHAT, Capability.REASONING, Capability.VISION, Capability.CODE, Capability.TOOLS],
        context_window=128000,
        speed_tps=40,
        quality=9,
        cost=0,
        description="Vision + razonamiento. Ideal para imagenes, screenshots, y tareas que requieren ver.",
    ),
    ModelInfo(
        id="nemotron-3-ultra-free",
        name="Nemotron 3 Ultra Free",
        provider="opencode-zen",
        capabilities=[Capability.CHAT, Capability.ANALYSIS, Capability.REASONING, Capability.TOOLS],
        context_window=128000,
        speed_tps=50,
        quality=8,
        cost=0,
        description="Analisis profundo, datos, metricas, evaluacion.",
    ),
    ModelInfo(
        id="north-mini-code-free",
        name="North Mini Code Free",
        provider="opencode-zen",
        capabilities=[Capability.CHAT, Capability.CODE, Capability.TOOLS],
        context_window=32000,
        speed_tps=70,
        quality=7,
        cost=0,
        description="Especializado en codigo. Rapido para programacion.",
    ),

    # === Ollama (Local, Free) ===
    ModelInfo(
        id="nexus-director-v6",
        name="Nexus Director v6",
        provider="ollama",
        capabilities=[Capability.CHAT, Capability.REASONING, Capability.ANALYSIS, Capability.TOOLS],
        context_window=32000,
        speed_tps=30,
        quality=8,
        cost=0,
        description="Director/orquestador. Razonamiento y planificacion.",
    ),
    ModelInfo(
        id="qwen3.5:9b",
        name="Qwen 3.5 9B",
        provider="ollama",
        capabilities=[Capability.CHAT, Capability.CREATIVE, Capability.REASONING],
        context_window=32000,
        speed_tps=35,
        quality=7,
        cost=0,
        description="Chat general, creativo.",
    ),
    ModelInfo(
        id="deepseek-r1:8b",
        name="DeepSeek R1 8B",
        provider="ollama",
        capabilities=[Capability.CHAT, Capability.REASONING, Capability.RESEARCH],
        context_window=32000,
        speed_tps=20,
        quality=9,
        cost=0,
        description="Razonamiento profundo, chain-of-thought.",
    ),
    ModelInfo(
        id="qwen2.5-coder:7b",
        name="Qwen 2.5 Coder 7B",
        provider="ollama",
        capabilities=[Capability.CHAT, Capability.CODE, Capability.CREATIVE],
        context_window=32000,
        speed_tps=35,
        quality=8,
        cost=0,
        description="Codigo, programacion, refactoring.",
    ),
    ModelInfo(
        id="qwen2.5vl:7b",
        name="Qwen 2.5 VL 7B",
        provider="ollama",
        capabilities=[Capability.CHAT, Capability.VISION],
        context_window=32000,
        speed_tps=25,
        quality=7,
        cost=0,
        description="Vision local. Screenshots, imagenes.",
    ),
    ModelInfo(
        id="gemma4:12b",
        name="Gemma 4 12B",
        provider="ollama",
        capabilities=[Capability.CHAT, Capability.VISION, Capability.CREATIVE],
        context_window=32000,
        speed_tps=20,
        quality=8,
        cost=0,
        description="Vision multimodal, creativo.",
    ),
    ModelInfo(
        id="nemotron-3-nano:4b",
        name="Nemotron 3 Nano 4B",
        provider="ollama",
        capabilities=[Capability.CHAT, Capability.ANALYSIS, Capability.FAST],
        context_window=8192,
        speed_tps=60,
        quality=5,
        cost=0,
        description="Rapido, lightweight, analisis basico.",
    ),
    ModelInfo(
        id="qwen2.5:0.5b",
        name="Qwen 2.5 0.5B",
        provider="ollama",
        capabilities=[Capability.CHAT, Capability.FAST],
        context_window=32000,
        speed_tps=100,
        quality=3,
        cost=0,
        description="Ultra-rapido, resumenes, clasificacion.",
    ),
]


# ── Task Type Classification ─────────────────────────────────────────────────

class TaskType(Enum):
    CODE = "code"
    RESEARCH = "research"
    REASONING = "reasoning"
    VISION = "vision"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    CHAT = "chat"
    FAST = "fast"


# Keywords that map to task types
TASK_KEYWORDS: dict[TaskType, list[str]] = {
    TaskType.CODE: [
        "programa", "codigo", "code", "python", "javascript", "typescript", "react",
        "bug", "debug", "refactor", "implementar", "clase", "funcion", "api",
        "docker", "server", "infra", "deploy", "git", "npm", "pip",
    ],
    TaskType.RESEARCH: [
        "investiga", "research", "busca", "web", "paper", "estudia", "aprende",
        "documentacion", "tutorial", "que es", "como funciona", "explica",
        "noticias", "actualidad", "leyes", "normativa",
    ],
    TaskType.REASONING: [
        "razona", "piensa", "analiza profundamente", "por que", "causa",
        "solucion", "problema", "evalua", "compara", "decide", "estrategia",
    ],
    TaskType.VISION: [
        "imagen", "captura", "screenshot", "foto", "video", "ocr",
        "mirá", "ve这张", "que ves", "describe la imagen",
    ],
    TaskType.CREATIVE: [
        "escribe", "cuento", "historia", "blog", "articulo", "contenido",
        "creativo", "narrativa", "copy", "marketing", "redes sociales",
    ],
    TaskType.ANALYSIS: [
        "analisis", "datos", "metricas", "estadistica", "reporte",
        "resumen", "evalua", "mide", "compara",
    ],
    TaskType.FAST: [
        "rapido", "breve", "corto", "resumí", "dame un ejemplo",
    ],
}


def classify_task_type(task: str) -> TaskType:
    """Classify a task into a TaskType based on keywords."""
    lower = task.lower()
    scores: dict[TaskType, int] = {t: 0 for t in TaskType}

    for task_type, keywords in TASK_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                scores[task_type] += 1

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return TaskType.CHAT
    return best


# ── Model Selection ──────────────────────────────────────────────────────────

# Mapping: TaskType → preferred capabilities (in priority order)
TASK_PREFERRED_CAPS: dict[TaskType, list[Capability]] = {
    TaskType.CODE: [Capability.CODE, Capability.TOOLS, Capability.CHAT],
    TaskType.RESEARCH: [Capability.RESEARCH, Capability.REASONING, Capability.TOOLS, Capability.CHAT],
    TaskType.REASONING: [Capability.REASONING, Capability.ANALYSIS, Capability.CHAT],
    TaskType.VISION: [Capability.VISION, Capability.CHAT],
    TaskType.CREATIVE: [Capability.CREATIVE, Capability.CHAT],
    TaskType.ANALYSIS: [Capability.ANALYSIS, Capability.REASONING, Capability.CHAT],
    TaskType.CHAT: [Capability.CHAT],
    TaskType.FAST: [Capability.FAST, Capability.CHAT],
}


def select_model(
    task: str,
    task_type: Optional[TaskType] = None,
    prefer_local: bool = False,
    require_vision: bool = False,
) -> ModelInfo:
    """Select the best model for a given task.

    Args:
        task: The task description
        task_type: Override task type classification
        prefer_local: If True, prefer Ollama models (lower latency)
        require_vision: If True, require vision capability
    """
    if task_type is None:
        task_type = classify_task_type(task)

    required_caps = [c for c in TASK_PREFERRED_CAPS.get(task_type, [Capability.CHAT])]
    if require_vision:
        required_caps = [Capability.VISION] + required_caps

    # Score each model
    scored: list[tuple[float, ModelInfo]] = []
    for model in MODEL_CATALOG:
        if prefer_local and model.provider != "ollama":
            continue

        # Check required capabilities
        has_required = all(model.supports(c) for c in required_caps[:2])
        if not has_required:
            continue

        # Score: capability match + quality + speed
        cap_match = sum(1 for c in required_caps if model.supports(c))
        score = (
            cap_match * 3.0           # capability match weight
            + model.quality * 0.5     # quality weight
            + model.speed_tps * 0.01  # speed weight (minor)
            - model.cost * 100        # cost penalty
        )
        scored.append((score, model))

    if not scored:
        # Fallback: return the first available model
        for m in MODEL_CATALOG:
            if not prefer_local or m.provider == "ollama":
                return m
        return MODEL_CATALOG[0]

    scored.sort(key=lambda x: x[0], reverse=True)
    best = scored[0][1]
    logger.info(f"Model selected: {best.id} for task_type={task_type.value} (score={scored[0][0]:.1f})")
    return best


def get_model_by_id(model_id: str) -> Optional[ModelInfo]:
    """Get a model by its ID."""
    for m in MODEL_CATALOG:
        if m.id == model_id:
            return m
    return None


def list_models(provider: Optional[str] = None) -> list[ModelInfo]:
    """List all models, optionally filtered by provider."""
    if provider:
        return [m for m in MODEL_CATALOG if m.provider == provider]
    return list(MODEL_CATALOG)
