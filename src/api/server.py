"""
REST API Server - Backend para NEXUS UI en SuperNEXUS v2.0

Servidor HTTP async con aiohttp.
Puerto: 9001 (diferente del NEXUS master en 9000)
"""

import asyncio
import json
import logging
import re
import sys
import os
import base64
import requests
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import aiohttp
from aiohttp import web

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.director import DirectorNexus
from src.core.connectivity import ConnectivityLayer
from src.core.ollama import OllamaClient, LLMRouter
from src.core.event_bus import EventBus
from src.core.communication import CommunicationFlow, AgentCapability
from src.core.runtime import AgentRuntime
from src.core.doctor import Doctor
from src.core.custom_commands import CustomCommandManager
from src.core.acp_protocol import ACPMessage, ACPMessageType
from src.core.skill_marketplace import SkillManifest
from src.memory.neural_patterns import NeuralPatterns
from src.memory.rag_memory import RAGMemory
from src.memory.knowledge_graph import KnowledgeGraph
from src.memory.qa_loop import QALoop
from src.memory.active_learning import ActiveLearningLoop
from src.bridges.pc2_bridge import PC2Bridge
from src.bridges.tailscale_bridge import TailscaleBridge
from src.bridges.mcp_bridge_server import mcp, execute_on_pc2, send_message, read_messages, brain_remember, brain_recall, memory_set, memory_get, nexus_status, list_nodes, execute_remote_task, list_skills, load_skill, send_task_to_antigravity, get_system_info, add_finding, add_decision, read_cloud, check_permissions, router_select, router_stats, self_learning_status, memory_hierarchical_stats, memory_hierarchical_store, memory_hierarchical_search, retrieval_search
from src.core.nexus_hive import NexusHive
from src.agents.scholar_gem import ScholarGem
from src.agents.sage_gem import SageGem
from src.agents.biblioteca_gem import BibliotecaGem

# Modulos portados de NEXUS_MASTER
from src.control.computer_control import ComputerControl
from src.control.pc_controller import PCController
from src.voice.audio_controller import AudioController
from src.voice.nexus_tts import NexusTTS
from src.voice.voice_gem import VoiceGem
from src.voice.vision_handler import VisionHandler
from src.brain.cerebro import Cerebro
from src.integrations.codex_skill import CodexSkill
from src.integrations.rcon_client import RustServerManager
from src.integrations.multimedia_engine import MultimediaEngine
from src.integrations.scheduler import NexusScheduler
from src.integrations.guardian import NexusGuardian
from src.optimization.token_optimizer import TokenOptimizer
from src.optimization.token_reduction import Token90Reduction
from src.optimization.system_optimizer import SystemOptimizer
from src.core.loop_guard import LoopGuard
from src.core.error_envelope import ErrorEnvelope, ErrorCategory, ErrorSeverity, ErrorDecision
from src.core.extension_pipeline import ExtensionPipeline, HookPhase, HookContext
from src.brain.data_collector import DataCollector, DataCollectorConfig
from src.optimization.api_safety import SafetyManager
from src.security.guardrails import NEXUSGuardrails
from src.security.auth import AuthManager
from src.optimization.resource_monitor import get_system_stats, is_safe_to_run_local

logging.basicConfig(level=logging.WARNING, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger("nexus-api")

# Filtrar ruido de logs de acceso (404s de /json)
class AccessLogFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        if 'GET /json' in msg and '404' in msg:
            return False
        return True

logging.getLogger("aiohttp.access").addFilter(AccessLogFilter())

_MAX_JSON_SIZE = 10 * 1024 * 1024  # 10MB
_SANITIZE_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


def _sanitize_str(v: str, max_len: int = 50_000) -> str:
    return _SANITIZE_RE.sub('', v[:max_len])


def _sanitize(obj, depth: int = 0):
    if depth > 20:
        return None
    if isinstance(obj, str):
        return _sanitize_str(obj)
    if isinstance(obj, dict):
        return {_sanitize_str(str(k), 200): _sanitize(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(item, depth + 1) for item in obj[:500]]
    return obj


async def _parse_json(request: web.Request) -> dict:
    if request.content_length and request.content_length > _MAX_JSON_SIZE:
        raise web.HTTPRequestEntityTooLarge(max_size=_MAX_JSON_SIZE, actual_size=request.content_length)
    try:
        raw = await request.json()
    except Exception:
        raise web.HTTPBadRequest(text='{"error":"Invalid JSON"}', content_type="application/json")
    if not isinstance(raw, dict):
        raise web.HTTPBadRequest(text='{"error":"Expected JSON object"}', content_type="application/json")
    return _sanitize(raw)


class SuperNEXUSBackend:
    """Backend completo de SuperNEXUS"""

    def __init__(self):
        self.director = DirectorNexus(project="default")
        self._last_msg_id = 0
        self._busy = False

        self._init_core()
        self._init_memory()
        self._init_agents()
        self._init_voice()
        self._init_integrations()
        self._init_optimization()
        self._jarvis_process = None

    # ── Init groups ──────────────────────────────────────────────

    def _init_core(self):
        self.connectivity = ConnectivityLayer()
        self.ollama = OllamaClient()
        self.llm_router = LLMRouter(self.ollama)
        self.event_bus = EventBus()
        self.comm_flow = CommunicationFlow(self.event_bus)
        self.runtime = AgentRuntime(self.event_bus)
        self.pc2 = self._safe_init("PC2Bridge", PC2Bridge)
        self.tailscale = self._safe_init("TailscaleBridge", TailscaleBridge)
        self.nexus_hive = self._safe_init("NexusHive", NexusHive)
        self.mcp_tools = {
            "execute_on_pc2": execute_on_pc2,
            "send_message": send_message,
            "read_messages": read_messages,
            "brain_remember": brain_remember,
            "brain_recall": brain_recall,
            "memory_set": memory_set,
            "memory_get": memory_get,
            "nexus_status": nexus_status,
            "list_nodes": list_nodes,
            "execute_remote_task": execute_remote_task,
            "list_skills": list_skills,
            "load_skill": load_skill,
            "send_task_to_antigravity": send_task_to_antigravity,
            "get_system_info": get_system_info,
            "add_finding": add_finding,
            "add_decision": add_decision,
            "read_cloud": read_cloud,
            "check_permissions": check_permissions,
            "router_select": router_select,
            "router_stats": router_stats,
            "self_learning_status": self_learning_status,
            "memory_hierarchical_stats": memory_hierarchical_stats,
            "memory_hierarchical_store": memory_hierarchical_store,
            "memory_hierarchical_search": memory_hierarchical_search,
            "retrieval_search": retrieval_search,
        }

    def _init_memory(self):
        self.neural = self._safe_init("NeuralPatterns", NeuralPatterns)
        self.rag = self._safe_init("RAGMemory", RAGMemory)
        self.kg = self._safe_init("KnowledgeGraph", KnowledgeGraph)
        self.qa = self._safe_init("QALoop", QALoop)
        self.learning = self._safe_init("ActiveLearningLoop", ActiveLearningLoop)
        self.cerebro = self._safe_init("Cerebro", Cerebro)

    def _init_agents(self):
        self.scholar = self._safe_init("ScholarGem", ScholarGem)
        self.sage = self._safe_init("SageGem", SageGem)
        self.biblioteca = self._safe_init("BibliotecaGem", BibliotecaGem)

    def _init_voice(self):
        self.audio = self._safe_init("AudioController", AudioController)
        self.tts = self._safe_init("NexusTTS", lambda: NexusTTS(motor="piper", voice="davefx-medium"))
        self.vision = self._safe_init("VisionHandler", VisionHandler)
        self.voice_gem = self._safe_init("VoiceGem", VoiceGem)
        try:
            from src.voice.personality_system import PersonalityManager, InteractionRouter
            self.personality_manager = self._safe_init("PersonalityManager", PersonalityManager)
            self.interaction_router = self._safe_init("InteractionRouter", InteractionRouter)
        except ImportError:
            logger.warning("Personality system not available")
            self.personality_manager = None
            self.interaction_router = None

    def _init_integrations(self):
        self.pc_control = self._safe_init("ComputerControl", ComputerControl)
        self.pc_controller = self._safe_init("PCController", PCController)
        self.codex = self._safe_init("CodexSkill", CodexSkill)
        self.rcon_manager = self._safe_init("RustServerManager", RustServerManager)
        self.multimedia = self._safe_init("MultimediaEngine", MultimediaEngine)
        self.scheduler = self._safe_init("NexusScheduler", NexusScheduler)
        self.guardian = self._safe_init("NexusGuardian", NexusGuardian)
        self.extension_pipeline = self._safe_init("ExtensionPipeline", ExtensionPipeline)
        self.doctor = self._safe_init("Doctor", Doctor)
        self.custom_commands = self._safe_init("CustomCommandManager", CustomCommandManager)

    def _init_optimization(self):
        self.token_optimizer = self._safe_init("TokenOptimizer", TokenOptimizer)
        self.token_reduction = self._safe_init("Token90Reduction", Token90Reduction)
        self.system_optimizer = self._safe_init("SystemOptimizer", SystemOptimizer)
        self.guardrails = self._safe_init("NEXUSGuardrails", lambda: NEXUSGuardrails(strict_mode=False, require_confirmation=True))
        self.safety = self._safe_init("SafetyManager", SafetyManager)
        self.loop_guard = self._safe_init("LoopGuard", lambda: LoopGuard(max_history=50, exact_threshold=3, semantic_threshold=0.8))
        self.data_collector = self._safe_init("DataCollector", lambda: DataCollector(config=DataCollectorConfig()))

    def _safe_init(self, name, factory):
        """Inicializa un modulo con manejo de errores — loguea traceback completo"""
        try:
            return factory()
        except Exception as e:
            logger.error(f"Failed to initialize {name}: {e}", exc_info=True)
            return None

    async def initialize(self):
        logger.info("Initializing SuperNEXUS backend...")

        if self.audio:
            await self.audio.initialize()

        if self.scholar:
            self.comm_flow.register_agent("scholar", AgentCapability(
                name="scholar", description="Research", tags=["research"], can_handle=["research", "web"]
            ), self._handle_scholar)

        if self.sage:
            self.comm_flow.register_agent("sage", AgentCapability(
                name="sage", description="Memory", tags=["memory"], can_handle=["memory", "persist"]
            ), self._handle_sage)

        if self.biblioteca:
            self.comm_flow.register_agent("biblioteca", AgentCapability(
                name="biblioteca", description="Organization", tags=["organization"], can_handle=["organize", "index"]
            ), self._handle_biblioteca)

        asyncio.create_task(self._deferred_pc2_connect())
        asyncio.create_task(self._deferred_hive_connect())

        # Wire up background review daemon
        if self.director and hasattr(self.director, 'review_daemon'):
            self.director.review_daemon.director = self.director
            self.director.review_daemon.cerebro = self.cerebro
            self.director.review_daemon.vault = self.director.vault

        # Wire up ExtensionPipeline to GemaHost
        if self.director and hasattr(self.director, 'gema_host') and self.extension_pipeline:
            self.director.gema_host.extension_pipeline = self.extension_pipeline

        # Start Actor System (Sprint 2)
        if hasattr(self.director, 'actor_system'):
            await self.director.actor_system.start_all()

        try:
            from src.improvements.integration import integrate_all_improvements
            integrate_all_improvements(self)
        except Exception as e:
            logger.warning(f"Improvements integration failed (non-critical): {e}")

        # Initialize Self-Model Engine (Phase 1: Auto-discovery)
        if self.director and hasattr(self.director, 'self_model'):
            asyncio.create_task(self._deferred_self_model_init())

        asyncio.create_task(self._message_poller())
        logger.info("SuperNEXUS backend initialized")

    async def _deferred_self_model_init(self):
        """Initialize self-model in background (non-blocking)"""
        try:
            await self.director.initialize_self_model()
        except Exception as e:
            logger.warning(f"Self-model initialization failed: {e}")

    async def _deferred_pc2_connect(self):
        if not self.pc2:
            return
        try:
            await self.pc2.connect()
        except Exception as e:
            logger.debug(f"PC2 deferred connect: {e}")

    async def _deferred_hive_connect(self):
        """Inicia NexusHive y registra handlers por defecto"""
        if not self.nexus_hive:
            return
        try:
            await self.nexus_hive.start()
            
            # Registrar handlers por defecto
            self.nexus_hive.register_handler("get_status", self._hive_get_status)
            self.nexus_hive.register_handler("execute_command", self._hive_execute_command)
            self.nexus_hive.register_handler("get_system_info", self._hive_get_system_info)
            
            logger.info("NexusHive started with default handlers")
        except Exception as e:
            logger.debug(f"NexusHive deferred connect: {e}")

    async def _hive_get_status(self, **kwargs):
        """Handler para obtener estado del sistema"""
        return await self.get_status()

    async def _hive_execute_command(self, command: str = "", **kwargs):
        """Handler para ejecutar comando"""
        if not command:
            return {"status": "error", "error": "No command provided"}
        if not self.pc2:
            return {"status": "error", "error": "PC2 bridge not available"}
        return await self.pc2.execute_remote(command)

    async def _hive_get_system_info(self, **kwargs):
        """Handler para obtener información del sistema"""
        if not self.pc2:
            return {"status": "error", "error": "PC2 bridge not available"}
        return await self.pc2.get_system_info()

    async def _handle_scholar(self, message):
        if not self.scholar:
            return {"status": "error", "error": "Scholar gem not available"}
        return await self.scholar.research(message.content, max_sources=3)

    async def _handle_sage(self, message):
        if not self.sage:
            return {"status": "error", "error": "Sage gem not available"}
        return await self.sage.analyze_and_persist(message.content, "comm_flow", "general")

    async def _handle_biblioteca(self, message):
        if not self.biblioteca:
            return {"status": "error", "error": "Biblioteca gem not available"}
        return await self.biblioteca.organize(message.content[:80], message.content, "General")

    async def _message_poller(self):
        """Loop cada 30s que lee mensajes y procesa tareas si está libre."""
        import json
        logger.info("📡 Starting message poller background task...")
        # Get the initial highest msg id so we don't process old messages on startup
        try:
            msgs_str = await read_messages(channel="general", limit=1)
            msgs_data = json.loads(msgs_str)
            messages = msgs_data.get("messages", [])
            if messages:
                self._last_msg_id = max(self._last_msg_id, int(messages[0]["id"]))
                logger.info(f"📡 Initialized _last_msg_id to {self._last_msg_id}")
        except Exception as e:
            logger.warning(f"Error during initial message fetch: {e}")

        while True:
            try:
                await asyncio.sleep(30)
                if self._busy:
                    continue

                # Read messages
                msgs_str = await read_messages(channel="general", limit=20)
                msgs_data = json.loads(msgs_str)
                messages = msgs_data.get("messages", [])

                for msg in messages:
                    msg_id = int(msg["id"])
                    if msg_id <= self._last_msg_id:
                        continue

                    self._last_msg_id = max(self._last_msg_id, msg_id)

                    # Condition: Target is director, supernexus, or * with type = task
                    target = str(msg.get("target", "")).lower()
                    msg_type = str(msg.get("type", "")).lower()

                    if (target in ["director", "supernexus", "*"]) and (msg_type == "task"):
                        # Process this message
                        asyncio.create_task(self._process_incoming_task(msg))

            except asyncio.CancelledError:
                logger.info("📡 Message poller background task cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in _message_poller: {e}")

    async def _process_incoming_task(self, msg: Dict):
        """Ejecuta la tarea recibida vía director.execute() y responde al sender."""
        import json
        self._busy = True
        sender = msg.get("sender", "unknown")
        content = msg.get("content", "")
        msg_id = msg.get("id")
        
        logger.info(f"📥 [POLLER] Processing incoming task #{msg_id} from '{sender}': '{content[:100]}'")
        
        try:
            if not self.director:
                raise ValueError("DirectorNexus is not initialized in the backend.")

            # Execute via ai_tools directly (faster than gema subprocess for poller tasks)
            result = await asyncio.wait_for(
                self.director.ai_tools.quick_response(task=content, gem="director", context="Responde de forma concisa."),
                timeout=120.0,
            )
            
            # Formulate response content
            response_content = result if isinstance(result, str) else result.get("content", result.get("reply", str(result)))
            
            # Send message response back to the sender
            logger.info(f"📤 [POLLER] Sending response back to '{sender}'")
            await send_message(
                content=response_content,
                sender="supernexus",
                target=sender,
                channel="general",
                msg_type="chat"
            )
            
        except Exception as e:
            logger.error(f"❌ [POLLER] Error processing task #{msg_id}: {e}")
            try:
                await send_message(
                    content=f"Error al procesar la tarea: {e}",
                    sender="supernexus",
                    target=sender,
                    channel="general",
                    msg_type="chat"
                )
            except Exception as send_err:
                logger.error(f"❌ [POLLER] Failed to send error response: {send_err}")
        finally:
            self._busy = False

    async def process_message(
        self,
        message: str,
        gem: str = "auto",
        project: str = "default",
        voice: bool = False,
        images: Optional[List[str]] = None,
        files: Optional[List[Dict]] = None,
    ) -> Dict:
        if project != self.director.current_project:
            await self.director.change_project(project)

        # Guardrails: Validar input del usuario
        if self.guardrails:
            input_check = self.guardrails.validate_input(message)
            if input_check["blocked"]:
                logger.warning(f"Input bloqueado: {input_check['reasons']}")
                return {
                    "reply": "NEXUS ha bloqueado esta solicitud por motivos de seguridad.",
                    "security": input_check,
                    "success": False,
                }

        # LoopGuard: Detectar loops potenciales
        if self.loop_guard:
            loop_detection = self.loop_guard.check("user_input", {"message": message})
            if loop_detection and loop_detection.is_loop:
                logger.warning(f"Loop detected: {loop_detection.loop_type} (similarity: {loop_detection.similarity})")
                return {
                    "reply": f"NEXUS ha detectado un patrón repetitivo. {loop_detection.suggestion}",
                    "loop_detected": True,
                    "loop_type": loop_detection.loop_type,
                    "success": False,
                }

        # ExtensionPipeline: Hook on_input
        if self.extension_pipeline:
            hook_ctx = HookContext(phase=HookPhase.ON_INPUT, gem_id="system", data=message)
            hook_ctx = self.extension_pipeline.execute_phase(HookPhase.ON_INPUT, hook_ctx.data, {"gem_id": "system"})
            if hook_ctx.should_abort:
                return {"reply": hook_ctx.abort_reason, "success": False}
            message = hook_ctx.data

        # Detectar si hay imágenes para usar modelo de visión
        has_images = images and len(images) > 0
        if has_images:
            logger.info(f"Processing {len(images)} image(s) with vision model")
            # Procesar imagenes con VisionHandler
            if self.vision:
                for img_path in images:
                    if os.path.exists(img_path):
                        # Codificar imagen para el modelo vision
                        base64_data = self.vision.encode_image_base64(img_path)
                        message = self.vision.format_message_with_image(base64_data, message)
                        logger.info(f"Imagen agregada al mensaje: {img_path}")

        classification = await self.director.classify_task(message)
        if gem != "auto":
            classification.selected_gems = [gem]
        elif has_images:
            # Si hay imágenes, forzar gem de visión
            classification.selected_gems = ["vision"]

        # Cerebro: Aprender de la interaccion
        primary_gem = classification.selected_gems[0] if classification.selected_gems else "auto"
        if self.cerebro:
            await self.cerebro.aprender_interaccion(message, "", primary_gem)
            await self.cerebro.aprender_herramienta(primary_gem)

        # Computer Control: Detectar acciones de PC
        pc_action = None
        if any(kw in message.lower() for kw in ["screenshot", "captura", "click", "mouse", "teclado", "abrir", "lanzar", "escribir"]):
            pc_action = await self._handle_pc_action(message)

        # Auto tool calling: Detectar intenciones de archivos y ejecutar herramientas automaticamente
        auto_tool_result = None
        try:
            msg_lower = message.lower()
            logger.info(f"Auto tool checking: {msg_lower[:100]}")
            
            # Detectar intencion de find files (con .gitignore) - ANTES que glob para evitar shadowing
            if any(kw in msg_lower for kw in ["donde esta el archivo", "encuentra archivo", "buscar archivo por nombre", "locate file", "find file by name"]):
                logger.info("Detected find_files intent")
                pattern_match = re.search(r'["\']([^"\']+\*\w+)["\']', msg_lower)
                if not pattern_match:
                    pattern_match = re.search(r'["\']?([^"\']+\.\w+)["\']?', msg_lower)
                pattern = pattern_match.group(1) if pattern_match else "*.*"
                path_match = re.search(r'(?:en|de|del)\s+["\']?([^"\']+)["\']?', msg_lower)
                path = path_match.group(1) if path_match else ""
                auto_tool_result = await self.director.ai_tools.execute_tool_call("find_files", {"pattern": pattern, "path": path})
            
            # Detectar intencion de buscar archivos por patron (glob)
            elif any(kw in msg_lower for kw in ["busca archivos", "glob", "patron de archivo", "files matching pattern"]):
                logger.info("Detected glob_files intent")
                pattern_match = re.search(r'["\']([^"\']+\*\w+)["\']', msg_lower)
                if not pattern_match:
                    pattern_match = re.search(r'(\S+\.\w+)', msg_lower)
                pattern = pattern_match.group(1) if pattern_match else "*.*"
                path_match = re.search(r'(?:en|de|del)\s+["\']?([^"\']+)["\']?', msg_lower)
                path = path_match.group(1) if path_match else ""
                auto_tool_result = await self.director.ai_tools.execute_tool_call("glob_files", {"pattern": pattern, "path": path})
            
            # Detectar intencion de buscar contenido
            elif any(kw in msg_lower for kw in ["busca en", "buscar en", "grep", "donde dice", "donde esta", "donde está"]):
                logger.info("Detected grep_content intent")
                pattern_match = re.search(r'["\']([^"\']+)["\']', msg_lower)
                if not pattern_match:
                    pattern_match = re.search(r'(?:buscar|busca|dice|esta|está)\s+(?:en\s+\S+\s+)?["\']?([^"\']+)["\']?', msg_lower)
                pattern = pattern_match.group(1) if pattern_match else ""
                path_match = re.search(r'(?:en|de|del)\s+["\']?([^"\']+)["\']?', msg_lower)
                path = path_match.group(1) if path_match else ""
                auto_tool_result = await self.director.ai_tools.execute_tool_call("grep_content", {"pattern": pattern, "path": path})
            
            # Detectar intencion de editar archivo
            elif any(kw in msg_lower for kw in ["edita", "editar", "edit", "reemplaza", "reemplazar", "cambia en el archivo", "modifica"]):
                logger.info("Detected edit_file intent")
                path_match = re.search(r'(?:el|la|en)?\s*["\']?([^"\']+\.\w+)["\']?', msg_lower)
                path = path_match.group(1) if path_match else ""
                if path:
                    old_match = re.search(r'(?:reemplaza|cambia|old)[:\s]+["\'](.+?)["\']', msg_lower)
                    new_match = re.search(r'(?:por|con|new)[:\s]+["\'](.+?)["\']', msg_lower)
                    old_string = old_match.group(1) if old_match else ""
                    new_string = new_match.group(1) if new_match else ""
                    if old_string or new_string:
                        auto_tool_result = await self.director.ai_tools.execute_tool_call("edit_file", {"path": path, "old_string": old_string, "new_string": new_string})
            
            # Detectar intencion de ver archivo
            elif any(kw in msg_lower for kw in ["ver archivo", "view file", "muestra el archivo", "lee el archivo"]):
                logger.info("Detected view_file intent")
                path_match = re.search(r'["\']?([^"\']+\.\w+)["\']?', msg_lower)
                path = path_match.group(1) if path_match else ""
                if path:
                    auto_tool_result = await self.director.ai_tools.execute_tool_call("view_file", {"path": path})
            
            # Detectar intencion de git status
            elif any(kw in msg_lower for kw in ["git status", "estado git", "estado del repo", "cambios sin commit"]):
                logger.info("Detected git_status intent")
                path_match = re.search(r'(?:en|de|del)\s+["\']?([^"\']+)["\']?', msg_lower)
                path = path_match.group(1) if path_match else ""
                auto_tool_result = await self.director.ai_tools.execute_tool_call("git_status", {"path": path})
            
            # Detectar intencion de git diff
            elif any(kw in msg_lower for kw in ["git diff", "diferencias git", "cambios staged"]):
                logger.info("Detected git_diff intent")
                path_match = re.search(r'(?:en|de|del)\s+["\']?([^"\']+)["\']?', msg_lower)
                path = path_match.group(1) if path_match else ""
                staged = "staged" in msg_lower
                auto_tool_result = await self.director.ai_tools.execute_tool_call("git_diff", {"path": path, "staged": staged})
            
            # Detectar intencion de git log
            elif any(kw in msg_lower for kw in ["git log", "historial de commits", "commits recientes"]):
                logger.info("Detected git_log intent")
                path_match = re.search(r'(?:en|de|del)\s+["\']?([^"\']+)["\']?', msg_lower)
                path = path_match.group(1) if path_match else ""
                auto_tool_result = await self.director.ai_tools.execute_tool_call("git_log", {"path": path, "limit": 10})
            
            # Detectar intencion de crear terminal
            elif any(kw in msg_lower for kw in ["crear terminal", "abrir terminal", "terminal session"]):
                logger.info("Detected terminal_create intent")
                name_match = re.search(r'["\']([^"\']+)["\']', msg_lower)
                name = name_match.group(1) if name_match else ""
                auto_tool_result = await self.director.ai_tools.execute_tool_call("terminal_create", {"name": name})
            
            # Detectar intencion de enviar a terminal
            elif any(kw in msg_lower for kw in ["envia a terminal", "ejecuta en terminal", "terminal send"]):
                logger.info("Detected terminal_send intent")
                session_match = re.search(r'session["\s]+["\']?([^"\']+)["\']?', msg_lower)
                session_id = session_match.group(1) if session_match else ""
                text_match = re.search(r'["\']([^"\']+)["\']', msg_lower)
                text = text_match.group(1) if text_match else ""
                auto_tool_result = await self.director.ai_tools.execute_tool_call("terminal_send", {"session_id": session_id, "text": text})
            
            # Detectar intencion de diagnosticos
            elif any(kw in msg_lower for kw in ["diagnosticos", "errores en", "lsp", "analiza archivo"]):
                logger.info("Detected lsp_diagnostics intent")
                path_match = re.search(r'["\']?([^"\']+\.\w+)["\']?', msg_lower)
                path = path_match.group(1) if path_match else ""
                auto_tool_result = await self.director.ai_tools.execute_tool_call("lsp_diagnostics", {"path": path})
            
            # Detectar intencion de web fetch
            elif any(kw in msg_lower for kw in ["fetch url", "obten url", "descarga pagina", "web fetch", "trae contenido de"]):
                logger.info("Detected web_fetch intent")
                url_match = re.search(r'(https?://[^\s"\']+)', msg_lower)
                url = url_match.group(1) if url_match else ""
                if url:
                    auto_tool_result = await self.director.ai_tools.execute_tool_call("web_fetch", {"url": url})
            
            # Detectar intencion de code search
            elif any(kw in msg_lower for kw in ["busca codigo", "code search", "donde esta la funcion", "donde esta la clase"]):
                logger.info("Detected code_search intent")
                query_match = re.search(r'["\']([^"\']+)["\']', msg_lower)
                query = query_match.group(1) if query_match else ""
                path_match = re.search(r'(?:en|de|del)\s+["\']?([^"\']+)["\']?', msg_lower)
                path = path_match.group(1) if path_match else ""
                if query:
                    auto_tool_result = await self.director.ai_tools.execute_tool_call("code_search", {"query": query, "path": path})
            
            # Detectar intencion de git blame
            elif any(kw in msg_lower for kw in ["git blame", "quien hizo", "quien modifico", "blame"]):
                logger.info("Detected git_blame intent")
                path_match = re.search(r'(?:en|de|del)\s+["\']?([^"\']+)["\']?', msg_lower)
                path = path_match.group(1) if path_match else ""
                file_match = re.search(r'["\']?([^"\']+\.\w+)["\']?', msg_lower)
                file_path = file_match.group(1) if file_match else ""
                auto_tool_result = await self.director.ai_tools.execute_tool_call("git_blame", {"path": path, "file": file_path})
            
            # Detectar intencion de lsp symbols
            elif any(kw in msg_lower for kw in ["simbolos", "funciones en", "clases en", "lsp symbols"]):
                logger.info("Detected lsp_symbols intent")
                path_match = re.search(r'["\']?([^"\']+\.\w+)["\']?', msg_lower)
                path = path_match.group(1) if path_match else ""
                auto_tool_result = await self.director.ai_tools.execute_tool_call("lsp_symbols", {"path": path})
            
            # Detectar intencion de find files (con .gitignore)
            elif any(kw in msg_lower for kw in ["donde esta el archivo", "encuentra archivo", "buscar archivo por nombre"]):
                logger.info("Detected find_files intent")
                pattern_match = re.search(r'["\']([^"\']+\*\w+)["\']', msg_lower)
                if not pattern_match:
                    pattern_match = re.search(r'["\']?([^"\']+\.\w+)["\']?', msg_lower)
                pattern = pattern_match.group(1) if pattern_match else "*.*"
                path_match = re.search(r'(?:en|de|del)\s+["\']?([^"\']+)["\']?', msg_lower)
                path = path_match.group(1) if path_match else ""
                auto_tool_result = await self.director.ai_tools.execute_tool_call("find_files", {"pattern": pattern, "path": path})
            
            # Detectar intencion de git commit
            elif any(kw in msg_lower for kw in ["git commit", "crear commit", "commitea", "haz commit"]):
                logger.info("Detected git_commit intent")
                path_match = re.search(r'(?:en|de|del)\s+["\']?([^"\']+)["\']?', msg_lower)
                path = path_match.group(1) if path_match else ""
                msg_match = re.search(r'["\']([^"\']+)["\']', msg_lower)
                commit_msg_text = msg_match.group(1) if msg_match else "Auto-commit by DirectorNexus"
                auto_tool_result = await self.director.ai_tools.execute_tool_call("git_commit", {"path": path, "message": commit_msg_text})
            
            # Detectar intencion de listar directorio
            elif any(kw in msg_lower for kw in ["lista", "listar", "list", "ls ", "archivos del directorio", "contenido de", "que hay en"]):
                logger.info("Detected list_dir intent")
                path_match = re.search(r'(?:en|de|del)\s+["\']?([^"\']+)["\']?', msg_lower)
                path = path_match.group(1) if path_match else ""
                logger.info(f"List dir path: '{path}'")
                auto_tool_result = await self.director.ai_tools.execute_tool_call("list_dir", {"path": path, "recursive": False})
            
            # Detectar intencion de leer archivo
            elif any(kw in msg_lower for kw in ["lee", "leer", "read", "abre", "abrir", "muestra", "mostrar", "ver", "contenido de"]):
                logger.info("Detected read_file intent")
                path_match = re.search(r'(?:el|la|los|las)?\s*["\']?([^"\']+\.\w+)["\']?', msg_lower)
                path = path_match.group(1) if path_match else ""
                if path:
                    auto_tool_result = await self.director.ai_tools.execute_tool_call("read_file", {"path": path})
            
            # Detectar intencion de escribir archivo
            elif any(kw in msg_lower for kw in ["escribe", "escribir", "write", "crea", "crear", "guarda", "guardar"]):
                logger.info("Detected write_file intent")
                path_match = re.search(r'(?:en|a|el|la)?\s*["\']?([^"\']+\.\w+)["\']?', msg_lower)
                path = path_match.group(1) if path_match else ""
                if path:
                    content_match = re.search(r'(?:con|el|la)?\s*(?:contenido|texto)?[:\s]+["\']?([^"\']+)["\']?', msg_lower)
                    content = content_match.group(1) if content_match else message
                    auto_tool_result = await self.director.ai_tools.execute_tool_call("write_file", {"path": path, "content": content})
            
            # Detectar intencion de ejecutar comando
            elif any(kw in msg_lower for kw in ["ejecuta", "ejecutar", "run", "comando", "terminal", "cmd"]):
                logger.info("Detected execute_command intent")
                cmd_match = re.search(r'(?:el|la)?\s*(?:comando)?[:\s]+["\']?([^"\']+)["\']?', msg_lower)
                cmd = cmd_match.group(1) if cmd_match else message
                
                # RCE Protection: Check command safety using SafetyManager
                is_safe, reason = self.safety.check_command_safety(cmd)
                if not is_safe:
                    logger.warning(f"RCE Prevention triggered: Blocked command '{cmd}' - Reason: {reason}")
                    # Log suspicious event to neural memory database
                    try:
                        import sqlite3
                        db_path = os.getenv("NEXUS_DB_PATH", str(Path(__file__).resolve().parents[2] / "memory" / "nexus_memory.db"))
                        conn = sqlite3.connect(db_path)
                        c = conn.cursor()
                        c.execute(
                            "INSERT INTO observations (ts, category, content) VALUES (?, ?, ?)",
                            (datetime.now().isoformat(), "security_alert", f"Blocked suspicious command execution: '{cmd}'. Reason: {reason}")
                        )
                        conn.commit()
                        conn.close()
                    except Exception as db_err:
                        logger.error(f"Failed to log security observation to DB: {db_err}")
                        
                    auto_tool_result = {"success": False, "error": f"Security Block: {reason}"}
                else:
                    auto_tool_result = await self.director.ai_tools.execute_tool_call("execute_command", {"command": cmd})
        except Exception as e:
            logger.warning(f"Auto tool calling error: {e}")
            auto_tool_result = None

        # Ejecutar siempre a traves del Director (no quick_response directo al LLM)
        try:
            result = await self.director.execute(message, gem=gem)
            reply = result.data.get("content", str(result.data)) if result.data else "Task executed"

            # Guardrails: Validar output
            if self.guardrails:
                output_check = self.guardrails.validate_output(reply)
                if output_check["blocked"]:
                    reply = "NEXUS ha filtrado esta respuesta por motivos de seguridad."
                elif output_check["sanitized"] != reply:
                    reply = output_check["sanitized"]

            # Cerebro: Guardar respuesta
            primary_gem = gem if gem != "auto" else (classification.selected_gems[0] if classification.selected_gems else "director")
            if self.cerebro:
                await self.cerebro.aprender_interaccion(message, reply, primary_gem)

            # TTS: Convertir a voz si se solicito
            audio_path = None
            if voice and reply and self.tts:
                try:
                    await self.tts.speak(reply)
                    audio_path = "speaking..."
                except Exception:
                    pass

            # DataCollector: Recolectar conversacion
            if self.data_collector:
                try:
                    conversation = {
                        "messages": [
                            {"role": "user", "content": message},
                            {"role": "assistant", "content": reply}
                        ],
                        "success": True,
                    }
                    metadata = {"gem_used": primary_gem, "project": project}
                    self.data_collector.collect(conversation, metadata)
                except Exception:
                    pass

            # PC Action
            pc_result = None
            if pc_action:
                pc_result = await self._execute_pc_action(pc_action)

            # Auto tool result
            tool_result = None
            if auto_tool_result:
                tool_result = auto_tool_result
                if auto_tool_result.get("success") or "entries" in auto_tool_result or "content" in auto_tool_result:
                    result_text = json.dumps(auto_tool_result, ensure_ascii=False, indent=2)[:2000]
                    reply = f"```tool_result\n{result_text}\n```"
                elif "error" in auto_tool_result:
                    reply = f"Error: {auto_tool_result['error']}"

            # ExtensionPipeline: Hook on_output
            if self.extension_pipeline:
                hook_ctx = HookContext(phase=HookPhase.ON_OUTPUT, gem_id=primary_gem, data=reply)
                hook_ctx = self.extension_pipeline.execute_phase(HookPhase.ON_OUTPUT, hook_ctx.data, {"gem_id": primary_gem})
                if not hook_ctx.should_abort:
                    reply = hook_ctx.data

            return {
                "reply": reply,
                "gem_used": primary_gem,
                "engines": classification.selected_engines,
                "voice": audio_path,
                "pc_action": pc_result,
                "tool_result": tool_result,
                "cerebro_stats": self.cerebro.obtener_estadisticas() if self.cerebro else {},
            }
        except Exception as e:
            logger.warning(f"Director execute error: {e}")
            if self.safety:
                self.safety.record_service_failure("ollama")

        # Fallback minimo
        return {
            "reply": "Error al procesar el mensaje.",
            "gem_used": gem or "director",
        }

    async def _handle_pc_action(self, message: str) -> Optional[Dict]:
        """Detecta y prepara accion de PC"""
        msg_lower = message.lower()
        if "screenshot" in msg_lower or "captura" in msg_lower:
            return {"type": "screenshot"}
        if "click" in msg_lower:
            return {"type": "click", "message": message}
        if "abrir" in msg_lower or "lanzar" in msg_lower:
            return {"type": "launch", "message": message}
        if "escribir" in msg_lower or "type" in msg_lower:
            return {"type": "type", "message": message}
        return None

    async def _execute_pc_action(self, action: Dict) -> Dict:
        """Ejecuta accion de PC detectada"""
        try:
            if action["type"] == "screenshot":
                path = await self.pc_control.screenshot()
                return {"success": True, "type": "screenshot", "path": str(path) if path else None}
            elif action["type"] == "launch":
                return {"success": True, "type": "launch", "message": "Programa lanzado"}
            elif action["type"] == "type":
                return {"success": True, "type": "type", "message": "Texto escrito"}
            elif action["type"] == "click":
                return {"success": True, "type": "click", "message": "Click ejecutado"}
            else:
                return {"success": False, "error": f"Unknown action type: {action.get('type')}"}
        except Exception as e:
            logger.error(f"PC action error: {e}")
            return {"success": False, "error": str(e)}

    async def _process_with_vision(self, message: str, images: List[str], gem: str = "vision") -> Dict:
        """Procesa imágenes - intenta local primero (más rápido), luego PC2"""
        from datetime import datetime
        
        start = datetime.now()
        VISION_MODEL = "qwen2.5vl:7b"
        
        img_clean = images[0] if images else ""
        if img_clean.startswith("data:"):
            img_clean = img_clean.split(",", 1)[1]
        
        prompt = message or "Describe esta imagen brevemente. ¿Qué ves?"
        
        # Intentar local primero (más rápido)
        try:
            LOCAL_URL = "http://localhost:11434"
            messages = [
                {"role": "user", "content": prompt, "images": [img_clean]}
            ]
            response = requests.post(
                f"{LOCAL_URL}/api/chat",
                json={"model": VISION_MODEL, "messages": messages, "stream": False},
                timeout=180
            )
            if response.status_code == 200:
                result = response.json()
                reply = result.get("message", {}).get("content", "")
                tokens = result.get("eval_count", 0) + result.get("prompt_eval_count", 0)
                duration = (datetime.now() - start).total_seconds() * 1000
                return {
                    "success": True,
                    "content": reply,
                    "model": VISION_MODEL,
                    "tool": "vision_analysis",
                    "tokens_used": tokens,
                    "duration_ms": duration,
                    "source": "local"
                }
        except Exception as e:
            logger.warning(f"Local vision failed: {e}")
        
        # Si local falla, intentar PC2
        try:
            PC2_URL = f"http://{os.environ.get('SUPER_NEXUS_PC2_IP', '')}:11434"
            if not os.environ.get('SUPER_NEXUS_PC2_IP'):
                raise ValueError("PC2 not configured")
            messages = [{"role": "user", "content": prompt, "images": [img_clean]}]
            response = requests.post(
                f"{PC2_URL}/api/chat",
                json={"model": VISION_MODEL, "messages": messages, "stream": False},
                timeout=180
            )
            if response.status_code == 200:
                result = response.json()
                reply = result.get("message", {}).get("content", "")
                tokens = result.get("eval_count", 0) + result.get("prompt_eval_count", 0)
                duration = (datetime.now() - start).total_seconds() * 1000
                return {
                    "success": True,
                    "content": reply,
                    "model": VISION_MODEL,
                    "tool": "vision_analysis",
                    "tokens_used": tokens,
                    "duration_ms": duration,
                    "source": "pc2"
                }
        except Exception as e2:
            logger.warning(f"PC2 vision also failed: {e2}")
        
        return {
            "success": False,
            "content": "No disponible. Ejecuta 'ollama run qwen2.5vl:7b' en terminal para usar visión.",
            "model": VISION_MODEL,
            "tool": "vision_analysis",
        }

    async def search_memory(self, query: str) -> Dict:
        if not self.rag:
            return {"results": [], "count": 0, "error": "RAG memory not available"}
        results = self.rag.search(query, top_k=5)
        return {"results": results, "count": len(results)}

    async def get_knowledge_graph(self) -> Dict:
        if not self.kg:
            return {"nodes": [], "edges": [], "stats": {}, "error": "Knowledge graph not available"}
        stats = self.kg.get_stats()
        notes = []
        for category in stats.get("by_category", {}).keys():
            notes_in_cat = self.kg.list_notes(category)
            notes.extend(notes_in_cat.get("notes", []))
        return {
            "nodes": [{"id": n.get("title", ""), "category": n.get("category", "")} for n in notes[:50]],
            "edges": [],
            "stats": stats,
        }

    async def learn(self, query: str, links: list = None) -> Dict:
        if not self.learning:
            return {"error": "Active learning not available"}
        return await self.learning.learn(query, links)

    async def get_status(self) -> Dict:
        engines = await self.connectivity.check_all_engines()
        pc2_status = self.pc2.get_status() if self.pc2 else {"available": False}
        
        def _safe_stats(obj, method="get_stats"):
            if obj and hasattr(obj, method):
                try:
                    return getattr(obj, method)()
                except Exception:
                    return {}
            return {}
        
        return {
            "online": True,
            "version": "2.0",
            "director": self.director.get_status() if self.director else {},
            "engines": engines,
            "pc2": pc2_status,
            "nexus_hive": _safe_stats(self.nexus_hive),
            "mcp_bridge": {
                "tools_count": len(self.mcp_tools),
                "tools": list(self.mcp_tools.keys()),
            },
            "memory": {
                "neural": _safe_stats(self.neural),
                "rag": _safe_stats(self.rag),
                "graph": _safe_stats(self.kg),
            },
            "qa": _safe_stats(self.qa),
            "learning": _safe_stats(self.learning, "get_learning_stats"),
            "communication": _safe_stats(self.comm_flow),
            "runtime": _safe_stats(self.runtime),
            "cerebro": _safe_stats(self.cerebro, "obtener_estadisticas"),
            "voice": {
                "tts_motor": self.tts.motor if self.tts else "N/A",
                "tts_voice": self.tts.voice if self.tts else "N/A",
                "audio_ready": self.audio._audio_ready if self.audio and hasattr(self.audio, '_audio_ready') else False,
                "voice_gem": self.voice_gem.get_status() if self.voice_gem and hasattr(self.voice_gem, 'get_status') else {},
            },
            "pc_control": {
                "screenshot_dir": str(self.pc_control.screenshot_dir) if self.pc_control else "N/A",
                "pc_controller": self.pc_controller.get_status() if self.pc_controller and hasattr(self.pc_controller, 'get_status') else {},
            },
            "security": _safe_stats(self.guardrails, "get_security_report"),
            "safety": _safe_stats(self.safety),
        }

    async def get_projects(self) -> Dict:
        projects_dir = Path(__file__).parent.parent.parent / "data" / "projects"
        projects = ["default"]
        if projects_dir.exists():
            projects.extend([d.name for d in projects_dir.iterdir() if d.is_dir()])
        return {"projects": projects, "current": self.director.current_project}

    async def get_gems(self) -> Dict:
        gems = []
        for name, cap in self.director.gemas.items():
            gems.append({
                "name": name,
                "tags": cap.tags,
                "description": cap.description,
                "model": cap.model,
                "execution_count": cap.execution_count,
                "success_rate": cap.success_count / cap.execution_count if cap.execution_count > 0 else 0,
            })
        return {"gems": gems, "count": len(gems)}

    async def get_tailscale_nodes(self) -> Dict:
        if not self.tailscale:
            return {"nodes": [], "error": "Tailscale bridge not available"}
        return await self.tailscale.list_nodes()

    async def close(self):
        if hasattr(self.director, 'actor_system'):
            await self.director.actor_system.stop_all()
        await self.connectivity.close()
        await self.ollama.close()
        if self.learning:
            await self.learning.close()
        if self.nexus_hive:
            await self.nexus_hive.stop()


# Routes
async def handle_status(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    data = await backend.get_status()
    return web.json_response(data)


async def handle_capabilities(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    report = await backend.director.get_capabilities_report()
    identity = await backend.director.get_dynamic_identity()
    return web.json_response({
        "report": report,
        "identity": identity,
    })


async def handle_projects(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    data = await backend.get_projects()
    return web.json_response(data)


async def handle_gems(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    data = await backend.get_gems()
    return web.json_response(data)


async def handle_knowledge_graph(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    data = await backend.get_knowledge_graph()
    return web.json_response(data)


async def handle_tailscale_nodes(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    data = await backend.get_tailscale_nodes()
    return web.json_response(data)


async def handle_chat(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]

    # Rate limiting
    client_ip = backend.safety.get_client_ip(request)
    allowed, rate_info = backend.safety.check_rate_limit(client_ip)
    if not allowed:
        return web.json_response({
            "error": "Rate limit exceeded",
            "reason": rate_info.get("reason"),
            "retry_after": rate_info.get("retry_after"),
        }, status=429)

    # Validar request
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    valid, error_msg = backend.safety.request_validator.validate(data)
    if not valid:
        return web.json_response({"error": error_msg}, status=400)

    message = data.get("message", "")
    gem = data.get("gem", "auto")
    project = data.get("project", "default")
    voice = data.get("voice", False)
    images = data.get("images", [])
    files = data.get("files", [])

    # Circuit breaker para Ollama
    if not backend.safety.can_use_service("ollama"):
        return web.json_response({
            "error": "Service temporarily unavailable",
            "service": "ollama",
            "retry_after": backend.safety.circuit_breakers["ollama"].config.recovery_timeout,
        }, status=503)

    result = await backend.process_message(message, gem, project, voice=voice, images=images, files=files)
    return web.json_response(result)


async def handle_chat_ws(request: web.Request) -> web.WebSocketResponse:
    """WebSocket handler for streaming chat responses token-by-token"""
    ws = web.WebSocketResponse(heartbeat=30.0)
    await ws.prepare(request)

    backend: SuperNEXUSBackend = request.app["backend"]
    client_ip = backend.safety.get_client_ip(request)

    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:
                    await ws.send_json({"type": "error", "content": "Invalid JSON"})
                    continue

                # Rate limiting
                allowed, rate_info = backend.safety.check_rate_limit(client_ip)
                if not allowed:
                    await ws.send_json({
                        "type": "error",
                        "content": "Rate limit exceeded",
                        "retry_after": rate_info.get("retry_after"),
                    })
                    continue

                # Circuit breaker
                if not backend.safety.can_use_service("ollama"):
                    await ws.send_json({
                        "type": "error",
                        "content": "Service temporarily unavailable",
                    })
                    continue

                message = data.get("message", "")
                gem = data.get("gem", "auto")
                project = data.get("project", "default")
                images = data.get("images", [])
                files = data.get("files", [])

                if not message:
                    await ws.send_json({"type": "error", "content": "Message is required"})
                    continue

                # Send start marker
                await ws.send_json({"type": "start", "gem": gem})

                try:
                    # Phase 1: ALWAYS run process_message (tools work without Ollama)
                    result = await backend.process_message(message, gem, project, images=images, files=files)
                    tool_context = result.get("tool_result")
                    primary_gem = result.get("gem_used", gem)
                    has_images = images and len(images) > 0
                    full_reply = ""

                    if tool_context or result.get("reply", "").startswith("```tool_result"):
                        # Tool executed — stream the result directly (no LLM needed)
                        reply_with_tools = result.get("reply", "")
                        for i in range(0, len(reply_with_tools), 8):
                            chunk = reply_with_tools[i:i+8]
                            await ws.send_json({"type": "token", "content": chunk})
                        full_reply = reply_with_tools
                    elif await backend.ollama.is_available():
                        # Phase 2: LLM streaming (only if Ollama available)
                        system_prompt = (
                            f"Eres el Director de SuperNEXUS, un sistema multi-agente con acceso completo al sistema de archivos de Windows. "
                            f"Gema activa: {primary_gem}. Tienes 37 herramientas: read_file, write_file, edit_file, grep, glob, git, terminal, LSP, web_fetch, code_search. "
                            f"Proyecto actual: D:\\ias\\proyectos\\supernexus-v2. Puedes leer, editar, crear archivos y ejecutar comandos. "
                            f"Responde en español, conciso y directo. Cuando el usuario pida algo del filesystem, ejecuta la herramienta y muestra el resultado."
                        )

                        if has_images:
                            img_clean = images[0]
                            if img_clean.startswith("data:"):
                                img_clean = img_clean.split(",", 1)[1]
                            msgs = [{"role": "user", "content": message or "Describe esta imagen brevemente.", "images": [img_clean]}]
                        else:
                            # Include Director's reply as context if it has one
                            director_reply = result.get("reply", "")
                            if director_reply and not director_reply.startswith("Task executed"):
                                msgs = [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": message},
                                    {"role": "assistant", "content": director_reply},
                                    {"role": "user", "content": "Responde al usuario basandote en el contexto anterior. Se conciso."},
                                ]
                            else:
                                msgs = [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": message},
                                ]

                        gem_model = "qwen2.5vl:7b" if has_images else (
                            backend.director.gemas[primary_gem].model if primary_gem in backend.director.gemas else "qwen2.5-coder:7b"
                        )

                        async for content in backend.ollama.chat_stream(
                            model=gem_model,
                            messages=msgs,
                            options={"temperature": 0.7, "num_predict": 2048},
                        ):
                            full_reply += content
                            await ws.send_json({"type": "token", "content": content})
                    else:
                        # Ollama down but no tool matched — return Director's raw reply
                        fallback = result.get("reply", "Director operando sin LLM. Las herramientas de archivo y terminal siguen disponibles.")
                        await ws.send_json({"type": "token", "content": fallback})
                        full_reply = fallback

                    await ws.send_json({
                        "type": "complete",
                        "gem_used": primary_gem,
                        "tokens_used": len(full_reply.split()),
                    })

                    if backend.cerebro:
                        await backend.cerebro.aprender_interaccion(message, full_reply, primary_gem)

                    try:
                        session = backend.director.sessions.get_session()
                        history = session.get_messages_for_llm(max_messages=20) if session else []
                        if history:
                            await backend.director.review_daemon.spawn_review(history, session.id)
                    except Exception:
                        pass

                except Exception as e:
                    logger.error(f"WebSocket chat error: {e}")
                    await ws.send_json({"type": "error", "content": str(e)})

            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                break

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")

    return ws


async def handle_memory_search(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    query = data.get("query", "")
    result = await backend.search_memory(query)
    return web.json_response(result)


async def handle_learn(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    query = data.get("query", "")
    links = data.get("links", [])
    result = await backend.learn(query, links)
    return web.json_response(result)


# ==================== PC CONTROL ENDPOINTS ====================

async def handle_screenshot(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    filename = request.query.get("filename", "screenshot.png")
    path = await backend.pc_control.screenshot(filename)
    if path:
        return web.json_response({"success": True, "path": str(path)})
    return web.json_response({"success": False, "error": "Screenshot failed"}, status=500)


async def handle_mouse_click(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    x, y = data.get("x", 0), data.get("y", 0)
    button = data.get("button", "left")
    clicks = data.get("clicks", 1)
    ok = await backend.pc_control.mouse_click(x, y, button=button, clicks=clicks)
    return web.json_response({"success": ok})


async def handle_mouse_move(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    ok = await backend.pc_control.mouse_move(data.get("x", 0), data.get("y", 0), data.get("duration", 0.5))
    return web.json_response({"success": ok})


async def handle_type_text(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    ok = await backend.pc_control.type_text(data.get("text", ""), data.get("interval", 0.05))
    return web.json_response({"success": ok})


async def handle_key_press(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    ok = await backend.pc_control.key_press(data.get("key", ""), data.get("presses", 1))
    return web.json_response({"success": ok})


async def handle_vision_describe(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    desc, path = await backend.pc_controller.describe_screen()
    return web.json_response({"description": desc, "screenshot_path": path})


async def handle_vision_instruction(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    instruction = data.get("instruction", "")
    result, response = await backend.pc_controller.follow_instruction(instruction)
    return web.json_response({"result": result, "ollama_response": response})


async def handle_vision_process(request: web.Request) -> web.Response:
    """Endpoint unificado de procesamiento de visión"""
    from src.core.vision_config import get_vision_config, get_all_providers, VISION_PROVIDERS, DEFAULT_VISION_PROVIDER
    
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    
    instruction = data.get("instruction", "Describe esta imagen")
    image_data = data.get("image", "")
    image_url = data.get("url", "")
    provider = data.get("provider", DEFAULT_VISION_PROVIDER)
    
    config = get_vision_config(provider)
    
    result = {
        "provider": provider,
        "model": config.get("model"),
        "instruction": instruction,
    }
    
    if image_url:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(image_url)
                if r.status_code == 200:
                    import base64
                    image_data = base64.b64encode(r.content).decode()
        except Exception as e:
            return web.json_response({"error": f"Failed to fetch image: {e}"}, status=400)
    
    if not image_data:
        return web.json_response({"error": "No image provided"}, status=400)
    
    try:
        import httpx
        ollama_url = config.get("url", "http://localhost:11434")
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": config["model"],
                    "prompt": instruction,
                    "images": [image_data],
                    "stream": False,
                }
            )
            
            if response.status_code == 200:
                result["success"] = True
                result["response"] = response.json().get("response", "")
            else:
                result["success"] = False
                result["error"] = f"HTTP {response.status_code}"
                
                fallback = config.get("fallback")
                if fallback and fallback != provider:
                    result["fallback_attempted"] = fallback
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
    
    return web.json_response(result)


async def handle_vision_providers(request: web.Request) -> web.Response:
    """Lista providers de visión disponibles"""
    from src.core.vision_config import get_all_providers, DEFAULT_VISION_PROVIDER
    return web.json_response({
        "providers": get_all_providers(),
        "default": DEFAULT_VISION_PROVIDER,
    })


async def handle_pc_status(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    from src.control.pc_agent import get_screen_size, get_cursor_pos
    return web.json_response({
        "pc_controller": backend.pc_controller.get_status(),
        "screen_size": get_screen_size(),
        "cursor_pos": get_cursor_pos(),
    })


# ==================== VOICE ENDPOINTS ====================

async def handle_tts_speak(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    text = data.get("text", "")
    if not text:
        return web.json_response({"error": "No text"}, status=400)

    # If client accepts audio, return bytes for browser playback
    accept = request.headers.get("Accept", "")
    if "audio" in accept or data.get("return_audio", False):
        try:
            audio_bytes = await backend.tts.synthesize_bytes(text)
            if audio_bytes:
                content_type = "audio/wav" if audio_bytes[:4] == b"RIFF" else "audio/mpeg"
                return web.Response(body=audio_bytes, content_type=content_type)
        except Exception as e:
            logger.error(f"TTS synthesize error: {e}")

    # Fallback: play on server
    await backend.tts.speak(text)
    return web.json_response({"success": True})


async def handle_tts_voices(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    voices = backend.tts.get_voices_list()
    return web.json_response({"voices": voices})


async def handle_voice_listen(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    timeout = float(request.query.get("timeout", 5))
    text, lang = await backend.audio.listen_for_command(timeout=timeout)
    return web.json_response({"text": text, "language": lang})


async def handle_voice_transcribe(request: web.Request) -> web.Response:
    """Transcribe audio file uploaded from the UI"""
    backend: SuperNEXUSBackend = request.app["backend"]
    
    try:
        reader = await request.multipart()
        audio_bytes = None
        language = "es"
        
        async for part in reader:
            if part.name == "audio":
                audio_bytes = await part.read()
            elif part.name == "language":
                language = (await part.read()).decode()
        
        if not audio_bytes:
            return web.json_response({"error": "No audio data"}, status=400)
        
        text, lang = await backend.audio.recognize(audio_bytes)
        return web.json_response({"text": text, "language": lang})
    except Exception as e:
        logger.error(f"Voice transcribe error: {e}")
        return web.json_response({"error": str(e), "text": ""}, status=500)


async def handle_voice_status(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response({
        "voice_gem": backend.voice_gem.get_status(),
        "audio_ready": backend.audio._audio_ready,
        "model_loaded": backend.audio.model_loaded,
        "personality": backend.personality_manager.current_personality,
        "personalities": backend.personality_manager.list_personalities(),
        "voice_config": backend.personality_manager.get_voice_config(),
    })


async def handle_voice_personalities(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response({
        "personalities": backend.personality_manager.list_personalities(),
        "current": backend.personality_manager.current_personality,
        "voice_config": backend.personality_manager.get_voice_config(),
    })


async def handle_voice_set_voice(request: web.Request) -> web.Response:
    """Change TTS voice (Piper or Edge)"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    voice_id = data.get("voice", "")
    if not voice_id:
        return web.json_response({"error": "No voice specified"}, status=400)
    backend.tts.set_voice(voice_id)
    return web.json_response({"success": True, "voice": voice_id})


async def handle_voice_set_personality(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    
    personality = data.get("personality", "")
    if personality and backend.personality_manager.set_personality(personality):
        voice_config = backend.personality_manager.get_voice_config()
        backend.tts.set_voice(voice_config.get("edge_voice", "es-MX-Dalia"))
        return web.json_response({
            "success": True,
            "personality": personality,
            "voice": voice_config,
        })
    return web.json_response({"success": False, "error": "Personality not found"})


async def handle_voice_route(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    
    query = data.get("query", "")
    result = backend.interaction_router.route(query)
    return web.json_response(result)


# ==================== JARVIS CONTROL ====================

JARVIS_PORT = 9039
MARK_REPO = Path(__file__).resolve().parents[1] / "voice" / "jarvis"

async def handle_jarvis_status(request: web.Request) -> web.Response:
    online = False
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f"http://localhost:{JARVIS_PORT}/status", timeout=aiohttp.ClientTimeout(total=3)):
                online = True
    except Exception:
        pass
    backend: SuperNEXUSBackend = request.app["backend"]
    running = backend._jarvis_process is not None and backend._jarvis_process.returncode is None
    return web.json_response({"online": online, "process_running": running})


async def handle_jarvis_start(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    if backend._jarvis_process and backend._jarvis_process.returncode is None:
        return web.json_response({"success": True, "message": "JARVIS ya está en ejecución"})

    main_py = MARK_REPO / "main.py"
    if not main_py.exists():
        return web.json_response({"success": False, "message": "main.py no encontrado"}, status=500)

    try:
        # Use pythonw to avoid console window
        pythonw = Path(sys.executable).parent / "pythonw.exe"
        exe = str(pythonw) if pythonw.exists() else sys.executable
        backend._jarvis_process = await asyncio.create_subprocess_exec(
            exe, str(main_py),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            cwd=str(MARK_REPO),
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )
        return web.json_response({"success": True, "message": "JARVIS iniciado", "pid": backend._jarvis_process.pid})
    except Exception as e:
        return web.json_response({"success": False, "message": str(e)}, status=500)


async def handle_jarvis_stop(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    if not backend._jarvis_process or backend._jarvis_process.returncode is not None:
        return web.json_response({"success": True, "message": "JARVIS no está en ejecución"})

    backend._jarvis_process.terminate()
    try:
        await asyncio.wait_for(backend._jarvis_process.wait(), timeout=5)
    except asyncio.TimeoutError:
        backend._jarvis_process.kill()
        await backend._jarvis_process.wait()
    backend._jarvis_process = None
    return web.json_response({"success": True, "message": "JARVIS detenido"})


# ==================== BRAIN ENDPOINTS ====================

async def handle_brain_stats(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.cerebro.obtener_estadisticas())


async def handle_brain_preferences(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.cerebro.obtener_preferencias())


async def handle_brain_prompt(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    prompt = backend.cerebro.get_system_prompt_adaptado()
    return web.json_response({"system_prompt": prompt})


async def handle_brain_learn(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    await backend.cerebro.aprender_interaccion(
        data.get("prompt", ""), data.get("response", ""), data.get("gem", "general")
    )
    return web.json_response({"success": True})


async def handle_brain_knowledge(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    tema = request.query.get("tema")
    conocimientos = backend.cerebro.obtener_conocimientos(tema)
    return web.json_response({"knowledge": conocimientos})


async def handle_brain_export(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    result = backend.cerebro.exportar()
    return web.json_response(result)


# ==================== INTEGRATIONS ENDPOINTS ====================

async def handle_codex_status(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.codex.status())


async def handle_codex_run(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    result = await backend.codex.run(
        data.get("prompt", ""), data.get("project", "supernexus-v2"),
        data.get("gem", "developer"), data.get("context"),
    )
    return web.json_response(result)


async def handle_rcon_servers(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response({"servers": backend.rcon_manager.list_servers()})


async def handle_rcon_command(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    server_name = data.get("server", "")
    command = data.get("command", "")

    if not command:
        return web.json_response({"error": "No command provided"}, status=400)

    controller = await backend.rcon_manager.connect(server_name)
    if controller:
        response = await controller.send(command)
        await controller.disconnect()
        if response and "Command rejected" in str(response):
            return web.json_response({"success": False, "error": response}, status=403)
        return web.json_response({"success": True, "response": response})
    return web.json_response({"success": False, "error": "Server not found"}, status=404)


async def handle_multimedia_status(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.multimedia.get_status())


async def handle_multimedia_scenes(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response({"scenes": backend.multimedia.get_scenes()})


async def handle_scheduler_status(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.scheduler.get_status())


async def handle_scheduler_add(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    job = backend.scheduler.add_job(
        data.get("name", ""), data.get("interval_minutes", 60),
        data.get("task", ""), data.get("gem", "scholar"),
    )
    return web.json_response({"success": True, "job": job})


async def handle_guardian_status(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.guardian.get_status())


async def handle_guardian_audit(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    report = await backend.guardian.full_security_audit(
        data.get("config_files", []), data.get("remote_host")
    )
    return web.json_response({"report": report})


# ==================== AI TOOLS ENDPOINTS ====================

async def handle_ai_tools_list(request: web.Request) -> web.Response:
    """Lista todas las herramientas de IA disponibles"""
    backend: SuperNEXUSBackend = request.app["backend"]
    tools = backend.director.ai_tools.get_available_tools()
    return web.json_response({"tools": tools, "count": len(tools)})


async def handle_ai_tools_stats(request: web.Request) -> web.Response:
    """Estadísticas de uso de herramientas de IA"""
    backend: SuperNEXUSBackend = request.app["backend"]
    stats = backend.director.ai_tools.get_stats()
    return web.json_response(stats)


async def handle_ai_tools_execute(request: web.Request) -> web.Response:
    """Ejecuta una herramienta de IA específica"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    
    tool_name = data.get("tool", "")
    message = data.get("message", "")
    context = data.get("context", "")
    images = data.get("images", [])
    
    if not tool_name or not message:
        return web.json_response({"error": "tool and message are required"}, status=400)
    
    result = await backend.director.ai_tools.execute(
        tool_name=tool_name,
        user_message=message,
        context=context,
        images=images,
    )
    return web.json_response(result)


async def handle_ai_tools_select(request: web.Request) -> web.Response:
    """Selecciona automáticamente la herramienta para una tarea"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    
    task = data.get("task", "")
    gem = data.get("gem", "auto")
    
    tool = backend.director.ai_tools.select_tool(task, gem)
    return web.json_response({"selected_tool": tool.to_dict()})

# ==================== MULTIMEDIA ENDPOINTS ====================

async def handle_design_generate(request: web.Request) -> web.Response:
    """Genera contenido multimedia (video, UI, escenas)"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    
    prompt = data.get("prompt", "")
    scene_type = data.get("type", "video")
    context = data.get("context", "")
    
    result = await backend.director.ai_tools.quick_response(
        task=f"Genera {scene_type}: {prompt}",
        gem="design",
        context=context,
    )
    return web.json_response(result)


async def handle_design_storyboard(request: web.Request) -> web.Response:
    """Genera storyboard para escena"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    
    scene_description = data.get("description", "")
    result = await backend.director.ai_tools.quick_response(
        task=f"Crea storyboard para: {scene_description}",
        gem="design",
        context="Estructura: escena, plano, ángulo, iluminación, movimiento, duración",
    )
    return web.json_response(result)


async def handle_music_generate(request: web.Request) -> web.Response:
    """Genera descripción/prompt para música"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    
    style = data.get("style", "")
    mood = data.get("mood", "")
    duration = data.get("duration", "60s")
    
    result = await backend.director.ai_tools.quick_response(
        task=f"Genera composición musical: estilo={style}, mood={mood}, duración={duration}",
        gem="music",
        context="Incluye: BPM, tonalidad, instrumentos, estructura (intro/verso/coro/outro)",
    )
    return web.json_response(result)


async def handle_prompt_optimize(request: web.Request) -> web.Response:
    """Optimiza/comprime prompt"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    
    prompt = data.get("prompt", "")
    target = data.get("target", "general")
    
    result = await backend.director.ai_tools.quick_response(
        task=f"Optimiza este prompt para {target}: {prompt}",
        gem="prompter",
        context="Reduce tokens sin perder significado. Estructura: contexto + instrucción + formato salida",
    )
    return web.json_response(result)


async def handle_producer_campaign(request: web.Request) -> web.Response:
    """Planifica campaña de marketing"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    
    campaign = data.get("campaign", "")
    platforms = data.get("platforms", ["twitter", "youtube"])
    duration = data.get("duration", "7 días")
    
    result = await backend.director.ai_tools.quick_response(
        task=f"Planifica campaña: {campaign} en {platforms} por {duration}",
        gem="producer",
        context="Incluye: calendario, copy por plataforma, métricas objetivo, automatizaciones",
    )
    return web.json_response(result)


async def handle_producer_schedule(request: web.Request) -> web.Response:
    """Crea calendario de contenido"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    
    topic = data.get("topic", "")
    frequency = data.get("frequency", "daily")
    
    result = await backend.director.ai_tools.quick_response(
        task=f"Crea calendario de contenido sobre {topic} con frecuencia {frequency}",
        gem="producer",
        context="Estructura: fecha, plataforma, tipo contenido, copy, hashtags, hora publicación",
    )
    return web.json_response(result)


# ==================== NEXUSHIVE ENDPOINTS ====================

async def handle_hive_status(request: web.Request) -> web.Response:
    """Estado de NexusHive y nodos conectados"""
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.nexus_hive.get_status())


async def handle_hive_send_command(request: web.Request) -> web.Response:
    """Envía comando a un nodo via NexusHive"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    command = data.get("command", "")
    target = data.get("target", None)
    timeout = data.get("timeout", 30)

    if not command:
        return web.json_response({"error": "command is required"}, status=400)

    result = await backend.nexus_hive.send_command(
        command, target_node=target, timeout=timeout
    )
    return web.json_response(result)


async def handle_hive_nodes(request: web.Request) -> web.Response:
    """Lista nodos en la red NexusHive"""
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.nexus_hive.get_nodes())


# ==================== FILESYSTEM ENDPOINTS (Editor UI) ====================

async def handle_fs_list(request: web.Request) -> web.Response:
    """List directory contents for file explorer"""
    import os
    try:
        data = await request.json()
        dir_path = data.get("path", ".")
        entries = []
        with os.scandir(dir_path) as it:
            for entry in sorted(it, key=lambda e: (not e.is_dir(), e.name.lower())):
                if entry.name.startswith(".") and entry.name not in (".env", ".gitignore"):
                    continue
                try:
                    stat = entry.stat()
                    entries.append({
                        "name": entry.name,
                        "path": entry.path.replace("\\", "/") if os.name == "nt" else entry.path,
                        "isDir": entry.is_dir(),
                        "size": stat.st_size if not entry.is_dir() else 0,
                    })
                except (PermissionError, OSError):
                    continue
        return web.json_response({"entries": entries})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


def _validate_fs_path(file_path: str) -> Optional[Path]:
    """Validate filesystem path is within allowed project boundaries."""
    _project_root = Path(__file__).resolve().parents[2]
    ALLOWED_ROOTS = [
        _project_root,
        _project_root.parent,  # sibling projects
        Path(os.path.expanduser("~/.nexus")),
    ]
    BLOCKED_PATTERNS = ["system32", "windows", ".ssh", ".gnupg", ".aws", "credentials"]
    try:
        p = Path(file_path).resolve()
        path_lower = str(p).lower().replace("\\", "/")
        for blocked in BLOCKED_PATTERNS:
            if blocked in path_lower:
                return None
        for root in ALLOWED_ROOTS:
            try:
                if p.is_relative_to(root.resolve()):
                    return p
            except (ValueError, OSError):
                continue
        return None
    except (ValueError, OSError):
        return None


EXEC_BLOCKED_COMMANDS = [
    "rm -rf /", "del /s /q c:", "format", "mkfs", "dd if=",
    "shutdown", "reboot", "halt", "poweroff",
    "net user", "net localgroup", "reg delete", "reg add",
    "curl|sh", "wget|sh", "powershell -enc",
]


async def handle_fs_read(request: web.Request) -> web.Response:
    """Read file content (path-validated)"""
    try:
        data = await request.json()
        file_path = data.get("path", "")
        p = _validate_fs_path(file_path)
        if p is None:
            return web.json_response({"error": "Path not allowed"}, status=403)
        if not p.exists():
            return web.json_response({"error": "File not found"}, status=404)
        if p.stat().st_size > 5_000_000:  # 5MB limit
            return web.json_response({"error": "File too large (>5MB)"}, status=413)
        content = p.read_text(encoding="utf-8", errors="replace")
        return web.json_response({"content": content, "size": len(content)})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


async def handle_fs_write(request: web.Request) -> web.Response:
    """Write file content (path-validated)"""
    try:
        data = await request.json()
        file_path = data.get("path", "")
        content = data.get("content", "")
        p = _validate_fs_path(file_path)
        if p is None:
            return web.json_response({"error": "Path not allowed"}, status=403)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return web.json_response({"ok": True, "size": len(content)})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


async def handle_fs_exec(request: web.Request) -> web.Response:
    """Execute shell command (sanitized)"""
    import asyncio
    try:
        data = await request.json()
        command = data.get("command", "")
        cwd = data.get("cwd", ".")
        if not command.strip():
            return web.json_response({"error": "Empty command"}, status=400)
        cmd_lower = command.lower().strip()
        for blocked in EXEC_BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                return web.json_response({"error": f"Blocked command pattern: {blocked}"}, status=403)
        cwd_path = _validate_fs_path(cwd) or Path(__file__).resolve().parents[2]
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=str(cwd_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        except asyncio.TimeoutError:
            proc.kill()
            return web.json_response({"error": "Command timed out (30s)"}, status=408)
        return web.json_response({
            "stdout": stdout.decode("utf-8", errors="replace") if stdout else "",
            "stderr": stderr.decode("utf-8", errors="replace") if stderr else "",
            "returncode": proc.returncode,
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


# ==================== MCP BRIDGE ENDPOINTS ====================

async def handle_mcp_tools(request: web.Request) -> web.Response:
    """Lista herramientas MCP disponibles"""
    backend: SuperNEXUSBackend = request.app["backend"]
    tools = [{"name": name, "description": getattr(tool, "__doc__", "")} for name, tool in backend.mcp_tools.items()]
    return web.json_response({"tools": tools})


async def handle_mcp_execute(request: web.Request) -> web.Response:
    """Ejecuta herramienta MCP"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    tool_name = data.get("tool", "")
    arguments = data.get("arguments", {})

    if not tool_name:
        return web.json_response({"error": "tool is required"}, status=400)

    tool = backend.mcp_tools.get(tool_name)
    if not tool:
        return web.json_response({"error": f"Unknown tool: {tool_name}"}, status=404)

    try:
        result = await tool(**arguments)
        return web.json_response({"result": result})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_mcp_execute_on_pc2(request: web.Request) -> web.Response:
    """Ejecuta comando en PC2 via MCP Bridge"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    command = data.get("command", "")
    if not command:
        return web.json_response({"error": "command is required"}, status=400)

    result = await execute_on_pc2(command=command)
    return web.json_response({"result": result})


async def handle_mcp_send_task(request: web.Request) -> web.Response:
    """Envía tarea a Antigravity via MCP Bridge"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    task_description = data.get("task_description", "")
    priority = data.get("priority", "medium")

    if not task_description:
        return web.json_response({"error": "task_description is required"}, status=400)

    result = await send_task_to_antigravity(task_description=task_description, priority=priority)
    return web.json_response({"result": result})


# ==================== OPTIMIZATION ENDPOINTS ====================

async def handle_system_stats(request: web.Request) -> web.Response:
    stats = get_system_stats()
    return web.json_response(stats)


async def handle_safe_to_run(request: web.Request) -> web.Response:
    threshold = float(request.query.get("threshold", 75))
    is_safe, cpu, ram = is_safe_to_run_local(threshold)
    return web.json_response({"safe": is_safe, "cpu": cpu, "ram": ram})


async def handle_token_optimize(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    task_type = data.get("task_type", "coding")
    complexity = data.get("complexity", "medium")
    result = backend.token_optimizer.select_model(task_type, complexity)
    return web.json_response(result)


async def handle_token_report(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    report = backend.token_optimizer.generate_report()
    return web.json_response({"report": report})


async def handle_token_compress(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    prompt = data.get("prompt", "")
    compressed, reduction = Token90Reduction.prompt_compression(prompt)
    return web.json_response({"compressed": compressed, "reduction_percent": reduction})


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        response = web.Response(status=200)
    else:
        response = await handler(request)

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


import mimetypes
mimetypes.add_type('.glb', 'model/gltf-binary')


# ==================== OPENAI-COMPATIBLE API ====================
# Enables OpenWebUI and other OpenAI-compatible clients to connect

SUPER_NEXUS_MODELS = [
    {"id": "supernexus/nemotron", "name": "Nemotron (Fast Chat)", "owned_by": "supernexus"},
    {"id": "supernexus/qwen-coder", "name": "Qwen Coder", "owned_by": "supernexus"},
    {"id": "supernexus/deepseek", "name": "DeepSeek (Reasoning)", "owned_by": "supernexus"},
    {"id": "supernexus/auto", "name": "Auto (Smart Routing)", "owned_by": "supernexus"},
    {"id": "auto", "name": "Nexus Director (auto)", "owned_by": "supernexus"},
    {"id": "qwen-coder", "name": "Nexus Code (qwen2.5-coder:7b)", "owned_by": "supernexus"},
    {"id": "deepseek-reason", "name": "Nexus Sage (deepseek-r1:8b)", "owned_by": "supernexus"},
    {"id": "nemotron", "name": "Nexus Director (nemotron)", "owned_by": "supernexus"},
    {"id": "vision", "name": "Nexus Vision (qwen2.5vl:7b)", "owned_by": "supernexus"},
]


async def handle_openai_models(request: web.Request) -> web.Response:
    """GET /v1/models - OpenAI-compatible model listing"""
    return web.json_response({
        "object": "list",
        "data": [
            {
                "id": m["id"],
                "object": "model",
                "created": 0,
                "owned_by": m["owned_by"],
                "permission": [],
            }
            for m in SUPER_NEXUS_MODELS
        ],
    })


async def handle_openai_chat_completions(request: web.Request) -> web.Response:
    """POST /v1/chat/completions - OpenAI-compatible chat endpoint"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": {"message": "Invalid JSON", "type": "invalid_request_error"}}, status=400)

    messages = data.get("messages", [])
    model = data.get("model", "supernexus/auto")
    stream = data.get("stream", False)
    temperature = data.get("temperature", 0.7)
    max_tokens = data.get("max_tokens", 2048)

    # Extract gem from model ID
    gem_map = {
        "supernexus/nemotron": "director",
        "supernexus/qwen-coder": "code",
        "supernexus/deepseek": "sage",
        "supernexus/auto": "auto",
        "nemotron": "director",
        "qwen-coder": "code",
        "deepseek-reason": "sage",
        "auto": "auto",
        "director": "director",
        "code": "code",
        "sage": "sage",
        "vision": "vision",
    }
    gem = gem_map.get(model, "auto")

    # Build message from OpenAI format (supports vision multi-part)
    user_message = ""
    system_context = ""
    images = []
    import tempfile
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            system_context = content if isinstance(content, str) else ""
        elif role == "user":
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            user_message = part.get("text", "")
                        elif part.get("type") == "image_url":
                            img_url = part.get("image_url", {}).get("url", "")
                            if img_url and img_url.startswith("data:image"):
                                import base64
                                fmt, b64 = img_url.split(",", 1)
                                ext = fmt.split(";")[0].split("/")[-1]
                                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
                                tmp.write(base64.b64decode(b64))
                                tmp.close()
                                images.append(tmp.name)
            else:
                user_message = content
        elif role == "assistant":
            if isinstance(content, str):
                user_message += f"\n[Previous: {content}]"

    if not user_message:
        return web.json_response({"error": {"message": "No user message found", "type": "invalid_request_error"}}, status=400)

    try:
        result = await backend.process_message(user_message, gem=gem, project="default", images=images or None)
        reply = result.get("reply", "")
        tokens_used = result.get("tokens_used", 0)

        if stream:
            # Streaming response
            response = web.StreamResponse(
                status=200,
                headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache", "Connection": "keep-alive"},
            )
            await response.prepare(request)

            chunk_id = f"chatcmpl-{int(datetime.now().timestamp())}"
            for i, char in enumerate(reply):
                chunk_data = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": int(datetime.now().timestamp()),
                    "model": model,
                    "choices": [{"index": 0, "delta": {"content": char}, "finish_reason": None}],
                }
                await response.write(f"data: {json.dumps(chunk_data)}\n\n")
                await asyncio.sleep(0)

            # Final chunk
            final_data = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(datetime.now().timestamp()),
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            await response.write(f"data: {json.dumps(final_data)}\n\ndata: [DONE]\n\n")
            await response.write_eof()
            return response
        else:
            # Non-streaming response
            return web.json_response({
                "id": f"chatcmpl-{int(datetime.now().timestamp())}",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": reply},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": tokens_used,
                    "total_tokens": tokens_used,
                },
            })
    except Exception as e:
        logger.error(f"OpenAI chat completions error: {e}")
        return web.json_response({"error": {"message": str(e), "type": "internal_error"}}, status=500)


async def handle_openai_health(request: web.Request) -> web.Response:
    """GET /v1 - OpenAI-compatible health/info endpoint"""
    return web.json_response({
        "service": "supernexus-v2",
        "version": "2.0",
        "openai_compatible": True,
        "endpoints": {
            "models": "/v1/models",
            "chat": "/v1/chat/completions",
        },
    })


async def handle_fetch_url(request: web.Request) -> web.Response:
    """GET /api/tools/fetch - Fetch content from URL (like opencode's fetch tool)"""
    import aiohttp
    
    url = request.query.get("url", "")
    if not url:
        return web.json_response({"error": "url parameter is required"}, status=400)
    
    timeout = aiohttp.ClientTimeout(total=30)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                content = await response.text()
                return web.json_response({
                    "url": url,
                    "status": response.status,
                    "content": content[:50000],
                    "content_type": response.headers.get("Content-Type", "unknown"),
                })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_sourcegraph_search(request: web.Request) -> web.Response:
    """GET /api/tools/sourcegraph - Search code in public repositories"""
    query = request.query.get("q", "")
    if not query:
        return web.json_response({"error": "q parameter is required"}, status=400)
    
    count = int(request.query.get("count", "10"))
    
    # Sourcegraph API (public search)
    import aiohttp
    url = f"https://sourcegraph.com/.api/search?q={query}&type=repo"
    
    timeout = aiohttp.ClientTimeout(total=15)
    try:
        async with aiohttp.ClientSession(timeout=timeout, headers={"Accept": "application/json"}) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return web.json_response({
                        "query": query,
                        "results": data.get("results", [])[:count],
                        "count": min(count, len(data.get("results", []))),
                    })
                else:
                    return web.json_response({
                        "query": query,
                        "error": f"Sourcegraph returned {response.status}",
                        "results": []
                    })
    except Exception as e:
        return web.json_response({
            "query": query,
            "error": str(e),
            "results": []
        })


# ==================== CUSTOM COMMANDS (like OpenCode) ====================
CUSTOM_COMMANDS = {}

def register_custom_command(command_id: str, prompt: str, description: str = "", args: list = None):
    """Registra un comando personalizado"""
    CUSTOM_COMMANDS[command_id] = {
        "prompt": prompt,
        "description": description,
        "args": args or [],
    }

# Registrar algunos comandos de ejemplo (como los de opencode)
register_custom_command(
    "context:prime",
    "RUN git status\nRUN git diff --staged\nREAD README.md",
    "Prepara contexto del proyecto"
)

register_custom_command(
    "git:commit",
    "RUN git add -A\nRUN git status\nRUN git diff --cached",
    "Preparar commit de git"
)

register_custom_command(
    "debug:error",
    "RUN powershell -Command 'Get-EventLog -LogName Application -Newest 10 | Format-List'",
    "Ver errores recientes del sistema"
)

register_custom_command(
    "system:info",
    "RUN systeminfo | findstr /C:\"OS Name\" /C:\"Total Physical Memory\" /C:\"Processor\"",
    "Información del sistema"
)

async def handle_custom_commands_list(request: web.Request) -> web.Response:
    """GET /api/commands - Lista comandos personalizados"""
    return web.json_response({
        "commands": [
            {"id": k, "description": v.get("description", ""), "args": v.get("args", [])}
            for k, v in CUSTOM_COMMANDS.items()
        ],
        "count": len(CUSTOM_COMMANDS)
    })

async def handle_custom_command_execute(request: web.Request) -> web.Response:
    """POST /api/commands/execute - Ejecuta un comando personalizado"""
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    
    command_id = data.get("command_id", "")
    args = data.get("args", {})
    
    if command_id not in CUSTOM_COMMANDS:
        return web.json_response({"error": f"Command '{command_id}' not found"}, status=404)
    
    command = CUSTOM_COMMANDS[command_id]
    prompt = command["prompt"]
    
    # Reemplazar argumentos en el prompt
    for key, value in args.items():
        prompt = prompt.replace(f"${key.upper()}", str(value))
    
    return web.json_response({
        "command_id": command_id,
        "prompt": prompt,
        "ready_to_send": True
    })


# ==================== SAFETY ENDPOINTS ====================

async def handle_safety_status(request: web.Request) -> web.Response:
    """GET /api/safety/status - Estado de protecciones de seguridad"""
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.safety.get_status())


async def handle_safety_reset(request: web.Request) -> web.Response:
    """POST /api/safety/reset - Resetear rate limits o circuit breakers"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        data = {}

    action = data.get("action", "")
    target = data.get("target", "")

    if action == "rate_limit" and target:
        backend.safety.rate_limiter.reset(target)
        return web.json_response({"success": True, "action": "rate_limit_reset", "target": target})
    elif action == "rate_limit":
        backend.safety.rate_limiter.reset()
        return web.json_response({"success": True, "action": "all_rate_limits_reset"})
    elif action == "circuit_breaker" and target:
        cb = backend.safety.circuit_breakers.get(target)
        if cb:
            cb.state = cb.__class__.__module__.split(".")[-1].replace("api_safety", "") or "closed"
            from src.optimization.api_safety import CircuitState
            cb.state = CircuitState.CLOSED
            cb.failure_count = 0
            return web.json_response({"success": True, "action": "circuit_breaker_reset", "target": target})
        return web.json_response({"error": f"Unknown circuit breaker: {target}"}, status=400)
    elif action == "all":
        backend.safety.rate_limiter.reset()
        for cb in backend.safety.circuit_breakers.values():
            from src.optimization.api_safety import CircuitState
            cb.state = CircuitState.CLOSED
            cb.failure_count = 0
        return web.json_response({"success": True, "action": "all_safety_reset"})

    return web.json_response({"error": "Invalid action. Use: rate_limit, circuit_breaker, all"}, status=400)


async def handle_safety_configure(request: web.Request) -> web.Response:
    """POST /api/safety/configure - Configurar protecciones"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    if "rate_limit" in data:
        rl = data["rate_limit"]
        if "max_requests" in rl:
            backend.safety.rate_limiter.config.max_requests = rl["max_requests"]
        if "window_seconds" in rl:
            backend.safety.rate_limiter.config.window_seconds = rl["window_seconds"]

    if "timeout" in data:
        for service, seconds in data["timeout"].items():
            backend.safety.timeout_manager.set_timeout(service, float(seconds))

    return web.json_response({"success": True, "config": backend.safety.get_status()})


# ==================== F15: DOCTOR COMMAND ====================

async def handle_doctor(request: web.Request) -> web.Response:
    """GET /api/doctor - Cached diagnostic report"""
    backend: SuperNEXUSBackend = request.app["backend"]
    if hasattr(backend, "_last_doctor_report"):
        return web.json_response(backend._last_doctor_report)
    return web.json_response({"message": "Run POST /api/doctor/run for fresh diagnostic"})


async def handle_doctor_run(request: web.Request) -> web.Response:
    """POST /api/doctor/run - Run full diagnostic"""
    backend: SuperNEXUSBackend = request.app["backend"]
    report = await backend.doctor.run_full_diagnostic()
    backend._last_doctor_report = report
    return web.json_response(report)


# ==================== F19: CUSTOM COMMANDS ====================

async def handle_custom_commands_list(request: web.Request) -> web.Response:
    """GET /api/commands - List all custom commands"""
    backend: SuperNEXUSBackend = request.app["backend"]
    scope = request.query.get("scope")
    return web.json_response({"commands": backend.custom_commands.list_commands(scope)})


async def handle_custom_command_get(request: web.Request) -> web.Response:
    """GET /api/commands/{name} - Get command details"""
    backend: SuperNEXUSBackend = request.app["backend"]
    name = request.match_info["name"]
    cmd = backend.custom_commands.get_command(name)
    if cmd:
        return web.json_response({"name": cmd.name, "description": cmd.description, "variables": cmd.variables, "scope": cmd.scope})
    return web.json_response({"error": "Command not found"}, status=404)


async def handle_custom_command_create(request: web.Request) -> web.Response:
    """POST /api/commands - Create new command"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    name = data.get("name")
    prompt = data.get("prompt")
    if not name or not prompt:
        return web.json_response({"error": "name and prompt required"}, status=400)

    cmd = backend.custom_commands.create_command(
        name=name,
        prompt=prompt,
        description=data.get("description", ""),
        scope=data.get("scope", "user"),
    )
    return web.json_response({"success": True, "command": {"name": cmd.name, "variables": cmd.variables}})


async def handle_custom_command_execute(request: web.Request) -> web.Response:
    """POST /api/commands/{name}/execute - Execute command with variables"""
    backend: SuperNEXUSBackend = request.app["backend"]
    name = request.match_info["name"]
    try:
        data = await request.json()
    except Exception as e:
        data = {}

    rendered = backend.custom_commands.execute_command(name, data.get("variables", {}))
    if rendered:
        return web.json_response({"success": True, "prompt": rendered})
    return web.json_response({"error": "Command not found"}, status=404)


async def handle_custom_command_delete(request: web.Request) -> web.Response:
    """DELETE /api/commands/{name} - Delete command"""
    backend: SuperNEXUSBackend = request.app["backend"]
    name = request.match_info["name"]
    if backend.custom_commands.delete_command(name):
        return web.json_response({"success": True})
    return web.json_response({"error": "Command not found"}, status=404)


# ==================== F1: SESSION MANAGEMENT ====================

async def handle_sessions_list(request: web.Request) -> web.Response:
    """GET /api/sessions - List sessions"""
    backend: SuperNEXUSBackend = request.app["backend"]
    project = request.query.get("project")
    return web.json_response({"sessions": backend.director.sessions.list_sessions(project)})


async def handle_session_get(request: web.Request) -> web.Response:
    """GET /api/sessions/{id} - Get session details"""
    backend: SuperNEXUSBackend = request.app["backend"]
    session_id = request.match_info["id"]
    session = backend.director.sessions.get_session(session_id)
    return web.json_response(session.to_dict())


async def handle_session_create(request: web.Request) -> web.Response:
    """POST /api/sessions - Create new session"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        data = {}
    session = backend.director.sessions.create_session(
        project=data.get("project", "default"),
        parent_id=data.get("parent_id"),
    )
    return web.json_response({"success": True, "session": session.to_dict()})


async def handle_session_compact(request: web.Request) -> web.Response:
    """POST /api/sessions/{id}/compact - Compact session"""
    backend: SuperNEXUSBackend = request.app["backend"]
    session_id = request.match_info["id"]
    try:
        data = await request.json()
    except Exception as e:
        data = {}
    result = backend.director.sessions.compact_session(session_id, summary=data.get("summary", ""))
    return web.json_response(result)


async def handle_session_pressure(request: web.Request) -> web.Response:
    """GET /api/sessions/{id}/pressure - Get context pressure"""
    backend: SuperNEXUSBackend = request.app["backend"]
    session_id = request.match_info["id"]
    return web.json_response(backend.director.sessions.get_context_pressure(session_id))


# ==================== F5: TOKEN BUDGET ====================

async def handle_budget_status(request: web.Request) -> web.Response:
    """GET /api/budget - Get token budget status"""
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.director.token_budget.get_status())


async def handle_budget_reset(request: web.Request) -> web.Response:
    """POST /api/budget/reset - Reset token budget"""
    backend: SuperNEXUSBackend = request.app["backend"]
    backend.director.token_budget.reset_run()
    return web.json_response({"success": True, "budget": backend.director.token_budget.get_status()})


async def handle_budget_configure(request: web.Request) -> web.Response:
    """POST /api/budget/configure - Configure token budget"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    backend.director.token_budget.configure(**data)
    return web.json_response({"success": True, "config": backend.director.token_budget.get_status()})


# ==================== AUTO-COMPACT (resumir conversaciones largas) ====================
CONVERSATION_HISTORY = []
MAX_MESSAGES_BEFORE_COMPACT = 20

async def handle_compact_conversation(request: web.Request) -> web.Response:
    """POST /api/compact - Resume la conversación actual"""
    backend: SuperNEXUSBackend = request.app["backend"]
    
    try:
        data = await request.json()
    except Exception as e:
        data = {}
    
    force = data.get("force", False)
    
    if len(CONVERSATION_HISTORY) < MAX_MESSAGES_BEFORE_COMPACT and not force:
        return web.json_response({
            "messages_count": len(CONVERSATION_HISTORY),
            "compact_needed": False,
            "message": "No es necesario compactar todavía"
        })
    
    # Generar resumen usando el modelo
    try:
        summary_prompt = f"Resume esta conversación en máximo 5 párrafos, manteniendo la información más importante:\n\n"
        for msg in CONVERSATION_HISTORY[-10:]:
            summary_prompt += f"{msg.get('role', 'user')}: {msg.get('content', '')[:200]}\n"
        
        response = await backend.ollama.chat(
            model="nemotron-3-nano:4b",
            messages=[{"role": "user", "content": summary_prompt}],
            options={"temperature": 0.3, "num_predict": 500}
        )
        
        summary = response.get("message", {}).get("content", "")[:500]
        
        # Guardar resumen y limpiar historial
        CONVERSATION_HISTORY.clear()
        CONVERSATION_HISTORY.append({
            "role": "system",
            "content": f"[RESUMEN DE CONVERSACIÓN ANTERIOR]\n{summary}"
        })
        
        return web.json_response({
            "summary": summary,
            "messages_before": MAX_MESSAGES_BEFORE_COMPACT,
            "messages_after": len(CONVERSATION_HISTORY)
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_conversation_history(request: web.Request) -> web.Response:
    """GET /api/conversation - Ver historial de conversación"""
    return web.json_response({
        "messages": CONVERSATION_HISTORY,
        "count": len(CONVERSATION_HISTORY),
        "compact_threshold": MAX_MESSAGES_BEFORE_COMPACT
    })


# ==================== F2: DAG / GOAL DECOMPOSITION ====================

async def handle_dag_decompose(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    goal = data.get("goal", "")
    if not goal:
        return web.json_response({"error": "goal required"}, status=400)
    dag = backend.director.dag.decompose_goal(goal)
    return web.json_response({"dag_id": dag.id, "goal": dag.goal, "tasks": len(dag.nodes), "nodes": [{"id": n.id, "title": n.title, "assignee": n.assignee, "depends_on": n.depends_on} for n in dag.nodes]})


async def handle_dag_execute(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    dag_id = request.match_info["id"]
    dag = backend.director.dag.get_run(dag_id)
    if not dag:
        return web.json_response({"error": "DAG not found"}, status=404)
    result = await backend.director.dag.execute_dag(dag)
    return web.json_response(result)


async def handle_dag_get(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    dag = backend.director.dag.get_run(request.match_info["id"])
    if dag:
        return web.json_response({"id": dag.id, "goal": dag.goal, "status": dag.status, "completion": dag.get_completion_percent(), "nodes": [{"id": n.id, "title": n.title, "status": n.status.value} for n in dag.nodes]})
    return web.json_response({"error": "Not found"}, status=404)


async def handle_dag_list(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response({"runs": backend.director.dag.list_runs()})


async def handle_orchestrate_status(request: web.Request) -> web.Response:
    """GET /api/orchestrate/status - Estado del sistema de orquestación multi-motor"""
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend.director, 'multi_motor_status'):
        return web.json_response({"available": False, "error": "Multi-motor system not initialized"})
    status = await backend.director.multi_motor_status()
    return web.json_response(status)


async def handle_orchestrate(request: web.Request) -> web.Response:
    """POST /api/orchestrate - Orquestación completa: descomposición LLM + ejecución + síntesis"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    goal = data.get("goal", "")
    if not goal:
        return web.json_response({"error": "goal required"}, status=400)
    if not hasattr(backend.director, 'orchestrator'):
        return web.json_response({"error": "Orchestrator not initialized"}, status=503)
    result = await backend.director.orchestrate(goal)
    return web.json_response({
        "success": result["success"],
        "goal": result["goal"],
        "dag_id": result["dag_id"],
        "tasks": result["tasks"],
        "completed": result["completed"],
        "failed": result["failed"],
        "task_results": result["task_results"],
        "synthesis": result["synthesis"],
        "judge": result.get("judge", {}),
        "duration_s": result["duration_s"],
    })


# ==================== DEVLOOP + CONDUCTOR (gstack pattern) ====================

_devloop_instance = None
_conductor_instance = None


def _get_devloop(backend):
    """Lazy-init DevLoop singleton."""
    global _devloop_instance
    if _devloop_instance is None:
        from src.core.dev_loop import DevLoop

        async def llm_call(prompt: str) -> str:
            result = await backend.director.chat(prompt)
            return result.get("response", "") if isinstance(result, dict) else str(result)

        _devloop_instance = DevLoop(llm_call=llm_call, context="SuperNEXUS v2")
    return _devloop_instance


def _get_conductor():
    """Lazy-init Conductor singleton."""
    global _conductor_instance
    if _conductor_instance is None:
        from src.core.conductor import Conductor
        _conductor_instance = Conductor(repo_path=r"D:\ias\proyectos\supernexus-v2")
    return _conductor_instance


async def handle_devloop_run(request: web.Request) -> web.Response:
    """POST /api/devloop/run - Ejecuta 7-phase loop para un objetivo."""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    goal = data.get("goal", "")
    if not goal:
        return web.json_response({"error": "goal required"}, status=400)
    start_phase = data.get("start_phase", "think")
    loop = _get_devloop(backend)
    from src.core.dev_loop import Phase
    phase_map = {p.value: p for p in Phase}
    phase = phase_map.get(start_phase, Phase.THINK)
    result = await loop.run(goal, start_phase=phase)
    return web.json_response({
        "id": result.id,
        "goal": result.goal,
        "status": result.status,
        "current_phase": result.current_phase.value,
        "phases": {
            k: {
                "gate": v.gate_result.value,
                "duration_s": round(v.duration_s, 2),
                "error": v.error,
            }
            for k, v in result.phases.items()
        },
        "total_duration_s": round(result.total_duration_s, 2),
    })


async def handle_devloop_status(request: web.Request) -> web.Response:
    """GET /api/devloop/status"""
    backend: SuperNEXUSBackend = request.app["backend"]
    loop = _get_devloop(backend)
    return web.json_response(loop.status())


async def handle_conductor_spawn(request: web.Request) -> web.Response:
    """POST /api/conductor/spawn - Crea nuevo work stream."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    name = data.get("name", "")
    goal = data.get("goal", "")
    if not name:
        return web.json_response({"error": "name required"}, status=400)
    conductor = _get_conductor()
    try:
        stream = await conductor.spawn(name, goal=goal)
        return web.json_response(stream.summary())
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


async def handle_conductor_merge(request: web.Request) -> web.Response:
    """POST /api/conductor/merge - Merge stream a main."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    name = data.get("name", "")
    if not name:
        return web.json_response({"error": "name required"}, status=400)
    conductor = _get_conductor()
    try:
        ok = await conductor.merge(name, squash=data.get("squash", True))
        return web.json_response({"merged": ok, "name": name})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


async def handle_conductor_cleanup(request: web.Request) -> web.Response:
    """POST /api/conductor/cleanup - Limpia worktree."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    name = data.get("name", "")
    if not name:
        return web.json_response({"error": "name required"}, status=400)
    conductor = _get_conductor()
    try:
        await conductor.cleanup(name)
        return web.json_response({"cleaned": True, "name": name})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


async def handle_conductor_status(request: web.Request) -> web.Response:
    """GET /api/conductor/status"""
    conductor = _get_conductor()
    return web.json_response(conductor.status())


# ==================== ACTOR SYSTEM (Sprint 5) ====================

# ==================== F1: DIRECTOR SOBERANO ====================

async def handle_sovereign_execute(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    task = data.get("task", "")
    if not task:
        return web.json_response({"error": "task required"}, status=400)
    if not hasattr(backend.director, 'sovereign_execute'):
        return web.json_response({"error": "Sovereign Director not initialized"}, status=503)
    result = await backend.director.sovereign_execute(task)
    return web.json_response(result)


async def handle_decision_engine_status(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend.director, 'decision_engine'):
        return web.json_response({"error": "Not initialized"}, status=503)
    return web.json_response(backend.director.decision_engine.status())


async def handle_sub_directors_status(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend.director, 'sub_directors'):
        return web.json_response({"error": "Not initialized"}, status=503)
    return web.json_response(backend.director.sub_directors.status())


async def handle_external_agents_status(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend.director, 'external_agents'):
        return web.json_response({"error": "Not initialized"}, status=503)
    return web.json_response(backend.director.external_agents.status())


async def handle_register_external_agent(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    required = ["name", "capabilities", "protocol", "endpoint"]
    if not all(k in data for k in required):
        return web.json_response({"error": f"Required: {required}"}, status=400)
    from src.core.external_agent import ExternalAgent
    agent = ExternalAgent(
        name=data["name"],
        capabilities=data["capabilities"],
        protocol=data["protocol"],
        endpoint=data["endpoint"],
        cost=data.get("cost", "free"),
        max_concurrent=data.get("max_concurrent", 1),
        timeout_s=data.get("timeout_s", 300),
    )
    backend.director.external_agents.register(agent)
    return web.json_response({"registered": agent.name, "capabilities": agent.capabilities})


async def handle_learning_status(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend.director, 'learning_loop'):
        return web.json_response({"error": "Not initialized"}, status=503)
    return web.json_response(backend.director.learning_loop.status())


async def handle_command_history(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend.director, 'command_dispatcher'):
        return web.json_response({"error": "Not initialized"}, status=503)
    return web.json_response(backend.director.command_dispatcher.status())


# ==================== F2: MEMORY HARDENING ====================

async def handle_memory_triage_status(request: web.Request) -> web.Response:
    """GET /api/memory/triage — Triage stats."""
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend.director, 'memory_triage'):
        return web.json_response({"error": "Not initialized"}, status=503)
    return web.json_response(backend.director.memory_triage.status())


async def handle_triage_evaluate(request: web.Request) -> web.Response:
    """POST /api/memory/triage/evaluate — Test content against triage gates."""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    content = data.get("content", "")
    if not content:
        return web.json_response({"error": "content required"}, status=400)
    if not hasattr(backend.director, 'memory_triage'):
        return web.json_response({"error": "Not initialized"}, status=503)
    result = backend.director.memory_triage.evaluate(content)
    return web.json_response({
        "passed": result.passed,
        "score": round(result.score, 2),
        "rejected_by": result.rejected_by.value if result.rejected_by else None,
        "factual_confidence": round(result.factual_confidence, 2),
        "gates_passed": result.gates_passed,
        "reason": result.reason,
    })


async def handle_pointer_status(request: web.Request) -> web.Response:
    """GET /api/memory/pointers — Pointer store stats."""
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend.director, 'pointer_store'):
        return web.json_response({"error": "Not initialized"}, status=503)
    return web.json_response(backend.director.pointer_store.status())


async def handle_dream_consolidate(request: web.Request) -> web.Response:
    """POST /api/memory/dream — Trigger dream consolidation."""
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend.director, 'dream_consolidator'):
        return web.json_response({"error": "Not initialized"}, status=503)
    if not hasattr(backend.director, 'hierarchical_memory'):
        return web.json_response({"error": "HierarchicalMemory not available"}, status=503)
    result = backend.director.dream_consolidator.consolidate(backend.director.hierarchical_memory)
    return web.json_response({
        "selected": result.selected,
        "promoted": result.promoted,
        "pruned": result.pruned,
        "snapshot_path": result.snapshot_path,
        "duration_s": round(result.duration_s, 3),
        "summary": result.summary(),
    })

# ==================== F3: PROTOCOL STACK ====================

async def handle_protocol_status(request: web.Request) -> web.Response:
    """GET /api/protocols/status — Protocol stack status."""
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend.director, 'protocol_router'):
        return web.json_response({"error": "Not initialized"}, status=503)
    return web.json_response(backend.director.protocol_router.status())


async def handle_acp_send(request: web.Request) -> web.Response:
    """POST /api/protocols/acp/send — Send ACP message."""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    if not hasattr(backend.director, 'acp_router'):
        return web.json_response({"error": "Not initialized"}, status=503)
    msg = ACPMessage(
        sender=data.get("sender", "api"),
        target=data.get("target", ""),
        msg_type=ACPMessageType(data.get("msg_type", "request")),
        payload=data.get("payload", {}),
    )
    response = await backend.director.acp_router.send(msg)
    if response:
        return web.json_response(response.to_dict())
    return web.json_response({"error": "No response", "expired": msg.is_expired()}, status=408)


async def handle_agent_card(request: web.Request) -> web.Response:
    """GET /.well-known/agent.json — A2A agent card."""
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend.director, 'a2a_server'):
        return web.json_response({"error": "Not initialized"}, status=503)
    return web.json_response(backend.director.a2a_server.agent_card.to_dict())


async def handle_a2a_create_task(request: web.Request) -> web.Response:
    """POST /api/a2a/tasks — Create and optionally execute A2A task."""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    if not hasattr(backend.director, 'a2a_server'):
        return web.json_response({"error": "Not initialized"}, status=503)
    description = data.get("description", "")
    if not description:
        return web.json_response({"error": "description required"}, status=400)
    task = backend.director.a2a_server.create_task(
        description=description, submitter=data.get("submitter", "api"),
    )
    if data.get("execute", True):
        task = await backend.director.a2a_server.execute_task(task.id)
    return web.json_response(task.to_dict())


async def handle_a2a_get_task(request: web.Request) -> web.Response:
    """GET /api/a2a/tasks/{task_id} — Get A2A task status."""
    backend: SuperNEXUSBackend = request.app["backend"]
    task_id = request.match_info.get("task_id", "")
    if not hasattr(backend.director, 'a2a_server'):
        return web.json_response({"error": "Not initialized"}, status=503)
    task = backend.director.a2a_server.get_task(task_id)
    if not task:
        return web.json_response({"error": "Task not found"}, status=404)
    return web.json_response(task.to_dict())


# ==================== F4: SKILLS MARKETPLACE ====================

async def handle_skills_marketplace(request: web.Request) -> web.Response:
    """GET /api/skills/marketplace — List and search skills."""
    backend: SuperNEXUSBackend = request.app["backend"]
    query = request.query.get("search", "")
    tag = request.query.get("tag", "")
    if not hasattr(backend.director, 'skill_registry'):
        return web.json_response({"error": "Not initialized"}, status=503)
    if query:
        results = backend.director.skill_registry.search(query)
    elif tag:
        results = backend.director.skill_registry.search_by_tag(tag)
    else:
        results = backend.director.skill_registry.skills
    return web.json_response({
        "total": len(results),
        "skills": [r.to_dict() for r in results],
    })


async def handle_skills_install(request: web.Request) -> web.Response:
    """POST /api/skills/install — Install a skill."""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    name = data.get("name", "")
    if not name:
        return web.json_response({"error": "name required"}, status=400)
    if not hasattr(backend.director, 'skill_registry'):
        return web.json_response({"error": "Not initialized"}, status=503)
    success = backend.director.skill_registry.install(name)
    return web.json_response({"installed": name, "success": success})


async def handle_skills_publish(request: web.Request) -> web.Response:
    """POST /api/skills/publish — Publish a skill manifest."""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    if not data.get("name"):
        return web.json_response({"error": "name required"}, status=400)
    if not hasattr(backend.director, 'skill_registry'):
        return web.json_response({"error": "Not initialized"}, status=503)
    manifest = SkillManifest(
        name=data["name"], version=data.get("version", "1.0.0"),
        author=data.get("author", ""), tags=data.get("tags", []),
        requires=data.get("requires", []), description=data.get("description", ""),
        install_path=data.get("install_path", ""),
    )
    try:
        backend.director.skill_registry.publish(manifest)
        return web.json_response({"published": manifest.name, "version": manifest.version})
    except ValueError as e:
        return web.json_response({"error": str(e)}, status=409)


async def handle_skills_rate(request: web.Request) -> web.Response:
    """POST /api/skills/rate — Rate a skill."""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    name = data.get("name", "")
    rating = data.get("rating", 0)
    if not name:
        return web.json_response({"error": "name required"}, status=400)
    if not hasattr(backend.director, 'skill_registry'):
        return web.json_response({"error": "Not initialized"}, status=503)
    result = backend.director.skill_registry.update_rating(name, float(rating))
    if not result:
        return web.json_response({"error": "Skill not found"}, status=404)
    return web.json_response({"name": name, "new_rating": result.rating, "count": result.rating_count})


# ==================== F6: CODE ABSORPTION ====================

async def handle_absorb_repo(request: web.Request) -> web.Response:
    """POST /api/absorb/repo — Trigger repo absorption."""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    repo_path = data.get("path", "")
    repo_name = data.get("name", "")
    if not repo_path:
        return web.json_response({"error": "path required"}, status=400)
    if not hasattr(backend.director, 'code_absorber'):
        return web.json_response({"error": "Not initialized"}, status=503)
    try:
        patterns = backend.director.code_absorber.scan_repo(repo_path, repo_name=repo_name)
        absorbed = backend.director.code_absorber.absorb()
        return web.json_response({
            "repo": repo_name or repo_path,
            "patterns_found": len(patterns),
            "absorbed": absorbed,
        })
    except FileNotFoundError as e:
        return web.json_response({"error": str(e)}, status=404)


async def handle_absorb_status(request: web.Request) -> web.Response:
    """GET /api/absorb/status — Absorption pipeline status."""
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend.director, 'code_absorber'):
        return web.json_response({"error": "Not initialized"}, status=503)
    return web.json_response(backend.director.code_absorber.status())


# ==================== F7: PRODUCTION HARDENING ====================

async def handle_health_circuit_breakers(request: web.Request) -> web.Response:
    """GET /api/health — Circuit breaker and health status."""
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend.director, 'health_checker'):
        return web.json_response({"error": "Not initialized"}, status=503)
    return web.json_response(backend.director.health_checker.status())


async def handle_token_usage(request: web.Request) -> web.Response:
    """GET /api/tokens/usage — Token monitor status."""
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend.director, 'token_monitor'):
        return web.json_response({"error": "Not initialized"}, status=503)
    agent = request.query.get("agent", "")
    if agent:
        return web.json_response(backend.director.token_monitor.check_budget(agent))
    return web.json_response(backend.director.token_monitor.status())


async def handle_actors_list(request: web.Request) -> web.Response:
    """GET /api/actors - Lista todos los actores y su estado."""
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend.director, 'actor_system'):
        return web.json_response({"error": "ActorSystem not initialized"}, status=503)
    return web.json_response(backend.director.actor_system.status())


async def handle_actors_tell(request: web.Request) -> web.Response:
    """POST /api/actors/{actor_id}/tell - Envía mensaje a un actor."""
    backend: SuperNEXUSBackend = request.app["backend"]
    actor_id = request.match_info.get("actor_id", "")
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    content = data.get("content", "")
    msg_type = data.get("msg_type", "task")
    if not content:
        return web.json_response({"error": "content required"}, status=400)
    if not hasattr(backend.director, 'actor_system'):
        return web.json_response({"error": "ActorSystem not initialized"}, status=503)
    result = await backend.director.actor_system.ask(actor_id, content, msg_type=msg_type,
                                                      timeout=data.get("timeout", 120.0))
    return web.json_response({"success": result.success, "content": result.content,
                              "error": result.error, "duration_s": result.duration_s})


async def handle_actors_route(request: web.Request) -> web.Response:
    """POST /api/actors/route - Enruta mensaje al mejor actor por contenido."""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    content = data.get("content", "")
    if not content:
        return web.json_response({"error": "content required"}, status=400)
    if not hasattr(backend.director, 'actor_system'):
        return web.json_response({"error": "ActorSystem not initialized"}, status=503)
    target = backend.director.actor_system.route(content)
    if not target:
        return web.json_response({"error": "No target found", "content": content[:60]}, status=404)
    result = await backend.director.actor_system.ask(target, content, timeout=data.get("timeout", 120.0))
    return web.json_response({"success": result.success, "content": result.content,
                              "target": target, "error": result.error, "duration_s": result.duration_s})


async def handle_actors_model_select(request: web.Request) -> web.Response:
    """POST /api/actors/model-select - Elige el mejor modelo según la tarea."""
    from src.core.actor_base import select_model, MODEL_CATALOG
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    goal = data.get("goal", "")
    if not goal:
        return web.json_response({"error": "goal required"}, status=400)
    model = select_model(goal, prefer_quality=data.get("prefer_quality", False),
                         prefer_speed=data.get("prefer_speed", False))
    info = MODEL_CATALOG.get(model, {})
    return web.json_response({"model": model, "info": {
        "context_window": info.context_window,
        "speed_tps": info.speed_tps,
        "quality_rating": info.quality_rating,
        "capabilities": info.capabilities,
    }})


# ==================== F3: CHECKPOINTS ====================

async def handle_checkpoints_list(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    run_id = request.query.get("run_id")
    if run_id:
        cps = backend.director.checkpoints.get_all_checkpoints(run_id)
        return web.json_response({"checkpoints": [{"id": c.id, "node": c.node_id, "created": c.created_at} for c in cps]})
    return web.json_response(backend.director.checkpoints.get_stats())


async def handle_checkpoints_incomplete(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response({"incomplete_runs": backend.director.checkpoints.get_incomplete_runs()})


async def handle_checkpoint_save(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    run_id = request.match_info["run_id"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    cp = backend.director.checkpoints.save_checkpoint(run_id, data.get("node_id", "main"), data.get("state", {}))
    return web.json_response({"checkpoint_id": cp.id})


# ==================== F8: RECIPES ====================

async def handle_recipes_list(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response({"recipes": backend.director.recipes.list_recipes()})


async def handle_recipe_load(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    recipe = backend.director.recipes.load_from_yaml(data.get("path", ""))
    return web.json_response({"name": recipe.name, "steps": len(recipe.steps)})


async def handle_recipe_execute(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    name = request.match_info["name"]
    try:
        data = await request.json()
    except Exception as e:
        data = {}
    result = await backend.director.recipes.execute_recipe(name, data.get("variables", {}))
    return web.json_response(result)


# ==================== F6: GRAPH EVOLUTION ====================

async def handle_graph_status(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.director.graph_evolution.get_stats())


# ==================== F7: APPROVAL GATES ====================

async def handle_approvals_list(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response({"pending": [{"id": r.id, "task": r.task, "created": r.created_at} for r in backend.director.approval.get_pending_requests()]})


async def handle_approval_request(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    req = await backend.director.approval.request_approval(data.get("task", ""), data.get("description", ""), data.get("timeout"), data.get("escalation"))
    return web.json_response({"id": req.id, "status": req.status.value})


async def handle_approval_respond(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    ok = await backend.director.approval.respond(request.match_info["id"], data.get("approved", False), data.get("responder", "human"), data.get("comment", ""))
    return web.json_response({"success": ok})


# ==================== F9: KNOWLEDGE VAULT ====================

async def handle_vault_list(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    category = request.query.get("category")
    return web.json_response({"notes": backend.director.vault.list_notes(category), "stats": backend.director.vault.get_stats()})


async def handle_vault_add(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    note = backend.director.vault.add_note(data.get("title", ""), data.get("content", ""), data.get("category", "general"), data.get("tags", []))
    return web.json_response({"id": note.id, "title": note.title})


async def handle_vault_search(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    query = request.query.get("q", "")
    return web.json_response({"results": backend.director.vault.search(query)})


async def handle_vault_get(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    note = backend.director.vault.get_note(request.match_info["id"])
    if note:
        return web.json_response({"id": note.id, "title": note.title, "content": note.content, "category": note.category, "tags": note.tags})
    return web.json_response({"error": "Not found"}, status=404)


# ==================== F11: RISK ASSESSMENT ====================

async def handle_risk_summary(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.director.risk.get_summary())


async def handle_risk_assess(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        data = {}
    findings = backend.director.risk.assess_system(data)
    return web.json_response(backend.director.risk.get_summary())


# ==================== F14: MEMORY HEALTH ====================

async def handle_memory_health(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.director.memory_health.get_summary())


# ==================== F17: TOOL MONITORING ====================

async def handle_tool_monitor(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.director.tool_monitor.get_summary())


async def handle_tool_record(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    backend.director.tool_monitor.record_call(data.get("tool", ""), data.get("duration_ms", 0), data.get("tokens", 0), data.get("success", True), data.get("error", ""), data.get("model_type", "local"))
    return web.json_response({"success": True})


# ==================== F13: COLLABORATION HALL ====================

async def handle_hall_create_room(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    room = backend.director.hall.create_room(data.get("topic", ""), data.get("agents", []))
    return web.json_response({"id": room.id, "topic": room.topic})


async def handle_hall_add_event(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    from src.core.collaboration_hall import EventType
    event = backend.director.hall.add_event(request.match_info["id"], data.get("agent", ""), EventType(data.get("type", "message")), data.get("content", ""), data.get("thread_id", ""))
    return web.json_response({"id": event.id})


async def handle_hall_timeline(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response({"timeline": backend.director.hall.get_timeline(request.match_info["id"])})


async def handle_hall_list(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response({"rooms": backend.director.hall.list_rooms()})


# ==================== F18: RETRY WITH BACKOFF ====================

async def handle_retry_status(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.director.retry.get_stats())


async def handle_retry_configure(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    backend.director.retry.configure(data.get("task_type", "default"), **data.get("config", {}))
    return web.json_response({"success": True})


# ==================== F20: LIVE NOTES ====================

async def handle_live_note_create(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    note = backend.director.live_notes.create_note(data.get("topic", ""), data.get("sources", []), data.get("content", ""), data.get("update_interval", 300))
    return web.json_response({"id": note.id, "topic": note.topic})


async def handle_live_notes_list(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response({"notes": backend.director.live_notes.list_notes()})


async def handle_live_note_update(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    backend.director.live_notes.update_note(request.match_info["id"], data.get("content", ""))
    return web.json_response({"success": True})


async def handle_live_notes_backlinks(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    topic = request.query.get("topic", "")
    return web.json_response({"backlinks": backend.director.live_notes.get_backlinks(topic)})


async def handle_live_notes_graph(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.director.live_notes.get_graph())


async def handle_live_notes_search(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    query = request.query.get("q", "")
    return web.json_response({"results": backend.director.live_notes.search_notes(query)})


# F21: Background Review Daemon handlers

async def handle_review_status(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    stats = backend.director.review_daemon.get_stats()
    return web.json_response(stats)


async def handle_review_configure(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    backend.director.review_daemon.configure(enabled=data.get("enabled", True))
    return web.json_response({"success": True, "enabled": backend.director.review_daemon._enabled})


async def handle_review_trigger(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    session = backend.director.sessions.get_session()
    history = session.get_messages_for_llm(max_messages=20) if session else []
    if not history:
        return web.json_response({"error": "No conversation history"}, status=400)
    await backend.director.review_daemon.spawn_review(history, session.id)
    return web.json_response({"success": True, "message": "Review triggered"})


# F22: Tool Call Guardrails handlers

async def handle_guardrails_status(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    stats = backend.director.tool_guardrails.get_stats()
    return web.json_response(stats)


async def handle_guardrails_configure(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    config = GuardrailConfig(
        warnings_enabled=data.get("warnings_enabled", True),
        hard_stop_enabled=data.get("hard_stop_enabled", False),
        exact_failure_warn_after=data.get("exact_failure_warn_after", 2),
        exact_failure_block_after=data.get("exact_failure_block_after", 5),
        same_tool_failure_warn_after=data.get("same_tool_failure_warn_after", 3),
        same_tool_failure_halt_after=data.get("same_tool_failure_halt_after", 8),
        no_progress_warn_after=data.get("no_progress_warn_after", 2),
        no_progress_block_after=data.get("no_progress_block_after", 5),
    )
    backend.director.tool_guardrails = ToolCallGuardrailController(config)
    return web.json_response({"success": True, "config": {
        "warnings_enabled": config.warnings_enabled,
        "hard_stop_enabled": config.hard_stop_enabled,
    }})


async def handle_guardrails_reset(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    backend.director.tool_guardrails.reset_for_turn()
    return web.json_response({"success": True, "message": "Guardrails reset for new turn"})


# ============================================================
# Auth endpoints
# ============================================================

AUTH_PUBLIC_PATHS = {"/api/auth/login", "/api/auth/setup", "/api/auth/status", "/api/chat", "/api/status", "/api/capabilities", "/api/voice/transcribe", "/api/voice/speak", "/api/voice/status", "/api/voice/voices", "/api/hive/status", "/api/hive/send", "/api/hive/nodes", "/api/training/collect", "/api/training/pipeline", "/api/training/sft", "/api/training/dpo", "/api/training/jobs", "/api/training/job", "/api/training/cancel", "/api/training/report", "/api/training/datasets", "/api/training/ollama", "/api/trainer/prepare", "/api/trainer/launch", "/api/trainer/jobs", "/api/jarvis/status", "/api/jarvis/start", "/api/jarvis/stop"}


async def auth_middleware(app, handler):
    """Middleware que protege rutas con autenticacion"""
    auth: AuthManager = app.get("auth")
    if not auth:
        return handler

    async def middleware_handler(request):
        path = request.path

        # Rutas publicas (UI estática + API pública)
        if path in AUTH_PUBLIC_PATHS or path.startswith("/v1") or path == "/" or path.startswith("/ui"):
            return await handler(request)

        # WebSocket: permitir token en query param
        if path.startswith("/api/ws/"):
            token = request.query.get("token") or request.headers.get("Sec-WebSocket-Protocol", "")
            if token:
                user = auth.validate_token(token)
                if user:
                    request["auth_user"] = user
                    return await handler(request)
            # Si no hay token valido, permitir conexion pero el handler debe validar
            return await handler(request)

        # Verificar token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            user = auth.validate_token(token)
            if user:
                request["auth_user"] = user
                return await handler(request)

        # Verificar API key (fallback)
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            user = auth.validate_token(api_key)
            if user:
                request["auth_user"] = user
                return await handler(request)

        return web.json_response(
            {"error": "Authentication required", "hint": "POST /api/auth/login with username/password"},
            status=401,
        )

    return middleware_handler


async def handle_auth_setup(request: web.Request) -> web.Response:
    """Crea cuenta admin en primer uso"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    auth: AuthManager = request.app["auth"]

    if auth.has_users():
        return web.json_response({"error": "Users already exist. Use login instead."}, status=409)

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return web.json_response({"error": "username and password required"}, status=400)

    success, message = auth.create_user(username, password, role="admin")
    if success:
        return web.json_response({"success": True, "message": message, "username": username})
    else:
        return web.json_response({"error": message}, status=400)


async def handle_auth_login(request: web.Request) -> web.Response:
    """Login con username/password"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    auth: AuthManager = request.app["auth"]
    username = data.get("username", "")
    password = data.get("password", "")
    ip = request.remote or "unknown"

    if not username or not password:
        return web.json_response({"error": "username and password required"}, status=400)

    success, result = auth.login(username, password, ip)
    if success:
        return web.json_response(result)
    else:
        return web.json_response(result, status=401)


async def handle_auth_logout(request: web.Request) -> web.Response:
    """Logout invalida token"""
    auth: AuthManager = request.app["auth"]
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        auth.logout(auth_header[7:])
    return web.json_response({"success": True, "message": "Logged out"})


async def handle_auth_status(request: web.Request) -> web.Response:
    """Estado de autenticacion"""
    auth: AuthManager = request.app["auth"]
    return web.json_response(auth.get_status())


async def handle_auth_me(request: web.Request) -> web.Response:
    """Info del usuario actual"""
    user = request.get("auth_user")
    if not user:
        return web.json_response({"error": "Not authenticated"}, status=401)
    return web.json_response({
        "username": user.username,
        "role": user.role,
        "created_at": user.created_at,
        "last_login": user.last_login,
    })


async def handle_auth_change_password(request: web.Request) -> web.Response:
    """Cambia contrasena"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    user = request.get("auth_user")
    if not user:
        return web.json_response({"error": "Not authenticated"}, status=401)

    auth: AuthManager = request.app["auth"]
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")

    success, message = auth.change_password(user.username, old_password, new_password)
    if success:
        return web.json_response({"success": True, "message": message})
    else:
        return web.json_response({"error": message}, status=400)


# ─── Skills Pattern Handlers ────────────────────────────────────────────────

async def handle_agent_loop_run(request: web.Request) -> web.Response:
    """Run TDAO agent loop for complex multi-step tasks."""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
        task = data.get("task", "")
        context = data.get("context", "")
        result = await backend.director.run_agent_loop(task, context)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_voice_pipeline_stats(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        return web.json_response(backend.director.voice_pipeline.get_stats())
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_comfyui_submit(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
        prompt = data.get("prompt", "")
        workflow = data.get("workflow", "default")
        params = {k: v for k, v in data.items() if k not in ("prompt", "workflow")}
        job = await backend.director.comfyui.submit(prompt, workflow, **params)
        return web.json_response({"id": job.id, "status": job.status.value, "cache_key": job.cache_key})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_comfyui_jobs(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        status = request.query.get("status")
        return web.json_response({"jobs": backend.director.comfyui.list_jobs(status)})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_comfyui_stats(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        return web.json_response(backend.director.comfyui.get_stats())
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ─── Claude Headless Handler ──────────────────────────────────────────

async def handle_claude_headless(request: web.Request) -> web.Response:
    """Execute a prompt via Claude Code CLI headless (uses OAuth, no API key)."""
    try:
        from src.core.claude_headless import ClaudeHeadless
        data = await request.json()
        prompt = data.get("prompt", "")
        if not prompt:
            return web.json_response({"error": "prompt required"}, status=400)

        claude = ClaudeHeadless(
            max_turns=data.get("max_turns", 10),
            timeout=data.get("timeout", 300),
            allowed_tools=data.get("allowed_tools"),
        )
        result = await claude.run(
            prompt=prompt,
            cwd=data.get("cwd"),
        )
        return web.json_response({
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "duration_ms": result.duration_ms,
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ─── Autopsia Integration Handlers ──────────────────────────────────────────

async def handle_auto_commit(request: web.Request) -> web.Response:
    """Auto-commit with AI-generated message (Aider pattern)."""
    try:
        from src.core.auto_commit import auto_commit
        data = await request.json()
        result = await auto_commit(
            message=data.get("message"),
            files=data.get("files"),
            add_all=data.get("add_all", False),
        )
        return web.json_response(result or {"status": "nothing_to_commit"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_recent_commits(request: web.Request) -> web.Response:
    try:
        from src.core.auto_commit import get_recent_commits
        n = int(request.query.get("n", "10"))
        return web.json_response({"commits": get_recent_commits(n)})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_curator_curate(request: web.Request) -> web.Response:
    """Curate logs/memories."""
    try:
        from src.core.log_curator import LogCurator
        data = await request.json()
        curator = LogCurator()
        entries = data.get("entries", [])
        content_key = data.get("content_key", "content")
        source = data.get("source", "api")
        clean, stats = curator.curate_batch(entries, content_key=content_key, source=source)
        return web.json_response({"clean": clean, "stats": stats})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_curator_stats(request: web.Request) -> web.Response:
    try:
        from src.core.log_curator import LogCurator
        return web.json_response(LogCurator().get_stats())
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_curator_cleanup(request: web.Request) -> web.Response:
    try:
        from src.core.log_curator import LogCurator
        data = await request.json()
        days = data.get("days", 30)
        deleted = LogCurator().cleanup_old(days)
        return web.json_response({"deleted": deleted})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_trainer_prepare(request: web.Request) -> web.Response:
    try:
        from src.core.muon_trainer import MuonTrainer
        data = await request.json()
        trainer = MuonTrainer()
        result = await trainer.prepare_dataset(
            source_dir=data.get("source_dir", "~/.nexus/logs"),
            output_file=data.get("output_file", "/tmp/nexus_train.jsonl"),
        )
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_trainer_launch(request: web.Request) -> web.Response:
    try:
        from src.core.muon_trainer import MuonTrainer
        data = await request.json()
        trainer = MuonTrainer()
        result = await trainer.launch_finetune(
            dataset_path=data.get("dataset_path", "/tmp/nexus_train.jsonl"),
            config=data.get("config"),
        )
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_trainer_jobs(request: web.Request) -> web.Response:
    try:
        from src.core.muon_trainer import MuonTrainer
        return web.json_response({"jobs": MuonTrainer().list_jobs()})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ─── NexusTrainer API Handlers ──────────────────────────────────────────────

async def handle_training_collect(request: web.Request) -> web.Response:
    """Recolecta datos de entrenamiento de todas las fuentes"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json() if request.can_read_body else {}
        smoltalk_dir = data.get("smoltalk_dir", "")
        smoltalk_path = Path(smoltalk_dir) if smoltalk_dir and Path(smoltalk_dir).is_dir() else None
        report = backend.director.data_collector.collect_all(smoltalk_dir=smoltalk_path)

        # Exportar datasets
        sft_path = backend.director.data_collector.export_sft()
        dpo_path = backend.director.data_collector.export_dpo()
        cat_dir = backend.director.data_collector.export_by_category()

        return web.json_response({
            "success": True,
            "report": report,
            "datasets": {
                "sft": str(sft_path),
                "dpo": str(dpo_path),
                "by_category": str(cat_dir),
            },
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_training_sft(request: web.Request) -> web.Response:
    """Ejecuta entrenamiento SFT"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
        dataset_path = data.get("dataset_path", "")
        if not dataset_path:
            return web.json_response({"error": "dataset_path required"}, status=400)

        job = backend.director.nexus_trainer.create_job("sft", dataset_path, data.get("config"))
        result = await backend.director.nexus_trainer.run_sft(job, data.get("lora_config"))
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_training_dpo(request: web.Request) -> web.Response:
    """Ejecuta entrenamiento DPO"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
        dataset_path = data.get("dataset_path", "")
        if not dataset_path:
            return web.json_response({"error": "dataset_path required"}, status=400)

        job = backend.director.nexus_trainer.create_job("dpo", dataset_path, data.get("config"))
        result = await backend.director.nexus_trainer.run_dpo(job, data.get("dpo_config"))
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_training_pipeline(request: web.Request) -> web.Response:
    """Ejecuta pipeline completo: SFT -> DPO -> Ollama"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
        sft_dataset = data.get("sft_dataset", "")
        dpo_dataset = data.get("dpo_dataset")
        if not sft_dataset:
            return web.json_response({"error": "sft_dataset required"}, status=400)

        result = await backend.director.nexus_trainer.run_full_pipeline(
            sft_dataset=sft_dataset,
            dpo_dataset=dpo_dataset,
            config=data.get("config"),
        )
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_training_jobs(request: web.Request) -> web.Response:
    """Lista todos los jobs de entrenamiento"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        status = request.query.get("status")
        jobs = backend.director.nexus_trainer.list_jobs(status)
        return web.json_response({"jobs": jobs})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_training_job(request: web.Request) -> web.Response:
    """Obtiene detalles de un job especifico"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        job_id = request.match_info["job_id"]
        job = backend.director.nexus_trainer.get_job(job_id)
        if job:
            return web.json_response(job)
        return web.json_response({"error": "Job not found"}, status=404)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_training_cancel(request: web.Request) -> web.Response:
    """Cancela un job en ejecucion"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        job_id = request.match_info["job_id"]
        result = backend.director.nexus_trainer.cancel_job(job_id)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_training_ollama_create(request: web.Request) -> web.Response:
    """Crea un modelo en Ollama desde entrenamiento completado"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
        job_id = data.get("job_id", "")
        model_name = data.get("model_name", "")
        if not job_id or not model_name:
            return web.json_response({"error": "job_id and model_name required"}, status=400)

        result = backend.director.nexus_trainer.create_ollama_model(job_id, model_name)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_training_report(request: web.Request) -> web.Response:
    """Genera reporte de todos los entrenamientos"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        report = backend.director.nexus_trainer.get_training_report()
        return web.json_response(report)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_training_datasets(request: web.Request) -> web.Response:
    """Lista datasets disponibles para entrenamiento"""
    try:
        from src.core.data_collector import DATA_DIR
        datasets = []
        if DATA_DIR.exists():
            for f in DATA_DIR.glob("*.jsonl"):
                datasets.append({
                    "name": f.name,
                    "path": str(f),
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                })
        return web.json_response({"datasets": datasets, "data_dir": str(DATA_DIR)})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


def create_app(backend: SuperNEXUSBackend) -> web.Application:
    auth = AuthManager()
    app = web.Application(middlewares=[cors_middleware, auth_middleware])
    app["backend"] = backend
    app["auth"] = auth

    # Core routes
    app.router.add_get("/api/status", handle_status)
    app.router.add_get("/api/capabilities", handle_capabilities)
    app.router.add_get("/api/projects", handle_projects)
    app.router.add_get("/api/gems", handle_gems)
    app.router.add_get("/api/knowledge/graph", handle_knowledge_graph)
    app.router.add_get("/api/tailscale/nodes", handle_tailscale_nodes)
    app.router.add_post("/api/chat", handle_chat)
    app.router.add_get("/api/ws/chat", handle_chat_ws)
    app.router.add_post("/api/memory/search", handle_memory_search)
    app.router.add_post("/api/learn", handle_learn)

    # OpenAI-compatible routes (for OpenWebUI and other clients)
    app.router.add_get("/v1", handle_openai_health)
    app.router.add_get("/v1/models", handle_openai_models)
    app.router.add_post("/v1/chat/completions", handle_openai_chat_completions)

    # AI Tools routes
    app.router.add_get("/api/ai/tools", handle_ai_tools_list)
    app.router.add_get("/api/ai/tools/stats", handle_ai_tools_stats)
    app.router.add_post("/api/ai/tools/execute", handle_ai_tools_execute)
    app.router.add_post("/api/ai/tools/select", handle_ai_tools_select)

    # OpenCode-style tools
    app.router.add_get("/api/tools/fetch", handle_fetch_url)
    app.router.add_get("/api/tools/sourcegraph", handle_sourcegraph_search)

    # Custom Commands (OpenCode-style)
    app.router.add_get("/api/commands", handle_custom_commands_list)
    app.router.add_post("/api/commands/execute", handle_custom_command_execute)

    # Auto-Compact
    app.router.add_get("/api/conversation", handle_conversation_history)
    app.router.add_post("/api/compact", handle_compact_conversation)

    # PC Control routes
    app.router.add_get("/api/pc/screenshot", handle_screenshot)
    app.router.add_post("/api/pc/mouse/click", handle_mouse_click)
    app.router.add_post("/api/pc/mouse/move", handle_mouse_move)
    app.router.add_post("/api/pc/type", handle_type_text)
    app.router.add_post("/api/pc/key", handle_key_press)
    app.router.add_get("/api/pc/vision/describe", handle_vision_describe)
    app.router.add_post("/api/pc/vision/instruct", handle_vision_instruction)
    app.router.add_post("/api/vision/process", handle_vision_process)
    app.router.add_get("/api/vision/providers", handle_vision_providers)
    app.router.add_get("/api/pc/status", handle_pc_status)

    # Voice routes
    app.router.add_post("/api/voice/speak", handle_tts_speak)
    app.router.add_get("/api/voice/voices", handle_tts_voices)
    app.router.add_post("/api/voice/transcribe", handle_voice_transcribe)
    app.router.add_get("/api/voice/listen", handle_voice_listen)
    app.router.add_get("/api/voice/status", handle_voice_status)
    app.router.add_get("/api/voice/personalities", handle_voice_personalities)
    app.router.add_post("/api/voice/set-personality", handle_voice_set_personality)
    app.router.add_post("/api/voice/set-voice", handle_voice_set_voice)
    app.router.add_post("/api/voice/route", handle_voice_route)

    # JARVIS routes
    app.router.add_get("/api/jarvis/status", handle_jarvis_status)
    app.router.add_post("/api/jarvis/start", handle_jarvis_start)
    app.router.add_post("/api/jarvis/stop", handle_jarvis_stop)

    # Brain routes
    app.router.add_get("/api/brain/stats", handle_brain_stats)
    app.router.add_get("/api/brain/preferences", handle_brain_preferences)
    app.router.add_get("/api/brain/prompt", handle_brain_prompt)
    app.router.add_post("/api/brain/learn", handle_brain_learn)
    app.router.add_get("/api/brain/knowledge", handle_brain_knowledge)
    app.router.add_get("/api/brain/export", handle_brain_export)

    # Integration routes
    app.router.add_get("/api/codex/status", handle_codex_status)
    app.router.add_post("/api/codex/run", handle_codex_run)
    app.router.add_get("/api/rcon/servers", handle_rcon_servers)
    app.router.add_post("/api/rcon/command", handle_rcon_command)
    app.router.add_get("/api/multimedia/status", handle_multimedia_status)
    app.router.add_get("/api/multimedia/scenes", handle_multimedia_scenes)
    app.router.add_get("/api/scheduler/status", handle_scheduler_status)
    app.router.add_post("/api/scheduler/add", handle_scheduler_add)
    app.router.add_get("/api/guardian/status", handle_guardian_status)
    app.router.add_post("/api/guardian/audit", handle_guardian_audit)

    # Multimedia AI routes (Design, Music, Prompter, Producer)
    app.router.add_post("/api/design/generate", handle_design_generate)
    app.router.add_post("/api/design/storyboard", handle_design_storyboard)
    app.router.add_post("/api/music/generate", handle_music_generate)
    app.router.add_post("/api/prompt/optimize", handle_prompt_optimize)
    app.router.add_post("/api/producer/campaign", handle_producer_campaign)
    app.router.add_post("/api/producer/schedule", handle_producer_schedule)

    # Optimization routes
    app.router.add_get("/api/system/stats", handle_system_stats)
    app.router.add_get("/api/system/safe", handle_safe_to_run)
    app.router.add_post("/api/token/optimize", handle_token_optimize)
    app.router.add_get("/api/token/report", handle_token_report)
    app.router.add_post("/api/token/compress", handle_token_compress)

    # Safety routes
    app.router.add_get("/api/safety/status", handle_safety_status)
    app.router.add_post("/api/safety/reset", handle_safety_reset)
    app.router.add_post("/api/safety/configure", handle_safety_configure)

    # F15: Doctor Command
    app.router.add_get("/api/doctor", handle_doctor)
    app.router.add_post("/api/doctor/run", handle_doctor_run)

    # F19: Custom Commands
    app.router.add_get("/api/commands", handle_custom_commands_list)
    app.router.add_get("/api/commands/{name}", handle_custom_command_get)
    app.router.add_post("/api/commands", handle_custom_command_create)
    app.router.add_post("/api/commands/{name}/execute", handle_custom_command_execute)
    app.router.add_delete("/api/commands/{name}", handle_custom_command_delete)

    # F1: Session Management
    app.router.add_get("/api/sessions", handle_sessions_list)
    app.router.add_get("/api/sessions/{id}", handle_session_get)
    app.router.add_post("/api/sessions", handle_session_create)
    app.router.add_post("/api/sessions/{id}/compact", handle_session_compact)
    app.router.add_get("/api/sessions/{id}/pressure", handle_session_pressure)

    # F5: Token Budget
    app.router.add_get("/api/budget", handle_budget_status)
    app.router.add_post("/api/budget/reset", handle_budget_reset)
    app.router.add_post("/api/budget/configure", handle_budget_configure)

    # F2: DAG / Goal Decomposition
    app.router.add_post("/api/dag/decompose", handle_dag_decompose)
    app.router.add_post("/api/dag/{id}/execute", handle_dag_execute)
    app.router.add_get("/api/dag/{id}", handle_dag_get)
    app.router.add_get("/api/dag", handle_dag_list)

    # Orchestrate: descomposición LLM + ejecución TaskQueue + síntesis
    app.router.add_post("/api/orchestrate", handle_orchestrate)
    app.router.add_get("/api/orchestrate/status", handle_orchestrate_status)

    # DevLoop: 7-Phase Development Loop (gstack pattern)
    app.router.add_post("/api/devloop/run", handle_devloop_run)
    app.router.add_get("/api/devloop/status", handle_devloop_status)

    # Conductor: Parallel Worktree Coordinator (gstack pattern)
    app.router.add_post("/api/conductor/spawn", handle_conductor_spawn)
    app.router.add_post("/api/conductor/merge", handle_conductor_merge)
    app.router.add_post("/api/conductor/cleanup", handle_conductor_cleanup)
    app.router.add_get("/api/conductor/status", handle_conductor_status)

    # F1: Director Soberano
    app.router.add_post("/api/director/execute", handle_sovereign_execute)
    app.router.add_get("/api/director/decision-engine", handle_decision_engine_status)
    app.router.add_get("/api/director/sub-directors", handle_sub_directors_status)
    app.router.add_get("/api/director/external-agents", handle_external_agents_status)
    app.router.add_post("/api/director/external-agents/register", handle_register_external_agent)
    app.router.add_get("/api/director/learning", handle_learning_status)
    app.router.add_get("/api/director/commands", handle_command_history)

    # F2: Memory Hardening
    app.router.add_get("/api/memory/triage", handle_memory_triage_status)
    app.router.add_post("/api/memory/triage/evaluate", handle_triage_evaluate)
    app.router.add_get("/api/memory/pointers", handle_pointer_status)
    app.router.add_post("/api/memory/dream", handle_dream_consolidate)

    # F3: Protocol Stack
    app.router.add_get("/api/protocols/status", handle_protocol_status)
    app.router.add_post("/api/protocols/acp/send", handle_acp_send)
    app.router.add_get("/.well-known/agent.json", handle_agent_card)
    app.router.add_post("/api/a2a/tasks", handle_a2a_create_task)
    app.router.add_get("/api/a2a/tasks/{task_id}", handle_a2a_get_task)

    # F4: Skills Marketplace
    app.router.add_get("/api/skills/marketplace", handle_skills_marketplace)
    app.router.add_post("/api/skills/install", handle_skills_install)
    app.router.add_post("/api/skills/publish", handle_skills_publish)
    app.router.add_post("/api/skills/rate", handle_skills_rate)

    # F6: Code Absorption
    app.router.add_post("/api/absorb/repo", handle_absorb_repo)
    app.router.add_get("/api/absorb/status", handle_absorb_status)

    # F7: Production Hardening
    app.router.add_get("/api/health", handle_health_circuit_breakers)
    app.router.add_get("/api/tokens/usage", handle_token_usage)

    # Actor System (Sprint 5)
    app.router.add_get("/api/actors", handle_actors_list)
    app.router.add_post("/api/actors/route", handle_actors_route)
    app.router.add_post("/api/actors/model-select", handle_actors_model_select)
    app.router.add_post("/api/actors/{actor_id}/tell", handle_actors_tell)

    # F3: Checkpoints
    app.router.add_get("/api/checkpoints", handle_checkpoints_list)
    app.router.add_get("/api/checkpoints/incomplete", handle_checkpoints_incomplete)
    app.router.add_post("/api/checkpoints/{run_id}/save", handle_checkpoint_save)

    # F8: Recipes
    app.router.add_get("/api/recipes", handle_recipes_list)
    app.router.add_post("/api/recipes/load", handle_recipe_load)
    app.router.add_post("/api/recipes/{name}/execute", handle_recipe_execute)

    # F6: Graph Evolution
    app.router.add_get("/api/graph/status", handle_graph_status)

    # F7: Approval Gates
    app.router.add_get("/api/approvals", handle_approvals_list)
    app.router.add_post("/api/approvals/request", handle_approval_request)
    app.router.add_post("/api/approvals/{id}/respond", handle_approval_respond)

    # F9: Knowledge Vault
    app.router.add_get("/api/vault", handle_vault_list)
    app.router.add_post("/api/vault", handle_vault_add)
    app.router.add_get("/api/vault/search", handle_vault_search)
    app.router.add_get("/api/vault/{id}", handle_vault_get)

    # F11: Risk Assessment
    app.router.add_get("/api/risk", handle_risk_summary)
    app.router.add_post("/api/risk/assess", handle_risk_assess)

    # F14: Memory Health
    app.router.add_get("/api/memory/health", handle_memory_health)

    # F17: Tool Monitoring
    app.router.add_get("/api/tools/monitor", handle_tool_monitor)
    app.router.add_post("/api/tools/record", handle_tool_record)

    # F13: Collaboration Hall
    app.router.add_post("/api/hall/room", handle_hall_create_room)
    app.router.add_post("/api/hall/{id}/event", handle_hall_add_event)
    app.router.add_get("/api/hall/{id}/timeline", handle_hall_timeline)
    app.router.add_get("/api/hall", handle_hall_list)

    # F18: Retry with Backoff
    app.router.add_get("/api/retry/status", handle_retry_status)
    app.router.add_post("/api/retry/configure", handle_retry_configure)

    # F20: Live Notes
    app.router.add_post("/api/notes", handle_live_note_create)
    app.router.add_get("/api/notes", handle_live_notes_list)
    app.router.add_post("/api/notes/{id}/update", handle_live_note_update)
    app.router.add_get("/api/notes/backlinks", handle_live_notes_backlinks)
    app.router.add_get("/api/notes/graph", handle_live_notes_graph)
    app.router.add_get("/api/notes/search", handle_live_notes_search)

    # F21: Background Review Daemon
    app.router.add_get("/api/review/status", handle_review_status)
    app.router.add_post("/api/review/configure", handle_review_configure)
    app.router.add_post("/api/review/trigger", handle_review_trigger)

    # F22: Tool Call Guardrails
    app.router.add_get("/api/guardrails/status", handle_guardrails_status)
    app.router.add_post("/api/guardrails/configure", handle_guardrails_configure)
    app.router.add_post("/api/guardrails/reset", handle_guardrails_reset)

    # NexusHive routes (comunicación en tiempo real)
    app.router.add_get("/api/hive/status", handle_hive_status)
    app.router.add_post("/api/hive/send", handle_hive_send_command)
    app.router.add_get("/api/hive/nodes", handle_hive_nodes)

    # Filesystem routes (Editor UI)
    app.router.add_post("/api/fs/list", handle_fs_list)
    app.router.add_post("/api/fs/read", handle_fs_read)
    app.router.add_post("/api/fs/write", handle_fs_write)
    app.router.add_post("/api/fs/exec", handle_fs_exec)

    # MCP Bridge routes
    app.router.add_get("/api/mcp/tools", handle_mcp_tools)
    app.router.add_post("/api/mcp/execute", handle_mcp_execute)
    app.router.add_post("/api/mcp/pc2", handle_mcp_execute_on_pc2)
    app.router.add_post("/api/mcp/task", handle_mcp_send_task)

    # Auth routes (public - no middleware protection)
    app.router.add_post("/api/auth/setup", handle_auth_setup)
    app.router.add_post("/api/auth/login", handle_auth_login)
    app.router.add_post("/api/auth/logout", handle_auth_logout)
    app.router.add_get("/api/auth/status", handle_auth_status)
    app.router.add_get("/api/auth/me", handle_auth_me)
    app.router.add_post("/api/auth/change-password", handle_auth_change_password)

    # Skills pattern routes (agent loop, voice pipeline, comfyui)
    app.router.add_post("/api/agent-loop/run", handle_agent_loop_run)
    app.router.add_get("/api/voice-pipeline/stats", handle_voice_pipeline_stats)
    app.router.add_post("/api/comfyui/submit", handle_comfyui_submit)
    app.router.add_get("/api/comfyui/jobs", handle_comfyui_jobs)
    app.router.add_get("/api/comfyui/stats", handle_comfyui_stats)
    app.router.add_post("/api/claude/run", handle_claude_headless)

    # Autopsia integration routes (auto-commit, log curator, muon trainer)
    app.router.add_post("/api/autocommit", handle_auto_commit)
    app.router.add_get("/api/autocommit/recent", handle_recent_commits)
    app.router.add_post("/api/curator/curate", handle_curator_curate)
    app.router.add_get("/api/curator/stats", handle_curator_stats)
    app.router.add_post("/api/curator/cleanup", handle_curator_cleanup)
    app.router.add_post("/api/trainer/prepare", handle_trainer_prepare)
    app.router.add_post("/api/trainer/launch", handle_trainer_launch)
    app.router.add_get("/api/trainer/jobs", handle_trainer_jobs)

    # NexusTrainer routes (training pipeline)
    app.router.add_post("/api/training/collect", handle_training_collect)
    app.router.add_post("/api/training/sft", handle_training_sft)
    app.router.add_post("/api/training/dpo", handle_training_dpo)
    app.router.add_post("/api/training/pipeline", handle_training_pipeline)
    app.router.add_get("/api/training/jobs", handle_training_jobs)
    app.router.add_get("/api/training/jobs/{job_id}", handle_training_job)
    app.router.add_post("/api/training/jobs/{job_id}/cancel", handle_training_cancel)
    app.router.add_post("/api/training/ollama/create", handle_training_ollama_create)
    app.router.add_get("/api/training/report", handle_training_report)
    app.router.add_get("/api/training/datasets", handle_training_datasets)

    # Improvements integration routes (patterns, skills, etc)
    try:
        from src.improvements.integration import add_new_routes
        add_new_routes(app, backend)
    except Exception as e:
        logger.warning(f"Could not add improvement routes (non-critical): {e}")

    # Static files (UI)
    ui_dist_path = Path(__file__).parent.parent.parent / "ui" / "dist"
    if ui_dist_path.exists() and (ui_dist_path / "index.html").exists():
        async def handle_ui_root(request: web.Request) -> web.Response:
            return web.FileResponse(ui_dist_path / "index.html")

        # SPA fallback: any /ui/* path serves index.html (client-side routing)
        async def handle_ui_spa(request: web.Request) -> web.Response:
            path = request.match_info.get("path", "")
            file = ui_dist_path / path
            if file.exists() and file.is_file():
                return web.FileResponse(file)
            return web.FileResponse(ui_dist_path / "index.html")

        app.router.add_get("/", handle_ui_root)
        app.router.add_get("/ui/{path:.*}", handle_ui_spa)
        app.router.add_static("/ui/assets/", ui_dist_path / "assets", name="ui_assets")
        logger.info(f"Serving UI from {ui_dist_path}")

    return app


async def run_server(port: int = 9000):
    """Inicia el servidor API"""
    backend = SuperNEXUSBackend()
    await backend.initialize()

    app = create_app(backend)
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info(f"NEXUS API server running on port {port}")
    auth_status = backend.director.ai_tools  # dummy access to ensure init
    auth = app["auth"]
    if not auth.has_users():
        print(f"  [!] FIRST RUN: Create admin account at http://localhost:{port}/api/auth/setup")
        print(f'      POST {{"username": "admin", "password": "secure_password"}}')
    else:
        print(f"  Auth: http://localhost:{port}/api/auth/login")
    print(f"  API: http://localhost:{port}")
    print(f"  Status: http://localhost:{port}/api/status")
    print(f"  Chat:  POST http://localhost:{port}/api/chat")
    print()

    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Shutting down API server...")
        await backend.close()
        await runner.cleanup()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    asyncio.run(run_server(port))
