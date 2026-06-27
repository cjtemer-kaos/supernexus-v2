"""Core Service — init core components on DirectorNexus."""
from __future__ import annotations
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class CoreService:

    @staticmethod
    def init_core(director):
        from src.core.connectivity import ConnectivityLayer
        from src.core.ai_tools import AIToolsRegistry
        from src.core.session_manager import SessionManager
        from src.core.token_budget import TokenBudget
        from src.core.llm_gateway import LLMGateway

        director.connectivity = ConnectivityLayer()
        director.ai_tools = AIToolsRegistry()
        director.gemas = {}
        director.sessions = SessionManager()
        director.token_budget = TokenBudget()
        director._cached_stable_prompt = None
        soul_path = Path(director._project_root) / "data" / "identity" / "SOUL.md"
        if soul_path.exists():
            director._cached_stable_prompt = soul_path.read_text(encoding="utf-8")

        director.llm_gateway = LLMGateway()
        _ollama_url2 = os.environ.get("OLLAMA_HOST", os.environ.get("OLLAMA_URL", "http://localhost:11434"))
        if _ollama_url2 and not _ollama_url2.startswith("http://") and not _ollama_url2.startswith("https://"):
            _ollama_url2 = "http://" + _ollama_url2
        director.llm_gateway.add_provider("ollama", _ollama_url2, priority=0)
        remote_ip = os.environ.get("SUPER_NEXUS_REMOTE_NODE_IP", "")
        if remote_ip:
            director.llm_gateway.add_provider("remote", f"http://{remote_ip}:11434", priority=1)
        _zen_key = os.environ.get("OPENCODE_API_KEY", "")
        if _zen_key:
            director.llm_gateway.add_provider("zen", "https://opencode.ai/zen/v1",
                                               api_key=_zen_key, priority=2,
                                               models=["deepseek-v4-flash-free", "nemotron-3-super-free"])
