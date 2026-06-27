"""
Builders — Carga el set estándar de gemas (5 dedicated + 18 manifests = 23).

Las 5 dedicated (ayuda, scholar, sage, biblioteca, prompter) se importan
desde gemas_core.workers y toman precedencia sobre el manifest JSON del
mismo nombre. Las 18 role-LLM restantes se cargan desde data/gemas/*.json.

Para añadir gemas client-specific (e.g. 8 gemas operativas Rust de LatamRust),
importar las clases desde gemas_client_overrides y mergear con el resultado.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .base import GemaBase
from .llm_role_gema import load_all_role_gemas

logger = logging.getLogger("gemas-core.builders")

# IDs de las gemas dedicated estándar (con worker Python).
# 'web_research' fue añadido en v1.6.0 (port RUFUS primitives → gem).
STANDARD_DEDICATED_IDS = (
    "ayuda", "scholar", "sage", "biblioteca", "prompter", "web_research",
)

# IDs de las 18 gemas role-LLM estándar (manifests sin worker).
# Mantener sincronizado con los manifests en data/gemas/*.json.
# 'prompter' fue promovido a dedicated en v1.1.0 (ver CHANGELOG).
STANDARD_ROLE_IDS = (
    "analyst", "architect", "code", "codex", "creative",
    "debugger", "design", "devops", "director", "engineer",
    "music", "opencode", "optimizer", "producer",
    "security", "tester", "trainer", "vision",
)


def list_standard_dedicated_ids() -> tuple:
    """Retorna IDs de las 5 gemas dedicated estándar."""
    return STANDARD_DEDICATED_IDS


def list_standard_role_ids() -> tuple:
    """Retorna IDs de las 18 gemas role-LLM estándar."""
    return STANDARD_ROLE_IDS


def list_all_standard_ids() -> tuple:
    """Retorna IDs de las 23 gemas estándar (5 dedicated + 18 role)."""
    return STANDARD_DEDICATED_IDS + STANDARD_ROLE_IDS


def _load_dedicated_workers(workers_module: Optional[Any] = None) -> Dict[str, GemaBase]:
    """Carga las 5 gemas dedicated estándar desde gemas_core.workers.

    Si workers_module es None, importa dinámicamente gemas_core.workers.
    Esto permite a los clientes pasar su propio módulo (e.g. con custom
    workers) sin tocar el estándar.
    """
    if workers_module is None:
        from . import workers as workers_module
    out: Dict[str, GemaBase] = {}
    for gema_id in STANDARD_DEDICATED_IDS:
        cls = getattr(workers_module, _class_name(gema_id), None)
        if cls is None:
            logger.warning(f"worker class not found: {_class_name(gema_id)}")
            continue
        try:
            instance = cls()
            out[gema_id] = instance
        except Exception as e:
            logger.error(f"failed instantiating {gema_id}: {e}")
    return out


def _class_name(gema_id: str) -> str:
    """Convierte gema_id a nombre de clase (e.g. 'ayuda' -> 'AyudaGem',
    'web_research' -> 'WebResearchGem').

    Cada segmento separado por '_' se capitaliza individualmente para
    soportar snake_case compuesto (v1.6.0 web_research fue el primer
    ID con underscore en STANDARD_DEDICATED_IDS).
    """
    parts = gema_id.split("_")
    return "".join(p.capitalize() for p in parts) + "Gem"


def build_standard_gemas(
    gemas_dir: Path,
    ollama_url: str = "http://127.0.0.1:11434",
    timeout_s: int = 120,
    workers_module: Optional[Any] = None,
) -> Dict[str, GemaBase]:
    """Carga el set estándar de gemas: 5 dedicated + 18 manifests.

    Las 5 dedicated se instancian desde gemas_core.workers (o el módulo
    pasado). Las 18 role-LLM se cargan desde data/gemas/*.json via
    load_all_role_gemas().

    Args:
        gemas_dir: Path al directorio data/gemas/ del proyecto cliente.
        ollama_url: URL del servidor Ollama.
        timeout_s: Timeout por request Ollama.
        workers_module: Módulo de workers (opcional). Si None, usa
                       gemas_core.workers.

    Returns:
        Dict {gema_id: instancia_GemaBase} con 23 entradas (5+18).
    """
    gemas: Dict[str, GemaBase] = {}

    # 1) Cargar 5 dedicated (toman precedencia sobre manifests con mismo nombre).
    for gema_id, instance in _load_dedicated_workers(workers_module).items():
        gemas[gema_id] = instance

    # 2) Cargar manifests. Los 5 con nombre = dedicated_id se saltan (worker gana).
    role_gemas = load_all_role_gemas(
        gemas_dir=Path(gemas_dir),
        ollama_url=ollama_url,
        timeout_s=timeout_s,
    )
    for gema_id, instance in role_gemas.items():
        if gema_id in gemas:
            logger.debug(f"manifest '{gema_id}' ignorado (overridden por dedicated worker)")
            continue
        gemas[gema_id] = instance

    return gemas
