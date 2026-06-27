"""
atomic_io — Safe atomic writes for config / state files.

Pattern (odysseus atomic_io.py): every write goes to a unique tempfile
in the SAME DIRECTORY (so rename is atomic on the same filesystem) and
then os.replace into the target path. A crash mid-write leaves either
the old file intact OR the new file intact — never a half-written one.

Use whenever you persist anything you cannot lose / cannot re-derive:
    - secret keys (token_secret.key)
    - auth DB exports / backups
    - setup state (~/.nexus/setup.json — already migrated)
    - user preferences
    - long-lived caches

NOT needed for append-only logs (JSONL line-buffered) or SQLite DBs
(SQLite has its own WAL+journal).

API:
    atomic_write_text(path, text)
    atomic_write_bytes(path, data)
    atomic_write_json(path, obj, indent=2)
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Union

PathLike = Union[str, Path]


def _ensure_parent(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)


def atomic_write_bytes(path: PathLike, data: bytes, *, mode: int = 0o600) -> Path:
    """Atomic-replace `path` with `data`. Returns the final path.

    `mode` defaults to 0o600 (owner read/write only) — safe-by-default
    for secrets. Override for less-sensitive files if needed (e.g.
    setup.json could pass mode=0o644 but 0o600 is fine and stricter).
    """
    p = Path(path)
    _ensure_parent(p)
    # mkstemp in the SAME directory guarantees rename atomicity (same FS).
    fd, tmp = tempfile.mkstemp(
        dir=str(p.parent),
        prefix=f".{p.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            try:
                os.fsync(f.fileno())   # durable before rename
            except OSError:
                pass  # not supported on all FS (e.g. some network mounts)
        try:
            os.chmod(tmp, mode)
        except OSError:
            pass  # Windows often ignores; non-fatal
        os.replace(tmp, p)
    except Exception:
        # Make sure the tempfile doesn't linger on failure
        try:
            os.unlink(tmp)
        except Exception:
            pass
        raise
    return p


def atomic_write_text(path: PathLike, text: str, *, encoding: str = "utf-8",
                      mode: int = 0o600) -> Path:
    """UTF-8 by default; pass `encoding` only if you have a real reason."""
    return atomic_write_bytes(path, text.encode(encoding), mode=mode)


def atomic_write_json(path: PathLike, obj: Any, *, indent: int = 2,
                      mode: int = 0o600, ensure_ascii: bool = False) -> Path:
    """Serialize obj as JSON and atomic-write. `default=str` so dataclasses /
    Path / datetime survive serialization (best-effort)."""
    payload = json.dumps(obj, indent=indent, ensure_ascii=ensure_ascii, default=str)
    return atomic_write_text(path, payload, mode=mode)
