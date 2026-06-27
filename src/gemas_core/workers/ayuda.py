"""
AyudaGem — Gema de ayuda reactiva del sistema.

Se adapta al nivel del usuario (novice/intermediate/advanced), enseña
capacidades del sistema, sugiere opciones y muestra cómo extender/modificar Nexus.

Métodos:
    execute(task) -> dict
    analyze_intent(task) -> dict
    get_profile() -> dict
    reset_profile() -> dict
    full_catalog(client_gemas=None) -> dict
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import GemaBase

logger = logging.getLogger("gemas-core.workers.ayuda")


class AyudaGem(GemaBase):
    """Gema de ayuda reactiva."""

    name = "ayuda"
    description = "Guía reactiva del sistema, perfil adaptativo de usuario"
    category = "workflow"

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path.cwd() / "data" / "user_profiles"
        self.data_path = Path(data_dir)
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.profile_file = self.data_path / "ayuda_profile.json"
        self._load_profile()

    def _load_profile(self) -> None:
        if self.profile_file.exists():
            self.profile = json.loads(self.profile_file.read_text(encoding="utf-8"))
        else:
            self.profile = {
                "user_level": "novice",
                "features_used": [],
                "features_asked": [],
                "sessions": 0,
                "last_interaction": None,
                "preferred_depth": "medium",
                "learned_topics": [],
            }
            self._save_profile()

    def _save_profile(self) -> None:
        self.profile_file.write_text(
            json.dumps(self.profile, indent=2), encoding="utf-8"
        )

    def _update_profile(self, task: str, features: List[str]) -> None:
        self.profile["sessions"] += 1
        self.profile["last_interaction"] = datetime.now().isoformat()
        for f in features:
            if f not in self.profile["features_used"]:
                self.profile["features_used"].append(f)
        self._auto_escalate_level()
        self._save_profile()

    def _auto_escalate_level(self) -> None:
        used = len(self.profile["features_used"])
        if used >= 15:
            self.profile["user_level"] = "advanced"
        elif used >= 8:
            self.profile["user_level"] = "intermediate"
        else:
            self.profile["user_level"] = "novice"

    def _build_gema_catalog(self) -> str:
        """Catálogo textual de las 23 gemas estándar (5 dedicated + 18 role)."""
        return """== CATALOGO DE GEMAS (23 especialistas) ==

DEDICADAS (con worker Python propio):
  Ayuda       | Guia del sistema, onboarding adaptativo
  Scholar     | Investigacion, web search, aprendizaje
  Sage        | Memoria, persistencia, conocimiento
  Biblioteca  | Organizacion de knowledge base
  Prompter    | Prompt engineering con 13 templates + 37 patterns

ROLE-LLM (system_prompt + Ollama):
  Code        | Programacion, refactoring, code review
  Architect   | Diseno de sistemas, infraestructura
  Creative    | Contenido creativo, escritura
  Analyst     | Analisis de datos, metricas
  Engineer    | Ingenieria, herramientas
  Debugger    | Debugging, errores, troubleshooting
  Optimizer   | Performance, tuning
  Tester      | Testing, QA, validacion
  Security    | Seguridad, compliance
  DevOps      | Deploy, infraestructura
  Trainer     | Entrenamiento, educacion
  Vision      | Screenshot, OCR, control de PC
  OpenCode    | Agente CLI, ejecucion de codigo
  Codex       | Delegacion a Codex CLI
  Design      | UI/UX, multimedia, video
  Music       | Audio, voz, TTS/STT
  Producer    | Automatizacion, scheduling
  Director    | Orquestador, planning, DAG coordination"""

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        """Método principal — analiza la tarea y prepara contexto de ayuda."""
        logger.info(f"AyudaGem executing: {task[:80]}")
        intent = await self.analyze_intent(task)
        return {
            "success": True,
            "gema": "AyudaGem",
            "intent": intent,
            "profile": {
                "level": self.profile["user_level"],
                "features_used": len(self.profile["features_used"]),
                "total_sessions": self.profile["sessions"],
            },
            "user_message": task,
            "catalog": self._build_gema_catalog(),
            "timestamp": datetime.now().isoformat(),
        }

    async def analyze_intent(self, task: str) -> Dict[str, Any]:
        """Detecta si la tarea es una pregunta de ayuda o una acción directa."""
        task_lower = task.lower()
        help_keywords = [
            "ayuda", "help", "que puedes", "como funciona", "capacidades",
            "que sabes", "tutorial", "guia", "onboarding", "empezar",
            "nuevo", "aprender", "explica", "que hace", "que puedo",
        ]
        # All 24 gemas (6 dedicated + 18 role-LLM) ordenados por longitud
        # descendente para evitar que 'code' se matchee antes que 'codex'
        # en 'codex-123'. v1.1.0: prompter añadido a dedicated.
        # v1.6.0: web_research añadido a dedicated.
        role_names = (
            "scholar", "architect", "creative", "analyst", "engineer",
            "debugger", "optimizer", "tester", "security", "devops",
            "trainer", "biblioteca", "opencode", "codex", "design",
            "music", "prompter", "producer", "director", "vision",
            "web_research", "code", "sage", "ayuda",
        )
        is_help_request = any(k in task_lower for k in help_keywords)
        # Match con word-boundary-ish: 'test' matchea 'tester' pero
        # 'code' no debe matchear 'codex' (ordenados por longitud).
        features_mentioned: List[str] = []
        for g in role_names:
            if g in task_lower:
                # Si ya hay un match más largo, saltar
                if any(other != g and other in task_lower and g in other
                       for other in role_names):
                    continue
                features_mentioned.append(g)
        self._update_profile(task, features_mentioned)
        return {
            "is_help_request": is_help_request,
            "features_mentioned": features_mentioned,
            "user_level": self.profile["user_level"],
            "suggested_depth": self.profile["preferred_depth"],
        }

    async def get_profile(self) -> Dict[str, Any]:
        return self.profile

    async def reset_profile(self) -> Dict[str, Any]:
        self.profile = {
            "user_level": "novice",
            "features_used": [],
            "features_asked": [],
            "sessions": 0,
            "last_interaction": None,
            "preferred_depth": "medium",
            "learned_topics": [],
        }
        self._save_profile()
        return {"success": True, "message": "Perfil resetado a novice"}

    async def full_catalog(
        self,
        client_gemas: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Devuelve el catálogo completo del sistema.

        Args:
            client_gemas: Lista opcional de gemas client-specific
                          (e.g. las 8 gemas operativas Rust de LatamRust).
                          Cada una debe ser un dict con
                          {id, name, description, category}.

        Returns:
            Dict con:
              - llm_dedicated: 6 gemas dedicated (v1.6.0: +1 web_research)
              - llm_role_count: 18
              - llm_role_examples: 18 IDs
              - client_operatives: lista de client_gemas (si se pasó)
              - total: total de gemas
        """
        llm_dedicated = [
            {"id": "ayuda", "name": "Ayuda"},
            {"id": "scholar", "name": "Scholar"},
            {"id": "sage", "name": "Sage"},
            {"id": "biblioteca", "name": "Biblioteca"},
            {"id": "prompter", "name": "Prompter",
             "note": "Prompt engineering con 13 templates + 37 patterns"},
            {"id": "web_research", "name": "Web Research",
             "note": "Crawling + ranking de páginas web (port RUFUS primitives)"},
        ]
        llm_role_examples = list(
            "code architect creative analyst engineer debugger optimizer "
            "tester security devops trainer vision opencode codex design "
            "music producer director".split()
        )
        total = 6 + 18
        out: Dict[str, Any] = {
            "llm_dedicated": llm_dedicated,
            "llm_role_count": 18,
            "llm_role_examples": llm_role_examples,
            "total": total,
        }
        if client_gemas:
            out["client_operatives"] = client_gemas
            out["total"] = total + len(client_gemas)
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": "ayuda",
            "name": "AYUDA",
            "description": self.description,
            "category": self.category,
            "type": "dedicated",
        }
