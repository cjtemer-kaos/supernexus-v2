"""Plugin manifest loader — descubre gemas y otros plugins por archivo.

Pattern (inspirado en claude-code/plugins/):
    Cada plugin = 1 archivo .py con un dict MANIFEST.
    Loader importa cada archivo, lee MANIFEST, lo agrega al registry.
    Errores aislados — un plugin roto no rompe la carga del resto.

Para gemas:
    src/plugins/gemas/code.py:
        MANIFEST = {
            "name": "code",
            "tags": ["programming", "code-review"],
            "description": "Programacion y refactoring",
            "model": "qwen2.5-coder:7b",
        }
        # opcional:
        # async def handle(task, context, app) -> str: ...
"""
from __future__ import annotations

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


REQUIRED_GEMA_FIELDS = {"name", "tags", "description", "model"}


class GemaPlugin:
    """Wrapper de una gema cargada desde su archivo plugin."""

    def __init__(self, manifest: Dict[str, Any], handler: Optional[callable] = None,
                 source_file: str = ""):
        self.name: str = manifest["name"]
        self.tags: List[str] = list(manifest.get("tags", []))
        self.description: str = manifest.get("description", "")
        self.preferred_model: str = manifest.get("model", "")
        # Agency-agents inspired fields (from divisions.json pattern)
        self.icon: str = manifest.get("icon", "")
        self.color: str = manifest.get("color", "")
        self.division: str = manifest.get("division", "")
        self.personality: str = manifest.get("personality", "")
        self.workflow: str = manifest.get("workflow", "")
        # Capability declarations (openfang pattern, MVP — declaration only,
        # enforcement is a separate step). Free-form strings, recommended:
        #   "net.fetch"      outbound HTTP
        #   "fs.read.user"   read under user home / project root
        #   "fs.write.user"  write under user home / project root
        #   "shell.exec"     spawn subprocesses
        #   "mcp.call"       invoke MCP tools
        #   "llm.cloud"      call paid cloud LLM (cost-bearing)
        #   "memory.write"   persist into nexus_memory.db
        # Default: empty list = no declared capabilities (minimal-privilege).
        self.capabilities: List[str] = list(manifest.get("capabilities", []))
        self.handler = handler
        self.source_file = source_file
        self._manifest = manifest

    def has_capability(self, cap: str) -> bool:
        """True if gema declared `cap` (or a parent prefix). 'net.fetch' is
        granted when manifest declares 'net' or 'net.fetch'."""
        for declared in self.capabilities:
            if cap == declared or cap.startswith(declared + "."):
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "tags": self.tags,
            "description": self.description,
            "preferred_model": self.preferred_model,
            "capabilities": list(self.capabilities),
            "has_handler": self.handler is not None,
            "source_file": self.source_file,
        }

    def __repr__(self) -> str:
        return f"<GemaPlugin {self.name!r} model={self.preferred_model!r}>"


def _validate_gema_manifest(manifest: Any, source: str) -> Optional[str]:
    """Devuelve None si OK, str con razon si invalido."""
    if not isinstance(manifest, dict):
        return f"{source}: MANIFEST must be dict, got {type(manifest).__name__}"
    missing = REQUIRED_GEMA_FIELDS - set(manifest.keys())
    if missing:
        return f"{source}: missing required fields {sorted(missing)}"
    if not isinstance(manifest.get("tags"), list):
        return f"{source}: 'tags' must be a list"
    if not manifest.get("name"):
        return f"{source}: 'name' empty"
    return None


def load_gemas(plugins_dir: Optional[Path] = None) -> Dict[str, GemaPlugin]:
    """Carga todas las gemas desde src/plugins/gemas/ (canonical),
    src/gemas_client_overrides/ (fork-cliente, FORK_STANDARD.md R2) Y
    desde ~/.nexus/gemas/ (user-level overlay, openakita pattern).

    Cada archivo .py (excepto __init__.py) se importa y se busca MANIFEST.

    Orden de precedencia (last wins por nombre):
        1. src/plugins/gemas/                (canonical core)
        2. src/gemas_client_overrides/       (client fork code — preserved by sync)
        3. ~/.nexus/gemas/                   (user overlay)

    Errores por archivo se loguean pero NO interrumpen la carga del resto.
    Todos pasan por el prompt-injection scanner antes de importar.

    Args:
        plugins_dir: si None, usa src/plugins/gemas/. Util para tests.

    Returns:
        Dict {gema_name: GemaPlugin}. Vacio si ningún dir existe.
    """
    if plugins_dir is None:
        plugins_dir = Path(__file__).parent / "gemas"

    # Client-overrides dir — opt-in por su sola existencia. Vive junto a
    # src/plugins/, en src/gemas_client_overrides/. Ver FORK_STANDARD.md
    # secciones 2 y 3.R2. El sync_gemas_core.py NUNCA lo toca.
    src_dir = Path(__file__).resolve().parent.parent  # .../src/
    client_overrides_dir = src_dir / "gemas_client_overrides"

    # User-level overlay dir — opt-in by simply existing. Loaded AFTER the
    # canonical dir so user gemas override builtins with the same name.
    user_dir = Path.home() / ".nexus" / "gemas"

    if (
        not plugins_dir.exists()
        and not client_overrides_dir.exists()
        and not user_dir.exists()
    ):
        logger.warning(f"Plugin dir not found: {plugins_dir} (and no client/user overlays)")
        return {}

    gemas: Dict[str, GemaPlugin] = {}
    errors: List[str] = []

    # If the dir is the canonical src/plugins/gemas, use the standard module path
    # so reload + dependencies work correctly. Otherwise load via importlib.util
    # (used for tests, custom plugin dirs, etc).
    canonical_dir = Path(__file__).parent / "gemas"
    is_canonical = plugins_dir.resolve() == canonical_dir.resolve()

    # Lazy import to avoid a hard dependency cycle during package init.
    try:
        from src.security.prompt_scanner import (
            scan_prompt_content, has_blocking_hit, summarize_hits,
        )
        _scanner_available = True
    except Exception:
        _scanner_available = False

    try:
        from src.security.medusa_scan import scan_text, has_blocking_hit as medusa_blocking, summary as medusa_summary
        _medusa_available = True
    except Exception:
        _medusa_available = False

    # Passes en orden: canonical → client overrides → user overlay.
    # last-write-wins por nombre de gema.
    dirs_to_scan: List[Path] = []
    seen_paths = set()

    def _maybe_add(d: Path) -> None:
        if not d.exists():
            return
        rp = d.resolve()
        if rp in seen_paths:
            return
        seen_paths.add(rp)
        dirs_to_scan.append(d)

    _maybe_add(plugins_dir)
    _maybe_add(client_overrides_dir)
    _maybe_add(user_dir)

    for current_dir in dirs_to_scan:
        is_canonical_now = current_dir.resolve() == canonical_dir.resolve()
        is_client_now = current_dir.resolve() == client_overrides_dir.resolve()
        if is_canonical_now:
            origin_tag = "builtin"
        elif is_client_now:
            origin_tag = "client_override"
        else:
            origin_tag = "user"
        for py_file in sorted(current_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue  # __init__.py et al

            # Security pre-check (openfang pattern): scan the raw source before
            # importing. A HIGH-severity hit refuses to import the file at all —
            # we'd rather lose one gema than load a malicious one. MEDIUM/LOW
            # just log; the gema still loads.
            if _scanner_available:
                try:
                    raw = py_file.read_text(encoding="utf-8", errors="replace")
                    hits = scan_prompt_content(raw, source=str(py_file))
                    if hits:
                        summary = summarize_hits(hits)
                        if has_blocking_hit(hits):
                            top = next(h for h in hits if h.severity.value == "high")
                            msg = (f"{py_file.name}: REFUSED — prompt-injection "
                                   f"scanner: {summary} (top: {top.category} :: "
                                   f"'{top.excerpt}')")
                            errors.append(msg)
                            logger.error(f"[plugins/security] {msg}")
                            try:
                                from src.observability.event_stream import emit, EventType
                                emit(EventType.GEMA_LOAD_REFUSED_SCAN,
                                     data={"file": py_file.name,
                                           "category": top.category,
                                           "excerpt": top.excerpt,
                                           "summary": summary,
                                           "origin": origin_tag},
                                     source="plugins.manifest")
                            except Exception:
                                pass
                            continue
                        else:
                            logger.warning(
                                f"[plugins/security] {py_file.name}: {summary} "
                                f"(non-blocking, loading anyway)"
                            )
                except Exception as e:
                    logger.warning(f"[plugins/security] scan failed for {py_file.name}: {e}")

            # MEDUSA defense layer — skip for builtin gemas (false positives on security patterns)
            if _medusa_available and not is_canonical_now:
                try:
                    raw = py_file.read_text(encoding="utf-8", errors="replace")
                    mhits = scan_text(raw)
                    if mhits:
                        msummary = medusa_summary(mhits)
                        if medusa_blocking(mhits):
                            msg = (f"{py_file.name}: REFUSED — MEDUSA scanner: {msummary}")
                            errors.append(msg)
                            logger.error(f"[plugins/medusa] {msg}")
                            continue
                        else:
                            logger.warning(
                                f"[plugins/medusa] {py_file.name}: {msummary} "
                                f"(non-blocking, loading anyway)"
                            )
                except Exception as e:
                    logger.warning(f"[plugins/medusa] scan failed for {py_file.name}: {e}")

            try:
                if is_canonical_now:
                    module_name = f"src.plugins.gemas.{py_file.stem}"
                    if module_name in importlib.sys.modules:
                        mod = importlib.reload(importlib.sys.modules[module_name])
                    else:
                        mod = importlib.import_module(module_name)
                elif is_client_now:
                    # Client overrides — usar el module path estable para que
                    # las gemas puedan hacer `from src.gemas_client_overrides...`
                    # entre ellas sin colisión de caché.
                    module_name = f"src.gemas_client_overrides.{py_file.stem}"
                    if module_name in importlib.sys.modules:
                        mod = importlib.reload(importlib.sys.modules[module_name])
                    else:
                        mod = importlib.import_module(module_name)
                else:
                    # Non-canonical dir (user overlay or test) — load by file path.
                    # spec_name disambiguated by dir id so multiple custom dirs
                    # with the same filename don't collide in importlib's cache.
                    spec_name = f"_plugin_{py_file.stem}_{id(current_dir)}"
                    spec = importlib.util.spec_from_file_location(spec_name, py_file)
                    if spec is None or spec.loader is None:
                        raise ImportError(f"could not create spec for {py_file}")
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
            except Exception as e:
                errors.append(f"{py_file.name}: import failed: {type(e).__name__}: {e}")
                logger.error(f"[plugins] {py_file.name}: import failed: {e}")
                continue

            manifest = getattr(mod, "MANIFEST", None)
            validation_error = _validate_gema_manifest(manifest, py_file.name)
            if validation_error:
                errors.append(validation_error)
                logger.error(f"[plugins] {validation_error}")
                continue

            handler = getattr(mod, "handle", None)
            plugin = GemaPlugin(
                manifest=manifest,
                handler=handler,
                source_file=str(py_file),
            )
            if plugin.name in gemas:
                logger.info(f"[plugins] '{plugin.name}' overridden by {origin_tag} version at {py_file}")
            gemas[plugin.name] = plugin

    logger.info(
        f"[plugins] loaded {len(gemas)} gemas (errors={len(errors)}) "
        f"from {len(dirs_to_scan)} dir(s): {[str(d) for d in dirs_to_scan]}"
    )
    return gemas


def list_gemas_summary(gemas: Dict[str, GemaPlugin]) -> List[Dict[str, Any]]:
    """Snapshot list-of-dicts para endpoints API."""
    return [g.to_dict() for g in gemas.values()]
