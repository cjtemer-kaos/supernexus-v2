"""Gema: security — Escaneo de vulnerabilidades con MEDUSA scanner."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MANIFEST = {
    "name": "security",
    "main": "src.plugins.gemas.security",
    "model": "gemma4:12b",
    "tags": ["security", "compliance", "protection", "scan", "vulnerability"],
    "description": "Escaneo de vulnerabilidades con MEDUSA scanner",
    "icon": "🛡️",
    "color": "#EF4444",
    "division": "security",
    "personality": "Auditor de seguridad paranoid. MEDUSA scanner, OWASP, zero-trust.",
    "workflow": "Scan → Classify → Prioritize → Report → Remediate",
}

# ---------------------------------------------------------------------------
# Recommendations map: category -> human-readable recommendation
# ---------------------------------------------------------------------------
_RECOMMENDATIONS: Dict[str, str] = {
    "prompt-injection": "Review input sanitisation; use allow-listing and prompt boundaries.",
    "sql-injection": "Use parameterised queries; never interpolate user input into SQL.",
    "xss": "Escape user output; use templating auto-escaping; apply Content-Security-Policy.",
    "command-injection": "Avoid shell=True with user input; use subprocess with argument lists.",
    "path-traversal": "Canonicalise and validate file paths; use allow-lists for directories.",
    "hardcoded-secret": "Move secrets to environment variables or a vault; rotate exposed credentials.",
    "crypto-weak": "Replace weak algorithms (MD5, SHA1) with SHA-256+ or modern ciphers.",
    "deserialization": "Avoid pickle/eval on untrusted input; use safe formats like JSON.",
    "ssrf": "Validate and allow-list target URLs; block internal/private IP ranges.",
    "lfi": "Validate filenames against an allow-list; never pass user input directly to open().",
    "rfi": "Block remote file includes; load only local, pre-approved resources.",
    "idor": "Enforce server-side authorisation checks on every resource access.",
    "info-disclosure": "Suppress verbose error messages in production; log details server-side.",
}

_DEFAULT_RECOMMENDATION = "Review the flagged code for potential security issues and apply least-privilege principles."


class SecurityGem:
    """Security gema — scans text/files for vulnerabilities using MEDUSA patterns."""

    def __init__(self) -> None:
        """Load MEDUSA patterns on instantiation."""
        from src.security.medusa_scan import _load_patterns

        self._patterns = _load_patterns()
        logger.info("SecurityGem initialised with %d MEDUSA patterns", len(self._patterns))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, task: str) -> Dict[str, Any]:
        """
        Scan *task* content for security threats.

        If *task* contains a recognisable file path, the referenced file is
        read and scanned in addition to the task text itself.

        Returns a structured dict consumed by GemaWorker._execute_task.
        """
        hits = self._scan_text(task)

        # Optionally scan a file mentioned in the task
        file_path = self._extract_file_path(task)
        file_hits: List = []
        scanned_file: Optional[str] = None
        if file_path:
            file_hits = self._scan_file(file_path)
            scanned_file = str(file_path)
            hits.extend(file_hits)

        severity_counts = self._count_by_severity(hits)
        categories = self._unique_categories(hits)
        recommendations = self._build_recommendations(hits)

        return {
            "gema": "security",
            "status": "completed",
            "threats_found": len(hits),
            "severity": severity_counts,
            "categories": categories,
            "hits": [
                {
                    "pattern_id": h.pattern_id,
                    "severity": h.severity,
                    "category": h.category,
                    "excerpt": h.excerpt,
                    "line": h.line,
                }
                for h in hits
            ],
            "scanned_file": scanned_file,
            "recommendations": recommendations,
            "metadata": {},
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _scan_text(text: str) -> list:
        """Delegate to MEDUSA scan_text."""
        from src.security.medusa_scan import scan_text

        return scan_text(text)

    @staticmethod
    def _scan_file(path: Path) -> list:
        """Read a file and scan its contents."""
        from src.security.medusa_scan import scan_file

        return scan_file(path)

    @staticmethod
    def _extract_file_path(task: str) -> Optional[Path]:
        """Best-effort extraction of a file path from the task string.

        Looks for common patterns:
          - Absolute paths (D:\\..., /home/..., C:/...)
          - Relative paths ending with a known code extension
          - Lines starting with 'file:', 'path:', 'archivo:'
        """
        # Explicit labels: file:/path, path:/path, archivo:/path
        label_match = re.search(
            r"(?:file|path|archivo)\s*[:=]\s*['\"]?([^\s'\"]+)",
            task,
            re.IGNORECASE,
        )
        if label_match:
            raw = label_match.group(1).strip(" ='\"")
            candidate = Path(raw)
            if candidate.is_file():
                return candidate
            # Try resolving relative to cwd
            resolved = Path.cwd() / candidate
            if resolved.is_file():
                return resolved

        # Find all tokens that look like file paths (absolute or relative)
        path_pattern = re.compile(
            r"(?:[A-Za-z]:[/\\]|[./~])[\w./\\\-]+",
        )
        for match in path_pattern.finditer(task):
            candidate = Path(match.group(0))
            if candidate.is_file():
                return candidate
            resolved = Path.cwd() / candidate
            if resolved.is_file():
                return resolved

        # Last resort: look for words with known code-file extensions
        ext_pattern = re.compile(
            r"[A-Za-z0-9_./\\\-]+\.(?:py|js|ts|jsx|tsx|go|rs|java|rb|php|sh|yaml|yml|json|toml|md|txt|sql|html|css)"
        )
        for match in ext_pattern.finditer(task):
            candidate = Path(match.group(0))
            if candidate.is_file():
                return candidate
            resolved = Path.cwd() / candidate
            if resolved.is_file():
                return resolved

        return None

    @staticmethod
    def _count_by_severity(hits: list) -> Dict[str, int]:
        counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}
        for h in hits:
            sev = getattr(h, "severity", "medium")
            counts[sev] = counts.get(sev, 0) + 1
        return counts

    @staticmethod
    def _unique_categories(hits: list) -> List[str]:
        seen = set()
        cats: List[str] = []
        for h in hits:
            c = getattr(h, "category", "unknown")
            if c not in seen:
                seen.add(c)
                cats.append(c)
        return cats

    @staticmethod
    def _build_recommendations(hits: list) -> List[str]:
        """Return de-duplicated recommendations based on hit categories."""
        recs: List[str] = []
        seen_cats: set = set()
        for h in hits:
            cat = getattr(h, "category", "unknown")
            if cat in seen_cats:
                continue
            seen_cats.add(cat)
            recs.append(_RECOMMENDATIONS.get(cat, _DEFAULT_RECOMMENDATION))
        return recs
