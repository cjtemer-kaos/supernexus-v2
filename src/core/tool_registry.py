"""
DirectorToolRegistry - Registro unificado de todas las herramientas disponibles

Centraliza AI tools, local tools, gemas, MCP tools y auto-registered tools
en una sola vista que el Director usa para conocer sus propias capacidades.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolEntry:
    """
    Una entrada de herramienta en el registro unificado.
    Independiente del origen (AI tool, local tool, gema, MCP).
    """
    name: str
    description: str
    category: str        # "ai_tool", "local_tool", "gema", "mcp", "registered"
    model: str = ""
    tags: List[str] = field(default_factory=list)
    call_count: int = 0
    success_count: int = 0
    parameters: Dict = field(default_factory=dict)
    source: str = ""     # modulo o archivo de origen

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "model": self.model,
            "tags": self.tags,
            "call_count": self.call_count,
            "success_count": self.success_count,
            "source": self.source,
        }


class DirectorToolRegistry:
    """
    Vista unificada de todas las herramientas que el Director puede usar.
    No duplica datos: agrega desde las fuentes existentes bajo demanda.
    """

    def __init__(self):
        self._cache: Dict[str, ToolEntry] = {}
        self._dirty = True

    def invalidate(self):
        self._cache.clear()
        self._dirty = True

    def rebuild(self, director: Any):
        """
        Reconstruye el registro desde todas las fuentes disponibles en el Director.
        Llama despues de inicializacion o cuando cambian las capacidades.
        """
        self._cache.clear()

        # 1. AI Tools (AIToolsRegistry)
        if hasattr(director, 'ai_tools') and hasattr(director.ai_tools, 'tools'):
            for name, tool in director.ai_tools.tools.items():
                self._cache[f"ai:{name}"] = ToolEntry(
                    name=name,
                    description=tool.role,
                    category="ai_tool",
                    model=tool.model,
                    tags=tool.tags,
                    source="AIToolsRegistry",
                )

        # 2. Auto-registered tools (decorator @auto_register_tool)
        if hasattr(director.ai_tools, 'get_registered_tools'):
            try:
                for t in director.ai_tools.get_registered_tools():
                    self._cache[f"reg:{t['name']}"] = ToolEntry(
                        name=t["name"],
                        description=t.get("description", ""),
                        category="registered",
                        tags=t.get("tags", []),
                        source="auto_register_tool",
                    )
            except Exception:
                pass

        # 3. Local tools (LocalToolCaller)
        if hasattr(director, 'tool_caller') and hasattr(director.tool_caller, 'get_tool_schemas'):
            try:
                for schema in director.tool_caller.get_tool_schemas():
                    fn = schema.get("function", {})
                    name = fn.get("name", "")
                    if name:
                        self._cache[f"local:{name}"] = ToolEntry(
                            name=name,
                            description=fn.get("description", ""),
                            category="local_tool",
                            parameters=fn.get("parameters", {}),
                            source="LocalToolCaller",
                        )
            except Exception:
                pass

        # 4. Gemas (como herramientas semanticas)
        if hasattr(director, 'gemas'):
            for name, gem in director.gemas.items():
                self._cache[f"gema:{name}"] = ToolEntry(
                    name=name,
                    description=gem.description,
                    category="gema",
                    model=gem.model,
                    tags=gem.tags,
                    call_count=gem.execution_count,
                    source="GemaHost",
                )

        # 5. MCP tools
        if hasattr(director, 'mcp_client') and hasattr(director.mcp_client, 'list_tools'):
            try:
                for t in director.mcp_client.list_tools():
                    self._cache[f"mcp:{t['name']}"] = ToolEntry(
                        name=t["name"],
                        description=t.get("description", ""),
                        category="mcp",
                        source="MCPClientBridge",
                    )
            except Exception:
                pass

        # 6. Skills como herramientas
        if hasattr(director, 'skill_loader') and hasattr(director.skill_loader, 'list_skills'):
            try:
                for s in director.skill_loader.list_skills():
                    self._cache[f"skill:{s}"] = ToolEntry(
                        name=s,
                        description=f"Skill: {s}",
                        category="skill",
                        source="ProgressiveSkillLoader",
                    )
            except Exception:
                pass

        self._dirty = False
        logger.info(f"ToolRegistry rebuilt: {len(self._cache)} tools total")

    def get_all(self) -> List[ToolEntry]:
        return list(self._cache.values())

    def get_by_category(self, category: str) -> List[ToolEntry]:
        return [t for t in self._cache.values() if t.category == category]

    def get_summary(self) -> Dict:
        """Resumen por categoria para reportes rapidos"""
        categories = {}
        for t in self._cache.values():
            categories.setdefault(t.category, {"count": 0, "tools": []})
            categories[t.category]["count"] += 1
            categories[t.category]["tools"].append(t.name)
        return {
            "total": len(self._cache),
            "categories": categories,
        }

    def get_tool_description_text(self) -> str:
        """Genera texto descriptivo de todas las herramientas para system prompt"""
        lines = []
        for cat in ["gema", "ai_tool", "local_tool", "mcp", "skill", "registered"]:
            tools = self.get_by_category(cat)
            if not tools:
                continue
            label = {"gema": "Gemas especializadas",
                     "ai_tool": "Modelos de IA",
                     "local_tool": "Herramientas locales",
                     "mcp": "Herramientas MCP",
                     "skill": "Skills disponibles",
                     "registered": "Funciones registradas"}.get(cat, cat)
            lines.append(f"\n{label}:")
            for t in sorted(tools, key=lambda x: x.name):
                parts = [f"  - {t.name}: {t.description}"]
                if t.model:
                    parts.append(f" [{t.model}]")
                if t.tags:
                    parts.append(f" ({', '.join(t.tags[:4])})")
                lines.append("".join(parts))
        return "\n".join(lines)
