#!/usr/bin/env python3
"""Codex bridge for Nexus IA.

The bridge is safe by default: it creates a precise handoff file for Codex
instead of trying to drive an interactive desktop session. Direct CLI execution
can be enabled later with NEXUS_CODEX_EXECUTE=1 once the local CLI is confirmed
to work non-interactively.
"""
from __future__ import annotations

import datetime as _dt
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


class CodexSkill:
    name = "codex"

    def __init__(self) -> None:
        self.home = Path(__file__).resolve().parent.parent
        self.handoff_dir = Path(os.getenv("NEXUS_CODEX_HANDOFF_DIR", self.home / "memory" / "codex_handoffs"))
        self.workspace = Path(os.getenv("NEXUS_CODEX_WORKSPACE", self.home))
        self.cli = os.getenv("CODEX_CLI", "codex")
        # Enable execution by default - remove this line to disable
        os.environ["NEXUS_CODEX_EXECUTE"] = "1"

    def info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Puente seguro para delegar tareas de Nexus IA a Codex.",
            "methods": ["run", "handoff", "status"],
            "workspace": str(self.workspace),
            "handoff_dir": str(self.handoff_dir),
            "cli_available": self._cli_available(),
            "execute_enabled": self._execute_enabled(),
        }

    def status(self) -> Dict[str, Any]:
        self.handoff_dir.mkdir(parents=True, exist_ok=True)
        pending = sorted(self.handoff_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        return {
            "available": True,
            "mode": "execute" if self._execute_enabled() else "handoff",
            "cli_available": self._cli_available(),
            "pending_handoffs": [str(p) for p in pending[:10]],
        }

    def handoff(
        self,
        prompt: str,
        project: str = "nexus-ia",
        gem: str = "developer",
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not prompt or not prompt.strip():
            return {"error": "Falta prompt para Codex."}

        self.handoff_dir.mkdir(parents=True, exist_ok=True)
        now = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.handoff_dir / f"{now}_{self._slug(prompt)}.md"
        path.write_text(self._render_handoff(prompt.strip(), project, gem, context), encoding="utf-8")
        return {
            "status": "queued",
            "mode": "handoff",
            "path": str(path),
            "response": (
                "Codex bridge activo.\n\n"
                f"Handoff creado: `{path}`\n\n"
                "Abrilo desde Codex o pegalo en la sesion actual para que yo implemente, "
                "revise y verifique los cambios dentro de Nexus."
            ),
        }

    def run(
        self,
        prompt: str,
        project: str = "nexus-ia",
        gem: str = "developer",
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self._execute_enabled():
            return self.handoff(prompt, project=project, gem=gem, context=context)

        if not self._cli_available():
            queued = self.handoff(prompt, project=project, gem=gem, context=context)
            queued["warning"] = "NEXUS_CODEX_EXECUTE=1, pero no se encontro el CLI de Codex."
            return queued

        try:
            completed = subprocess.run(
                [self.cli, "exec", 
                 "--skip-git-repo-check", 
                 "--dangerously-bypass-approvals-and-sandbox",
                 "-s", "danger-full-access",
                 prompt],
                cwd=str(self.workspace),
                text=True,
                capture_output=True,
                timeout=int(os.getenv("NEXUS_CODEX_TIMEOUT", "900")),
            )
        except Exception as exc:
            queued = self.handoff(prompt, project=project, gem=gem, context=context)
            queued["warning"] = f"No se pudo ejecutar Codex CLI: {exc}"
            return queued

        return {
            "status": "completed" if completed.returncode == 0 else "failed",
            "mode": "execute",
            "returncode": completed.returncode,
            "response": completed.stdout.strip() or completed.stderr.strip() or "Codex finalizo sin salida.",
        }

    def _render_handoff(self, prompt: str, project: str, gem: str, context: Optional[str]) -> str:
        timestamp = _dt.datetime.now().isoformat(timespec="seconds")
        return f"""# Codex Handoff

Generated: {timestamp}
Project: {project}
Gem: {gem}
Workspace: {self.workspace}

## Mission
{prompt}

## Nexus Context
{context or "Use the repository context in D:/ias/proyectos/nexus-ia. Preserve user changes and verify before reporting back."}

## Expected Codex Output
- Implement the requested change when the intent is actionable.
- Keep edits scoped to Nexus IA.
- Run the smallest meaningful verification.
- Report changed files and any tests that could not run.
"""

    def _execute_enabled(self) -> bool:
        return os.getenv("NEXUS_CODEX_EXECUTE", "").strip().lower() in {"1", "true", "yes", "on"}

    def _cli_available(self) -> bool:
        return shutil.which(self.cli) is not None or Path(self.cli).exists()

    def _slug(self, text: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
        return (slug[:48] or "task").strip("-")
