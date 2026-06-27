"""Checkpoint metrics tracker — pass/fail/vague stats per gema.

Updated by LLMRoleGema when use_checkpoint_contract=true.
Read by GET /api/checkpoint/metrics.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger(__name__)


@dataclass
class GemaMetrics:
    total: int = 0
    passed: int = 0
    failed: int = 0
    vague: int = 0
    last_run: str = ""


_tracker: Dict[str, GemaMetrics] = defaultdict(GemaMetrics)


def record(gema_name: str, valid: bool, vague_rejected: bool = False) -> None:
    m = _tracker[gema_name]
    m.total += 1
    m.last_run = datetime.now(timezone.utc).isoformat()
    if vague_rejected:
        m.vague += 1
        m.failed += 1
    elif valid:
        m.passed += 1
    else:
        m.failed += 1


def get_metrics() -> Dict[str, Any]:
    result: Dict[str, Any] = {"gemas": {}, "totals": {"total": 0, "passed": 0, "failed": 0, "vague": 0}}

    for name, m in sorted(_tracker.items()):
        result["gemas"][name] = {
            "total": m.total,
            "passed": m.passed,
            "failed": m.failed,
            "vague": m.vague,
            "pass_rate": round(m.passed / m.total * 100, 1) if m.total else 0,
            "last_run": m.last_run,
        }
        for k in ("total", "passed", "failed", "vague"):
            result["totals"][k] += getattr(m, k)

    if result["totals"]["total"]:
        result["totals"]["pass_rate"] = round(
            result["totals"]["passed"] / result["totals"]["total"] * 100, 1
        )
    else:
        result["totals"]["pass_rate"] = 0

    return result


def reset(gema_name: str = "") -> None:
    if gema_name:
        _tracker.pop(gema_name, None)
    else:
        _tracker.clear()
