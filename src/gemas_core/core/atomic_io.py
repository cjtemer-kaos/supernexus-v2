"""Atomic JSON and text file writes.

Pattern ported from pewdiepie-archdaemon/odysseus
(``core/atomic_io.py``): write to a sibling tmp file, fsync, then
``os.replace`` into place. On POSIX and modern Windows the rename is
atomic on the same filesystem.

Use this everywhere a JSON or text config file is persisted. A plain
``open(path, "w") + json.dump`` truncates the file on first write and
only fills it with new content afterwards — a kill -9 / power loss /
OOM in between produces a truncated or empty file. For password DBs,
session stores, and live state, that's a data-loss event.

The temp filename uses the live PID and thread id as a suffix so
concurrent writers (multiple processes, or multiple threads in the
same process — e.g. async FastAPI handlers) don't collide on the
rename target. The last ``os.replace`` to run wins, which is the
standard contract.

On any error after the temp file is created, the temp file is
cleaned up before the exception propagates — no orphaned ``.tmp.*``
files are left behind.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Union

__all__ = ["atomic_write_json", "atomic_write_text"]

PathLike = Union[str, os.PathLike[str]]


def _resolve_dir(path: PathLike) -> str:
    """Return the parent directory for *path* (or ``"."`` for bare names)."""
    parent = os.path.dirname(os.fspath(path))
    return parent or "."


def _tmp_suffix() -> str:
    """Unique-per-writer suffix combining pid and thread id."""
    return f".tmp.{os.getpid()}.{threading.get_ident()}"


def _atomic_write(path: PathLike, payload: str) -> None:
    """Internal: write *payload* to *path* atomically, cleaning up on error."""
    parent = _resolve_dir(path)
    os.makedirs(parent, exist_ok=True)
    tmp = f"{os.fspath(path)}{_tmp_suffix()}"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        # On any failure (write error, fsync error, replace error, even
        # KeyboardInterrupt), drop the tmp file so we don't leave garbage
        # in the target directory. The original file (if any) is preserved
        # because os.replace never ran.
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_text(path: PathLike, text: str) -> None:
    """Atomically persist *text* at *path*.

    Writes to ``<path>.tmp.<pid>.<tid>``, fsyncs the file descriptor, then
    renames into place. The original file (if any) is preserved until
    the rename succeeds.
    """
    _atomic_write(path, text)


def atomic_write_json(path: PathLike, data: Any, *, indent: int | None = None) -> None:
    """Atomically persist *data* as JSON at *path*.

    *indent* follows :func:`json.dump` semantics: ``None`` (default)
    produces compact single-line output, an integer produces pretty
    multi-line output.
    """
    payload = json.dumps(data, indent=indent)
    _atomic_write(path, payload)
