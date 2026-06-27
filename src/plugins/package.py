"""
package — .nexus-gema bundle format (import/export).

Pattern (openakita .akita-agent spec): ZIP container that ships a gema +
optional skills + manifest + integrity checksum. Operator drops the file
into ~/.nexus/gemas/ via the import endpoint and it's loaded next reload.

Layout (inside ZIP):
    manifest.json   metadata: name, version, author, sha256_of(gema.py)
    gema.py         the actual MANIFEST + handler
    README.md       optional, displayed in import UI
    skills/         optional, copied into ~/.nexus/skills/<name>/
"""
from __future__ import annotations

import hashlib
import json
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


SPEC_VERSION = "1.0"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def export_gema(name: str, source_path: Path, *, author: str = "anonymous",
                version: str = "1.0.0", out_dir: Optional[Path] = None,
                readme: str = "") -> Path:
    """Bundle one .py gema into a .nexus-gema ZIP at out_dir.
    Returns the created path."""
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    if out_dir is None:
        out_dir = Path.home() / ".nexus" / "gemas-exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    pkg_path = out_dir / f"{name}.nexus-gema"
    gema_bytes = source_path.read_bytes()
    manifest = {
        "spec_version": SPEC_VERSION,
        "name": name,
        "version": version,
        "author": author,
        "created_at": datetime.now().isoformat(),
        "sha256_gema": _sha256(gema_bytes),
    }
    with zipfile.ZipFile(pkg_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
        z.writestr("gema.py", gema_bytes)
        if readme:
            z.writestr("README.md", readme)
    return pkg_path


class PackageError(Exception):
    pass


def import_gema(package_path: Path, *, target_dir: Optional[Path] = None,
                verify_signature: bool = False) -> Dict[str, Any]:
    """Verify and install a .nexus-gema bundle into target_dir
    (defaults to ~/.nexus/gemas/).

    Verification steps:
      1. spec_version matches
      2. sha256 of gema.py matches manifest
      3. prompt-injection scanner on gema.py
      4. (opt) Ed25519 signature if present and verify_signature=True

    Returns dict with {ok, name, path, sha256, warnings, scan_summary}.
    Raises PackageError on any blocking failure.
    """
    if target_dir is None:
        target_dir = Path.home() / ".nexus" / "gemas"
    target_dir.mkdir(parents=True, exist_ok=True)

    if not package_path.exists():
        raise PackageError(f"package not found: {package_path}")

    try:
        with zipfile.ZipFile(package_path, "r") as z:
            names = set(z.namelist())
            if "manifest.json" not in names or "gema.py" not in names:
                raise PackageError("missing manifest.json or gema.py")
            manifest = json.loads(z.read("manifest.json").decode("utf-8"))
            gema_bytes = z.read("gema.py")
            readme = z.read("README.md").decode("utf-8") if "README.md" in names else ""
    except zipfile.BadZipFile as e:
        raise PackageError(f"not a valid ZIP: {e}")

    # 1. spec
    if manifest.get("spec_version") != SPEC_VERSION:
        raise PackageError(f"unsupported spec_version: {manifest.get('spec_version')!r}")

    # 2. hash
    actual = _sha256(gema_bytes)
    if actual != manifest.get("sha256_gema"):
        raise PackageError(
            f"sha256 mismatch: manifest={manifest.get('sha256_gema')!r} actual={actual!r}"
        )

    # 3. prompt injection scan
    warnings = []
    try:
        from src.security.prompt_scanner import scan_prompt_content, has_blocking_hit, summarize_hits
        hits = scan_prompt_content(gema_bytes.decode("utf-8", errors="replace"),
                                   source=package_path.name)
        scan_summary = summarize_hits(hits) if hits else "clean"
        if has_blocking_hit(hits):
            raise PackageError(f"REFUSED by prompt scanner: {scan_summary}")
        if hits:
            warnings.append(f"non-blocking scanner hits: {scan_summary}")
    except PackageError:
        raise
    except Exception as e:
        scan_summary = f"scanner unavailable: {e}"

    # 4. optional signature (Ed25519 — see commit 45)
    if verify_signature:
        try:
            from src.security.signer import verify_gema_package
            ok, reason = verify_gema_package(manifest, gema_bytes)
            if not ok:
                raise PackageError(f"signature verification failed: {reason}")
        except ImportError:
            warnings.append("signature verification requested but signer unavailable")

    # 5. install — destination filename = manifest.name + .py
    name = manifest.get("name", "").strip()
    if not name or not name.replace("_", "").replace("-", "").isalnum():
        raise PackageError(f"invalid name: {name!r}")
    dest = target_dir / f"{name}.py"
    if dest.exists():
        warnings.append(f"overwriting existing {dest.name}")
    dest.write_bytes(gema_bytes)

    return {
        "ok": True,
        "name": name,
        "version": manifest.get("version"),
        "author": manifest.get("author"),
        "path": str(dest),
        "sha256": actual,
        "readme": readme[:500] if readme else "",
        "scan_summary": scan_summary,
        "warnings": warnings,
    }
