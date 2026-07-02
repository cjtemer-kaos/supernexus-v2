"""
Hive Hub — push-WS dispatcher for agent CLIs.

Replaces the old polling-based message_board.db with:
  - WebSocket /api/hive/ws          (push events to subscribers)
  - Server-Sent Events /api/hive/stream  (one-way stream, no handshake)
  - REST POST /api/hive/dispatch    (returns immediately; result via WS)
  - REST GET  /api/hive/agents      (registry dump)
  - REST GET  /api/hive/result/{id} (last N results cache)

The hub is aiohttp-native (matches the rest of SuperNEXUS). All execution
flows through src.bridges.hive_runner — no direct HTTP/SSH here.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections import deque

from aiohttp import web

from src.bridges.hive_runner import run_agent, list_agents, load_registry

log = logging.getLogger("hive_hub")

# ---------- in-process pub/sub ----------
_ws_clients: set[web.WebSocketResponse] = set()
_sse_subscribers: set[asyncio.Queue] = set()
_recent_results: dict[str, dict] = {}
_results_ring: deque[str] = deque(maxlen=200)
_MAX_PAYLOAD_BYTES = 256 * 1024

# ---------- persistencia (sobrevive a restarts) ----------
from pathlib import Path as _Path
_RESULTS_PATH = _Path.home() / ".nexus" / "hive_results.jsonl"


def _persist_result(result: dict) -> None:
    """Append result to disk JSONL — best-effort, never raises."""
    try:
        _RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_RESULTS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
    except Exception as e:
        log.warning(f"hive: persist failed: {e}")


def _load_recent_from_disk() -> None:
    """Load last 200 results from JSONL into RAM cache at boot."""
    if not _RESULTS_PATH.exists():
        return
    try:
        lines = _RESULTS_PATH.read_text(encoding="utf-8").splitlines()[-200:]
        for line in lines:
            if not line.strip():
                continue
            try:
                r = json.loads(line)
                rid = r.get("run_id", "")
                if rid:
                    _recent_results[rid] = r
                    _results_ring.append(rid)
            except Exception:
                continue
        log.info(f"hive: loaded {len(_recent_results)} results from {_RESULTS_PATH}")
    except Exception as e:
        log.warning(f"hive: load failed: {e}")


# Auto-load at import time
_load_recent_from_disk()


def _truncate(value: str, limit: int = 16_000) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + f"... [truncated {len(value) - limit} chars]"


async def _broadcast(event: dict) -> None:
    """Push an event to every WS client and every SSE subscriber."""
    event = {**event, "ts": event.get("ts", time.time())}
    if "raw_stdout" in event:
        event["raw_stdout"] = _truncate(event.get("raw_stdout", ""))
    if "raw_stderr" in event:
        event["raw_stderr"] = _truncate(event.get("raw_stderr", ""))
    msg = json.dumps(event, ensure_ascii=False)

    dead: set[web.WebSocketResponse] = set()
    for ws in _ws_clients:
        try:
            await ws.send_str(msg)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)

    for q in list(_sse_subscribers):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass


def _remember(result: dict) -> None:
    run_id = result.get("run_id", "")
    if not run_id:
        return
    _recent_results[run_id] = result
    _results_ring.append(run_id)
    while len(_recent_results) > _results_ring.maxlen:
        old = _results_ring.popleft()
        _recent_results.pop(old, None)
    _persist_result(result)


async def _run_and_broadcast(agent: str, task: str, run_id: str | None = None) -> dict:
    """Execute one agent via the runner, broadcast lifecycle events."""
    run_id = run_id or uuid.uuid4().hex[:12]
    await _broadcast({
        "type": "hive.dispatched",
        "run_id": run_id,
        "agent": agent,
        "task": task,
    })
    try:
        result = await asyncio.get_running_loop().run_in_executor(
            None, run_agent, agent, task
        )
        result_dict = result.to_dict()
        result_dict["run_id"] = run_id
    except Exception as e:
        result_dict = {
            "ok": False,
            "agent": agent,
            "task": task,
            "run_id": run_id,
            "error": f"{type(e).__name__}: {e}",
            "exit_code": -1,
            "reply": "",
        }
    _remember(result_dict)
    await _broadcast({"type": "hive.finished", **result_dict})
    return result_dict


# ---------- routes ----------
routes = web.RouteTableDef()


@routes.post("/api/hive/dispatch")
async def dispatch(request: web.Request) -> web.Response:
    """Fire-and-forget dispatch. Returns immediately with a run_id; the result
    is delivered to WS/SSE subscribers via `hive.finished` events and stored
    in /api/hive/result/{run_id}."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid JSON body"}, status=400)
    agent = (data.get("agent") or "").strip()
    task = (data.get("task") or "").strip()
    if not agent or not task:
        return web.json_response({"ok": False, "error": "agent and task are required"}, status=400)
    if len(task) > _MAX_PAYLOAD_BYTES:
        return web.json_response({"ok": False, "error": f"task too large ({len(task)} > {_MAX_PAYLOAD_BYTES})"}, status=413)

    run_id = uuid.uuid4().hex[:12]
    asyncio.create_task(_run_and_broadcast(agent, task, run_id=run_id))
    return web.json_response({
        "ok": True,
        "agent": agent,
        "task": task[:120],
        "run_id": run_id,
        "result_url": f"/api/hive/result/{run_id}",
        "stream_url": "/api/hive/stream",
        "ws_url": "/api/hive/ws",
        "subscribers_ws": len(_ws_clients),
        "subscribers_sse": len(_sse_subscribers),
    })


@routes.get("/api/hive/agents")
async def agents(_request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "agents": list_agents()})


@routes.get("/api/hive/registry")
async def registry(_request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "registry": load_registry()})


@routes.get("/api/hive/result/{run_id}")
async def get_result(request: web.Request) -> web.Response:
    run_id = request.match_info["run_id"]
    result = _recent_results.get(run_id)
    if not result:
        return web.json_response({"ok": False, "error": "result not found (expired or unknown run_id)"}, status=404)
    return web.json_response({"ok": True, "result": result})


@routes.post("/api/hive/result/{run_id}")
async def post_result(request: web.Request) -> web.Response:
    """Async agents (e.g. Antigravity) publish results here instead of
    going through the synchronous bridge polling loop."""
    run_id = request.match_info["run_id"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid JSON"}, status=400)
    result_dict = {
        "ok": True,
        "agent": data.get("agent", "unknown"),
        "task": data.get("task", ""),
        "reply": data.get("reply", ""),
        "run_id": run_id,
        "finished_at": data.get("finished_at", time.time()),
        "exit_code": 0,
        "error": "",
        **{k: v for k, v in data.items() if k not in ("agent", "task", "reply", "run_id", "finished_at")},
    }
    _remember(result_dict)
    await _broadcast({"type": "hive.finished", **result_dict})
    return web.json_response({"ok": True, "run_id": run_id, "stored": True})


@routes.get("/api/hive/ws")
async def ws_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse(max_msg_size=_MAX_PAYLOAD_BYTES)
    await ws.prepare(request)
    _ws_clients.add(ws)
    try:
        await ws.send_json({
            "type": "hive.hello",
            "agents": list_agents(),
            "subscribers": len(_ws_clients),
        })
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except Exception:
                    await ws.send_json({"type": "hive.error", "error": "invalid JSON"})
                    continue
                ctype = data.get("type")
                if ctype == "ping":
                    await ws.send_json({"type": "hive.pong", "ts": time.time()})
                elif ctype == "dispatch":
                    agent = (data.get("agent") or "").strip()
                    task = (data.get("task") or "").strip()
                    if agent and task:
                        run_id = uuid.uuid4().hex[:12]
                        asyncio.create_task(_run_and_broadcast(agent, task, run_id=run_id))
                        await ws.send_json({"type": "hive.queued", "agent": agent, "run_id": run_id})
                    else:
                        await ws.send_json({"type": "hive.error", "error": "agent and task required"})
            elif msg.type == web.WSMsgType.ERROR:
                log.warning("ws error: %s", ws.exception())
                break
    finally:
        _ws_clients.discard(ws)
    return ws


@routes.get("/api/hive/stream")
async def sse_stream(request: web.Request) -> web.StreamResponse:
    """Server-Sent Events: same payload as WS, one-way, easy curl access."""
    resp = web.StreamResponse(
        status=200,
        reason="OK",
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
    await resp.prepare(request)
    q: asyncio.Queue = asyncio.Queue(maxsize=128)
    _sse_subscribers.add(q)
    try:
        await resp.write(b": hive stream ready\n\n")
        await resp.write(f"data: {json.dumps({'type': 'hive.hello', 'agents': list_agents()})}\n\n".encode("utf-8"))
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=15.0)
            except asyncio.TimeoutError:
                await resp.write(b": keepalive\n\n")
                continue
            await resp.write(f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8"))
    except (ConnectionResetError, asyncio.CancelledError, ConnectionError):
        pass
    finally:
        _sse_subscribers.discard(q)
    return resp


@routes.get("/api/hive/status")
async def status(_request: web.Request) -> web.Response:
    from ..bridges.hive_runner import get_registry_warnings, load_registry
    registry = load_registry()
    agents = registry.get("agents", {})
    enabled = sum(1 for a in agents.values() if a.get("enabled", True))
    return web.json_response({
        "ok": True,
        "agents_total": len(agents),
        "agents_enabled": enabled,
        "subscribers_ws": len(_ws_clients),
        "subscribers_sse": len(_sse_subscribers),
        "results_cached": len(_recent_results),
        "results_ring_size": _results_ring.maxlen,
        "registry_warnings": get_registry_warnings(),
    })
