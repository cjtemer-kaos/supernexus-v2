"""
Learning System - Aprendizaje activo de SuperNEXUS

Flujo:
1. ScholarGem investiga en la web
2. Usuario pasa link para enseñar
3. SageGem + ScholarGem analizan contenido
4. BibliotecaGem organiza la investigacion
5. Se implementa al sistema (nuevo skill/gema/patron)
6. Director lo activa cuando necesita
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import httpx

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class LearningSystem:
    """
    Sistema de aprendizaje activo.
    NEXUS investiga, analiza, organiza e implementa nuevo conocimiento.
    """

    def __init__(self):
        self.learning_log: List[Dict] = []
        self.skills_path = Path(__file__).parent.parent.parent / "src" / "skills"
        self.knowledge_path = Path(__file__).parent.parent.parent / "data" / "knowledge"

    async def investigate(self, topic: str, sources: List[str] = None) -> Dict:
        """
        ScholarGem investiga un tema.
        Busca en web, analiza fuentes, extrae conocimiento.
        """
        logger.info(f"ScholarGem investigating: {topic}")

        result = {
            "topic": topic,
            "sources_analyzed": 0,
            "key_findings": [],
            "timestamp": datetime.now().isoformat(),
        }

        # In production, this would use web search + LLM analysis
        # For now, structure the learning pipeline
        if sources:
            for source in sources:
                content = await self._fetch_and_analyze(source)
                if content:
                    result["sources_analyzed"] += 1
                    result["key_findings"].append({
                        "source": source,
                        "summary": content[:500],
                    })

        self.learning_log.append({
            "type": "investigation",
            "topic": topic,
            "result": result,
        })

        return result

    async def learn_from_link(self, url: str, category: str = "Topics") -> Dict:
        """
        Usuario pasa un link para enseñar.
        SageGem + ScholarGem analizan, BibliotecaGem organiza.
        """
        logger.info(f"Learning from link: {url}")

        # Fetch content
        content = await self._fetch_and_analyze(url)
        if not content:
            return {"success": False, "error": "Could not fetch content"}

        # Analyze and extract key concepts
        analysis = await self._analyze_content(content, url)

        # Organize via BibliotecaGem
        from src.memory.knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph()

        # Create knowledge note
        note_name = analysis.get("title", url.split("/")[-1] or "untitled")
        kg.create_note(
            category=category,
            name=note_name,
            content=analysis.get("summary", content[:2000]),
            tags=analysis.get("tags", []),
            links=analysis.get("related", []),
        )

        # Store as neural pattern
        from src.memory.neural_patterns import NeuralPatterns
        neural = NeuralPatterns()
        neural.store(
            task_name=f"learned_{note_name.lower().replace(' ', '_')}",
            data={
                "url": url,
                "title": note_name,
                "summary": analysis.get("summary", ""),
                "tags": analysis.get("tags", []),
            },
        )

        result = {
            "success": True,
            "title": note_name,
            "category": category,
            "tags": analysis.get("tags", []),
            "stored_in": ["knowledge_graph", "neural_patterns"],
        }

        self.learning_log.append({
            "type": "learn_from_link",
            "url": url,
            "result": result,
        })

        return result

    async def implement_skill(self, skill_name: str, skill_content: str) -> Dict:
        """
        Implementa un nuevo skill al sistema.
        Se activa cuando el Director lo necesita.
        """
        logger.info(f"Implementing skill: {skill_name}")

        skill_path = self.skills_path / f"{skill_name}.json"
        skill_data = {
            "name": skill_name,
            "content": skill_content,
            "created": datetime.now().isoformat(),
            "active": True,
        }

        skill_path.write_text(json.dumps(skill_data, indent=2), encoding="utf-8")

        result = {
            "success": True,
            "skill_name": skill_name,
            "path": str(skill_path),
        }

        self.learning_log.append({
            "type": "implement_skill",
            "skill_name": skill_name,
            "result": result,
        })

        return result

    async def _fetch_and_analyze(self, url: str) -> Optional[str]:
        """Obtiene y analiza contenido de una URL"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(url, follow_redirects=True)
                if r.status_code == 200:
                    # Extract text content (simplified)
                    # In production, use proper HTML parsing
                    text = r.text[:10000]  # Limit for now
                    return text
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
        return None

    async def _analyze_content(self, content: str, source: str) -> Dict:
        """
        Analiza contenido y extrae conceptos clave.
        En produccion, usaria LLM para analisis profundo.
        """
        # Simplified analysis - in production use LLM
        words = content.split()
        title = source.split("/")[-1] or "untitled"

        return {
            "title": title,
            "summary": content[:1000],
            "tags": ["learned", "web"],
            "related": [],
            "word_count": len(words),
        }

    def get_learning_stats(self) -> Dict:
        """Estadisticas de aprendizaje"""
        return {
            "total_learning_events": len(self.learning_log),
            "by_type": {
                "investigation": sum(1 for e in self.learning_log if e["type"] == "investigation"),
                "learn_from_link": sum(1 for e in self.learning_log if e["type"] == "learn_from_link"),
                "implement_skill": sum(1 for e in self.learning_log if e["type"] == "implement_skill"),
            },
            "recent": self.learning_log[-5:] if self.learning_log else [],
        }
