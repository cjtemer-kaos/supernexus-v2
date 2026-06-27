"""Routing Service — task classification, keyword routing, LLM classify, sticky cache."""
from __future__ import annotations
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

from src.core.o1_indexing import O1IndexManager
from src.brain.routing import TaskClassification

logger = logging.getLogger(__name__)


@dataclass
class RoutingService:
    gemas: Dict[str, Any] = field(default_factory=dict)
    llm_call_fn: Optional[Any] = None
    o1_index: Optional[O1IndexManager] = None

    _sticky_cache: Dict[str, dict] = field(default_factory=dict)
    _sticky_ttl_s: int = 300

    def classify(self, task: str, session_id: str = "") -> TaskClassification:

        task_lower = task.lower()
        selected_gems: Set[str] = set()

        selected_gems |= self._multi_word_match(task_lower)
        if not selected_gems:
            selected_gems |= self._o1_index_match(task_lower)
        selected_gems |= self._keyword_match(task_lower)
        selected_gems = self._llm_fallback(task_lower, selected_gems, task)
        if not selected_gems:
            selected_gems = {"director"}
        if "director" in selected_gems:
            selected_gems.discard("ayuda")

        engines = ["nexus_master"]
        if any(k in task_lower for k in ["gpu", "heavy", "train", "video", "image"]):
            engines.append("nexus_remote")
        if any(k in task_lower for k in ["research", "web", "search"]):
            engines.append("openclaw")

        result = TaskClassification(
            task=task,
            selected_gems=list(selected_gems),
            selected_engines=engines,
            confidence=0.8 if len(selected_gems) > 1 else 0.5,
            can_parallelize=len(engines) > 1,
        )
        if session_id:
            self._sticky_cache[session_id] = {
                "gems": result.selected_gems,
                "engines": result.selected_engines,
                "timestamp": time.time(),
            }
        return result

    def _multi_word_match(self, task_lower: str) -> Set[str]:
        multi_word = {
            "vulnerabilidad": "security", "vulnerabilidades": "security", "owasp": "security", "penetration": "security",
            "logs": "debugger", "traceback": "debugger", "excepcion": "debugger",
            "microservicio": "code", "rest api": "code", "restful": "code",
            "entrena": "trainer", "capacitacion": "trainer", "enseña": "trainer",
            "pc control": "vision", "cli agent": "opencode",
            "handoff": "code", "delegar": "code",
            "tts": "music", "stt": "music", "habla": "music",
            "rcon": "producer", "rust server": "producer",
            "que puedes hacer": "director", "como funciona": "director",
            "que sabes hacer": "director", "funcionalidades": "director",
            "que gemas tienes": "director",
            "optimizar tokens": "prompter",
            "base de conocimiento": "biblioteca", "organiza": "biblioteca",
            "backup diario": "producer", "schedule": "producer",
            "describe esta imagen": "vision",
            "ejecuta comando": "opencode", "script bash": "opencode", "bash script": "opencode",
        }
        return {gem for pattern, gem in multi_word.items() if pattern in task_lower}

    def _o1_index_match(self, task_lower: str) -> Set[str]:
        if self.o1_index is None:
            return set()
        selected: Set[str] = set()
        for keyword in task_lower.split():
            if len(keyword) > 2:
                gemas = self.o1_index.get_gemas_by_keyword(keyword)
                selected.update(gemas)
        return selected

    def _keyword_match(self, task_lower: str) -> Set[str]:
        keywords_to_gem = {
            "refactor": "code", "codigo": "code", "programa": "code",
            "python": "code", "javascript": "code", "golang": "code", "rust": "code",
            "api": "code", "endpoint": "code", "implementa": "code",
            "scholar": "scholar", "research": "scholar", "investiga": "scholar",
            "documentacion": "scholar", "bibliografia": "scholar",
            "debug": "debugger", "bug": "debugger", "error": "debugger", "fix": "debugger",
            "creative": "creative", "escribe": "creative", "contenido": "creative",
            "test": "tester", "qa": "tester", "prueba": "tester",
            "security": "security", "hack": "security", "encrypt": "security", "cifrar": "security",
            "deploy": "devops", "docker": "devops", "devops": "devops", "despliega": "devops",
            "optimiza": "optimizer", "performance": "optimizer", "rendimiento": "optimizer",
            "analiza": "analyst", "analytics": "analyst", "metricas": "analyst", "dashboard": "analyst",
            "trainer": "trainer", "enseñar": "trainer", "educar": "trainer",
            "herramienta": "opencode", "scripting": "opencode", "script": "opencode", "bash": "opencode", "shell": "opencode", "powershell": "opencode",
            "vision": "vision", "screenshot": "vision", "pantalla": "vision",
            "imagen": "vision", "describe": "vision",
            "opencode": "opencode", "comando": "opencode", "cli": "opencode",
            "delega": "code", "handoff": "code", "compile": "code", "sandbox": "code",
            "design": "design", "logo": "design", "ui": "design",
            "music": "music", "audio": "music", "voz": "music",
            "prompter": "prompter", "prompt": "prompter",
            "producer": "producer", "automatiza": "producer", "scheduler": "producer",
            "ayuda": "ayuda", "guide": "ayuda", "tutorial": "ayuda", "onboarding": "ayuda",
            "memoria": "sage", "aprender": "sage", "recordar": "sage",
            "arquitectura": "architect", "infra": "architect", "sistema": "architect",
            "busca": "scholar", "explora": "scholar",
            "gemas": "director", "capacidades": "director", "estado": "director", "status": "director",
        }
        return {gem for keyword, gem in keywords_to_gem.items() if keyword in task_lower}

    def _llm_fallback(self, task_lower: str, selected_gems: Set[str], task: str) -> Set[str]:
        """Determine if LLM classification is needed. Non-async — returns selected_gems,
        actual LLM call happens in the director's execute method."""
        director_meta = bool(selected_gems == {"director"} and any(
            p in task_lower for p in ["que gemas tienes", "que puedes hacer",
                                        "que sabes hacer", "funcionalidades",
                                        "como funciona", "capacidades", "status"]
        ))
        if (not selected_gems or selected_gems == {"director"}) and not director_meta:
            if self.llm_call_fn is not None:
                return selected_gems  # caller handles async LLM
        return selected_gems

    async def shutdown(self) -> None:
        pass

    async def initialize(self) -> None:
        pass

    def healthcheck(self) -> bool:
        return True
