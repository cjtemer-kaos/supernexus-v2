"""
DirectorNexus v2 - Cerebro central de SuperNEXUS

Combina:
- Runtime loop (Rowboat pattern)
- LLM semantic routing (OpenSwarm pattern)
- Agent capabilities registry (NEXUS pattern)
- Multi-engine orchestration (ConnectivityLayer)
- AI Tools Registry (Brain + Tools pattern)

NEXUS es el cerebro. Los modelos de IA son herramientas stateless.
"""

import asyncio
import json
import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# --- Core ---
from src.core.connectivity import ConnectivityLayer, EngineResult
from src.core.ai_tools import AIToolsRegistry
from src.core.session_manager import SessionManager
from src.core.ollama import OllamaClient

# --- Orchestration ---
from src.core.token_budget import TokenBudget
from src.core.goal_detector import GoalDetector
from src.core.dag_coordinator import DAGCoordinator
from src.core.checkpoint import CheckpointStore
from src.core.recipe_engine import RecipeEngine
from src.core.loop_guard import LoopGuard
from src.core.approval_gate import ApprovalGate
from src.core.risk_assessor import RiskAssessor
from src.core.retry_manager import RetryManager
from src.core.tool_guardrails import ToolCallGuardrailController, GuardrailConfig
from src.core.custom_commands import CustomCommandManager

# --- Memory & Knowledge ---
from src.core.graph_evolution import GraphEvolution
from src.core.knowledge_vault import KnowledgeVault
from src.core.memory_health import MemoryHealthMonitor
from src.core.hybrid_memory import HybridMemoryBackend
from src.core.memory_consolidator import MemoryConsolidator
from src.core.fts5_search import FTS5Search
from src.core.rag_engine import RAGEngine

# --- Agent Infrastructure ---
from src.core.tool_monitor import ToolMonitor
from src.core.collaboration_hall import CollaborationHall
from src.core.live_notes import LiveNotes
from src.core.background_review import BackgroundReviewDaemon
from src.core.doctor import Doctor
from src.core.gema_host import GemaHost
from src.core.judge_pipeline import JudgePipeline
from src.core.cursor_checkpoint import CursorCheckpoint
from src.core.message_bus import MessageBus
from src.core.nexus_hive import NexusHive
from src.core.sub_agent_spawner import SubAgentSpawner
from src.core.mixture_of_agents import MixtureOfAgents
from src.core.skill_curator import SkillCurator
from src.core.agent_loop import AgentLoop, AgentLoopResult

# --- Integrations ---
from src.integrations.codegraph_integration import CodeGraphIntegration
from src.core.voice_pipeline import VoicePipeline
from src.core.comfyui_gateway import ComfyUIGateway
from src.core.context_compactor import ContextCompactor
from src.core.hooks_engine import HooksEngine, HookPhase
from src.core.error_compactor import ErrorCompactor
from src.skills.skill_loader import ProgressiveSkillLoader
from src.core.session_context_recovery import SessionContextRecovery, SessionState
from src.core.background_workers import BackgroundWorkerManager
from src.core.o1_indexing import O1IndexManager
from src.core.graceful_degradation import GracefulDegradationManager

# --- Training & Learning ---
from src.core.peer_chat import PeerChat
from src.core.data_collector import DataCollector
from src.core.nexus_trainer import NexusTrainer
from src.core.self_model import SelfModelEngine
from src.core.local_tool_calling import LocalToolCaller, ToolDefinition

# --- Bridges ---
from src.bridges.remote_node_bridge import RemoteNodeBridge

# --- New Provider + Runner (Orquestador Multi-Motor) ---
from src.core.provider_base import (
    ProviderRegistry, ProviderProfile, OllamaProvider, FallbackProvider, LLMMessage,
)
from src.core.agent_runner import AgentRunner, AgentRunSpec
from src.core.orchestrator import NexusOrchestrator, OrchestratorConfig
from src.core.actor_base import ActorSystem, GemaActor, SupervisorActor, ActorMessage, ActorResult, Actor
from src.core.adaptive_router import AdaptiveRouter, ThompsonSampler, AdaptiveRouterActor
from src.core.self_learning_loop import SelfLearningLoop
from src.core.tool_registry import DirectorToolRegistry

# --- F1: Director Soberano ---
from src.core.decision_engine import DecisionEngine, LLMAdapter
from src.core.command_protocol import CommandDispatcher, Command, CommandResult, CommandStatus
from src.core.external_agent import ExternalAgentRegistry, ExternalAgent, HTTPAdapter, CLIAdapter, MessageBoardAdapter
from src.core.sub_director import SubDirectorRegistry
from src.core.learning_loop import LearningLoop

# --- F2: Memory Hardening ---
from src.core.memory_triage import MemoryTriage
from src.core.pointer_store import PointerStore
from src.core.dream_consolidation import DreamConsolidator, DreamConfig
from src.core.perplexity_scorer import PerplexityScorer

# --- F3: Protocol Stack ---
from src.core.acp_protocol import ACPRouter, ACPMessage, ACPMessageType
from src.core.a2a_server import A2AServer
from src.core.protocol_router import ProtocolRouter, DiscoveryService, ServiceEntry, Protocol

# --- F4: Skills Marketplace ---
from src.core.skill_marketplace import SkillRegistry

# --- F6: Code Absorption ---
from src.core.code_absorber import CodeAbsorber

# --- F7: Production Hardening ---
from src.core.circuit_breaker import CircuitBreaker, HealthChecker
from src.core.token_monitor import TokenMonitor

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class GemCapability:
    """Capacidad de un Gema"""
    name: str
    tags: List[str]
    description: str
    model: str = ""
    parallel_capable: bool = True
    execution_count: int = 0
    success_count: int = 0
    total_latency_ms: float = 0


@dataclass
class TaskClassification:
    """Resultado de clasificacion de tarea"""
    task: str
    selected_gems: List[str]
    selected_engines: List[str]
    confidence: float
    can_parallelize: bool
    priority: int = 3


class DirectorNexus:
    """
    DirectorNexus v2 - Orquestador central (CEREBRO)

    SIEMPRE EN MEMORIA (nunca se olvida):
    - Identidad (quien es, su funcion)
    - 15 gemas disponibles
    - Skills registry base
    - Conexiones (SSH, Tailscale, MCP)
    - AI Tools Registry (herramientas de IA)

    MEMORIA SELECTIVA POR PROYECTO:
    - Contexto especifico del proyecto activo
    - Skills cargados para el proyecto
    - Historial de conversaciones del proyecto

    ARQUITECTURA BRAIN + TOOLS:
    - DirectorNexus mantiene contexto, identidad y estado
    - AI Tools son stateless, se invocan con prompts especificos
    - Cada herramienta tiene un rol definido y system prompt acotado
    """

    # Identidad permanente
    IDENTITY = {
        "name": "NEXUS IA",
        "version": "2.0",
        "role": "Cerebro central del ecosistema NEXUS",
        "function": "Coordinar motores, gemas, memoria y herramientas de IA para resolver tareas",
        "architecture": "Brain + Tools (NEXUS es el cerebro, los modelos son herramientas)",
    }

    def __init__(self, project: str = "default"):
        self.identity = self.IDENTITY.copy()
        self.current_project = project
        self.execution_log: List[Dict] = []
        self._stats_lock = asyncio.Lock()
        self._project_root = str(Path(__file__).resolve().parent.parent.parent)

        self._init_core()
        self._init_orchestration()
        self._init_memory()
        self._init_agents()
        self._init_integrations()
        self._init_training()
        self._init_tooling()
        self._init_new_providers()

        self._init_adaptive_router()
        self._init_self_learning()
        self._load_gemas()
        self._init_actor_system()
        self._init_sovereign_director()
        self._init_memory_hardening()
        self._init_protocol_stack()
        self._init_skill_marketplace()
        self._init_code_absorption()
        self._init_production_hardening()
        self.o1_index.build_gema_index(self.gemas)
        self.o1_index.build_skill_index(self.skill_loader)

        # Autoconocimiento: registro unificado de herramientas
        self.tool_registry = DirectorToolRegistry()
        self.tool_registry.rebuild(self)

        logger.info(f"DirectorNexus v2 initialized (project: {project}, architecture: Brain + Tools)")

    # ── Init groups ──────────────────────────────────────────────

    def _init_core(self):
        self.connectivity = ConnectivityLayer()
        self.ai_tools = AIToolsRegistry()
        self.gemas: Dict[str, GemCapability] = {}
        self.sessions = SessionManager()
        self.token_budget = TokenBudget()

        from src.core.llm_gateway import LLMGateway
        self.llm_gateway = LLMGateway()
        self.llm_gateway.add_provider("ollama", "http://localhost:11434", priority=0)
        remote_ip = os.environ.get("SUPER_NEXUS_REMOTE_NODE_IP", "")
        if remote_ip:
            self.llm_gateway.add_provider("remote", f"http://{remote_ip}:11434", priority=1)
        self._register_teacher_providers()

    def _init_orchestration(self):
        self.goal_detector = GoalDetector()
        self.dag = DAGCoordinator()
        self.checkpoints = CheckpointStore()
        self.recipes = RecipeEngine()
        self.loop_guard = LoopGuard(max_history=50, exact_threshold=3, semantic_threshold=0.8)
        self.approval = ApprovalGate()
        self.risk = RiskAssessor()
        self.retry = RetryManager()
        self.tool_guardrails = ToolCallGuardrailController()
        self.custom_commands = CustomCommandManager()
        self.o1_index = O1IndexManager()
        self.degradation_mgr = GracefulDegradationManager()

    def _init_memory(self):
        self.graph_evolution = GraphEvolution()
        self.vault = KnowledgeVault()
        self.memory_health = MemoryHealthMonitor()
        self.hybrid_memory = HybridMemoryBackend()
        self.memory_consolidator = MemoryConsolidator()
        self.search = FTS5Search()
        self.rag_engine = RAGEngine()
        self.hive = NexusHive()
        self.context_recovery = SessionContextRecovery()
        self._recover_session_context(self.current_project)

    def _init_agents(self):
        self.gema_host = GemaHost(project_root=self._project_root)
        self.gema_host.initialize()
        self.gema_host.start_health_checks(interval=30)

        self.judge = JudgePipeline(llm_executor=self.ai_tools.quick_response)
        self.cursor = CursorCheckpoint()
        self.message_bus = MessageBus()
        self.sub_agents = SubAgentSpawner(executor=self.execute)
        self.moa = MixtureOfAgents(executor=self.ai_tools.quick_response)
        self.agent_loop = AgentLoop(
            llm_fn=self._agent_loop_llm,
            max_iterations=10,
            workdir=self._project_root,
        )
        self.doctor = Doctor()
        self.tool_monitor = ToolMonitor()
        self.hall = CollaborationHall()
        self.live_notes = LiveNotes()
        self.review_daemon = BackgroundReviewDaemon()

        from src.core.mcp_client_bridge import MCPClientBridge
        self.mcp_client = MCPClientBridge(workdir=self._project_root)
        self.mcp_client.register_builtin_servers()

    def _init_integrations(self):
        self.codegraph = CodeGraphIntegration(project_root=self._project_root)
        self.voice_pipeline = VoicePipeline()
        self.comfyui = ComfyUIGateway()
        self.compactor = ContextCompactor()
        self.hooks = HooksEngine()
        self.hooks.register_builtin_hooks(workdir=Path(self._project_root))
        self.error_compactor = ErrorCompactor()
        self.skills = SkillCurator()
        skills_base = Path(self._project_root) / "src" / "skills" / "hub"
        self.skill_loader = ProgressiveSkillLoader(skills_base)
        self.worker_manager = BackgroundWorkerManager()
        self.worker_manager.register_all()
        self._setup_degradation_fallbacks()

    def _init_training(self):
        from src.core.recursive_seed_ai import RecursiveSeedAI, RecursiveImprovementLoop
        self.recursive_seed = RecursiveSeedAI()
        self.recursive_improvement = RecursiveImprovementLoop(self.recursive_seed)

        from src.core.model_autopsy import ModelAutopsy
        self.model_autopsy = ModelAutopsy(llm_gateway=self.llm_gateway)

        from src.core.three_loop import ThreeLoopSystem
        self.three_loop = ThreeLoopSystem(
            recursive_seed=self.recursive_seed,
            model_autopsy=self.model_autopsy,
        )

        self.peer_chat = PeerChat()
        self.data_collector = DataCollector(min_quality=0.7)

        self.remote_bridge = RemoteNodeBridge()
        async def _remote_executor(command: str) -> Dict:
            try:
                return await self.remote_bridge.execute_remote(command, timeout=300)
            except Exception as e:
                logger.warning(f"Remote executor failed: {e}")
                return {"success": False, "error": str(e)}
        self.nexus_trainer = NexusTrainer(execute_on_pc2=_remote_executor)

        self.ai_tools.data_collector = self.data_collector
        self.ai_tools.three_loop = self.three_loop

        self.self_model = SelfModelEngine(
            project_root=self._project_root,
            ollama_client=OllamaClient(),
            execution_log=self.execution_log,
            storage_path=Path.home() / ".nexus" / "self_model_state.json",
        )

    def _init_tooling(self):
        self.tool_caller = LocalToolCaller(
            ollama_client=OllamaClient(),
            model="nexus-coder",
        )
        self.tool_caller.register_handler(
            "read_file", "Read a file and return its contents",
            {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            handler=lambda path: self.ai_tools.workspace.read_file(path),
        )
        self.tool_caller.register_handler(
            "search_code", "Search for a pattern in code files",
            {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string", "default": "."}}, "required": ["pattern"]},
            handler=lambda pattern, path=".": self.ai_tools._tool_grep(pattern, path),
        )
        self.tool_caller.register_handler(
            "list_files", "List files in a directory",
            {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            handler=lambda path: self.ai_tools.workspace.list_dir(path),
        )

    async def initialize_async(self):
        """Initialize async components (RAG, self-model). Call after __init__."""
        # RAG Engine
        try:
            await self.rag_engine.initialize()
            logger.info("RAG engine initialized")
        except Exception as e:
            logger.error(f"RAG engine init failed: {e}")

        # Self-model
        try:
            await self.self_model.initialize()
            logger.info("Self-model initialized with auto-discovery")
        except Exception as e:
            logger.error(f"Self-model initialization failed: {e}")

    async def initialize_self_model(self):
        """Legacy wrapper — use initialize_async() instead."""
        await self.initialize_async()

    def _load_gemas(self):
        """Carga los 22 gemas con sus capacidades"""
        gemas_data = [
            ("ayuda", ["help", "ayuda", "tutorial", "guide", "onboarding", "capacidades", "aprendizaje"], "Guia reactiva del sistema - se adapta al usuario y ensena capacidades", "gemma4:latest"),
            ("director", ["leadership", "orchestration", "planning"], "Orquestacion y liderazgo", "gemma4:latest"),
            ("code", ["programming", "code-review", "refactoring"], "Programacion y desarrollo", "qwen2.5-coder:7b"),
            ("scholar", ["research", "learning", "web-search"], "Investigacion y aprendizaje", "gemma4:latest"),
            ("architect", ["architecture", "design", "infrastructure"], "Diseno de sistemas", "qwen2.5-coder:7b"),
            ("creative", ["creative", "writing", "content"], "Contenido creativo", "qwen2.5-coder:7b"),
            ("sage", ["memory", "persistence", "learning"], "Persistencia y memoria", "gemma4:latest"),
            ("analyst", ["analysis", "data", "metrics"], "Analisis de datos", "nemotron-3-nano:4b"),
            ("engineer", ["engineering", "tools", "optimization"], "Ingenieria y herramientas", "qwen2.5-coder:7b"),
            ("debugger", ["debugging", "troubleshooting", "error-handling"], "Debugging", "qwen2.5-coder:7b"),
            ("optimizer", ["optimization", "performance", "tuning"], "Optimizacion", "qwen2.5-coder:7b"),
            ("tester", ["testing", "qa", "validation"], "Testing y QA", "qwen2.5-coder:7b"),
            ("security", ["security", "compliance", "protection"], "Seguridad", "gemma4:latest"),
            ("devops", ["devops", "deployment", "infrastructure"], "DevOps", "qwen2.5-coder:7b"),
            ("trainer", ["training", "education", "teaching"], "Entrenamiento", "qwen2.5-coder:7b"),
            ("biblioteca", ["organization", "knowledge", "indexing"], "Organizacion de conocimiento", "gemma4:latest"),
            # Nuevas gemas portadas de NEXUS_MASTER
            ("vision", ["screenshot", "screen-control", "pc-control", "vision", "mouse", "keyboard"], "Control visual de PC con Ollama vision", "qwen2.5vl:7b"),
            ("opencode", ["opencode", "cli-agent", "code-execution"], "Agente CLI de codigo", "qwen2.5-coder:7b"),
            ("codex", ["codex", "handoff", "delegation"], "Delegacion a Codex CLI", "qwen2.5-coder:7b"),
            ("design", ["design", "ui", "ux", "multimedia", "video", "scene"], "Diseno multimedia y Veo", "qwen2.5-coder:7b"),
            ("music", ["music", "audio", "sound", "voice", "tts", "stt"], "Audio, voz y musica", "qwen2.5-coder:7b"),
            ("prompter", ["prompt", "token", "optimization", "compression"], "Optimizacion de prompts y tokens", "qwen2.5-coder:7b"),
            ("producer", ["schedule", "task", "automation", "rcon", "server", "rust"], "Automatizacion y servidores", "qwen2.5-coder:7b"),
        ]

        for name, tags, desc, model in gemas_data:
            self.gemas[name] = GemCapability(
                name=name,
                tags=tags,
                description=desc,
                model=model,
            )

    def _recover_session_context(self, project: str):
        """Recuperar contexto de sesión al iniciar y guardar en memoria"""
        try:
            context = self.context_recovery.build_session_context(project)
            if context.get("context_summary"):
                # Guardar en archivo JSON para que MCP bridge lo lea
                context_file = Path.home() / ".nexus" / "brain" / "recovered_context.json"
                context_file.parent.mkdir(parents=True, exist_ok=True)
                with open(context_file, "w", encoding="utf-8") as f:
                    json.dump(context, f, indent=2, ensure_ascii=False)
                logger.info(f"Session context recovered and saved to {context_file}")
        except Exception as e:
            logger.error(f"Failed to recover session context: {e}")

    def _setup_degradation_fallbacks(self):
        """Configurar fallbacks para graceful degradation"""
        # Memory consolidator fallback
        self.degradation_mgr.register_component(
            name="memory_consolidator",
            primary_fn=self.memory_consolidator.consolidate if hasattr(self.memory_consolidator, "consolidate") else lambda x: {},
            fallback_fn=lambda x: {"status": "degraded", "action": "memory_consolidation_skipped", "data": x},
            health_check_fn=lambda: True,
        )
        
        # Context compactor fallback
        self.degradation_mgr.register_component(
            name="context_compactor",
            primary_fn=self.compactor.compact if hasattr(self.compactor, "compact") else lambda x: x,
            fallback_fn=lambda x: x,
        )
        
        # Skill loader fallback
        self.degradation_mgr.register_component(
            name="skill_loader",
            primary_fn=self.skill_loader.load_skill if hasattr(self.skill_loader, "load_skill") else lambda x: "",
            fallback_fn=lambda x: f"# Skill {x} unavailable (degraded mode)",
        )
        
        # GemaHost fallback
        self.degradation_mgr.register_component(
            name="gema_host",
            primary_fn=lambda g, t, c: self.gema_host.execute_gema(g, t, c),
            fallback_fn=lambda g, t, c: {"error": "gema_host_unavailable", "note": "fallback_to_ai_tools"},
        )
        
        logger.info(f"Graceful degradation configured with {len(self.degradation_mgr.components)} components")

    def persist_session_state(self, session_id: str, project: str, messages: List[Dict], tokens: int = 0):
        """Persistir estado de sesión (llamar periódicamente o al finalizar)"""
        try:
            state = SessionState(
                session_id=session_id,
                project=project,
                started_at=datetime.now().isoformat(),
                last_activity=datetime.now().isoformat(),
                message_count=len(messages),
                total_tokens=tokens,
                recent_messages=messages[-self.context_recovery.max_recent_messages:],
            )
            self.context_recovery.save_session_state(state)
        except Exception as e:
            logger.error(f"Failed to persist session state: {e}")

    async def _agent_loop_llm(self, prompt: str, model: str = "gemma4:latest") -> str:
        """Bridge for AgentLoop → Ollama via ConnectivityLayer."""
        try:
            result = await self.ai_tools.quick_response(
                task=prompt, gem="director", context="", model_override=model
            )
            return result.get("content", str(result))
        except Exception as e:
            return f"Error: {e}"

    async def run_agent_loop(self, task: str, context: str = "") -> dict:
        """Run TDAO agent loop for complex multi-step tasks."""
        result = await self.agent_loop.run(task, context)
        return {
            "success": result.success,
            "output": result.final_output,
            "iterations": result.iterations,
            "steps": len(result.steps),
            "duration_ms": result.total_duration_ms,
        }

    async def classify_task(self, task: str) -> TaskClassification:
        """
        Clasifica tarea usando routing semantico con self-model.
        Determina que gema(s) y motor(es) usar.
        Includes progressive skill matching.
        """
        task_lower = task.lower()

        # Phase 1: Try self-model routing if initialized
        if self.self_model.capability_map:
            best_gema = self.self_model.get_best_gema_for_task(task)
            if best_gema:
                selected_gems = {best_gema}
            else:
                selected_gems = set()
        else:
            selected_gems = set()

        # Fallback: O(1) routing usando indices
        if not selected_gems:
            for keyword in task_lower.split():
                if len(keyword) > 2:
                    gemas = self.o1_index.get_gemas_by_keyword(keyword)
                    selected_gems.update(gemas)
        
        # Fallback a keyword matching tradicional si no hay matches
        if not selected_gems:
            keywords_to_gem = {
                "code": "code", "python": "code", "javascript": "code", "programming": "code", "refactor": "code",
                "architecture": "architect", "design": "architect", "system": "architect", "infra": "architect",
                "research": "scholar", "learn": "scholar", "investigate": "scholar", "busca": "scholar", "investiga": "scholar",
                "debug": "debugger", "error": "debugger", "bug": "debugger", "fix": "debugger",
                "creative": "creative", "write": "creative", "content": "creative",
                "test": "tester", "qa": "tester",
                "security": "security", "safe": "security", "encrypt": "security",
                "deploy": "devops", "devops": "devops", "docker": "devops",
                "optimize": "optimizer", "performance": "optimizer", "speed": "optimizer",
                "analyze": "analyst", "data": "analyst", "metrics": "analyst",
                "organize": "biblioteca", "knowledge": "biblioteca", "index": "biblioteca",
                "teach": "trainer", "train": "trainer", "educate": "trainer",
                "engineer": "engineer", "tools": "engineer",
                "memory": "sage", "persist": "sage",
                "screenshot": "vision", "screen": "vision", "pc control": "vision", "vision": "vision",
                "mouse": "vision", "keyboard": "vision", "click": "vision",
                "opencode": "opencode", "cli agent": "opencode",
                "codex": "codex", "handoff": "codex", "delegar": "codex",
                "multimedia": "design", "video": "design", "scene": "design", "veo": "design",
                "music": "music", "audio": "music", "voice": "music", "tts": "music", "stt": "music", "habla": "music",
                "prompt": "prompter", "token": "prompter", "compression": "prompter", "optimizar tokens": "prompter",
                "schedule": "producer", "automation": "producer", "rcon": "producer", "rust server": "producer",
                "task": "producer", "scheduler": "producer",
                "help": "ayuda", "ayuda": "ayuda", "tutorial": "ayuda", "guide": "ayuda", "onboarding": "ayuda",
                "capacidades": "director", "que puedes hacer": "director", "como funciona": "director",
                "empezar": "ayuda", "que sabes hacer": "director", "funcionalidades": "director",
                "gemas": "director", "activas": "director", "estado": "director", "status": "director",
            }
            for keyword, gem in keywords_to_gem.items():
                if keyword in task_lower:
                    selected_gems.add(gem)

        if not selected_gems:
            selected_gems = {"director"}

        # Director handles meta-questions directly
        if "director" in selected_gems:
            selected_gems.discard("ayuda")

        # Seleccion de motores segun tipo de tarea
        engines = ["nexus_master"]  # Default
        if any(k in task_lower for k in ["gpu", "heavy", "train", "video", "image"]):
            engines.append("nexus_remote")
        if any(k in task_lower for k in ["research", "web", "search"]):
            engines.append("openclaw")

        return TaskClassification(
            task=task,
            selected_gems=list(selected_gems),
            selected_engines=engines,
            confidence=0.8 if len(selected_gems) > 1 else 0.5,
            can_parallelize=len(engines) > 1,
        )

    async def get_relevant_skills(self, task: str, top_k: int = 3) -> str:
        """Get relevant skill content for task context."""
        matched = self.skill_loader.match_skills(task, top_k=top_k)
        if not matched:
            return ""
        contents = []
        for name in matched:
            content = self.skill_loader.load_skill(name)
            if content and not content.startswith("Skill not found") and not content.startswith("Error"):
                contents.append(f"## Skill: {name}\n{content[:2000]}")
        return "\n\n".join(contents)

    # ── Nuevo Sistema de Proveedores (Orquestador Multi-Motor) ────────────

    def _init_new_providers(self):
        """Inicializa ProviderRegistry + fallbacks vía perfiles declarativos."""
        self.provider_registry = ProviderRegistry()

        PROFILES = [
            ProviderProfile(name="ollama", model="qwen2.5-coder:7b", base_url="http://localhost:11434",
                            description="Fallback genérico para GemaActors", tags=["gema", "fallback"]),
            ProviderProfile(name="ollama-gema", model="nexus-coder", base_url="http://localhost:11434",
                            description="Gema principal (nexus-coder)", tags=["gema", "primary"]),
            ProviderProfile(name="ollama-local", model="qwen2.5-coder:7b", base_url="http://localhost:11434",
                            description="Coder local", tags=["coder", "fallback"]),
            ProviderProfile(name="ollama-fallback", model="qwen2.5:0.5b", base_url="http://localhost:11434",
                            description="Tiny para fallback extremo", tags=["tiny", "last-resort"]),
            ProviderProfile(name="gema-con-fallback", model="nexus-coder", base_url="http://localhost:11434",
                            fallbacks=["ollama-local", "ollama-fallback"],
                            fallback_threshold=2, cooldown_s=60,
                            description="Gema con circuit breaker a local → tiny", tags=["gema", "fallback-chain"]),
        ]
        self.provider_registry.configure(PROFILES)

        # Tool executor wrapper: conecta AgentRunner con los handlers del Director
        async def tool_executor(name: str, args: dict) -> str:
            caller = self.tool_caller
            if hasattr(caller, 'execute_tool'):
                return await caller.execute_tool(name, args)
            if hasattr(caller, '_tools') and name in caller._tools:
                return await caller._tools[name].handler(**args)
            return f"Tool '{name}' not found"
        self._multi_motor_tool_executor = tool_executor

        # NexusOrchestrator: descomposición LLM + ejecución TaskQueue + síntesis
        self.orchestrator = NexusOrchestrator(OrchestratorConfig(
            provider_registry=self.provider_registry,
            tool_executor=tool_executor,
            get_tool_schemas=lambda: self.tool_caller.get_tool_schemas() if hasattr(self, 'tool_caller') else [],
            max_iterations_per_task=5,
            max_concurrent_tasks=3,
            coordinator_provider="gema-con-fallback",
        ))

        logger.info("ProviderRegistry + AgentRunner + Orchestrator initialized (Orquestador Multi-Motor)")

    # ── Adaptive Router (Thompson Sampling) ─────────────────────

    def _init_adaptive_router(self):
        self._adaptive_router = AdaptiveRouter()
        self._adaptive_sampler = self._adaptive_router._sampler
        logger.info("AdaptiveRouter initialized with Thompson Sampling")

    # ── Self-Learning Loop ───────────────────────────────────────

    def _init_self_learning(self):
        self._self_learning = SelfLearningLoop(
            judge_fn=getattr(self, 'judge', None),
            memory_store_fn=lambda k, v: self.hive.remember(k, v) if hasattr(self, 'hive') else None,
            adaptive_router=self._adaptive_router if hasattr(self, '_adaptive_router') else None,
            interval_s=180.0,
        )
        logger.info("SelfLearningLoop initialized")

    # ── Actor System (Sprint 2) ──────────────────────────────────

    def _init_actor_system(self):
        """Inicializa el sistema de actores: gemas como GemaActors + DMN."""
        from src.core.actor_base import ActorSystem, GemaActor, BackgroundCognition

        self.actor_system = ActorSystem()
        gemas = list(getattr(self, 'gemas', {}).keys())

        # Registrar supervisor
        self._actor_supervisor = SupervisorActor(actor_id="supervisor-v1")
        self.actor_system.register(self._actor_supervisor)

        # Registrar gemas como GemaActors
        for gema_name in gemas:
            gema = self.gemas[gema_name]
            actor = GemaActor(
                name=gema_name,
                model=gema.model or "qwen2.5-coder:7b",
                provider_registry=self.provider_registry,
                tool_executor=getattr(self, '_multi_motor_tool_executor', None),
                get_tool_schemas=lambda: self.tool_caller.get_tool_schemas() if hasattr(self, 'tool_caller') else [],
                actor_id=f"gema-{gema_name}",
            )
            self.actor_system.register(actor, parent=self._actor_supervisor)

        # Registrar DMN (Background Cognition)
        self._dmn_actor = BackgroundCognition(
            review_daemon=self.review_daemon,
            worker_manager=self.worker_manager,
            memory_consolidator=self.memory_consolidator,
            interval_s=120.0,
            actor_id="dmn-v1",
        )
        self.actor_system.register(self._dmn_actor, parent=self._actor_supervisor)

        # Registrar RouterActor (MessageIntent routing)
        from src.core.actor_base import RouterActor
        self._router_actor = RouterActor(self.actor_system, actor_id="router-v1")
        self.actor_system.register(self._router_actor, parent=self._actor_supervisor)

        # Registrar AdaptiveRouterActor (Thompson Sampling)
        self._adaptive_router_actor = AdaptiveRouterActor(
            self._adaptive_router, self.actor_system, actor_id="adaptive-router-v1",
        )
        self.actor_system.register(self._adaptive_router_actor, parent=self._actor_supervisor)

        # Registrar SelfLearningLoop
        self.actor_system.register(self._self_learning, parent=self._actor_supervisor)

        n_extra = len([a for a in self.actor_system._actors.values() if a.name not in [g for g in gemas] and a.name not in ("supervisor",)])
        logger.info("ActorSystem initialized: %d actors (supervisor + %d gemas + %d extras)",
                    len(self.actor_system._actors), len(gemas), n_extra)

    async def orchestrate_multi_motor(self, task: str, context: str = "",
                                       providers: list[str] | None = None) -> dict:
        """
        Orquestación multi-motor: ejecuta la misma tarea con múltiples
        proveedores/gemas en paralelo, evalúa con JudgePipeline, sintetiza.

        Args:
            task: Tarea a ejecutar
            context: Contexto adicional
            providers: Lista de proveedores a usar (default: todos)
        Returns:
            Dict con resultados individuales, evaluación y síntesis
        """
        from datetime import datetime

        if not providers:
            providers = ["ollama-gema", "ollama-local"]
            if self.token_budget.is_within_budget():
                providers.append("ollama-fallback")

        start = datetime.now()
        provider_instances = []
        for name in providers:
            p = self.provider_registry.get(name)
            if p:
                provider_instances.append((name, p))

        if not provider_instances:
            return {"success": False, "error": "No providers available"}

        tool_schemas = self.tool_caller.get_tool_schemas() if hasattr(self, 'tool_caller') else []
        spec = AgentRunSpec(
            messages=[LLMMessage(role="user", content=task)],
            tools_definitions=tool_schemas,
            max_iterations=3,
        )

        async def run_single(name: str, provider) -> dict:
            try:
                runner = AgentRunner(provider, tool_executor=self._multi_motor_tool_executor)
                result = await runner.run(spec)
                return {"name": name, "success": result.stop_reason != "error",
                        "content": result.content[-800:] if result.content else "",
                        "stop_reason": result.stop_reason,
                        "usage": result.usage, "error": None}
            except Exception as e:
                logger.exception("Provider %s failed", name)
                return {"name": name, "success": False, "content": "", "error": str(e)}

        tasks = [run_single(name, p) for name, p in provider_instances]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        best = None
        for r in results:
            if r.get("success") and r.get("content"):
                if best is None or len(r["content"]) > len(best["content"]):
                    best = r

        evaluations = []
        if best and best.get("content"):
            verdict = self.judge.evaluate(task, best["content"])
            evaluations.append({"provider": best["name"], "verdict": str(verdict)})

        duration = (datetime.now() - start).total_seconds()

        return {
            "success": best is not None,
            "providers_tried": providers,
            "results": results,
            "best": best,
            "evaluations": evaluations,
            "duration_s": duration,
        }

    async def orchestrate(self, goal: str) -> dict:
        """Orquestación completa: decompose → execute → synthesize.
        Usa el NexusOrchestrator con descomposición LLM.
        """
        from datetime import datetime
        start = datetime.now()

        if not hasattr(self, 'orchestrator'):
            return {"success": False, "error": "Orchestrator not initialized"}

        try:
            result = await self.orchestrator.orchestrate(goal)

            # Judge evaluation
            if result.synthesis:
                verdict = self.judge.evaluate(goal, result.synthesis)
                judge_result = {"action": verdict.action.value, "feedback": verdict.feedback}
            else:
                judge_result = {"action": "skip", "feedback": "No content to evaluate"}

            return {
                "success": result.success,
                "goal": goal,
                "dag_id": result.dag.id if result.dag else "",
                "tasks": len(result.task_results),
                "completed": sum(1 for r in result.task_results.values() if r["status"] == "completed"),
                "failed": sum(1 for r in result.task_results.values() if r["status"] == "failed"),
                "task_results": result.task_results,
                "synthesis": result.synthesis,
                "judge": judge_result,
                "duration_s": result.duration_s,
            }
        except Exception as e:
            logger.exception("Orchestration failed")
            return {"success": False, "error": str(e), "duration_s": (datetime.now() - start).total_seconds()}

    async def multi_motor_status(self) -> dict:
        """Estado completo del sistema multi-motor."""
        providers = {}
        if hasattr(self, 'provider_registry'):
            providers = await self.provider_registry.health_check()
        orch_status = {}
        if hasattr(self, 'orchestrator'):
            orch_status = self.orchestrator.status()
        return {
            "available": hasattr(self, 'provider_registry'),
            "providers": providers,
            "provider_count": len(providers),
            "orchestrator": orch_status,
        }

    async def execute(self, task: str, gem: str = "auto", context: str = "", images: list = None) -> EngineResult:
        """
        Ejecuta tarea: clasifica -> selecciona herramienta IA -> ejecuta -> aprende
        
        NEXUS es el cerebro. Selecciona la herramienta de IA apropiada y la invoca
        con un prompt específico. Los modelos son stateless, NEXUS mantiene el contexto.
        
        Integraciones:
        - F1: Session Manager (auto-compact context)
        - F5: Token Budget Enforcement
        - F12: Simple Goal Short-Circuit
        """
        start = datetime.now()

        # Auto-descripcion: inyectar identidad en el contexto
        identity_blurb = (
            f"Soy {self.IDENTITY['name']} v{self.IDENTITY['version']}, {self.IDENTITY['role']}.\n"
            f"Tengo {len(self.gemas)} gemas especializadas y "
            f"{len(self.tool_registry.get_all()) if hasattr(self, 'tool_registry') else 0} herramientas registradas.\n"
            f"Arquitectura: {self.IDENTITY['architecture']}.\n"
            f"Proyecto actual: {self.current_project}."
        )
        if context:
            context = f"{identity_blurb}\n\n{context}"
        else:
            context = identity_blurb

        # F1: Learning Loop — detect knowledge gaps before execution
        if hasattr(self, 'learning_loop') and self.learning_loop.has_gap(task):
            try:
                learn_result = await self.learning_loop.learn(task)
                if learn_result.found:
                    logger.info(f"LearningLoop: filled gap with '{learn_result.new_capability}' from {learn_result.source}")
                else:
                    logger.warning(f"LearningLoop: gap detected but no source found for: {task[:80]}")
            except Exception as e:
                logger.warning(f"LearningLoop error: {e}")

        # F12: Simple Goal Short-Circuit
        goal_analysis = self.goal_detector.analyze(task)
        if goal_analysis.bypass_coordinator and gem == "auto":
            gem = goal_analysis.suggested_gem
            logger.info(f"Goal short-circuit: bypassing coordinator (reason: {goal_analysis.reason})")

        # F1: Get/create session
        session = self.sessions.get_session()

        # F5: Check token budget before execution
        if not self.token_budget.is_within_budget():
            return EngineResult(
                success=False,
                data={"error": "Token budget exceeded", "budget": self.token_budget.get_status()},
                engine="token_budget",
                duration=0,
            )

        # Hooks: PRE_EXECUTE
        hook_result = await self.hooks.run_hooks(HookPhase.PRE_EXECUTE, {
            "task": task,
            "token_budget": self.token_budget,
        })
        if not hook_result.allow:
            return EngineResult(
                success=False,
                data={"error": hook_result.message},
                engine="hooks",
                duration=0,
            )
        if hook_result.modified_input:
            task = hook_result.modified_input.get("task", task)
            context = hook_result.modified_input.get("context", context)

        # 1. Clasificar
        classification = await self.classify_task(task)
        if gem != "auto":
            classification.selected_gems = [gem]
        
        logger.info(f"Task classified: gems={classification.selected_gems}, engines={classification.selected_engines}")

        # 2. Ejecutar con herramienta de IA (NEXUS es el cerebro, IA es la herramienta)
        primary_gem = classification.selected_gems[0] if classification.selected_gems else "director"
        
        # MCP Client Bridge: Check if task is an MCP tool call
        if task.startswith("mcp__"):
            parts = task.split("__", 2)
            if len(parts) == 3:
                _, server, tool = parts
                # Extract arguments from context
                mcp_args = {}
                if context:
                    try:
                        mcp_args = json.loads(context)
                    except json.JSONDecodeError:
                        mcp_args = {"query": context}
                mcp_result = await self.mcp_client.call_tool(f"mcp__{server}__{tool}", mcp_args)
                return EngineResult(
                    success="error" not in mcp_result,
                    data=mcp_result,
                    engine="mcp_client",
                    duration=(datetime.now() - start).total_seconds(),
                )
        
        # Intentar ejecutar via AgentRunner (nuevo sistema de proveedores)
        provider = self.provider_registry.get("gema-con-fallback")
        ai_result = None
        if provider:
            try:
                task_prompt = task
                if context:
                    task_prompt = f"Context:\n{context}\n\nTask: {task}"
                tool_schemas = self.tool_caller.get_tool_schemas() if hasattr(self, 'tool_caller') else []
                runner = AgentRunner(provider, tool_executor=self._multi_motor_tool_executor)
                spec = AgentRunSpec(
                    messages=[LLMMessage(role="user", content=task_prompt)],
                    tools_definitions=tool_schemas,
                    max_iterations=5,
                )
                runner_result = await runner.run(spec)
                if runner_result.stop_reason != "error":
                    total_tokens = runner_result.usage.get("prompt_tokens", 0) + runner_result.usage.get("completion_tokens", 0)
                    ai_result = {
                        "success": True,
                        "content": runner_result.content or "",
                        "tool": primary_gem,
                        "model": provider.model,
                        "tokens_used": total_tokens,
                        "duration_ms": 0,
                        "tools_used": runner_result.tools_used,
                    }
            except Exception as e:
                logger.exception("AgentRunner failed, falling back")

        # Fallback: GemaHost + quick_response
        if ai_result is None:
            gema_result = await self.gema_host.execute_gema(
                primary_gem,
                "execute_task",
                {"task": task, "context": context},
            )
            if "error" not in gema_result or "note" not in gema_result:
                ai_result = {
                    "success": True,
                    "content": gema_result.get("content", gema_result.get("response", "")),
                    "tool": primary_gem,
                    "model": self.gemas.get(primary_gem, GemCapability("", [], "")).model,
                    "tokens_used": gema_result.get("metadata", {}).get("tokens_used", 0),
                    "duration_ms": gema_result.get("metadata", {}).get("execution_ms", 0),
                }
            else:
                try:
                    ai_result = await self.ai_tools.quick_response(
                        task=task, gem=primary_gem, context=context,
                    )
                except Exception as e:
                    ai_result = {"success": False, "error": str(e), "content": ""}
        
        tokens_used = ai_result.get("tokens_used", 0)
        
        # F5: Record token usage
        budget_check = self.token_budget.record_tokens(tokens_used, source=f"gem:{primary_gem}")
        
        # F1: Add to session (atomic — SessionManager._lock is threading.RLock)
        with self.sessions._lock:
            self.sessions.add_message("user", task, session_id=session.id)
            self.sessions.add_message("assistant", ai_result.get("content", ""), tokens=tokens_used, session_id=session.id)
            current_tokens = session.total_tokens

        # F1: Check if session needs compact
        if self.sessions.needs_compact(session.id):
            compact_result = self.sessions.compact_session_trajectory(session.id)
            logger.info(f"Auto-compact (Trajectory Compressor) triggered for session {compact_result.get('session_id')} (status: {compact_result.get('status')})")

        
        result_data = {
            "content": ai_result.get("content", ""),
            "tool_used": ai_result.get("tool", ""),
            "model_used": ai_result.get("model", ""),
            "tokens_used": tokens_used,
            "duration_ms": ai_result.get("duration_ms", 0),
            "classification": {
                "gems": classification.selected_gems,
                "engines": classification.selected_engines,
            },
            "budget": budget_check,
            "session": {
                "id": session.id,
                "tokens": current_tokens,
            },
        }
        
        success = ai_result.get("success", False)

        # 3. Si necesita paralelo, enviar a otros motores
        if classification.can_parallelize and len(classification.selected_engines) > 1:
            try:
                broadcast_results = await asyncio.wait_for(
                    self.connectivity.broadcast(
                        task,
                        engines=classification.selected_engines[1:]
                    ),
                    timeout=30.0
                )
                result_data["parallel"] = {name: r.data for name, r in broadcast_results.items()}
            except asyncio.TimeoutError:
                logger.warning("Broadcast timeout, continuing without parallel results")

        # Sprint 2: Judge evaluation
        if success and result_data.get("content"):
            verdict = self.judge.evaluate(
                task=task,
                result=result_data.get("content", ""),
                tool_results=[{"tool": primary_gem, "status": "success" if success else "error"}],
            )
            result_data["judge"] = {
                "action": verdict.action.value,
                "feedback": verdict.feedback,
                "confidence": verdict.confidence,
                "level": verdict.level,
            }
            if verdict.action.value == "retry":
                logger.info(f"Judge verdict: RETRY - {verdict.feedback}")

        # Sprint 2: Cursor checkpoint
        self.cursor.save_state(
            agent_id=primary_gem,
            iteration=self.execution_log.__len__(),
            task=task[:200],
            outputs={"content": result_data.get("content", "")[:500]},
            status="completed" if success else "failed",
        )

        # 4. Registrar ejecucion
        duration = (datetime.now() - start).total_seconds() * 1000
        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "task": task[:200],
            "gems": classification.selected_gems,
            "engines": classification.selected_engines,
            "success": success,
            "duration_ms": duration,
        })

        # 5. Actualizar stats del gema (thread-safe)
        async with self._stats_lock:
            for gem_name in classification.selected_gems:
                if gem_name in self.gemas:
                    self.gemas[gem_name].execution_count += 1
                    if success:
                        self.gemas[gem_name].success_count += 1
                    self.gemas[gem_name].total_latency_ms += duration

        # Self-model: Record outcome for learning
        judge_quality = 0.0
        if result_data.get("judge"):
            judge_quality = result_data["judge"].get("confidence", 0.0)
        self.self_model.record_outcome(
            task=task,
            gema_used=primary_gem,
            success=success,
            quality=judge_quality if success else 0.0,
            latency_ms=duration,
        )

        # Auto-aprender: si el orchestrator esta disponible, registrar resultado
        if hasattr(self, 'orchestrator') and success and result_data.get("content"):
            await self.hooks.run_hooks(HookPhase.LEARN, {
                "task": task,
                "result": result_data["content"][:500],
                "gem": primary_gem,
            })

        logger.info(f"Task completed in {duration:.0f}ms: {'OK' if success else 'FAILED'}")

        # Hooks: POST_EXECUTE
        await self.hooks.run_hooks(HookPhase.POST_EXECUTE, {
            "task": task,
            "success": success,
            "result": result_data.get("content", "")[:500],
            "files_modified": [],
        })

        # Hooks: SESSION_END + Memory Consolidation
        if success and result_data.get("content"):
            session = self.sessions.get_session()
            if len(session.messages) >= 4:
                consolidation = await self.memory_consolidator.run_pipeline(
                    [m.to_dict() for m in session.messages[-10:]]
                )
                if consolidation.get("status") == "success":
                    logger.info(f"Memory consolidated: {consolidation.get('facts_extracted', 0)} facts")

        # Hooks: ON_COMPACT
        if self.sessions.needs_compact(session.id):
            await self.hooks.run_hooks(HookPhase.ON_COMPACT, {
                "session_id": session.id,
                "tokens": session.total_tokens,
            })
        
        return EngineResult(
            success=success,
            data=result_data,
            engine="ai_tools",
            duration_ms=duration,
        )

    async def get_dynamic_identity(self) -> Dict:
        """
        Identidad auto-consciente del Director.
        Fusiona la identidad estatica con capacidades descubiertas en runtime.
        """
        identity = self.IDENTITY.copy()
        identity["project"] = self.current_project

        # Gemas
        gemas_info = {}
        for name, g in self.gemas.items():
            gemas_info[name] = {
                "model": g.model,
                "tags": g.tags,
                "description": g.description,
                "executions": g.execution_count,
                "success_rate": (g.success_count / g.execution_count * 100) if g.execution_count > 0 else 0,
            }
        identity["gemas"] = {
            "total": len(self.gemas),
            "list": gemas_info,
        }

        # Modelos disponibles
        models = set()
        for g in self.gemas.values():
            if g.model:
                models.add(g.model)
        identity["models"] = {
            "total": len(models),
            "list": sorted(models),
        }

        # Tools del registro unificado
        if hasattr(self, 'tool_registry'):
            summary = self.tool_registry.get_summary()
            identity["tools"] = summary
            identity["tool_description"] = self.tool_registry.get_tool_description_text()

        # Sesiones y ejecuciones
        identity["sessions"] = self.sessions.get_stats() if hasattr(self, 'sessions') else {}
        identity["executions"] = {
            "total": len(self.execution_log),
            "successful": sum(1 for e in self.execution_log if e.get("success")),
        }

        # Self-model: capacidades descubiertas, limites, rendimiento
        if hasattr(self, 'self_model') and self.self_model:
            try:
                sm = self.self_model
                identity["self_model"] = {
                    "capability_map_available": sm.capability_map is not None,
                    "gema_count": len(sm.capability_map.gemas) if sm.capability_map else 0,
                    "performance_profiles": len(sm.performance_profiles),
                    "knowledge_boundaries": [
                        {"type": b.boundary_type, "description": b.description, "severity": b.severity}
                        for b in sm.knowledge_boundaries
                    ],
                    "routing_rules": len(sm.routing_rules),
                }
            except Exception:
                identity["self_model"] = {"error": "self_model not fully initialized"}

        identity["generated_at"] = datetime.now().isoformat()
        return identity

    async def get_capabilities_report(self) -> str:
        """
        Genera un reporte en lenguaje natural de todo lo que el Director puede hacer.
        Ideal para responder "que puedes hacer?" o inyectar como system prompt.
        """
        identity = await self.get_dynamic_identity()
        lines = []
        lines.append(f"Soy {identity['name']} v{identity['version']}.")
        lines.append(identity['role'])
        lines.append(f"Arquitectura: {identity['architecture']}")
        lines.append(f"Nombre interno: DirectorNexus v2.0")
        lines.append("")

        # Gemas
        g = identity.get("gemas", {})
        lines.append(f"Tengo {g.get('total', 0)} gemas especializadas disponibles:")
        for name, info in g.get("list", {}).items():
            rate = info.get("success_rate", 0)
            lines.append(f"  - {name}: {info['description']} ({info['model']}) - {info['executions']} ejecuciones, {rate:.0f}% exito")

        # Modelos
        m = identity.get("models", {})
        lines.append(f"\nModelos de IA disponibles: {', '.join(m.get('list', []))}")

        # Tools
        t = identity.get("tools", {})
        if t:
            lines.append(f"\nHerramientas registradas: {t.get('total', 0)}")
            for cat, info in t.get("categories", {}).items():
                lines.append(f"  - {cat}: {info['count']} herramientas")

        # Ejecuciones
        ex = identity.get("executions", {})
        lines.append(f"\nHe ejecutado {ex.get('total', 0)} tareas ({ex.get('successful', 0)} exitosas)")

        # Limites conocidos
        sm = identity.get("self_model", {})
        boundaries = sm.get("knowledge_boundaries", [])
        if boundaries:
            lines.append("\nLimitaciones conocidas:")
            for b in boundaries[:5]:
                lines.append(f"  [{b['severity']}] {b['description']}")

        return "\n".join(lines)

    async def change_project(self, new_project: str):
        """
        Cambia de proyecto con memoria selectiva.
        El Director NUNCA olvida su identidad ni gemas base.
        """
        old_project = self.current_project

        # Archivar contexto del proyecto actual
        logger.info(f"Archiving project context: {old_project}")

        # Cargar contexto del nuevo proyecto
        logger.info(f"Loading project context: {new_project}")
        self.current_project = new_project

        # El director mantiene su identidad
        logger.info(f"Director identity preserved: {self.identity['name']}")
        logger.info(f"Project changed: {old_project} → {new_project}")

    def get_status(self) -> Dict:
        """Estado completo del Director"""
        status = {
            "identity": self.identity,
            "tool_registry": self.tool_registry.get_summary() if hasattr(self, 'tool_registry') else {},
            "current_project": self.current_project,
            "gemas_count": len(self.gemas),
            "gemas": {name: {
                "execution_count": g.execution_count,
                "success_rate": g.success_count / g.execution_count if g.execution_count > 0 else 0,
            } for name, g in self.gemas.items()},
            "executions": len(self.execution_log),
            "sessions": self.sessions.get_stats(),
            "token_budget": self.token_budget.get_status(),
            "goal_detector": self.goal_detector.get_stats(),
            "dag": self.dag.get_stats(),
            "checkpoints": self.checkpoints.get_stats(),
            "recipes": self.recipes.get_stats(),
            "loop_guard": self.loop_guard.get_stats(),
            "graph_evolution": self.graph_evolution.get_stats(),
            "approval": self.approval.get_stats(),
            "vault": self.vault.get_stats(),
            "risk": self.risk.get_stats(),
            "memory_health": self.memory_health.get_summary(),
            "tool_monitor": self.tool_monitor.get_summary(),
            "collaboration_hall": self.hall.get_stats(),
            "retry": self.retry.get_stats(),
            "live_notes": self.live_notes.get_stats(),
            "gema_host": self.gema_host.get_status(),
            "mcp_client": self.mcp_client.get_status(),
            "llm_gateway": self.llm_gateway.get_stats(),
            "recursive_seed_ai": self.recursive_seed.get_stats(),
            "recursive_improvement": self.recursive_improvement.get_summary(),
            "judge": self.judge.get_stats(),
            "cursor": self.cursor.get_status(),
            "message_bus": self.message_bus.get_stats(),
            "sub_agents": self.sub_agents.get_stats(),
            "mixture_of_agents": self.moa.get_stats(),
            "fts5_search": self.search.get_stats(),
            "skill_curator": self.skills.get_stats(),
            "codegraph": self.codegraph.get_stats(),
            "context_compactor": self.compactor.get_status(),
            "hooks_engine": self.hooks.get_stats(),
            "memory_consolidator": self.memory_consolidator.get_stats(),
            "skill_loader": self.skill_loader.get_stats(),
            "background_workers": self.worker_manager.get_status(),
            "o1_indexing": self.o1_index.get_stats(),
            "graceful_degradation": self.degradation_mgr.get_status(),
            "hybrid_memory": self.hybrid_memory.get_stats(),
            "data_collector": self.data_collector.get_stats(),
            "nexus_trainer": self.nexus_trainer.get_training_report(),
            "self_model": self.self_model.get_status(),
            "model_autopsy": self.model_autopsy.generate_report() if self.model_autopsy.get_capability_map() else "not_scanned",
            "three_loop": self.three_loop.get_full_report(),
        }

    async def run_improvement_iteration(self, sample_size: int = 10, generate_new: bool = True, use_judge: bool = True) -> Dict:
        judge_fn = self._judge_response if use_judge else None
        return await self.recursive_improvement.run_iteration(
            execute_fn=self.llm_gateway_text,
            judge_fn=judge_fn,
            sample_size=sample_size,
            generate_new_examples=generate_new,
        )

    async def run_three_loops(self, sample_size: int = 30) -> Dict:
        """Run all three self-improvement loops."""
        judge_fn = self._judge_response if True else None
        async def exec_fn(task: str) -> str:
            return await self.llm_gateway_text(task)

        result = await self.three_loop.run_all_loops(
            execute_fn=exec_fn,
            judge_fn=judge_fn,
            sample_size=sample_size,
        )
        logger.info(f"Three-Loop complete. State: fast={self.three_loop.state.fast_loop_count}, "
                    f"medium={self.three_loop.state.medium_loop_count}, "
                    f"slow={self.three_loop.state.slow_loop_count}")
        return result

    def _register_teacher_providers(self):
        """Register external teacher models (Claude, FreeQwenApi) from env vars."""
        import os
        from pathlib import Path
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent.parent / ".env")

        claude_key = os.getenv("ANTHROPIC_API_KEY", "")
        claude_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
        if claude_key:
            self.llm_gateway.add_provider(
                "claude", claude_url, api_key=claude_key,
                priority=2, timeout=120.0,
                cost_per_1m_tokens=15.0,
            )
            logger.info("Teacher provider registered: claude")

        qwen_key = os.getenv("QWEN_API_KEY", "")
        if qwen_key:
            self.llm_gateway.add_provider(
                "freeqwen", "http://localhost:3264/v1", api_key=qwen_key,
                priority=3, timeout=60.0,
            )
            logger.info("Teacher provider registered: freeqwen")

        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        if openrouter_key:
            self.llm_gateway.add_provider(
                "openrouter", "https://openrouter.ai/api/v1", api_key=openrouter_key,
                priority=4, timeout=120.0,
                cost_per_1m_tokens=2.0,
            )
            logger.info("Teacher provider registered: openrouter")

    async def _judge_response(self, prompt: str) -> Dict:
        """Judge a response using LLM-as-Judge."""
        try:
            resp = await self.llm_gateway.chat(
                messages=[{"role": "user", "content": prompt}],
                model="qwen2.5-coder:7b",
                temperature=0.1,
            )
            content = resp.content.strip()
            # Strip markdown code fences if present
            if content.startswith("```"):
                lines = content.splitlines()
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else ""
                content = content.strip()
            if content.startswith("{"):
                return json.loads(content)
            logger.warning(f"Judge: could not parse response (started with {content[:30]})")
            return {"score": 0.5, "reasoning": "Could not parse judge response"}
        except Exception as e:
            logger.warning(f"Judge failed: {e}")
            return {"score": 0.5, "reasoning": str(e)}

    async def llm_gateway_text(self, prompt: str) -> str:
        """Execute a text prompt through LLM Gateway (bypasses full Director pipeline)."""
        try:
            resp = await self.llm_gateway.chat(
                messages=[{"role": "user", "content": prompt}],
                model="qwen2.5-coder:7b",
            )
            return resp.content
        except Exception as e:
            logger.warning(f"LLM Gateway text failed: {e}")
            return ""

    async def run_model_autopsy(self, use_judge: bool = True) -> Dict:
        """Run full model autopsy: probe all models on all skill categories."""
        if use_judge:
            from src.core.recursive_seed_ai import JUDGE_PROMPT
            async def autopsy_judge(task: str, response: str) -> float:
                prompt = JUDGE_PROMPT.format(task=task, response=response)
                result = await self._judge_response(prompt)
                return float(result.get("score", 0.5))
            judge_fn = autopsy_judge
        else:
            judge_fn = None

        cm = await self.model_autopsy.full_scan(judge_fn=judge_fn)
        report = self.model_autopsy.generate_report()

        # Distill Recursive Seed using best models
        distill = await self.model_autopsy.distill_recursive_seed(
            rsai=self.recursive_seed,
            judge_fn=judge_fn,
        )
        report["distillation"] = distill

        logger.info(f"Autopsy complete. Best overall: {cm.overall_best_model}")
        return report

    async def distill_from_teachers(self, tasks: List[str], categories: List[str] = None) -> Dict:
        """
        Teacher-Student Distillation: sends tasks to teachers (local qwen, FreeQwen, Claude),
        picks the best response, and saves as training data for the local model.
        """
        import os, httpx
        from pathlib import Path
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent.parent / ".env")

        output_path = Path.home() / ".nexus" / "autopsy" / "teacher_distillation.jsonl"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        examples = []
        teacher_stats = {}

        for i, task in enumerate(tasks):
            cat = categories[i] if categories and i < len(categories) else "general"
            candidates = []

            # 1. Local qwen-coder (baseline)
            try:
                local = await self.llm_gateway_text(task)
                if local and len(local) > 50:
                    candidates.append(("qwen-coder (local)", local, len(local)))
                    teacher_stats.setdefault("qwen-coder", {"ok": 0, "fail": 0})["ok"] += 1
            except Exception:
                teacher_stats.setdefault("qwen-coder", {"ok": 0, "fail": 0})["fail"] += 1

            # 2. FreeQwenApi proxy (corriendo en :3264)
            try:
                async with httpx.AsyncClient(timeout=60) as c:
                    r = await c.post(
                        "http://localhost:3264/v1/chat/completions",
                        json={"model": "qwen3-coder-plus", "messages": [{"role": "user", "content": task}], "max_tokens": 2048},
                        headers={"Authorization": f"Bearer {os.getenv('QWEN_API_KEY', 'sk-free-qwen-proxy')}"},
                    )
                    if r.status_code == 200:
                        content = r.json()["choices"][0]["message"]["content"]
                        candidates.append(("freeqwen (cloud)", content, len(content)))
                        teacher_stats.setdefault("freeqwen", {"ok": 0, "fail": 0})["ok"] += 1
                    else:
                        teacher_stats.setdefault("freeqwen", {"ok": 0, "fail": 0})["fail"] += 1
            except Exception:
                teacher_stats.setdefault("freeqwen", {"ok": 0, "fail": 0})["fail"] += 1

            # 3. Claude via opencode.ai/zen/v1 (OpenAI-compatible)
            try:
                async with httpx.AsyncClient(timeout=120) as c:
                    r = await c.post(
                        "https://opencode.ai/zen/v1/chat/completions",
                        json={
                            "model": "claude-sonnet-4-20250514",
                            "max_tokens": 2048,
                            "messages": [{"role": "user", "content": task}],
                        },
                        headers={"Authorization": f"Bearer {os.getenv('OPENCODE_API_KEY', '')}"},
                    )
                    if r.status_code == 200:
                        content = r.json()["choices"][0]["message"]["content"]
                        candidates.append(("claude (zen)", content, len(content)))
                        teacher_stats.setdefault("claude", {"ok": 0, "fail": 0})["ok"] += 1
                    else:
                        teacher_stats.setdefault("claude", {"ok": 0, "fail": 0})["fail"] += 1
                        logger.warning(f"Claude/Zen returned {r.status_code} for task {i}")
            except Exception as e:
                logger.warning(f"Claude/Zen failed for task {i}: {e}")
                teacher_stats.setdefault("claude", {"ok": 0, "fail": 0})["fail"] += 1

            # Pick the longest response as best
            if candidates:
                candidates.sort(key=lambda x: x[2], reverse=True)
                best_teacher, best_response, _ = candidates[0]
                examples.append({
                    "id": f"teacher_distill_{i}",
                    "category": cat,
                    "instruction": task,
                    "output": best_response,
                    "source_teacher": best_teacher,
                })
                logger.info(f"  Task {i}: teacher={best_teacher} ({len(candidates)} candidates)")

        with open(output_path, "w", encoding="utf-8") as f:
            for ex in examples:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")

        return {"path": str(output_path), "examples": len(examples), "teacher_stats": teacher_stats}

    async def run_peer_learning(self, tasks: List[str] = None, categories: List[str] = None) -> Dict:
        """Ejecuta PeerChat: PC1 y PC2 colaboran y aprenden de cada tarea."""
        default_tasks = [
            "Write a Python function to merge two sorted linked lists",
            "Explain how to implement a RAG system from scratch",
            "Optimize a SQL query with 3 JOINs and a subquery",
            "Design a microservice architecture for real-time chat",
        ]
        tasks = tasks or default_tasks
        if not self.peer_chat.pc1.online and not self.peer_chat.pc2.online:
            await self.peer_chat.ping()
        result = await self.peer_chat.learn_from_best(tasks, categories)
        self.peer_chat.post_report_to_memory(self.hybrid_memory, "PeerChat Auto-Learning Session")
        return result

    async def run_peer_conversation(self, topic: str = None, rounds: int = 2):
        """Inicia una conversacion entre PC1 y PC2 sobre un tema."""
        await self.peer_chat.ping()
        history = await self.peer_chat.peer_conversation(rounds=rounds, topic=topic)
        self.peer_chat.post_report_to_memory(self.hybrid_memory, f"PeerChat: {topic}")
        return history

    async def shutdown(self):
        """Apaga todos los componentes del Director"""
        logger.info("Shutting down DirectorNexus...")
        await self.worker_manager.stop()
        self.gema_host.shutdown()
        await self.message_bus.stop()
        await self.peer_chat.close()
        self.cursor.store.clear_history(older_than_days=7)

        # Persist training job state
        self.nexus_trainer._save_jobs()

        # Persist self-model state (routing rules, knowledge boundaries)
        self.self_model.save_state()

        logger.info("DirectorNexus shut down")
    
    async def start_background_workers(self):
        """Iniciar los 12 background workers"""
        context = {
            "director": self,
            "sessions": self.sessions,
            "token_budget": self.token_budget,
            "hooks": self.hooks,
            "compactor": self.compactor,
            "memory_consolidator": self.memory_consolidator,
            "skill_loader": self.skill_loader,
            "connectivity": self.connectivity,
            "memory_health": self.memory_health,
            "execution_log": self.execution_log,
            "nexus_home": str(Path.home() / ".nexus"),
        }
        await self.worker_manager.start(context)
        logger.info("12 background workers started")
    
    async def run_worker(self, worker_name: str) -> Dict:
        """Ejecutar un worker específico on-demand"""
        context = {
            "director": self,
            "sessions": self.sessions,
            "token_budget": self.token_budget,
            "hooks": self.hooks,
            "compactor": self.compactor,
            "memory_consolidator": self.memory_consolidator,
            "skill_loader": self.skill_loader,
            "connectivity": self.connectivity,
            "memory_health": self.memory_health,
            "execution_log": self.execution_log,
            "nexus_home": str(Path.home() / ".nexus"),
        }
        result = await self.worker_manager.run_on_demand(worker_name, context)
        return result.__dict__

    # ── F1: Director Soberano ────────────────────────────────────

    def _init_sovereign_director(self):
        self.decision_engine = DecisionEngine()
        for name, gema in self.gemas.items():
            if hasattr(gema, 'tags'):
                self.decision_engine.capabilities.register(f"gema-{name}", gema.tags)

        self.command_dispatcher = CommandDispatcher(default_timeout_s=300)
        self.sub_directors = SubDirectorRegistry.create_defaults()
        for sd in self.sub_directors.sub_directors:
            target = f"sub-director-{sd.config.name}"
            self.command_dispatcher.register(target, lambda cmd, sd=sd: self._sub_director_handle(sd, cmd))

        self.external_agents = ExternalAgentRegistry()
        self._register_default_external_agents()

        self.learning_loop = LearningLoop()
        for name, gema in self.gemas.items():
            if hasattr(gema, 'tags'):
                self.learning_loop.register_known(*gema.tags)

        # LLMAdapter — optional LLM enhancement (engine always has final say)
        self.llm_adapter = LLMAdapter(llm_call=self._llm_enhance_call if hasattr(self, 'connectivity') else None)

        logger.info(f"Sovereign Director initialized: {len(self.sub_directors.sub_directors)} sub-directors, "
                     f"{len(self.external_agents.agents)} external agents, LLM adapter: {self.llm_adapter.available}")

    async def _sub_director_handle(self, sd, cmd: Command) -> CommandResult:
        agent_name = sd.select_agent(cmd)
        agent_cmd = Command(
            target=agent_name, action=cmd.action,
            instruction=cmd.instruction, constraints=cmd.constraints,
            priority=cmd.priority, deadline_tokens=cmd.deadline_tokens,
        )
        result = await self.command_dispatcher.dispatch(agent_cmd)
        sd.record_result(result)
        sd.consume_budget(result.tokens_used)
        return result

    def _register_default_external_agents(self):
        defaults = [
            ExternalAgent(name="antigravity", capabilities=["research", "download", "analyze", "repos"],
                         protocol="messageboard", endpoint="antigravity", cost="free"),
            ExternalAgent(name="opencode", capabilities=["code", "refactor", "implement", "fix"],
                         protocol="messageboard", endpoint="opencode", cost="free"),
            ExternalAgent(name="director-llm", capabilities=["reasoning", "analysis", "code", "research"],
                         protocol="http", endpoint="http://localhost:9000/api/chat", cost="free"),
            ExternalAgent(name="claude-code", capabilities=["code", "refactor", "debug", "test", "architect"],
                         protocol="cli", endpoint="claude", cost="token-based", max_concurrent=1),
            ExternalAgent(name="aider", capabilities=["code", "refactor", "git"],
                         protocol="cli", endpoint="aider", cost="free"),
            ExternalAgent(name="agent-zero", capabilities=["code", "research", "browser", "terminal"],
                         protocol="http", endpoint="http://localhost:50080", cost="free"),
            ExternalAgent(name="hermes", capabilities=["messaging", "telegram", "discord", "slack"],
                         protocol="mcp", endpoint="hermes", cost="free"),
            ExternalAgent(name="pc2-ollama", capabilities=["code", "reasoning", "gpu"],
                         protocol="http", endpoint="http://192.168.1.50:11434/api/chat", cost="free"),
            ExternalAgent(name="n8n", capabilities=["workflow", "automation", "webhook"],
                         protocol="http", endpoint="http://localhost:5678", cost="free"),
        ]
        for agent in defaults:
            self.external_agents.register(agent)

    # ── F2: Memory Hardening ────────────────────────────────────

    def _init_memory_hardening(self):
        self.memory_triage = MemoryTriage()
        self.pointer_store = PointerStore()
        self.dream_consolidator = DreamConsolidator(config=DreamConfig(
            snapshot_dir=str(Path(self._project_root) / ".nexus" / "snapshots"),
        ))
        self.perplexity_scorer = PerplexityScorer()

        if hasattr(self, 'hierarchical_memory'):
            for item in self.hierarchical_memory._items:
                self.memory_triage.register_known(item.content)

        logger.info("Memory Hardening initialized: triage, pointers, dream consolidation, perplexity")

    # ── F3: Protocol Stack ──────────────────────────────────────

    def _init_protocol_stack(self):
        self.acp_router = ACPRouter()
        self.a2a_server = A2AServer(executor=self._a2a_execute)
        self.protocol_router = ProtocolRouter()

        self.protocol_router.register_protocol(Protocol.ACP, self.acp_router)
        self.protocol_router.register_protocol(Protocol.A2A, self.a2a_server)

        if hasattr(self, 'external_agents'):
            for agent in self.external_agents.agents:
                proto = Protocol.ACP if agent.protocol == "messageboard" else \
                        Protocol.HTTP if agent.protocol == "http" else \
                        Protocol.MCP if agent.protocol == "mcp" else \
                        Protocol.CLI
                self.protocol_router.discovery.register(ServiceEntry(
                    name=agent.name, protocol=proto, endpoint=agent.endpoint,
                    capabilities=agent.capabilities,
                ))

        logger.info(f"Protocol Stack initialized: {len(self.protocol_router.discovery.services)} services, "
                     f"{len(self.acp_router.agents)} ACP agents")

    async def _a2a_execute(self, task: str) -> dict:
        """Executor for A2A server — delegates to sovereign_execute."""
        if hasattr(self, 'sovereign_execute'):
            return await self.sovereign_execute(task)
        return {"error": "Sovereign execute not available"}

    # ── F4: Skills Marketplace ──────────────────────────────────

    def _init_skill_marketplace(self):
        self.skill_registry = SkillRegistry()

    # ── F6: Code Absorption ─────────────────────────────────────

    def _init_code_absorption(self):
        self.code_absorber = CodeAbsorber(brain_store=self._absorb_to_brain)

    def _absorb_to_brain(self, content: str) -> None:
        if hasattr(self, 'hierarchical_memory'):
            self.hierarchical_memory.store(content, tags=["absorbed"], source="code-absorber")

    # ── F7: Production Hardening ─────────────────────────────────

    def _init_production_hardening(self):
        self.health_checker = HealthChecker()
        self.token_monitor = TokenMonitor()
        # Default circuit breakers for key agents
        for agent in ["director", "code", "scholar", "analyst", "engineer"]:
            self.health_checker.add_breaker(CircuitBreaker(name=agent, failure_threshold=5, recovery_timeout_s=30.0))
        # Default token budgets
        for agent in self.gemas:
            name = agent if isinstance(agent, str) else agent.get("name", "unknown")
            self.token_monitor.set_budget(name, 500_000)

    async def _llm_enhance_call(self, prompt: str) -> str:
        """LLM call for LLMAdapter — uses connectivity layer."""
        try:
            result = await self.connectivity.execute(
                prompt=prompt, engine="ollama", model="gemma4:latest",
            )
            return result.data.get("response", "") if result.success else ""
        except Exception as e:
            logger.warning(f"LLM enhance call failed: {e}")
            return ""

    async def sovereign_execute(self, task: str) -> dict:
        # 1. Learning check
        if self.learning_loop.has_gap(task):
            learn_result = await self.learning_loop.learn(task)
            if not learn_result.found:
                logger.warning(f"Knowledge gap detected, no learning source found for: {task[:80]}")

        # 2. Decompose (deterministic)
        commands = self.decision_engine.decompose(task)

        # 2b. Optional LLM enhancement (engine has final say)
        if self.llm_adapter.available:
            commands = await self.llm_adapter.enhance_decomposition(task, commands)

        # 3. Dispatch
        results = await self.command_dispatcher.dispatch_batch(commands, max_parallel=3)

        # 4. Evaluate
        verdicts = []
        for cmd, result in zip(commands, results):
            verdict = self.decision_engine.evaluate(
                output=result.output, exit_code=0 if result.status == CommandStatus.COMPLETED else 1,
                error=result.error,
            )
            # Optional LLM second opinion
            if self.llm_adapter.available:
                verdict = await self.llm_adapter.judge(result.output, task, verdict)
            verdicts.append(verdict)

        # 5. Synthesize
        success = all(v.passed for v in verdicts)
        summary = await self.llm_adapter.synthesize(
            [r.to_dict() for r in results], task
        ) if self.llm_adapter.available else f"{'OK' if success else 'FAILED'}: {len(commands)} commands"

        return {
            "task": task,
            "success": success,
            "commands": len(commands),
            "summary": summary,
            "results": [r.to_dict() for r in results],
            "verdicts": [{"passed": v.passed, "reason": v.reason} for v in verdicts],
        }
