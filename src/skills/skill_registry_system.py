#!/usr/bin/env python3
"""
🎓 SKILL REGISTRY SYSTEM
Sistema para registrar, cargar y gestionar 1.441+ skills
Proporciona indexación rápida y búsqueda de skills por tipo/categoría
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import hashlib
import datetime


@dataclass
class SkillMetadata:
    """Estructura estándar para metadata de skill"""
    name: str
    category: str  # ARCHITECT, DEVELOPER, SCHOLAR, CREATIVE, SAGE, CUSTOM
    subcategory: str
    version: str
    author: str
    description: str
    capabilities: List[str]
    dependencies: List[str]
    tags: List[str]
    gem_delegation: str  # Qué Gema debe ejecutar esto
    requires_internet: bool = False
    last_updated: str = ""
    status: str = "available"  # available, experimental, deprecated


class SkillRegistry:
    """Registro maestro de todos los skills disponibles"""

    def __init__(self, registry_dir: Path = Path("D:\\ias\\NEXUS_RESTORED\\03_SKILLS_CATALOG"), skills_root: Optional[str] = None, index_path: Optional[str] = None, node_id: str = "default"):
        if skills_root:
            self.registry_dir = Path(skills_root)
        else:
            self.registry_dir = Path(registry_dir)
        self.node_id = node_id
        self.registry_file = Path(index_path) if index_path else self.registry_dir / "skill_registry.json"
        self.index_file = self.registry_dir / "skill_index.json"

        self.registry = {}
        self.index = {}
        self.load_or_create_registry()

    def load_or_create_registry(self):
        """Carga registro existente o crea uno nuevo"""
        if self.registry_file.exists():
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                self.registry = json.load(f)
                print(f"[OK] Registro cargado: {len(self.registry)} skills")
        else:
            self.registry = {
                "metadata": {
                    "created": datetime.datetime.now().isoformat(),
                    "version": "1.0",
                    "total_skills": 0
                },
                "skills": {},
                "categories": {}
            }
            print("[OK] Nuevo registro creado")

        self.rebuild_index()

    def rebuild_index(self):
        """Reconstruye índice de búsqueda rápida"""
        self.index = {
            "by_name": {},
            "by_category": {},
            "by_capability": {},
            "by_gem": {},
            "search": {}
        }

        for skill_id, skill_data in self.registry.get("skills", {}).items():
            # Índice por nombre
            self.index["by_name"][skill_data.get("name", "")] = skill_id

            # Índice por categoría
            cat = skill_data.get("category", "CUSTOM")
            if cat not in self.index["by_category"]:
                self.index["by_category"][cat] = []
            self.index["by_category"][cat].append(skill_id)

            # Índice por capacidades
            for capability in skill_data.get("capabilities", []):
                if capability not in self.index["by_capability"]:
                    self.index["by_capability"][capability] = []
                self.index["by_capability"][capability].append(skill_id)

            # Índice por Gema delegado
            gem = skill_data.get("gem_delegation", "general")
            if gem not in self.index["by_gem"]:
                self.index["by_gem"][gem] = []
            self.index["by_gem"][gem].append(skill_id)

    def register_skill(self, metadata: SkillMetadata) -> str:
        """Registra un nuevo skill en el sistema"""
        skill_id = self._generate_skill_id(metadata.name)

        if skill_id in self.registry.get("skills", {}):
            print(f"[WARN] Skill {metadata.name} ya existe")
            return skill_id

        self.registry["skills"][skill_id] = {
            "id": skill_id,
            "name": metadata.name,
            "category": metadata.category,
            "subcategory": metadata.subcategory,
            "version": metadata.version,
            "author": metadata.author,
            "description": metadata.description,
            "capabilities": metadata.capabilities,
            "dependencies": metadata.dependencies,
            "tags": metadata.tags,
            "gem_delegation": metadata.gem_delegation,
            "requires_internet": metadata.requires_internet,
            "status": metadata.status,
            "registered_at": datetime.datetime.now().isoformat()
        }

        # Actualizar categoría
        if metadata.category not in self.registry.get("categories", {}):
            self.registry["categories"][metadata.category] = []
        self.registry["categories"][metadata.category].append(skill_id)

        # Actualizar contador
        self.registry["metadata"]["total_skills"] = len(self.registry["skills"])

        self.rebuild_index()
        self.save()

        print(f"[OK] Skill registrado: {metadata.name} ({skill_id})")
        return skill_id

    def register_skill_from_dict(self, skill_dict: Dict) -> str:
        """Registra skill desde diccionario"""
        metadata = SkillMetadata(
            name=skill_dict.get("name", "Unknown"),
            category=skill_dict.get("category", "CUSTOM"),
            subcategory=skill_dict.get("subcategory", ""),
            version=skill_dict.get("version", "1.0"),
            author=skill_dict.get("author", "Unknown"),
            description=skill_dict.get("description", ""),
            capabilities=skill_dict.get("capabilities", []),
            dependencies=skill_dict.get("dependencies", []),
            tags=skill_dict.get("tags", []),
            gem_delegation=skill_dict.get("gem_delegation", "general"),
            requires_internet=skill_dict.get("requires_internet", False),
            status=skill_dict.get("status", "available")
        )
        return self.register_skill(metadata)

    def find_skill_by_name(self, name: str) -> Optional[Dict]:
        """Busca skill por nombre exacto"""
        skill_id = self.index["by_name"].get(name)
        if skill_id:
            return self.registry["skills"].get(skill_id)
        return None

    def find_skills_by_category(self, category: str) -> List[Dict]:
        """Busca todos los skills en una categoría"""
        skill_ids = self.index["by_category"].get(category, [])
        return [self.registry["skills"][sid] for sid in skill_ids if sid in self.registry["skills"]]

    def find_skills_by_capability(self, capability: str) -> List[Dict]:
        """Busca skills que tienen cierta capacidad"""
        skill_ids = self.index["by_capability"].get(capability, [])
        return [self.registry["skills"][sid] for sid in skill_ids if sid in self.registry["skills"]]

    def find_skills_by_gem(self, gem_type: str) -> List[Dict]:
        """Busca skills delegados a cierto Gema"""
        skill_ids = self.index["by_gem"].get(gem_type, [])
        return [self.registry["skills"][sid] for sid in skill_ids if sid in self.registry["skills"]]

    def search_skills(self, query: str) -> List[Dict]:
        """Búsqueda full-text en descripción, tags, capabilities"""
        query_lower = query.lower()
        results = []

        for skill_id, skill_data in self.registry.get("skills", {}).items():
            match_score = 0

            # Búsqueda en nombre
            if query_lower in skill_data.get("name", "").lower():
                match_score += 10

            # Búsqueda en descripción
            if query_lower in skill_data.get("description", "").lower():
                match_score += 5

            # Búsqueda en tags
            for tag in skill_data.get("tags", []):
                if query_lower in tag.lower():
                    match_score += 3

            # Búsqueda en capabilities
            for cap in skill_data.get("capabilities", []):
                if query_lower in cap.lower():
                    match_score += 2

            if match_score > 0:
                skill_data["_match_score"] = match_score
                results.append(skill_data)

        # Ordenar por relevancia
        results.sort(key=lambda x: x["_match_score"], reverse=True)
        return results

    def get_statistics(self) -> Dict:
        """Obtiene estadísticas del registro"""
        stats = {
            "total_skills": self.registry["metadata"]["total_skills"],
            "by_category": {},
            "by_gem": {},
            "requires_internet": 0,
            "deprecated": 0
        }

        for category, skills in self.index["by_category"].items():
            stats["by_category"][category] = len(skills)

        for gem, skills in self.index["by_gem"].items():
            stats["by_gem"][gem] = len(skills)

        for skill_data in self.registry.get("skills", {}).values():
            if skill_data.get("requires_internet"):
                stats["requires_internet"] += 1
            if skill_data.get("status") == "deprecated":
                stats["deprecated"] += 1

        return stats

    def save(self):
        """Guarda registro a disco"""
        self.registry_dir.mkdir(parents=True, exist_ok=True)

        with open(self.registry_file, 'w', encoding='utf-8') as f:
            json.dump(self.registry, f, indent=2, ensure_ascii=False)

        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)

        print(f"[OK] Registro guardado en {self.registry_file}")

    def export_for_nexus_director(self) -> Dict:
        """Exporta skills para integración con NexusDirector"""
        director_config = {
            "skills_by_category": {},
            "skill_to_gem_mapping": {},
            "capabilities_mapping": {}
        }

        for skill_id, skill_data in self.registry.get("skills", {}).items():
            cat = skill_data["category"]
            if cat not in director_config["skills_by_category"]:
                director_config["skills_by_category"][cat] = []
            director_config["skills_by_category"][cat].append({
                "id": skill_id,
                "name": skill_data["name"],
                "gem": skill_data["gem_delegation"]
            })

            director_config["skill_to_gem_mapping"][skill_id] = skill_data["gem_delegation"]

            for cap in skill_data.get("capabilities", []):
                if cap not in director_config["capabilities_mapping"]:
                    director_config["capabilities_mapping"][cap] = []
                director_config["capabilities_mapping"][cap].append(skill_id)

        return director_config

    # ─── Skill Loading Pipeline ─────────────────────────────────────────

    def load_skills_parallel(self, skill_ids: List[str], max_workers: int = 4) -> Dict[str, Dict]:
        """Carga multiples skills en paralelo usando un pool de threads."""
        import concurrent.futures
        import json
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_map = {
                pool.submit(self._load_single_skill, sid): sid
                for sid in skill_ids if sid in self.registry.get("skills", {})
            }
            for future in concurrent.futures.as_completed(future_map):
                sid = future_map[future]
                try:
                    results[sid] = future.result()
                except Exception as e:
                    results[sid] = {"error": str(e)}
        return results

    def _load_single_skill(self, skill_id: str) -> Dict:
        skill = self.registry.get("skills", {}).get(skill_id)
        if not skill:
            return {"error": f"Skill not found: {skill_id}"}
        manifest_path = Path(self.registry_dir) / skill_id / "SKILL.md"
        if manifest_path.exists():
            skill["manifest"] = manifest_path.read_text(encoding="utf-8")[:5000]
        return skill

    def progressive_skill_scan(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Progressive loading: first scans manifest (fast), then loads full content.
        Phase 1: metadata match (from registry index)
        Phase 2: manifest scan (SKILL.md headers only)
        Phase 3: full content load (on demand)
        """
        phase1 = self.search_skills(query)[:limit * 3]
        if not phase1:
            return []

        scored = []
        for skill in phase1:
            path = Path(self.registry_dir) / skill.get("id", "") / "SKILL.md"
            manifest_hit = False
            if path.exists():
                header = path.read_text(encoding="utf-8")[:1000].lower()
                manifest_hit = query.lower() in header
            scored.append({
                **skill,
                "manifest_hit": manifest_hit,
                "match_score": skill.get("_match_score", 0) + (5 if manifest_hit else 0),
            })

        scored.sort(key=lambda x: x["match_score"], reverse=True)
        return scored[:limit]

    def get_skills_by_capabilities(self, capabilities: List[str], match_all: bool = False) -> List[Dict]:
        """Encuentra skills que cubren un conjunto de capacidades."""
        results = []
        for skill_id, skill_data in self.registry.get("skills", {}).items():
            skill_caps = set(skill_data.get("capabilities", []))
            query_caps = set(capabilities)
            if match_all:
                if query_caps.issubset(skill_caps):
                    results.append(skill_data)
            else:
                if query_caps & skill_caps:
                    results.append(skill_data)
        return results

    def skill_dependency_graph(self, skill_id: str, max_depth: int = 3) -> Dict:
        """Build dependency graph for a skill up to max_depth."""
        graph = {"root": skill_id, "dependencies": {}, "depth": 0}
        visited = {skill_id}
        queue = [(skill_id, 0)]
        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            skill = self.registry.get("skills", {}).get(current)
            if not skill:
                continue
            deps = skill.get("dependencies", [])
            graph["dependencies"][current] = dep_info = []
            for dep in deps:
                dep_id = self.index["by_name"].get(dep)
                if dep_id and dep_id not in visited:
                    visited.add(dep_id)
                    dep_info.append({"name": dep, "id": dep_id})
                    queue.append((dep_id, depth + 1))
                elif dep_id:
                    dep_info.append({"name": dep, "id": dep_id, "circular": True})
                else:
                    dep_info.append({"name": dep, "id": None, "missing": True})
        return graph

    def print_report(self):
        """Imprime reporte del registro"""
        stats = self.get_statistics()

        print("\n" + "="*80)
        print("[SKILLS] REPORTE DEL REGISTRO DE SKILLS")
        print("="*80 + "\n")

        print(f"Total de skills: {stats['total_skills']}\n")

        print("Por categoría:")
        for cat, count in stats["by_category"].items():
            print(f"  {cat}: {count} skills")

        print(f"\nPor Gema:")
        for gem, count in stats["by_gem"].items():
            print(f"  {gem}: {count} skills")

        print(f"\nRequiere internet: {stats['requires_internet']}")
        print(f"Deprecated: {stats['deprecated']}")

    def _generate_skill_id(self, name: str) -> str:
        """Genera ID único para skill"""
        # Formato: category_name_hash
        name_clean = name.lower().replace(" ", "_").replace("-", "_")
        name_hash = hashlib.md5(name.encode()).hexdigest()[:8]
        return f"{name_clean}_{name_hash}"


def main():
    """Demo del sistema de registro"""
    registry = SkillRegistry()

    # Ejemplo: registrar algunos skills de prueba
    test_skills = [
        {
            "name": "Sequential Thinking",
            "category": "SCHOLAR",
            "subcategory": "Advanced Reasoning",
            "version": "1.0",
            "author": "Nexus Team",
            "description": "Desglosar problemas complejos paso a paso",
            "capabilities": ["reasoning", "problem-solving", "chain-of-thought"],
            "dependencies": [],
            "tags": ["ai", "logic", "analysis"],
            "gem_delegation": "scholar_gem"
        },
        {
            "name": "Code Review Automation",
            "category": "DEVELOPER",
            "subcategory": "Code Analysis",
            "version": "1.2",
            "author": "Nexus Team",
            "description": "Revisar código automáticamente para calidad y seguridad",
            "capabilities": ["code-review", "security-scan", "quality-metrics"],
            "dependencies": ["sequential_thinking"],
            "tags": ["python", "security", "quality"],
            "gem_delegation": "developer_gem"
        }
    ]

    for skill_dict in test_skills:
        registry.register_skill_from_dict(skill_dict)

    # Búsquedas de ejemplo
    print("\n\n=== EJEMPLOS DE BÚSQUEDA ===\n")

    print("Búsqueda: 'reasoning'")
    results = registry.search_skills("reasoning")
    for r in results:
        print(f"  - {r['name']} ({r['category']})")

    print("\nSkills por categoría DEVELOPER:")
    dev_skills = registry.find_skills_by_category("DEVELOPER")
    for skill in dev_skills:
        print(f"  - {skill['name']}: {skill['capabilities']}")

    registry.print_report()


if __name__ == "__main__":
    main()
