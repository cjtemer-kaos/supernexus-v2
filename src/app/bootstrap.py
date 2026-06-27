"""Build a NexusApp with all 5 services registered in dependency order.

Pattern from opencode-go App-as-Container. Each service receives only its
dependencies (constructor injection), no globals, no nested init cascades.

Usage:
    from src.app.bootstrap import build_app
    app = await build_app("default")
    director = DirectorNexus(app=app)
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, Any

from src.app.registry import NexusApp
from src.services.memory_service import MemoryService
from src.services.tool_service import ToolService
from src.services.agent_service import AgentService
from src.services.routing_service import RoutingService

logger = logging.getLogger(__name__)


def _project_root() -> str:
    return str(Path(__file__).resolve().parent.parent.parent)


async def build_app(project: str = "default", config: Dict[str, Any] | None = None) -> NexusApp:
    if config is None:
        config = {}
    root = _project_root()

    app = NexusApp(project=project, config=config)

    # Memory — no dependencies on other services
    memory = MemoryService(project_root=root, recover_session_cb=None)
    app.register("memory", memory)

    # Tools — needs ai_tools reference (set later via wiring)
    tools = ToolService(project_root=root)
    app.register("tools", tools)

    # Agents — needs gema_host (auto-created)
    agents = AgentService(project_root=root)
    app.register("agents", agents)

    # Routing — needs gemas + o1_index (set later via wiring)
    routing = RoutingService()
    app.register("routing", routing)

    results = await app.initialize_all()
    failed = [k for k, v in results.items() if not v]
    if failed:
        logger.warning(f"bootstrap: {len(failed)} services failed init: {failed}")

    logger.info(f"NexusApp built: {project} ({len(app._services)} services)")
    return app
