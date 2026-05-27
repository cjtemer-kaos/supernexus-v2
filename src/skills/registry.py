"""
Skills Registry - Lazy loading de skills para SuperNEXUS v2.0

Carga skills on-demand segun el proyecto activo y la tarea.
No carga todos los 1425+ skills en memoria, solo los necesarios.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class SkillsRegistry:
    """
    Registro de skills con lazy loading.
    Solo carga skills cuando el Director los necesita.
    """

    def __init__(self, skills_base: Optional[str] = None, projects_base: Optional[str] = None):
        if skills_base is None:
            skills_base = str(Path(__file__).parent.parent.parent / "src" / "skills")
        if projects_base is None:
            projects_base = str(Path(__file__).parent.parent.parent / "data" / "projects")

        self.skills_base = Path(skills_base)
        self.projects_base = Path(projects_base)
        self.loaded_skills: Dict[str, Dict] = {}
        self.skill_index: Dict[str, Dict] = {}
        self._build_index()

    def _build_index(self):
        """Construye indice de skills disponibles"""
        if self.skills_base.exists():
            for skill_file in self.skills_base.glob("*.json"):
                try:
                    data = json.loads(skill_file.read_text(encoding="utf-8"))
                    self.skill_index[data.get("name", skill_file.stem)] = {
                        "path": str(skill_file),
                        "tags": data.get("tags", []),
                        "active": data.get("active", True),
                    }
                except:
                    pass

    def load_skill(self, skill_name: str) -> Optional[Dict]:
        """Carga un skill especifico (lazy loading)"""
        if skill_name in self.loaded_skills:
            return self.loaded_skills[skill_name]

        skill_info = self.skill_index.get(skill_name)
        if not skill_info:
            logger.warning(f"Skill not found: {skill_name}")
            return None

        try:
            data = json.loads(Path(skill_info["path"]).read_text(encoding="utf-8"))
            self.loaded_skills[skill_name] = data
            logger.info(f"Skill loaded: {skill_name}")
            return data
        except Exception as e:
            logger.error(f"Error loading skill {skill_name}: {e}")
            return None

    def load_skills_for_project(self, project: str) -> List[Dict]:
        """Carga skills especificos de un proyecto"""
        project_skills_path = self.projects_base / project / "skills"
        loaded = []

        if project_skills_path.exists():
            for skill_file in project_skills_path.glob("*.json"):
                try:
                    data = json.loads(skill_file.read_text(encoding="utf-8"))
                    self.loaded_skills[data.get("name", skill_file.stem)] = data
                    loaded.append(data)
                except:
                    pass

        logger.info(f"Loaded {len(loaded)} skills for project: {project}")
        return loaded

    def unload_project_skills(self, project: str):
        """Descarga skills de un proyecto (memoria selectiva)"""
        project_skills_path = self.projects_base / project / "skills"
        if project_skills_path.exists():
            for skill_file in project_skills_path.glob("*.json"):
                name = skill_file.stem
                if name in self.loaded_skills:
                    del self.loaded_skills[name]
        logger.info(f"Unloaded skills for project: {project}")

    def find_skills(self, tags: List[str]) -> List[Dict]:
        """Busca skills por tags"""
        results = []
        for name, info in self.skill_index.items():
            if any(tag in info.get("tags", []) for tag in tags):
                skill = self.load_skill(name)
                if skill:
                    results.append(skill)
        return results

    def get_stats(self) -> Dict:
        """Estadisticas del registro de skills"""
        return {
            "total_indexed": len(self.skill_index),
            "loaded_in_memory": len(self.loaded_skills),
            "skills": list(self.skill_index.keys())[:20],  # First 20
        }
