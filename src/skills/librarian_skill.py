import os
import datetime
from pathlib import Path
from playwright_scholar import PlaywrightScholarSkill
from yt_extract import get_yt_transcript

class LibrarianSkill:
    """
    Automatización del Protocolo Sage: Registro y Aprendizaje de Enlaces.
    Organiza el conocimiento en la estructura nexus_brain.
    """
    def __init__(self):
        # Ruta relativa al proyecto para portabilidad
        self.base_path = str(Path(__file__).parent.parent.parent / "brain")
        self.scholar = PlaywrightScholarSkill()
        self.paths = {
            "STUDY": os.path.join(self.base_path, "1_NEXUS", "STUDY_LINKS.md"),
            "REPO": os.path.join(self.base_path, "1_NEXUS", "REPOSITORIES.md"),
            "TOOL": os.path.join(self.base_path, "2_HABILIDADES", "TOOLS_COLLECTION.md"),
            "DOC": os.path.join(self.base_path, "1_NEXUS", "DOCS_REFERENCES.md"),
            "OTHER": os.path.join(self.base_path, "1_NEXUS", "LINKS_ARCHIVE.md")
        }

    def process_link(self, url, category="OTHER", relevance="Alta"):
        """Investiga, categoriza y guarda el link según el protocolo."""
        print(f"[LIBRARIAN] Procesando: {url}...")
        
        info = {}
        # Manejo especial para YouTube
        if "youtube.com" in url or "youtu.be" in url:
            import re
            video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
            if video_id_match:
                video_id = video_id_match.group(1)
                transcript = get_yt_transcript(video_id)
                info['content'] = f"TRANSCRIPT EXTRACTED:\n{transcript[:1000]}..."
                info['title'] = f"YouTube Video: {video_id}"
        
        if not info.get('content'):
            info = self.scholar.research_url(url)
        
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        entry = f"""
## [FECHA: {date_str}]
### Tipo: {category}
- **Título**: {info.get('title', 'Sin Título')}
- **URL**: {url}
- **Descripción**: {info.get('content', '')[:500]}...
- **Relevancia**: {relevance}
---
"""
        target_file = self.paths.get(category, self.paths["OTHER"])
        
        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        
        with open(target_file, "a", encoding="utf-8") as f:
            f.write(entry)
            
        return {"status": "INDEXED", "file": target_file, "title": info.get('title')}

    def search_library(self, query):
        """Busca información dentro de los archivos de la biblioteca."""
        results = []
        query = query.lower()
        
        for category, path in self.paths.items():
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Búsqueda simple por bloques (delimitados por ---)
                    blocks = content.split("---")
                    for block in blocks:
                        if query in block.lower():
                            results.append({
                                "category": category,
                                "content": block.strip(),
                                "path": path
                            })
        return results

    def get_categories(self):
        return list(self.paths.keys())

    def list_recent(self, limit=5):
        """Muestra las entradas más recientes de la biblioteca global."""
        all_entries = []
        for category, path in self.paths.items():
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    blocks = f.read().split("---")
                    for b in blocks:
                        if b.strip():
                            all_entries.append(b.strip())
        
        return all_entries[-limit:]

if __name__ == "__main__":
    lib = LibrarianSkill()
    # Test de búsqueda
    print(f"Buscando 'Superhumano'...")
    print(lib.search_library("Superhumano"))
