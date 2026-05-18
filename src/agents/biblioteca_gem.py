"""
Gema Biblioteca - Organizacion de conocimiento para SuperNEXUS v2.0

Organiza, indexa y clasifica la investigacion y el conocimiento.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class BibliotecaGem:
    """
    Gema especializado en organizacion de conocimiento.
    Indexa, clasifica y mantiene el conocimiento organizado.
    """

    def __init__(self):
        self.knowledge_path = Path(__file__).parent.parent.parent / "data" / "knowledge"
        self.index_file = self.knowledge_path / "index.json"
        self._ensure_index()

    def _ensure_index(self):
        """Asegura que el indice exista"""
        self.knowledge_path.mkdir(parents=True, exist_ok=True)
        if not self.index_file.exists():
            self.index_file.write_text(json.dumps({
                "entries": [],
                "categories": ["People", "Organizations", "Projects", "Topics"],
                "updated": datetime.now().isoformat(),
            }, indent=2), encoding="utf-8")

    async def organize(self, title: str, content: str, category: str, tags: List[str] = None) -> Dict:
        """
        Organiza conocimiento en la biblioteca.
        Crea nota, actualiza indice, establece links.
        """
        logger.info(f"BibliotecaGem organizing: {title}")

        # Create note
        note_id = title.lower().replace(" ", "_").replace("/", "_")[:50]
        note_dir = self.knowledge_path / category.lower().replace(" ", "_")
        note_dir.mkdir(parents=True, exist_ok=True)
        filepath = note_dir / f"{note_id}.md"
        filepath.write_text(
            f"# {title}\n\n"
            f"Category: {category}\n"
            f"Tags: {', '.join(tags or [])}\n"
            f"Created: {datetime.now().isoformat()}\n\n"
            f"---\n\n"
            f"{content}\n",
            encoding="utf-8"
        )

        # Update index
        index = json.loads(self.index_file.read_text(encoding="utf-8"))
        index["entries"].append({
            "title": title,
            "category": category,
            "tags": tags or [],
            "path": filepath,
            "created": datetime.now().isoformat(),
        })
        index["updated"] = datetime.now().isoformat()
        self.index_file.write_text(json.dumps(index, indent=2), encoding="utf-8")

        return {
            "success": True,
            "title": title,
            "category": category,
            "path": filepath,
        }

    async def search(self, query: str) -> List[Dict]:
        """Busca en la biblioteca"""
        index = json.loads(self.index_file.read_text(encoding="utf-8"))
        query_lower = query.lower()

        results = []
        for entry in index.get("entries", []):
            if (query_lower in entry.get("title", "").lower() or
                    any(query_lower in tag.lower() for tag in entry.get("tags", []))):
                results.append(entry)

        return results

    def get_stats(self) -> Dict:
        """Estadisticas de la biblioteca"""
        index = json.loads(self.index_file.read_text(encoding="utf-8"))
        entries = index.get("entries", [])

        by_category = {}
        for entry in entries:
            cat = entry.get("category", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1

        return {
            "total_entries": len(entries),
            "by_category": by_category,
            "last_updated": index.get("updated", ""),
        }
