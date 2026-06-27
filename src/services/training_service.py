"""Training Service — init training subsystems on DirectorNexus."""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class TrainingService:

    @staticmethod
    def init_training(director):
        from src.core.recursive_seed_ai import RecursiveSeedAI, RecursiveImprovementLoop
        director.recursive_seed = RecursiveSeedAI()
        director.recursive_improvement = RecursiveImprovementLoop(director.recursive_seed)

        from src.core.model_autopsy import ModelAutopsy
        director.model_autopsy = ModelAutopsy(llm_gateway=director.llm_gateway)

        from src.core.three_loop import ThreeLoopSystem
        director.three_loop = ThreeLoopSystem(
            recursive_seed=director.recursive_seed,
            model_autopsy=director.model_autopsy,
        )

        from src.core.peer_chat import PeerChat
        director.peer_chat = PeerChat()

        from src.core.data_collector import DataCollector
        director.data_collector = DataCollector(min_quality=0.7)

        from src.bridges.remote_node_bridge import RemoteNodeBridge
        director.remote_bridge = RemoteNodeBridge()

        async def _remote_executor(command: str) -> Dict:
            try:
                return await director.remote_bridge.execute_remote(command, timeout=300)
            except Exception as e:
                logger.warning(f"Remote executor failed: {e}")
                return {"success": False, "error": str(e)}

        from src.core.nexus_trainer import NexusTrainer
        director.nexus_trainer = NexusTrainer(execute_on_REMOTE=_remote_executor)

        director.ai_tools.data_collector = director.data_collector
        director.ai_tools.three_loop = director.three_loop

        from src.core.ollama import OllamaClient
        from src.core.self_model import SelfModelEngine
        director.self_model = SelfModelEngine(
            project_root=director._project_root,
            ollama_client=OllamaClient(),
            execution_log=director.execution_log,
            storage_path=Path.home() / ".nexus" / "self_model_state.json",
        )

        from src.brain.training import TrainingBrain
        director.training_brain = TrainingBrain(director)
        director.training_brain.register_teacher_providers()
