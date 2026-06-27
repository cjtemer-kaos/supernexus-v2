"""Orchestration Service — init orchestration components on DirectorNexus."""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


class OrchestrationService:

    @staticmethod
    def init_orchestration(director):
        from src.core.goal_detector import GoalDetector
        from src.core.dag_coordinator import DAGCoordinator
        from src.core.checkpoint import CheckpointStore
        from src.core.recipe_engine import RecipeEngine
        from src.core.loop_guard import LoopGuard
        from src.core.approval_gate import ApprovalGate
        from src.core.risk_assessor import RiskAssessor
        from src.core.retry_manager import RetryManager
        from src.core.tool_guardrails import ToolCallGuardrailController
        from src.core.custom_commands import CustomCommandManager
        from src.core.o1_indexing import O1IndexManager
        from src.core.graceful_degradation import GracefulDegradationManager

        director.goal_detector = GoalDetector()
        director.dag = DAGCoordinator()
        director.checkpoints = CheckpointStore()
        director.recipes = RecipeEngine()
        director.loop_guard = LoopGuard(max_history=50, exact_threshold=3, semantic_threshold=0.8)
        director.approval = ApprovalGate()
        director.risk = RiskAssessor()
        director.retry = RetryManager()
        director.tool_guardrails = ToolCallGuardrailController()
        director.custom_commands = CustomCommandManager()
        director.o1_index = O1IndexManager()
        director.degradation_mgr = GracefulDegradationManager()
