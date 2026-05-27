"""
Gema Ayuda - Guia reactiva del sistema para SuperNEXUS v2.0

Se adapta al nivel del usuario, ensena capacidades del sistema,
sugiere opciones y muestra como extender/modificar Nexus.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AyudaGem:
    """
    Gema de ayuda reactiva. Se adapta al usuario, ensena el sistema,
    sugiere opciones y guia en la extension de Nexus.
    """

    def __init__(self):
        self.data_path = Path(__file__).parent.parent.parent / "data" / "user_profiles"
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.profile_file = self.data_path / "ayuda_profile.json"
        self._load_profile()

    def _load_profile(self):
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

    def _save_profile(self):
        self.profile_file.write_text(json.dumps(self.profile, indent=2), encoding="utf-8")

    def _update_profile(self, task: str, features: List[str]):
        self.profile["sessions"] += 1
        self.profile["last_interaction"] = datetime.now().isoformat()
        for f in features:
            if f not in self.profile["features_used"]:
                self.profile["features_used"].append(f)
        self._auto_escalate_level()
        self._save_profile()

    def _auto_escalate_level(self):
        used = len(self.profile["features_used"])
        if used >= 15:
            self.profile["user_level"] = "advanced"
        elif used >= 8:
            self.profile["user_level"] = "intermediate"
        else:
            self.profile["user_level"] = "novice"

    def _get_gema_catalog(self) -> str:
        return """== CATALOGO DE GEMAS (22 especialistas) ==

Codigo      | Programacion, refactoring, code review (qwen2.5-coder:7b)
Scholar     | Investigacion, web search, aprendizaje (gemma4:latest)
Arquitecto  | Diseno de sistemas, infraestructura (qwen2.5-coder:7b)
Creative    | Contenido creativo, escritura (qwen2.5-coder:7b)
Sage        | Memoria, persistencia, conocimiento (gemma4:latest)
Analyst     | Analisis de datos, metricas (nemotron-3-nano:4b)
Engineer    | Ingenieria, herramientas (qwen2.5-coder:7b)
Debugger    | Debugging, errores, troubleshooting (qwen2.5-coder:7b)
Optimizer   | Performance, tuning (qwen2.5-coder:7b)
Tester      | Testing, QA, validacion (qwen2.5-coder:7b)
Security    | Seguridad, compliance (gemma4:latest)
DevOps      | Deploy, infraestructura (qwen2.5-coder:7b)
Trainer     | Entrenamiento, educacion (qwen2.5-coder:7b)
Biblioteca  | Organizacion de conocimiento (gemma4:latest)
Vision      | Screenshot, control de PC (qwen2.5vl:7b)
OpenCode    | Agente CLI, ejecucion de codigo (qwen2.5-coder:7b)
Codex       | Delegacion a Codex CLI (qwen2.5-coder:7b)
Design      | UI/UX, multimedia, video (qwen2.5-coder:7b)
Music       | Audio, voz, TTS/STT (qwen2.5-coder:7b)
Prompter    | Optimizacion de prompts y tokens (qwen2.5-coder:7b)
Producer    | Automatizacion, scheduling (qwen2.5-coder:7b)
Ayuda       | Guia del sistema, onboarding (gemma4:latest) <- YO"""

    def _get_system_capabilities(self) -> str:
        return """== CAPACIDADES DEL SISTEMA ==

INFRAESTRUCTURA:
- 22 gemas especializadas con modelos Ollama locales
- DirectorNexus: orquestador con routing semantico
- Harness Engineering: hooks, compaction, memoria, skills
- Training Pipeline: SFT, DPO, datasets locales
- RAG Engine: busqueda semantica con nomic-embed-text
- MCP Bridge: 40+ tools via modelo de contexto
- NexusHive: comunicacion entre agentes (message board)
- GemaHost: ejecucion aislada de gemas en procesos separados

VOZ Y MULTIMEDIA:
- JARVIS: interfaz de voz PTT + VAD
- TTS: Piper local + Windows SAPI fallback
- STT: faster-whisper (local)
- Vision: qwen2.5vl + pytesseract OCR
- Music: generacion de audio
- Design: UI/UX, video, scenes

ENTORNO LOCAL:
- Todo Ollama local, sin API keys externas
- GPU: RTX 3060 12GB (CUDA)
- Procesos ocultos (CREATE_NO_WINDOW)
- Docker: Agent Zero, Redis, n8n
- Memoria compartida: nexus_memory.db (FTS5)
- Skills catalog: 1632 skills indexados

AUTONOMIA:
- Autonomous loops: Zero, Aider, Hermes, JARVIS, Qwen
- Sprint contract con takeover tras 3 errores
- Progressive skill loading
- Context compaction 4-layer
- Session context recovery"""

    def _get_extension_guide(self) -> str:
        return """== COMO EXTENDER NEXUS ==

CREAR UNA NUEVA GEMA:
1. Crear manifest en data/gemas/tugema.json (ver data/gemas/ayuda.json como ejemplo)
2. Crear implementacion en src/agents/tugema_gem.py
3. Registrar en director.py (metodo _load_gemas)
4. Agregar system prompt en ai_tools.py
5. Agregar tool mapping en ai_tools.py (gem_to_tool)

ANADIR UN NUEVO TOOL MCP:
1. Definir funcion en src/bridges/mcp_bridge_server.py
2. Anadir al dict de tools
3. Documentar con schema JSON

CREAR UN NUEVO SKILL:
1. Crear directorio en src/skills/tu-skill/
2. Escribir SKILL.md con instrucciones
3. Escanear con load_skill

MODIFICAR EL UI:
- Frontend: ui/src/components/ (React + Tailwind + Zustand)
- Backend: src/api/server.py (aiohttp)
- Nuevo panel: crear en ui/src/components/panels/ + agregar a sidebar + appStore

CONECTAR NUEVO NODO:
- Agregar a NexusHive via configuracion
- Implementar protocolo message_board con target=nombre-nodo"""

    async def get_profile(self) -> Dict:
        """Retorna el perfil actual del usuario"""
        return self.profile

    async def reset_profile(self) -> Dict:
        """Resetea el perfil a valores iniciales"""
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

    async def analyze_intent(self, task: str) -> Dict:
        """
        Analiza la intencion del usuario y sugiere opciones.
        Detecta si la tarea es una pregunta de ayuda o una accion directa.
        """
        task_lower = task.lower()
        help_keywords = ["ayuda", "help", "que puedes", "como funciona", "capacidades",
                        "que sabes", "tutorial", "guia", "onboarding", "empezar",
                        "nuevo", "aprender", "explica", "que hace", "que puedo"]

        is_help_request = any(k in task_lower for k in help_keywords)
        features_mentioned = []
        for gema_name in ["code", "scholar", "architect", "creative", "sage",
                         "analyst", "engineer", "debugger", "optimizer", "tester",
                         "security", "devops", "trainer", "biblioteca", "vision",
                         "opencode", "codex", "design", "music", "prompter", "producer"]:
            if gema_name in task_lower:
                features_mentioned.append(gema_name)

        self._update_profile(task, features_mentioned)

        return {
            "is_help_request": is_help_request,
            "features_mentioned": features_mentioned,
            "user_level": self.profile["user_level"],
            "suggested_depth": self.profile["preferred_depth"],
        }

    async def get_guided_response(self, task: str, context: Optional[Dict] = None) -> str:
        """
        Genera una respuesta guiada segun el nivel del usuario y la tarea.
        Esta funcion se llama desde el sistema prompt cuando el modelo
        necesita estructurar su respuesta de ayuda.
        """
        intent = await self.analyze_intent(task)
        level = intent["user_level"]

        if level == "novice":
            depth_prompt = "Explica en terminos simples, con ejemplos concretos. Asume que el usuario nunca uso Nexus antes."
        elif level == "intermediate":
            depth_prompt = "Explica con detalle tecnico medio. Asume que el usuario conoce los conceptos basicos."
        else:
            depth_prompt = "Explica con profundidad tecnica. Incluye referencias a la implementacion, archivos y configuracion."

        return depth_prompt

    async def execute(self, task: str) -> Dict:
        """
        Metodo principal - analiza la tarea y prepara contexto de ayuda.
        El modelo (gemma4:latest) genera la respuesta final usando el system prompt.
        """
        logger.info(f"AyudaGem executing: {task[:80]}")
        intent = await self.analyze_intent(task)
        profile_info = {
            "level": self.profile["user_level"],
            "features_used": len(self.profile["features_used"]),
            "total_sessions": self.profile["sessions"],
        }

        return {
            "success": True,
            "gema": "AyudaGem",
            "intent": intent,
            "profile": profile_info,
            "user_message": task,
            "timestamp": datetime.now().isoformat(),
        }
