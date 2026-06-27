"""Memory Service — wraps memory subsystems + init_memory for DirectorNexus."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Optional, Callable

logger = logging.getLogger(__name__)


@dataclass
class MemoryService:
    project_root: str = ""
    recover_session_cb: Optional[Callable] = None

    graph: Optional = None
    vault: Optional = None
    memory_health: Optional = None
    hybrid_memory: Optional = None
    memory_consolidator: Optional = None
    search: Optional = None
    rag_engine: Optional = None
    hive: Optional = None
    context_recovery: Optional = None

    _initialized: bool = field(default=False, init=False)

    def __post_init__(self):
        from src.core.graph_evolution import GraphEvolution
        from src.core.knowledge_vault import KnowledgeVault
        from src.core.memory_health import MemoryHealthMonitor
        from src.core.hybrid_memory import HybridMemoryBackend
        from src.core.memory_consolidator import MemoryConsolidator
        from src.core.fts5_search import FTS5Search
        from src.core.rag_engine import RAGEngine
        from src.core.nexus_hive import NexusHive
        from src.core.session_context_recovery import SessionContextRecovery

        self.graph = GraphEvolution()
        self.vault = KnowledgeVault()
        self.memory_health = MemoryHealthMonitor()
        self.hybrid_memory = HybridMemoryBackend()
        self.memory_consolidator = MemoryConsolidator()
        self.search = FTS5Search()
        self.rag_engine = RAGEngine()
        self.hive = NexusHive()
        self.context_recovery = SessionContextRecovery()

    async def initialize(self) -> None:
        if self._initialized:
            return
        if self.recover_session_cb:
            self.recover_session_cb(self.project_root)

        self._initialized = True
        logger.info("MemoryService initialized")

    async def shutdown(self) -> None:
        pass

    def healthcheck(self) -> bool:
        return self.graph is not None

    @staticmethod
    def init_memory(director):
        from src.core.graph_evolution import GraphEvolution
        from src.core.knowledge_vault import KnowledgeVault
        from src.core.memory_health import MemoryHealthMonitor
        from src.core.hybrid_memory import HybridMemoryBackend
        from src.core.memory_consolidator import MemoryConsolidator
        from src.core.fts5_search import FTS5Search
        from src.core.rag_engine import RAGEngine
        from src.core.nexus_hive import NexusHive
        from src.core.session_context_recovery import SessionContextRecovery

        director.graph_evolution = GraphEvolution()
        director.vault = KnowledgeVault()
        director.memory_health = MemoryHealthMonitor()
        director.hybrid_memory = HybridMemoryBackend()
        director.memory_consolidator = MemoryConsolidator()
        director.search = FTS5Search()
        director.rag_engine = RAGEngine()
        director.hive = NexusHive()
        director.context_recovery = SessionContextRecovery()
        director._recover_session_context(director.current_project)
