"""
otel_exporter — Drain event_stream events to an OTLP-compatible collector.

Pattern (aden-hive): events on the canonical bus already carry trace_id,
span_id, parent_span_id (OTel-aligned). All that was missing was the
shipping. This module subscribes once at boot and POSTs each event as
an OTLP log/span via HTTP JSON encoding — no SDK dependency.

Activation:
    NEXUS_OTEL_ENDPOINT  e.g. "http://localhost:4318/v1/logs"
                          (Tempo/Jaeger/OTel-collector all accept OTLP HTTP)
    NEXUS_OTEL_SERVICE   optional, default "nexus-ia"

Best-effort: 0 retries beyond the httpx client default; one failed
emit is logged and dropped (we won't block the agent loop on a flaky
collector). The subscriber drains forever until process exit.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

_started = False
_task: Optional[asyncio.Task] = None


def _endpoint() -> str:
    return os.environ.get("NEXUS_OTEL_ENDPOINT", "").strip()


def _service() -> str:
    return os.environ.get("NEXUS_OTEL_SERVICE", "nexus-ia")


def _to_otlp_log(ev) -> dict:
    """Convert one Event to OTLP logs JSON wire format.
    Reference: opentelemetry-proto LogRecord."""
    # Severity: map by event type prefix
    sev = "INFO"
    t = ev.type.value if hasattr(ev.type, "value") else str(ev.type)
    if t.startswith("sec.") or "failed" in t or "error" in t:
        sev = "ERROR"
    elif "stall" in t or "loop" in t or "degraded" in t:
        sev = "WARN"
    attrs = [
        {"key": "event.type", "value": {"stringValue": t}},
        {"key": "event.id", "value": {"stringValue": ev.id}},
    ]
    if ev.session_id:
        attrs.append({"key": "session.id", "value": {"stringValue": ev.session_id}})
    if ev.request_id:
        attrs.append({"key": "request.id", "value": {"stringValue": ev.request_id}})
    if ev.source:
        attrs.append({"key": "source", "value": {"stringValue": ev.source}})
    for k, v in (ev.data or {}).items():
        attrs.append({
            "key": f"data.{k}",
            "value": {"stringValue": str(v)[:500]},
        })
    return {
        "resourceLogs": [{
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": _service()}},
                ]
            },
            "scopeLogs": [{
                "logRecords": [{
                    "timeUnixNano": str(int(time.time() * 1e9)),
                    "severityText": sev,
                    "body": {"stringValue": f"{t}"},
                    "attributes": attrs,
                }]
            }]
        }]
    }


async def _consumer_loop():
    endpoint = _endpoint()
    if not endpoint:
        return
    try:
        import httpx
    except ImportError:
        logger.warning("otel_exporter: httpx not installed; OTel export disabled")
        return
    try:
        from src.observability.event_stream import bus
    except Exception as e:
        logger.warning(f"otel_exporter: event_stream unavailable: {e}")
        return
    logger.info(f"otel_exporter: streaming to {endpoint}")
    async with httpx.AsyncClient(timeout=5.0) as client:
        async for ev in bus.subscribe(label="otel_exporter"):
            try:
                payload = _to_otlp_log(ev)
                r = await client.post(endpoint, json=payload)
                if r.status_code >= 400:
                    logger.debug(f"otel_exporter: HTTP {r.status_code} for {ev.id}")
            except Exception as e:
                logger.debug(f"otel_exporter: emit failed for {ev.id}: {e}")


def ensure_started(loop: Optional[asyncio.AbstractEventLoop] = None) -> bool:
    """Idempotent. Returns True if subscriber is now running (or was already)."""
    global _started, _task
    if _started:
        return True
    if not _endpoint():
        return False
    try:
        lp = loop or asyncio.get_event_loop()
    except RuntimeError:
        return False
    if not lp.is_running():
        return False
    _task = lp.create_task(_consumer_loop())
    _started = True
    return True
