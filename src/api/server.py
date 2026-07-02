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
import time
import base64
import shlex
import webbrowser
import shutil
import requests
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path
import aiohttp
from aiohttp import web

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.director import DirectorNexus
from src.core.connectivity import ConnectivityLayer
from src.core.ollama import OllamaClient, LLMRouter
from src.core.event_bus import EventBus
from src.core.realtime_hub import RealtimeHub
from src.core.event_store import EventStore
from src.core import nexus_config
from src.core.communication import CommunicationFlow, AgentCapability
from src.core.runtime import AgentRuntime
from src.core.doctor import Doctor
from src.core.custom_commands import CustomCommandManager
from src.services.research_service import ResearchService
from src.core.acp_protocol import ACPMessage, ACPMessageType
from src.core.skill_marketplace import SkillManifest
from src.memory.neural_patterns import NeuralPatterns
from src.memory.rag_memory import RAGMemory
from src.memory.knowledge_graph import KnowledgeGraph
from src.memory.qa_loop import QALoop
from src.memory.active_learning import ActiveLearningLoop
# PC2Bridge removed for distro
from src.bridges.tailscale_bridge import TailscaleBridge
from src.bridges.mcp_bridge_server import send_message, read_messages, brain_remember, brain_recall, brain_stats, memory_set, memory_get, nexus_status, list_nodes, execute_remote_task, execute_on_remote_node, list_skills, load_skill, load_skill_section, send_task_to_antigravity, get_system_info, add_finding, add_decision, read_cloud, check_permissions, router_select, router_stats, self_learning_status, memory_hierarchical_stats, memory_hierarchical_store, memory_hierarchical_search, retrieval_search, add_observation, search_observations, get_observation, add_task_finding, list_findings, memory_stats, optimize_prompt, select_model, token_report, system_resources, agent_cu_execute, codebase_context, codebase_query, sandbox_execute
from src.core.nexus_hive import NexusHive
from src.agents.scholar_gem import ScholarGem
from src.agents.sage_gem import SageGem
from src.agents.biblioteca_gem import BibliotecaGem

try:
    from src.core.response_builder import ResponseBuilder
except ImportError:
    ResponseBuilder = None

# Modulos portados de NEXUS_MASTER
from src.control.computer_control import ComputerControl
from src.control.pc_controller import PCController

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
from src.core.extension_pipeline import ExtensionPipeline, HookPhase, HookContext
from src.brain.data_collector import DataCollector, DataCollectorConfig
from src.optimization.api_safety import SafetyManager
from src.security.guardrails import NEXUSGuardrails
from src.security.auth import AuthManager
from src.security.permission_manager import manager as permission_manager
from src.optimization.resource_monitor import get_system_stats, is_safe_to_run_local
from src.core.rate_limiter import rate_limit_middleware
from src.core.voice_engine import VoiceEngine, get_engine as get_voice_engine
from src.core.swarm_memory import SwarmMemory
from src.core.swarm_lifecycle import SwarmLifecycle
from src.core.connection_manager import load_connections, get_connection, add_connection, remove_connection, check_health, check_all_connections, sync_to_hive_agents

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


def _scan_ollama_manifests() -> list[dict]:
    """Scan Ollama manifests directory for all available models."""
    base = Path(os.environ.get("USERPROFILE", "")) / ".ollama" / "models" / "manifests" / "registry.ollama.ai" / "library"
    if not base.exists():
        return []
    models = []
    for model_dir in base.iterdir():
        if model_dir.is_dir():
            for tag_file in model_dir.iterdir():
                model_name = f"{model_dir.name}:{tag_file.name}"
                try:
                    data = json.loads(tag_file.read_text())
                    size_bytes = sum(layer.get("size", 0) for layer in data.get("layers", []))
                    models.append({
                        "name": model_name,
                        "size_gb": round(size_bytes / 1e9, 2),
                        "modified": "",
                        "family": "",
                        "param_size": "",
                        "source": "manifest",
                    })
                except Exception:
                    pass
    return models


def _merge_ollama_models(api_models: list[dict], manifest_models: list[dict]) -> list[dict]:
    """Merge manifest models with API models, deduplicating by name."""
    seen = set()
    merged = []
    for m in api_models:
        seen.add(m["name"])
        merged.append(m)
    for m in manifest_models:
        if m["name"] not in seen:
            seen.add(m["name"])
            merged.append(m)
    merged.sort(key=lambda x: x["name"])
    return merged


async def _get_ollama_models_merged() -> dict:
    """Fetch Ollama models from API and manifests, merge, return dict for status."""
    return await _fetch_ollama_models()


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
        # v3 architecture: NexusApp container for services
        # Services se van migrando aca de a uno (Fases 4+ del refactor v3).
        # Por ahora coexiste con la inicializacion legacy del backend.
        from src.core.nexus import NexusApp
        self.app = NexusApp(project="default")

        self.director = DirectorNexus(project="default")
        self._last_msg_id = 0
        self._busy = False

        self._init_core()
        self._init_memory()
        self._init_agents()
        self._init_voice()
        self._init_integrations()
        self._init_optimization()


    # ── Init groups ──────────────────────────────────────────────

    def _init_core(self):
        self.connectivity = ConnectivityLayer()
        self.ollama = OllamaClient()
        self.llm_router = LLMRouter(self.ollama)
        self.event_store = EventStore()
        self.realtime_hub = RealtimeHub(event_store=self.event_store)
        self.event_bus = EventBus(hub=self.realtime_hub)
        self.comm_flow = CommunicationFlow(self.event_bus)
        self.runtime = AgentRuntime(self.event_bus)
        # self.pc2 = self._safe_init("PC2Bridge", PC2Bridge)  # REMOTE
        self.tailscale = self._safe_init("TailscaleBridge", TailscaleBridge)
        self.nexus_hive = self._safe_init("NexusHive", NexusHive)
        self.compare_mode = None  # Inicializado bajo demanda en handle_compare_start
        self.mcp_tools = {
            # "execute_on_pc2": execute_on_pc2,  # REMOTE
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
            "brain_stats": brain_stats,
            "execute_on_remote_node": execute_on_remote_node,
            "load_skill_section": load_skill_section,
            "add_observation": add_observation,
            "search_observations": search_observations,
            "get_observation": get_observation,
            "add_task_finding": add_task_finding,
            "list_findings": list_findings,
            "memory_stats": memory_stats,
            "optimize_prompt": optimize_prompt,
            "select_model": select_model,
            "token_report": token_report,
            "system_resources": system_resources,
            "agent_cu_execute": agent_cu_execute,
            "codebase_context": codebase_context,
            "codebase_query": codebase_query,
            "sandbox_execute": sandbox_execute,
        }

    def _init_memory(self):
        self.neural = self._safe_init("NeuralPatterns", NeuralPatterns)
        self.rag = self._safe_init("RAGMemory", RAGMemory)
        self.kg = self._safe_init("KnowledgeGraph", KnowledgeGraph)
        self.qa = self._safe_init("QALoop", QALoop)
        self.learning = self._safe_init("ActiveLearningLoop", ActiveLearningLoop)
        self.cerebro = self._safe_init("Cerebro", Cerebro)
        self.swarm_memory = self._safe_init("SwarmMemory", SwarmMemory)
        self.swarm_lifecycle = self._safe_init("SwarmLifecycle", SwarmLifecycle)

    def _init_agents(self):
        self.scholar = self._safe_init("ScholarGem", ScholarGem)
        self.sage = self._safe_init("SageGem", SageGem)
        self.biblioteca = self._safe_init("BibliotecaGem", BibliotecaGem)

    def _init_voice(self):
        try:
            self.voice = get_voice_engine()
            if self.voice.available:
                logger.info(f"Voice engine initialized: {self.voice.voice_name} ({self.voice.sample_rate}Hz)")
            else:
                logger.warning("Voice engine not available")
                self.voice = None
        except Exception as e:
            logger.warning(f"Voice engine init failed: {e}")
            self.voice = None

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

        # Sync connections.json -> hive_agents.json so Hive Hub has agents
        try:
            sync_to_hive_agents()
        except Exception as e:
            logger.warning(f"Hive agents sync failed (non-critical): {e}")

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
        asyncio.create_task(self._start_provider_discovery(), name="provider-discovery")

        # Wire up director with brain modules
        if self.director:
            self.director.cerebro = self.cerebro
            if hasattr(self.director, 'review_daemon'):
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
        asyncio.create_task(self._memory_maintenance_loop())
        asyncio.create_task(self._graph_regenerator())

        # Background workers: disabled by default — enable with NEXUS_WORKERS=true
        # Reason: Windows ProactorEventLoop stalls with 50+ tasks doing concurrent I/O.
        if os.environ.get("NEXUS_WORKERS", "").lower() == "true":
            if self.director and hasattr(self.director, 'worker_manager'):
                async def _start_bg():
                    await asyncio.sleep(5)
                    await self.director.start_background_workers()
                asyncio.create_task(_start_bg())
        else:
            logger.info("Background workers disabled (set NEXUS_WORKERS=true to enable)")

        logger.info("SuperNEXUS backend initialized")

    async def _deferred_self_model_init(self):
        """Initialize self-model in background (non-blocking)"""
        try:
            await self.director.initialize_async()
        except Exception as e:
            logger.warning(f"Self-model initialization failed: {e}")

    async def _start_provider_discovery(self):
        """Background provider discovery — refreshes every 30s."""
        try:
            from src.core.provider_discovery import discover_providers
            await discover_providers(force=True)
            logger.info("Provider discovery: initial probe complete")
        except Exception as e:
            logger.debug(f"Provider discovery initial probe: {e}")

    async def _graph_regenerator(self):
        """Regenera static/graph.json al startup y cada 5 min."""
        import subprocess
        graph_script = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "graph_scanner.py")
        graph_script = os.path.normpath(graph_script)
        if not os.path.exists(graph_script):
            logger.debug(f"Graph scanner not found: {graph_script}")
            return

        async def _run_graph_scan():
            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, graph_script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
                if proc.returncode == 0:
                    out = stdout.decode(errors="ignore").strip()
                    logger.info(f"Graph regenerated: {out}")
                else:
                    logger.debug(f"Graph scan failed: {stderr.decode(errors='ignore')[:200]}")
            except Exception as e:
                logger.debug(f"Graph regen error: {e}")

        # Initial scan on startup
        await asyncio.sleep(3)
        await _run_graph_scan()

        # Periodic refresh every 5 minutes
        while True:
            await asyncio.sleep(300)
            await _run_graph_scan()

    async def _deferred_pc2_connect(self):
        pc2 = getattr(self, "pc2", None)
        if not pc2:
            return
        try:
            await pc2.connect()
        except Exception as e:
            logger.debug(f"PC2 deferred connect: {e}")

    async def _deferred_hive_connect(self):
        """Inicia NexusHive, RealtimeHub y registra handlers por defecto"""
        try:
            await self.realtime_hub.start()
        except Exception as e:
            logger.debug(f"RealtimeHub deferred start: {e}")

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
        pc2 = getattr(self, "pc2", None)
        if not pc2:
            return {"status": "error", "error": "Remote bridge not available"}
        return await pc2.execute_remote(command)

    async def _hive_get_system_info(self, **kwargs):
        """Handler para obtener información del sistema"""
        pc2 = getattr(self, "pc2", None)
        if not pc2:
            return {"status": "error", "error": "Remote bridge not available"}
        return await pc2.get_system_info()

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

    async def _memory_maintenance_loop(self):
        """Background loop: memory_maintenance cada 6h."""
        while True:
            try:
                await asyncio.sleep(21600)
                from src.agents.sage_gem import SageGem
                sage = SageGem()
                result = sage.run_full_maintenance()
                total = sum(v for k, v in result.items() if isinstance(v, int))
                if total:
                    logger.info(f"Auto-maintenance: {result}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Auto-maintenance error: {e}")
                await asyncio.sleep(3600)

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
        session_id: Optional[str] = None,
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

        # Detectar si hay imágenes
        has_images = images and len(images) > 0
        if has_images:
            logger.info(f"Processing {len(images)} image(s)")
            vision_result = await self._process_with_vision(message, images)
            if vision_result.get("success"):
                return {
                    "reply": vision_result.get("content", ""),
                    "gem_used": "vision",
                    "engines": ["nexus_master"],
                    "vision_source": vision_result.get("source", "unknown"),
                }
            message = f"[Imagen adjunta: {vision_result.get('img_info', {}).get('format', 'desconocido')} {vision_result.get('img_info', {}).get('width', '?')}x{vision_result.get('img_info', {}).get('height', '?')}px]\n\n{message}"
            logger.warning("Vision model unavailable, using text-only fallback")

        classification = await self.director.classify_task(message, session_id=session_id or "")
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
            
            # Detectar busqueda en la web (PRIORIDAD sobre grep para evitar tratar la query como path)
            elif any(kw in msg_lower for kw in [
                "busca en la web", "buscar en la web", "busca en internet", "buscar en internet",
                "busca en google", "buscar en google", "search the web", "google ",
                "investiga sobre", "investiga ", "que sabes de", "informacion sobre",
                "información sobre", "noticias sobre", "ultimas noticias", "últimas noticias",
                "novedades de", "novedades sobre", "que hay de nuevo", "search online",
            ]):
                logger.info("Detected web_search intent")
                # Extract clean query: drop the trigger phrase, keep the rest
                query = msg_lower
                for trigger in [
                    "busca en la web", "buscar en la web", "busca en internet", "buscar en internet",
                    "busca en google", "buscar en google", "search the web", "investiga sobre",
                    "investiga", "que sabes de", "informacion sobre", "información sobre",
                    "noticias sobre", "ultimas noticias", "últimas noticias", "novedades de",
                    "novedades sobre", "que hay de nuevo sobre", "search online", "google",
                ]:
                    query = query.replace(trigger, "").strip()
                query = query.strip(" :,.?!")
                if query:
                    try:
                        auto_tool_result = await self.director.ai_tools.execute_tool_call(
                            "web_search", {"query": query, "max_results": 5}
                        )
                    except Exception as e:
                        logger.warning(f"web_search failed: {e}")
                        auto_tool_result = {"success": False, "error": str(e), "tool": "web_search"}

            # Detectar intencion de buscar contenido (grep) — solo si NO matched web search
            elif any(kw in msg_lower for kw in ["grep", "donde dice", "buscar texto en archivo", "find string in file"]):
                logger.info("Detected grep_content intent")
                pattern_match = re.search(r'["\']([^"\']+)["\']', msg_lower)
                if not pattern_match:
                    pattern_match = re.search(r'(?:buscar|busca|dice)\s+(?:en\s+\S+\s+)?["\']?([^"\']+)["\']?', msg_lower)
                pattern = pattern_match.group(1) if pattern_match else ""
                path_match = re.search(r'(?:en|de|del)\s+["\']?([^"\']+\.[a-z]+)["\']?', msg_lower)
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
            elif any(kw in msg_lower for kw in ["lista", "listar", "list", "ls ", "archivos del directorio", "contenido de", "que hay en", "carpetas de", "carpeta de", "muestra las", "muestra los", "que tiene"]):
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

        # URL auto-persist — Scholar investiga → Sage persiste → Cerebro
        url_match = re.search(r'https?://[^\s"\']+', message)
        _url_ingested = False
        if url_match and self.cerebro:
            try:
                from src.agents.scholar_gem import ScholarGem
                scholar = ScholarGem(
                    web_researcher=getattr(self.director, 'web_researcher', None),
                    mcp_client=getattr(self.director, 'mcp_client', None),
                )
                url = url_match.group()
                msg_without_url = message.replace(url, "").strip()
                if len(msg_without_url) < 40:
                    result = await scholar.ingest_url(url)
                    if result.get("success"):
                        _url_ingested = True
                        await self.cerebro.aprender_interaccion(
                            f"Aprender URL: {url}", f"Persistido ({result.get('content_length',0)} chars)", "scholar")
                        # Auto-maintenance cada 5 URLs
                        try:
                            from src.agents.sage_gem import SageGem
                            conn = sqlite3.connect(str(Path.home() / ".nexus" / "brain" / "cerebro.db"), timeout=10)
                            cnt = conn.execute("SELECT COUNT(*) FROM conocimientos").fetchone()[0]
                            conn.close()
                            if cnt % 5 == 0:
                                sage = SageGem()
                                sage.run_full_maintenance()
                        except Exception as m:
                            logger.warning(f"Auto-maintenance failed: {m}")
            except Exception as e:
                logger.warning(f"Scholar ingest failed for {url}: {e}")
            # Biblioteca persistence (separate try/except)
            try:
                from src.agents.biblioteca_gem import BibliotecaGem
                biblio = BibliotecaGem()
                await biblio.organize(
                    title=f"url:{url}",
                    content=f"# {url}\n\nSource: {url}\n\nURL auto-ingested.",
                    category="Web",
                    tags=["auto-ingested", "web"],
                )
            except Exception as e:
                logger.warning(f"URL biblioteca persist failed for {url}: {e}")

        # If URL was just ingested, respond immediately
        if _url_ingested:
            topic_name = url.rsplit("/", 1)[-1].replace("-", " ").replace("_", " ").replace(".md", "")
            reply = f"Aprendi el contenido de {url}. Preguntame sobre {topic_name} cuando quieras."
            return {
                "reply": reply,
                "gem_used": gem,
                "engines": ["url_ingest"],
                "voice": None,
                "pc_action": None,
                "tool_result": None,
                "cerebro_stats": self.cerebro.obtener_estadisticas() if self.cerebro else {},
            }

        # Auto-research: si es pregunta (no accion), investigar en paralelo para enriquecer contexto
        _action_kw = {"escribe","crea","haz","genera","programa","codigo","funcion","implementa",
                      "refactoriza","arregla","debug","test","prueba","instala","configura",
                      "convierte","compara","analiza","disena","construye","despliega"}
        _is_action = any(kw in message.lower().split() for kw in _action_kw)
        _research_result = None
        if not _is_action and len(message) < 200 and self.director:
            try:
                from src.agents.scholar_gem import ScholarGem
                mem = self.director._get_memory_context(message, limit=3)
                mem_relevant = len(mem) > 100 and any(w in mem.lower() for w in message.lower().split() if len(w) > 4)
                if not mem_relevant:
                    scholar = ScholarGem(
                        web_researcher=getattr(self.director, 'web_researcher', None),
                        mcp_client=getattr(self.director, 'mcp_client', None),
                    )
                    sr = await scholar.research(message, max_sources=3)
                    if sr.get("sources"):
                        snippets = []
                        for s in sr["sources"][:3]:
                            t = s.get("title", "")
                            sn = (s.get("snippet", "") or s.get("summary", ""))[:300]
                            if t or sn:
                                snippets.append(f"- {t}: {sn}")
                        if snippets:
                            _research_result = "\n\n[INVESTIGACION AUTOMATICA DE SCHOLAR]\n" + "\n".join(snippets)
            except Exception as e:
                logger.debug(f"Auto-research failed: {e}")

        if _research_result:
            message = message + _research_result

        # Director execute: maneja memoria, tools, y gemas
        try:
            result = await self.director.execute(message, gem=gem, session_id=session_id)
            reply = result.data.get("content", str(result.data)) if result.data else "Task executed"
        except Exception as e:
            import traceback
            logger.error(f"Director execute error: {type(e).__name__}: {e}")
            logger.error(traceback.format_exc())
            return {
                "reply": f"Error al ejecutar: {e}",
                "gem_used": gem,
                "engines": ["error"],
                "voice": None,
                "pc_action": None,
                "tool_result": None,
                "cerebro_stats": self.cerebro.obtener_estadisticas() if self.cerebro else {},
            }

        # Guardrails: Validar output
        if self.guardrails and reply:
            try:
                output_check = self.guardrails.validate_output(reply)
                if output_check["blocked"]:
                    reply = "NEXUS ha filtrado esta respuesta por motivos de seguridad."
                elif output_check["sanitized"] != reply:
                    reply = output_check["sanitized"]
            except Exception:
                pass

        # Cerebro: Guardar respuesta
        if self.cerebro and reply:
            try:
                await self.cerebro.aprender_interaccion(message, reply, primary_gem)
            except Exception:
                pass

        audio_path = None

        # Voz: Sintetizar respuesta si se solicito
        if voice and reply and self.voice and self.voice.available:
            try:
                import os
                out_dir = Path(__file__).parent.parent.parent / "ui" / "assets" / "voice"
                out_dir.mkdir(parents=True, exist_ok=True)
                clean_text = reply[:500].replace("**", "").replace("*", "").replace("#", "").replace("`", "")
                filename = f"voice_{abs(hash(reply)) % 100000}.wav"
                out_path = str(out_dir / filename)
                result = self.voice.speak(clean_text, out_path)
                if result:
                    audio_path = f"/ui/assets/voice/{filename}"
            except Exception as e:
                logger.warning(f"Voice synthesis failed: {e}")

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
        if auto_tool_result and auto_tool_result.get("tool") == "web_search":
            # Web search results feed into director as context, not reply
            search_text = auto_tool_result.get("content", "") or json.dumps(auto_tool_result, ensure_ascii=False)
            message = f"{message}\n\n[Resultado de busqueda web proporcionado:]\n{search_text[:2000]}"
            auto_tool_result = None
        if auto_tool_result:
            tool_result = auto_tool_result
            if "entries" in auto_tool_result:
                dirs = [e for e in auto_tool_result["entries"] if e.get('type') == 'dir']
                files = [e for e in auto_tool_result["entries"] if e.get('type') == 'file']
                lines = [f"#### 📂 Carpetas ({len(dirs)})"]
                for e in dirs:
                    lines.append(f"- `{e.get('name', e.get('path', ''))}/`")
                lines.append("")
                lines.append(f"#### 📄 Archivos ({len(files)})")
                for e in files:
                    sz = e.get('size', 0)
                    szs = f" — `{sz:,} bytes`" if sz else ""
                    lines.append(f"- `{e.get('name', e.get('path', ''))}`{szs}")
                reply = "**Contenido del directorio:**\n\n" + "\n\n".join(lines)
            elif auto_tool_result.get("success") or "content" in auto_tool_result:
                result_text = json.dumps(auto_tool_result, ensure_ascii=False, indent=2)[:2000]
                if not reply:
                    reply = f"```\n{result_text}\n```"
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
        """Procesa imágenes - prueba providers en cadena, sin depender de PC2"""
        from datetime import datetime
        import io as io_mod
        
        start = datetime.now()
        VISION_MODEL = "qwen2.5vl:7b"
        
        img_clean = images[0] if images else ""
        if img_clean.startswith("data:"):
            img_clean = img_clean.split(",", 1)[1]
        
        prompt = message or "Describe esta imagen brevemente. ¿Qué ves?"
        
        # 1. Intentar Ollama local
        try:
            LOCAL_URL = os.environ.get("OLLAMA_HOST", os.environ.get("OLLAMA_URL", "http://localhost:11434"))
            if LOCAL_URL and not LOCAL_URL.startswith("http://") and not LOCAL_URL.startswith("https://"):
                LOCAL_URL = "http://" + LOCAL_URL
            messages = [
                {"role": "user", "content": prompt, "images": [img_clean]}
            ]
            response = requests.post(
                f"{LOCAL_URL}/api/chat",
                json={"model": VISION_MODEL, "messages": messages, "stream": False},
                timeout=10
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
                    "source": "local"
                }
        except Exception as e:
            logger.warning(f"Local vision failed: {e}")
        
        # 2. Análisis PIL básico (siempre funciona, sin dependencias externas)
        try:
            from PIL import Image
            
            img_bytes = base64.b64decode(img_clean)
            img_stream = io_mod.BytesIO(img_bytes)
            with Image.open(img_stream) as img:
                fmt = img.format or "unknown"
                mode = img.mode
                w, h = img.size
            
            size_kb = len(img_bytes) // 1024
            analysis = f"Recibí una imagen ({fmt}, {w}x{h}px, {size_kb}KB, modo {mode}). No puedo ver su contenido sin un modelo de visión (Ollama, OpenRouter, etc.). Describime qué contiene y te ayudo."
            return {
                "success": True,
                "content": analysis,
                "model": "pil_basic",
                "tool": "vision_analysis",
                "source": "pil_fallback",
                "img_info": {"format": fmt, "width": w, "height": h, "mode": mode},
            }
        except Exception as e3:
            logger.error(f"PIL fallback failed: {e3}")
        
        return {
            "success": False,
            "content": "No disponible. La imagen no pudo procesarse.",
            "model": VISION_MODEL,
            "tool": "vision_analysis",
        }

    async def search_memory(self, query: str) -> Dict:
        if not self.rag:
            return {"results": [], "count": 0, "error": "RAG memory not available"}
        results = self.rag.search(query, top_k=5)
        return {"results": results, "count": len(results)}

    async def get_knowledge_graph(self, search: str = "", centrality: bool = False,
                                   path_from: str = "", path_to: str = "",
                                   limit: int = 200) -> Dict:
        if not self.kg:
            return {"nodes": [], "edges": [], "stats": {}, "error": "Knowledge graph not available"}

        result = {}

        if search:
            nodes = [{
                "id": r["node_id"], "label": r["label"],
                "content": r["content"][:200] if r.get("content") else "",
                "tags": r.get("tags", []), "rank": r.get("rank", 0),
            } for r in self.kg.fts_search(search, limit=limit)]
            return {"nodes": nodes, "edges": [], "stats": {"search": search, "count": len(nodes)}}

        if centrality:
            nodes = self.kg.centrality(top_n=limit)
            return {"nodes": nodes, "edges": [], "stats": {"centrality": True, "count": len(nodes)}}

        if path_from and path_to:
            path = self.kg.shortest_path(path_from, path_to)
            return {"path": path, "stats": {"path_from": path_from, "path_to": path_to}}

        data = self.kg.export_for_visualization()
        return {
            "nodes": [{
                "id": n["id"], "label": n["label"], "type": n["type"],
                "tags": n["tags"], "epistemic_status": n.get("epistemic_status", "draft"),
                "access_count": n.get("access_count", 0),
            } for n in data.get("nodes", [])[:limit]],
            "edges": [{
                "source": e["source"], "target": e["target"], "type": e["type"],
                "weight": e.get("weight", 1.0),
                "why_connected": e.get("why_connected", ""),
                "cognitive_pattern": e.get("cognitive_pattern", ""),
            } for e in data.get("edges", [])[:limit * 5]],
            "stats": data.get("stats", {}),
        }

    async def learn(self, query: str, links: list = None) -> Dict:
        if not self.learning:
            return {"error": "Active learning not available"}
        return await self.learning.learn(query, links)

    async def get_status(self) -> Dict:
        # Engines check is best-effort with hard timeout — never block /api/status
        try:
            engines = await asyncio.wait_for(self.connectivity.check_all_engines(), timeout=5.0)
        except (asyncio.TimeoutError, Exception):
            engines = {"_error": "engines check timed out"}
        pc2 = getattr(self, "pc2", None)
        pc2_status = pc2.get_status() if pc2 else {"available": False}
        
        def _safe_stats(obj, method="get_stats"):
            if obj and hasattr(obj, method):
                try:
                    return getattr(obj, method)()
                except Exception:
                    return {}
            return {}
        
        ollama_models = await _get_ollama_models_merged()
        
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
            "pc_control": {
                "screenshot_dir": str(self.pc_control.screenshot_dir) if self.pc_control else "N/A",
                "pc_controller": self.pc_controller.get_status() if self.pc_controller and hasattr(self.pc_controller, 'get_status') else {},
            },
            "security": _safe_stats(self.guardrails, "get_security_report"),
            "safety": _safe_stats(self.safety),
            "ollama": ollama_models,
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


async def handle_v3_services(request: web.Request) -> web.Response:
    """v3 architecture — list services registered in NexusApp.

    Empty by default. As services are migrated from director to the v3
    container (Fases 4+), they appear here.
    """
    backend: SuperNEXUSBackend = request.app["backend"]
    app_v3 = getattr(backend, "app", None)
    if app_v3 is None:
        return web.json_response({"error": "v3 NexusApp not initialized"}, status=503)
    return web.json_response(app_v3.get_status())


async def handle_v3_plugins(request: web.Request) -> web.Response:
    """v3 architecture — list active gema plugins (src/plugins/gemas/)."""
    try:
        from src.plugins.manifest import list_gemas_summary, load_gemas
        gemas = load_gemas()
        return web.json_response({
            "count": len(gemas),
            "gemas": list_gemas_summary(gemas),
        })
    except Exception as e:
        return web.json_response(
            {"error": f"{type(e).__name__}: {e}"},
            status=500,
        )


async def handle_v3_capabilities_audit(request: web.Request) -> web.Response:
    """GET /api/v3/capabilities/audit — Per-gema list of tools the gema would
    be DENIED if NEXUS_ENFORCE_CAPS=1. Use BEFORE flipping enforcement on
    in distribution so you know what to expect."""
    try:
        from src.plugins.manifest import load_gemas
        from src.security.capability_enforcer import audit_all, enforcement_active, TOOL_CAP_MAP
        gemas = load_gemas()
        missing = audit_all(gemas)
        return web.json_response({
            "enforcement_active": enforcement_active(),
            "total_gemas": len(gemas),
            "gemas_with_missing": len(missing),
            "missing": missing,
            "tools_with_required_caps": sorted(TOOL_CAP_MAP),
        })
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_v3_capabilities(request: web.Request) -> web.Response:
    """v3 — capability inventory across gemas.

    Returns:
        {
          "total_gemas": N,
          "by_capability": {cap_str: [gema_name, ...]},
          "unprivileged": [gema_name, ...]    # zero capabilities declared
        }

    MVP enforcement note: capabilities are DECLARED today, not yet ENFORCED.
    This endpoint is the prep for a future capability manager that gates
    tool calls. Listing them now lets users (and audit tools like medusa)
    see the surface area each gema requests before that lands.
    """
    try:
        from src.plugins.manifest import load_gemas
        gemas = load_gemas()
        by_cap: Dict[str, List[str]] = {}
        unprivileged: List[str] = []
        for name, g in gemas.items():
            if not g.capabilities:
                unprivileged.append(name)
                continue
            for cap in g.capabilities:
                by_cap.setdefault(cap, []).append(name)
        return web.json_response({
            "total_gemas": len(gemas),
            "by_capability": {k: sorted(v) for k, v in sorted(by_cap.items())},
            "unprivileged": sorted(unprivileged),
            "enforcement": "declarative_only",  # roadmap signal
        })
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_v3_brain(request: web.Request) -> web.Response:
    """v3 architecture — expose the brain modules wired into the director.

    Useful for confirming the refactor surface: identity / health / routing /
    tools / memory brains all visible here regardless of the legacy backend.
    """
    backend: SuperNEXUSBackend = request.app["backend"]
    director = backend.director
    out = {}
    for attr in ("identity_brain", "health_brain", "routing_brain", "tool_brain", "memory_brain", "training_brain"):
        brain = getattr(director, attr, None)
        if brain is None:
            out[attr] = {"present": False}
        else:
            info = {"present": True, "class": type(brain).__name__}
            # Optional: brains may expose extra introspection
            if hasattr(brain, "check_all"):
                try:
                    info["checks"] = brain.check_all()
                except Exception:
                    pass
            if attr == "routing_brain":
                try:
                    info["sticky_sessions"] = len(brain._sticky_cache)
                    info["sticky_ttl_s"] = brain.sticky_ttl_s
                except Exception:
                    pass
            out[attr] = info
    return web.json_response({"brain_modules": out})


async def handle_capabilities(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    report = await backend.director.get_capabilities_report()
    identity = await backend.director.get_dynamic_identity()
    return web.json_response({
        "report": report,
        "identity": identity,
    })


async def handle_providers(request: web.Request) -> web.Response:
    from src.core.provider_discovery import discover_providers, get_discovered_providers
    await discover_providers()
    providers = get_discovered_providers()
    result = [
        {
            "id": p.def_.id,
            "name": p.def_.name,
            "online": p.online,
            "models": [{"id": m.id, "name": m.name} for m in p.models],
        }
        for p in providers
    ]
    # Add cloud providers from env (.env config)
    try:
        import os
        seen_ids = {p["id"] for p in result}
        zen_key = os.environ.get("OPENCODE_API_KEY", "")
        if zen_key and "opencode-zen" not in seen_ids:
            result.append({
                "id": "opencode-zen",
                "name": "OpenCode Zen (Cloud)",
                "online": True,
                "models": [
                    {"id": "deepseek-v4-flash-free", "name": "DeepSeek V4 Flash Free"},
                    {"id": "mimo-v2.5-free", "name": "MiMo V2.5 Free"},
                    {"id": "nemotron-3-ultra-free", "name": "Nemotron 3 Ultra Free"},
                    {"id": "north-mini-code-free", "name": "North Mini Code Free"},
                ],
            })
    except Exception:
        pass
    return web.json_response(result)


async def handle_provider_catalog(request: web.Request) -> web.Response:
    """GET /api/provider-catalog - Lista el catalogo completo de providers
    preconfigurados (inspirado en openhuman/inference-provider-catalog.md).

    Query: ?available=true filtra solo los que tienen API key configurada.
    """
    import os
    from src.core.provider_catalog import PROVIDER_CATALOG
    only_available = request.query.get("available", "").lower() == "true"
    result = []
    for entry in PROVIDER_CATALOG:
        api_key = ""
        if entry.get("api_key_env"):
            api_key = os.environ.get(entry["api_key_env"], "")
        available = bool(api_key) or not entry.get("api_key_env")
        if only_available and not available:
            continue
        # Ocultar la key, solo indicar si esta configurada
        out = {**entry, "api_key_configured": bool(api_key), "available": available}
        if "api_key" in out:
            out.pop("api_key", None)
        result.append(out)
    return web.json_response({
        "total": len(PROVIDER_CATALOG),
        "shown": len(result),
        "providers": result,
    })


async def handle_llm_gateway_stats(request: web.Request) -> web.Response:
    """GET /api/llm/gateway/stats - Stats del gateway con fallback chain."""
    backend: SuperNEXUSBackend = request.app["backend"]
    gw = getattr(backend.director, "llm_gateway", None)
    if gw is None:
        return web.json_response({"error": "llm_gateway not initialized"}, status=503)

    # Introspeccionar el gateway para sacar provider_status
    stats = {}
    for m in ("get_status", "status", "get_state"):
        if hasattr(gw, m):
            cand = getattr(gw, m)
            try:
                stats = cand() if callable(cand) else cand
                if isinstance(stats, dict) and stats:
                    break
            except Exception:
                pass

    # Listar providers del registry tambien
    reg = getattr(backend.director, "provider_registry", None)
    registry_profiles = []
    if reg is not None:
        for prov in getattr(reg, "_providers", {}).values():
            registry_profiles.append({
                "name": getattr(prov, "name", ""),
                "model": getattr(prov, "model", ""),
            })

    return web.json_response({
        "gateway": stats,
        "registry_profiles": registry_profiles,
        "registry_count": len(registry_profiles),
    })


# ─── Cloud Providers (user-managed) ────────────────────────────────────────
import json as _json_cp
from pathlib import Path as _Path_cp


def _cloud_providers_path() -> _Path_cp:
    p = _Path_cp.home() / ".nexus" / "cloud_providers.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_cloud_providers() -> list:
    p = _cloud_providers_path()
    if not p.exists():
        return []
    try:
        return _json_cp.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_cloud_providers(items: list) -> None:
    _cloud_providers_path().write_text(
        _json_cp.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8"
    )


async def handle_cloud_providers_list(request: web.Request) -> web.Response:
    """GET /api/cloud-providers — list user-added cloud LLM providers."""
    items = _load_cloud_providers()
    # Strip api_key for safety, return masked
    safe = []
    for it in items:
        key = it.get("api_key", "")
        masked = (key[:6] + "…" + key[-4:]) if len(key) > 12 else ("****" if key else "")
        safe.append({**it, "api_key": masked, "has_key": bool(key)})
    return web.json_response({"providers": safe})


async def handle_cloud_providers_save(request: web.Request) -> web.Response:
    """POST /api/cloud-providers — add/update a cloud provider.

    Body: {id, name, base_url, api_key, models[], enabled}
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    pid = (data.get("id") or "").strip()
    if not pid:
        return web.json_response({"error": "id required"}, status=400)

    items = _load_cloud_providers()
    found = False
    for i, it in enumerate(items):
        if it.get("id") == pid:
            # Preserve existing key if new one is empty/masked
            new_key = data.get("api_key", "")
            if not new_key or "…" in new_key or new_key.startswith("****"):
                data["api_key"] = it.get("api_key", "")
            items[i] = data
            found = True
            break
    if not found:
        items.append(data)
    _save_cloud_providers(items)
    return web.json_response({"ok": True, "id": pid, "updated": found})


async def handle_cloud_providers_delete(request: web.Request) -> web.Response:
    """DELETE /api/cloud-providers/{id}"""
    pid = request.match_info.get("id", "")
    items = _load_cloud_providers()
    n0 = len(items)
    items = [it for it in items if it.get("id") != pid]
    _save_cloud_providers(items)
    return web.json_response({"ok": True, "removed": n0 - len(items)})


_OLLAMA_CACHE = {"models": [], "count": 0, "cached_at": 0.0}
_OLLAMA_CACHE_TTL = 10.0

async def _fetch_ollama_models() -> dict:
    """Fetch Ollama models from live API, with short TTL cache."""
    global _OLLAMA_CACHE
    now = time.time()
    if now - _OLLAMA_CACHE.get("cached_at", 0) < _OLLAMA_CACHE_TTL and _OLLAMA_CACHE.get("models"):
        return _OLLAMA_CACHE
    try:
        import httpx as _httpx
        async with _httpx.AsyncClient(timeout=3.0) as c:
            r = await c.get("http://localhost:11434/api/tags")
            api_models = []
            if r.status_code == 200:
                data = r.json()
                api_models = [
                    {
                        "name": m.get("name", ""),
                        "size_gb": round(m.get("size", 0) / 1e9, 2),
                        "modified": m.get("modified_at", ""),
                        "family": (m.get("details") or {}).get("family", ""),
                        "param_size": (m.get("details") or {}).get("parameter_size", ""),
                        "source": "ollama",
                    }
                    for m in data.get("models", [])
                ]
            manifest_models = _scan_ollama_manifests()
            models = _merge_ollama_models(api_models, manifest_models)
            _OLLAMA_CACHE = {"models": models, "count": len(models), "cached_at": time.time()}
            return _OLLAMA_CACHE
    except Exception as e:
        manifest_models = _scan_ollama_manifests()
        models = _merge_ollama_models([], manifest_models)
        _OLLAMA_CACHE = {"models": models, "count": len(models), "cached_at": time.time(), "error": str(e)}
        return _OLLAMA_CACHE


async def handle_ollama_tags(request: web.Request) -> web.Response:
    """GET /api/ollama/tags — proxy live Ollama model list + manifest scan fallback."""
    result = await _fetch_ollama_models()
    return web.json_response(result, headers={"Cache-Control": "no-store, max-age=0"})


async def handle_ollama_refresh(request: web.Request) -> web.Response:
    """POST /api/ollama/refresh — force refresh Ollama model cache + provider discovery."""
    global _OLLAMA_CACHE
    _OLLAMA_CACHE = {"models": [], "count": 0, "cached_at": 0.0}
    from src.core.provider_discovery import discover_providers
    providers = await discover_providers(force=True)
    result = await _fetch_ollama_models()
    return web.json_response({
        "status": "refreshed",
        "models": result["models"],
        "count": result["count"],
        "providers_detected": len(providers),
    }, headers={"Cache-Control": "no-store, max-age=0"})


async def handle_projects(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    data = await backend.get_projects()
    return web.json_response(data)


async def handle_project_activate(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    body = await request.json()
    name = body.get("project", "default")
    projects_dir = Path(__file__).parent.parent.parent / "data" / "projects"
    if name != "default" and not (projects_dir / name).exists():
        return web.json_response({"error": f"Project '{name}' not found"}, status=404)
    await backend.director.change_project(name)
    return web.json_response({"status": "ok", "current": name})


async def handle_project_context_get(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    name = request.match_info.get("name", "default")
    projects_dir = Path(__file__).parent.parent.parent / "data" / "projects"
    context_path = projects_dir / name / "CONTEXT.md"
    content = ""
    if context_path.exists():
        content = context_path.read_text(encoding="utf-8")
    return web.json_response({"project": name, "context": content})


async def handle_project_context_put(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    name = request.match_info.get("name", "default")
    projects_dir = Path(__file__).parent.parent.parent / "data" / "projects"
    project_dir = projects_dir / name
    project_dir.mkdir(parents=True, exist_ok=True)
    body = await request.json()
    content = body.get("context", "")
    context_path = project_dir / "CONTEXT.md"
    context_path.write_text(content, encoding="utf-8")
    # Si es el proyecto activo, refrescar contexto en el director
    if backend.director.current_project == name:
        await backend.director.change_project(name)
    return web.json_response({"project": name, "saved": True, "chars": len(content)})


async def handle_gems(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    data = await backend.get_gems()
    return web.json_response(data)


async def handle_knowledge_graph(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    search = request.query.get("search", "")
    centrality = request.query.get("centrality", "").lower() in ("true", "1")
    path_from = request.query.get("path_from", "")
    path_to = request.query.get("path_to", "")
    try:
        limit = int(request.query.get("limit", "200"))
    except (ValueError, TypeError):
        limit = 200
    data = await backend.get_knowledge_graph(
        search=search, centrality=centrality,
        path_from=path_from, path_to=path_to, limit=limit,
    )
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
    except Exception:
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
    session_id = (data.get("session_id") or "").strip() or None

    # Propagate session_id through the async chain via contextvars so any
    # downstream emit (LLM_TOKEN_USAGE, MCP events, etc.) can attribute
    # cost / activity to the right session without firing-signatures.
    try:
        from src.observability.context import set_session_id
        set_session_id(session_id)
    except Exception:
        pass

    # Slash command intercept (openakita pattern): /foo... bypasses the LLM
    # entirely and routes to the slash registry. Return the SlashResult
    # shaped to look like a normal chat reply so the UI doesn't branch.
    msg_stripped = (message or "").strip()
    if msg_stripped.startswith("/") and not msg_stripped.startswith("//"):
        try:
            from src.core.slash_commands import registry
            sr = await registry.execute(msg_stripped, {
                "session_id": session_id,
                "request_id": request.get("request_id"),
            })
            return web.json_response({
                "reply": sr.message,
                "slash": sr.to_dict(),
                "session_id": session_id,
                "via": "slash",
            })
        except Exception as e:
            logger.warning(f"slash intercept failed: {e}")
            # fall through to normal chat path

    # Circuit breaker para Ollama
    if not backend.safety.can_use_service("ollama"):
        return web.json_response({
            "error": "Service temporarily unavailable",
            "service": "ollama",
            "retry_after": backend.safety.circuit_breakers["ollama"].config.recovery_timeout,
        }, status=503)

    # Wrap the LLM call in a runtime_logs run so L1/L2/L3 capture this turn.
    # No-op if session_id absent — anonymous chats don't get per-session logs.
    _run = None
    if session_id:
        try:
            from src.observability.runtime_logs import session_logger
            _run = session_logger(session_id).start_run(trace_id=request.get("request_id"))
        except Exception:
            _run = None

    result = await backend.process_message(message, gem, project, voice=voice, images=images, files=files)
    # Echo session_id back so client knows where its cost/logs are landing
    if session_id:
        result.setdefault("session_id", session_id)

    if _run is not None:
        try:
            reply = result.get("reply") or ""
            gem_used = result.get("gem_used") or gem
            _run.note_node(
                f"chat:{gem_used}",
                tokens_in=max(1, len(message) // 4),
                tokens_out=max(0, len(reply) // 4),
                cost_usd=float(result.get("cost_usd") or 0.0),
            )
            status = "completed" if not result.get("error") else "failed"
            _run.finalize(status=status, cost_usd=float(result.get("cost_usd") or 0.0))
        except Exception:
            pass
    # Synthetic LLM_TOKEN_USAGE so the per-session budget tracker has data
    # even when this chat path didn't flow through LLMProvider.chat() (it
    # often goes via llm_gateway / direct ollama). Best-effort token estimate;
    # cost=0 unless backend reported one. Skipped silently if anything fails.
    if session_id:
        try:
            from src.observability.event_stream import emit, EventType
            reply = result.get("reply") or ""
            tokens_in_est = max(1, len(message) // 4)
            tokens_out_est = max(0, len(reply) // 4)
            emit(EventType.LLM_TOKEN_USAGE,
                 data={
                     "provider": "chat", "model": gem,
                     "prompt_tokens": tokens_in_est,
                     "completion_tokens": tokens_out_est,
                     "total_tokens": tokens_in_est + tokens_out_est,
                     "cost_usd": float(result.get("cost_usd") or 0.0),
                     "estimated": True,  # signal: not provider-reported
                 },
                 session_id=session_id,
                 request_id=request.get("request_id"),
                 source="handle_chat")
        except Exception:
            pass
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
                voice = data.get("voice", False)
                images = data.get("images", [])
                files = data.get("files", [])
                session_id = (data.get("session_id") or "").strip() or None

                # Propagate session_id so sticky routing + cost tracking work
                if session_id:
                    try:
                        from src.observability.context import set_session_id
                        set_session_id(session_id)
                    except Exception:
                        pass

                if not message:
                    await ws.send_json({"type": "error", "content": "Message is required"})
                    continue

                # Send start marker
                await ws.send_json({"type": "start", "gem": gem})
                logger.info(f"[WS] start marker sent for gem={gem}, msg={message[:50]}")
                await ws.send_json({"type": "thinking", "content": "Procesando..."})

                try:
                    # Phase 0: Skip proactive for WS — POST handles it
                    proactive_data = None
                    gem_override = gem

                    # Phase 1: ALWAYS run process_message (tools work without Ollama)
                    try:
                        async with asyncio.timeout(45):
                            result = await backend.process_message(message, gem if not proactive_data else gem_override, project, voice=voice, images=images, files=files, session_id=session_id)
                        logger.info(f"[WS] process_message completed, gem_used={result.get('gem_used')}, reply_len={len(result.get('reply',''))}")
                    except (asyncio.TimeoutError, TimeoutError):
                        logger.warning("process_message timeout after 45s, using fallback reply")
                        result = {
                            "reply": "Estoy procesando tu mensaje. El Director esta respondiendo, por favor espera un momento.",
                            "gem_used": gem if not proactive_data else gem_override,
                            "success": True,
                        }
                    tool_context = result.get("tool_result")
                    primary_gem = result.get("gem_used", gem if not proactive_data else gem_override)
                    has_images = images and len(images) > 0
                    full_reply = ""

                    # Build proactive context ONCE para todas las rutas
                    proactive_context = ""
                    scholar_summary = ""
                    scholar_sources = []
                    if proactive_data:
                        scholar_summary = proactive_data.get("summary", "")
                        scholar_sources = proactive_data.get("sources", [])
                        if scholar_summary or scholar_sources:
                            proactive_context = (
                                f"\n\n[DATOS DE INTERNET — obtenidos ANTES de responder]\n"
                                f"Fuentes consultadas: {len(scholar_sources)}\n"
                                f"{scholar_summary[:2000]}\n"
                                f"\nIMPORTANTE: Usa estos datos para responder. NUNCA digas 'no tengo acceso a internet'."
                            )

                    if tool_context or result.get("reply", "").startswith("```tool_result"):
                        # Tool executed — synthesize via LLM if applicable
                        tool_data = tool_context or {}
                        tool_name = (tool_data.get("tool") or "").lower() if isinstance(tool_data, dict) else ""
                        synth_tools = {"web_search", "web_fetch", "code_search", "find_files", "glob_files",
                                       "grep_content", "lsp_diagnostics", "lsp_symbols"}
                        reply_with_tools = result.get("reply", "")
                        if tool_name in synth_tools and await backend.ollama.is_available():
                            # Send tool result first as a small "thinking" card, then stream synthesis
                            await ws.send_json({
                                "type": "tool_event",
                                "tool": tool_name,
                                "status": "ok",
                                "hint": f"{tool_data.get('count', len(tool_data.get('results', tool_data.get('content', ''))))} resultados",
                            })
                            gem_model = (
                                backend.director.gemas[primary_gem].model
                                if primary_gem in backend.director.gemas
                                else "deepseek-v4-flash-free"
                            )
                            synth_prompt = (
                                f"El usuario pidio: {message}\n\n"
                                f"Resultados de la herramienta {tool_name}:\n"
                                f"{json.dumps(tool_data, ensure_ascii=False)[:6000]}\n\n"
                                f"{proactive_context + chr(10) if proactive_context else ''}"
                                f"Sintetiza los resultados en una respuesta natural, concisa, en espanol. "
                                f"Si son resultados de busqueda web, resume los puntos clave y cita los titulos de las fuentes mas relevantes. "
                                f"Si hay una respuesta obvia, da la respuesta directa. NO muestres JSON crudo, NO uses bloques de codigo. "
                                f"TIENES ACCESO A INTERNET — si los datos son insuficientes, dilo y busca mas."
                            )
                            try:
                                synth_stream = backend.ollama.chat_stream(
                                    model=gem_model,
                                    messages=[
                                        {"role": "system", "content": f"Eres {primary_gem}, una gema de SuperNEXUS. Responde en espanol de forma clara y concisa."},
                                        {"role": "user", "content": synth_prompt},
                                    ],
                                    options={"temperature": 0.5, "num_predict": 1024},
                                )
                                async with asyncio.timeout(30):
                                    async for content in synth_stream:
                                        full_reply += content
                                        await ws.send_json({"type": "token", "content": content})
                            except (asyncio.TimeoutError, TimeoutError):
                                logger.warning(f"tool synthesis timeout, using raw result")
                                for i in range(0, len(reply_with_tools), 8):
                                    chunk = reply_with_tools[i:i+8]
                                    await ws.send_json({"type": "token", "content": chunk})
                                full_reply = reply_with_tools
                            except Exception as e:
                                logger.warning(f"tool synthesis failed: {e}")
                                # Fallback: stream raw tool result
                                for i in range(0, len(reply_with_tools), 8):
                                    chunk = reply_with_tools[i:i+8]
                                    await ws.send_json({"type": "token", "content": chunk})
                                full_reply = reply_with_tools
                        else:
                            # Other tools (write_file, read_file, edit_file) — stream raw result
                            for i in range(0, len(reply_with_tools), 8):
                                chunk = reply_with_tools[i:i+8]
                                await ws.send_json({"type": "token", "content": chunk})
                            full_reply = reply_with_tools
                    elif await backend.ollama.is_available():
                        # Phase 2: Use process_message reply directly (fast path)
                        # Ollama re-generation was causing 30s+ delays; skip it
                        director_reply = result.get("reply", "")
                        if director_reply:
                            # Stream the Director's reply directly to client
                            for i in range(0, len(director_reply), 4):
                                chunk = director_reply[i:i+4]
                                await ws.send_json({"type": "token", "content": chunk})
                            full_reply = director_reply
                        else:
                            # Fallback: Ollama streaming
                            system_prompt = (
                                f"Eres el Director de SuperNEXUS. Gema activa: {primary_gem}. "
                                f"Responde en espanol, conciso y directo."
                            )
                            msgs = [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": message + proactive_context if proactive_context else message},
                            ]
                            gem_model = "qwen2.5vl:7b" if has_images else (
                                backend.director.gemas[primary_gem].model if primary_gem in backend.director.gemas else "deepseek-v4-flash-free"
                            )
                            try:
                                stream_task = backend.ollama.chat_stream(
                                    model=gem_model,
                                    messages=msgs,
                                    options={"temperature": 0.7, "num_predict": 2048},
                                )
                                async with asyncio.timeout(30):
                                    async for content in stream_task:
                                        full_reply += content
                                        await ws.send_json({"type": "token", "content": content})
                            except (asyncio.TimeoutError, TimeoutError):
                                logger.warning("Ollama stream timeout, no fallback reply available")
                            except Exception as stream_err:
                                logger.warning(f"Ollama stream error: {stream_err}")
                    else:
                        # Ollama down but no tool matched — return Director's raw reply
                        fallback = result.get("reply", "Director operando sin LLM. Las herramientas de archivo y terminal siguen disponibles.")
                        await ws.send_json({"type": "token", "content": fallback})
                        full_reply = fallback

                    fallback_used = False
                    if await _is_low_confidence_reply(full_reply):
                        try:
                            fallback_summary = scholar_summary
                            fallback_sources = scholar_sources
                            if not fallback_summary and not fallback_sources:
                                await ws.send_json({
                                    "type": "thinking",
                                    "content": "No estoy seguro. Buscando en internet...",
                                })
                                from src.agents.scholar_gem import ScholarGem
                                mcp2 = getattr(backend.director, "mcp_client", None)
                                scholar = ScholarGem(mcp_client=mcp2)
                                search = await scholar.research(message, max_sources=3)
                                fallback_summary = search.get("summary", "")
                                fallback_sources = search.get("sources", [])
                            if fallback_sources or fallback_summary:
                                fallback_text = (
                                    f"[Datos obtenidos de internet]\n"
                                    f"Fuentes consultadas: {len(fallback_sources)}\n"
                                    f"\n"
                                    f"{fallback_summary[:2000]}"
                                )
                                # SOBRESCRIBIR full_reply — el LLM se nego pero tenemos datos reales
                                full_reply = fallback_text
                                fallback_used = True
                                await ws.send_json({"type": "fallback", "sources": len(fallback_sources)})
                        except Exception as e:
                            logger.warning(f"web fallback failed: {e}")

                    await ws.send_json({
                        "type": "complete",
                        "gem_used": primary_gem,
                        "tokens_used": len(full_reply.split()),
                    })

                    if backend.cerebro:
                        await backend.cerebro.aprender_interaccion(
                            message, full_reply, primary_gem,
                            contexto="auto-fallback" if fallback_used else "",
                        )

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
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    query = data.get("query", "")
    result = await backend.search_memory(query)
    return web.json_response(result)


def _safe_dict(obj):
    """Convert any dict to JSON-safe dict, stripping non-serializable values."""
    import json as _json
    try:
        _json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        if isinstance(obj, dict):
            return {k: _safe_dict(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_safe_dict(x) for x in obj]
        return str(obj)


async def handle_learn(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    query = data.get("query", "")
    links = data.get("links", [])
    result = await backend.learn(query, links)
    return web.json_response(_safe_dict(result))


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
    except Exception:
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
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    ok = await backend.pc_control.mouse_move(data.get("x", 0), data.get("y", 0), data.get("duration", 0.5))
    return web.json_response({"success": ok})


async def handle_type_text(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    ok = await backend.pc_control.type_text(data.get("text", ""), data.get("interval", 0.05))
    return web.json_response({"success": ok})


async def handle_key_press(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
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
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    instruction = data.get("instruction", "")
    result, response = await backend.pc_controller.follow_instruction(instruction)
    return web.json_response({"result": result, "ollama_response": response})


async def handle_vision_process(request: web.Request) -> web.Response:
    """Endpoint unificado de procesamiento de visión (multi-provider)"""
    from src.core.vision_config import get_vision_config, DEFAULT_VISION_PROVIDER
    
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    
    instruction = data.get("instruction", "Describe esta imagen")
    image_data = data.get("image", "")
    image_url = data.get("url", "")
    provider = data.get("provider", DEFAULT_VISION_PROVIDER)
    
    if image_url:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(image_url)
                if r.status_code == 200:
                    image_data = base64.b64encode(r.content).decode()
        except Exception as e:
            return web.json_response({"error": f"Failed to fetch image: {e}"}, status=400)
    
    if not image_data:
        return web.json_response({"error": "No image provided"}, status=400)
    
    img_clean = image_data
    if img_clean.startswith("data:"):
        img_clean = img_clean.split(",", 1)[1]
    
    result = {
        "provider": provider,
        "model": "",
        "instruction": instruction,
    }
    
    providers_to_try = [provider]
    visited = set()
    while providers_to_try:
        p = providers_to_try.pop(0)
        if p in visited:
            continue
        visited.add(p)
        cfg = get_vision_config(p)
        ptype = cfg.get("type", "ollama")
        result["provider"] = p
        result["model"] = cfg.get("model", "")
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                if ptype == "ollama":
                    url = cfg.get("url", "http://localhost:11434")
                    resp = await client.post(f"{url}/api/generate", json={
                        "model": cfg["model"], "prompt": instruction,
                        "images": [img_clean], "stream": False,
                    })
                    if resp.status_code == 200:
                        data = resp.json()
                        result["success"] = True
                        result["response"] = data.get("response", "")
                        return web.json_response(result)
                    raise Exception(f"Ollama HTTP {resp.status_code}")
                
                elif ptype == "openai":
                    base_url = cfg.get("url", "https://openrouter.ai/api/v1")
                    api_key = cfg.get("api_key", "")
                    if not api_key:
                        raise Exception(f"API key not configured for {p}")
                    data_uri = f"data:image/png;base64,{img_clean}"
                    resp = await client.post(f"{base_url}/chat/completions", json={
                        "model": cfg["model"],
                        "messages": [{"role": "user", "content": [
                            {"type": "text", "text": instruction},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ]}],
                        "max_tokens": 1024,
                    }, headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    })
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"]
                        result["success"] = True
                        result["response"] = content
                        return web.json_response(result)
                    raise Exception(f"OpenAI HTTP {resp.status_code}: {resp.text[:200]}")
                
                elif ptype == "pil":
                    try:
                        from PIL import Image
                        import io
                        img_bytes = base64.b64decode(img_clean)
                        with Image.open(io.BytesIO(img_bytes)) as img:
                            fmt = img.format or "unknown"
                            w, h = img.size
                            mode = img.mode
                        size_kb = len(img_bytes) // 1024
                        content = f"Imagen: {fmt} {w}x{h}px, {size_kb}KB, modo {mode}"
                        result["success"] = True
                        result["response"] = content
                        return web.json_response(result)
                    except Exception as pil_e:
                        raise Exception(f"PIL failed: {pil_e}")
                
                else:
                    raise Exception(f"Unknown provider type: {ptype}")
        except Exception as e:
            logger.warning(f"Provider {p} failed: {e}")
            result["success"] = False
            result["error"] = str(e)
            fb = cfg.get("fallback")
            if fb and fb not in visited:
                providers_to_try.append(fb)
    
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




# ==================== BRAIN ENDPOINTS ====================


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


async def _is_low_confidence_reply(reply: str) -> bool:
    """Detecta respuestas que indican que el modelo no sabe o alucina.

    Patrones cubiertos:
    - "no se", "no estoy seguro", "no tengo informacion", "no dispongo"
    - Alucinaciones tipicas: "GPT-4", "OpenAI", "ChatGPT" (NEXUS local no los usa)
    - "como IA" (cliche de no-respuesta)
    """
    if not reply or len(reply.strip()) < 5:
        return True
    text_lower = reply.lower()
    low_conf_patterns = [
        r"\bno\s+s[eé]\b", r"\bno\s+estoy\s+seguro", r"\bno\s+tengo\s+(?:informaci[oó]n|la\s+capacidad|acceso|datos)",
        r"\bno\s+dispongo", r"\bno\s+puedo\s+(?:acceder|buscar|responder|proporcionar|verificar)",
        r"\bno\s+lo\s+s[eé]\b", r"\bno\s+encontr[eé]\s+(?:informaci[oó]n|datos)",
        r"\bno\s+es\s+posible\b", r"\bno\s+me\s+es\s+posible\b",
        r"\bno\s+tengo\s+acceso\s+a\s+internet", r"\bno\s+cuanto\s+con\s+(?:acceso|informaci[oó]n)",
        r"\bno\s+puedo\s+acceder\s+a\s+internet", r"\bno\s+tengo\s+conexi[oó]n",
        r"\bi\s+don'?t\s+know", r"\bnot\s+sure\b", r"\bunsure\b",
        r"\bi'?m\s+not\s+(?:sure|certain|able)", r"\bno\s+specific\s+data\b",
        r"\bno\s+hay\s+(?:informaci[oó]n|datos)\s+disponibles",
        r"\bmi\s+conocimiento\s+(?:no\s+incluye|llega\s+hasta)",
    ]
    for pat in low_conf_patterns:
        if re.search(pat, text_lower):
            return True
    hallucination_markers = [
        "gpt-4", "gpt-3.5", "openai's gpt", "i'm chatgpt", "soy chatgpt",
        "como modelo de lenguaje de openai", "as an ai language model",
        "fui creado por openai", "desarrollado por openai",
    ]
    for marker in hallucination_markers:
        if marker in text_lower:
            return True
    return False


def _requires_live_data(message: str) -> bool:
    """Detecta si el mensaje del usuario requiere datos en vivo de internet.

    NEXUS tiene acceso a TODO el internet via Scholar y web_fetch. Si el mensaje
    implica datos externos (precios, versiones actuales, noticias, clima, etc.),
    el sistema debe PRE-FETCH los datos ANTES de que el LLM responda, para
    que el LLM sintetice con informacion real en vez de negarse.
    """
    msg_lower = message.lower()
    # URLs always trigger proactive research
    if re.search(r'https?://[^\s"\']+', msg_lower):
        return True
    live_data_patterns = [
        # Precios y finanzas
        r"\bprecio\b", r"\bcotizaci[oó]n\b", r"\bvalor\s+actual\b", r"\bcu[aá]nto\s+(?:vale|cuesta)\b",
        r"\bbitcoin\b", r"\bethereum\b", r"\bcripto\w*\b", r"\bd[oó]lar\b", r"\beuro\b",
        r"\bbolsa\b", r"\bmercado\b", r"\bacci[oó]n\w*\b",
        # Versiones actuales
        r"[uú]ltima\s+versi[oó]n", r"latest\s+version", r"current\s+version",
        r"versi[oó]n\s+actual", r"\bque\s+versi[oó]n\b", r"\bcu[aá]nto\s+(?:cuesta|vale)\b",
        # Fechas y tiempo real
        r"\bqu[eé]\s+d[ií]a\b", r"\bqu[eé]\s+hora\b", r"\bfecha\s+de\s+(?:release|lanzamiento|publicaci[oó]n)\b",
        r"\bhoy\b", r"\bayer\b", r"\bma[nñ]ana\b", r"\besta\s+semana\b", r"\beste\s+mes\b",
        r"\bactual\w*\b", r"\bactualmente\b", r"\ben\s+este\s+momento\b", r"\bahora\s+mismo\b",
        r"\bacaba\s+de\b", r"\bacaban\s+de\b", r"\bultima\w*\b", r"\bu[ú]ltima\w*\b",
        r"\brecient\w*\b", r"\bnuevo\w*\b", r"\brelease\b", r"\blanzamiento\b",
        # Noticias y trending
        r"\bnoticia\w*\b", r"\bnovedad\w*\b", r"\btrending\b", r"\bviral\b",
        # Datos del mundo
        r"\bclima\b", r"\btiempo\b", r"\btemperatura\b", r"\blluvia\b",
        # Definiciones externas
        r"\bqu[eé]\s+es\s+(?!la\s+versi[oó]n)", r"\bdefinici[oó]n\s+de\b",
        r"\bsignificado\s+de\b", r"\bquien\s+(?:es|fue|cre[oó])\b",
        # Búsqueda
        r"\bbusca\b", r"\bbuscar\b", r"\bencuentra\b", r"\bexplora\b",
        r"\binvestiga\w*\b", r"\bresearch\b",
    ]
    for pat in live_data_patterns:
        if re.search(pat, msg_lower):
            return True
    return False


async def handle_brain_learn(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    if "topic" in data and "content" in data:
        topic = (data.get("topic") or "").strip()
        content = (data.get("content") or "").strip()
        if not topic or not content:
            return web.json_response({"error": "topic y content requeridos"}, status=400)
        source = data.get("source", "ui-manual")
        importance = int(data.get("importance", 7))
        await backend.cerebro.guardar_conocimiento(topic, content, source, importance)
        return web.json_response({
            "success": True,
            "schema": "knowledge",
            "topic": topic,
            "source": source,
        })

    prompt = data.get("prompt", "")
    response = data.get("response", "")
    gem = data.get("gem", "general")
    contexto = data.get("contexto", "")
    await backend.cerebro.aprender_interaccion(prompt, response, gem, contexto)
    return web.json_response({
        "success": True,
        "schema": "interaction",
        "gem": gem,
    })


async def handle_brain_knowledge(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    tema = request.query.get("tema")
    conocimientos = backend.cerebro.obtener_conocimientos(tema)
    return web.json_response({"knowledge": conocimientos})


async def handle_brain_export(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    result = backend.cerebro.exportar()
    return web.json_response(result)


async def handle_brain_conversations(request: web.Request) -> web.Response:
    """Devuelve las ultimas N conversaciones (auto-aprendizaje)."""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        limit = int(request.query.get("limit", "20"))
    except ValueError:
        limit = 20
    limit = max(1, min(limit, 200))
    import sqlite3
    db_path = backend.cerebro.db_path
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, fecha, gem, mensaje, respuesta, contexto "
        "FROM conversaciones WHERE mensaje != '' AND respuesta != '' "
        "ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return web.json_response({
        "conversations": [
            {
                "id": r["id"],
                "timestamp": r["fecha"],
                "gem": r["gem"],
                "prompt": r["mensaje"],
                "response": r["respuesta"],
                "context": r["contexto"],
            }
            for r in rows
        ],
    })


async def handle_brain_learn_from_url(request: web.Request) -> web.Response:
    """URL -> Scholar (fetch+analyze) -> Sage (persist) -> Cerebro (knowledge)."""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    url = (data.get("url") or "").strip()
    topic_hint = (data.get("topic") or "").strip()
    importance = int(data.get("importance", 7))

    if not url:
        return web.json_response({"error": "url requerido"}, status=400)
    if not (url.startswith("http://") or url.startswith("https://")):
        return web.json_response({"error": "url debe empezar con http:// o https://"}, status=400)

    try:
        from src.agents.scholar_gem import ScholarGem
        from src.agents.sage_gem import SageGem
        from src.agents.biblioteca_gem import BibliotecaGem
    except Exception as e:
        return web.json_response({"error": f"gems no disponibles: {e}"}, status=500)

    scholar = ScholarGem()
    sage = SageGem()
    biblioteca = BibliotecaGem()

    try:
        analysis = await scholar.analyze_link(url)
        if not analysis.get("success"):
            return web.json_response({
                "error": "Scholar no pudo leer la URL",
                "details": analysis,
            }, status=502)
    except Exception as e:
        return web.json_response({"error": f"scholar error: {e}"}, status=500)

    preview = analysis.get("content_preview", "")
    word_count = analysis.get("word_count", 0)

    topic = topic_hint or f"web:{url.split('//', 1)[-1].split('/', 1)[0]}"
    content = (
        f"Source: {url}\n"
        f"Words: {word_count}\n"
        f"Auto-fetched by Scholar.\n\n"
        f"--- preview ---\n{preview}"
    )

    try:
        sage_result = await sage.analyze_and_persist(content, url, "web", topic=topic)
    except Exception as e:
        sage_result = {"success": False, "error": str(e)}

    try:
        await backend.cerebro.aprender_interaccion(
            f"Aprender de URL: {url}",
            f"Sage persistido: {sage_result.get('fact_id','?')}. Preview: {preview[:200]}",
            "scholar",
        )
    except Exception:
        pass

    try:
        biblio_result = await biblioteca.organize(
            title=topic,
            content=f"# {topic}\n\nSource: {url}\nWords: {word_count}\n{preview[:500]}",
            category="Web",
            tags=["auto-ingested", "web", topic],
        )
        biblio_ok = biblio_result.get("success", False)
    except Exception:
        biblio_ok = False

    return web.json_response({
        "success": True,
        "topic": topic,
        "url": url,
        "word_count": word_count,
        "sage_fact_id": sage_result.get("fact_id"),
        "biblioteca_indexed": biblio_ok,
        "preview": preview[:500],
    })


# ==================== INTEGRATIONS ENDPOINTS ====================

async def handle_codex_status(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.codex.status())


async def handle_codex_run(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    result = await backend.codex.run(
        data.get("prompt", ""), data.get("project", "supernexus-v2"),
        data.get("gem", "developer"), data.get("context"),
    )
    return web.json_response(result)


async def handle_rcon_servers(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response({"servers": backend.rcon_manager.list_servers()})


_RCON_ACTION_MAP = {
    "wipe": "rcon.wipe", "reset": "rcon.wipe",
    "ban": "rcon.ban", "banid": "rcon.ban",
    "kick": "rcon.kick",
    "unban": "rcon.unban",
    "playerlist": "rcon.list_players", "player.list": "rcon.list_players",
    "serverinfo": "rcon.server_info", "status": "rcon.server_info",
    "say": "rcon.message", "server.say": "rcon.message", "chat.say": "rcon.message",
    "save": "rcon.save",
    "restart": "rcon.restart",
    "quit": "rcon.stop",
}


def _rcon_action(command: str) -> str:
    """Map an RCON command to a permission action key."""
    base = command.strip().lower().split()[0] if command.strip() else ""
    return _RCON_ACTION_MAP.get(base, "rcon.server_info")  # unknown commands default to info


async def handle_rcon_command(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    server_name = data.get("server", "")
    command = data.get("command", "")

    if not command:
        return web.json_response({"error": "No command provided"}, status=400)

    # Permission check
    action = _rcon_action(command)
    verdict = permission_manager.check_and_request("latamrust", action, {"command": command, "server": server_name})
    if verdict.level == "never":
        return web.json_response({
            "success": False, "error": f"Permission denied: {action}",
            "verdict": {"action": action, "level": "never", "reason": verdict.reason},
        }, status=403)
    if verdict.level == "ask" and not verdict.pending_token:
        # auto_approved (NEXUS_CONFIRM_DISABLED) — proceed
        pass
    elif verdict.level == "ask" and verdict.pending_token:
        return web.json_response({
            "success": False, "error": f"HITL required: {action}",
            "verdict": {
                "action": action, "level": "ask",
                "pending_token": verdict.pending_token,
                "instructions": "POST /api/permissions/resolve with {token, approve: true|false}",
            },
        }, status=202)

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


async def handle_guardian_status(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.guardian.get_status())


async def handle_guardian_audit(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
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
    except Exception:
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
    except Exception:
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
    except Exception:
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
    except Exception:
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
    except Exception:
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
    except Exception:
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
    except Exception:
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
    except Exception:
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
    if not backend.nexus_hive:
        return web.json_response({"status": "unavailable", "nodes": []})
    return web.json_response(backend.nexus_hive.get_status())


async def handle_hive_send_command(request: web.Request) -> web.Response:
    """Envía comando a un nodo via NexusHive"""
    backend: SuperNEXUSBackend = request.app["backend"]
    if not backend.nexus_hive:
        return web.json_response({"error": "NexusHive unavailable"}, status=503)
    try:
        data = await request.json()
    except Exception:
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
    if not backend.nexus_hive:
        return web.json_response({"nodes": []})
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


EXEC_ALLOWED_BINARIES = {
    # Dev tools
    "git.exe", "python.exe", "python3.exe", "pip.exe", "pip3.exe",
    "node.exe", "npm.exe", "npx.cmd", "code.exe", "gh.exe",
    "docker.exe", "wsl.exe", "cargo.exe", "rustc.exe", "go.exe",
    # System info
    "whoami.exe", "hostname.exe", "ver.exe",
    "tasklist.exe", "systeminfo.exe", "ipconfig.exe",
    "ping.exe", "netstat.exe", "tracert.exe", "nslookup.exe",
    # File inspection (read-only)
    "find.exe", "findstr.exe", "fc.exe", "comp.exe",
}

CMD_NATIVE = {
    "echo": lambda args: (" ".join(args), None),
    "cls": lambda args: ("", None),
    "clear": lambda args: ("", None),
    "pwd": lambda args: (_resolve_current_cwd(args), None),
    "dir": lambda args: _native_dir(args),
    "type": lambda args: _native_type(args),
    "ls": lambda args: _native_dir(args),
    "cat": lambda args: _native_type(args),
}


def _resolve_current_cwd(args: list[str]) -> str:
    """Resolve cwd for pwd command."""
    return os.getcwd()


def _native_dir(args: list[str]) -> tuple[str, str | None]:
    """Implement dir/ls natively in Python (no subprocess)."""
    path = "."
    show_size = False
    recursive = False
    for a in args:
        if a.lower() in ("/s", "-r", "-recursive", "--recursive"):
            recursive = True
        elif a.lower() in ("/q", "-s", "--size"):
            show_size = True
        elif not a.startswith("/") and not a.startswith("-"):
            path = a
    try:
        p = Path(path) if path != "." else Path(".")
    except Exception:
        return (f"Invalid path: {path}", "error")
    if not p.exists():
        return (f"Path not found: {path}", "error")
    if p.is_file():
        return (str(p), None)
    try:
        if recursive:
            lines = []
            for root, dirs, files in os.walk(str(p)):
                rel = Path(root).relative_to(p)
                prefix = "." if rel == Path(".") else str(rel)
                lines.append(f"\n{prefix}\\")
                for d in sorted(dirs):
                    lines.append(f"    {d}/")
                for f in sorted(files):
                    fp = Path(root) / f
                    if show_size:
                        lines.append(f"    {f} ({fp.stat().st_size:,} bytes)")
                    else:
                        lines.append(f"    {f}")
            return ("\n".join(lines), None)
        else:
            entries = sorted(os.listdir(str(p)))
            result = []
            for e in entries:
                fp = p / e
                if fp.is_dir():
                    result.append(f"{e}/")
                else:
                    if show_size:
                        result.append(f"{e} ({fp.stat().st_size:,} bytes)")
                    else:
                        result.append(e)
            return ("\n".join(result) if result else "(empty)", None)
    except PermissionError:
        return (f"Permission denied: {path}", "error")
    except Exception as e:
        return (str(e), "error")


def _native_type(args: list[str]) -> tuple[str, str | None]:
    """Implement type/cat natively in Python (no subprocess)."""
    if not args:
        return ("Usage: type <file>", "error")
    path = args[0]
    p = _validate_fs_path(path)
    if p is None:
        return (f"Path not allowed: {path}", "error")
    if not p.exists():
        return (f"File not found: {path}", "error")
    if p.is_dir():
        return (f"Cannot type directory: {path}", "error")
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        max_chars = 50000
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n...(truncated, {len(content)} total chars)"
        return (content, None)
    except Exception as e:
        return (f"Error reading {path}: {e}", "error")


def _check_exec_token(request: web.Request) -> tuple[str | None, int | None]:
    """Always-on token guard for /api/fs/exec and /api/fs/write.
    Independent of NEXUS_AUTH. Peers use NEXUS_API_KEY or NEXUS_EXEC_TOKEN.
    Returns (error, status) or (None, None) if allowed.
    """
    token = os.environ.get("NEXUS_EXEC_TOKEN") or os.environ.get("NEXUS_API_KEY") or ""
    if not token:
        return (None, None)
    host = request.headers.get("Host", "").split(":")[0]
    if host in ("127.0.0.1", "localhost", "::1"):
        return (None, None)
    header = request.headers.get("X-Nexus-Token", "")
    if not header:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            header = auth[7:]
    if header == token:
        return (None, None)
    return ("Unauthorized: valid NEXUS_EXEC_TOKEN or Authorization: Bearer required for remote exec", 401)


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
    """Write file content (path-validated + exec token guard)"""
    err, status = _check_exec_token(request)
    if err:
        return web.json_response({"error": err}, status=status)
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
    """Execute shell command (allowlist + always-on token guard + no shell=True)"""
    import asyncio
    try:
        data = await request.json()
        command = data.get("command", "")
        cwd = data.get("cwd", ".")
        if not command.strip():
            return web.json_response({"error": "Empty command"}, status=400)

        err, status = _check_exec_token(request)
        if err:
            return web.json_response({"error": err}, status=status)

        parts = shlex.split(command.strip())
        binary = parts[0].lower()

        native = CMD_NATIVE.get(binary)
        if native:
            stdout, stderr = native(parts[1:])
            return web.json_response({
                "stdout": stdout or "",
                "stderr": stderr or "",
                "returncode": 0 if stderr is None else 1,
            })

        resolved = shutil.which(parts[0])
        if not resolved:
            return web.json_response(
                {"error": f"Command not found: {parts[0]}. See NEXUS_EXEC_ALLOWED or use native aliases (dir, type, echo, cls)"},
                status=400,
            )
        if os.path.basename(resolved).lower() not in EXEC_ALLOWED_BINARIES:
            return web.json_response(
                {"error": f"Command not allowed: {parts[0]}. See NEXUS_EXEC_ALLOWED env var for allowlist customization"},
                status=403,
            )

        cwd_path = _validate_fs_path(cwd) or Path(__file__).resolve().parents[2]
        proc = await asyncio.create_subprocess_exec(
            resolved, *parts[1:],
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


async def handle_mcp_hub_search(request: web.Request) -> web.Response:
    """MCP Hub — busca servidores MCP de múltiples fuentes."""
    query = request.query.get("q", "")
    try:
        from src.core.mcp_hub import unified_search
        entries, warnings = await unified_search(query=query)
        return web.json_response({
            "entries": [
                {
                    "source": e.source,
                    "id": e.id,
                    "name": e.name,
                    "description": e.description,
                    "trust": e.trust,
                    "installed": e.installed,
                    "transport": e.transport,
                    "tags": e.tags,
                }
                for e in entries
            ],
            "warnings": warnings,
            "total": len(entries),
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_mcp_tools_cache(request: web.Request) -> web.Response:
    """MCP Tools Cache — estado de caché de tools por servidor."""
    from src.core.mcp_tools_cache import list_probes
    probes = list_probes()
    return web.json_response({
        "probes": {
            name: {
                "status": p.status,
                "tool_count": p.tool_count,
                "tool_names": p.tool_names,
                "latency_ms": p.latency_ms,
                "error": p.error,
                "tested_at": p.tested_at,
            }
            for name, p in probes.items()
        }
    })


async def handle_mcp_execute(request: web.Request) -> web.Response:
    """Ejecuta herramienta MCP"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
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
    except Exception:
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
    except Exception:
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
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    task_type = data.get("task_type", "coding")
    complexity = data.get("complexity", "medium")
    result = backend.token_optimizer.select_model(task_type, complexity)
    return web.json_response(result)


async def handle_mcp_discover(request: web.Request) -> web.Response:
    """GET /api/mcp/discover — Scan mcp_servers.json files for server configs."""
    try:
        from src.bridges.mcp_autodiscovery import discover_servers, SCAN_PATHS
        servers = discover_servers()
        return web.json_response({
            "count": len(servers),
            "servers": [
                {k: v for k, v in s.items() if k != "_source"}
                for s in servers
            ],
            "scan_paths": [str(p.resolve()) for p in SCAN_PATHS],
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_checkpoint_metrics(request: web.Request) -> web.Response:
    """GET /api/checkpoint/metrics — Checkpoint contract validation stats per gema."""
    try:
        from src.core.checkpoint_metrics import get_metrics
        return web.json_response(get_metrics())
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_token_report(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    report = backend.token_optimizer.generate_report()
    return web.json_response({"report": report})


async def handle_token_compress(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception:
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
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Request-Id, Authorization, X-API-Key"
    response.headers["Access-Control-Expose-Headers"] = "X-Request-Id"
    return response


@web.middleware
async def request_id_middleware(request: web.Request, handler):
    """
    Inject a request_id propagable through the request lifecycle and echo it
    back on the response. Honors caller-supplied X-Request-Id when present
    (for end-to-end tracing); generates one otherwise.

    Pattern: openfang observability foundation. Once every request carries a
    correlatable ID, structured logging and (future) event-bus events can be
    joined across subsystems without ambiguity.
    """
    import uuid
    rid = request.headers.get("X-Request-Id", "").strip() or uuid.uuid4().hex[:16]
    # Cap length defensively to avoid log injection via giant headers.
    rid = rid[:64]
    request["request_id"] = rid
    # Propagate via contextvars so non-aiohttp consumers (LLM provider,
    # event emitters in worker tasks) can read it without the request obj.
    try:
        from src.observability.context import set_request_id
        set_request_id(rid)
    except Exception:
        pass
    try:
        response = await handler(request)
    except Exception:
        # Re-raise after logging; aiohttp returns 500 with no headers we control.
        logger.exception("request_id=%s unhandled exception in %s %s",
                         rid, request.method, request.path)
        raise
    try:
        response.headers["X-Request-Id"] = rid
    except Exception:
        pass
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


async def handle_mcp_health(request: web.Request) -> web.Response:
    """GET /api/mcp/health?restart=1 — Per-server health probe.

    Inspects subprocess.poll() (no JSON-RPC traffic — can't time out on a
    stuck server). When restart=1, dead-but-was-connected auto_start
    servers are relaunched once and the result is reflected in the row.

    Each detected death emits MCP_SERVER_FAILED; each successful restart
    emits MCP_SERVER_STARTED.
    """
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        restart = request.query.get("restart", "0") == "1"
        mcp = getattr(backend.director, "mcp_client", None)
        if mcp is None or not hasattr(mcp, "health_probe"):
            return web.json_response({"servers": {}, "detail": "mcp_client not present"})
        report = await mcp.health_probe(attempt_restart=restart)
        return web.json_response({
            "restart_attempted": restart,
            "total": len(report),
            "alive": sum(1 for r in report.values() if r["process_alive"]),
            "connected": sum(1 for r in report.values() if r["connected"]),
            "restarted": sum(1 for r in report.values() if r.get("restarted")),
            "servers": report,
        })
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_dmn_stats(request: web.Request) -> web.Response:
    """GET /api/dmn/stats — DefaultModeNetwork counters + interval."""
    try:
        from src.brain.dmn import dmn
        return web.json_response({
            "running": dmn._running,
            "interval_s": dmn.interval,
            "stats": dmn.get_stats(),
        })
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_dmn_tick(request: web.Request) -> web.Response:
    """POST /api/dmn/tick — Force a synchronous DMN scan. Useful for tests
    or operator-driven 'rescan now'. Returns the candidates produced."""
    try:
        from src.brain.dmn import dmn
        cands = dmn.tick()
        return web.json_response({
            "candidates": [
                {"category": c.category, "level": c.level, "title": c.title,
                 "user_facing": c.user_facing}
                for c in cands
            ],
            "count": len(cands),
        })
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)





async def handle_workers_stalled(request: web.Request) -> web.Response:
    """GET /api/workers/stalled?threshold_minutes=30 — Watchdog report.
    Returns workers that haven't run within max(threshold, 2*interval).
    Each call also emits WORKER_STALLED events to the bus for live dashboards.
    """
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        thresh = int(request.query.get("threshold_minutes", "30"))
    except Exception:
        thresh = 30
    try:
        # Multiple historical attr names — try all before giving up.
        bw = None
        for attr in ("worker_manager", "background_workers", "background_worker_manager"):
            cand = getattr(backend, attr, None) or getattr(backend.director, attr, None)
            if cand is not None and hasattr(cand, "detect_stalled"):
                bw = cand
                break
        if bw is None:
            return web.json_response({"stalled": [], "detail": "worker_manager not present or lacks detect_stalled"})
        stalled = bw.detect_stalled(threshold_minutes=thresh)
        return web.json_response({
            "threshold_minutes": thresh,
            "stalled_count": len(stalled),
            "stalled": stalled,
        })
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_sessions_catalog(request: web.Request) -> web.Response:
    """GET /api/sessions/catalog — Catalog of every session known to disk
    (~/.nexus/sessions/<sid>/) PLUS in-memory budget rows. Returns one
    row per unique session_id with whatever metadata is available:
        {session_id, has_logs, has_budget, request_count, total_tokens,
         cost_usd, last_update, summary_status}

    Foundation for a multi-surface UI (jcode pattern) — the UI can ask
    'what sessions can I attach to?' without having to crawl disk."""
    from pathlib import Path as _P
    out: Dict[str, Dict[str, Any]] = {}

    # 1) Disk-tracked sessions (those with runtime_logs)
    try:
        base = _P.home() / ".nexus" / "sessions"
        if base.exists():
            for d in base.iterdir():
                if not d.is_dir():
                    continue
                sid = d.name
                row: Dict[str, Any] = {"session_id": sid, "has_logs": False, "has_budget": False}
                summary_p = d / "logs" / "summary.json"
                if summary_p.exists():
                    row["has_logs"] = True
                    try:
                        s = json.loads(summary_p.read_text(encoding="utf-8"))
                        row["summary_status"] = s.get("status")
                        row["finished_at"] = s.get("finished_at")
                        row["total_tokens_in"] = s.get("total_tokens_in")
                        row["total_tokens_out"] = s.get("total_tokens_out")
                        row["total_cost_usd"] = s.get("total_cost_usd")
                    except Exception:
                        pass
                out[sid] = row
    except Exception as e:
        logger.debug(f"sessions_list disk scan failed: {e}")

    # 2) Budget tracker (in-memory)
    try:
        from src.observability.budget_tracker import tracker
        for sid, b in tracker.snapshot().items():
            row = out.setdefault(sid, {"session_id": sid, "has_logs": False, "has_budget": False})
            row["has_budget"] = True
            row["request_count"] = b.get("request_count")
            row["total_tokens"] = b.get("total_tokens")
            row["cost_usd"] = b.get("cost_usd")
            row["last_update"] = b.get("last_update")
            if b.get("cap_exceeded"):
                row["cap_exceeded"] = True
    except Exception as e:
        logger.debug(f"sessions_list budget scan failed: {e}")

    rows = list(out.values())
    rows.sort(key=lambda r: r.get("last_update") or r.get("finished_at") or "", reverse=True)
    return web.json_response({"count": len(rows), "sessions": rows})


async def handle_session_attach(request: web.Request) -> web.Response:
    """POST /api/sessions/{session_id}/attach — Confirm a session exists
    and return its bundle: budget + summary + recent_messages (if backend
    exposes them). Idempotent — does NOT mutate session state, just
    surfaces what the UI needs to render the surface.

    For a future multi-surface UI: the same session can be attached to
    many client surfaces simultaneously (jcode model)."""
    sid = request.match_info.get("session_id", "").strip()
    if not sid or "/" in sid or ".." in sid:
        return web.json_response({"error": "invalid session_id"}, status=400)

    bundle: Dict[str, Any] = {"session_id": sid, "attached_at": datetime.now().isoformat()}

    # budget
    try:
        from src.observability.budget_tracker import tracker
        bundle["budget"] = tracker.session_snapshot(sid)
    except Exception:
        bundle["budget"] = None

    # runtime summary
    try:
        from src.observability.runtime_logs import session_logger
        bundle["log_summary"] = session_logger(sid).read_summary()
    except Exception:
        bundle["log_summary"] = None

    # Optional: backend's session-recent-messages if available.
    try:
        backend: SuperNEXUSBackend = request.app["backend"]
        sm = getattr(backend.director, "session_manager", None) \
             or getattr(backend, "session_manager", None)
        if sm is not None:
            for getter in ("get_recent_messages", "recent_messages", "get_messages"):
                fn = getattr(sm, getter, None)
                if callable(fn):
                    try:
                        msgs = fn(sid, 10) if "id" in fn.__code__.co_varnames[:2] else fn(10)
                        bundle["recent_messages"] = msgs
                        break
                    except Exception:
                        continue
    except Exception:
        pass

    found = bool(bundle.get("budget") or bundle.get("log_summary"))
    bundle["found"] = found
    return web.json_response(bundle)


async def handle_session_budget(request: web.Request) -> web.Response:
    """GET /api/sessions/{session_id}/budget — token + cost snapshot.
    Updated automatically from LLM_TOKEN_USAGE events. If
    NEXUS_MAX_USD_PER_SESSION is set, cap_exceeded flips true when
    accumulated cost crosses it."""
    sid = request.match_info.get("session_id", "").strip()
    if not sid or "/" in sid or ".." in sid:
        return web.json_response({"error": "invalid session_id"}, status=400)
    try:
        from src.observability.budget_tracker import tracker
        snap = tracker.session_snapshot(sid)
        if snap is None:
            return web.json_response({
                "session_id": sid, "exists": False,
                "detail": "no LLM activity recorded for this session yet",
            })
        snap["exists"] = True
        return web.json_response(snap)
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_budgets_all(request: web.Request) -> web.Response:
    """GET /api/budget/all — every tracked session (for ops dashboards)."""
    try:
        from src.observability.budget_tracker import tracker
        snap = tracker.snapshot()
        total_cost = round(sum(b.get("cost_usd", 0.0) for b in snap.values()), 6)
        return web.json_response({
            "sessions": len(snap),
            "total_cost_usd": total_cost,
            "budgets": snap,
            "cap_env": os.environ.get("NEXUS_MAX_USD_PER_SESSION", ""),
        })
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_session_logs(request: web.Request) -> web.Response:
    """GET /api/sessions/{session_id}/logs — return L1 summary + tail counts.
    Optional ?tail=N returns last N lines of L2 details + L3 tool_logs.

    Pattern: aden-hive runtime_log_store. Useful for cost/audit/debug
    without rummaging through SQLite or wading through the noisy app log.
    """
    sid = request.match_info.get("session_id", "").strip()
    if not sid or "/" in sid or ".." in sid:
        return web.json_response({"error": "invalid session_id"}, status=400)
    try:
        tail = int(request.query.get("tail", "0") or 0)
    except Exception:
        tail = 0
    try:
        from src.observability.runtime_logs import session_logger
        sl = session_logger(sid)
        out: Dict[str, Any] = {"stats": sl.stats(), "summary": sl.read_summary()}
        if tail > 0:
            from pathlib import Path as _Path
            for fname, key in (("details.jsonl", "details_tail"),
                               ("tool_logs.jsonl", "tool_logs_tail")):
                p = _Path(sl._dir) / fname
                if p.exists():
                    try:
                        lines = p.read_text(encoding="utf-8").splitlines()[-tail:]
                        out[key] = [json.loads(line) for line in lines if line.strip()]
                    except Exception as e:
                        out[key] = {"error": str(e)}
                else:
                    out[key] = []
        return web.json_response(out)
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_events_stats(request: web.Request) -> web.Response:
    """GET /api/events/stats — Observability event-stream stats."""
    try:
        from src.observability.event_stream import bus
        return web.json_response(bus.stats())
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_events_stream(request: web.Request) -> web.StreamResponse:
    """GET /api/events/stream?types=... — SSE feed of live events.

    Query: types=comma,separated (e.g. types=chat.error,tool.loop.detected).
    Omit for all types. Disconnect when the client closes the connection.
    """
    from src.observability.event_stream import bus, EventType
    filt = request.query.get("types", "")
    types = None
    if filt:
        wanted = {t.strip() for t in filt.split(",") if t.strip()}
        types = {et for et in EventType if et.value in wanted}
    response = web.StreamResponse(
        status=200,
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
    await response.prepare(request)
    label = f"sse-{request.get('request_id', 'anon')}"
    try:
        async for ev in bus.subscribe(types=types, label=label):
            payload = json.dumps(ev.to_dict(), ensure_ascii=False)
            await response.write(f"event: {ev.type.value}\ndata: {payload}\n\n".encode("utf-8"))
    except (asyncio.CancelledError, ConnectionResetError):
        pass
    finally:
        try:
            await response.write_eof()
        except Exception:
            pass
    return response


# ==================== SETUP WIZARD BACKEND ====================
# openakita pattern: backend for a "Quick (3 min) / Full (10 min)" first-run
# wizard. Persists to ~/.nexus/setup.json so the wizard doesn't reappear.
# UI is separate — these endpoints provide the data layer.

def _setup_state_path():
    from pathlib import Path
    return Path.home() / ".nexus" / "setup.json"


def _load_setup_state() -> dict:
    import json as _json
    p = _setup_state_path()
    if not p.exists():
        return {"completed": False, "steps": {}}
    try:
        return _json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"completed": False, "steps": {}, "_error": "state file corrupt"}


def _save_setup_state(state: dict):
    # Canonical atomic write (odysseus pattern, see src/security/atomic_io.py).
    from src.security.atomic_io import atomic_write_json
    atomic_write_json(_setup_state_path(), state, mode=0o644)


async def handle_setup_state(request: web.Request) -> web.Response:
    """GET /api/setup/state — current wizard progress + which steps remain."""
    state = _load_setup_state()
    # Always derive 'next_step' from completed flags so UI doesn't track it.
    order = ["python", "disk", "ollama", "llm_endpoint", "first_user"]
    completed_steps = set(state.get("steps", {}).keys())
    next_step = next((s for s in order if s not in completed_steps), None)
    return web.json_response({
        **state,
        "next_step": next_step,
        "auth_enabled": os.environ.get("NEXUS_AUTH", "0") == "1",
    })


async def handle_setup_preflight(request: web.Request) -> web.Response:
    """GET /api/setup/preflight — boot-readiness checks for the wizard.
    Lighter than /api/doctor: only what blocks a first-run install."""
    import shutil
    import sys
    from pathlib import Path as _Path

    checks = {}
    # python
    checks["python"] = {
        "ok": sys.version_info >= (3, 10),
        "detail": f"Python {sys.version.split()[0]}",
        "fix": "Install Python 3.10+" if sys.version_info < (3, 10) else None,
    }
    # disk
    free_gb = shutil.disk_usage(_Path.home()).free / (1024 ** 3)
    checks["disk"] = {
        "ok": free_gb >= 5,
        "detail": f"{free_gb:.1f} GB free under {_Path.home()}",
        "fix": "Free at least 5 GB before installing Ollama models" if free_gb < 5 else None,
    }
    # data dir writable
    nexus_dir = _Path.home() / ".nexus"
    try:
        nexus_dir.mkdir(parents=True, exist_ok=True)
        test_file = nexus_dir / ".write_test"
        test_file.write_text("x", encoding="utf-8")
        test_file.unlink()
        checks["data_dir"] = {"ok": True, "detail": str(nexus_dir), "fix": None}
    except Exception as e:
        checks["data_dir"] = {"ok": False, "detail": str(e),
                              "fix": f"Make {nexus_dir} writable"}
    # ollama (optional but recommended)
    try:
        import httpx as _httpx
        async with _httpx.AsyncClient(timeout=3.0) as c:
            r = await c.get("http://localhost:11434/api/tags")
            tags = r.json().get("models", []) if r.status_code == 200 else []
            checks["ollama"] = {
                "ok": r.status_code == 200,
                "detail": f"{len(tags)} models available" if r.status_code == 200 else f"HTTP {r.status_code}",
                "fix": None if r.status_code == 200 else "Start Ollama: `ollama serve`",
                "optional": True,
            }
    except Exception as e:
        checks["ollama"] = {"ok": False, "detail": f"unreachable: {e}",
                            "fix": "Install + start Ollama (optional, recommended)",
                            "optional": True}

    blocking_fails = [k for k, v in checks.items()
                      if not v["ok"] and not v.get("optional")]
    return web.json_response({
        "ready": len(blocking_fails) == 0,
        "blocking": blocking_fails,
        "checks": checks,
    })


async def handle_setup_save_step(request: web.Request) -> web.Response:
    """POST /api/setup/step — Save one wizard step. Body:
        {"step": "llm_endpoint", "data": {...}, "complete_wizard": false}
    'data' is opaque to the backend (UI defines the schema per step).
    Secrets like api_key are persisted verbatim — same trust model as .env.
    """
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    step = (body.get("step") or "").strip()
    if not step:
        return web.json_response({"error": "'step' required"}, status=400)
    data = body.get("data") or {}
    if not isinstance(data, dict):
        return web.json_response({"error": "'data' must be object"}, status=400)

    state = _load_setup_state()
    state.setdefault("steps", {})[step] = {
        "data": data,
        "saved_at": datetime.now().isoformat(),
    }
    if body.get("complete_wizard"):
        state["completed"] = True
        state["completed_at"] = datetime.now().isoformat()
    try:
        _save_setup_state(state)
    except Exception as e:
        return web.json_response({"error": f"persist failed: {e}"}, status=500)
    return web.json_response({"ok": True, "step": step, "completed": state.get("completed", False)})


async def handle_setup_reset(request: web.Request) -> web.Response:
    """POST /api/setup/reset — Forget wizard state (re-run setup)."""
    try:
        p = _setup_state_path()
        if p.exists():
            p.unlink()
        return web.json_response({"ok": True, "message": "setup state cleared"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_gemas_import(request: web.Request) -> web.Response:
    """POST /api/gemas/import (multipart with 'file' field) — install a
    .nexus-gema package into ~/.nexus/gemas/. Verifies sha256 + runs the
    prompt scanner. Restart or hit /api/v3/plugins to load."""
    try:
        reader = await request.multipart()
        field = await reader.next()
        if field is None or field.name != "file":
            return web.json_response({"error": "expected multipart field 'file'"}, status=400)
        # cap upload at 5 MB defensively
        data = await field.read(decode=False)
        if len(data) > 5 * 1024 * 1024:
            return web.json_response({"error": "package too large (>5MB)"}, status=413)
        # write to a tempfile and hand off
        import tempfile
        from pathlib import Path as _P
        tmp = _P(tempfile.mkstemp(suffix=".nexus-gema")[1])
        tmp.write_bytes(data)
        try:
            from src.plugins.package import import_gema, PackageError
            result = import_gema(tmp)
            return web.json_response(result)
        except PackageError as e:
            return web.json_response({"ok": False, "error": str(e)}, status=400)
        finally:
            try: tmp.unlink()
            except Exception: pass
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_scratchpad_get(request: web.Request) -> web.Response:
    """GET /api/sessions/{session_id}/scratchpad — persistent working memory."""
    sid = request.match_info.get("session_id", "").strip()
    if not sid:
        return web.json_response({"error": "invalid session_id"}, status=400)
    try:
        from src.brain import scratchpad as sp
        return web.json_response({
            "session_id": sid,
            "content": sp.read(sid),
            "exists": (sp._path(sid)).exists(),
        })
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_scratchpad_post(request: web.Request) -> web.Response:
    """POST /api/sessions/{session_id}/scratchpad  Body: {content?, append?}"""
    sid = request.match_info.get("session_id", "").strip()
    if not sid:
        return web.json_response({"error": "invalid session_id"}, status=400)
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    try:
        from src.brain import scratchpad as sp
        if "append" in body and body["append"]:
            sp.append(sid, str(body["append"]))
            action = "appended"
        elif "content" in body:
            sp.write(sid, str(body["content"]))
            action = "written"
        elif body.get("clear"):
            sp.clear(sid)
            action = "cleared"
        else:
            return web.json_response({"error": "body must have 'content', 'append', or 'clear'"}, status=400)
        return web.json_response({"ok": True, "action": action, "session_id": sid})
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_confirm_request(request: web.Request) -> web.Response:
    """POST /api/confirm/request body: {op, payload?} -> {token, expires_in_s}"""
    try:
        body = await request.json()
        from src.security.confirmation_gate import gate
        return web.json_response(gate.request(op=body["op"], payload=body.get("payload")))
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=400)


async def handle_confirm_respond(request: web.Request) -> web.Response:
    """POST /api/confirm body: {token, approve:bool}"""
    try:
        body = await request.json()
        from src.security.confirmation_gate import gate
        return web.json_response(gate.respond(token=body["token"],
                                               approve=bool(body.get("approve"))))
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=400)


async def handle_confirm_pending(request: web.Request) -> web.Response:
    """GET /api/confirm/pending — list ops awaiting approval."""
    from src.security.confirmation_gate import gate
    return web.json_response({"pending": gate.pending_list()})


async def handle_skill_suggest(request: web.Request) -> web.Response:
    """GET /api/skills/suggest?context=... — procedural memory rank."""
    ctx = request.query.get("context", "")
    try:
        limit = int(request.query.get("limit", "5"))
    except Exception:
        limit = 5
    try:
        from src.brain.procedural import suggest_skill
        return web.json_response({"context_len": len(ctx),
                                  "suggestions": suggest_skill(ctx, limit=limit)})
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_skill_record(request: web.Request) -> web.Response:
    """POST /api/skills/record body: {skill, context, outcome, gem?, duration_ms?, error?}"""
    try:
        body = await request.json()
        from src.brain.procedural import record_invocation
        return web.json_response(record_invocation(
            skill=body["skill"], context=body.get("context", ""),
            outcome=body.get("outcome", "success"),
            gem=body.get("gem", ""),
            duration_ms=int(body.get("duration_ms", 0)),
            error=body.get("error", ""),
        ))
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=400)


async def handle_router_stats(request: web.Request) -> web.Response:
    """GET /api/router/stats — Thompson sampling router per-gem arm stats."""
    try:
        from src.brain.thompson_router import router
        return web.json_response({"groups": router.stats()})
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_router_record(request: web.Request) -> web.Response:
    """POST /api/router/record body: {gem, model, success, weight?} — log outcome."""
    try:
        body = await request.json()
        from src.brain.thompson_router import router
        router.record(
            gem=body["gem"], model=body["model"],
            success=bool(body.get("success", False)),
            weight=float(body.get("weight", 1.0)),
        )
        return web.json_response({"ok": True})
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=400)


async def handle_memory_consolidate(request: web.Request) -> web.Response:
    """POST /api/memory/consolidate?age_days=30 — single consolidation pass.
    Soft-deletes orphan + crowded-topic observations. Idempotent."""
    try:
        age = int(request.query.get("age_days", "30"))
    except Exception:
        age = 30
    try:
        from src.brain.memory_consolidator import consolidate_now
        return web.json_response(consolidate_now(age_days=age))
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_memory_purge(request: web.Request) -> web.Response:
    """POST /api/memory/purge?older_than_days=90 — HARD delete archived obs.
    Admin-only operation (irreversible). Default 90-day grace window."""
    try:
        d = int(request.query.get("older_than_days", "90"))
    except Exception:
        d = 90
    try:
        from src.brain.memory_consolidator import hard_purge_archived
        return web.json_response(hard_purge_archived(older_than_days=d))
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_memory_maintenance(request: web.Request) -> web.Response:
    """POST /api/memory/maintenance?dry_run=true — Sage memory management."""
    try:
        from src.agents.sage_gem import SageGem
        sage = SageGem()
        dry_run = request.query.get("dry_run", "").lower() in ("1", "true", "yes")
        result = sage.run_full_maintenance(dry_run=dry_run)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_a2a_agent_card(request: web.Request) -> web.Response:
    """GET /.well-known/agent.json — A2A (Agent-to-Agent) discovery card.

    Standard endpoint other agents query to learn what we are and how
    to talk to us. Pattern from Google A2A + openfang implementation.
    """
    backend: SuperNEXUSBackend = request.app["backend"]
    # Construct base URL defensively — request.url chokes on hostnames
    # containing ':' (Forwarded headers in some proxy setups).
    try:
        scheme = request.scheme or "http"
        host = request.host or "localhost"
        base = f"{scheme}://{host}"
    except Exception:
        base = nexus_config.get_nexus_url()
    card = {
        "name": "NEXUS IA",
        "version": "3.0",
        "description": "Self-hosted multi-agent AI orchestration system",
        "url": base,
        "provider": {
            "organization": "NEXUS IA project",
            "url": "https://github.com/cjtemer-kaos/supernexus-v2",
        },
        "capabilities": {
            "streaming": True,
            "openai_compatible": True,
            "tool_use": True,
            "mcp_client": True,
            "voice": True,
            "vision": True,
        },
        "endpoints": {
            "chat": f"{base}/api/chat",
            "openai_chat": f"{base}/v1/chat/completions",
            "openai_models": f"{base}/v1/models",
            "events_stream": f"{base}/api/events/stream",
            "doctor": f"{base}/api/doctor",
            "sbom": f"{base}/api/sbom",
            "slash": f"{base}/api/slash",
        },
        "skills": [],  # Populated from gemas below
        "auth": {
            "schemes": ["none"] if os.environ.get("NEXUS_AUTH", "0") != "1" else ["bearer"],
        },
    }
    # Surface gemas as A2A skills
    try:
        from src.plugins.manifest import load_gemas
        gemas = load_gemas()
        card["skills"] = [
            {
                "id": g.name,
                "name": g.name,
                "description": g.description,
                "tags": list(g.tags),
            }
            for g in sorted(gemas.values(), key=lambda x: x.name)
        ]
    except Exception:
        pass
    return web.json_response(card)


async def handle_api_config(request: web.Request) -> web.Response:
    """GET /api/config — configuración dinámica del servidor.
    La UI y otros clientes llaman esto al inicio para autodetectar puerto/host."""
    port = nexus_config.get_port()
    host = nexus_config.get_host()
    # Obtener modelo por defecto actual
    default_model = "deepseek-v4-flash-free"
    try:
        backend = request.app.get("backend")
        if backend and hasattr(backend, 'ai_tools') and backend.ai_tools:
            default_model = backend.ai_tools.get_default_model()
    except Exception:
        pass
    return web.json_response({
        "nexus_url": f"http://{host}:{port}",
        "nexus_ws_url": f"ws://{host}:{port}",
        "port": port,
        "host": host,
        "default_model": default_model,
    })


async def handle_set_default_model(request: web.Request) -> web.Response:
    """POST /api/config/default-model — set & persist default model."""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    model = (body.get("model") or "").strip()
    if not model:
        return web.json_response({"error": "'model' required"}, status=400)
    try:
        backend = request.app.get("backend")
        if not backend or not hasattr(backend, 'ai_tools'):
            return web.json_response({"error": "Backend not ready"}, status=503)
        backend.ai_tools.set_default_model(model)
        return web.json_response({"ok": True, "default_model": backend.ai_tools.get_default_model()})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_cookbook_install(request: web.Request) -> web.Response:
    """POST /api/cookbook/install body: {model:"<name>"} — pull via Ollama.
    Blocks until pull finishes (or fails). Validate against catalog first."""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    model = (body.get("model") or "").strip()
    if not model:
        return web.json_response({"error": "'model' required"}, status=400)
    try:
        from src.core.cookbook import install_model
        return web.json_response(await install_model(model))
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_slash_list(request: web.Request) -> web.Response:
    """GET /api/slash — palette listing for any UI (web, CLI, voice)."""
    try:
        from src.core.slash_commands import registry
        cmds = [c.to_dict() for c in registry.list()]
        return web.json_response({"count": len(cmds), "commands": cmds})
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_slash_execute(request: web.Request) -> web.Response:
    """POST /api/slash {raw:"/persona jarvis", session_id?:"..."} → SlashResult"""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    raw = (body.get("raw") or "").strip()
    if not raw:
        return web.json_response({"error": "'raw' required"}, status=400)
    ctx = {"session_id": body.get("session_id"), "request_id": request.get("request_id")}
    try:
        from src.core.slash_commands import registry
        result = await registry.execute(raw, ctx)
        return web.json_response(result.to_dict())
    except Exception as e:
        return web.json_response({"error": f"{type(e).__name__}: {e}"}, status=500)


async def handle_sbom(request: web.Request) -> web.Response:
    """GET /api/sbom — Software Bill of Materials for this NEXUS install.

    Distribution / audit endpoint: complete inventory of everything that
    can execute code or access data on behalf of the user. Paste the
    output into a security review and the auditor knows the full surface
    area.

    Sections:
      gemas        21 declared, capabilities per gema, source_file
      mcp_servers  registered servers + command + autostart flag
      brain        which brain modules are wired
      ollama       reachable + model list (if any)
      env_flags    relevant NEXUS_* flags currently set
      versions     python, platform, key deps
    """
    import platform as _platform
    import sys as _sys

    backend: SuperNEXUSBackend = request.app["backend"]
    sbom: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "request_id": request.get("request_id"),
    }

    # 1. Gemas (plugins) + capabilities
    try:
        from src.plugins.manifest import load_gemas
        gemas = load_gemas()
        sbom["gemas"] = {
            "count": len(gemas),
            "with_capabilities": sum(1 for g in gemas.values() if g.capabilities),
            "list": [
                {
                    "name": g.name,
                    "model": g.preferred_model,
                    "capabilities": list(g.capabilities),
                    "tags": list(g.tags),
                    "source": str(g.source_file).replace(os.sep, "/").rsplit("supernexus-v2/", 1)[-1],
                }
                for g in sorted(gemas.values(), key=lambda x: x.name)
            ],
        }
    except Exception as e:
        sbom["gemas"] = {"error": str(e)}

    # 2. MCP servers
    try:
        mcp = getattr(backend.director, "mcp_client", None)
        if mcp and hasattr(mcp, "_servers"):
            servers = []
            for n, s in mcp._servers.items():
                servers.append({
                    "name": n,
                    "command": s.command,
                    "args": s.args,
                    "auto_start": getattr(s, "auto_start", False),
                    "connected": s.connected,
                    "tool_count": len(s.tools or []),
                })
            sbom["mcp_servers"] = {
                "count": len(servers),
                "fallbacks_registered": len(getattr(mcp, "_fallbacks", {}) or {}),
                "list": sorted(servers, key=lambda x: x["name"]),
            }
        else:
            sbom["mcp_servers"] = {"count": 0, "detail": "mcp_client missing"}
    except Exception as e:
        sbom["mcp_servers"] = {"error": str(e)}

    # 3. Brain modules
    try:
        director = backend.director
        sbom["brain"] = {
            attr: getattr(director, attr, None) is not None
            for attr in ("identity_brain", "health_brain", "routing_brain",
                         "tool_brain", "memory_brain", "training_brain")
        }
    except Exception as e:
        sbom["brain"] = {"error": str(e)}

    # 4. Ollama snapshot
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as c:
            r = await c.get("http://localhost:11434/api/tags")
            if r.status_code == 200:
                models = r.json().get("models", [])
                sbom["ollama"] = {
                    "reachable": True,
                    "model_count": len(models),
                    "models": sorted([m.get("name") for m in models])[:30],
                }
            else:
                sbom["ollama"] = {"reachable": False, "http": r.status_code}
    except Exception as e:
        sbom["ollama"] = {"reachable": False, "error": str(e)}

    # 5. Relevant NEXUS_* env flags (presence only — never values)
    flag_names = (
        "NEXUS_AUTH", "NEXUS_ENFORCE_CAPS", "NEXUS_MAX_USD_PER_SESSION",
        "NEXUS_DMN_DISABLED", "NEXUS_DMN_INTERVAL_S", "NEXUS_EVENT_LOG",
        "NEXUS_AUTOPILOT_WEBHOOK", "NEXUS_DEBUG_WORKERS",
    )
    sbom["env_flags"] = {
        k: os.environ.get(k) for k in flag_names if os.environ.get(k) is not None
    }

    # 6. Versions
    try:
        import aiohttp as _aiohttp
        sbom["versions"] = {
            "python": ".".join(str(x) for x in _sys.version_info[:3]),
            "platform": _platform.platform(),
            "aiohttp": getattr(_aiohttp, "__version__", "?"),
        }
    except Exception:
        sbom["versions"] = {"python": ".".join(str(x) for x in _sys.version_info[:3])}

    # 7. Quick scores for the auditor's eye
    sbom["summary"] = {
        "gemas": sbom.get("gemas", {}).get("count", 0),
        "mcp_servers": sbom.get("mcp_servers", {}).get("count", 0),
        "brain_modules_wired": sum(1 for v in sbom.get("brain", {}).values() if v is True),
        "ollama_reachable": sbom.get("ollama", {}).get("reachable", False),
        "auth_on": os.environ.get("NEXUS_AUTH", "0") == "1",
        "caps_enforced": os.environ.get("NEXUS_ENFORCE_CAPS", "0") == "1",
    }
    return web.json_response(sbom)


async def handle_doctor_quick(request: web.Request) -> web.Response:
    """
    GET /api/doctor — Self-diagnostic for distribution and user support.

    Pattern from engram (mem_doctor) + openfang (`doctor` CLI command).
    Returns a structured pass/warn/fail report across every major
    subsystem so a new user can paste a single URL response into a bug
    report and get triaged fast.

    This is the LIVE diagnostic (always runs on each call). The legacy
    handle_doctor stub kept a cached-report shape but never had a fresh
    path that didn't require the heavy backend.doctor module — we delegate
    to this quick version when no cached report exists.

    Each section returns:
        {"status": "ok"|"warn"|"fail", "detail": "...", "data": {...}}
    """
    import platform
    import shutil
    import sys
    from pathlib import Path

    backend: SuperNEXUSBackend = request.app["backend"]
    report = {"request_id": request.get("request_id"), "checks": {}}

    def add(name, status, detail, data=None):
        report["checks"][name] = {"status": status, "detail": detail}
        if data is not None:
            report["checks"][name]["data"] = data

    # 1. Python runtime
    add("python", "ok" if sys.version_info >= (3, 10) else "warn",
        f"Python {sys.version.split()[0]} on {platform.platform()}",
        {"version": sys.version_info[:3], "platform": platform.system()})

    # 2. Disk space (warn < 5GB free under HOME)
    try:
        home = Path.home()
        usage = shutil.disk_usage(home)
        free_gb = usage.free / (1024 ** 3)
        add("disk", "ok" if free_gb > 5 else ("warn" if free_gb > 1 else "fail"),
            f"{free_gb:.1f} GB free under {home}",
            {"free_gb": round(free_gb, 1), "total_gb": round(usage.total / (1024 ** 3), 1)})
    except Exception as e:
        add("disk", "warn", f"disk check failed: {e}")

    # 3. NEXUS data dir
    try:
        nexus_dir = Path.home() / ".nexus"
        ok = nexus_dir.exists() and nexus_dir.is_dir()
        add("nexus_data_dir", "ok" if ok else "warn",
            f"{nexus_dir} {'exists' if ok else 'missing — will be auto-created'}",
            {"path": str(nexus_dir), "exists": ok})
    except Exception as e:
        add("nexus_data_dir", "fail", str(e))

    # 4. Brain modules (via NexusApp if present)
    try:
        app_obj = getattr(backend, "app", None)
        director = getattr(backend, "director", None)
        modules = ("identity_brain", "health_brain", "routing_brain",
                   "tool_brain", "memory_brain", "training_brain")
        present = sum(1 for m in modules if getattr(director, m, None) is not None)
        add("brain_modules", "ok" if present == 6 else ("warn" if present >= 3 else "fail"),
            f"{present}/6 brain modules wired",
            {"present": present, "expected": 6})
    except Exception as e:
        add("brain_modules", "fail", str(e))

    # 5. Plugins / gemas
    try:
        gemas = getattr(backend.director, "gemas", {}) or {}
        n = len(gemas)
        add("gemas", "ok" if n >= 20 else ("warn" if n >= 10 else "fail"),
            f"{n} gemas loaded",
            {"count": n, "sample": list(gemas.keys())[:5]})
    except Exception as e:
        add("gemas", "fail", str(e))

    # 6. LLM providers
    try:
        gw = getattr(backend.director, "llm_gateway", None)
        if gw:
            stats = {}
            for m in ("get_status", "status", "get_state"):
                if hasattr(gw, m):
                    candidate = getattr(gw, m)
                    try:
                        stats = candidate() if callable(candidate) else candidate
                        if isinstance(stats, dict) and stats:
                            break
                    except Exception:
                        pass
            providers = stats.get("provider_status", {}) if isinstance(stats, dict) else {}
            if not isinstance(providers, dict):
                providers = {}
            healthy = sum(
                1 for p in providers.values()
                if isinstance(p, dict) and p.get("status") == "healthy"
            )
            total = len(providers)
            # total=0 means we couldn't introspect the gateway shape — warn,
            # not fail (the actual provider may still work via Ollama check #7).
            if total == 0:
                status = "warn"
                detail = "provider list not introspectable (see ollama check)"
            elif healthy >= 1:
                status = "ok"
                detail = f"{healthy}/{total} providers healthy"
            else:
                status = "fail"
                detail = f"{healthy}/{total} providers healthy"
            add("providers", status, detail, {"healthy": healthy, "total": total})
        else:
            add("providers", "warn", "llm_gateway not initialized")
    except Exception as e:
        add("providers", "warn", f"check error: {e}")

    # 7. Ollama reachable
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get("http://localhost:11434/api/tags")
            if r.status_code == 200:
                tags = r.json().get("models", [])
                add("ollama", "ok", f"reachable, {len(tags)} models",
                    {"models_count": len(tags)})
            else:
                add("ollama", "warn", f"HTTP {r.status_code}")
    except Exception as e:
        add("ollama", "warn", f"unreachable: {e}")

    # 8. MCP servers
    try:
        mcp = getattr(backend.director, "mcp_client", None)
        if mcp:
            status = mcp.get_status() if hasattr(mcp, "get_status") else {}
            servers = status.get("servers", {})
            connected = sum(1 for s in servers.values() if s.get("connected"))
            add("mcp", "ok" if connected >= 1 else "warn",
                f"{connected}/{len(servers)} MCP servers connected",
                {"connected": connected, "total": len(servers)})
        else:
            add("mcp", "warn", "mcp_client not initialized")
    except Exception as e:
        add("mcp", "warn", str(e))

    # 9. Memory health (delegate to director.memory_health if present)
    try:
        mh = getattr(backend.director, "memory_health", None)
        if mh and hasattr(mh, "summary"):
            s = mh.summary()
            overall = s.get("overall", "unknown")
            add("memory", "ok" if overall == "healthy" else "warn",
                f"overall: {overall}", s)
        else:
            add("memory", "warn", "memory_health not initialized")
    except Exception as e:
        add("memory", "warn", str(e))

    # 10. Auth mode
    auth_on = os.environ.get("NEXUS_AUTH", "0") == "1"
    add("auth_mode", "ok",
        f"NEXUS_AUTH={'on (Bearer required for /api/* and /v1/*)' if auth_on else 'off (default, single-user local)'}",
        {"opt_in": auth_on})

    # Overall verdict
    statuses = [c["status"] for c in report["checks"].values()]
    if "fail" in statuses:
        report["overall"] = "fail"
    elif "warn" in statuses:
        report["overall"] = "warn"
    else:
        report["overall"] = "ok"
    report["summary"] = (
        f"{statuses.count('ok')} ok, {statuses.count('warn')} warn, "
        f"{statuses.count('fail')} fail"
    )
    return web.json_response(report)


async def handle_fetch_url(request: web.Request) -> web.Response:
    """GET /api/tools/fetch - Fetch content from URL (like opencode's fetch tool)"""
    import aiohttp
    from src.security.ssrf_guard import ensure_safe_url

    url = request.query.get("url", "")
    if not url:
        return web.json_response({"error": "url parameter is required"}, status=400)

    try:
        ensure_safe_url(url)
    except Exception as e:
        return web.json_response({"error": f"SSRF blocked: {e}"}, status=403)

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
    except Exception:
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
    except Exception:
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


# ==================== TEAMS (Parallel Gema Execution) ====================

async def handle_teams_execute(request: web.Request) -> web.Response:
    """POST /api/teams/execute — Ejecutar tarea en paralelo con múltiples gemas"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "JSON inválido"}, status=400)

    task = data.get("task", "").strip()
    if not task:
        return web.json_response({"error": "task es requerido"}, status=400)

    gemas = data.get("gemas", None)
    timeout = float(data.get("timeout", 60.0))
    synthesize = bool(data.get("synthesize", True))
    context = data.get("context", "")

    from src.core.agent_teams import ParallelTeamExecutor
    executor = ParallelTeamExecutor(director=backend.director, hub=getattr(backend, "hub", None))

    execution = await executor.execute(
        task=task,
        gemas=gemas,
        timeout=timeout,
        synthesize=synthesize,
        context=context,
    )

    return web.json_response(executor.to_dict(execution))


async def handle_teams_status(request: web.Request) -> web.Response:
    """GET /api/teams/status/{task_id} — Estado de una ejecución paralela"""
    backend: SuperNEXUSBackend = request.app["backend"]
    exec_id = request.match_info.get("task_id", "")

    from src.core.agent_teams import ParallelTeamExecutor
    executor = ParallelTeamExecutor(director=backend.director, hub=getattr(backend, "hub", None))
    execution = executor.get_execution(exec_id)

    if not execution:
        return web.json_response({"error": "Ejecución no encontrada"}, status=404)

    return web.json_response(executor.to_dict(execution))


async def handle_teams_list(request: web.Request) -> web.Response:
    """GET /api/teams/list — Listar ejecuciones recientes"""
    backend: SuperNEXUSBackend = request.app["backend"]
    limit = int(request.query.get("limit", "20"))

    from src.core.agent_teams import ParallelTeamExecutor
    executor = ParallelTeamExecutor(director=backend.director, hub=getattr(backend, "hub", None))
    execs = executor.list_executions(limit=limit)

    return web.json_response({
        "executions": [executor.to_dict(e) for e in execs],
        "total": len(execs),
    })


async def handle_teams_gemas(request: web.Request) -> web.Response:
    """GET /api/teams/gemas — Listar gemas disponibles para equipos"""
    backend: SuperNEXUSBackend = request.app["backend"]
    gemas_list = []
    if hasattr(backend, 'director') and hasattr(backend.director, 'gemas'):
        for name, gem in backend.director.gemas.items():
            gemas_list.append({
                "name": name,
                "description": gem.description,
                "model": gem.model,
                "tags": gem.tags,
                "execution_count": gem.execution_count,
                "success_rate": gem.success_count / gem.execution_count if gem.execution_count > 0 else 0,
            })
    return web.json_response({"gemas": gemas_list, "total": len(gemas_list)})


async def handle_teams_stream(request: web.Request) -> web.Response:
    """GET /api/teams/stream/{task_id} — SSE stream para progreso en tiempo real"""
    backend: SuperNEXUSBackend = request.app["backend"]
    exec_id = request.match_info.get("task_id", "")

    from src.core.agent_teams import ParallelTeamExecutor
    executor = ParallelTeamExecutor(director=backend.director, hub=getattr(backend, "hub", None))
    execution = executor.get_execution(exec_id)

    if not execution:
        return web.json_response({"error": "Ejecución no encontrada"}, status=404)

    async def stream_events():
        import json as _json
        last_progress = {}
        while execution.status == "running":
            for gema, status in execution.progress.items():
                if last_progress.get(gema) != status:
                    last_progress[gema] = status
                    event_data = _json.dumps({
                        "execution_id": exec_id,
                        "gema": gema,
                        "status": status,
                        "progress": execution.progress,
                    })
                    yield f"event: progress\ndata: {event_data}\n\n"
            await asyncio.sleep(0.5)

        # Evento final
        final_data = _json.dumps(executor.to_dict(execution))
        yield f"event: complete\ndata: {final_data}\n\n"

    return web.StreamResponse(
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    ).with_body(stream_events())


# ==================== SCHOLAR (Deep Research) ====================

async def handle_scholar_research(request: web.Request) -> web.Response:
    """POST /api/scholar/research — Investigacion web profunda iterativa"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "JSON inválido"}, status=400)

    query = data.get("query", "").strip()
    if not query:
        return web.json_response({"error": "query es requerido"}, status=400)

    deep = bool(data.get("deep", True))

    # Obtener LLM caller del director
    async def llm_caller(prompt, temperature=0.3, max_tokens=4096):
        provider = backend.director.provider_registry.get("gema-con-fallback")
        response = await provider.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.content

    from src.agents.scholar_gem import ScholarGem
    scholar = ScholarGem(llm_caller=llm_caller)
    include_tor = bool(data.get("include_tor", False))
    result = await scholar.research(query, deep=deep, include_tor=include_tor)

    return web.json_response(result, status=200)


async def handle_scholar_darkweb(request: web.Request) -> web.Response:
    """POST /api/scholar/darkweb — Busqueda en darkweb via Tor"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "JSON inválido"}, status=400)

    query = data.get("query", "").strip()
    if not query:
        return web.json_response({"error": "query es requerido"}, status=400)

    max_sources = int(data.get("max_sources", 5))

    async def llm_caller(prompt, temperature=0.3, max_tokens=4096):
        provider = backend.director.provider_registry.get("gema-con-fallback")
        response = await provider.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.content

    from src.agents.scholar_gem import ScholarGem
    scholar = ScholarGem(llm_caller=llm_caller)

    # darkweb_search method
    try:
        from src.core.web_researcher import WebResearcher
        researcher = WebResearcher(mcp_client=getattr(backend.director, 'mcp_client', None))
        sources = await researcher.search(query, max_sources, include_tor=True)
        result = {
            "query": query, "mode": "darkweb", "sources": sources,
            "summary": "", "timestamp": datetime.now().isoformat(),
        }
        if sources:
            result["summary"] = f"Found {len(sources)} darkweb sources for '{query}'"
    except Exception as e:
        result = {"query": query, "mode": "darkweb", "sources": [], "error": str(e)}

    return web.json_response(result, status=200)


async def handle_scholar_onion(request: web.Request) -> web.Response:
    """POST /api/scholar/onion — Navegar a un sitio .onion via Tor"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "JSON inválido"}, status=400)

    url = data.get("url", "").strip()
    if not url:
        return web.json_response({"error": "url es requerido"}, status=400)

    from src.core.web_researcher import WebResearcher
    researcher = WebResearcher()
    result = await researcher.navigate_tor(url)

    return web.json_response(result, status=200)


# ==================== COMPARE MODE (A/B Testing) ====================

async def handle_compare_start(request: web.Request) -> web.Response:
    """POST /api/compare/start — Iniciar comparacion A/B entre modelos"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "JSON inválido"}, status=400)

    prompt = data.get("prompt", "").strip()
    model_a = data.get("model_a", "").strip()
    model_b = data.get("model_b", "").strip()
    is_blind = bool(data.get("is_blind", True))

    if not prompt or not model_a or not model_b:
        return web.json_response({"error": "prompt, model_a, model_b requeridos"}, status=400)

    from src.core.compare_mode import CompareMode
    if backend.compare_mode is None:
        backend.compare_mode = CompareMode(director=backend.director)
    compare = backend.compare_mode
    result = await compare.start_comparison(
        prompt=prompt,
        model_a=model_a,
        model_b=model_b,
        is_blind=is_blind,
    )
    return web.json_response(result, status=200)


async def handle_compare_vote(request: web.Request) -> web.Response:
    """POST /api/compare/{comp_id}/vote — Votar en comparacion"""
    backend: SuperNEXUSBackend = request.app["backend"]
    comp_id = request.match_info.get("comp_id", "")
    
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "JSON inválido"}, status=400)

    winner = data.get("winner", "").strip()
    if winner not in ("left", "right", "tie"):
        return web.json_response({"error": "winner debe ser 'left', 'right', o 'tie'"}, status=400)

    from src.core.compare_mode import CompareMode
    if backend.compare_mode is None:
        backend.compare_mode = CompareMode(director=backend.director)
    compare = backend.compare_mode
    result = await compare.vote(comp_id, winner)
    
    if "error" in result:
        return web.json_response(result, status=404)
    return web.json_response(result, status=200)


async def handle_compare_history(request: web.Request) -> web.Response:
    """GET /api/compare/history — Historial de comparaciones"""
    from src.core.compare_mode import CompareMode
    backend: SuperNEXUSBackend = request.app["backend"]
    if backend.compare_mode is None:
        backend.compare_mode = CompareMode(director=backend.director)
    compare = backend.compare_mode
    history = compare.get_history()
    return web.json_response({"comparisons": history}, status=200)


# ==================== GALLERY ====================

async def handle_gallery_upload(request: web.Request) -> web.Response:
    """POST /api/gallery/upload — Subir imagen"""
    try:
        form = await request.post()
        file = form.get("file")
        if not file:
            return web.json_response({"error": "No file provided"}, status=400)
        
        content = file.file.read()
        filename = file.filename or "image.png"
        prompt = form.get("prompt", "")
        tags = form.get("tags", "")
        model = form.get("model", "")
        
        from src.core.gallery import Gallery
        gallery = Gallery()
        result = await gallery.upload(
            content=content,
            filename=filename,
            prompt=prompt,
            tags=tags,
            model=model,
        )
        return web.json_response(result, status=200)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_gallery_transform(request: web.Request) -> web.Response:
    """POST /api/gallery/transform — Transformar imagen"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "JSON inválido"}, status=400)

    img_id = data.get("img_id", "")
    operation = data.get("operation", "")
    params = {k: v for k, v in data.items() if k not in ("img_id", "operation")}

    from src.core.gallery import Gallery
    gallery = Gallery()
    result = gallery.transform(img_id, operation, **params)
    
    if "error" in result:
        return web.json_response(result, status=400)
    return web.json_response(result, status=200)


async def handle_gallery_library(request: web.Request) -> web.Response:
    """GET /api/gallery/library — Obtener biblioteca"""
    search = request.query.get("search")
    tag = request.query.get("tag")
    model = request.query.get("model")
    limit = int(request.query.get("limit", "24"))
    offset = int(request.query.get("offset", "0"))

    from src.core.gallery import Gallery
    gallery = Gallery()
    result = gallery.get_library(
        search=search,
        tag=tag,
        model=model,
        limit=limit,
        offset=offset,
    )
    return web.json_response(result, status=200)


async def handle_gallery_enhance_face(request: web.Request) -> web.Response:
    """POST /api/gallery/enhance-face — Mejorar rostro"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "JSON inválido"}, status=400)

    img_id = data.get("img_id", "")
    from src.core.gallery import Gallery
    gallery = Gallery()
    result = gallery.enhance_face(img_id)
    
    if "error" in result:
        return web.json_response(result, status=400)
    return web.json_response(result, status=200)


async def handle_gallery_upscale(request: web.Request) -> web.Response:
    """POST /api/gallery/upscale — Upscale imagen"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "JSON inválido"}, status=400)

    img_id = data.get("img_id", "")
    scale = int(data.get("scale", "2"))
    
    from src.core.gallery import Gallery
    gallery = Gallery()
    result = gallery.upscale_local(img_id, scale)
    
    if "error" in result:
        return web.json_response(result, status=400)
    return web.json_response(result, status=200)


async def handle_gallery_image(request: web.Request) -> web.Response:
    """GET /api/gallery/image/{filename} — Servir imagen"""
    filename = request.match_info.get("filename", "")
    if not filename or ".." in filename or "/" in filename:
        return web.json_response({"error": "Invalid filename"}, status=400)
    
    from pathlib import Path
    img_path = Path.home() / ".nexus" / "gallery" / filename
    if not img_path.exists() or not img_path.is_file():
        return web.json_response({"error": "Imagen no encontrada"}, status=404)
    
    return web.FileResponse(img_path)


async def handle_gallery_delete(request: web.Request) -> web.Response:
    """DELETE /api/gallery/delete/{img_id} — Eliminar imagen"""
    img_id = request.match_info.get("img_id", "")
    if not img_id:
        return web.json_response({"error": "No img_id provided"}, status=400)
    
    from src.core.gallery import Gallery
    gallery = Gallery()
    result = gallery.delete_image(img_id)
    
    if not result:
        return web.json_response({"error": "Imagen no encontrada"}, status=404)
    return web.json_response({"ok": True, "deleted": img_id}, status=200)


async def handle_gallery_upload_from_path(request: web.Request) -> web.Response:
    """POST /api/gallery/upload-from-path — Importar imagen desde ruta local"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "JSON inválido"}, status=400)
    
    file_path = data.get("path", "")
    from pathlib import Path
    p = Path(file_path)
    if not p.exists() or not p.is_file():
        return web.json_response({"error": "Archivo no encontrado"}, status=404)
    
    ext = p.suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif", ".ico"):
        return web.json_response({"error": "Formato no soportado"}, status=400)
    
    content = p.read_bytes()
    from src.core.gallery import Gallery
    gallery = Gallery()
    result = await gallery.upload(
        content=content,
        filename=p.name,
        prompt=f"Importado de {p.name}",
        tags="imported",
    )
    return web.json_response(result, status=200)


async def handle_gallery_browse(request: web.Request) -> web.Response:
    """POST /api/gallery/browse — Navegador de archivos local (todos los discos)"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "JSON inválido"}, status=400)
    
    path = data.get("path", "")
    from pathlib import Path
    import string
    
    # Si path vacío o "root", mostrar discos disponibles
    if not path or path.lower() in ("root", "/"):
        drives = []
        for letter in string.ascii_uppercase:
            drive = Path(f"{letter}:\\")
            if drive.exists():
                drives.append({
                    "name": f"{letter}:\\",
                    "path": str(drive),
                    "type": "dir",
                    "size": 0,
                })
        return web.json_response({
            "current": "Mis discos",
            "parent": "",
            "items": drives,
        }, status=200)
    
    current = Path(path)
    if not current.exists() or not current.is_dir():
        return web.json_response({"error": "Directorio inválido"}, status=400)
    
    try:
        items = []
        for entry in sorted(current.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if entry.name.startswith("."):
                continue
            try:
                is_dir = entry.is_dir()
                info = {
                    "name": entry.name,
                    "path": str(entry),
                    "type": "dir" if is_dir else "file",
                    "size": entry.stat().st_size if not is_dir else 0,
                }
                if not is_dir:
                    ext = entry.suffix.lower()
                    info["is_image"] = ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif")
                items.append(info)
            except (PermissionError, OSError):
                continue
        
        # En Windows, C:\.parent == C:\, así que detectar raíz de disco
        is_drive_root = current.parent == current
        parent = "" if is_drive_root else str(current.parent)
        return web.json_response({
            "current": str(current),
            "parent": parent,
            "items": items,
        }, status=200)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ==================== COOKBOOK (Hardware Detection) ====================

async def handle_cookbook_scan(request: web.Request) -> web.Response:
    """POST /api/cookbook/scan — Detectar hardware (local o remoto via SSH)"""
    try:
        data = await request.json()
    except Exception:
        data = {}

    remote_host = data.get("remote_host")
    ssh_port = data.get("ssh_port", "22")

    from src.core.cookbook import scan_hardware, recommend
    hw = scan_hardware(remote_host=remote_host, ssh_port=ssh_port)
    recs = recommend(hw)
    return web.json_response(recs, status=200)

async def handle_permissions_get(request: web.Request) -> web.Response:
    """GET /api/permissions — list all override rules + known actions"""
    return web.json_response({
        "overrides": permission_manager.get_rules(),
        "known_actions": permission_manager.get_known_actions(),
    })


async def handle_permissions_put(request: web.Request) -> web.Response:
    """PUT /api/permissions — set a permission override"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    gema = data.get("gema", "")
    action = data.get("action", "")
    level = data.get("level", "")
    if not gema or not action or not level:
        return web.json_response({"error": "gema, action, level required"}, status=400)
    ok = permission_manager.set_rule(gema, action, level)
    if not ok:
        return web.json_response({"error": f"Invalid level '{level}'. Use: allow, ask, never"}, status=400)
    permission_manager.save()
    return web.json_response({"success": True, "gema": gema, "action": action, "level": level})


async def handle_permissions_delete(request: web.Request) -> web.Response:
    """DELETE /api/permissions — remove an override"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    gema = data.get("gema", "")
    action = data.get("action", "")
    if not gema or not action:
        return web.json_response({"error": "gema, action required"}, status=400)
    ok = permission_manager.remove_rule(gema, action)
    if not ok:
        return web.json_response({"error": "Rule not found"}, status=404)
    permission_manager.save()
    return web.json_response({"success": True, "gema": gema, "action": action})


async def handle_permissions_pending(request: web.Request) -> web.Response:
    """GET /api/permissions/pending — list pending HITL approval requests"""
    return web.json_response({"pending": permission_manager.pending()})


async def handle_permissions_resolve(request: web.Request) -> web.Response:
    """POST /api/permissions/resolve — approve or reject a pending request"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    token = data.get("token", "")
    approve = data.get("approve", False)
    if not token:
        return web.json_response({"error": "token required"}, status=400)
    result = permission_manager.resolve(token, bool(approve))
    return web.json_response(result)


async def handle_permissions_check(request: web.Request) -> web.Response:
    """POST /api/permissions/check — evaluate a permission without executing"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    gema = data.get("gema", "user")
    action = data.get("action", "")
    if not action:
        return web.json_response({"error": "action required"}, status=400)
    verdict = permission_manager.check(gema, action)
    return web.json_response({
        "action": verdict.action,
        "level": verdict.level,
        "from_safe_default": verdict.from_safe_default,
        "pending_token": verdict.pending_token,
        "reason": verdict.reason,
    })


# ==================== F15: DOCTOR COMMAND ====================

async def handle_doctor(request: web.Request) -> web.Response:
    """GET /api/doctor - Cached diagnostic report; falls back to quick live
    diagnostic when no cached report exists (instead of an unhelpful stub)."""
    backend: SuperNEXUSBackend = request.app["backend"]
    if hasattr(backend, "_last_doctor_report"):
        return web.json_response(backend._last_doctor_report)
    return await handle_doctor_quick(request)


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
    except Exception:
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
    except Exception:
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
    except Exception:
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
    except Exception:
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
    except Exception:
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
    except Exception:
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
        summary_prompt = "Resume esta conversación en máximo 5 párrafos, manteniendo la información más importante:\n\n"
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
    except Exception:
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
    except Exception:
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
        _conductor_instance = Conductor(repo_path=os.environ.get("NEXUS_PROJECT_DIR", "."))
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


# ==================== COMPOSE WORKFLOW ====================

async def handle_compose_create(request: web.Request) -> web.Response:
    """POST /api/compose — Create a new compose run"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    spec = data.get("spec", "")
    if not spec:
        return web.json_response({"error": "spec required"}, status=400)
    run = await backend.director.compose.create(
        spec=spec,
        goal=data.get("goal", ""),
        project=data.get("project", "default"),
    )
    return web.json_response({
        "id": run.id, "status": run.status.value,
        "created_at": run.created_at,
    })


async def handle_compose_execute(request: web.Request) -> web.Response:
    """POST /api/compose/{run_id}/execute — Execute a compose run"""
    backend: SuperNEXUSBackend = request.app["backend"]
    run_id = request.match_info["run_id"]
    run = await backend.director.compose.execute(run_id)
    return web.json_response({
        "id": run.id,
        "status": run.status.value,
        "current_phase": run.current_phase.value,
        "phases": list(run.phases.keys()),
        "tasks": [
            {"id": t.id, "title": t.title, "status": t.status}
            for t in run.tasks
        ],
        "summary": run.summary[:200],
    })


async def handle_compose_get(request: web.Request) -> web.Response:
    """GET /api/compose/{run_id} — Get compose run status"""
    backend: SuperNEXUSBackend = request.app["backend"]
    run_id = request.match_info["run_id"]
    run = backend.director.compose.get_run(run_id)
    if not run:
        return web.json_response({"error": "Run not found"}, status=404)
    return web.json_response({
        "id": run.id,
        "spec": run.spec[:500],
        "goal": run.goal,
        "status": run.status.value,
        "current_phase": run.current_phase.value,
        "phases": list(run.phases.keys()),
        "tasks": [
            {"id": t.id, "title": t.title, "status": t.status, "assignee": t.assignee}
            for t in run.tasks
        ],
        "summary": run.summary,
        "created_at": run.created_at,
        "duration_s": run.metadata.get("duration_s", 0),
    })


async def handle_compose_list(request: web.Request) -> web.Response:
    """GET /api/compose — List compose runs"""
    backend: SuperNEXUSBackend = request.app["backend"]
    project = request.query.get("project")
    limit = int(request.query.get("limit", 20))
    runs = backend.director.compose.list_runs(project=project, limit=limit)
    return web.json_response({"runs": runs, "count": len(runs)})


async def handle_compose_stats(request: web.Request) -> web.Response:
    """GET /api/compose/stats — Compose workflow stats"""
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.director.compose.get_stats())


# ==================== DREAM / DISTILL ====================

async def handle_dream_run(request: web.Request) -> web.Response:
    """POST /api/dream/run — Ejecuta ciclo Dream (consolidacion semanal)"""
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend.director, "dream"):
        return web.json_response({"error": "Dream engine not initialized"}, status=503)
    cycle = await backend.director.dream.dream()
    return web.json_response({
        "id": cycle.id, "cycle": cycle.cycle,
        "status": cycle.status, "insight_count": cycle.insight_count,
        "summary": cycle.summary,
        "duration_s": cycle.metadata.get("duration_s", 0),
    })


async def handle_distill_run(request: web.Request) -> web.Response:
    """POST /api/distill/run — Ejecuta ciclo Distill (descubrimiento mensual)"""
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend.director, "dream"):
        return web.json_response({"error": "Dream engine not initialized"}, status=503)
    cycle = await backend.director.dream.distill()
    return web.json_response({
        "id": cycle.id, "cycle": cycle.cycle,
        "status": cycle.status, "insight_count": cycle.insight_count,
        "summary": cycle.summary,
        "duration_s": cycle.metadata.get("duration_s", 0),
    })


async def handle_dream_insights(request: web.Request) -> web.Response:
    """GET /api/dream/insights — Lista insights (dream o distill)"""
    backend: SuperNEXUSBackend = request.app["backend"]
    dream_type = request.query.get("type", "dream")
    limit = int(request.query.get("limit", 50))
    insights = backend.director.dream.get_insights(dream_type=dream_type, limit=limit)
    return web.json_response({"insights": insights, "count": len(insights)})


async def handle_dream_cycles(request: web.Request) -> web.Response:
    """GET /api/dream/cycles — Lista ciclos"""
    backend: SuperNEXUSBackend = request.app["backend"]
    dream_type = request.query.get("type", "")
    limit = int(request.query.get("limit", 20))
    cycles = backend.director.dream.get_cycles(dream_type=dream_type, limit=limit)
    return web.json_response({"cycles": cycles, "count": len(cycles)})


async def handle_dream_logs(request: web.Request) -> web.Response:
    """GET /api/dream/logs — Logs del engine"""
    backend: SuperNEXUSBackend = request.app["backend"]
    limit = int(request.query.get("limit", 50))
    logs = backend.director.dream.get_logs(limit=limit)
    return web.json_response({"logs": logs, "count": len(logs)})


async def handle_dream_stats(request: web.Request) -> web.Response:
    """GET /api/dream/stats — Estadisticas del Dream engine"""
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.director.dream.get_stats())


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

# ==================== F1: NEXUS DIRECTOR ====================

async def handle_nexus_execute(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    task = data.get("task", "")
    if not task:
        return web.json_response({"error": "task required"}, status=400)
    if not hasattr(backend.director, 'nexus_execute'):
        return web.json_response({"error": "NEXUS Director not initialized"}, status=503)
    result = await backend.director.nexus_execute(task)
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
    """GET /api/health — Public health endpoint. Minimal info only."""
    from datetime import datetime, timezone
    return web.json_response({
        "status": "ok",
        "service": "nexus-supernexus-v2",
        "version": "2.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def handle_health_full(request: web.Request) -> web.Response:
    """GET /api/health/full — Full health status (requires auth)."""
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
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    cp = backend.director.checkpoints.save_checkpoint(run_id, data.get("node_id", "main"), data.get("state", {}))
    return web.json_response({"checkpoint_id": cp.id})


async def handle_auto_checkpoint_status(request: web.Request) -> web.Response:
    """GET /api/checkpoints/auto — auto-checkpoint trigger status"""
    backend: SuperNEXUSBackend = request.app["backend"]
    run_id = request.query.get("run_id")
    status = backend.director.checkpoints.get_auto_checkpoint_status(run_id)
    return web.json_response(status)


async def handle_auto_checkpoint_inject(request: web.Request) -> web.Response:
    """POST /api/checkpoints/auto/inject — inject budgeted context"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    result = backend.director.checkpoints.budgeted_inject(
        backend.director.sessions,
        session_id=data.get("session_id"),
        max_tokens=data.get("max_tokens", 2000),
        run_id=data.get("run_id"),
    )
    return web.json_response({"injected": result is not None, "context": result})


async def handle_auto_checkpoint_reconstruct(request: web.Request) -> web.Response:
    """GET /api/checkpoints/auto/reconstruct — reconstruct context from checkpoints"""
    backend: SuperNEXUSBackend = request.app["backend"]
    session_id = request.query.get("session_id")
    run_id = request.query.get("run_id")
    result = backend.director.checkpoints.reconstruct_context(
        backend.director.sessions, session_id=session_id, run_id=run_id,
    )
    return web.json_response(result)


# ==================== F8: RECIPES ====================

async def handle_recipes_list(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response({"recipes": backend.director.recipes.list_recipes()})


async def handle_recipe_load(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    recipe = backend.director.recipes.load_from_yaml(data.get("path", ""))
    return web.json_response({"name": recipe.name, "steps": len(recipe.steps)})


async def handle_recipe_execute(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    name = request.match_info["name"]
    try:
        data = await request.json()
    except Exception:
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
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    req = await backend.director.approval.request_approval(data.get("task", ""), data.get("description", ""), data.get("timeout"), data.get("escalation"))
    return web.json_response({"id": req.id, "status": req.status.value})


async def handle_approval_respond(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
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
    except Exception:
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
    except Exception:
        data = {}
    findings = backend.director.risk.assess_system(data)
    return web.json_response(backend.director.risk.get_summary())


# ==================== F14: MEMORY HEALTH ====================

async def handle_memory_health(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.director.memory_health.get_summary())


async def handle_cerebro_stats(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    from src.agents.sage_gem import SageGem
    sage = SageGem()
    sage_stats = sage.get_memory_stats()
    cerebro_stats = {}
    try:
        cerebro_stats = backend.cerebro.obtener_estadisticas() if hasattr(backend, "cerebro") else {}
    except Exception:
        pass
    return web.json_response({
        "sage": sage_stats,
        "cerebro": cerebro_stats,
    })


# ==================== F17: TOOL MONITORING ====================

async def handle_tool_monitor(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.director.tool_monitor.get_summary())


async def handle_tool_record(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    backend.director.tool_monitor.record_call(data.get("tool", ""), data.get("duration_ms", 0), data.get("tokens", 0), data.get("success", True), data.get("error", ""), data.get("model_type", "local"))
    return web.json_response({"success": True})


# ==================== F13: COLLABORATION HALL ====================

async def handle_hall_create_room(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    room = backend.director.hall.create_room(data.get("topic", ""), data.get("agents", []))
    return web.json_response({"id": room.id, "topic": room.topic})


async def handle_hall_add_event(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
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
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    backend.director.retry.configure(data.get("task_type", "default"), **data.get("config", {}))
    return web.json_response({"success": True})


# ==================== F20: LIVE NOTES ====================

async def handle_live_note_create(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
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
    except Exception:
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
    except Exception:
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
    from src.core.tool_guardrails import GuardrailConfig, ToolCallGuardrailController
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
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

AUTH_PUBLIC_PATHS = {
    # Auth
    "/api/auth/login", "/api/auth/setup", "/api/auth/status",
    # Chat & Status
    "/api/chat", "/api/status", "/api/health", "/api/doctor", "/api/capabilities",
    "/api/events/stats", "/api/events/stream",
    "/api/workers/stalled", "/api/mcp/health",
    "/api/budget/all", "/api/sessions/catalog",
    "/api/dmn/stats", "/api/dmn/tick", "/api/sbom",
    "/api/slash", "/api/cookbook/scan",
    # Setup wizard (must be reachable before user is created)
    "/api/setup/state", "/api/setup/preflight",
    "/api/setup/step", "/api/setup/reset",
    # A2A agent discovery (public per spec)
    "/.well-known/agent.json",
    # Providers discovery (public, read-only)
    "/api/providers",
    # v3 architecture diagnostics (public, read-only)
    "/api/v3/services", "/api/v3/brain", "/api/v3/plugins", "/api/v3/capabilities",
    "/api/v3/capabilities/audit",

    # Hive
    "/api/hive/status", "/api/hive/send", "/api/hive/nodes",
    "/api/hive/agents", "/api/hive/dispatch", "/api/hive/registry",
    "/api/hive/stream", "/api/hive/result",
    # Training
    "/api/training/collect", "/api/training/pipeline", "/api/training/sft",
    "/api/training/dpo", "/api/training/jobs", "/api/training/job",
    "/api/training/cancel", "/api/training/report", "/api/training/datasets",
    "/api/training/ollama",
    # Trainer
    "/api/trainer/prepare", "/api/trainer/launch", "/api/trainer/jobs",

    # MCP
    "/api/mcp/tools", "/api/mcp/list_tools", "/api/mcp/hub", "/api/mcp/tools-cache",
    # AI tools
    "/api/ai/tools", "/api/ai/tools/stats",
    # System
    "/api/system/stats", "/api/system/safe",
    # Providers (UI needs this)
    "/api/providers",
    "/api/cloud-providers",
    "/api/ollama/tags", "/api/ollama/refresh",
    # File system (UI terminal needs this)
    "/api/fs/list", "/api/fs/read",
    # Memory
    "/api/memory/health",
    # Tools monitor
    "/api/tools/monitor",
    # Graph
    "/api/graph/status",
    # Checkpoints
    "/api/checkpoints",
    # Brain (UI reads)
    "/api/brain/stats", "/api/brain/preferences",
    # Swarm
    "/api/swarm/events", "/api/swarm/checkpoints", "/api/swarm/handoffs",
    "/api/swarm/stats", "/api/swarm/context", "/api/swarm/lifecycle",
    # Sessions
    "/api/sessions",
    # PC control
    "/api/pc/status", "/api/pc/screenshot",
    # Vision
    "/api/vision/providers",
    # Safety
    "/api/safety/status",
    # Agent loop
    "/api/agent-loop/run",
    # Commands (UI reads)
    "/api/commands",
}


@web.middleware
async def auth_middleware(request: web.Request, handler):
    """Middleware que protege rutas con autenticacion (new-style @web.middleware).

    Auth es OPT-IN: por default NEXUS corre sin auth (modo local single-user,
    soberania > conveniencia). Para habilitar:
        $env:NEXUS_AUTH = "1"
    o setearlo en .env del proyecto.

    Cuando esta habilitada, el flujo de primer uso es:
        1. GET /api/auth/status -> {"has_users": false}
        2. POST /api/auth/setup {"username": "...", "password": "..."}
        3. POST /api/auth/login  -> token Bearer
    """
    auth: AuthManager = request.app.get("auth")
    if not auth:
        return await handler(request)

    # OPT-IN: si NEXUS_AUTH != "1", todos los endpoints son publicos
    if os.environ.get("NEXUS_AUTH", "0") != "1":
        return await handler(request)

    path = request.path

    # Rutas publicas (UI estática + API pública + assets estáticos).
    # NOTA: /v1/* (OpenAI-compatible) ya NO esta en el bypass — cuando
    # NEXUS_AUTH=1 requiere Bearer estandar OpenAI (Authorization: Bearer sk-...).
    # Excepcion: /v1 health endpoint sigue publico para drop-in compat checks.
    if (path in AUTH_PUBLIC_PATHS
            or path == "/v1"
            or path == "/"
            or path.startswith("/ui")
            or path.endswith((".ico", ".png", ".jpg", ".svg", ".webp", ".woff2"))):
        return await handler(request)

    # WebSocket: permitir token en query param o subprotocol
    if path.startswith("/api/ws/"):
        token = request.query.get("token") or request.headers.get("Sec-WebSocket-Protocol", "")
        if token:
            user = auth.validate_token(token)
            if user:
                request["auth_user"] = user
        # Permitir conexion aunque no haya token: el handler de WS valida
        return await handler(request)

    # Bearer token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        user = auth.validate_token(token)
        if user:
            request["auth_user"] = user
            return await handler(request)

    # API key fallback
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
    """Estado de autenticacion (incluye si auth esta habilitada via NEXUS_AUTH=1)."""
    auth: AuthManager = request.app["auth"]
    status = auth.get_status()
    # auth_enabled le dice a la UI si debe mostrar login/setup wizard
    status["auth_enabled"] = os.environ.get("NEXUS_AUTH", "0") == "1"
    return web.json_response(status)


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


# ── Swarm endpoints ──────────────────────────────────────────────


async def handle_swarm_events(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    worker_id = request.query.get("worker_id")
    mission_id = request.query.get("mission_id")
    limit = int(request.query.get("limit", 50))
    events = backend.swarm_memory.get_events(worker_id=worker_id, mission_id=mission_id, limit=limit)
    return web.json_response({"events": events, "total": len(events)})


async def handle_swarm_checkpoints(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    mission_id = request.query.get("mission_id")
    checkpoints = backend.swarm_memory.get_checkpoints(mission_id=mission_id)
    return web.json_response({"checkpoints": checkpoints})


async def handle_swarm_handoffs(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    worker_id = request.query.get("worker_id")
    handoffs = backend.swarm_memory.get_pending_handoffs(worker_id=worker_id)
    return web.json_response({"handoffs": handoffs})


async def handle_swarm_stats(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    return web.json_response(backend.swarm_memory.stats())


async def handle_swarm_context(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    if request.method == "GET":
        content = backend.swarm_memory.get_project_context()
        return web.json_response({"context": content or ""})
    data = await request.json()
    content = data.get("content", "")
    backend.swarm_memory.set_project_context(content)
    return web.json_response({"ok": True})


async def handle_swarm_lifecycle(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    worker_id = request.query.get("worker_id")
    if worker_id:
        status = backend.swarm_lifecycle.get_status(worker_id)
        return web.json_response(status.__dict__)
    statuses = backend.swarm_lifecycle.all_status()
    return web.json_response({"workers": [s.__dict__ for s in statuses]})


# ── Fusion Engine endpoints ──────────────────────────────────────

_fusion_engine_instance = None


def _get_fusion_engine(backend):
    global _fusion_engine_instance
    if _fusion_engine_instance is None:
        from src.core.fusion_engine import FusionEngine
        _fusion_engine_instance = FusionEngine(
            director=backend.director if hasattr(backend, 'director') else None,
            memory_system=backend.memory if hasattr(backend, 'memory') else None,
        )
    return _fusion_engine_instance


async def handle_fusion(request: web.Request) -> web.Response:
    """POST /api/fusion - Multi-model deliberation con juez y busqueda web"""
    backend: SuperNEXUSBackend = request.app["backend"]

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    prompt = data.get("prompt", "") or data.get("message", "")
    if not prompt:
        return web.json_response({"error": "prompt is required"}, status=400)

    panel = data.get("panel", None)
    preset = data.get("preset", "quality")
    use_web_search = data.get("use_web_search", True)
    context = data.get("context", "")
    max_panel_time_ms = data.get("max_panel_time_ms", 60000)

    engine = _get_fusion_engine(backend)
    engine.backend = backend

    try:
        result = await engine.fuse(
            prompt=prompt,
            panel=panel,
            preset=preset,
            use_web_search=use_web_search,
            max_panel_time_ms=max_panel_time_ms,
            context=context,
        )

        return web.json_response({
            "reply": result.content,
            "analysis": {
                "consensus": result.analysis.consensus,
                "contradictions": result.analysis.contradictions,
                "partial_coverage": result.analysis.partial_coverage,
                "unique_insights": result.analysis.unique_insights,
                "blind_spots": result.analysis.blind_spots,
                "best_gema": result.analysis.best_gema,
                "confidence_score": result.analysis.confidence_score,
            },
            "panel_size": len(result.panel_responses),
            "panel_responses": [
                {
                    "gema": r.gema,
                    "model": r.model,
                    "confidence": r.confidence,
                    "duration_ms": r.duration_ms,
                }
                for r in result.panel_responses
            ],
            "web_context_used": bool(result.web_context),
            "duration_ms": result.duration_ms,
            "fusion_round": result.fusion_round,
            "learning_applied": result.learning_applied,
        })

    except Exception as e:
        logger.error(f"Fusion failed: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_fusion_stats(request: web.Request) -> web.Response:
    """GET /api/fusion/stats - Estadisticas del motor de fusion"""
    global _fusion_engine_instance
    if _fusion_engine_instance is None:
        return web.json_response({"stats": {}, "message": "Fusion engine not initialized"})
    return web.json_response({"stats": _fusion_engine_instance.get_stats()})


# ── Connections endpoints ────────────────────────────────────────


async def handle_connections_list(request: web.Request) -> web.Response:
    """GET /api/connections - List all connections with live health status"""
    conns = load_connections()
    results = []
    for c in conns.get("connections", []):
        health = await check_health(c)
        results.append({
            "name": c["name"],
            "label": c.get("label", c["name"]),
            "description": c.get("description", ""),
            "type": c.get("type", "cli"),
            "protocol": c.get("protocol", ""),
            "tags": c.get("tags", []),
            "enabled": c.get("enabled", True),
            "autonomous": c.get("autonomous", False),
            "health": health,
        })
    return web.json_response({"connections": results, "total": len(results)})


async def handle_connections_get(request: web.Request) -> web.Response:
    """GET /api/connections/{name} - Get a single connection"""
    name = request.match_info.get("name", "")
    c = get_connection(name)
    if not c:
        return web.json_response({"error": "not found"}, status=404)
    health = await check_health(c)
    c["health"] = health
    return web.json_response({"connection": c})


async def handle_connections_create(request: web.Request) -> web.Response:
    """POST /api/connections - Add or update a connection"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    if "name" not in data:
        return web.json_response({"error": "name is required"}, status=400)
    add_connection(data)
    return web.json_response({"success": True, "name": data["name"]})


async def handle_connections_delete(request: web.Request) -> web.Response:
    """DELETE /api/connections/{name} - Remove a connection"""
    name = request.match_info.get("name", "")
    if remove_connection(name):
        return web.json_response({"deleted": True, "name": name})
    return web.json_response({"error": "not found"}, status=404)


async def handle_connections_health(request: web.Request) -> web.Response:
    """GET /api/connections/health - Check health of all connections"""
    results = await check_all_connections()
    return web.json_response({"health": results})


async def handle_connections_sync(request: web.Request) -> web.Response:
    """POST /api/connections/sync - Force resync to hive_agents.json"""
    sync_to_hive_agents()
    return web.json_response({"synced": True})


def create_app(backend: SuperNEXUSBackend) -> web.Application:
    auth = AuthManager()
    app = web.Application(middlewares=[request_id_middleware, cors_middleware, rate_limit_middleware(200, 60_000), auth_middleware])
    app["backend"] = backend
    app["auth"] = auth

    # Auto-subscribe budget tracker to LLM_TOKEN_USAGE events when the loop
    # is up. Lazy/idempotent — does nothing if event_stream missing.
    async def _wire_budget_tracker(_app):
        try:
            from src.observability.budget_tracker import tracker
            tracker.ensure_subscribed()
        except Exception as e:
            logger.debug(f"budget_tracker subscribe failed: {e}")
    app.on_startup.append(_wire_budget_tracker)

    # OTel exporter (opt-in via NEXUS_OTEL_ENDPOINT) — drains event_stream
    # to an OTLP-compatible collector (Tempo/Jaeger/etc).
    async def _wire_otel(_app):
        try:
            from src.observability.otel_exporter import ensure_started
            if ensure_started():
                logger.info("otel_exporter: started")
        except Exception as e:
            logger.debug(f"otel_exporter wire failed: {e}")
    app.on_startup.append(_wire_otel)

    # Spin up auto_start MCP servers (those declared with auto_start:true
    # in mcp_servers.json or builtin defaults). Backgrounded so a slow
    # subprocess spawn doesn't delay the boot signal.
    async def _wire_mcp_autostart(_app):
        try:
            mcp = getattr(backend.director, "mcp_client", None)
            if mcp is None or not hasattr(mcp, "start_all"):
                return
            # Fire-and-forget — boot doesn't wait
            asyncio.create_task(mcp.start_all(), name="mcp_start_all")
        except Exception as e:
            logger.debug(f"mcp_autostart wire failed: {e}")
    app.on_startup.append(_wire_mcp_autostart)

    # Start the Default Mode Network (background reflection actor).
    # Disabled with NEXUS_DMN_DISABLED=1. Fires every NEXUS_DMN_INTERVAL_S
    # (default 600s = 10min). All output goes through the notification gate.
    async def _wire_dmn(_app):
        try:
            from src.brain.dmn import dmn
            import os as _os
            try:
                interval = int(_os.environ.get("NEXUS_DMN_INTERVAL_S", "600"))
            except Exception:
                interval = 600
            dmn.interval = max(60, interval)
            dmn.start()
        except Exception as e:
            logger.debug(f"DMN wire failed: {e}")
    app.on_startup.append(_wire_dmn)

    # Core routes
    app.router.add_get("/api/status", handle_status)
    app.router.add_get("/api/events/stats", handle_events_stats)
    app.router.add_get("/api/events/stream", handle_events_stream)
    app.router.add_get("/api/sessions/catalog", handle_sessions_catalog)
    app.router.add_post("/api/sessions/{session_id}/attach", handle_session_attach)
    app.router.add_get("/api/sessions/{session_id}/logs", handle_session_logs)
    app.router.add_get("/api/sessions/{session_id}/budget", handle_session_budget)
    app.router.add_get("/api/sessions/{session_id}/scratchpad", handle_scratchpad_get)
    app.router.add_post("/api/sessions/{session_id}/scratchpad", handle_scratchpad_post)
    app.router.add_get("/api/budget/all", handle_budgets_all)
    app.router.add_get("/api/workers/stalled", handle_workers_stalled)

    app.router.add_get("/api/sbom", handle_sbom)
    app.router.add_get("/api/cookbook/scan", handle_cookbook_scan)
    app.router.add_post("/api/cookbook/install", handle_cookbook_install)
    app.router.add_get("/.well-known/agent.json", handle_a2a_agent_card)
    app.router.add_get("/api/config", handle_api_config)
    app.router.add_post("/api/config/default-model", handle_set_default_model)
    app.router.add_post("/api/gemas/import", handle_gemas_import)
    app.router.add_post("/api/memory/consolidate", handle_memory_consolidate)
    app.router.add_post("/api/memory/purge", handle_memory_purge)
    app.router.add_post("/api/memory/maintenance", handle_memory_maintenance)
    app.router.add_get("/api/router/stats", handle_router_stats)
    app.router.add_post("/api/router/record", handle_router_record)
    app.router.add_get("/api/skills/suggest", handle_skill_suggest)
    app.router.add_post("/api/skills/record", handle_skill_record)
    app.router.add_post("/api/confirm/request", handle_confirm_request)
    app.router.add_post("/api/confirm", handle_confirm_respond)
    app.router.add_get("/api/confirm/pending", handle_confirm_pending)
    app.router.add_get("/api/slash", handle_slash_list)
    app.router.add_post("/api/slash", handle_slash_execute)
    app.router.add_get("/api/dmn/stats", handle_dmn_stats)
    app.router.add_post("/api/dmn/tick", handle_dmn_tick)
    app.router.add_get("/api/mcp/health", handle_mcp_health)
    app.router.add_get("/api/setup/state", handle_setup_state)
    app.router.add_get("/api/setup/preflight", handle_setup_preflight)
    app.router.add_post("/api/setup/step", handle_setup_save_step)
    app.router.add_post("/api/setup/reset", handle_setup_reset)
    app.router.add_get("/api/capabilities", handle_capabilities)
    # v3 architecture endpoints (public, read-only diagnostics)
    app.router.add_get("/api/v3/services", handle_v3_services)
    app.router.add_get("/api/v3/brain", handle_v3_brain)
    app.router.add_get("/api/v3/plugins", handle_v3_plugins)
    app.router.add_get("/api/v3/capabilities", handle_v3_capabilities)
    app.router.add_get("/api/v3/capabilities/audit", handle_v3_capabilities_audit)
    app.router.add_get("/api/projects", handle_projects)
    app.router.add_post("/api/projects/activate", handle_project_activate)
    app.router.add_get("/api/projects/{name}/context", handle_project_context_get)
    app.router.add_put("/api/projects/{name}/context", handle_project_context_put)

    # Connections
    app.router.add_get("/api/connections", handle_connections_list)
    app.router.add_get("/api/connections/health", handle_connections_health)
    app.router.add_post("/api/connections/sync", handle_connections_sync)
    app.router.add_get("/api/connections/{name}", handle_connections_get)
    app.router.add_post("/api/connections", handle_connections_create)
    app.router.add_delete("/api/connections/{name}", handle_connections_delete)

    app.router.add_get("/api/providers", handle_providers)
    app.router.add_get("/api/provider-catalog", handle_provider_catalog)
    app.router.add_get("/api/llm/gateway/stats", handle_llm_gateway_stats)
    app.router.add_get("/api/cloud-providers", handle_cloud_providers_list)
    app.router.add_post("/api/cloud-providers", handle_cloud_providers_save)
    app.router.add_delete("/api/cloud-providers/{id}", handle_cloud_providers_delete)
    app.router.add_get("/api/ollama/tags", handle_ollama_tags)
    app.router.add_post("/api/ollama/refresh", handle_ollama_refresh)
    app.router.add_get("/api/gems", handle_gems)
    app.router.add_get("/api/knowledge/graph", handle_knowledge_graph)
    app.router.add_get("/api/tailscale/nodes", handle_tailscale_nodes)
    app.router.add_post("/api/chat", handle_chat)
    app.router.add_get("/api/ws/chat", handle_chat_ws)
    app.router.add_post("/api/memory/search", handle_memory_search)
    app.router.add_post("/api/learn", handle_learn)
    app.router.add_post("/api/research", handle_research)
    app.router.add_post("/api/execute", handle_execute)

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

    # Auto-Compact
    app.router.add_get("/api/conversation", handle_conversation_history)
    app.router.add_post("/api/compact", handle_compact_conversation)

    # Producer-Verifier Loop
    app.router.add_post("/api/pvl/run", handle_producer_verifier_loop)
    app.router.add_get("/api/pvl/status", handle_pvl_status)

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



    # Brain routes
    app.router.add_get("/api/brain/stats", handle_brain_stats)
    app.router.add_get("/api/brain/preferences", handle_brain_preferences)
    app.router.add_get("/api/brain/prompt", handle_brain_prompt)
    app.router.add_post("/api/brain/learn", handle_brain_learn)
    app.router.add_get("/api/brain/knowledge", handle_brain_knowledge)
    app.router.add_get("/api/brain/conversations", handle_brain_conversations)
    app.router.add_post("/api/brain/learn-from-url", handle_brain_learn_from_url)
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

    # Teams routes (Parallel Gema Execution)
    app.router.add_post("/api/teams/execute", handle_teams_execute)
    app.router.add_get("/api/teams/status/{task_id}", handle_teams_status)
    app.router.add_get("/api/teams/list", handle_teams_list)
    app.router.add_get("/api/teams/gemas", handle_teams_gemas)
    app.router.add_get("/api/teams/stream/{task_id}", handle_teams_stream)

    # Scholar routes (Deep Research)
    app.router.add_post("/api/scholar/research", handle_scholar_research)
    app.router.add_post("/api/scholar/darkweb", handle_scholar_darkweb)
    app.router.add_post("/api/scholar/onion", handle_scholar_onion)

    # Compare Mode routes (A/B Testing)
    app.router.add_post("/api/compare/start", handle_compare_start)
    app.router.add_post("/api/compare/{comp_id}/vote", handle_compare_vote)
    app.router.add_get("/api/compare/history", handle_compare_history)

    # Gallery routes
    app.router.add_post("/api/gallery/upload", handle_gallery_upload)
    app.router.add_post("/api/gallery/transform", handle_gallery_transform)
    app.router.add_get("/api/gallery/library", handle_gallery_library)
    app.router.add_post("/api/gallery/enhance-face", handle_gallery_enhance_face)
    app.router.add_post("/api/gallery/upscale", handle_gallery_upscale)
    app.router.add_get("/api/gallery/image/{filename}", handle_gallery_image)
    app.router.add_delete("/api/gallery/delete/{img_id}", handle_gallery_delete)
    app.router.add_post("/api/gallery/browse", handle_gallery_browse)
    app.router.add_post("/api/gallery/upload-from-path", handle_gallery_upload_from_path)

    # Cookbook routes (Hardware Detection)
    app.router.add_post("/api/cookbook/scan", handle_cookbook_scan)

    # Permission Manager routes
    app.router.add_get("/api/permissions", handle_permissions_get)
    app.router.add_put("/api/permissions", handle_permissions_put)
    app.router.add_delete("/api/permissions", handle_permissions_delete)
    app.router.add_get("/api/permissions/pending", handle_permissions_pending)
    app.router.add_post("/api/permissions/resolve", handle_permissions_resolve)
    app.router.add_post("/api/permissions/check", handle_permissions_check)

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

    # Compose: Specs-driven autonomous development workflow
    app.router.add_post("/api/compose", handle_compose_create)
    app.router.add_post("/api/compose/{run_id}/execute", handle_compose_execute)
    app.router.add_get("/api/compose/{run_id}", handle_compose_get)
    app.router.add_get("/api/compose", handle_compose_list)
    app.router.add_get("/api/compose/stats", handle_compose_stats)

    # Dream / Distill: Self-improvement cycles (7d consolidation, 30d pattern discovery)
    app.router.add_post("/api/dream/run", handle_dream_run)
    app.router.add_post("/api/distill/run", handle_distill_run)
    app.router.add_get("/api/dream/insights", handle_dream_insights)
    app.router.add_get("/api/dream/cycles", handle_dream_cycles)
    app.router.add_get("/api/dream/logs", handle_dream_logs)
    app.router.add_get("/api/dream/stats", handle_dream_stats)

    # Conductor: Parallel Worktree Coordinator (gstack pattern)
    app.router.add_post("/api/conductor/spawn", handle_conductor_spawn)
    app.router.add_post("/api/conductor/merge", handle_conductor_merge)
    app.router.add_post("/api/conductor/cleanup", handle_conductor_cleanup)
    app.router.add_get("/api/conductor/status", handle_conductor_status)

    # F1: NEXUS Director
    app.router.add_post("/api/director/execute", handle_nexus_execute)
    app.router.add_get("/api/director/decision-engine", handle_decision_engine_status)
    app.router.add_get("/api/director/sub-directors", handle_sub_directors_status)
    app.router.add_get("/api/director/external-agents", handle_external_agents_status)
    app.router.add_post("/api/director/external-agents/register", handle_register_external_agent)
    app.router.add_get("/api/director/learning", handle_learning_status)
    app.router.add_get("/api/director/commands", handle_command_history)

    # HIVE HUB: push-WS dispatcher for agent CLIs (claude/hermes/director/pc2/...)
    # 100% CLI: each agent is a subprocess invocation, see hive_agents.json
    from src.api.hive_hub import routes as hive_routes
    app.router.add_routes(hive_routes)

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

    # Skill Indexer - Fast search and discovery
    try:
        from src.api.skill_index_routes import register_skill_index_routes
        register_skill_index_routes(app)
    except Exception as e:
        logger.warning(f"Failed to register skill index routes: {e}")

    # F6: Code Absorption
    app.router.add_post("/api/absorb/repo", handle_absorb_repo)
    app.router.add_get("/api/absorb/status", handle_absorb_status)

    # F7: Production Hardening
    app.router.add_get("/api/health", handle_health_circuit_breakers)
    app.router.add_get("/api/health/full", handle_health_full)
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
    app.router.add_get("/api/checkpoints/auto", handle_auto_checkpoint_status)
    app.router.add_post("/api/checkpoints/auto/inject", handle_auto_checkpoint_inject)
    app.router.add_get("/api/checkpoints/auto/reconstruct", handle_auto_checkpoint_reconstruct)

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

    # Cerebro Stats
    app.router.add_get("/api/cerebro", handle_cerebro_stats)

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

    # F20: Live Notes (sub-routes only — base CRUD handled by Notes block below)
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

    # NexusHive legacy routes — DISABLED (hive_hub.py handles /api/hive/* now)

    # Filesystem routes (Editor UI)
    app.router.add_post("/api/fs/list", handle_fs_list)
    app.router.add_post("/api/fs/read", handle_fs_read)
    app.router.add_post("/api/fs/write", handle_fs_write)
    app.router.add_post("/api/fs/exec", handle_fs_exec)

    # MCP Bridge routes
    app.router.add_get("/api/mcp/tools", handle_mcp_tools)
    app.router.add_get("/api/mcp/hub", handle_mcp_hub_search)
    app.router.add_get("/api/mcp/tools-cache", handle_mcp_tools_cache)
    app.router.add_post("/api/mcp/execute", handle_mcp_execute)
    app.router.add_post("/api/mcp/pc2", handle_mcp_execute_on_pc2)
    app.router.add_post("/api/mcp/task", handle_mcp_send_task)
    app.router.add_get("/api/mcp/discover", handle_mcp_discover)
    app.router.add_get("/api/checkpoint/metrics", handle_checkpoint_metrics)

    # Auth routes (public - no middleware protection)
    app.router.add_post("/api/auth/setup", handle_auth_setup)
    app.router.add_post("/api/auth/login", handle_auth_login)
    app.router.add_post("/api/auth/logout", handle_auth_logout)
    app.router.add_get("/api/auth/status", handle_auth_status)
    app.router.add_get("/api/auth/me", handle_auth_me)
    app.router.add_post("/api/auth/change-password", handle_auth_change_password)

    # Skills pattern routes (agent loop, comfyui)
    app.router.add_post("/api/agent-loop/run", handle_agent_loop_run)
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

    # Swarm routes
    app.router.add_get("/api/swarm/events", handle_swarm_events)
    app.router.add_get("/api/swarm/checkpoints", handle_swarm_checkpoints)
    app.router.add_get("/api/swarm/handoffs", handle_swarm_handoffs)
    app.router.add_get("/api/swarm/stats", handle_swarm_stats)
    app.router.add_route("*", "/api/swarm/context", handle_swarm_context)
    app.router.add_get("/api/swarm/lifecycle", handle_swarm_lifecycle)

    # Fusion Engine (multi-model deliberation)
    app.router.add_post("/api/fusion", handle_fusion)
    app.router.add_get("/api/fusion/stats", handle_fusion_stats)

    # Incognito mode
    app.router.add_post("/api/incognito/toggle", handle_incognito_toggle)

    # Scheduler
    app.router.add_get("/api/scheduler/tasks", handle_scheduler_list)
    app.router.add_post("/api/scheduler/tasks", handle_scheduler_add)
    app.router.add_delete("/api/scheduler/tasks/{task_id}", handle_scheduler_delete)
    app.router.add_get("/api/scheduler/runs", handle_scheduler_runs)

    # Notes
    app.router.add_get("/api/notes", handle_notes_list)
    app.router.add_post("/api/notes", handle_notes_create)
    app.router.add_put("/api/notes/{note_id}", handle_notes_update)
    app.router.add_delete("/api/notes/{note_id}", handle_notes_delete)

    # Calendar
    app.router.add_get("/api/calendar/events", handle_calendar_list)
    app.router.add_post("/api/calendar/events", handle_calendar_create)

    # Personas
    app.router.add_get("/api/personas", handle_personas_list)
    app.router.add_post("/api/personas", handle_personas_create)
    app.router.add_put("/api/personas/{persona_id}", handle_personas_update)
    app.router.add_delete("/api/personas/{persona_id}", handle_personas_delete)

    # Library
    app.router.add_get("/api/library", handle_library)

    # Themes
    app.router.add_get("/api/themes", handle_themes_list)
    app.router.add_post("/api/themes", handle_themes_set)

    # Email
    app.router.add_get("/api/email/accounts", handle_email_accounts)
    app.router.add_get("/api/email/list", handle_email_list)
    app.router.add_post("/api/email/send", handle_email_send)

    # Prompt presets
    app.router.add_get("/api/prompts/presets", handle_prompt_presets)
    app.router.add_post("/api/prompts/active", handle_prompt_set_active)

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

        # Root-level static assets (favicon, avatar, etc.)
        async def handle_root_asset(request: web.Request) -> web.Response:
            name = request.path.lstrip("/")
            file = ui_dist_path / name
            if file.exists() and file.is_file():
                return web.FileResponse(file)
            return web.Response(status=404)

        app.router.add_get("/", handle_ui_root)
        app.router.add_get("/{name}.ico", handle_root_asset)
        app.router.add_get("/{name}.png", handle_root_asset)
        app.router.add_get("/{name}.svg", handle_root_asset)
        app.router.add_get("/ui/{path:.*}", handle_ui_spa)
        app.router.add_static("/ui/assets/", ui_dist_path / "assets", name="ui_assets")
        # Voice output static files
        voice_assets_path = Path(__file__).parent.parent.parent / "ui" / "assets" / "voice"
        voice_assets_path.mkdir(parents=True, exist_ok=True)
        app.router.add_static("/ui/assets/voice/", voice_assets_path, name="voice_assets")
        # Static files (graph visualizer, etc.)
        static_path = Path(__file__).parent.parent.parent / "static"
        if static_path.exists():
            app.router.add_static("/static/", static_path, name="static_files")
            logger.info(f"Serving static files from {static_path}")

            # /graph shortcut -> /static/graph.html
            async def handle_graph_redirect(request: web.Request) -> web.Response:
                graph_html = static_path / "graph.html"
                if graph_html.exists():
                    return web.FileResponse(graph_html)
                return web.Response(status=404, text="graph.html not found")
            app.router.add_get("/graph", handle_graph_redirect)

        logger.info(f"Serving UI from {ui_dist_path}")

    return app


@web.middleware
async def _ready_gate(request: web.Request, handler):
    """Rechaza requests mientras el backend se inicializa en background."""
    ready = request.app.get("_ready", False)
    public = ("/api/status", "/api/health", "/")
    if not ready and request.path not in public:
        return web.json_response({"error": "Backend initializing"}, status=503)
    return await handler(request)


async def run_server(port: int = 9000):
    """Inicia el servidor HTTP — arranca full app pero con gate middleware."""
    nexus_config.set_port(port)
    # Note: loop.set_debug(True) introduces huge overhead — only enable via NEXUS_DEBUG=1
    if os.environ.get("NEXUS_DEBUG") == "1":
        loop = asyncio.get_running_loop()
        loop.set_debug(True)
    backend = SuperNEXUSBackend()
    AuthManager._instance = None  # reset singleton si existe

    app = create_app(backend)
    app["_ready"] = False
    app.middlewares.append(_ready_gate)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"NEXUS HTTP listening on port {port}")
    print(f"  Status: http://localhost:{port}/api/status")
    print(f"  API: http://localhost:{port}")
    ui_url = f"http://localhost:{port}/"
    if os.environ.get("NEXUS_NO_BROWSER", "").lower() not in ("1", "true"):
        try:
            webbrowser.open(ui_url)
            print(f"  UI: {ui_url} (opened in browser)")
        except Exception:
            print(f"  UI: {ui_url}")
    else:
        print(f"  UI: {ui_url}")
    print()

    async def _bg_init():
        try:
            await backend.initialize()
            app["_ready"] = True
            auth = app.get("auth")
            if auth and not auth.has_users():
                print(f'  [!] FIRST RUN: POST {"username": "admin", "password": "..."} -> /api/auth/setup')
            elif auth:
                print(f"  Auth: http://localhost:{port}/api/auth/login")
            logger.info("SuperNEXUS backend fully initialized")
        except Exception as e:
            logger.error(f"Backend init failed (degraded): {e}")

    asyncio.create_task(_bg_init(), name="bg-init")
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        await runner.cleanup()


async def handle_research(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    query = data.get("query", "")
    max_time = data.get("max_time", 300)
    if not query:
        return web.json_response({"error": "query is required"}, status=400)
    try:
        wr = getattr(backend.director, "web_researcher", None)
        svc = ResearchService(web_researcher=wr)
        result = await svc.deep_research(query, max_time=max_time)
        return web.json_response({"result": result})
    except Exception as e:
        logger.exception("research failed")
        return web.json_response({"error": str(e)}, status=500)


async def handle_execute(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    task = data.get("task", "")
    gem = data.get("gema", data.get("gem", "auto"))
    max_time = data.get("max_time", 60)
    if not task:
        return web.json_response({"error": "task is required"}, status=400)
    try:
        result = await backend.director.execute(task, gem=gem)
        content = result.data.get("content", result.data) if isinstance(result.data, dict) else result.data
        return web.json_response({
            "result": content,
            "engine": result.engine,
            "success": result.success,
            "duration_ms": result.duration_ms,
        })
    except Exception as e:
        logger.exception("execute failed")
        return web.json_response({"error": str(e)}, status=500)


# ==================== NEW MODULE ENDPOINTS ====================

async def handle_incognito_toggle(request: web.Request) -> web.Response:
    """Toggle incognito mode for a session"""
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    session_id = data.get("session_id", "")
    if not session_id:
        return web.json_response({"error": "session_id required"}, status=400)
    if not hasattr(backend, "incognito"):
        from src.core.incognito import IncognitoManager
        backend.incognito = IncognitoManager()
    state = backend.incognito.toggle(session_id)
    return web.json_response({"incognito": state, "session_id": session_id})


async def handle_scheduler_list(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend, "task_scheduler"):
        from src.core.scheduler import TaskScheduler
        backend.task_scheduler = TaskScheduler()
    return web.json_response({"tasks": backend.task_scheduler.list_tasks()})


async def handle_scheduler_add(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    if not hasattr(backend, "task_scheduler"):
        from src.core.scheduler import TaskScheduler
        backend.task_scheduler = TaskScheduler()
    task = backend.task_scheduler.add_task(data)
    return web.json_response({"task": task.to_dict()})


async def handle_scheduler_delete(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    task_id = request.match_info.get("task_id", "")
    if not hasattr(backend, "task_scheduler"):
        return web.json_response({"error": "scheduler not init"}, status=500)
    ok = backend.task_scheduler.delete_task(task_id)
    return web.json_response({"deleted": ok})


async def handle_scheduler_runs(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    task_id = request.query.get("task_id")
    if not hasattr(backend, "task_scheduler"):
        return web.json_response({"runs": []})
    return web.json_response({"runs": backend.task_scheduler.list_runs(task_id=task_id)})


async def handle_notes_list(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend, "notes"):
        from src.core.notes_calendar import NotesManager
        backend.notes = NotesManager()
    label = request.query.get("label", "")
    return web.json_response({"notes": backend.notes.list_notes(label=label)})


async def handle_notes_create(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    if not hasattr(backend, "notes"):
        from src.core.notes_calendar import NotesManager
        backend.notes = NotesManager()
    note = backend.notes.create(data)
    return web.json_response({"note": note.to_dict()})


async def handle_notes_update(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    note_id = request.match_info.get("note_id", "")
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    if not hasattr(backend, "notes"):
        return web.json_response({"error": "not init"}, status=500)
    note = backend.notes.update(note_id, data)
    return web.json_response({"note": note.to_dict() if note else None})


async def handle_notes_delete(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    note_id = request.match_info.get("note_id", "")
    if not hasattr(backend, "notes"):
        return web.json_response({"error": "not init"}, status=500)
    ok = backend.notes.delete(note_id)
    return web.json_response({"deleted": ok})


async def handle_calendar_list(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend, "calendar"):
        from src.core.notes_calendar import CalendarManager
        backend.calendar = CalendarManager()
    start = request.query.get("start", "")
    end = request.query.get("end", "")
    return web.json_response({"events": backend.calendar.list_events(start=start, end=end)})


async def handle_calendar_create(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    if not hasattr(backend, "calendar"):
        from src.core.notes_calendar import CalendarManager
        backend.calendar = CalendarManager()
    event = backend.calendar.create_event(data)
    return web.json_response({"event": event.to_dict()})


async def handle_personas_list(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend, "personas"):
        from src.core.personas import PersonaManager
        backend.personas = PersonaManager()
    return web.json_response({"personas": backend.personas.list_personas()})


async def handle_personas_create(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    if not hasattr(backend, "personas"):
        from src.core.personas import PersonaManager
        backend.personas = PersonaManager()
    persona = backend.personas.create(data)
    return web.json_response({"persona": persona.to_dict()})


async def handle_personas_update(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    persona_id = request.match_info.get("persona_id", "")
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    if not hasattr(backend, "personas"):
        return web.json_response({"error": "not init"}, status=500)
    persona = backend.personas.update(persona_id, data)
    return web.json_response({"persona": persona.to_dict() if persona else None})


async def handle_personas_delete(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    persona_id = request.match_info.get("persona_id", "")
    if not hasattr(backend, "personas"):
        return web.json_response({"error": "not init"}, status=500)
    ok = backend.personas.delete(persona_id)
    return web.json_response({"deleted": ok})


async def handle_library(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    from src.core.library import LibraryManager
    lib = LibraryManager()
    type_filter = request.query.get("type", "")
    search = request.query.get("search", "")
    return web.json_response({"items": lib.get_all(type_filter=type_filter, search=search), "stats": lib.get_stats()})


async def handle_themes_list(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend, "themes"):
        from src.core.themes import ThemeManager
        backend.themes = ThemeManager()
    return web.json_response({"themes": backend.themes.list_themes(), "active": backend.themes.active_theme, "pattern": backend.themes.pattern})


async def handle_themes_set(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    if not hasattr(backend, "themes"):
        from src.core.themes import ThemeManager
        backend.themes = ThemeManager()
    name = data.get("name", "")
    if name:
        backend.themes.set_theme(name)
    pattern = data.get("pattern")
    if pattern:
        backend.themes.set_pattern(pattern)
    return web.json_response({"success": True, "active": backend.themes.active_theme, "pattern": backend.themes.pattern})


async def handle_email_accounts(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend, "email_mgr"):
        from src.core.email_manager import EmailManager
        backend.email_mgr = EmailManager()
    return web.json_response({"accounts": backend.email_mgr.list_accounts()})


async def handle_email_list(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    account_id = request.query.get("account_id", "")
    folder = request.query.get("folder", "INBOX")
    if not hasattr(backend, "email_mgr"):
        return web.json_response({"error": "not init"}, status=500)
    emails = await backend.email_mgr.list_emails(account_id, folder)
    return web.json_response({"emails": emails})


async def handle_email_send(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    if not hasattr(backend, "email_mgr"):
        return web.json_response({"error": "not init"}, status=500)
    result = await backend.email_mgr.send_email(
        data.get("account_id", ""), data.get("to", ""),
        data.get("subject", ""), data.get("body", ""),
    )
    return web.json_response(result)


async def handle_prompt_presets(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    if not hasattr(backend, "prompt_mgr"):
        from src.core.prompt_manager import PromptManager
        backend.prompt_mgr = PromptManager()
    return web.json_response({"presets": backend.prompt_mgr.list_presets(), "active": backend.prompt_mgr.active_preset})


async def handle_prompt_set_active(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    if not hasattr(backend, "prompt_mgr"):
        from src.core.prompt_manager import PromptManager
        backend.prompt_mgr = PromptManager()
    ok = backend.prompt_mgr.set_active(data.get("name", ""))
    return web.json_response({"success": ok, "active": backend.prompt_mgr.active_preset})


# ---- PRODUCER-VERIFIER LOOP ----

async def handle_producer_verifier_loop(request: web.Request) -> web.Response:
    backend: SuperNEXUSBackend = request.app["backend"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    task = data.get("task", "")
    max_iterations = data.get("max_iterations", 3)
    success_criteria = data.get("success_criteria", "")

    if not task:
        return web.json_response({"error": "task is required"}, status=400)

    try:
        from src.evaluation.verifier_agent import VerifierAgent
        from src.core.producer_verifier_loop import ProducerVerifierLoop

        async def producer(ctx: dict) -> str:
            result = await backend.director.execute(ctx.get("task", task))
            content = result.data
            if isinstance(content, dict):
                return content.get("content", json.dumps(content))
            return str(content)

        async def verifier_fn(task: str, result: str, success_criteria: str) -> dict:
            va = VerifierAgent(
                llm_executor=backend.director._call_ollama if hasattr(backend.director, '_call_ollama') else None,
            )
            report = await va.verify_code(
                task=task,
                result=result,
                success_criteria=success_criteria,
            )
            return {
                "verdict": report.verdict.value,
                "feedback": report.feedback,
                "checks": [
                    {"name": c.name, "method": c.method, "evidence": c.evidence[:200], "result": c.result}
                    for c in report.checks
                ],
                "to_text": report.to_text(),
            }

        loop = ProducerVerifierLoop(
            producer=producer,
            verifier=verifier_fn,
            max_iterations=max_iterations,
        )

        loop_result = await loop.run(task=task, success_criteria=success_criteria)

        return web.json_response({
            "passed": loop_result.passed,
            "iterations": loop_result.iterations,
            "final_output": loop_result.final_output[:1000],
            "report": loop_result.report[:2000],
            "iteration_logs": loop_result.iteration_logs,
        })
    except ImportError as e:
        return web.json_response({"error": f"Module not available: {e}"}, status=501)
    except Exception as e:
        logger.exception("producer-verifier loop failed")
        return web.json_response({"error": str(e)}, status=500)


async def handle_pvl_status(request: web.Request) -> web.Response:
    """Check if Producer-Verifier modules are available"""
    try:
        from src.evaluation.verifier_agent import VerifierAgent
        from src.core.producer_verifier_loop import ProducerVerifierLoop
        return web.json_response({
            "available": True,
            "verifier_checks": ["build", "tests", "lint", "diff_review", "adversarial", "llm_semantic"],
            "max_iterations_default": 3,
        })
    except ImportError as e:
        return web.json_response({"available": False, "error": str(e)})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    asyncio.run(run_server(port))
