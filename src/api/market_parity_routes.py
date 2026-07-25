"""
Market Parity Routes — API endpoints for the 16 new core modules.

Exposes: TypedEvents, EpisodicMemory, CapabilitySecurity, PromptCompressor,
SelfImproving, SmartCodebaseIndexer, MultiFileEditor, TaskExecutor,
ContextManager, PlanningEngine, QualityJudge, AutoSkillCreator,
SkillLifecycle, Curator, LearningGraph, PlatformAdapter.

All routes are async, aiohttp-based, mounted under /api/v3/parity/.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from aiohttp import web

logger = logging.getLogger(__name__)

# ─── Lazy singletons ────────────────────────────────────────────────
_typed_events = None
_episodic_memory = None
_capability_security = None
_prompt_compressor = None
_self_improving = None
_indexer = None
_editor = None
_executor = None
_context_mgr = None
_planner = None
_judge = None
_skill_creator = None
_lifecycle = None
_curator = None
_learning_graph = None
_gateway_registry = None


def _te():
    global _typed_events
    if _typed_events is None:
        from src.core.typed_events import typed_event_bus
        _typed_events = typed_event_bus
    return _typed_events


def _ep():
    global _episodic_memory
    if _episodic_memory is None:
        from src.brain.episodic_memory import EpisodicMemory
        _episodic_memory = EpisodicMemory.instance()
    return _episodic_memory


def _cs():
    global _capability_security
    if _capability_security is None:
        from src.core.capability_security import get_capability_manager
        _capability_security = get_capability_manager()
    return _capability_security


def _pc():
    global _prompt_compressor
    if _prompt_compressor is None:
        from src.core.prompt_compressor import get_compressor
        _prompt_compressor = get_compressor()
    return _prompt_compressor


def _si():
    global _self_improving
    if _self_improving is None:
        from src.core.self_improving import get_self_improving_loop
        _self_improving = get_self_improving_loop()
    return _self_improving


def _ix():
    global _indexer
    if _indexer is None:
        from src.core.smart_codebase_indexer import get_indexer
        _indexer = get_indexer()
    return _indexer


def _ed():
    global _editor
    if _editor is None:
        from src.core.multi_file_editor import get_editor
        _editor = get_editor()
    return _editor


def _ex():
    global _executor
    if _executor is None:
        from src.core.task_executor import get_executor
        _executor = get_executor()
    return _executor


def _cm():
    global _context_mgr
    if _context_mgr is None:
        from src.core.context_manager import get_context_manager
        _context_mgr = get_context_manager()
    return _context_mgr


def _pl():
    global _planner
    if _planner is None:
        from src.core.planning_engine import get_planner
        _planner = get_planner()
    return _planner


def _qj():
    global _judge
    if _judge is None:
        from src.core.quality_judge import get_judge
        _judge = get_judge()
    return _judge


def _asc():
    global _skill_creator
    if _skill_creator is None:
        from src.core.auto_skill_creator import get_skill_creator
        _skill_creator = get_skill_creator()
    return _skill_creator


def _sl():
    global _lifecycle
    if _lifecycle is None:
        from src.core.skill_lifecycle import get_lifecycle_manager
        _lifecycle = get_lifecycle_manager()
    return _lifecycle


def _cu():
    global _curator
    if _curator is None:
        from src.core.curator import get_curator
        _curator = get_curator()
    return _curator


def _lg():
    global _learning_graph
    if _learning_graph is None:
        from src.core.learning_graph import get_learning_graph
        _learning_graph = get_learning_graph()
    return _learning_graph


def _gr():
    global _gateway_registry
    if _gateway_registry is None:
        from src.gateways.platform_adapter import get_gateway_registry
        _gateway_registry = get_gateway_registry()
    return _gateway_registry


# ─── Helpers ─────────────────────────────────────────────────────────
def _json_ok(data, status=200):
    return web.json_response(data, status=status)


def _json_err(msg, status=400):
    return web.json_response({"error": msg}, status=status)


# ─── Typed Events ────────────────────────────────────────────────────
async def events_stats(request):
    """GET /api/v3/parity/events/stats"""
    return _json_ok(_te().get_stats())


async def events_history(request):
    """GET /api/v3/parity/events/history?limit=50"""
    limit = int(request.query.get("limit", 50))
    return _json_ok({"history": _te().get_history(limit)})


async def events_publish(request):
    """POST /api/v3/parity/events/publish — body: {event_type, data}"""
    body = await request.json()
    event_type = body.get("event_type", "")
    data = body.get("data", {})
    from src.core.typed_events import NexusEvent
    ev = NexusEvent(event_type=event_type, data=data)
    await _te().publish(ev)
    return _json_ok({"published": event_type})


# ─── Episodic Memory ────────────────────────────────────────────────
async def episodic_create(request):
    """POST /api/v3/parity/episodic/create"""
    body = await request.json()
    ep_id = _ep().create_episode(
        what=body.get("what", ""),
        why=body.get("why", ""),
        where_text=body.get("where", ""),
        learned=body.get("learned", ""),
        category=body.get("category", "general"),
        importance=body.get("importance", 0.5),
        tags=body.get("tags", []),
    )
    return _json_ok({"id": ep_id})


async def episodic_search(request):
    """GET /api/v3/parity/episodic/search?q=...&limit=10"""
    q = request.query.get("q", "")
    limit = int(request.query.get("limit", 10))
    results = _ep().search(q, limit=limit)
    return _json_ok({"results": results})


async def episodic_stats(request):
    """GET /api/v3/parity/episodic/stats"""
    return _json_ok(_ep().get_stats())


# ─── Capability Security ────────────────────────────────────────────
async def caps_list(request):
    """GET /api/v3/parity/caps"""
    caps = _cs().list_all()
    return _json_ok({"capabilities": {k: v.to_dict() for k, v in caps.items()}})


async def caps_check(request):
    """GET /api/v3/parity/caps/check?agent=...&capability=..."""
    agent = request.query.get("agent", "default")
    cap = request.query.get("capability", "")
    allowed = _cs().check_permission(agent, cap)
    return _json_ok({"allowed": allowed})


async def caps_audit(request):
    """GET /api/v3/parity/caps/audit"""
    return _json_ok({"audit_log": _cs().get_audit_log(limit=100)})


# ─── Prompt Compression ────────────────────────────────────────────
async def compress_prompt(request):
    """POST /api/v3/parity/compress — body: {prompt, ratio}"""
    body = await request.json()
    prompt = body.get("prompt", "")
    ratio = body.get("ratio", 0.5)
    compressed, savings = _pc().compress(prompt, target_ratio=ratio)
    return _json_ok({
        "compressed": compressed,
        "original_tokens": _pc().estimate_tokens(prompt),
        "compressed_tokens": _pc().estimate_tokens(compressed),
        "savings_pct": round(savings * 100, 1),
    })


# ─── Self-Improving Loop ───────────────────────────────────────────
async def selfimprove_stats(request):
    """GET /api/v3/parity/selfimprove/stats"""
    return _json_ok(_si().get_stats())


async def selfimprove_experiments(request):
    """GET /api/v3/parity/selfimprove/experiments"""
    return _json_ok({"experiments": _si().list_experiments()})


async def selfimprove_log(request):
    """POST /api/v3/parity/selfimprove/log — body: {name, task_type}"""
    body = await request.json()
    exp_id = _si().log_experiment(
        name=body.get("name", ""),
        task_type=body.get("task_type", ""),
    )
    return _json_ok({"id": exp_id})


# ─── Smart Codebase Indexer ────────────────────────────────────────
async def indexer_index(request):
    """POST /api/v3/parity/indexer/index — body: {path}"""
    body = await request.json()
    path = body.get("path", ".")
    stats = _ix().index_directory(path)
    return _json_ok(stats)


async def indexer_search(request):
    """GET /api/v3/parity/indexer/search?q=...&language=...&limit=10"""
    q = request.query.get("q", "")
    lang = request.query.get("language")
    limit = int(request.query.get("limit", 10))
    results = _ix().search_code(q, language=lang, limit=limit)
    return _json_ok({"results": results})


async def indexer_symbol(request):
    """GET /api/v3/parity/indexer/symbol?name=..."""
    name = request.query.get("name", "")
    info = _ix().get_symbol_info(name)
    return _json_ok(info or {"error": "Symbol not found"})


# ─── Multi-File Editor ─────────────────────────────────────────────
async def editor_apply(request):
    """POST /api/v3/parity/editor/apply — body: {filepath, old_text, new_text}"""
    body = await request.json()
    result = _ed().apply_edit(
        body.get("filepath", ""),
        body.get("old_text", ""),
        body.get("new_text", ""),
    )
    return _json_ok(result.to_dict())


async def editor_preview(request):
    """POST /api/v3/parity/editor/preview"""
    body = await request.json()
    diff = _ed().preview_edit(
        body.get("filepath", ""),
        body.get("old_text", ""),
        body.get("new_text", ""),
    )
    return _json_ok({"diff": diff})


async def editor_undo(request):
    """POST /api/v3/parity/editor/undo — body: {filepath}"""
    body = await request.json()
    ok = _ed().undo_last(body.get("filepath", ""))
    return _json_ok({"success": ok})


# ─── Task Executor ──────────────────────────────────────────────────
async def executor_create(request):
    """POST /api/v3/parity/executor/create — body: {goal}"""
    body = await request.json()
    task_id = _ex().create_task(body.get("goal", ""))
    return _json_ok({"task_id": task_id})


async def executor_add_step(request):
    """POST /api/v3/parity/executor/step — body: {task_id, description, action, params}"""
    body = await request.json()
    step_id = _ex().add_step(
        body["task_id"], body["description"],
        body.get("action", ""), body.get("params", {}),
        rollback_action=body.get("rollback_action"),
    )
    return _json_ok({"step_id": step_id})


async def executor_start(request):
    """POST /api/v3/parity/executor/start — body: {task_id}"""
    body = await request.json()
    _ex().start_task(body["task_id"])
    return _json_ok({"started": True})


async def executor_rollback(request):
    """POST /api/v3/parity/executor/rollback — body: {task_id}"""
    body = await request.json()
    ok = _ex().rollback_task(body["task_id"])
    return _json_ok({"rolled_back": ok})


async def executor_stats(request):
    """GET /api/v3/parity/executor/stats"""
    return _json_ok(_ex().get_stats())


async def executor_active(request):
    """GET /api/v3/parity/executor/active"""
    return _json_ok({"tasks": _ex().get_active_tasks()})


# ─── Context Manager ────────────────────────────────────────────────
async def context_add(request):
    """POST /api/v3/parity/context/add"""
    body = await request.json()
    _cm().add_context(
        body.get("context_id", ""),
        body.get("content", ""),
        body.get("source", ""),
        relevance=body.get("relevance", 0.5),
        ttl_seconds=body.get("ttl_seconds"),
    )
    return _json_ok({"added": True})


async def context_relevant(request):
    """GET /api/v3/parity/context/relevant?q=...&limit=10"""
    q = request.query.get("q", "")
    limit = int(request.query.get("limit", 10))
    items = _cm().get_relevant_context(q, limit=limit)
    return _json_ok({"items": [i.to_dict() for i in items]})


async def context_compress(request):
    """POST /api/v3/parity/context/compress — body: {max_tokens}"""
    body = await request.json()
    text = _cm().compress_context(max_tokens=body.get("max_tokens", 4000))
    return _json_ok({"compressed": text})


async def context_stats(request):
    """GET /api/v3/parity/context/stats"""
    return _json_ok(_cm().get_stats())


# ─── Planning Engine ────────────────────────────────────────────────
async def plan_create(request):
    """POST /api/v3/parity/plan/create"""
    body = await request.json()
    plan_id = _pl().create_plan(body.get("goal", ""), body.get("steps", []))
    return _json_ok({"plan_id": plan_id})


async def plan_get(request):
    """GET /api/v3/parity/plan/{plan_id}"""
    plan_id = request.match_info["plan_id"]
    plan = _pl().get_plan(plan_id)
    if plan is None:
        return _json_err("Plan not found", 404)
    return _json_ok(plan.to_dict())


async def plan_active(request):
    """GET /api/v3/parity/plan/active"""
    plan = _pl().get_active_plan()
    return _json_ok(plan.to_dict() if plan else {"active": False})


async def plan_export(request):
    """GET /api/v3/parity/plan/{plan_id}/export"""
    plan_id = request.match_info["plan_id"]
    md = _pl().export_plan(plan_id)
    if md is None:
        return _json_err("Plan not found", 404)
    return _json_ok({"markdown": md})


async def plan_stats(request):
    """GET /api/v3/parity/plan/stats"""
    return _json_ok(_pl().get_stats())


# ─── Quality Judge ──────────────────────────────────────────────────
async def judge_response(request):
    """POST /api/v3/parity/judge/response"""
    body = await request.json()
    score = _qj().judge_response(
        body.get("query", ""),
        body.get("response", ""),
        context=body.get("context"),
    )
    return _json_ok(score.to_dict())


async def judge_code(request):
    """POST /api/v3/parity/judge/code"""
    body = await request.json()
    score = _qj().judge_code(
        body.get("filepath", ""),
        body.get("code", ""),
        tests_pass=body.get("tests_pass"),
    )
    return _json_ok(score.to_dict())


async def judge_stats(request):
    """GET /api/v3/parity/judge/stats"""
    return _json_ok(_qj().get_stats())


# ─── Auto Skill Creator ────────────────────────────────────────────
async def skill_create(request):
    """POST /api/v3/parity/skill/create"""
    body = await request.json()
    skill_id = _asc().create_skill(
        body.get("name", ""),
        body.get("content", ""),
        category=body.get("category", ""),
        tags=body.get("tags", []),
    )
    return _json_ok({"skill_id": skill_id})


async def skill_search(request):
    """GET /api/v3/parity/skill/search?q=...&category=...&limit=10"""
    q = request.query.get("q", "")
    cat = request.query.get("category")
    limit = int(request.query.get("limit", 10))
    results = _asc().search_skills(q, category=cat, limit=limit)
    return _json_ok({"skills": [s.to_dict() for s in results]})


async def skill_stats(request):
    """GET /api/v3/parity/skill/stats"""
    return _json_ok(_asc().get_stats())


# ─── Skill Lifecycle ────────────────────────────────────────────────
async def lifecycle_scan(request):
    """POST /api/v3/parity/lifecycle/scan"""
    changes = _sl().scan_and_update()
    return _json_ok({"changes": changes})


async def lifecycle_stats(request):
    """GET /api/v3/parity/lifecycle/stats"""
    return _json_ok(_sl().get_lifecycle_stats())


async def lifecycle_pin(request):
    """POST /api/v3/parity/lifecycle/pin — body: {skill_id}"""
    body = await request.json()
    _sl().pin(body["skill_id"])
    return _json_ok({"pinned": True})


# ─── Curator ────────────────────────────────────────────────────────
async def curator_dedup(request):
    """GET /api/v3/parity/curator/duplicates"""
    dupes = _cu().find_duplicate_skills()
    return _json_ok({"duplicates": dupes})


async def curator_consolidate(request):
    """GET /api/v3/parity/curator/consolidate"""
    suggestions = _cu().suggest_consolidation()
    return _json_ok({"suggestions": suggestions})


async def curator_stats(request):
    """GET /api/v3/parity/curator/stats"""
    return _json_ok(_cu().get_stats())


# ─── Learning Graph ────────────────────────────────────────────────
async def learning_add_node(request):
    """POST /api/v3/parity/learning/node"""
    body = await request.json()
    node_id = _lg().add_node(
        body.get("label", ""),
        body.get("type", "SKILL"),
        level=body.get("level", 1),
    )
    return _json_ok({"node_id": node_id})


async def learning_add_edge(request):
    """POST /api/v3/parity/learning/edge"""
    body = await request.json()
    ok = _lg().add_edge(
        body["from_id"], body["to_id"],
        body.get("relationship", "RELATED_TO"),
    )
    return _json_ok({"created": ok})


async def learning_progress(request):
    """GET /api/v3/parity/learning/progress"""
    report = _lg().get_progress()
    return _json_ok(report.to_dict())


async def learning_mermaid(request):
    """GET /api/v3/parity/learning/mermaid"""
    return _json_ok({"mermaid": _lg().export_mermaid()})


async def learning_stats(request):
    """GET /api/v3/parity/learning/stats"""
    from dataclasses import asdict
    stats = _lg().get_stats()
    return _json_ok(asdict(stats) if hasattr(stats, "__dataclass_fields__") else stats)


async def learning_timeline(request):
    """GET /api/v3/parity/learning/timeline?days=7"""
    days = int(request.query.get("days", 7))
    return _json_ok({"timeline": _lg().get_timeline(days)})


# ─── Voice Engine ─────────────────────────────────────────────────
_voice_engine = None


def _ve():
    global _voice_engine
    if _voice_engine is None:
        from src.core.voice_engine import get_engine
        _voice_engine = get_engine()
    return _voice_engine


async def voice_status(request):
    """GET /api/v3/parity/voice/status"""
    return _json_ok(_ve().get_status())


async def voice_tts(request):
    """POST /api/v3/parity/voice/speak — body: {text, out_path?}"""
    body = await request.json()
    text = body.get("text", "")
    out_path = body.get("out_path")
    result = _ve().speak(text, out_path)
    return _json_ok({"audio_path": result, "text": text})


async def voice_tts_bytes(request):
    """POST /api/v3/parity/voice/speak-bytes — body: {text} → returns WAV"""
    body = await request.json()
    text = body.get("text", "")
    audio = _ve().speak_bytes(text)
    if audio is None:
        return _json_err("TTS not available or synthesis failed", 503)
    return web.Response(body=audio, content_type="audio/wav")


async def voice_stt(request):
    """POST /api/v3/parity/voice/transcribe — upload WAV file, return text"""
    reader = await request.multipart()
    field = await reader.next()
    if field is None:
        return _json_err("No file uploaded")
    audio_bytes = await field.read()
    language = request.query.get("language", "es")
    result = _ve().transcribe_bytes(audio_bytes, language=language)
    return _json_ok(result)


async def voice_push_to_talk_start(request):
    """POST /api/v3/parity/voice/ptt/start"""
    ok = _ve().start_recording()
    return _json_ok({"recording": ok})


async def voice_push_to_talk_stop(request):
    """POST /api/v3/parity/voice/ptt/stop — stop recording + transcribe"""
    result = _ve().stop_recording()
    return _json_ok(result)


async def voice_voices(request):
    """GET /api/v3/parity/voice/voices"""
    voices = _ve().get_voices() if _ve().available else []
    return _json_ok({"voices": voices})


async def voice_set_voice(request):
    """POST /api/v3/parity/voice/set — body: {name}"""
    body = await request.json()
    ok = _ve().set_voice(body.get("name", ""))
    return _json_ok({"success": ok})


# ─── Platform Gateway ──────────────────────────────────────────────
async def gateway_platforms(request):
    """GET /api/v3/parity/gateway/platforms"""
    return _json_ok({"platforms": _gr().list_platforms()})


async def gateway_active(request):
    """GET /api/v3/parity/gateway/active"""
    return _json_ok({"active": _gr().get_active_platforms()})


# ─── Mount all routes ───────────────────────────────────────────────
def register_parity_routes(app: web.Application):
    """Register all market parity routes on the aiohttp app."""
    routes = [
        # Events
        web.get("/api/v3/parity/events/stats", events_stats),
        web.get("/api/v3/parity/events/history", events_history),
        web.post("/api/v3/parity/events/publish", events_publish),
        # Episodic Memory
        web.post("/api/v3/parity/episodic/create", episodic_create),
        web.get("/api/v3/parity/episodic/search", episodic_search),
        web.get("/api/v3/parity/episodic/stats", episodic_stats),
        # Capability Security
        web.get("/api/v3/parity/caps", caps_list),
        web.get("/api/v3/parity/caps/check", caps_check),
        web.get("/api/v3/parity/caps/audit", caps_audit),
        # Prompt Compression
        web.post("/api/v3/parity/compress", compress_prompt),
        # Self-Improving
        web.get("/api/v3/parity/selfimprove/stats", selfimprove_stats),
        web.get("/api/v3/parity/selfimprove/experiments", selfimprove_experiments),
        web.post("/api/v3/parity/selfimprove/log", selfimprove_log),
        # Codebase Indexer
        web.post("/api/v3/parity/indexer/index", indexer_index),
        web.get("/api/v3/parity/indexer/search", indexer_search),
        web.get("/api/v3/parity/indexer/symbol", indexer_symbol),
        # Multi-File Editor
        web.post("/api/v3/parity/editor/apply", editor_apply),
        web.post("/api/v3/parity/editor/preview", editor_preview),
        web.post("/api/v3/parity/editor/undo", editor_undo),
        # Task Executor
        web.post("/api/v3/parity/executor/create", executor_create),
        web.post("/api/v3/parity/executor/step", executor_add_step),
        web.post("/api/v3/parity/executor/start", executor_start),
        web.post("/api/v3/parity/executor/rollback", executor_rollback),
        web.get("/api/v3/parity/executor/stats", executor_stats),
        web.get("/api/v3/parity/executor/active", executor_active),
        # Context Manager
        web.post("/api/v3/parity/context/add", context_add),
        web.get("/api/v3/parity/context/relevant", context_relevant),
        web.post("/api/v3/parity/context/compress", context_compress),
        web.get("/api/v3/parity/context/stats", context_stats),
        # Planning Engine
        web.post("/api/v3/parity/plan/create", plan_create),
        web.get("/api/v3/parity/plan/active", plan_active),
        web.get("/api/v3/parity/plan/stats", plan_stats),
        web.get("/api/v3/parity/plan/{plan_id}", plan_get),
        web.get("/api/v3/parity/plan/{plan_id}/export", plan_export),
        # Quality Judge
        web.post("/api/v3/parity/judge/response", judge_response),
        web.post("/api/v3/parity/judge/code", judge_code),
        web.get("/api/v3/parity/judge/stats", judge_stats),
        # Auto Skill Creator
        web.post("/api/v3/parity/skill/create", skill_create),
        web.get("/api/v3/parity/skill/search", skill_search),
        web.get("/api/v3/parity/skill/stats", skill_stats),
        # Skill Lifecycle
        web.post("/api/v3/parity/lifecycle/scan", lifecycle_scan),
        web.get("/api/v3/parity/lifecycle/stats", lifecycle_stats),
        web.post("/api/v3/parity/lifecycle/pin", lifecycle_pin),
        # Curator
        web.get("/api/v3/parity/curator/duplicates", curator_dedup),
        web.get("/api/v3/parity/curator/consolidate", curator_consolidate),
        web.get("/api/v3/parity/curator/stats", curator_stats),
        # Learning Graph
        web.post("/api/v3/parity/learning/node", learning_add_node),
        web.post("/api/v3/parity/learning/edge", learning_add_edge),
        web.get("/api/v3/parity/learning/progress", learning_progress),
        web.get("/api/v3/parity/learning/mermaid", learning_mermaid),
        web.get("/api/v3/parity/learning/stats", learning_stats),
        web.get("/api/v3/parity/learning/timeline", learning_timeline),
        # Voice Engine
        web.get("/api/v3/parity/voice/status", voice_status),
        web.post("/api/v3/parity/voice/speak", voice_tts),
        web.post("/api/v3/parity/voice/speak-bytes", voice_tts_bytes),
        web.post("/api/v3/parity/voice/transcribe", voice_stt),
        web.post("/api/v3/parity/voice/ptt/start", voice_push_to_talk_start),
        web.post("/api/v3/parity/voice/ptt/stop", voice_push_to_talk_stop),
        web.get("/api/v3/parity/voice/voices", voice_voices),
        web.post("/api/v3/parity/voice/set", voice_set_voice),
        # Platform Gateway
        web.get("/api/v3/parity/gateway/platforms", gateway_platforms),
        web.get("/api/v3/parity/gateway/active", gateway_active),
    ]
    app.router.add_routes(routes)
    logger.info(f"Registered {len(routes)} market parity routes under /api/v3/parity/")
