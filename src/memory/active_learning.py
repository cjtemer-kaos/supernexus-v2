"""
Active Learning Loop - Aprendizaje activo para SuperNEXUS v2.0

Flujo completo: Scholar investiga → Sage analiza → Biblioteca organiza → Implementa.
Si NEXUS no sabe algo, lo aprende.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from src.agents.scholar_gem import ScholarGem
from src.agents.sage_gem import SageGem
from src.agents.biblioteca_gem import BibliotecaGem
from src.memory.knowledge_graph import KnowledgeGraph
from src.memory.rag_memory import RAGMemory

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ActiveLearningLoop:
    """
    Loop de aprendizaje activo.
    Si no sabe algo → investiga → analiza → organiza → implementa.
    """

    def __init__(self):
        self.scholar = ScholarGem()
        self.sage = SageGem()
        self.biblioteca = BibliotecaGem()
        self.kg = KnowledgeGraph()
        self.rag = RAGMemory()
        self.learning_history: List[Dict] = []
        self._knowledge_base_path = Path(__file__).parent.parent.parent / "data" / "knowledge" / "learned"
        self._knowledge_base_path.mkdir(parents=True, exist_ok=True)

    async def learn(self, query: str, user_links: List[str] = None) -> Dict:
        """
        Flujo completo de aprendizaje:
        1. Scholar investiga en la web
        2. Usuario pasa links para enseñar (opcional)
        3. Sage analiza contenido
        4. Biblioteca organiza
        5. Se implementa como nuevo conocimiento
        """
        logger.info(f"ActiveLearning: Starting learning for '{query}'")
        start = datetime.now()

        result = {
            "query": query,
            "steps": [],
            "success": False,
            "knowledge_added": [],
        }

        # Paso 1: Scholar investiga
        logger.info("Step 1: Scholar investigating...")
        research = await self.scholar.research(query, max_sources=3)
        result["steps"].append({
            "step": "research",
            "gem": "scholar",
            "sources_found": len(research.get("sources", [])),
            "summary": research.get("summary", "")[:500],
        })

        # Paso 2: Analizar links del usuario (si hay)
        if user_links:
            logger.info(f"Step 2: Analyzing {len(user_links)} user-provided links...")
            for link in user_links:
                analysis = await self.scholar.analyze_link(link)
                result["steps"].append({
                    "step": "user_link_analysis",
                    "gem": "scholar",
                    "url": link,
                    "success": analysis.get("success", False),
                })

        # Paso 3: Sage analiza y persiste
        logger.info("Step 3: Sage analyzing and persisting...")
        combined_content = research.get("summary", "")
        if research.get("sources"):
            for source in research["sources"]:
                combined_content += f"\n\nSource: {source.get('url', '')}\n{source.get('summary', '')}"

        persist_result = await self.sage.analyze_and_persist(
            content=combined_content,
            source=f"research:{query}",
            category="learned",
        )
        result["steps"].append({
            "step": "analysis_persistence",
            "gem": "sage",
            "fact_id": persist_result.get("fact_id", ""),
            "success": persist_result.get("success", False),
        })

        # Paso 4: Biblioteca organiza
        logger.info("Step 4: Biblioteca organizing...")
        org_result = await self.biblioteca.organize(
            title=f"Learned: {query[:80]}",
            content=combined_content[:3000],
            category="Learned",
            tags=["auto-learned", query[:30]],
        )
        result["steps"].append({
            "step": "organization",
            "gem": "biblioteca",
            "title": org_result.get("title", ""),
            "path": org_result.get("path", ""),
            "success": org_result.get("success", False),
        })

        # Paso 5: Agregar a RAG
        logger.info("Step 5: Adding to RAG memory...")
        rag_id = f"learned_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        rag_result = self.rag.add(
            entry_id=rag_id,
            text=combined_content[:5000],
            source=f"learning:{query}",
            tags=["learned", query[:30]],
        )
        result["steps"].append({
            "step": "rag_indexing",
            "gem": "rag",
            "id": rag_id,
            "success": rag_result.get("success", False),
        })

        # Paso 6: Guardar en base de conocimiento
        logger.info("Step 6: Saving to knowledge base...")
        kb_file = self._knowledge_base_path / f"{rag_id}.json"
        kb_data = {
            "query": query,
            "content": combined_content,
            "research": research,
            "learned_at": datetime.now().isoformat(),
            "sources_count": len(research.get("sources", [])),
        }
        kb_file.write_text(json.dumps(kb_data, indent=2), encoding="utf-8")
        result["knowledge_added"].append(str(kb_file))

        result["success"] = True
        duration = (datetime.now() - start).total_seconds()
        result["duration_seconds"] = duration

        self.learning_history.append(result)
        logger.info(f"ActiveLearning: Completed in {duration:.1f}s")
        return result

    async def learn_from_link(self, url: str, topic: str) -> Dict:
        """
        Aprende directamente de un link pasado por el usuario.
        """
        logger.info(f"ActiveLearning: Learning from link '{url}'")

        # Analizar link
        analysis = await self.scholar.analyze_link(url)
        if not analysis.get("success"):
            return {"success": False, "error": "Could not analyze link"}

        # Persistir
        persist_result = await self.sage.analyze_and_persist(
            content=analysis.get("content_preview", ""),
            source=url,
            category="user_taught",
        )

        # Organizar
        org_result = await self.biblioteca.organize(
            title=f"User taught: {topic[:80]}",
            content=analysis.get("content_preview", "")[:3000],
            category="UserTaught",
            tags=["user-taught", topic[:30]],
        )

        # RAG
        rag_id = f"user_taught_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.rag.add(
            entry_id=rag_id,
            text=analysis.get("content_preview", "")[:5000],
            source=url,
            tags=["user-taught", topic[:30]],
        )

        return {
            "success": True,
            "url": url,
            "topic": topic,
            "fact_id": persist_result.get("fact_id", ""),
            "rag_id": rag_id,
        }

    def get_learning_stats(self) -> Dict:
        """Estadisticas de aprendizaje"""
        return {
            "total_learnings": len(self.learning_history),
            "successful": sum(1 for l in self.learning_history if l.get("success")),
            "failed": sum(1 for l in self.learning_history if not l.get("success")),
            "knowledge_files": len(list(self._knowledge_base_path.glob("*.json"))) if self._knowledge_base_path.exists() else 0,
        }

    async def close(self):
        await self.scholar.close()
