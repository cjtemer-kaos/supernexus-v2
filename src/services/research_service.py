import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Callable, Dict, List, Optional

from src.research.handler import ResearchHandler

logger = logging.getLogger(__name__)

_raw_ollama = os.environ.get("OLLAMA_HOST", os.environ.get("OLLAMA_URL", "http://localhost:11434"))
if not _raw_ollama.startswith("http"):
    _raw_ollama = "http://" + _raw_ollama
OLLAMA_URL = _raw_ollama.rstrip("/")
DEFAULT_MODEL = os.environ.get("NEXUS_RESEARCH_MODEL", "qwen2.5-coder:7b")
RESEARCH_DATA_DIR = Path(os.environ.get("NEXUS_HOME", Path.home() / ".nexus")) / "research"


class ResearchService:

    def __init__(self, web_researcher=None):
        self._handler = ResearchHandler(data_dir=RESEARCH_DATA_DIR)
        self._web_researcher = web_researcher
        self._llm_endpoint = OLLAMA_URL
        self._llm_model = DEFAULT_MODEL

    def configure(self, llm_endpoint: str = None, llm_model: str = None, web_researcher=None):
        if llm_endpoint:
            self._llm_endpoint = llm_endpoint
        if llm_model:
            self._llm_model = llm_model
        if web_researcher:
            self._web_researcher = web_researcher

    async def deep_research(
        self,
        query: str,
        max_time: int = 300,
        category: str = None,
        on_progress: Callable = None,
        session_id: str = None,
    ) -> str:
        sid = session_id or f"research_{int(asyncio.get_running_loop().time())}"
        result_future = asyncio.get_running_loop().create_future()

        results_holder = {}

        def _on_complete(sid, result, sources, findings):
            results_holder["result"] = result
            results_holder["sources"] = sources
            results_holder["findings"] = findings
            if not result_future.done():
                result_future.set_result(result)

        self._handler.start_research(
            session_id=sid,
            query=query,
            llm_endpoint=self._llm_endpoint,
            llm_model=self._llm_model,
            max_time=max_time,
            on_complete=_on_complete,
            category=category,
            web_researcher=self._web_researcher,
            owner="nexus",
        )

        try:
            result = await asyncio.wait_for(result_future, timeout=max_time + 60)
            return result
        except asyncio.TimeoutError:
            return f"Research timed out after {max_time + 60}s"
        finally:
            self._handler.clear_result(sid)

    def start_background_research(
        self,
        query: str,
        max_time: int = 300,
        category: str = None,
        on_complete: Callable = None,
        owner: str = "",
    ) -> dict:
        sid = f"research_{int(asyncio.get_running_loop().time())}"
        return self._handler.start_research(
            session_id=sid,
            query=query,
            llm_endpoint=self._llm_endpoint,
            llm_model=self._llm_model,
            max_time=max_time,
            on_complete=on_complete,
            category=category,
            web_researcher=self._web_researcher,
            owner=owner or "nexus",
        )

    def get_status(self, session_id: str) -> Optional[dict]:
        return self._handler.get_status(session_id)

    def get_result(self, session_id: str) -> Optional[str]:
        return self._handler.get_result(session_id)

    def cancel_research(self, session_id: str) -> bool:
        return self._handler.cancel_research(session_id)

    def list_completed(self) -> List[Dict]:
        results = []
        try:
            for p in sorted(RESEARCH_DATA_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    if not data.get("consumed") and data.get("status") == "done":
                        results.append({
                            "session_id": p.stem,
                            "query": data.get("query", ""),
                            "started_at": data.get("started_at", 0),
                            "completed_at": data.get("completed_at", 0),
                        })
                except Exception:
                    continue
        except Exception:
            pass
        return results[:20]
