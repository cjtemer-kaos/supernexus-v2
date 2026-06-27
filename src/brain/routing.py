"""Brain: Routing — clasifica tareas y las rutea a la gema correcta.

El cerebro de NEXUS para decidir QUE gema atiende cada tarea.

4 fases (en orden, primero que matchea gana cuando es definitivo):
    1. Multi-word patterns (mas especificos)
    2. O(1) index routing (via o1_indexing si esta disponible)
    3. Single-keyword matching (refina/extiende)
    4. LLM classification (fallback, async, con cache)

Sticky cache (AnythingLLM pattern): mensajes de seguimiento en la misma
sesion reusan la clasificacion previa (TTL configurable).

Design:
    RoutingBrain recibe el director como owner. Lee `o1_index` opcionalmente
    (Phase 2 se salta si no esta). El LLM classify es opt-in via
    `enable_llm_classify=False` para tests sin red.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set

import httpx

from src.brain.fast_router import FastRouter, FastRouteResult, get_fast_router

logger = logging.getLogger(__name__)


# ── Data ────────────────────────────────────────────────────────────────


@dataclass
class TaskClassification:
    """Resultado de clasificacion."""
    task: str
    selected_gems: List[str]
    selected_engines: List[str]
    confidence: float
    can_parallelize: bool
    priority: int = 3


# ── Routing tables ──────────────────────────────────────────────────────


MULTI_WORD_PATTERNS: Dict[str, str] = {
    "vulnerabilidad": "security", "vulnerabilidades": "security",
    "owasp": "security", "penetration": "security",
    "logs": "debugger", "traceback": "debugger", "excepcion": "debugger",
    "microservicio": "code", "rest api": "code", "restful": "code",
    "entrena": "trainer", "capacitacion": "trainer", "enseña": "trainer",
    "ensename": "trainer", "enseñame": "trainer", "ensena": "trainer",
    "audita seguridad": "security", "audita la seguridad": "security",
    "pipeline": "devops", "ci/cd": "devops", "continuous integration": "devops",
    "diseno de sistema": "architect",
    "cuento de": "creative", "cuentos de": "creative",
    "entorno aislado": "codex", "entorno sandbox": "codex",
    "optimizar tokens": "prompter",
    "guia del sistema": "ayuda", "guia de usuario": "ayuda",
    "campaña de marketing": "producer", "campana de marketing": "producer",
    "genera musica": "music", "genera una melodia": "music", "crea una cancion": "music",
    "toolchain": "engineer", "build system": "engineer", "compilador": "engineer",
    "tuning": "optimizer", "ajuste de rendimiento": "optimizer", "optimizar base de datos": "optimizer",
    "pc control": "vision", "cli agent": "opencode",
    "handoff": "code", "delegar": "code",
    "tts": "music", "stt": "music", "habla": "music",
    "rcon": "producer", "rust server": "producer",
    "que puedes hacer": "ayuda", "como funciona": "ayuda",
    "que sabes hacer": "ayuda", "funcionalidades": "ayuda",
    "que gemas tienes": "ayuda",
    "base de conocimiento": "biblioteca", "organiza": "biblioteca",
    "backup diario": "producer", "schedule": "producer",
    "describe esta imagen": "vision",
    "ejecuta comando": "opencode", "script bash": "opencode", "bash script": "opencode",
    # design phrases (prioridad sobre 'dashboard' → analyst)
    "diseña un": "design", "diseño de": "design", "diseña una": "design",
    "interfaz de usuario": "design", "design system": "design",
    # sage (conceptual/cientifico)
    "explica que": "sage", "explica como": "sage", "que es la": "sage",
    "concepto de": "sage", "teoria de": "sage",
    # real-time / live data (debe ir a scholar, no a LLM que no tiene acceso)
    "precio actual": "scholar", "valor en vivo": "scholar", "datos en tiempo real": "scholar",
    "ultima version": "scholar", "última versión": "scholar", "latest version": "scholar",
    "fecha de release": "scholar", "fecha de lanzamiento": "scholar",
}


SINGLE_KEYWORD_PATTERNS: Dict[str, str] = {
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
    "analiza": "analyst", "analytics": "analyst", "metricas": "analyst", "dashboard": "analyst", "analisis": "analyst",
    "trainer": "trainer", "enseñar": "trainer", "educar": "trainer",
    "herramienta": "opencode", "scripting": "opencode", "script": "opencode",
    "bash": "opencode", "shell": "opencode", "powershell": "opencode",
    "vision": "vision", "screenshot": "vision", "pantalla": "vision",
    "imagen": "vision", "describe": "vision",
    "opencode": "opencode", "comando": "opencode", "cli": "opencode",
    "delega": "code", "handoff": "code", "compile": "code",
    "design": "design", "logo": "design", "ui/ux": "design",
    "tailwind": "design", "frontend": "design", "css": "design",
    "diseña": "design", "diseño": "design",
    "cuantica": "sage", "fisica": "sage", "ciencia": "sage",
    "filosofia": "sage", "concepto": "sage", "entropia": "sage",
    "music": "music", "audio": "music", "voz": "music",
    "prompter": "prompter", "prompt": "prompter",
    "producer": "producer", "automatiza": "producer", "scheduler": "producer",
    "ayuda": "ayuda", "guide": "ayuda", "tutorial": "ayuda", "onboarding": "ayuda", "guia": "ayuda",
    "memoria": "sage", "aprender": "sage", "recordar": "sage",
    "biblio": "biblioteca", "clasifica": "biblioteca", "organización": "biblioteca",
    "ingeniería": "engineer", "ingenieria": "engineer", "build": "engineer",
    "compilacion": "codex", "sandbox": "codex",
    "codex": "codex", "delega a codex": "codex",
    "arquitectura": "architect", "infra": "architect", "sistema": "architect",
    "busca": "scholar", "explora": "scholar",
    "investigar": "scholar", "investigacion": "scholar",
    "busca en la web": "scholar", "buscar en la web": "scholar",
    "busca en internet": "scholar", "buscar en internet": "scholar",
    "que sabes de": "scholar", "informacion sobre": "scholar",
    "información sobre": "scholar", "noticias sobre": "scholar",
    "novedades": "scholar", "ultimas noticias": "scholar", "últimas noticias": "scholar",
    "driver": "scholar", "drivers": "scholar",
    # Real-time / web data (must go to scholar for live data)
    "precio": "scholar", "cotizacion": "scholar", "cotización": "scholar",
    "valor actual": "scholar", "tipo de cambio": "scholar", "dolar": "scholar",
    "dólar": "scholar", "euro": "scholar", "bitcoin": "scholar", "crypto": "scholar",
    "criptomonedas": "scholar", "ethereum": "scholar", "bolsa": "scholar",
    "mercado": "scholar", "accion": "scholar", "acciones": "scholar",
    "version actual": "scholar", "ultima version": "scholar", "ultima release": "scholar",
    "que version": "scholar", "nueva version": "scholar", "nuevo release": "scholar",
    "última versión": "scholar", "latest version": "scholar", "latest release": "scholar", "current version": "scholar",
    "que dia": "scholar", "qué día": "scholar", "que hora": "scholar", "qué hora": "scholar",
    "clima": "scholar", "tiempo": "scholar", "temperatura": "scholar",
    "en este momento": "scholar", "ahora mismo": "scholar", "hoy": "scholar",
    "esta semana": "scholar", "este mes": "scholar", "recien": "scholar",
    "recientement": "scholar", "acaba de": "scholar", "acaban de": "scholar",
    "fecha de release": "scholar", "fecha de lanzamiento": "scholar",
    "trending": "scholar", "viral": "scholar", "twitter": "scholar",
    "wikipedia": "scholar", "definicion de": "scholar", "definición de": "scholar",
    "quien escribio": "scholar", "quién escribió": "scholar", "quien gano": "scholar",
    "resultado de": "scholar", "marcador": "scholar",
    "gemas": "director", "capacidades": "director", "estado": "director", "status": "director",
    # Identity & generic chit-chat → ayuda (guia del sistema)
    "quien eres": "ayuda", "quien sos": "ayuda", "que eres": "ayuda",
    "hola": "ayuda", "hi": "ayuda", "hello": "ayuda", "buenas": "ayuda",
    "como estas": "ayuda", "como va": "ayuda", "que tal": "ayuda",
    "presentate": "ayuda", "preséntate": "ayuda",
    "nexus": "ayuda", "director": "ayuda",
    # File system / disk operations → engineer (tiene herramientas de sistema)
    "carpeta": "engineer", "carpetas": "engineer", "directorio": "engineer",
    "directorios": "engineer", "archivo": "engineer", "archivos": "engineer",
    "lista": "engineer", "listar": "engineer", "muestra": "engineer",
    "dime el contenido": "engineer", "dime las carpetas": "engineer",
    "que hay en": "engineer", "contenido de": "engineer",
    "ls ": "engineer", "dir ": "engineer", "d:/": "engineer", "d:\\": "engineer",
    "c:/": "engineer", "c:\\": "engineer", "disco": "engineer",
}


ID_META_KEYWORDS: List[str] = [
    "que gemas tienes", "que puedes hacer",
    "que sabes hacer", "funcionalidades",
    "como funciona", "capacidades", "status",
    # Identity / chit-chat: skip LLM classification
    "quien eres", "quien sos", "que eres", "presentate", "preséntate",
    "hola", "hi", "hello", "buenas", "buen dia", "buenos dias",
    "como estas", "como va", "que tal", "nexus", "director",
]


VALID_GEMAS: Set[str] = {
    "code", "scholar", "security", "analyst", "debugger",
    "optimizer", "tester", "devops", "creative", "architect",
    "vision", "director", "ayuda", "sage",
    "biblioteca", "opencode", "design", "music",
    "prompter", "producer", "trainer", "engineer", "codex",
}


# Engine selection by task content
ENGINE_RULES = [
    (("gpu", "heavy", "train", "video", "image"), "nexus_remote"),
    (("research", "web", "search"), "openclaw"),
]


# ── RoutingBrain ────────────────────────────────────────────────────────


class RoutingBrain:
    """Clasificacion de tareas a gemas, con sticky cache y LLM fallback."""

    def __init__(
        self,
        owner: Any,
        sticky_ttl_s: int = 300,
        enable_llm_classify: bool = True,
    ):
        """
        Args:
            owner: el Director — espera `o1_index` opcional para Phase 2.
            sticky_ttl_s: TTL del cache de sesion (default 5 min).
            enable_llm_classify: si False, Phase 4 (LLM) se salta (util para tests).
        """
        self.owner = owner
        self.sticky_ttl_s = sticky_ttl_s
        self.enable_llm_classify = enable_llm_classify
        self._sticky_cache: Dict[str, dict] = {}

    # ── Public API ──────────────────────────────────────────────────────

    async def classify(
        self,
        task: str,
        session_id: str = "",
    ) -> TaskClassification:
        """Clasifica una tarea aplicando las 4 fases + FastRouter + sticky cache.

        Flujo:
          1. Phases 1-3 (keyword deterministic): multi-word → O(1) index → single-keyword
          2. FastRouter TF-IDF (si no hay match deterministico, <1ms)
          3. LLM fallback (solo si FastRouter confianza < threshold)

        Sticky strategy: only short follow-ups (< 6 words, no explicit gem keyword)
        inherit the previous gem. Messages with clear intent always re-classify so
        topic changes (chit-chat -> filesystem action) route correctly.
        """
        task_lower = task.lower()
        word_count = len(task_lower.split())
        has_explicit_keyword = (
            any(p in task_lower for p in MULTI_WORD_PATTERNS) or
            any(k in task_lower for k in SINGLE_KEYWORD_PATTERNS)
        )

        # Sticky cache only for SHORT follow-ups WITHOUT explicit keywords
        cached = self._check_sticky_cache(session_id)
        if cached is not None and word_count < 6 and not has_explicit_keyword:
            return TaskClassification(
                task=task,
                selected_gems=cached["gems"],
                selected_engines=cached.get("engines", ["nexus_master"]),
                confidence=0.85,
                can_parallelize=False,
            )

        selected_gems: Set[str] = set()
        fast_result: Optional[FastRouteResult] = None

        # Phase 1: Multi-word
        for pattern, gem in MULTI_WORD_PATTERNS.items():
            if pattern in task_lower:
                selected_gems.add(gem)

        # Phase 2: O(1) index (optional)
        if not selected_gems:
            o1_index = getattr(self.owner, "o1_index", None)
            if o1_index is not None:
                for keyword in task_lower.split():
                    if len(keyword) > 2:
                        try:
                            selected_gems.update(o1_index.get_gemas_by_keyword(keyword))
                        except Exception:
                            pass

        # Phase 3: Single keyword (always runs to refine)
        for keyword, gem in SINGLE_KEYWORD_PATTERNS.items():
            if keyword in task_lower:
                selected_gems.add(gem)

        # Phase 4: FastRouter TF-IDF (cuando no hay matches deterministicos)
        has_id_meta = (
            selected_gems in ({"director"}, {"ayuda"}) and
            any(p in task_lower for p in ID_META_KEYWORDS)
        )
        if not selected_gems and not has_id_meta:
            router = get_fast_router()
            fast_result = router.classify(task)
            if fast_result.confidence >= router._confidence_threshold:
                selected_gems = {fast_result.gem}
            elif self.enable_llm_classify:
                # LLM fallback solo si FastRouter confianza < threshold
                llm_gema = await self._llm_classify(task)
                if llm_gema:
                    fast_result = FastRouteResult(
                        gem=llm_gema,
                        confidence=0.6,
                        all_scores=fast_result.all_scores,
                        top_n=[(llm_gema, 0.6)] + fast_result.top_n,
                        source="llm_fallback",
                    )
                    selected_gems = {llm_gema}

        if not selected_gems:
            selected_gems = {"director"}

        # Confidence: usar FastRouter si disponible, sino default
        confidence = 0.5
        if fast_result:
            confidence = fast_result.confidence
        elif len(selected_gems) > 0:
            confidence = 0.8

        # Engine selection
        engines = ["nexus_master"]
        for keywords, engine in ENGINE_RULES:
            if any(k in task_lower for k in keywords):
                engines.append(engine)

        result = TaskClassification(
            task=task,
            selected_gems=list(selected_gems),
            selected_engines=engines,
            confidence=confidence,
            can_parallelize=len(engines) > 1,
        )

        if session_id:
            self._save_to_cache(session_id, result)

        return result

    # ── Sticky cache ────────────────────────────────────────────────────

    def _check_sticky_cache(self, session_id: str) -> Optional[dict]:
        if not session_id or session_id not in self._sticky_cache:
            return None
        cached = self._sticky_cache[session_id]
        age = time.time() - cached["timestamp"]
        if age >= self.sticky_ttl_s:
            return None
        logger.debug(
            f"Sticky cache hit: session={session_id}, age={age:.0f}s, "
            f"gems={cached['gems']}"
        )
        cached["timestamp"] = time.time()  # refresh TTL
        return cached

    def _save_to_cache(self, session_id: str, result: TaskClassification) -> None:
        self._sticky_cache[session_id] = {
            "gems": result.selected_gems,
            "engines": result.selected_engines,
            "timestamp": time.time(),
        }

    def clear_cache(self, session_id: Optional[str] = None) -> None:
        """Invalida cache (un session_id o todo)."""
        if session_id is None:
            self._sticky_cache.clear()
        else:
            self._sticky_cache.pop(session_id, None)

    # ── LLM classification (Phase 4) ────────────────────────────────────

    async def _llm_classify(self, task: str) -> Optional[str]:
        """LLM fallback usando Ollama (qwen2.5-coder:7b).

        NO usa modelos fine-tuned propios — no rutean bien.
        """
        prompt = (
            f"Clasifica esta tarea en UNA gema. Responde SOLO el nombre.\n"
            f"Gemas: {', '.join(sorted(VALID_GEMAS))}\n"
            f"Tarea: {task}"
        )

        # Try Ollama
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post("http://localhost:11434/api/chat", json={
                    "model": "qwen2.5-coder:7b",
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 20},
                })
            if r.status_code == 200:
                raw = r.json().get("message", {}).get("content", "")
                gema = raw.strip().lower().split()[0].rstrip(".,!?;:") if raw.strip() else ""
                if gema in VALID_GEMAS:
                    return gema
        except Exception as e:
            logger.debug(f"Ollama LLM classify failed: {e}")

        return None
