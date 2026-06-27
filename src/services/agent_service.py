"""Agent Service — wraps GemaHost, SubAgents, MixtureOfAgents, AgentLoop, Judge."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GemCapability:
    name: str
    tags: List[str]
    description: str
    model: str = ""
    execution_count: int = 0
    success_count: int = 0
    total_latency_ms: float = 0.0


from src.core.gema_host import GemaHost
from src.core.judge_pipeline import JudgePipeline
from src.core.cursor_checkpoint import CursorCheckpoint
from src.core.message_bus import MessageBus
from src.core.realtime_hub import RealtimeHub
from src.core.sub_agent_spawner import SubAgentSpawner
from src.core.mixture_of_agents import MixtureOfAgents
from src.core.agent_loop import AgentLoop
from src.core.doctor import Doctor
from src.core.tool_monitor import ToolMonitor
from src.core.collaboration_hall import CollaborationHall
from src.core.live_notes import LiveNotes
from src.core.background_review import BackgroundReviewDaemon
from src.core.background_workers import BackgroundWorkerManager
from src.core.autopilot_service import AutopilotService
from src.core.graceful_degradation import GracefulDegradationManager

logger = logging.getLogger(__name__)


def _init_mcp_fallbacks_inline(director):
    import json as _json
    from src.bridges import mcp_bridge_server as _mbs
    async def fb_add(args): return _json.loads(await _mbs.add_observation(content=args.get("content",""), category=args.get("category","general"), project=args.get("project","supernexus-v2"), agent=args.get("agent","fallback"), metadata=args.get("metadata","{}"), topic_key=args.get("topic_key",""), dedupe_window_h=int(args.get("dedupe_window_h",24))))
    async def fb_search(args): return _json.loads(await _mbs.search_observations(query=args.get("query",""), category=args.get("category",""), project=args.get("project",""), limit=int(args.get("limit",10))))
    async def fb_get(args): return _json.loads(await _mbs.get_observation(int(args.get("obs_id",0))))
    for srv in ("nexus-sovereign","memory"):
        director.mcp_client.register_fallback(srv,"add_observation",fb_add)
        director.mcp_client.register_fallback(srv,"search_observations",fb_search)
        director.mcp_client.register_fallback(srv,"get_observation",fb_get)
    from src.core.web_researcher import WebResearcher
    director.web_researcher = WebResearcher(mcp_client=director.mcp_client)


def _scan_ollama_manifests() -> set:
    """Scan Ollama manifests directory for all available model names."""
    import os
    base = Path(os.environ.get("USERPROFILE", "")) / ".ollama" / "models" / "manifests" / "registry.ollama.ai" / "library"
    if not base.exists():
        return set()
    models = set()
    for model_dir in base.iterdir():
        if model_dir.is_dir():
            for tag_file in model_dir.iterdir():
                name = f"{model_dir.name}:{tag_file.name}"
                models.add(name.replace(":latest", ""))
    return models


def _detect_available_models():
    import json
    import urllib.request
    available = set()
    try:
        from src.core.provider_discovery import get_discovered_models
        cached = get_discovered_models()
        if cached: available.update(m.id for m in cached)
    except Exception: pass
    if not available:
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
                available.update(m["name"].replace(":latest", "") for m in data.get("models", []))
        except Exception: pass
    manifest_models = _scan_ollama_manifests()
    available.update(manifest_models)
    import os
    CLOUD = {"ANTHROPIC_API_KEY": "cloud-claude", "OPENAI_API_KEY": "cloud-openai",
             "GROQ_API_KEY": "cloud-groq", "GEMINI_API_KEY": "cloud-gemini"}
    for env_var, provider_name in CLOUD.items():
        if os.environ.get(env_var): available.add(provider_name)
    return available


def _resolve_best_model(preferred: str, available: set) -> str:
    MODEL_FALLBACKS = {
        "deepseek-v4-flash-free": ["deepseek-v4-flask-free", "cloud-zen", "qwen2.5-coder:7b", "deepseek-r1:8b", "nemotron-3-nano:4b"],
        "qwen2.5-coder:7b": ["deepseek-v4-flash-free", "qwen2.5-coder:7b", "deepseek-r1:8b", "nemotron-3-nano:4b", "qwen2.5:0.5b"],
        "deepseek-r1:8b": ["deepseek-v4-flash-free", "deepseek-r1:8b", "qwen2.5-coder:7b", "nemotron-3-nano:4b"],
        "gemma4:latest": ["deepseek-v4-flash-free", "gemma4:latest", "qwen2.5-coder:7b", "deepseek-r1:8b"],
        "qwen2.5vl:7b": ["qwen2.5vl:7b", "qwen2.5-coder:7b"],
        "nemotron-3-nano:4b": ["deepseek-v4-flash-free", "nemotron-3-nano:4b", "nemotron-3-nano:4b", "qwen2.5:0.5b", "qwen2.5-coder:7b"],
        "qwen2.5:0.5b": ["deepseek-v4-flash-free", "qwen2.5:0.5b", "nemotron-3-nano:4b", "qwen2.5-coder:7b"],
    }
    for m in MODEL_FALLBACKS.get(preferred, [preferred]):
        if m in available: return m
    return preferred


@dataclass
class AgentService:
    project_root: str = ""
    llm_executor: Optional[Callable] = None
    execute_fn: Optional[Callable] = None
    agent_loop_llm: Optional[Callable] = None
    ai_tools: Any = None
    mcp_client: Any = None
    hybrid_memory: Any = None
    memory_consolidator: Any = None
    compactor: Any = None
    skill_loader: Any = None

    gema_host: Optional[GemaHost] = None
    judge: Optional[JudgePipeline] = None
    cursor: Optional[CursorCheckpoint] = None
    message_bus: Optional[MessageBus] = None
    realtime_hub: Optional[RealtimeHub] = None
    sub_agents: Optional[SubAgentSpawner] = None
    moa: Optional[MixtureOfAgents] = None
    agent_loop: Optional[AgentLoop] = None
    doctor: Optional[Doctor] = None
    tool_monitor: Optional[ToolMonitor] = None
    hall: Optional[CollaborationHall] = None
    live_notes: Optional[LiveNotes] = None
    review_daemon: Optional[BackgroundReviewDaemon] = None
    worker_manager: Optional[BackgroundWorkerManager] = None
    autopilot: Optional[AutopilotService] = None
    degradation_mgr: Optional[GracefulDegradationManager] = None

    _initialized: bool = field(default=False, init=False)

    async def initialize(self) -> None:
        if self._initialized:
            return
        if self.gema_host is None:
            self.gema_host = GemaHost(project_root=self.project_root)
            self.gema_host.initialize()
            self.gema_host.start_health_checks(interval=30)

        if self.llm_executor is not None:
            if self.judge is None:
                self.judge = JudgePipeline(llm_executor=self.llm_executor)
            if self.moa is None:
                self.moa = MixtureOfAgents(executor=self.llm_executor)

        if self.cursor is None:
            self.cursor = CursorCheckpoint()
        if self.message_bus is None:
            self.message_bus = MessageBus()
        if self.realtime_hub is None:
            self.realtime_hub = RealtimeHub(message_bus=self.message_bus)
        if self.sub_agents is None and self.execute_fn is not None:
            self.sub_agents = SubAgentSpawner(executor=self.execute_fn)
        if self.agent_loop is None and self.agent_loop_llm is not None:
            self.agent_loop = AgentLoop(
                llm_fn=self.agent_loop_llm,
                max_iterations=10,
                workdir=self.project_root,
            )
        if self.doctor is None:
            self.doctor = Doctor()
        if self.tool_monitor is None:
            self.tool_monitor = ToolMonitor()
            if self.ai_tools is not None:
                self.ai_tools.set_tool_monitor(self.tool_monitor)
        if self.hall is None:
            self.hall = CollaborationHall()
        if self.live_notes is None:
            self.live_notes = LiveNotes()
        if self.review_daemon is None:
            self.review_daemon = BackgroundReviewDaemon()
        if self.worker_manager is None:
            self.worker_manager = BackgroundWorkerManager()
            self.worker_manager.register_all()
        if self.autopilot is None:
            self.autopilot = AutopilotService(
                worker_manager=self.worker_manager,
                realtime_hub=self.realtime_hub,
            )
        if self.degradation_mgr is None:
            self.degradation_mgr = GracefulDegradationManager()
            self._setup_degradation_fallbacks()

        self._initialized = True
        logger.info("AgentService initialized")

    def _setup_degradation_fallbacks(self) -> None:
        mgr = self.degradation_mgr
        if self.memory_consolidator is not None and hasattr(self.memory_consolidator, "consolidate"):
            mgr.register_component(
                name="memory_consolidator",
                primary_fn=self.memory_consolidator.consolidate,
                fallback_fn=lambda x: {"status": "degraded", "action": "memory_consolidation_skipped", "data": x},
                health_check_fn=lambda: True,
            )
        if self.compactor is not None and hasattr(self.compactor, "compact"):
            mgr.register_component(
                name="context_compactor",
                primary_fn=self.compactor.compact if hasattr(self.compactor, "compact") else lambda x: x,
                fallback_fn=lambda x: x,
            )
        if self.skill_loader is not None and hasattr(self.skill_loader, "load_skill"):
            mgr.register_component(
                name="skill_loader",
                primary_fn=self.skill_loader.load_skill,
                fallback_fn=lambda x: f"# Skill {x} unavailable (degraded mode)",
            )
        if self.gema_host is not None:
            mgr.register_component(
                name="gema_host",
                primary_fn=lambda g, t, c: self.gema_host.execute_gema(g, t, c),
                fallback_fn=lambda g, t, c: {"error": "gema_host_unavailable", "note": "fallback_to_ai_tools"},
            )
        logger.info(f"Graceful degradation configured with {len(mgr.components)} components")

    @staticmethod
    def load_gemas(gemas_dict: dict) -> int:
        """Load gemas into given dict. Returns count loaded."""
        available = _detect_available_models()
        try:
            from src.plugins.manifest import load_gemas as _load_plugins
            plugins = _load_plugins()
            if plugins:
                for name, plugin in plugins.items():
                    model = _resolve_best_model(plugin.preferred_model, available)
                    gemas_dict[name] = GemCapability(
                        name=name, tags=plugin.tags, description=plugin.description, model=model)
                return len(plugins)
        except Exception: pass

        gemas_data = [
            ("ayuda", ["help", "ayuda", "tutorial", "guide", "onboarding", "capacidades"], "Guia reactiva del sistema", "deepseek-v4-flash-free"),
            ("director", ["leadership", "orchestration", "planning"], "Orquestacion y liderazgo", "nexus-director-v6"),
            ("code", ["programming", "code-review", "refactoring", "handoff", "delegation", "compile", "sandbox"], "Programacion", "deepseek-v4-flash-free"),
            ("scholar", ["research", "learning", "web-search"], "Investigacion y aprendizaje", "deepseek-v4-flash-free"),
            ("architect", ["architecture", "design", "infrastructure"], "Diseno de sistemas", "deepseek-v4-flash-free"),
            ("creative", ["creative", "writing", "content"], "Contenido creativo", "deepseek-v4-flash-free"),
            ("sage", ["memory", "persistence", "learning"], "Persistencia y memoria", "deepseek-v4-flash-free"),
            ("analyst", ["analysis", "data", "metrics"], "Analisis de datos", "deepseek-v4-flash-free"),
            ("debugger", ["debugging", "troubleshooting", "error-handling"], "Debugging", "deepseek-v4-flash-free"),
            ("optimizer", ["optimization", "performance", "tuning"], "Optimizacion", "deepseek-v4-flash-free"),
            ("tester", ["testing", "qa", "validation"], "Testing y QA", "deepseek-v4-flash-free"),
            ("security", ["security", "compliance", "protection"], "Seguridad", "deepseek-v4-flash-free"),
            ("devops", ["devops", "deployment", "infrastructure"], "DevOps", "deepseek-v4-flash-free"),
            ("trainer", ["training", "education", "teaching"], "Entrenamiento", "deepseek-v4-flash-free"),
            ("biblioteca", ["organization", "knowledge", "indexing"], "Organizacion de conocimiento", "deepseek-v4-flash-free"),
            ("vision", ["screenshot", "screen-control", "pc-control", "mouse", "keyboard"], "Control visual de PC", "qwen2.5vl:7b"),
            ("opencode", ["opencode", "cli-agent", "code-execution", "engineering", "tools", "scripting", "bash", "shell", "powershell"], "Agente CLI y scripting", "deepseek-v4-flash-free"),
            ("design", ["design", "ui", "ux", "multimedia", "video", "scene"], "Diseno multimedia", "deepseek-v4-flash-free"),
            ("music", ["music", "audio", "sound", "voice", "tts", "stt"], "Audio, voz y musica", "deepseek-v4-flash-free"),
            ("prompter", ["prompt", "token", "optimization", "compression"], "Optimizacion de prompts", "deepseek-v4-flash-free"),
            ("producer", ["schedule", "task", "automation", "rcon", "server", "cron", "backup"], "Automatizacion y cron", "deepseek-v4-flash-free"),
            ("engineer", ["engineering", "tools", "automation", "scripting", "cli", "build"], "Ingenieria de herramientas", "deepseek-v4-flash-free"),
            ("codex", ["codex", "delegation", "compilation", "sandbox"], "Delegacion de codigo", "deepseek-v4-flash-free"),
            ("verifier", ["verification", "qa", "validation", "review", "quality", "audit"], "Verificacion adversarial", "deepseek-v4-flash-free"),
        ]
        for name, tags, desc, preferred in gemas_data:
            model = _resolve_best_model(preferred, available)
            gemas_dict[name] = GemCapability(name=name, tags=tags, description=desc, model=model)
        return len(gemas_data)

    async def shutdown(self) -> None:
        pass

    def healthcheck(self) -> bool:
        return self.gema_host is not None

    @staticmethod
    def init_agents(director):
        director.gema_host = GemaHost(project_root=director._project_root)
        director.gema_host.initialize()
        director.gema_host.start_health_checks(interval=30)

        director.judge = JudgePipeline(llm_executor=director.ai_tools.quick_response)
        director.cursor = CursorCheckpoint()
        director.message_bus = MessageBus()
        director.realtime_hub = RealtimeHub(message_bus=director.message_bus)
        director.sub_agents = SubAgentSpawner(executor=director.execute)
        director.moa = MixtureOfAgents(executor=director.ai_tools.quick_response)
        director.agent_loop = AgentLoop(
            llm_fn=director._agent_loop_llm, max_iterations=10, workdir=director._project_root,
        )
        director.doctor = Doctor()
        director.tool_monitor = ToolMonitor()
        director.ai_tools.set_tool_monitor(director.tool_monitor)
        director.hall = CollaborationHall()
        director.live_notes = LiveNotes()
        director.review_daemon = BackgroundReviewDaemon()

        from src.core.mcp_client_bridge import MCPClientBridge
        director.mcp_client = MCPClientBridge(workdir=director._project_root)
        director.mcp_client.register_builtin_servers()
        try:
            extra = director.mcp_client.autodiscover()
            if extra:
                logger.info(f"MCP autodiscover added {extra} server(s) from mcp_servers.json")
        except Exception as e:
            logger.warning(f"MCP autodiscover failed (continuing): {e}")
        _init_mcp_fallbacks_inline(director)
