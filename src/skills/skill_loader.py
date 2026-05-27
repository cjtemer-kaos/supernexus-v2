"""
ProgressiveSkillLoader - Carga on-demand de skills con manifest scan + Dynamic Creation

Fusiona:
- opencode: ThreadPool parallel scan para 14,000+ skills
- hermes-agent: Dynamic skill creation runtime

Patrón:
1. Scan paralelo de manifests (solo primeras líneas, no contenido completo)
2. Match por keywords contra task del usuario
3. Load completo solo del skill seleccionado
4. Dynamic Creation: Crear nuevos skills en runtime desde instrucciones naturales
"""

import logging
import re
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("nexus-skills")


@dataclass
class SkillManifest:
    name: str
    description: str
    triggers: List[str] = field(default_factory=list)
    category: str = "general"
    path: Path = None
    _content_cache: Optional[str] = None


class ProgressiveSkillLoader:
    """
    Carga progresiva de skills: scan manifests → match keywords → load on-demand.
    """

    def __init__(self, skills_base: Path, max_workers: int = 8):
        self.skills_base = skills_base
        self.max_workers = max_workers
        self.manifests: Dict[str, SkillManifest] = {}
        self._loaded: Dict[str, str] = {}
        self._scan_manifests()

    def _scan_manifests(self):
        """Scan paralelo de manifests. Solo lee primeras 15 líneas de cada SKILL.md."""
        if not self.skills_base.exists():
            logger.warning(f"Skills base not found: {self.skills_base}")
            return

        skill_dirs = [d for d in self.skills_base.iterdir() if d.is_dir()]
        logger.info(f"Scanning {len(skill_dirs)} skill directories (parallel, {self.max_workers} workers)")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._scan_single_skill, d): d
                for d in skill_dirs
            }
            for future in as_completed(futures):
                try:
                    manifest = future.result()
                    if manifest:
                        self.manifests[manifest.name] = manifest
                except Exception as e:
                    logger.warning(f"Failed to scan skill: {e}")

        logger.info(f"Indexed {len(self.manifests)} skills")

    def _scan_single_skill(self, skill_dir: Path) -> Optional[SkillManifest]:
        manifest_file = skill_dir / "SKILL.md"
        if not manifest_file.exists():
            manifest_file = skill_dir / "skill.md"
        if not manifest_file.exists():
            return None

        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                header = ""
                for _ in range(15):
                    line = f.readline()
                    if not line:
                        break
                    header += line

            name = skill_dir.name
            description = ""
            triggers = []
            category = "general"

            for line in header.split("\n"):
                line_stripped = line.strip()
                if line_stripped.startswith("# "):
                    if not description:
                        description = line_stripped[2:].strip()
                elif line_stripped.lower().startswith("name:"):
                    name = line_stripped.split(":", 1)[1].strip().strip('"').strip("'")
                elif line_stripped.lower().startswith("description:"):
                    description = line_stripped.split(":", 1)[1].strip().strip('"').strip("'")
                elif line_stripped.lower().startswith("category:"):
                    category = line_stripped.split(":", 1)[1].strip().strip('"').strip("'")
                elif line_stripped.lower().startswith("triggers:"):
                    raw = line_stripped.split(":", 1)[1].strip()
                    triggers = [t.strip() for t in raw.split(",") if t.strip()]

            if not description:
                desc_match = re.search(r'# (.+)', header)
                if desc_match:
                    description = desc_match.group(1).strip()

            if not triggers:
                all_text = header.lower()
                for word in all_text.split():
                    if len(word) > 4 and word.isalpha():
                        triggers.append(word)
                triggers = triggers[:10]

            return SkillManifest(
                name=name,
                description=description[:200],
                triggers=triggers,
                category=category,
                path=manifest_file,
            )
        except Exception as e:
            logger.warning(f"Error scanning {skill_dir}: {e}")
            return None

    def match_skills(self, task: str, top_k: int = 3) -> List[str]:
        """Dado un task, retorna los top_k skills más relevantes por keyword match."""
        task_lower = task.lower()
        task_words = set(re.findall(r'\b\w+\b', task_lower))

        scored = []
        for name, manifest in self.manifests.items():
            score = 0
            all_text = f"{manifest.name} {manifest.description} {' '.join(manifest.triggers)}".lower()
            for word in task_words:
                if word in all_text:
                    score += 1
            if manifest.description:
                desc_words = set(re.findall(r'\b\w+\b', manifest.description.lower()))
                score += len(task_words & desc_words) * 2
            if score > 0:
                scored.append((score, name))

        scored.sort(reverse=True)
        return [name for _, name in scored[:top_k]]

    def load_skill(self, name: str) -> str:
        """Carga contenido completo solo cuando se necesita."""
        if name in self._loaded:
            return self._loaded[name]

        manifest = self.manifests.get(name)
        if not manifest:
            return f"Skill not found: {name}"

        try:
            content = manifest.path.read_text(encoding="utf-8")
            self._loaded[name] = content
            logger.info(f"Skill loaded: {name} ({len(content)} chars)")
            return content
        except Exception as e:
            return f"Error loading skill {name}: {e}"

    def get_catalog(self) -> str:
        """Retorna catálogo de skills disponibles (solo manifests)."""
        lines = []
        for name, m in sorted(self.manifests.items()):
            lines.append(f"- **{name}** ({m.category}): {m.description}")
        return "\n".join(lines) if lines else "(no skills indexed)"

    def get_stats(self) -> Dict:
        return {
            "indexed_skills": len(self.manifests),
            "loaded_skills": len(self._loaded),
            "categories": list(set(m.category for m in self.manifests.values())),
        }

    # ─── Dynamic Skill Creation (hermes-agent pattern) ─────────────────────

    def create_skill(
        self,
        name: str,
        description: str,
        category: str = "general",
        triggers: List[str] = None,
        instructions: str = "",
        workflow: str = "",
        examples: str = "",
        author: str = "nexus-dynamic",
        version: str = "1.0.0",
        overwrite: bool = False,
    ) -> Dict:
        """
        Create a new skill at runtime.

        Args:
            name: Skill name (kebab-case, e.g. 'my-custom-skill')
            description: Short description of what the skill does
            category: Category (architecture, development, security, etc.)
            triggers: Keywords that trigger this skill
            instructions: Main instructions for the skill
            workflow: Step-by-step workflow
            examples: Usage examples
            author: Who created the skill
            version: Semantic version
            overwrite: Whether to overwrite existing skill

        Returns:
            Dict with status, path, and manifest info
        """
        # Validate name
        if not re.match(r'^[a-z][a-z0-9-]*$', name):
            return {"error": "Invalid name. Use kebab-case (e.g. 'my-skill')", "status": "error"}

        # Check if exists
        skill_dir = self.skills_base / name
        manifest_file = skill_dir / "SKILL.md"

        if manifest_file.exists() and not overwrite:
            return {"error": f"Skill '{name}' already exists. Use overwrite=True.", "status": "exists"}

        # Create directory
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Generate SKILL.md content
        triggers_str = ", ".join(triggers or [])
        workflow_text = workflow or "1. Understand the task\n2. Execute the workflow\n3. Return results"
        examples_text = examples or "No examples yet."
        instructions_text = instructions or f"Instructions for {name}."

        content = f"""---
name: {name}
description: {description}
category: {category}
triggers: {triggers_str}
author: {author}
version: {version}
created: {time.strftime('%Y-%m-%d %H:%M:%S')}
---

# {name}

{description}

## Instructions

{instructions_text}

## Workflow

{workflow_text}

## Examples

{examples_text}
"""

        manifest_file.write_text(content, encoding="utf-8")

        # Create README for the skill
        readme = skill_dir / "README.md"
        readme.write_text(f"# {name}\n\n{description}\n\nAuto-generated by Nexus Dynamic Skill Creation.", encoding="utf-8")

        # Register in memory
        manifest = SkillManifest(
            name=name,
            description=description,
            triggers=triggers or [],
            category=category,
            path=manifest_file,
        )
        self.manifests[name] = manifest

        logger.info(f"Dynamic skill created: {name} ({description})")

        return {
            "status": "created",
            "name": name,
            "path": str(skill_dir),
            "manifest": str(manifest_file),
            "description": description,
            "category": category,
            "triggers": triggers or [],
        }

    def create_skill_from_natural_language(self, request: str) -> Dict:
        """
        Create a skill from a natural language description.
        Parses the request to extract skill parameters.

        Args:
            request: Natural language description of the skill

        Returns:
            Dict with creation result
        """
        # Extract name from request
        name_match = re.search(r'(?:create|make|build|add)\s+(?:a\s+)?(?:skill\s+)?(?:called|named|for)?\s*["\']?([a-z][a-z0-9-]+)', request, re.IGNORECASE)
        name = name_match.group(1) if name_match else None

        if not name:
            # Generate name from first meaningful words
            words = re.findall(r'\b\w+\b', request)
            meaningful = [w for w in words if len(w) > 3 and w.lower() not in ('create', 'make', 'build', 'skill', 'called', 'named', 'that', 'this', 'with', 'from', 'should', 'would', 'could', 'will', 'can', 'able', 'help', 'please')]
            name = "-".join(meaningful[:3]).lower() if meaningful else f"custom-skill-{int(time.time())}"

        # Extract category
        categories = ['architecture', 'business', 'data-ai', 'development', 'general', 'infrastructure', 'security', 'testing', 'workflow']
        request_lower = request.lower()
        category = "general"
        for cat in categories:
            if cat in request_lower:
                category = cat
                break

        # Extract triggers (keywords that appear in the request)
        task_words = set(re.findall(r'\b\w+\b', request_lower))
        triggers = [w for w in task_words if len(w) > 4 and w.isalpha()][:8]

        # Extract description (first sentence or the whole request)
        desc_match = re.split(r'[.!?]', request)
        description = desc_match[0].strip() if desc_match else request[:200]

        # Extract instructions (text after 'instructions', 'should', 'must')
        instructions = ""
        inst_match = re.search(r'(?:instructions?|should|must|needs?\s+to)\s*:?\s*(.+)', request, re.IGNORECASE | re.DOTALL)
        if inst_match:
            instructions = inst_match.group(1).strip()

        # Extract workflow (text after 'workflow', 'steps', 'process')
        workflow = ""
        wf_match = re.search(r'(?:workflow|steps?|process)\s*:?\s*(.+)', request, re.IGNORECASE | re.DOTALL)
        if wf_match:
            workflow = wf_match.group(1).strip()

        return self.create_skill(
            name=name,
            description=description,
            category=category,
            triggers=triggers,
            instructions=instructions,
            workflow=workflow,
        )

    def delete_skill(self, name: str) -> Dict:
        """Delete a dynamically created skill."""
        manifest = self.manifests.get(name)
        if not manifest:
            return {"error": f"Skill '{name}' not found", "status": "not_found"}

        skill_dir = manifest.path.parent if manifest.path else self.skills_base / name

        try:
            if skill_dir.exists():
                import shutil
                shutil.rmtree(skill_dir)

            self.manifests.pop(name, None)
            self._loaded.pop(name, None)

            logger.info(f"Dynamic skill deleted: {name}")
            return {"status": "deleted", "name": name}
        except Exception as e:
            return {"error": str(e), "status": "error"}

    def list_dynamic_skills(self) -> List[Dict]:
        """List all dynamically created skills."""
        dynamic = []
        for name, manifest in self.manifests.items():
            if manifest.path:
                try:
                    content = manifest.path.read_text(encoding="utf-8")
                    if "author: nexus-dynamic" in content or "Auto-generated" in content:
                        dynamic.append({
                            "name": name,
                            "description": manifest.description,
                            "category": manifest.category,
                            "triggers": manifest.triggers,
                            "path": str(manifest.path.parent),
                        })
                except Exception:
                    pass
        return dynamic

    def export_skill(self, name: str) -> Optional[str]:
        """Export a skill as a JSON-serializable dict."""
        manifest = self.manifests.get(name)
        if not manifest:
            return None

        content = self.load_skill(name)
        return json.dumps({
            "name": name,
            "description": manifest.description,
            "category": manifest.category,
            "triggers": manifest.triggers,
            "content": content,
        }, indent=2)

    def import_skill(self, skill_json: str) -> Dict:
        """Import a skill from JSON export."""
        try:
            data = json.loads(skill_json)
            return self.create_skill(
                name=data["name"],
                description=data.get("description", ""),
                category=data.get("category", "general"),
                triggers=data.get("triggers", []),
                instructions=data.get("content", ""),
                overwrite=True,
            )
        except Exception as e:
            return {"error": str(e), "status": "error"}
