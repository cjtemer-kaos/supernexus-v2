"""Gema: code — Programacion, ejecucion y sandbox

Provides deterministic code analysis: file reading, line counting,
language detection, TODO/FIXME/HACK scanning, function-length checks,
and structured review feedback. No LLM call needed for the analysis
itself — the result is returned as structured data so the router or
a downstream gema can decide what to do with it.
"""

import re
import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MANIFEST = {
    "name": "code",
    "main": "src.plugins.gemas.code",
    "model": "gemma4:12b",
    "tags": ['programming', 'code-review', 'refactoring', 'handoff', 'delegation', 'compile', 'sandbox'],
    "description": "Programacion, ejecucion y sandbox",
    "icon": "💻",
    "color": "#3B82F6",
    "division": "engineering",
    "personality": "Senior developer pragmático. Código limpio, tests, documentación.",
    "workflow": "Analizar → Planificar → Implementar → Testear → Documentar",
}

# ── Language detection by extension ──────────────────────────────────────────
_EXT_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript-jsx",
    ".tsx": "typescript-tsx",
    ".java": "java",
    ".kt": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".h": "c-header",
    ".hpp": "cpp-header",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".cs": "csharp",
    ".lua": "lua",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "zsh",
    ".ps1": "powershell",
    ".bat": "batch",
    ".cmd": "batch",
    ".sql": "sql",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".md": "markdown",
    ".rst": "restructuredtext",
    ".dockerfile": "dockerfile",
    ".tf": "terraform",
    ".vue": "vue",
    ".svelte": "svelte",
}

# ── Patterns to detect ───────────────────────────────────────────────────────
TODO_PATTERN = re.compile(
    r"#\s*(TODO|FIXME|HACK|XXX|BUGBUG|OPTIMIZE|REVIEW)\b",
    re.IGNORECASE,
)
BLOCK_COMMENT_TODO = re.compile(
    r"(TODO|FIXME|HACK|XXX|BUGBUG|OPTIMIZE|REVIEW)\b",
    re.IGNORECASE,
)

# Function detection patterns (best-effort, no AST dependency)
_FUNC_PATTERNS = {
    "python":   re.compile(r"^\s*def\s+(\w+)\s*\(", re.MULTILINE),
    "javascript": re.compile(r"^\s*(?:async\s+)?function\s+(\w+)\s*\(", re.MULTILINE),
    "typescript": re.compile(r"^\s*(?:async\s+)?function\s+(\w+)\s*\(", re.MULTILINE),
    "java":     re.compile(r"^\s*(?:public|private|protected|static|\s)+\s+\w+\s+(\w+)\s*\(", re.MULTILINE),
    "go":       re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(", re.MULTILINE),
    "rust":     re.compile(r"^\s*(?:pub\s+)?fn\s+(\w+)\s*[<(]", re.MULTILINE),
    "csharp":   re.compile(r"^\s*(?:public|private|protected|internal|static|\s)+\s+\w+\s+(\w+)\s*\(", re.MULTILINE),
    "ruby":     re.compile(r"^\s*def\s+(\w+)", re.MULTILINE),
    "php":      re.compile(r"^\s*(?:public|private|protected|static|\s)*function\s+(\w+)\s*\(", re.MULTILINE),
}

# Common anti-patterns / issues
ISSUE_PATTERNS = [
    ("bare-except",       re.compile(r"except\s*:", re.MULTILINE), "Bare `except:` — catches all exceptions including SystemExit/KeyboardInterrupt"),
    ("eval-usage",        re.compile(r"\beval\s*\(", re.MULTILINE), "`eval()` usage — potential security risk"),
    ("exec-usage",        re.compile(r"\bexec\s*\(", re.MULTILINE), "`exec()` usage — potential security risk"),
    ("hardcoded-secret",  re.compile(r"""(?:password|passwd|secret|token|api_key|apikey)\s*=\s*['"][^'"]+['"]""", re.IGNORECASE), "Hardcoded secret/password"),
    ("print-debug",       re.compile(r"\bprint\s*\(['\"]DEBUG", re.IGNORECASE), "Debug print statement left in code"),
    ("empty-except",      re.compile(r"except.*:\s*\n\s*pass\b", re.MULTILINE), "Empty except:pass — silently swallows errors"),
    ("star-import",       re.compile(r"from\s+\S+\s+import\s+\*", re.MULTILINE), "Wildcard import (`from X import *`)"),
    ("mutable-default",   re.compile(r"def\s+\w+\s*\([^)]*=\s*(\[\]|\{\}|set\(\))", re.MULTILINE), "Mutable default argument (list/dict/set)"),
    ("nested-deep",       re.compile(r"^\t\t\t\t|^( {16})", re.MULTILINE), "Deeply nested code (4+ levels)"),
    ("long-line",         None, "Line exceeds 120 characters (checked separately)"),
]


# ── Helper functions ─────────────────────────────────────────────────────────

def _detect_language(filepath: str) -> str:
    """Detect programming language from file extension."""
    ext = Path(filepath).suffix.lower()
    return _EXT_MAP.get(ext, "unknown")


def _extract_file_path(task: str) -> Optional[str]:
    """Try to extract a file path from the task text."""
    # Match quoted paths: "path", 'path'
    quoted = re.findall(r'["\']([A-Za-z]:\\[^\s"\']+|/[^\s"\']+)["\']', task)
    if quoted:
        return quoted[0]
    # Match bare Windows paths: D:\folder\file.py  or  D:\\folder\\file.py
    win = re.findall(r'([A-Z]:\\[^\s"\']+)', task)
    if win:
        return win[0]
    # Match bare unix paths: /folder/file.py (not starting with http)
    unix = re.findall(r'(?<!\w)(/[\w/._-]+\.\w{1,5})(?!\w)', task)
    if unix:
        return unix[0]
    # Match relative paths like src/plugins/code.py
    rel = re.findall(r'(?<!\w)((?:[\w_-]+/)+[\w._-]+\.\w{1,5})(?!\w)', task)
    if rel:
        return rel[0]
    return None


def _count_lines(content: str) -> Dict[str, int]:
    """Count total, blank, comment, and code lines."""
    lines = content.splitlines()
    total = len(lines)
    blank = sum(1 for l in lines if l.strip() == "")
    comment = 0
    in_block = False
    for line in lines:
        stripped = line.strip()
        if not in_block and stripped.startswith("#"):
            comment += 1
        elif not in_block and stripped.startswith('"""') or stripped.startswith("'''"):
            in_block = True
            comment += 1
        elif in_block:
            comment += 1
            if stripped.endswith('"""') or stripped.endswith("'''"):
                in_block = False
    code = total - blank - comment
    return {
        "total": total,
        "blank": blank,
        "comment": comment,
        "code": max(0, code),
    }


def _find_todos(content: str) -> List[Dict[str, Any]]:
    """Find TODO/FIXME/HACK comments in the code."""
    results = []
    for i, line in enumerate(content.splitlines(), start=1):
        match = TODO_PATTERN.search(line)
        if match:
            tag = match.group(1).upper()
            results.append({
                "line": i,
                "tag": tag,
                "text": line.strip(),
            })
    return results


def _find_functions(content: str, language: str) -> List[Dict[str, Any]]:
    """Detect functions and measure their approximate length."""
    pattern = _FUNC_PATTERNS.get(language)
    if not pattern:
        return []

    functions = []
    lines = content.splitlines()
    for match in pattern.finditer(content):
        name = match.group(1)
        # Find the line number of this match
        line_num = content[:match.start()].count("\n") + 1
        # Estimate function length by looking for the next top-level definition or end of file
        func_start_indent = len(lines[line_num - 1]) - len(lines[line_num - 1].lstrip()) if line_num <= len(lines) else 0
        end_line = len(lines)
        for j in range(line_num, len(lines)):
            if j == line_num:
                continue
            curr = lines[j]
            if curr.strip() == "":
                continue
            curr_indent = len(curr) - len(curr.lstrip())
            # If we hit a line at the same or lesser indent that looks like a definition
            if curr_indent <= func_start_indent and curr.strip():
                # Check if it's a new def/class/decorator or end of block
                if any(curr.strip().startswith(kw) for kw in ["def ", "class ", "@", "async def"]):
                    end_line = j
                    break
                # In C-like languages, check for closing braces at root level
                if language in ("c", "cpp", "java", "csharp", "go", "rust", "javascript", "typescript"):
                    if curr.strip() in ("}", "};"):
                        end_line = j
                        break
        func_length = end_line - line_num + 1
        functions.append({
            "name": name,
            "start_line": line_num,
            "length": func_length,
            "is_long": func_length > 50,
        })
    return functions


def _find_issues(content: str, language: str) -> List[Dict[str, str]]:
    """Detect common code issues / anti-patterns."""
    issues = []
    for name, pattern, description in ISSUE_PATTERNS:
        if name == "long-line":
            for i, line in enumerate(content.splitlines(), start=1):
                if len(line) > 120:
                    issues.append({
                        "rule": name,
                        "line": i,
                        "message": description,
                        "severity": "warning",
                    })
                    # Cap long-line reports at 10
                    if sum(1 for iss in issues if iss["rule"] == "long-line") >= 10:
                        break
        elif pattern:
            for match in pattern.finditer(content):
                line_num = content[:match.start()].count("\n") + 1
                sev = "error" if name in ("eval-usage", "exec-usage", "hardcoded-secret") else "warning"
                issues.append({
                    "rule": name,
                    "line": line_num,
                    "message": description,
                    "severity": sev,
                })
    return issues


def _code_metrics(content: str, language: str) -> Dict[str, Any]:
    """Compute additional code quality metrics."""
    lines = content.splitlines()

    # Average line length
    non_empty = [l for l in lines if l.strip()]
    avg_len = sum(len(l) for l in non_empty) / max(len(non_empty), 1)

    # Max indentation depth
    max_indent = 0
    for line in lines:
        if line.strip():
            indent = len(line) - len(line.lstrip())
            # Normalize: tabs = 4 spaces
            indent = line[:indent].count("\t") * 4 + indent % 4
            # Rough: count leading spaces
            indent = len(line) - len(line.lstrip())
            max_indent = max(max_indent, indent)

    return {
        "avg_line_length": round(avg_len, 1),
        "max_indent_depth": max_indent,
        "has_encoding_declaration": bool(re.search(r"#.*coding[:=]\s*(utf-8|latin-1|ascii)", content)),
        "has_docstring": '"""' in content or "'''" in content,
    }


# ── Main class ───────────────────────────────────────────────────────────────

class CodeGem:
    """Deterministic code analysis gema.

    Usage::

        gem = CodeGem()
        result = await gem.execute("Analyze D:\\src\\main.py")
    """

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        """Analyze code based on the task description.

        1. If the task mentions a file path, reads and analyzes it.
        2. Provides code review feedback.
        3. Returns structured analysis dict.
        """
        logger.info(f"CodeGem executing: {task[:80]}...")

        filepath = _extract_file_path(task)

        # If no file path found, return a diagnostic about the task
        if not filepath:
            return {
                "gema": "code",
                "status": "no_file_found",
                "task": task,
                "message": "No file path detected in the task. Provide a file path to analyze (e.g. 'Analyze src/main.py').",
                "analysis": None,
            }

        # Resolve and read the file
        resolved = Path(filepath)
        if not resolved.is_absolute():
            # Try relative to cwd
            resolved = Path.cwd() / resolved

        if not resolved.exists():
            return {
                "gema": "code",
                "status": "file_not_found",
                "task": task,
                "filepath": str(resolved),
                "message": f"File not found: {resolved}",
                "analysis": None,
            }

        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {
                "gema": "code",
                "status": "read_error",
                "task": task,
                "filepath": str(resolved),
                "message": f"Error reading file: {e}",
                "analysis": None,
            }

        language = _detect_language(str(resolved))
        line_counts = _count_lines(content)
        todos = _find_todos(content)
        functions = _find_functions(content, language)
        issues = _find_issues(content, language)
        metrics = _code_metrics(content, language)

        # Build summary
        long_functions = [f for f in functions if f["is_long"]]
        errors = [i for i in issues if i["severity"] == "error"]
        warnings = [i for i in issues if i["severity"] == "warning"]

        analysis = {
            "filepath": str(resolved),
            "language": language,
            "lines": line_counts,
            "todos": todos,
            "functions": {
                "total": len(functions),
                "long": long_functions,
            },
            "issues": {
                "errors": errors,
                "warnings": warnings,
                "total": len(issues),
            },
            "metrics": metrics,
        }

        # Build human-readable summary
        summary_parts = [
            f"**File:** {resolved.name}",
            f"**Language:** {language}",
            f"**Lines:** {line_counts['total']} total ({line_counts['code']} code, {line_counts['comment']} comment, {line_counts['blank']} blank)",
        ]

        if todos:
            summary_parts.append(f"**TODOs/FIXMEs:** {len(todos)} found")
            for t in todos[:5]:
                summary_parts.append(f"  - Line {t['line']}: [{t['tag']}] {t['text'][:80]}")

        if long_functions:
            summary_parts.append(f"**Long functions:** {len(long_functions)} (>50 lines)")
            for f in long_functions[:5]:
                summary_parts.append(f"  - {f['name']}() at line {f['start_line']} ({f['length']} lines)")

        if errors:
            summary_parts.append(f"**Errors:** {len(errors)}")
            for e in errors[:5]:
                summary_parts.append(f"  - Line {e['line']}: {e['message']}")

        if warnings:
            summary_parts.append(f"**Warnings:** {len(warnings)}")
            for w in warnings[:5]:
                summary_parts.append(f"  - Line {w['line']}: {w['message']}")

        if not todos and not long_functions and not errors and not warnings:
            summary_parts.append("**Status:** ✅ No significant issues found")

        return {
            "gema": "code",
            "status": "analyzed",
            "task": task,
            "content": "\n".join(summary_parts),
            "analysis": analysis,
        }


# ── Module-level handler (for manifest loader) ──────────────────────────────

_gem_instance = CodeGem()

async def handle(task: str, context: str = "", app: Any = None) -> Dict[str, Any]:
    """Module-level handler called by the manifest loader."""
    return await _gem_instance.execute(task, context)
