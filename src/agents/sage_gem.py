"""
Gema Sage - Persistencia y memoria para SuperNEXUS v2.0

Analiza contenido, persiste conocimiento, mantiene memoria a largo plazo.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class SageGem:
    """
    Gema especializado en persistencia y memoria.
    Analiza, persiste y mantiene conocimiento a largo plazo.
    """

    def __init__(self):
        self.memory_path = Path(__file__).parent.parent.parent / "data" / "base_memory"
        self.long_term_file = self.memory_path / "long_term_memory.json"
        self._ensure_memory_file()

    def _ensure_memory_file(self):
        """Asegura que el archivo de memoria exista"""
        self.memory_path.mkdir(parents=True, exist_ok=True)
        if not self.long_term_file.exists():
            self.long_term_file.write_text(json.dumps({
                "identity": {"name": "SuperNEXUS", "version": "2.0"},
                "learned_facts": [],
                "preferences": {},
            }, indent=2), encoding="utf-8")

    async def analyze_and_persist(self, content: str, source: str, category: str = "general") -> Dict:
        """
        Analiza contenido y lo persiste en memoria a largo plazo.
        """
        logger.info(f"SageGem analyzing and persisting: {source}")

        fact = {
            "id": f"fact_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "content": content[:2000],
            "source": source,
            "category": category,
            "learned_at": datetime.now().isoformat(),
            "confidence": 0.9,
        }

        # Save to long-term memory
        memory = json.loads(self.long_term_file.read_text(encoding="utf-8"))
        memory["learned_facts"].append(fact)
        self.long_term_file.write_text(json.dumps(memory, indent=2), encoding="utf-8")

        return {"success": True, "fact_id": fact["id"], "category": category}

    async def recall(self, query: str) -> List[Dict]:
        """Busca en memoria a largo plazo"""
        memory = json.loads(self.long_term_file.read_text(encoding="utf-8"))
        query_lower = query.lower()

        results = []
        for fact in memory.get("learned_facts", []):
            if query_lower in fact.get("content", "").lower():
                results.append(fact)

        return results

    def get_memory_stats(self) -> Dict:
        """Estadisticas de memoria"""
        memory = json.loads(self.long_term_file.read_text(encoding="utf-8"))
        facts = memory.get("learned_facts", [])

        return {
            "total_facts": len(facts),
            "by_category": {},
            "identity": memory.get("identity", {}),
        }
