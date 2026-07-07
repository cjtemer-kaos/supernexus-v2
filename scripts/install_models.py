#!/usr/bin/env python
"""Auto-install NEXUS Ollama models from data/models/*/Modelfile.

Called on first boot (or manually) to ensure the project's bundled models
exist in the user's local Ollama. Idempotent: skips models already present.
"""
from __future__ import annotations
import subprocess
import sys
import json
from pathlib import Path

# Windows: suppress console windows for child processes (ollama, etc.)
_CREATIONFLAGS = 0
_STARTUPINFO = None
if sys.platform == "win32":
    _CREATIONFLAGS = 0x08000000 | 0x00000008  # CREATE_NO_WINDOW | DETACHED_PROCESS
    _STARTUPINFO = subprocess.STARTUPINFO()
    _STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _STARTUPINFO.wShowWindow = 0

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "data" / "models"
DIRECTOR_V6_DIR = ROOT / "models" / "nexus-director-v6"
MIN_GGUF_BYTES = 100 * 1024 * 1024


def installed_models() -> set[str]:
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5, creationflags=_CREATIONFLAGS, startupinfo=_STARTUPINFO)
        if r.returncode != 0:
            return set()
        lines = r.stdout.strip().splitlines()[1:]  # skip header
        return {line.split()[0] for line in lines if line.strip()}
    except Exception as e:
        print(f"[install_models] ollama not reachable: {e}")
        return set()


def install_one(name: str, modelfile: Path) -> bool:
    print(f"[install_models] creating {name} from {modelfile.relative_to(ROOT)}...")
    try:
        r = subprocess.run(
            ["ollama", "create", name, "-f", str(modelfile)],
            capture_output=True, text=True, timeout=300,
            creationflags=_CREATIONFLAGS,
            startupinfo=_STARTUPINFO,
        )
        if r.returncode == 0:
            print(f"[install_models] OK {name}")
            return True
        print(f"[install_models] FAILED {name}: {r.stderr.strip()[:200]}")
        return False
    except Exception as e:
        print(f"[install_models] ERROR {name}: {e}")
        return False


def _register_director_v6(installed: set[str]) -> bool:
    """Register nexus-director-v6 from models/nexus-director-v6/ if GGUF is present."""
    name = "nexus-director-v6"
    if name in installed:
        print(f"[install_models] director-v6 already registered")
        return True
    modelfile = DIRECTOR_V6_DIR / "Modelfile"
    gguf = DIRECTOR_V6_DIR / f"{name}-Q8_0.gguf"
    if not modelfile.exists():
        print(f"[install_models] director-v6 Modelfile not found")
        return False
    if not gguf.exists() or gguf.stat().st_size < MIN_GGUF_BYTES:
        print(f"[install_models] director-v6 GGUF missing — run 'git lfs pull'")
        return False
    return install_one(name, modelfile)


def main() -> int:
    # Skip entirely if marker file exists (all models already installed)
    marker = ROOT / "data" / ".models_installed"
    if marker.exists():
        print(f"[install_models] marker exists, skipping")
        return 0

    installed = installed_models()
    print(f"[install_models] {len(installed)} models already installed")

    created = []
    skipped = []
    failed = []

    # Bundled models from data/models/
    if MODELS_DIR.exists():
        for model_dir in MODELS_DIR.iterdir():
            if not model_dir.is_dir():
                continue
            modelfile = model_dir / "Modelfile"
            if not modelfile.exists():
                continue
            name = model_dir.name
            candidates = {name, f"{name}:latest"}
            if candidates & installed:
                skipped.append(name)
                continue
            if install_one(name, modelfile):
                created.append(name)
            else:
                failed.append(name)

    # Director-V6 from models/nexus-director-v6/
    if _register_director_v6(installed):
        created.append("nexus-director-v6")
    else:
        failed.append("nexus-director-v6")

    print(f"[install_models] created={len(created)} skipped={len(skipped)} failed={len(failed)}")
    if not failed:
        marker.write_text("ok", encoding="utf-8")
        print(f"[install_models] marker written — future starts will skip")
    if failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
