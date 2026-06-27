"""Tool Service — wraps LocalToolCaller + MCP bridge + web/browser tools."""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from src.core.ollama import OllamaClient
from src.core.local_tool_calling import LocalToolCaller

logger = logging.getLogger(__name__)


@dataclass
class ToolService:
    ai_tools: Any = None
    mcp_client: Any = None
    web_researcher: Any = None
    project_root: str = ""

    tool_caller: Optional[LocalToolCaller] = None
    _initialized: bool = field(default=False, init=False)

    async def initialize(self) -> None:
        if self._initialized:
            return
        self.tool_caller = LocalToolCaller(
            ollama_client=OllamaClient(),
            model="nexus-coder",
        )
        self._register_builtin_handlers()
        self._initialized = True
        logger.info("ToolService initialized")

    def _register_builtin_handlers(self) -> None:
        if self.ai_tools is None:
            logger.warning("ToolService: ai_tools not set, skipping handler registration")
            return

        async def _read(path: str):
            return str(self.ai_tools.workspace.read_file(path))

        async def _grep(pattern: str, path: str = "."):
            return str(self.ai_tools._tool_grep(pattern, path))

        async def _list(path: str):
            result = await self.ai_tools._tool_list_directory(path)
            return result.get("content", str(result)) if isinstance(result, dict) else str(result)

        async def _web_search(query: str):
            if self.web_researcher is not None:
                r = await self.web_researcher.search(query, max_results=5)
                return json.dumps(r)
            return "web_researcher not available"

        async def _web_navigate(url: str):
            if self.web_researcher is not None:
                r = await self.web_researcher.navigate(url)
                return str(r)
            return "web_researcher not available"

        async def _mcp_call(tool_name: str, arguments: dict):
            if self.mcp_client is not None:
                return await self.mcp_client.call_tool(tool_name, arguments)
            return "mcp_client not available"

        async def _list_mcp_tools(server: str = ""):
            if self.mcp_client is not None:
                return await self.mcp_client.list_tools(server)
            return "mcp_client not available"

        self.tool_caller.register_handler(
            "read_file", "Read a file and return its contents",
            {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            handler=_read,
        )
        self.tool_caller.register_handler(
            "search_code", "Search for a pattern in code files",
            {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string", "default": "."}}, "required": ["pattern"]},
            handler=_grep,
        )
        self.tool_caller.register_handler(
            "list_files", "List files in a directory",
            {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            handler=_list,
        )
        self.tool_caller.register_handler(
            "web_search", "Search the web for current information, documentation, or facts.",
            {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            handler=_web_search,
        )

    async def shutdown(self) -> None:
        pass

    def healthcheck(self) -> bool:
        return self.tool_caller is not None

    @staticmethod
    def init_tooling(director):
        tc = LocalToolCaller(ollama_client=OllamaClient(), model="nexus-coder")

        async def _read(path: str): return str(director.ai_tools.workspace.read_file(path))
        async def _grep(pattern: str, path: str = "."): return str(director.ai_tools._tool_grep(pattern, path))
        async def _list(path: str):
            result = await director.ai_tools._tool_list_directory(path)
            return result.get("content", str(result)) if isinstance(result, dict) else str(result)
        async def _web_search(query: str): return await director.tool_brain.web_search(query)
        async def _web_navigate(url: str): return await director.tool_brain.web_navigate(url)
        async def _browser_snapshot(url: str = "", interactive_only: bool = True) -> str:
            return await director.tool_brain.browser_snapshot(url, interactive_only)
        async def _browser_interact(ref_or_command: str, value: str = "") -> str:
            return await director.tool_brain.browser_interact(ref_or_command, value)
        async def _browser(command: str) -> str:
            return await director.tool_brain.browser(command)
        async def _mcp_call(tool_name: str, arguments: dict) -> str:
            return await director.tool_brain.mcp_call(tool_name, arguments)
        async def _list_mcp_tools(server: str = "") -> str:
            return await director.tool_brain.list_mcp_tools(server)

        tc.register_handler("read_file", "Read a file and return its contents",
            {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, handler=_read)
        tc.register_handler("grep_content", "Search for a pattern in code files",
            {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string", "default": "."}}, "required": ["pattern"]}, handler=_grep)
        tc.register_handler("list_dir", "List files in a directory",
            {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, handler=_list)
        tc.register_handler("web_search", "Search the web for current information, documentation, or facts.",
            {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}, handler=_web_search)
        tc.register_handler("web_navigate", "Navigate to a specific URL and extract its content. Use for YouTube channels, docs pages, etc.",
            {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}, handler=_web_navigate)
        tc.register_handler("browser", "Control a web browser using agent-browser commands. Use: open <url>, snapshot, click @e1, fill @e2 <text>, get text, eval <js>, screenshot, close. Run commands one at a time. Start with 'open <url>', then 'snapshot' to get refs, then interact with @e1, @e2 refs.",
            {"type": "object", "properties": {"command": {"type": "string", "description": "agent-browser command + args, e.g. 'open https://example.com', or 'snapshot -i', or 'click @e1', or 'fill @e2 hello'"}}, "required": ["command"]}, handler=_browser)
        tc.register_handler("browser_snapshot", "Navigate to a URL and get a compact accessibility tree with @e1/@e2 refs.",
            {"type": "object", "properties": {"url": {"type": "string", "description": "URL to navigate to (optional, uses current page if empty)"}, "interactive_only": {"type": "boolean", "description": "Only show interactive elements (default: true)"}}, "required": []}, handler=_browser_snapshot)
        tc.register_handler("browser_interact", "Interact with the page using deterministic refs from browser_snapshot.",
            {"type": "object", "properties": {"ref_or_command": {"type": "string", "description": "ref like @e1, or command like 'click @e1', or 'fill @e2 hello', or 'eval document.title'"}, "value": {"type": "string", "description": "optional: value for fill/type/select commands"}}, "required": ["ref_or_command"]}, handler=_browser_interact)
        tc.register_handler("mcp_call", "Call a tool from an external MCP server.",
            {"type": "object", "properties": {"tool_name": {"type": "string"}, "arguments": {"type": "object"}}, "required": ["tool_name", "arguments"]}, handler=_mcp_call)
        tc.register_handler("list_mcp_tools", "List all available MCP server tools.",
            {"type": "object", "properties": {"server": {"type": "string", "description": "Optional: filter by server name"}}, "required": []}, handler=_list_mcp_tools)

        async def _search_knowledge(query: str):
            ctx = director._get_memory_context(query, limit=8)
            return ctx if ctx else "No se encontró conocimiento relevante en mi base."

        tc.register_handler("search_knowledge", "Busca en tu propia base de conocimiento (cerebro) información relevante sobre un tema que hayas aprendido antes. Úsala cuando necesites recordar conceptos, ejemplos de código, patrones o cualquier cosa que hayas almacenado.",
            {"type": "object", "properties": {"query": {"type": "string", "description": "La consulta sobre lo que quieres recordar, ej: 'curso python funciones', 'patrones de diseño', 'ejemplos de API REST'"}}, "required": ["query"]}, handler=_search_knowledge)

        async def _research_scholar(query: str, deep: bool = False):
            from src.agents.scholar_gem import ScholarGem
            scholar = ScholarGem(
                web_researcher=getattr(director, 'web_researcher', None),
                mcp_client=getattr(director, 'mcp_client', None),
            )
            result = await scholar.research(query, deep=deep)
            sources = result.get("sources", [])
            summary = result.get("summary", "")
            report = result.get("report", "")
            if report:
                return f"Investigacion profunda:\n{report[:3000]}"
            parts = [f"Scholar encontro {len(sources)} fuentes para: {query}"]
            if summary:
                parts.append(f"Resumen: {summary}")
            for s in sources[:5]:
                parts.append(f"- {s.get('title','')}: {s.get('url','')} | {s.get('snippet','')[:200]}")
            return "\n".join(parts)

        tc.register_handler("research_scholar", "INVESTIGA en internet cuando NO sepas algo. Usa Scholar (búsqueda web multi-backend) para encontrar información actualizada. Pásale una consulta clara y específica. Usa deep=True para investigación exhaustiva.",
            {"type": "object", "properties": {"query": {"type": "string", "description": "La pregunta o tema a investigar, ej: 'ultima version de Python 2026', 'como funciona match case en python 3.10'"}, "deep": {"type": "boolean", "description": "True para investigación profunda iterativa (mas lenta pero mas completa), False para rapida"}}, "required": ["query"]}, handler=_research_scholar)

        director.tool_caller = tc
