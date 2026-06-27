"""
Gema Ayuda - Guia reactiva completa del sistema SuperNEXUS v2.0

Conoce TODO el sistema: arquitectura, gemas, UI, comandos, flujos de trabajo,
configuracion, troubleshooting y extension. Se adapta al nivel del usuario.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

SYSTEM_KNOWLEDGE = r"""== GUIA COMPLETA DE SUPERNEXUS v2.0 ==

Lee TODO este documento antes de responder. Contiene el conocimiento
completo del sistema para guiar a cualquier usuario.

--- 1. ARQUITECTURA GENERAL ---

SuperNEXUS es un ecosistema local de IA con 4 capas:

Capa 1 - UI Web (React + Tailwind + Zustand)
  - Puerto 3000 (dev) o servido por el backend en /ui/
  - 7 vistas principales: Home, Chat, Editor, Conexiones, Paneles, Settings
  - Sidebar izquierdo con iconos de navegacion
  - RightPanel con avatar ASCII, monitor del sistema y activity log
  - Estado global via Zustand store (appStore.ts)

Capa 2 - API Backend (Python aiohttp)
  - Puerto 9000
  - REST + WebSocket para chat en tiempo real
  - Endpoints principales: /api/chat, /api/gemas, /api/ollama/tags, /api/status
  - WebSocket: /api/ws/chat?token=<token>

Capa 3 - DirectorNexus (Orquestador)
  - 22 gemas especializadas + 1 supervisor
  - Routing semantico: el Director decide que gema ejecuta cada tarea
  - ProviderRegistry: gestiona proveedores (Zen, Ollama, cloud)
  - ToolRegistry: 54+ herramientas disponibles
  - AgentRunner + Orchestrator Multi-Motor

Capa 4 - Infraestructura Local
  - Ollama: modelos locales (qwen2.5-coder, deepseek-r1, gemma4, etc.)
  - GPU: NVIDIA RTX 3060 12GB (CUDA 8.6, Vulkan)
  - Docker: Agent Zero (50080), Redis (6379), n8n (5678)
  - Memoria: SQLite FTS5 + RAG (nomic-embed-text) + SentenceTransformer
  - Cerebro: base de conocimientos persistente

--- 2. LAS 22 GEMAS (Especialistas) ---

Cada gema es un agente especializado con un rol unico.

GEMAS DE CODIGO:
  code      - Programacion, refactoring, code review, depuracion
  engineer  - Ingenieria de herramientas, scripting, builds
  debugger  - Debugging, troubleshooting, analisis de errores
  tester    - Testing, QA, validacion (unit, integracion, e2e)
  optimizer - Performance tuning, optimizacion de codigo
  codex     - Delegacion de codigo a Codex CLI
  opencode  - Agente CLI, scripting, bash, powershell, ejecucion

GEMAS DE CONOCIMIENTO:
  scholar     - Investigacion, web search, aprendizaje profundo
  sage        - Memoria persistente, consolidacion de conocimiento
  biblioteca  - Organizacion, indexacion y clasificacion de datos
  trainer     - Entrenamiento, educacion, tutoriales
  ayuda       - Guia del sistema, onboarding, capacitacion <- YO

GEMAS DE CREATIVIDAD:
  creative  - Contenido creativo, escritura, generacion
  design    - UI/UX, multimedia, video, escenas
  music     - Audio, voz, TTS/STT, composicion

GEMAS DE ANALISIS:
  analyst   - Analisis de datos, metricas, dashboards
  architect - Diseno de sistemas, infraestructura, planificacion
  security  - Seguridad, compliance, auditoria

GEMAS DE INFRAESTRUCTURA:
  devops    - Deployment, CI/CD, Docker, infraestructura
  producer  - Automatizacion, scheduling, cron, backups
  vision    - Screenshot, control de PC, OCR, mouse/teclado

GEMA PRINCIPAL:
  director  - Orquestador y lider (nexus-director-v6)

Como cambiar de gema:
  - En el chat: selector desplegable arriba a la derecha, junto al avatar
  - Por comando: /gema <nombre> o /mode <nombre>
  - Auto: el Director elige la gema segun tu mensaje

--- 3. COMANDOS SLASH ---

Todos los comandos disponibles escribiendo / en el chat:

SISTEMA:
  /help [cmd]     - Muestra ayuda de comandos
  /clear          - Limpia el chat
  /status         - Info del sistema
  /voice [on|off] - Activa/desactiva voz
  /avatar         - Abre el avatar del director

NAVEGACION:
  /gema <nombre>  - Cambia de gema (code, scholar, creative...)
  /mode <nombre>  - Cambia de modo (alias de /gema)
  /think <texto>  - Activa scholar para razonar
  /guide [texto]  - Invoca a la gema Ayuda

UTILIDADES:
  /export         - Exportar conversacion
  /system <cmd>   - Envia comando al backend

Consejos:
  - Escribe / para ver autocomplete
  - Flechas arriba/abajo para navegar sugerencias
  - Tab o Enter para seleccionar, Escape para cerrar

--- 4. NAVEGACION POR LA UI ---

BARRA LATERAL IZQUIERDA (iconos verticales):
  🏠 Home      - Dashboard principal, recursos del sistema, redes
  💬 Chat      - Conversacion con el Director/gemas (vista principal)
  🛠️ Editor    - Editor de archivos + terminal + explorador
  🔗 Conexiones- Estado de MCP servers, peers, nodos remotos
  📋 Paneles   - Acceso a los 20+ paneles especializados
  ⚙️ Settings  - Configuracion de proveedores, gemas, preferencias

RIGHT PANEL (panel derecho,闭合ible):
  - Avatar ASCII del Director (animado segun emocion)
  - Monitor del sistema (CPU, RAM, GPU)
  - Activity log en tiempo real
  - Control de voz (Space para hablar)

PANELES ESPECIALIZADOS (acceso desde Paneles en sidebar):
  - Brain: memoria y conocimiento del sistema
  - Budget: uso de tokens y costos
  - Commands: comandos personalizados del backend
  - Cookbook: recetas y flujos predefinidos
  - Creative: generacion de contenido multimedia
  - DAG: visualizacion de grafos de tareas
  - Doctor: diagnostico del sistema
  - Gallery: galeria de assets generados
  - Guardian: monitoreo de seguridad
  - Hall: colaboracion entre agentes
  - Hive: red de peers NexusHive
  - Monitor: metricas en tiempo real
  - Notes: notas en vivo
  - Projects: gestion de proyectos
  - Recipes: recetas de automatizacion
  - Scheduler: tareas programadas
  - Sessions: historial de sesiones
  - Skills: catalogo de 1632 skills
  - System: informacion del sistema
  - TaskMonitor: monitoreo de tareas activas
  - Team: panel de equipo multi-agente
  - Vault: almacen seguro de secretos

--- 5. COMUNICACION Y VOZ ---

CHAT ESCRITO:
  - Enter envia el mensaje
  - Shift+Enter nueva linea
  - Ctrl+V pega imagenes directamente
  - Adjuntar imagenes con el icono de clip

CHAT POR VOZ:
  - Presiona el icono de micro o mantien Space
  - Habla, suelta para enviar
  - Usa /voice on/off para activar/desactivar
  - Web Speech API (navegador, no requiere backend)

WEBSOCKET:
  - El chat usa WebSocket para respuesta en tiempo real
  - Mensajes tipo: start, token, complete, error, tool_event
  - Los tool_event muestran que esta haciendo el backend
    (ej: "Buscando en la web...", "Analizando codigo...")

--- 6. PROVEEDORES Y MODELOS ---

Actualmente configurados:

ZEN (principal, gratis):
  - deepseek-v4-flash-free: rapido, proposito general
  - nemotron-3-super-free: razonamiento profundo
  - Se conecta via OPENCODE_API_KEY

OLLAMA (local, 11 modelos):
  - deepseek-r1:8b    - Razonamiento (32K contexto)
  - gemma2:9b         - General (8K)
  - gemma4:latest     - Creativo, 128K contexto
  - moondream:latest  - Vision
  - nemotron-3-nano:4b - Analisis rapido
  - nexus-director-v5 - Director legacy
  - nexus-director-v6 - Director actual (16K)
  - nomic-embed-text  - Embeddings para RAG
  - qwen2.5:0.5b      - Tiny para fallback
  - qwen2.5-coder:7b  - Codigo (128K contexto)
  - qwen2.5vl:7b      - Vision, screenshots

Como cambiar de modelo:
  - En Settings > Providers
  - O desde el selector de modelos en el chat

--- 7. MEMORIA Y CONOCIMIENTO ---

Nexus tiene multiples sistemas de memoria:

CEREBRO (conocimiento a largo plazo):
  - Almacena conversaciones, aprendizajes, patrones
  - 140+ conocimientos almacenados
  - Se consolida automaticamente cada 10 minutos
  - Base de datos: cerebro.db

NEXUS MEMORY (FTS5 - busqueda textual):
  - Observaciones: hechos y aprendizajes atomicos
  - Hallazgos: resultados de tareas completadas
  - Busqueda por texto completo
  - Base: nexus_memory.db

VECTOR MEMORY (RAG semantico):
  - Embeddings con nomic-embed-text (Ollama)
  - SentenceTransformer all-MiniLM-L6-v2 (fallback)
  - Busqueda por similitud semantica
  - Memoria hibrida: vector + keyword + entidades

MEMORIA JERARQUICA (3 niveles):
  - Nivel 1: contexto activo (ventana actual)
  - Nivel 2: memoria de trabajo (sesion)
  - Nivel 3: archivo a largo plazo (con olvido progresivo)

--- 8. SISTEMAS AUTONOMOS ---

AGENTES AUTONOMOS (escuchan message board):
  - zero_autonomous_loop.py -> Agent Zero (Docker, puerto 50080)
  - aider_autonomous_loop.py -> Aider CLI
  - hermes_autonomous_loop.py -> Hermes Agent CLI
  - qwen_autonomous_loop.py -> Qwen local

WORKERS PROGRAMADOS (se ejecutan en background):
  - memory_consolidation (cada 10 min)
  - session_cleanup (cada 30 min)
  - token_optimization (cada 15 min)
  - security_scan (cada 5 min)
  - performance_metrics (cada 1 min)
  - context_compaction (cada 20 min)
  - error_pattern_detection (cada 5 min)
  - knowledge_sync (cada 10 min)
  - health_check (cada 30 seg)
  - learning (cada 30 min)
  - skill_audit (cada 1 hora)
  - backup (cada 2 horas)
  - three_loop_improvement (cada 1 hora)
  - training (cada 15 min)
  - peer_learning (cada 30 min)

HARNESS ENGINEERING:
  - Context Compaction: 4 capas (seguridad -> presupuesto -> recorte -> micro)
  - Hooks Engine: 10 fases con pipeline de seguridad de 3 puertas
  - Progressive Skill Loading: escaneo paralelo de manifiestos
  - Sprint Contract: condicion de "done" + takeover tras 3 errores

--- 9. NEXUSHIVE (RED DE AGENTES) ---

Peer          | Ubicacion | Funcion
claude-code   | PC1       | Claude Code (Anthropic)
antigravity   | PC1       | Antigravity (Gemini)

supernexus    | PC1       | Director SuperNEXUS
zero-code     | Docker    | Agent Zero (50080) - coding, sandbox
aider-code    | Local     | Aider - pair programming
hermes-code   | Local     | Hermes Agent - orchestration

Protocolo:
  - message_board.db (SQLite)
  - target=<agent-name>, msg_type=task
  - Respuesta: msg_type=task_done

--- 10. SERVICIOS DOCKER ---

Servicio     | Puerto  | Funcion
Agent Zero   | 50080   | Sandbox Python, coding autonomo
Redis        | 6379    | Cache, colas, pub/sub
n8n          | 5678    | Automatizacion visual de workflows

--- 11. ENTRENAMIENTO (Training Pipeline) ---

  - SFT (Supervised Fine-Tuning) con datasets locales
  - DPO (Direct Preference Optimization)
  - Datasets en data/datasets/
  - Modelos base: Ollama locales
  - Evaluacion con pipeline de 3 niveles (juez)

--- 12. FLUJOS DE TRABAJO COMUNES ---

PARA PROGRAMAR:
  1. Escribe tu tarea de codigo directamente
  2. El Director activara code u opencode segun el caso
  3. O usa /gema code para forzar la gema de codigo
  4. Para debugging: /gema debugger + describe el error

PARA INVESTIGAR:
  1. Describe que necesitas saber
  2. La gema scholar buscara en la web
  3. Para razonamiento profundo: /think <pregunta>

PARA CREAR CONTENIDO:
  1. /gema creative + describe tu idea
  2. Para diseno visual: /gema design
  3. Para audio/musica: /gema music

PARA CONTROLAR EL PC:
  1. /gema vision
  2. Pide: "toma screenshot", "describe la pantalla"
  3. O: "haz clic en X", "escribe Y"

PARA AUTOMATIZAR:
  1. /gema producer
  2. Describe la tarea recurrente
  3. El producer creara un schedule

PARA APRENDER EL SISTEMA (NUEVOS USUARIOS):
  1. Escribe /guide o simplemente "ayuda"
  2. Pregunta: "que puedes hacer", "como empiezo"
  3. Para ver gemas: "que gemas hay", "cuales son las gemas"
  4. Para comandos: escribe / en el chat

--- 13. CONSEJOS DE TROUBLESHOOTING ---

SI EL CHAT NO RESPONDE:
  - Revisa que el servidor este en puerto 9000
  - Revisa el monitor de recursos en RightPanel
  - Espera a que termine la tarea anterior

SI UN MODELO NO APARECE:
  - Los modelos Ollama se detectan del disco (11 modelos)
  - Si falta alguno: ollama pull <nombre>
  - La UI se actualiza automaticamente

SI LA UI NO CARGA:
  - El backend sirve el UI compilado en ui/dist/
  - Para desarrollo: npm run dev en ui/ (puerto 3000)
  - El backend proxy al 3000 si esta en dev

ERRORES COMUNES:
  - "Tool not found": la gema no tiene esa herramienta
  - "Provider unavailable": el modelo no esta disponible
  - "Streaming timeout": la respuesta tardo demasiado
  - "Port in use": otro proceso ocupa el puerto

--- 14. EXTENDER NEXUS ---

NUEVA GEMA:
  1. Crea manifest en data/gemas/tugema.json
  2. Implementa en src/agents/tugema_gem.py
  3. Agrega system prompt en ai_tools.py
  4. Registra en el tool mapping

NUEVO MCP TOOL:
  1. Define funcion en src/bridges/mcp_bridge_server.py
  2. Agrega al dict de tools con schema JSON

NUEVO SKILL:
  1. Crea directorio en src/skills/tu-skill/
  2. Escribe SKILL.md con instrucciones
  3. Escanea con load_skill

MODIFICAR UI:
  - Componentes: ui/src/components/ (React + Tailwind)
  - Estado: ui/src/stores/appStore.ts (Zustand)
  - API: ui/src/api/ (conexion con backend)
  - Nuevo panel: crear componente + agregar a sidebar + store
"""


class AyudaGem:
    """
    Gema de ayuda reactiva. Conoce TODO el sistema SuperNEXUS.
    Se adapta al usuario, ensena capacidades, sugiere opciones y guia.
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

    def get_guide_context(self) -> Dict:
        """Retorna TODO el contexto de conocimiento del sistema."""
        return {
            "system_knowledge": SYSTEM_KNOWLEDGE,
            "profile": self.profile,
        }

    async def get_profile(self) -> Dict:
        return self.profile

    async def reset_profile(self) -> Dict:
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
        """Analiza la intencion del usuario y detecta que necesita."""
        task_lower = task.lower()
        help_keywords = ["ayuda", "help", "que puedes", "como funciona", "capacidades",
                        "que sabes", "tutorial", "guia", "onboarding", "empezar",
                        "nuevo", "aprender", "explica", "que hace", "que puedo",
                        "como se usa", "como hago", "que es", "dime"]

        is_help_request = any(k in task_lower for k in help_keywords)

        topic_map = {
            "programar": "code", "codigo": "code", "programming": "code",
            "investigar": "scholar", "research": "scholar", "buscar": "scholar",
            "crear": "creative", "escribir": "creative", "contenido": "creative",
            "memoria": "sage", "recordar": "sage", "aprender": "sage",
            "datos": "analyst", "analisis": "analyst", "metricas": "analyst",
            "debug": "debugger", "error": "debugger", "bug": "debugger",
            "seguridad": "security", "auditar": "security",
            "diseno": "design", "ui": "design", "ux": "design",
            "audio": "music", "voz": "music", "musica": "music",
            "prueba": "tester", "test": "tester", "testing": "tester",
            "automatizar": "producer", "schedule": "producer", "cron": "producer",
            "entrenar": "trainer", "training": "trainer", "ensenar": "trainer",
        }

        features_mentioned = []
        for keyword, gema in topic_map.items():
            if keyword in task_lower:
                features_mentioned.append(gema)

        # Also detect direct gema name mentions
        for gema_name in ["code", "scholar", "architect", "creative", "sage",
                         "analyst", "engineer", "debugger", "optimizer", "tester",
                         "security", "devops", "trainer", "biblioteca", "vision",
                         "opencode", "codex", "design", "music", "prompter", "producer",
                         "ayuda", "director"]:
            if gema_name in task_lower and gema_name not in features_mentioned:
                features_mentioned.append(gema_name)

        self._update_profile(task, features_mentioned)

        return {
            "is_help_request": is_help_request,
            "features_mentioned": list(set(features_mentioned)),
            "user_level": self.profile["user_level"],
            "suggested_depth": self.profile["preferred_depth"],
            "total_sessions": self.profile["sessions"],
            "features_used_count": len(self.profile["features_used"]),
        }

    async def get_guided_response(self, task: str, context: Optional[Dict] = None) -> str:
        """
        Devuelve la instruccion de profundidad para el LLM.
        El LLM genera la respuesta final usando SYSTEM_KNOWLEDGE
        y esta guia de profundidad.
        """
        intent = await self.analyze_intent(task)
        level = intent["user_level"]

        if level == "novice":
            return (
                "RESPONDE COMO GUIA PARA NUEVO USUARIO:\n"
                "- Asume que el usuario NUNCA uso Nexus antes\n"
                "- Explica en terminos simples, con ejemplos concretos\n"
                "- Ofrece 2-3 opciones claras de lo que puede hacer\n"
                "- Pregunta si quiere saber mas sobre algun tema\n"
                "- Recomienda empezar con /guide o escribir 'ayuda'\n"
                "- NO uses jerga tecnica sin explicarla\n"
                "- Si menciona una tarea especifica, guialo paso a paso"
            )
        elif level == "intermediate":
            return (
                "RESPONDE COMO GUIA PARA USUARIO INTERMEDIO:\n"
                "- El usuario conoce los conceptos basicos de Nexus\n"
                "- Explica con detalle tecnico medio\n"
                "- Menciona gemas especificas y comandos slash\n"
                "- Ofrece atajos: /gema, /mode, /think\n"
                "- Sugiere paneles y vistas relevantes\n"
                "- Incluye ejemplos de uso avanzado si aplica"
            )
        else:
            return (
                "RESPONDE COMO GUIA PARA USUARIO AVANZADO:\n"
                "- El usuario conoce el sistema en profundidad\n"
                "- Incluye referencias a implementacion (archivos, config)\n"
                "- Explica pipelines, workers, y arquitectura interna\n"
                "- Ofrece opciones de extension: nuevas gemas, tools, skills\n"
                "- Menciona NexusHive, autonomous loops, training pipeline\n"
                "- Referencia archivos especificos del codigo fuente"
            )

    async def execute(self, task: str) -> Dict:
        """
        Metodo principal. Devuelve contexto completo para que
        el LLM genere la respuesta de ayuda con todo el conocimiento.
        """
        logger.info(f"AyudaGem executing: {task[:80]}")
        intent = await self.analyze_intent(task)
        depth_guide = await self.get_guided_response(task)

        return {
            "success": True,
            "gema": "AyudaGem",
            "intent": intent,
            "profile": {
                "level": self.profile["user_level"],
                "features_used": len(self.profile["features_used"]),
                "total_sessions": self.profile["sessions"],
                "learned_topics": self.profile["learned_topics"],
            },
            "system_knowledge": SYSTEM_KNOWLEDGE,
            "depth_guide": depth_guide,
            "user_message": task,
            "timestamp": datetime.now().isoformat(),
        }

