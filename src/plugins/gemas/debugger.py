"""Gema: debugger — Debugging & troubleshooting

Analyzes tasks for error patterns, reads files for common issues,
and returns actionable debugging suggestions.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

MANIFEST = {
    "name": "debugger",
    "main": "src.plugins.gemas.debugger",
    "model": "gemma4:12b",
    "tags": ['debugging', 'troubleshooting', 'error-handling'],
    "description": "Debugging",
    "icon": "🐛",
    "color": "#3B82F6",
    "division": "engineering",
    "personality": "Detector de bugs metódico. Lee logs, traza flujos, encuentra root cause.",
    "workflow": "Reproducir → Aislar → Analizar → Fix → Verificar",
}

# ---------------------------------------------------------------------------
# Error pattern classification
# ---------------------------------------------------------------------------
_ERROR_PATTERNS: Dict[str, List[str]] = {
    "import": [r"ImportError", r"ModuleNotFoundError", r"No module named"],
    "type": [r"TypeError", r"AttributeError", r"NameError", r"UnboundLocalError"],
    "index": [r"IndexError", r"KeyError"],
    "value": [r"ValueError", r"OverflowError"],
    "connection": [r"ConnectionError", r"TimeoutError", r"OSError", r"ConnectionRefusedError"],
    "memory": [r"MemoryError", r"RecursionError"],
    "permission": [r"PermissionError", r"AccessDenied"],
    "file": [r"FileNotFoundError", r"FileExistsError", r"IsADirectoryError"],
    "null": [r"NoneType", r"object has no attribute", r"'NoneType'"],
    "assertion": [r"AssertionError"],
    "runtime": [r"RuntimeError", r"NotImplementedError"],
}

_STACK_FRAME_RE = re.compile(
    r'File "(.+?)", line (\d+), in (.+)'
)

# File analysis patterns
_BARE_EXCEPT_RE = re.compile(r"^\s*except\s*:", re.MULTILINE)
_LOOSE_EXCEPT_RE = re.compile(r"^\s*except\s+Exception\s*:", re.MULTILINE)
_NONE_DEREF_RE = re.compile(r"\bNone\b")
_UNCHECKED_GET_RE = re.compile(r"\.get\([^)]+\)\s*\[")  # dict.get(...)[...]
_RAW_PRINT_RE = re.compile(r"^\s*print\s*\(", re.MULTILINE)
_UNUSED_IMPORT_RE = None  # handled specially


class DebuggerGem:
    """Lightweight debugger gema — pattern matching + file analysis.

    The gema_worker discovers this class because its name contains 'Gem'
    and calls ``execute(task)`` via JSON-RPC.
    """

    # -- public API (called by gema_worker) -----------------------------------

    def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        """Main entry point.  Analyse *task*, optionally read a file, return suggestions."""
        error_type = self._classify_error(task)
        stack_frames = self._extract_stack_frames(task)

        suggestions: List[str] = []
        file_issues: List[Dict[str, Any]] = []

        # --- file analysis if a path is mentioned ---
        file_path = self._extract_file_path(task)
        if file_path:
            file_issues = self._analyze_file(file_path)
            suggestions.extend(self._suggestions_for_file(file_path, file_issues))

        # --- error-type suggestions ---
        suggestions.extend(self._get_suggestions(error_type, task))

        # --- stack-frame hints ---
        if stack_frames:
            last = stack_frames[-1]
            suggestions.append(
                f"Last frame: {last['file']}:{last['line']} in {last['function']} — "
                f"check the code at that location."
            )

        # --- build readable content ---
        lines = [f"**Error type:** {error_type}"]
        if stack_frames:
            lines.append(f"**Stack frames found:** {len(stack_frames)}")
            for sf in stack_frames[:5]:
                lines.append(f"  - `{sf['file']}:{sf['line']}` in `{sf['function']}`")
            if len(stack_frames) > 5:
                lines.append(f"  ... and {len(stack_frames) - 5} more")
        if file_path:
            lines.append(f"\n**File analysed:** `{file_path}` ({len(file_issues)} issue(s) found)")
            for issue in file_issues:
                lines.append(f"  - Line {issue['line']}: {issue['description']}")
        lines.append("\n**Suggestions:**")
        for s in suggestions:
            lines.append(f"  1. {s}")

        return {
            "gema": "debugger",
            "task": task,
            "status": "processed",
            "error_type": error_type,
            "stack_frames": stack_frames[:10],
            "file": file_path,
            "file_issues": file_issues,
            "suggestions": suggestions,
            "content": "\n".join(lines),
        }

    # -- error classification ------------------------------------------------

    def _classify_error(self, text: str) -> str:
        """Return the most likely error category from *text*."""
        for error_type, patterns in _ERROR_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, text, re.IGNORECASE):
                    return error_type
        return "unknown"

    def _extract_stack_frames(self, text: str) -> List[Dict[str, Any]]:
        """Pull ``File "...", line N, in func`` entries from a traceback."""
        frames: List[Dict[str, Any]] = []
        for m in _STACK_FRAME_RE.finditer(text):
            frames.append({
                "file": m.group(1),
                "line": int(m.group(2)),
                "function": m.group(3),
            })
        return frames

    # -- file path extraction ------------------------------------------------

    def _extract_file_path(self, task: str) -> Optional[str]:
        """Try to pull a filesystem path out of *task*."""
        # Look for common patterns: "in file X", "file: X", or a bare .py path
        m = re.search(
            r'(?:in\s+file|file[:\s]+|look\s+at)\s+[`"\']*([^\s`"\']+\.py)[`"\']*',
            task,
            re.IGNORECASE,
        )
        if m:
            return self._resolve_path(m.group(1))

        # Fallback: any path ending in .py
        m = re.search(r'([A-Za-z0-9_./\\-]+\.py)\b', task)
        if m:
            return self._resolve_path(m.group(1))

        return None

    @staticmethod
    def _resolve_path(raw: str) -> Optional[str]:
        p = Path(raw)
        if p.is_file():
            return str(p.resolve())
        # Try relative to cwd
        cwd = Path.cwd() / raw
        if cwd.is_file():
            return str(cwd.resolve())
        return str(p)  # return as-is so caller sees it wasn't found

    # -- file analysis -------------------------------------------------------

    def _analyze_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Read *file_path* and flag common issues."""
        issues: List[Dict[str, Any]] = []
        try:
            text = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            issues.append({"line": 0, "description": f"Could not read file: {file_path}"})
            return issues

        lines = text.splitlines()

        # 1) Bare except
        for m in _BARE_EXCEPT_RE.finditer(text):
            line_no = text[:m.start()].count("\n") + 1
            issues.append({
                "line": line_no,
                "type": "bare-except",
                "description": "Bare `except:` — catches everything including "
                               "KeyboardInterrupt/SystemExit. Use specific exceptions.",
            })

        # 2) Broad except Exception
        for m in _LOOSE_EXCEPT_RE.finditer(text):
            line_no = text[:m.start()].count("\n") + 1
            issues.append({
                "line": line_no,
                "type": "broad-except",
                "description": "`except Exception:` — too broad, may hide bugs. "
                               "Catch more specific exceptions.",
            })

        # 3) Potential None dereference
        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()
            # Skip comments / strings (very rough heuristic)
            if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
                continue
            # .get(...)[  — dangerous
            if _UNCHECKED_GET_RE.search(stripped):
                issues.append({
                    "line": line_no,
                    "type": "unsafe-get-index",
                    "description": "Dict `.get(...)[...]` — `.get()` may return None, "
                                   "then indexing fails. Check the value first.",
                })

        # 4) print() debug leftovers (if more than 3, likely debug code)
        print_count = len(_RAW_PRINT_RE.findall(text))
        if print_count > 3:
            issues.append({
                "line": 0,
                "type": "debug-prints",
                "description": f"Found {print_count} print() calls — "
                               "consider using logging instead.",
            })

        # 5) Mutable default argument
        mutable_default_re = re.compile(
            r"def\s+\w+\s*\([^)]*=\s*(?:\[\]|\{\}|set\(\))"
        )
        for m in mutable_default_re.finditer(text):
            line_no = text[:m.start()].count("\n") + 1
            issues.append({
                "line": line_no,
                "type": "mutable-default",
                "description": "Mutable default argument (list/dict/set) — "
                               "shared across calls. Use None and create inside.",
            })

        # 6) Global keyword misuse
        global_re = re.compile(r"^\s*global\s+", re.MULTILINE)
        for m in global_re.finditer(text):
            line_no = text[:m.start()].count("\n") + 1
            issues.append({
                "line": line_no,
                "type": "global-usage",
                "description": "`global` keyword used — consider passing state "
                               "explicitly or using a class.",
            })

        return issues

    def _suggestions_for_file(self, file_path: str, issues: List[Dict]) -> List[str]:
        """Generate suggestions specific to file analysis results."""
        suggestions: List[str] = []
        if not Path(file_path).exists():
            suggestions.append(f"File not found: {file_path} — verify the path.")
            return suggestions

        types_seen = {i.get("type") for i in issues}
        if "bare-except" in types_seen:
            suggestions.append("Replace bare `except:` with specific exception types.")
        if "broad-except" in types_seen:
            suggestions.append("Narrow `except Exception:` to the expected exception.")
        if "unsafe-get-index" in types_seen:
            suggestions.append("Use `.get(key, default)` or check for None before indexing.")
        if "debug-prints" in types_seen:
            suggestions.append("Replace print() calls with `logging.info()` / `logging.debug()`.")
        if "mutable-default" in types_seen:
            suggestions.append("Use `def f(x=None): x = x or []` pattern for mutable defaults.")
        if "global-usage" in types_seen:
            suggestions.append("Avoid `global` — pass state as parameters or use a class.")
        return suggestions

    # -- error-type suggestions ----------------------------------------------

    def _get_suggestions(self, error_type: str, text: str) -> List[str]:
        """Return generic suggestions based on the classified error type."""
        mapping: Dict[str, List[str]] = {
            "import": [
                "Verify the module is installed: `pip install <module>`",
                "Check the module name (case-sensitive).",
                "Ensure the module is on sys.path.",
            ],
            "type": [
                "Check the data types involved in the operation.",
                "Use `isinstance()` to validate types before operating.",
                "Verify function arguments match the expected signature.",
            ],
            "index": [
                "Check that the key/index exists before accessing it.",
                "Use `.get(key, default)` for dicts.",
                "Validate list length before indexing.",
            ],
            "value": [
                "Validate input ranges and formats.",
                "Add input validation at function boundaries.",
            ],
            "connection": [
                "Verify the server/service is running.",
                "Check host, port, and URL configuration.",
                "Test network connectivity (ping / telnet).",
                "Inspect firewall / proxy settings.",
            ],
            "memory": [
                "Profile memory usage (e.g. `tracemalloc`, `memory_profiler`).",
                "Check for infinite recursion (missing base case).",
                "Use generators / itertools instead of large lists.",
            ],
            "permission": [
                "Check file/directory permissions.",
                "Run with appropriate privileges if needed.",
                "Verify ownership of the target resource.",
            ],
            "file": [
                "Verify the file path is correct.",
                "Check that the file/directory exists.",
                "Ensure read/write permissions.",
            ],
            "null": [
                "The code is operating on a `None` value.",
                "Add explicit None checks before attribute access.",
                "Verify that functions return the expected type.",
            ],
        }
        return mapping.get(error_type, [
            "Review the stack trace to pinpoint the exact failure line.",
            "Add logging around the suspected area.",
            "Reproduce with a minimal test case.",
        ])
