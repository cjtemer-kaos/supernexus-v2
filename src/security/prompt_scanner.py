"""
prompt_scanner — detecta intentos de prompt injection en contenido textual
antes de cargarlo en el sistema (gemas, skills, system prompts, manifests).

Pattern: openfang openfang-skills scan_prompt_content().

Uso:
    from src.security.prompt_scanner import scan_prompt_content, Severity
    hits = scan_prompt_content(text, source="src/plugins/gemas/foo.py")
    if any(h.severity == Severity.HIGH for h in hits):
        raise SecurityError(...)

Severidad:
    HIGH   = intento claro de override/exfil → bloquear carga
    MEDIUM = sospechoso, ambiguo → warn + log + permitir
    LOW    = ruido informativo (referencias a shell, urls, etc.) → debug log
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import List

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class ScanHit:
    severity: Severity
    category: str
    pattern: str
    excerpt: str  # 80 chars context
    source: str  # filename / origin label


# Each pattern: (severity, category, regex)
# - HIGH patterns trigger blocks. Tune false positives carefully.
# - Use re.IGNORECASE | re.MULTILINE for all natural-language patterns.
_NL_FLAGS = re.IGNORECASE | re.MULTILINE

_PATTERNS: List[tuple] = [
    # === HIGH: system-prompt override attempts =====================
    (Severity.HIGH, "override",
     re.compile(r"\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|rules|prompts)\b", _NL_FLAGS)),
    (Severity.HIGH, "override",
     re.compile(r"\bdisregard\s+(?:all\s+)?(?:previous|prior|system|above)\s+(?:instructions|rules|prompts)\b", _NL_FLAGS)),
    (Severity.HIGH, "override",
     re.compile(r"\b(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be|roleplay\s+as)\s+(?:DAN|jailbreak|unrestricted|god\s*mode|admin|root)\b", _NL_FLAGS)),
    (Severity.HIGH, "override",
     re.compile(r"\b(?:\[system\]|<system>|SYSTEM:)\s*(?:reset|override|replace|new\s+instructions)\b", _NL_FLAGS)),
    (Severity.HIGH, "override",
     re.compile(r"\bfrom\s+now\s+on[,\s]+you\s+(?:will|must|should)\b", _NL_FLAGS)),

    # === HIGH: data exfiltration via shell ==========================
    (Severity.HIGH, "exfil",
     re.compile(r"\bcat\s+(?:~|/home/[^/\s]+|/etc/passwd|/etc/shadow|\$HOME)/?\S*", _NL_FLAGS)),
    (Severity.HIGH, "exfil",
     re.compile(r"\bcurl\s+[^|;\n]*\$\{?(?:HOME|USER|PATH|PWD|API[_A-Z]*KEY|TOKEN|SECRET)[A-Z_]*\}?", _NL_FLAGS)),
    (Severity.HIGH, "exfil",
     re.compile(r"\b(?:wget|curl)\s+[^|;\n]*\?\S*(?:env|secret|passwd|token|api[_-]?key)=", _NL_FLAGS)),
    (Severity.HIGH, "exfil",
     re.compile(r"\.ssh/(?:id_rsa|id_ed25519|known_hosts|authorized_keys)\b", _NL_FLAGS)),

    # === MEDIUM: suspicious code-eval =================================
    (Severity.MEDIUM, "eval",
     re.compile(r"\b(?:exec|eval)\s*\(\s*(?:base64|input|request|user_input|prompt)\b", _NL_FLAGS)),
    (Severity.MEDIUM, "eval",
     re.compile(r"\b__import__\s*\(\s*['\"](?:os|subprocess|sys|socket)['\"]", _NL_FLAGS)),
    (Severity.MEDIUM, "eval",
     re.compile(r"\bsubprocess\.\w+\s*\([^)]*shell\s*=\s*True", _NL_FLAGS)),

    # === MEDIUM: developer/maintenance mode tricks ===================
    (Severity.MEDIUM, "mode",
     re.compile(r"\b(?:developer|debug|maintenance|admin)\s+mode\s+(?:on|enabled|activated)\b", _NL_FLAGS)),

    # === LOW: shell references (likely benign, just noise) ===========
    (Severity.LOW, "shell-ref",
     re.compile(r"\b(?:rm\s+-rf\s+/|sudo\s+rm)\b", _NL_FLAGS)),
    (Severity.LOW, "shell-ref",
     re.compile(r"\bbash\s+-c\s+['\"]", _NL_FLAGS)),

    # === LOW: zero-width / invisible chars (steganography vector) ====
    (Severity.LOW, "stego",
     re.compile(r"[​‌‍⁠﻿]")),
]


def _excerpt(text: str, match_start: int, span: int = 80) -> str:
    """80-char window around match, single line."""
    a = max(0, match_start - span // 2)
    b = min(len(text), match_start + span // 2)
    e = text[a:b].replace("\n", " ").replace("\r", " ").strip()
    return e[:span]


def scan_prompt_content(
    text: str,
    source: str = "<unknown>",
    *,
    max_hits_per_category: int = 5,
) -> List[ScanHit]:
    """
    Scan `text` for prompt-injection / exfil patterns.
    Returns a list of ScanHit ordered by severity (HIGH first).

    `source` is propagated into every hit so callers can report origin.
    `max_hits_per_category` prevents pathological inputs from generating
    thousands of identical findings.
    """
    if not text:
        return []
    hits: List[ScanHit] = []
    per_cat: dict = {}
    for severity, category, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            key = (category, severity)
            per_cat[key] = per_cat.get(key, 0) + 1
            if per_cat[key] > max_hits_per_category:
                break
            hits.append(ScanHit(
                severity=severity,
                category=category,
                pattern=pattern.pattern[:60],
                excerpt=_excerpt(text, m.start()),
                source=source,
            ))
    # Sort: HIGH > MEDIUM > LOW
    order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
    hits.sort(key=lambda h: (order[h.severity], h.category))
    return hits


def has_blocking_hit(hits: List[ScanHit]) -> bool:
    """True if any hit is HIGH severity (caller should block load)."""
    return any(h.severity == Severity.HIGH for h in hits)


def summarize_hits(hits: List[ScanHit]) -> str:
    """One-line human summary, useful for logs."""
    if not hits:
        return "no findings"
    counts = {}
    for h in hits:
        counts[h.severity.value] = counts.get(h.severity.value, 0) + 1
    return " ".join(f"{k}={v}" for k, v in sorted(counts.items()))
