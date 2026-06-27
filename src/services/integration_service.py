"""Integration Service — init integrations on DirectorNexus."""
from __future__ import annotations
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class IntegrationService:

    @staticmethod
    def init_integrations(director):
        from src.integrations.codegraph_integration import CodeGraphIntegration

        from src.core.comfyui_gateway import ComfyUIGateway
        from src.core.context_compactor import ContextCompactor
        from src.core.hooks_engine import HooksEngine
        from src.core.error_compactor import ErrorCompactor
        from src.core.skill_curator import SkillCurator
        from src.skills.skill_loader import ProgressiveSkillLoader
        from src.core.background_workers import BackgroundWorkerManager
        from src.core.autopilot_service import AutopilotService

        director.codegraph = CodeGraphIntegration(project_root=director._project_root)
        director.comfyui = ComfyUIGateway()
        director.compactor = ContextCompactor()
        director.hooks = HooksEngine()
        director.hooks.register_builtin_hooks(workdir=Path(director._project_root))
        director.error_compactor = ErrorCompactor()
        director.skills = SkillCurator()
        skills_base = Path(director._project_root) / "src" / "skills" / "hub"
        director.skill_loader = ProgressiveSkillLoader(skills_base)
        director.worker_manager = BackgroundWorkerManager()
        director.worker_manager.register_all()
        director.autopilot = AutopilotService(
            worker_manager=director.worker_manager,
            realtime_hub=getattr(director, 'realtime_hub', None),
        )
