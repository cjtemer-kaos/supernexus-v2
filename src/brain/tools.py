"""Brain: Tools — wrappers que el director usa para ejecutar acciones.

Dos familias de wrappers vivien aca:

1. Deterministic tools (sin LLM): list_files / read_file / search / time /
   identity / system. Los usa el modo `_execute_deterministic` cuando no hay
   LLM disponible.

2. LLM-asistidos: web_search / web_navigate / browser_snapshot / browser_interact /
   browser / mcp_call / list_mcp_tools. Acceden a servicios externos (agent-browser,
   MCP servers).

Design:
    ToolBrain recibe el director como owner y consulta:
        - owner.identity_brain  — para get_identity_blurb
        - owner.web_researcher  — para web/browser
        - owner.mcp_client      — para MCP calls
    Todos opcionales: degrada con mensaje claro si faltan.
"""
from __future__ import annotations

import json
import logging
import shlex
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# Limit configurations
MAX_FILE_READ_BYTES: int = 2000
MAX_BROWSER_OUTPUT_BYTES: int = 2000
MAX_NAVIGATE_BYTES: int = 3000
MAX_MCP_RESULT_BYTES: int = 5000
DEFAULT_TIMEOUT_S: int = 10


class ToolBrain:
    """Wrappers de tools usados por el director."""

    def __init__(self, owner: Any):
        """
        Args:
            owner: el Director. Lee de owner.identity_brain, owner.web_researcher,
                owner.mcp_client. Todos opcionales.
        """
        self.owner = owner

    # ─── Deterministic tools (no LLM) ─────────────────────────────────

    async def list_files(self, task: str, ctx: str) -> str:
        path = ctx.strip() or "."
        try:
            p = Path(path)
            if not p.is_dir():
                return f"Directorio no encontrado: {path}"
            entries = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            lines = []
            for e in entries:
                suffix = "/" if e.is_dir() else ""
                lines.append(f"{e.name}{suffix}")
            return "\n".join(lines) if lines else "(empty)"
        except Exception as e:
            return f"Error listando archivos: {e}"

    async def read_file(self, task: str, ctx: str) -> str:
        path = ctx.strip() or ""
        if not path and " " in task:
            parts = task.split(" ", 1)
            if len(parts) > 1:
                path = parts[1].strip()
        if not path:
            return "Especifica que archivo leer."
        try:
            p = Path(path)
            if not p.exists():
                return f"Archivo no encontrado: {path}"
            content = p.read_text(encoding="utf-8", errors="replace")
            return content[:MAX_FILE_READ_BYTES] + (
                "\n...(truncado)" if len(content) > MAX_FILE_READ_BYTES else ""
            )
        except Exception as e:
            return f"Error leyendo archivo: {e}"

    async def search(self, task: str, ctx: str) -> str:
        query = ctx.strip() or ""
        if not query and " " in task:
            parts = task.split(" ", 1)
            if len(parts) > 1:
                query = parts[1].strip()
        if not query:
            return "Especifica que buscar."
        try:
            result = subprocess.run(
                ["findstr", "/s", "/i", query, "*"],
                capture_output=True, text=True, timeout=15,
                cwd=".",
            )
            lines = result.stdout.splitlines()[:30]
            if not lines:
                return f"Sin resultados para: {query}"
            return "\n".join(lines)
        except Exception as e:
            return f"Error buscando: {e}"

    async def time(self, task: str = "", ctx: str = "") -> str:
        now = datetime.now()
        return f"Son las {now.strftime('%H:%M:%S')} del {now.strftime('%d/%m/%Y')}"

    async def identity(self, task: str = "", ctx: str = "") -> str:
        ib = getattr(self.owner, "identity_brain", None)
        if ib is None:
            return "Identity brain not initialized"
        return ib.get_identity_blurb()

    async def system(self, task: str = "", ctx: str = "") -> str:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage(".")
            return (
                f"CPU: {cpu}%\n"
                f"RAM: {mem.percent}% ({mem.used // 1024**2}MB / {mem.total // 1024**2}MB)\n"
                f"Disco: {disk.percent}% ({disk.used // 1024**3}GB / {disk.total // 1024**3}GB)"
            )
        except ImportError:
            return "psutil no instalado. No puedo leer recursos del sistema."
        except Exception as e:
            return f"Error leyendo recursos: {e}"

    # ─── Web / browser (require web_researcher) ───────────────────────

    def _web(self):
        return getattr(self.owner, "web_researcher", None)

    async def web_search(self, query: str) -> str:
        wr = self._web()
        if wr is None:
            return "web_search unavailable: web_researcher not initialized"
        try:
            results = await wr.search(query, max_results=5)
            if results:
                lines = []
                for i, r in enumerate(results, 1):
                    lines.append(f"{i}. {r.get('title', '')}")
                    lines.append(
                        f"   {r.get('snippet', '')[:200]} [{r.get('source', '?')}]"
                    )
                return "\n".join(lines)
            return "(no results)"
        except Exception as e:
            return f"web_search error: {e}"

    async def web_navigate(self, url: str) -> str:
        wr = self._web()
        if wr is None:
            return "web_navigate unavailable: web_researcher not initialized"
        try:
            content = await wr.navigate(url)
            if content:
                return content[:MAX_NAVIGATE_BYTES]
            return f"(no content from {url})"
        except Exception as e:
            return f"web_navigate error: {e}"

    async def browser_snapshot(self, url: str = "", interactive_only: bool = True) -> str:
        wr = self._web()
        if wr is None:
            return "browser_snapshot unavailable: web_researcher not initialized"
        try:
            result = await wr.snapshot(url, interactive_only)
            if not result.get("success"):
                return f"[snapshot error] {result.get('error', 'unknown')}"
            refs = result.get("refs", {})
            compact = result.get("compact", "")
            title = result.get("title", "")
            url_out = result.get("url", "")
            parts = [
                f"URL: {url_out}",
                f"Title: {title}",
                f"Refs: {result.get('ref_count', 0)} available",
                "",
            ]
            for ref, desc in list(refs.items())[:20]:
                parts.append(f"  {ref} {desc}")
            parts.append("")
            parts.append("--- Compact Tree ---")
            parts.append(compact[:MAX_BROWSER_OUTPUT_BYTES])
            return "\n".join(parts)
        except Exception as e:
            return f"[snapshot error] {e}"

    async def browser_interact(self, ref_or_command: str, value: str = "") -> str:
        wr = self._web()
        if wr is None:
            return "browser_interact unavailable: web_researcher not initialized"
        try:
            return await wr.interact(ref_or_command, value)
        except Exception as e:
            return f"[interact error] {e}"

    async def browser(self, command: str) -> str:
        """Ejecuta un comando de agent-browser CLI."""
        try:
            parts = shlex.split(command)
            r = subprocess.run(
                ["agent-browser"] + parts,
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode != 0:
                return f"[browser error] {r.stderr.strip() or r.stdout.strip()}"
            return r.stdout.strip() or "(done)"
        except FileNotFoundError:
            return "[browser error] agent-browser not installed. Run: npm install -g agent-browser"
        except subprocess.TimeoutExpired:
            return "[browser timeout]"
        except Exception as e:
            return f"[browser error] {e}"

    # ─── MCP (require mcp_client) ─────────────────────────────────────

    def _mcp(self):
        return getattr(self.owner, "mcp_client", None)

    # ─── Deep Research ─────────────────────────────────────────────

    async def deep_research(self, query: str, max_time: int = 300) -> str:
        wr = self._web()
        try:
            from src.services.research_service import ResearchService
            svc = ResearchService(web_researcher=wr)
            result = await svc.deep_research(query, max_time=max_time)
            if len(result) > 5000:
                return result[:5000] + f"\n\n... (truncated, full report: {len(result)} chars)"
            return result
        except Exception as e:
            return f"deep_research error: {e}"

    async def mcp_call(self, tool_name: str, arguments: dict) -> str:
        client = self._mcp()
        if client is None:
            return "mcp_call unavailable: mcp_client not initialized"

        # Capability check (opt-in via NEXUS_ENFORCE_CAPS=1).
        # Reads current gema from contextvar (set by the dispatcher that
        # invoked this brain method). Skipped silently if anything is
        # unavailable — never breaks the call path itself.
        try:
            from src.observability.context import current_gema
            from src.security.capability_enforcer import check_call, enforcement_active
            gema_name = current_gema()
            if gema_name and enforcement_active():
                # mcp_call itself requires 'mcp.call' regardless of inner tool;
                # check_call will look up the gema in the loaded registry.
                gemas_dict = getattr(self.owner, "gemas", None) or {}
                verdict = check_call(gema_name, "mcp_call", gemas_dict)
                if not verdict.allowed:
                    return (f"mcp_call DENIED by capability_enforcer: "
                            f"{verdict.reason}. declared={list(verdict.declared_caps)}")
        except Exception:
            pass

        try:
            result = await client.call_tool(tool_name, arguments)
            return json.dumps(result, indent=2, default=str)[:MAX_MCP_RESULT_BYTES]
        except Exception as e:
            return f"mcp_call error: {e}"

    async def list_mcp_tools(self, server: str = "") -> str:
        client = self._mcp()
        if client is None:
            return "list_mcp_tools unavailable: mcp_client not initialized"
        try:
            if server:
                tools = client.get_tools_for_server(server)
            else:
                tools = client.list_tools()
            if not tools:
                return "(no MCP tools available)"
            lines = []
            for t in tools:
                name = t.get("name", t.get("full_name", "?"))
                desc = t.get("description", "")[:100]
                srv = t.get("server", "?")
                lines.append(f"- {name} [{srv}]: {desc}")
            return "\n".join(lines)
        except Exception as e:
            return f"list_mcp_tools error: {e}"
