"""
scratchpad — Persistent per-session working memory.

Pattern (openakita memory-redesign): MEMORY.md's 800-char limit is too
small for cross-session continuity. Scratchpad is a free-form markdown
file per session that survives compaction, restart, and can be auto-
injected into the next turn's context.

Storage: ~/.nexus/scratchpad/<session_id>.md  (atomic writes)
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

DEFAULT_MAX_CHARS = 8000   # 8KB cap; truncate oldest if exceeded
HEADER_FMT = "# Scratchpad: {sid}\n_Updated: {ts}_\n\n"


def _scratchpad_dir() -> Path:
    d = Path.home() / ".nexus" / "scratchpad"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path(session_id: str) -> Path:
    # session_id sanitization — avoid traversal
    safe = "".join(c for c in (session_id or "default")
                   if c.isalnum() or c in ("-", "_", "."))
    return _scratchpad_dir() / f"{safe or 'default'}.md"


def read(session_id: str) -> str:
    """Return the scratchpad content (empty string if missing)."""
    p = _path(session_id)
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"scratchpad read {p}: {e}")
        return ""


def write(session_id: str, content: str, *, max_chars: int = DEFAULT_MAX_CHARS) -> Path:
    """Overwrite the scratchpad with `content` (header re-rendered).
    Atomic — uses src.security.atomic_io. Truncates oldest if too long."""
    from src.security.atomic_io import atomic_write_text
    if len(content) > max_chars:
        content = content[-max_chars:]
    header = HEADER_FMT.format(sid=session_id, ts=datetime.now().isoformat(timespec="seconds"))
    body = content if content.startswith("# Scratchpad:") else header + content
    return atomic_write_text(_path(session_id), body, mode=0o644)


def append(session_id: str, line: str, *, max_chars: int = DEFAULT_MAX_CHARS) -> Path:
    """Append `line` (timestamped) to the scratchpad. Creates if missing."""
    existing = read(session_id)
    ts = datetime.now().strftime("%H:%M:%S")
    addition = f"- [{ts}] {line.rstrip()}\n"
    if not existing:
        header = HEADER_FMT.format(sid=session_id, ts=datetime.now().isoformat(timespec="seconds"))
        new = header + addition
    else:
        new = existing.rstrip() + "\n" + addition
    return write(session_id, new, max_chars=max_chars)


def clear(session_id: str) -> bool:
    p = _path(session_id)
    if p.exists():
        try:
            p.unlink()
            return True
        except Exception as e:
            logger.warning(f"scratchpad clear {p}: {e}")
    return False


def list_sessions() -> List[str]:
    """Return session_ids that have a scratchpad on disk."""
    d = _scratchpad_dir()
    return sorted(p.stem for p in d.glob("*.md"))


def as_context_block(session_id: str, *, max_chars: int = 2000) -> str:
    """Return a prompt-ready context block for injection. Empty string if
    the scratchpad is missing or too short to be useful (< 40 chars)."""
    raw = read(session_id)
    if len(raw) < 40:
        return ""
    body = raw[-max_chars:] if len(raw) > max_chars else raw
    return f"[Working memory from this session's scratchpad:]\n{body}"
