"""
Tools - Herramientas builtin para SuperNEXUS v2.0

Adaptado de Rowboat builtin-tools.
Workspace CRUD, executeCommand, parseFile, etc.
"""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class WorkspaceTools:
    """Herramientas de workspace (CRUD de archivos)"""

    def __init__(self, workspace_root: Optional[str] = None):
        if workspace_root is None:
            workspace_root = str(Path(__file__).parent.parent.parent / "data")
        self.root = Path(workspace_root)

    def read_file(self, path: str, offset: int = 1, limit: int = 2000) -> Dict:
        """Lee archivo con paginacion"""
        filepath = Path(path) if Path(path).is_absolute() else self.root / path
        if not filepath.exists():
            return {"error": f"File not found: {path}"}

        try:
            lines = filepath.read_text(encoding="utf-8").split("\n")
            start = max(0, offset - 1)
            end = start + limit
            page = lines[start:end]
            has_more = end < len(lines)

            prefixed = [f"{i + offset}: {line}" for i, line in enumerate(page)]
            footer = f"(Showing lines {offset}-{offset + len(page) - 1} of {len(lines)})"

            return {
                "path": path,
                "content": "\n".join(prefixed),
                "total_lines": len(lines),
                "has_more": has_more,
                "footer": footer,
            }
        except Exception as e:
            return {"error": str(e)}

    def write_file(self, path: str, data: str, mkdirp: bool = True) -> Dict:
        """Escribe archivo"""
        filepath = Path(path) if Path(path).is_absolute() else self.root / path
        if mkdirp:
            filepath.parent.mkdir(parents=True, exist_ok=True)

        try:
            filepath.write_text(data, encoding="utf-8")
            return {"success": True, "path": str(filepath)}
        except Exception as e:
            return {"error": str(e)}

    def list_dir(self, path: str = "", recursive: bool = False, max_depth: int = 5) -> Dict:
        """Lista directorio"""
        dirpath = self.root / path if path else self.root
        if not dirpath.exists():
            return {"error": f"Directory not found: {path}"}

        exclude_dirs = {'.git', 'node_modules', '__pycache__', 'venv', '.venv', '.tox', 'dist', 'build', '.mypy_cache', '.pytest_cache'}
        entries = []

        if recursive:
            for p in dirpath.rglob("*"):
                rel_parts = p.relative_to(self.root).parts
                if any(part in exclude_dirs for part in rel_parts):
                    continue
                if len(rel_parts) > max_depth:
                    continue
                rel = str(p.relative_to(self.root))
                entries.append({"path": rel, "type": "dir" if p.is_dir() else "file"})
        else:
            for p in dirpath.iterdir():
                if p.name in exclude_dirs:
                    continue
                rel = str(p.relative_to(self.root))
                entries.append({"path": rel, "type": "dir" if p.is_dir() else "file"})

        return {"entries": entries, "count": len(entries)}


class ExecuteTools:
    """Herramientas de ejecucion"""

    def __init__(self):
        from src.tools.persistent_shell import PersistentShell
        self.shell = PersistentShell.get_instance()

    async def execute_command(self, command: str, cwd: Optional[str] = None, timeout: int = 60) -> Dict:
        """Ejecuta comando shell usando persistent shell"""
        try:
            timeout_ms = timeout * 1000
            stdout, stderr, exit_code, interrupted = await self.shell.exec(command, timeout_ms)
            return {
                "success": exit_code == 0 and not interrupted,
                "stdout": stdout[:5000],
                "stderr": stderr[:5000],
                "returncode": exit_code,
                "interrupted": interrupted,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class ParseTools:
    """Herramientas de parseo de archivos"""

    def parse_file(self, path: str) -> Dict:
        """Parsea archivo segun extension"""
        filepath = Path(path)
        if not filepath.exists():
            return {"error": f"File not found: {path}"}

        if filepath.stat().st_size > 5 * 1024 * 1024:
            return {"error": f"File too large (>5MB): {path}"}

        ext = filepath.suffix.lower()
        try:
            content = filepath.read_text(encoding="utf-8")

            if ext in (".json",):
                return {"success": True, "format": "json", "data": json.loads(content)}
            elif ext in (".md", ".txt", ".py", ".js", ".ts", ".html", ".css", ".yaml", ".yml", ".toml", ".env", ".sh", ".dockerfile", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".rb"):
                return {"success": True, "format": "text", "content": content[:5000]}
            else:
                return {"success": True, "format": "unknown", "size": filepath.stat().st_size}
        except Exception as e:
            return {"error": str(e)}
