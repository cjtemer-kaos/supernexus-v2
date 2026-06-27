"""
LLMRoleGema — Dispatcher Ollama genérico para gemas definidas solo por manifest.

Las gemas role-LLM (code, architect, debugger, etc.) NO tienen código propio:
solo un manifest JSON con system_prompt + modelo. Esta clase las dispatcha
a Ollama usando el system_prompt del manifest.

Las gemas con worker Python dedicado (ayuda, scholar, sage, biblioteca)
sobrescriben en el caller — ver builders.build_standard_gemas().
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from .base import GemaBase, GemaManifest

logger = logging.getLogger("gemas-core.role-gema")


class LLMRoleGema(GemaBase):
    """Gema LLM-as-role basada en un manifest JSON.

    Carga metadata desde data/gemas/<name>.json y dispatcha a Ollama
    con el system_prompt del manifest.
    """

    def __init__(
        self,
        manifest_path: Path,
        ollama_url: str = "http://127.0.0.1:11434",
        timeout_s: int = 120,
    ):
        self.manifest_path = Path(manifest_path)
        self.manifest: GemaManifest = GemaManifest.from_file(self.manifest_path)
        self.name = self.manifest.name
        self.model = self.manifest.model
        self.description = self.manifest.description
        self.system_prompt: str = self.manifest.system_prompt
        self.keywords: List[str] = self.manifest.keywords
        self.category: str = self.manifest.category
        self.ollama_url = ollama_url.rstrip("/")
        self.timeout_s = timeout_s
        # Build a default system prompt if manifest is bare
        if not self.system_prompt:
            self.system_prompt = self._build_default_prompt()

    def _build_default_prompt(self) -> str:
        """Genera un system_prompt por defecto si el manifest no incluye uno."""
        return (
            f"Eres {self.name.upper()}, una gema especializada de NEXUS.\n"
            f"Rol: {self.description}\n"
            f"Categoria: {self.category}\n"
            f"Responde en espanol, con precision tecnica, sin rodeos. "
            f"Si no tienes la informacion, dilo claramente."
        )

    @property
    def use_checkpoint_contract(self) -> bool:
        return self.manifest.use_checkpoint_contract

    def _checkpoint_prompt(self) -> str:
        path = Path(__file__).resolve().parent.parent / "core" / "checkpoint_prompt.md"
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        """Ejecuta la gema: manda el task a Ollama con el system_prompt del rol."""
        import aiohttp
        prompt = task
        if context:
            prompt = f"{context}\n\n---\nTarea: {task}"

        system = self.system_prompt
        if self.use_checkpoint_contract:
            cp = self._checkpoint_prompt()
            if cp:
                system = f"{system}\n\n{cp}"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout_s),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        raw_output = data.get("response", "").strip()
                        if self.use_checkpoint_contract:
                            return self._build_checkpoint_result(task, raw_output)
                        return {
                            "success": True,
                            "gema": self.name,
                            "model": self.model,
                            "category": self.category,
                            "task": task,
                            "output": raw_output,
                            "tokens": data.get("eval_count", 0),
                        }
                    text = await resp.text()
                    return {
                        "success": False,
                        "gema": self.name,
                        "error": f"ollama http {resp.status}: {text[:200]}",
                    }
        except Exception as e:
            logger.warning(
                f"LLMRoleGema {self.name} ollama error: {type(e).__name__}: {e}"
            )
            return {
                "success": False,
                "gema": self.name,
                "error": f"{type(e).__name__}: {e}",
                "note": "ollama unavailable - check NEXUS_OLLAMA_URL or local ollama service",
            }

    def _build_checkpoint_result(self, task: str, raw_output: str) -> Dict[str, Any]:
        from src.core.checkpoint_contract import parse_llm_response, validate_report
        from src.core.checkpoint_metrics import record as record_metric
        report = parse_llm_response(raw_output)
        valid, errors = validate_report(report)
        vague_rejected = not valid and any("vague" in e.lower() for e in errors)
        record_metric(self.name, valid, vague_rejected)
        result: Dict[str, Any] = {
            "success": True,
            "gema": self.name,
            "task": task,
            "checkpoint": True,
            "report": report.to_dict(),
            "report_valid": valid,
            "raw": raw_output,
        }
        if errors:
            result["validation_errors"] = errors
            logger.warning(f"Checkpoint validation for {self.name}: {errors}")
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Serializa metadata para listar en UI/API."""
        d = self.manifest.to_dict()
        d.update({
            "id": self.name,
            "name": self.name.upper(),
            "model": self.model,
            "keywords": self.keywords,
            "type": "llm-role",
            "has_system_prompt": bool(self.manifest.system_prompt),
        })
        return d


def load_all_role_gemas(
    gemas_dir: Path,
    ollama_url: str = "http://127.0.0.1:11434",
    timeout_s: int = 120,
) -> Dict[str, LLMRoleGema]:
    """Carga todos los manifests en data/gemas/*.json como LLMRoleGema.

    Retorna dict {nombre: instancia}. Las gemas con worker Python dedicado
    (ayuda, scholar, sage, biblioteca) deben sobreescribir en el caller.

    Args:
        gemas_dir: Path al directorio con manifests (data/gemas/).
        ollama_url: URL del servidor Ollama.
        timeout_s: Timeout por request Ollama.
    """
    out: Dict[str, LLMRoleGema] = {}
    gemas_dir = Path(gemas_dir)
    if not gemas_dir.exists():
        logger.warning(f"gemas_dir not found: {gemas_dir}")
        return out
    for f in sorted(gemas_dir.glob("*.json")):
        try:
            instance = LLMRoleGema(
                manifest_path=f,
                ollama_url=ollama_url,
                timeout_s=timeout_s,
            )
            out[instance.name] = instance
        except Exception as e:
            logger.error(f"failed loading {f}: {e}")
    return out
