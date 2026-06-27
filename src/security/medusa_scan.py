"""MEDUSA pattern scanner — pre-load security check for 3rd-party gemas.

Usage from code:
    from src.security.medusa_scan import scan_text, has_blocking_hit, scan_file

Usage from CLI:
    python -m src.security.medusa_scan <path>
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

_PATTERNS_PATH = Path(__file__).parent / "medusa_patterns.json"
_patterns: List[dict] = []
_loaded = False


def _load_patterns() -> List[dict]:
    global _patterns, _loaded
    if _loaded:
        return _patterns
    try:
        raw = json.loads(_PATTERNS_PATH.read_text(encoding="utf-8"))
        _patterns = raw
    except Exception as e:
        logger.error(f"medusa_scan: failed to load patterns: {e}")
        _patterns = []
    _loaded = True
    return _patterns


@dataclass
class Hit:
    pattern_id: str
    severity: str
    category: str
    excerpt: str
    line: int


def scan_text(text: str) -> List[Hit]:
    patterns = _load_patterns()
    hits: List[Hit] = []
    for i, line in enumerate(text.splitlines(), 1):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        for p in patterns:
            try:
                if re.search(p["regex"], line_stripped, re.IGNORECASE):
                    hits.append(Hit(
                        pattern_id=p["id"],
                        severity=p.get("severity", "medium"),
                        category=p.get("category", "unknown"),
                        excerpt=line_stripped[:120],
                        line=i,
                    ))
            except re.error:
                continue
    return hits


def has_blocking_hit(hits: List[Hit]) -> bool:
    return any(h.severity == "high" for h in hits)


def scan_file(path: Path) -> List[Hit]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    return scan_text(raw)


def summary(hits: List[Hit]) -> str:
    if not hits:
        return "no hits"
    by_sev = {"high": 0, "medium": 0, "low": 0}
    for h in hits:
        by_sev[h.severity] = by_sev.get(h.severity, 0) + 1
    parts = []
    if by_sev["high"]:
        parts.append(f"{by_sev['high']} high")
    if by_sev["medium"]:
        parts.append(f"{by_sev['medium']} medium")
    if by_sev["low"]:
        parts.append(f"{by_sev['low']} low")
    return ", ".join(parts)


# CLI entry point
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m src.security.medusa_scan <path>")
        sys.exit(1)

    target = Path(sys.argv[1])
    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = list(target.rglob("*.py"))
    else:
        print(f"Not found: {target}")
        sys.exit(1)

    total = 0
    blocked = 0
    for f in files:
        hits = scan_file(f)
        total += 1
        if has_blocking_hit(hits):
            blocked += 1
            print(f"BLOCKED  {f.name}: {summary(hits)}")
        elif hits:
            print(f"WARNING  {f.name}: {summary(hits)}")
        else:
            print(f"CLEAN    {f.name}")

    print(f"\nScanned: {total} files, {blocked} blocked")
    sys.exit(0 if blocked == 0 else 1)
