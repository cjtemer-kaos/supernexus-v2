"""
Model Registry API routes — CRUD providers, probe, active model management.

aiohttp handlers (server uses aiohttp, not FastAPI).
"""
import json
import logging
from aiohttp import web

from src.core.model_registry import get_model_registry, ProviderConfig

logger = logging.getLogger("nexus.api.models")


def register_model_routes(app: web.Application):
    """Registra todas las rutas del model registry en la app aiohttp."""
    app.router.add_get("/api/models", handle_get_models)
    app.router.add_get("/api/models/active", handle_get_active)
    app.router.add_post("/api/models/active", handle_set_active)
    app.router.add_get("/api/models/providers", handle_list_providers)
    app.router.add_post("/api/models/providers", handle_create_provider)
    app.router.add_patch("/api/models/providers/{provider_id}", handle_update_provider)
    app.router.add_delete("/api/models/providers/{provider_id}", handle_delete_provider)
    app.router.add_post("/api/models/providers/{provider_id}/probe", handle_probe_provider)
    app.router.add_post("/api/models/auto-detect", handle_auto_detect)
    logger.info("Model registry routes registered")


async def handle_get_models(request: web.Request) -> web.Response:
    """GET /api/models — Estado completo."""
    reg = get_model_registry()
    return web.json_response(reg.to_api_response())


async def handle_get_active(request: web.Request) -> web.Response:
    """GET /api/models/active — Modelo activo actual."""
    reg = get_model_registry()
    active = reg.get_active()
    full = reg.get_active_model_full()
    return web.json_response({**active, "info": full})


async def handle_set_active(request: web.Request) -> web.Response:
    """POST /api/models/active — Cambiar modelo activo."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    provider_id = data.get("provider_id", "")
    model = data.get("model", "")

    if not provider_id or not model:
        return web.json_response({"error": "'provider_id' and 'model' required"}, status=400)

    reg = get_model_registry()

    # Auto-agregar modelo si el provider existe pero no tiene el modelo
    if provider_id in reg.providers:
        p = reg.providers[provider_id]
        if model not in p.models:
            p.models.append(model)
            reg.save()
    else:
        return web.json_response({"error": f"Provider '{provider_id}' not found"}, status=404)

    reg.set_active(provider_id, model)

    # Also update ai_tools.default_model on the backend director
    try:
        backend = request.app.get("backend")
        if backend and hasattr(backend, "ai_tools"):
            backend.ai_tools.default_model = model
            backend.ai_tools._user_selected_model = model
    except Exception:
        pass

    return web.json_response({"ok": True, "active": reg.get_active()})


async def handle_list_providers(request: web.Request) -> web.Response:
    """GET /api/models/providers — Listar providers."""
    reg = get_model_registry()
    return web.json_response({"providers": [p.__dict__ for p in reg.providers.values()]})


async def handle_create_provider(request: web.Request) -> web.Response:
    """POST /api/models/providers — Agregar provider."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    required = ["id", "name", "base_url"]
    for field in required:
        if not data.get(field):
            return web.json_response({"error": f"'{field}' required"}, status=400)

    reg = get_model_registry()
    if data["id"] in reg.providers:
        return web.json_response({"error": f"Provider '{data['id']}' already exists"}, status=409)

    provider = ProviderConfig(
        id=data["id"],
        name=data["name"],
        type=data.get("type", "openai"),
        base_url=data["base_url"],
        api_key=data.get("api_key", ""),
        enabled=data.get("enabled", True),
        models=data.get("models", []),
        is_free=data.get("is_free", False),
    )
    reg.add_provider(provider)
    return web.json_response({"ok": True, "provider": provider.__dict__})


async def handle_update_provider(request: web.Request) -> web.Response:
    """PATCH /api/models/providers/{provider_id} — Editar provider."""
    provider_id = request.match_info["provider_id"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    reg = get_model_registry()
    result = reg.update_provider(provider_id, data)
    if not result:
        return web.json_response({"error": f"Provider '{provider_id}' not found"}, status=404)
    return web.json_response({"ok": True, "provider": result.__dict__})


async def handle_delete_provider(request: web.Request) -> web.Response:
    """DELETE /api/models/providers/{provider_id} — Eliminar provider."""
    provider_id = request.match_info["provider_id"]
    reg = get_model_registry()
    if not reg.remove_provider(provider_id):
        return web.json_response({"error": f"Provider '{provider_id}' not found"}, status=404)
    return web.json_response({"ok": True})


async def handle_probe_provider(request: web.Request) -> web.Response:
    """POST /api/models/providers/{provider_id}/probe — Auto-detectar modelos."""
    provider_id = request.match_info["provider_id"]
    reg = get_model_registry()
    p = reg.providers.get(provider_id)
    if not p:
        return web.json_response({"error": f"Provider '{provider_id}' not found"}, status=404)

    if p.type == "ollama":
        models = await reg.probe_ollama(p.base_url)
    else:
        models = await reg.probe_openai_compatible(p.base_url, p.api_key)

    if models:
        p.models = models
        reg.save()

    return web.json_response({"ok": True, "models": models, "count": len(models)})


async def handle_auto_detect(request: web.Request) -> web.Response:
    """POST /api/models/auto-detect — Auto-detectar Ollama."""
    reg = get_model_registry()
    ollama_models = await reg.auto_detect_ollama()
    return web.json_response({
        "ok": True,
        "ollama": {"models": ollama_models, "count": len(ollama_models)},
    })
