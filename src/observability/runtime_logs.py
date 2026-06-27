"""
runtime_logs — 3-level structured logging per session.

Pattern (aden-hive runtime_log_schemas.py + runtime_log_store.py):

    ~/.nexus/sessions/{session_id}/logs/
        summary.json        L1 — one row per run: totals + execution_quality
        details.jsonl       L2 — one row per node/step: tokens, latency, status
        tool_logs.jsonl     L3 — one row per tool call: name, args, result, ms

Why 3 levels instead of one giant log:
    L1 answers "what did this session cost / how well did it run?"
    L2 answers "where did the time/tokens go inside the session?"
    L3 answers "what arguments did THAT tool get and what did it return?"

Each level can be tailed, replayed, or shipped to OTel without parsing
the others. trace_id / span_id / parent_span_id fields are OTel-aligned.

Usage:

    from src.observability.runtime_logs import session_logger
    log = session_logger(session_id="abc")
    with log.start_run(trace_id="req-42") as run:
        run.note_node("routing", tokens_in=20, tokens_out=5, ms=120)
        run.note_tool("search", args={"q":"x"}, result="ok", ms=80)
        run.finalize(status="completed", cost_usd=0.0042)

Files are append-only (JSONL) + one summary.json overwritten on finalize.
Crash-safe via line-buffered writes.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _logs_dir(session_id: str) -> Path:
    base = Path.home() / ".nexus" / "sessions" / session_id / "logs"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _now() -> str:
    return datetime.now().isoformat()


@dataclass
class NodeRecord:
    """L2 — one row per logical step (routing, tool dispatch, llm call)."""
    ts: str
    node: str
    status: str = "ok"  # ok|error|skipped
    tokens_in: int = 0
    tokens_out: int = 0
    ms: float = 0.0
    cost_usd: float = 0.0
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolRecord:
    """L3 — one row per tool call."""
    ts: str
    tool: str
    status: str = "ok"  # ok|error|timeout|loop
    ms: float = 0.0
    args_preview: str = ""   # truncated for size; full args persisted elsewhere
    result_preview: str = ""
    error: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None


@dataclass
class RunSummary:
    """L1 — one row per run (the whole session turn)."""
    run_id: str
    session_id: str
    trace_id: Optional[str]
    started_at: str
    finished_at: Optional[str] = None
    status: str = "running"   # running|completed|failed|cancelled
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float = 0.0
    total_ms: float = 0.0
    node_count: int = 0
    tool_count: int = 0
    error_count: int = 0


class _Run:
    """Active run context — accumulates totals and writes L2/L3 lines as they
    happen. Call finalize() to flush the L1 summary."""

    def __init__(self, parent: "SessionLogger", trace_id: Optional[str]):
        self.parent = parent
        self.summary = RunSummary(
            run_id=f"run_{uuid.uuid4().hex[:12]}",
            session_id=parent.session_id,
            trace_id=trace_id,
            started_at=_now(),
        )
        self._t0 = datetime.now()
        self._finalized = False

    # --- L2 ---
    def note_node(self, node: str, **kwargs):
        rec = NodeRecord(
            ts=_now(), node=node,
            trace_id=self.summary.trace_id,
            span_id=kwargs.pop("span_id", None),
            parent_span_id=kwargs.pop("parent_span_id", None),
            **{k: v for k, v in kwargs.items() if k in NodeRecord.__dataclass_fields__},
        )
        self.summary.node_count += 1
        self.summary.total_tokens_in += rec.tokens_in
        self.summary.total_tokens_out += rec.tokens_out
        self.summary.total_cost_usd = round(self.summary.total_cost_usd + rec.cost_usd, 6)
        if rec.status == "error":
            self.summary.error_count += 1
        self.parent._append_jsonl("details.jsonl", asdict(rec))

    # --- L3 ---
    def note_tool(self, tool: str, args: Any = None, result: Any = None,
                  ms: float = 0.0, status: str = "ok", error: Optional[str] = None,
                  span_id: Optional[str] = None):
        rec = ToolRecord(
            ts=_now(), tool=tool, status=status, ms=ms,
            args_preview=self._preview(args),
            result_preview=self._preview(result),
            error=error,
            trace_id=self.summary.trace_id,
            span_id=span_id,
        )
        self.summary.tool_count += 1
        if status != "ok":
            self.summary.error_count += 1
        self.parent._append_jsonl("tool_logs.jsonl", asdict(rec))

    @staticmethod
    def _preview(obj: Any, cap: int = 240) -> str:
        if obj is None:
            return ""
        try:
            s = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, default=str)
        except Exception:
            s = repr(obj)
        return s[:cap]

    # --- L1 ---
    def finalize(self, status: str = "completed", cost_usd: Optional[float] = None,
                 extra_total_ms: Optional[float] = None):
        if self._finalized:
            return
        self._finalized = True
        self.summary.finished_at = _now()
        self.summary.status = status
        self.summary.total_ms = (datetime.now() - self._t0).total_seconds() * 1000
        if extra_total_ms is not None:
            self.summary.total_ms = extra_total_ms
        if cost_usd is not None:
            self.summary.total_cost_usd = round(cost_usd, 6)
        # summary.json holds the LAST run (overwrite). Past runs survive in
        # details.jsonl / tool_logs.jsonl via their trace_id.
        path = self.parent._dir / "summary.json"
        try:
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(asdict(self.summary), indent=2, ensure_ascii=False),
                           encoding="utf-8")
            os.replace(tmp, path)
        except Exception as e:
            logger.warning(f"runtime_logs: summary write failed: {e}")

    # context manager sugar
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if not self._finalized:
            self.finalize(status="failed" if exc_type else "completed")


class SessionLogger:
    """One per session. Cheap to instantiate; reuses dir/file handles."""

    _instances: Dict[str, "SessionLogger"] = {}
    _lock = threading.Lock()

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._dir = _logs_dir(session_id)
        self._jsonl_locks: Dict[str, threading.Lock] = {}

    def _append_jsonl(self, fname: str, record: Dict[str, Any]):
        if fname not in self._jsonl_locks:
            self._jsonl_locks[fname] = threading.Lock()
        line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
        path = self._dir / fname
        with self._jsonl_locks[fname]:
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(line)
            except Exception as e:
                logger.warning(f"runtime_logs: append {fname} failed: {e}")

    def start_run(self, trace_id: Optional[str] = None) -> _Run:
        return _Run(self, trace_id)

    def read_summary(self) -> Optional[Dict[str, Any]]:
        p = self._dir / "summary.json"
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def stats(self) -> Dict[str, Any]:
        d = self._dir
        return {
            "session_id": self.session_id,
            "dir": str(d),
            "summary_exists": (d / "summary.json").exists(),
            "details_bytes": (d / "details.jsonl").stat().st_size if (d / "details.jsonl").exists() else 0,
            "tool_logs_bytes": (d / "tool_logs.jsonl").stat().st_size if (d / "tool_logs.jsonl").exists() else 0,
        }


def session_logger(session_id: str) -> SessionLogger:
    """Get or create the SessionLogger for a session_id."""
    with SessionLogger._lock:
        inst = SessionLogger._instances.get(session_id)
        if inst is None:
            inst = SessionLogger(session_id)
            SessionLogger._instances[session_id] = inst
        return inst
