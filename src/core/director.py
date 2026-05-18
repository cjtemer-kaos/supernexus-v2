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
import logging
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.core.connectivity import ConnectivityLayer, EngineResult
from src.core.ai_tools import AIToolsRegistry
from src.core.session_manager import SessionManager
from src.core.token_budget import TokenBudget
from src.core.goal_detector import GoalDetector
from src.core.dag_coordinator import DAGCoordinator
from src.core.checkpoint import CheckpointStore
from src.core.recipe_engine import RecipeEngine
from src.core.loop_detector import LoopDetector
from src.core.graph_evolution import GraphEvolution
from src.core.approval_gate import ApprovalGate
from src.core.knowledge_vault import KnowledgeVault
from src.core.risk_assessor import RiskAssessor
from src.core.memory_health import MemoryHealthMonitor
from src.core.tool_monitor import ToolMonitor
from src.core.collaboration_hall import CollaborationHall
from src.core.retry_manager import RetryManager
from src.core.live_notes import LiveNotes
from src.core.background_review import BackgroundReviewDaemon
from src.core.tool_guardrails import ToolCallGuardrailController, GuardrailConfig
from src.core.custom_commands import CustomCommandManager
from src.core.doctor import Doctor
from src.core.gema_host import GemaHost
from src.core.judge_pipeline import JudgePipeline
from src.core.cursor_checkpoint import CursorCheckpoint
from src.core.message_bus import MessageBus
from src.core.sub_agent_spawner import SubAgentSpawner
from src.core.mixture_of_agents import MixtureOfAgents
from src.core.fts5_search import FTS5Search
from src.core.skill_curator import SkillCurator
from src.integrations.codegraph_integration import CodeGraphIntegration

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
        "name": "DirectorNexus",
        "version": "2.0",
        "role": "Cerebro central de SuperNEXUS",
        "function": "Coordinar motores, gemas, memoria y herramientas de IA para resolver tareas",
        "architecture": "Brain + Tools (NEXUS es el cerebro, los modelos son herramientas)",
    }

    def __init__(self, project: str = "default"):
        self.identity = self.IDENTITY.copy()
        self.current_project = project
        self.connectivity = ConnectivityLayer()
        self.ai_tools = AIToolsRegistry()
        self.gemas: Dict[str, GemCapability] = {}
        self.execution_log: List[Dict] = []
        self._stats_lock = threading.Lock()

        # F1: Session Manager
        self.sessions = SessionManager()
        # F5: Token Budget
        self.token_budget = TokenBudget()
        # F12: Goal Detector
        self.goal_detector = GoalDetector()
        # F2: DAG Coordinator
        self.dag = DAGCoordinator()
        # F3: Checkpoint Store
        self.checkpoints = CheckpointStore()
        # F8: Recipe Engine
        self.recipes = RecipeEngine()
        # F16: Loop Detector
        self.loop_detector = LoopDetector()
        # F6: Graph Evolution
        self.graph_evolution = GraphEvolution()
        # F7: Approval Gate
        self.approval = ApprovalGate()
        # F9: Knowledge Vault
        self.vault = KnowledgeVault()
        # F11: Risk Assessor
        self.risk = RiskAssessor()
        # F14: Memory Health
        self.memory_health = MemoryHealthMonitor()
        # F17: Tool Monitor
        self.tool_monitor = ToolMonitor()
        # F13: Collaboration Hall
        self.hall = CollaborationHall()
        # F18: Retry Manager
        self.retry = RetryManager()
        # F20: Live Notes
        self.live_notes = LiveNotes()
        # F21: Background Review Daemon (hermes-agent extraction)
        self.review_daemon = BackgroundReviewDaemon()
        # F22: Tool Call Guardrails (hermes-agent extraction)
        self.tool_guardrails = ToolCallGuardrailController()
        # F19: Custom Commands
        self.custom_commands = CustomCommandManager()
        # F15: Doctor
        self.doctor = Doctor()

        # Sprint 0.5: GemaHost (Extension Host multiproceso)
        self.gema_host = GemaHost(project_root=str(Path(__file__).parent.parent.parent))
        self.gema_host.initialize()
        self.gema_host.start_health_checks(interval=30)

        # Sprint 2: Judge Pipeline (evaluacion de calidad 3 niveles)
        self.judge = JudgePipeline(llm_executor=self.ai_tools.quick_response)

        # Sprint 2: Cursor Checkpoint (persistencia de estados)
        self.cursor = CursorCheckpoint()

        # Sprint 3: MessageBus (comunicacion inter-gemas)
        self.message_bus = MessageBus()

        # Sprint 3: Sub-Agent Spawner (delegacion dinamica)
        self.sub_agents = SubAgentSpawner(executor=self.execute)

        # Sprint 3: Mixture of Agents (inferencia paralela)
        self.moa = MixtureOfAgents(executor=self.ai_tools.quick_response)

        # Sprint 4: FTS5 Search (busqueda rapida indexada)
        self.search = FTS5Search()

        # Sprint 4: Skill Curator (gestor de ciclo de vida)
        self.skills = SkillCurator()

        # Sprint 5: CodeGraph (motor semantico AST)
        self.codegraph = CodeGraphIntegration(project_root=str(Path(__file__).parent.parent.parent))

        self._load_gemas()
        logger.info(f"DirectorNexus v2 initialized (project: {project}, architecture: Brain + Tools)")

    def _load_gemas(self):
        """Carga los 22 gemas con sus capacidades"""
        gemas_data = [
            ("director", ["leadership", "orchestration", "planning"], "Orquestacion y liderazgo", "deepseek-r1:8b"),
            ("code", ["programming", "code-review", "refactoring"], "Programacion y desarrollo", "qwen2.5-coder:7b"),
            ("scholar", ["research", "learning", "web-search"], "Investigacion y aprendizaje", "deepseek-r1:8b"),
            ("architect", ["architecture", "design", "infrastructure"], "Diseno de sistemas", "qwen2.5-coder:7b"),
            ("creative", ["creative", "writing", "content"], "Contenido creativo", "qwen2.5-coder:7b"),
            ("sage", ["memory", "persistence", "learning"], "Persistencia y memoria", "deepseek-r1:8b"),
            ("analyst", ["analysis", "data", "metrics"], "Analisis de datos", "nemotron-3-nano:4b"),
            ("engineer", ["engineering", "tools", "optimization"], "Ingenieria y herramientas", "qwen2.5-coder:7b"),
            ("debugger", ["debugging", "troubleshooting", "error-handling"], "Debugging", "deepseek-r1:8b"),
            ("optimizer", ["optimization", "performance", "tuning"], "Optimizacion", "qwen2.5-coder:7b"),
            ("tester", ["testing", "qa", "validation"], "Testing y QA", "qwen2.5-coder:7b"),
            ("security", ["security", "compliance", "protection"], "Seguridad", "deepseek-r1:8b"),
            ("devops", ["devops", "deployment", "infrastructure"], "DevOps", "qwen2.5-coder:7b"),
            ("trainer", ["training", "education", "teaching"], "Entrenamiento", "qwen2.5-coder:7b"),
            ("biblioteca", ["organization", "knowledge", "indexing"], "Organizacion de conocimiento", "deepseek-r1:8b"),
            # Nuevas gemas portadas de NEXUS_MASTER
            ("vision", ["screenshot", "screen-control", "pc-control", "vision", "mouse", "keyboard"], "Control visual de PC con Ollama vision", "qwen2.5vl:2b"),
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

    async def classify_task(self, task: str) -> TaskClassification:
        """
        Clasifica tarea usando routing semantico (OpenSwarm pattern).
        Determina que gema(s) y motor(es) usar.
        """
        task_lower = task.lower()

        # Keyword-based routing (mejorable con LLM semantico)
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
            # Nuevas gemas
            "screenshot": "vision", "screen": "vision", "pc control": "vision", "vision": "vision",
            "mouse": "vision", "keyboard": "vision", "click": "vision",
            "opencode": "opencode", "cli agent": "opencode",
            "codex": "codex", "handoff": "codex", "delegar": "codex",
            "multimedia": "design", "video": "design", "scene": "design", "veo": "design",
            "music": "music", "audio": "music", "voice": "music", "tts": "music", "stt": "music", "habla": "music",
            "prompt": "prompter", "token": "prompter", "compression": "prompter", "optimizar tokens": "prompter",
            "schedule": "producer", "automation": "producer", "rcon": "producer", "rust server": "producer",
            "task": "producer", "scheduler": "producer",
        }

        selected_gems = set()
        for keyword, gem in keywords_to_gem.items():
            if keyword in task_lower:
                selected_gems.add(gem)

        if not selected_gems:
            selected_gems = {"director"}

        # Seleccion de motores segun tipo de tarea
        engines = ["nexus_master"]  # Default
        if any(k in task_lower for k in ["gpu", "heavy", "train", "video", "image"]):
            engines.append("nexus_Remote Node")
        if any(k in task_lower for k in ["research", "web", "search"]):
            engines.append("openclaw")

        return TaskClassification(
            task=task,
            selected_gems=list(selected_gems),
            selected_engines=engines,
            confidence=0.8 if len(selected_gems) > 1 else 0.5,
            can_parallelize=len(engines) > 1,
        )

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

        # 1. Clasificar
        classification = await self.classify_task(task)
        if gem != "auto":
            classification.selected_gems = [gem]
        
        logger.info(f"Task classified: gems={classification.selected_gems}, engines={classification.selected_engines}")

        # 2. Ejecutar con herramienta de IA (NEXUS es el cerebro, IA es la herramienta)
        primary_gem = classification.selected_gems[0] if classification.selected_gems else "director"
        
        # Sprint 0.5: Intentar ejecutar via GemaHost (aislamiento multiproceso)
        gema_result = await self.gema_host.execute_gema(
            primary_gem,
            "execute_task",
            {"task": task, "context": context},
        )
        
        if "error" not in gema_result or "note" not in gema_result:
            # GemaHost ejecuto correctamente
            ai_result = {
                "success": True,
                "content": gema_result.get("content", gema_result.get("response", "")),
                "tool": primary_gem,
                "model": self.gemas.get(primary_gem, GemCapability("", [], "")).model,
                "tokens_used": gema_result.get("metadata", {}).get("tokens_used", 0),
                "duration_ms": gema_result.get("metadata", {}).get("execution_ms", 0),
            }
        else:
            # Fallback al sistema actual si la gema no esta implementada
            try:
                ai_result = await self.ai_tools.quick_response(
                    task=task,
                    gem=primary_gem,
                    context=context,
                )
            except Exception as e:
                ai_result = {"success": False, "error": str(e), "content": ""}
        
        tokens_used = ai_result.get("tokens_used", 0)
        
        # F5: Record token usage
        budget_check = self.token_budget.record_tokens(tokens_used, source=f"gem:{primary_gem}")
        
        # F1: Add to session (atomic token update)
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
            verdict = await self.judge.evaluate(
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
        with self._stats_lock:
            for gem_name in classification.selected_gems:
                if gem_name in self.gemas:
                    self.gemas[gem_name].execution_count += 1
                    if success:
                        self.gemas[gem_name].success_count += 1
                    self.gemas[gem_name].total_latency_ms += duration

        logger.info(f"Task completed in {duration:.0f}ms: {'OK' if success else 'FAILED'}")
        
        return EngineResult(
            success=success,
            data=result_data,
            engine="ai_tools",
            duration=duration,
        )

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
        return {
            "identity": self.identity,
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
            "loop_detector": self.loop_detector.get_stats(),
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
            "judge": self.judge.get_stats(),
            "cursor": self.cursor.get_status(),
            "message_bus": self.message_bus.get_stats(),
            "sub_agents": self.sub_agents.get_stats(),
            "mixture_of_agents": self.moa.get_stats(),
            "fts5_search": self.search.get_stats(),
            "skill_curator": self.skills.get_stats(),
            "codegraph": self.codegraph.get_stats(),
        }

    async def shutdown(self):
        """Apaga todos los componentes del Director"""
        logger.info("Shutting down DirectorNexus...")
        self.gema_host.shutdown()
        await self.message_bus.stop()
        self.cursor.store.clear_history(older_than_days=7)
        logger.info("DirectorNexus shut down")
