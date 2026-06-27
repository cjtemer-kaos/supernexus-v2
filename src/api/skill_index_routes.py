"""
Skill Index API Routes - Lightweight skill search and discovery.

Endpoints:
- GET  /api/skills/index       → Full index stats
- GET  /api/skills/search      → Search skills by query
- GET  /api/skills/topics      → List all topics with counts
- GET  /api/skills/topic/{name} → Get skills by topic
- GET  /api/skills/suggest     → Suggest skills for a task
- GET  /api/skills/{name}      → Get specific skill manifest
- POST /api/skills/rebuild     → Force rebuild index
"""

from aiohttp import web
import logging
from pathlib import Path

logger = logging.getLogger("nexus-skill-index-routes")

# Global indexer instance
_indexer = None


def _get_indexer():
    """Lazy-load the skill indexer."""
    global _indexer
    if _indexer is None:
        from src.skills.skill_indexer import SkillIndexer
        # Usa el directorio de skills de SuperNEXUS
        skills_dir = Path(__file__).parent.parent / "skills" / "hub"
        _indexer = SkillIndexer(skills_dir)
        _indexer.build_index()
    return _indexer


async def handle_skill_index(request: web.Request) -> web.Response:
    """GET /api/skills/index - Get index statistics."""
    indexer = _get_indexer()
    stats = indexer.get_stats()
    return web.json_response(stats)


async def handle_skill_search(request: web.Request) -> web.Response:
    """GET /api/skills/search?q=react&limit=10 - Search skills."""
    query = request.query.get("q", "").strip()
    limit = int(request.query.get("limit", "20"))
    
    if not query:
        return web.json_response({"error": "Missing query parameter 'q'"}, status=400)
    
    indexer = _get_indexer()
    results = indexer.search(query, limit=limit)
    return web.json_response({
        "query": query,
        "count": len(results),
        "results": results,
    })


async def handle_skill_topics(request: web.Request) -> web.Response:
    """GET /api/skills/topics - List all topics with skill counts."""
    indexer = _get_indexer()
    topics = indexer.get_topics()
    
    # Sort by count descending
    sorted_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)
    
    return web.json_response({
        "total_topics": len(sorted_topics),
        "topics": [{"name": t, "count": c} for t, c in sorted_topics],
    })


async def handle_skill_by_topic(request: web.Request) -> web.Response:
    """GET /api/skills/topic/{topic} - Get skills by topic."""
    topic = request.match_info.get("topic", "").strip()
    if not topic:
        return web.json_response({"error": "Missing topic"}, status=400)
    
    indexer = _get_indexer()
    results = indexer.get_by_topic(topic)
    return web.json_response({
        "topic": topic,
        "count": len(results),
        "skills": results,
    })


async def handle_skill_suggest(request: web.Request) -> web.Response:
    """GET /api/skills/suggest?task=build+react+component&limit=5 - Suggest skills for task."""
    task = request.query.get("task", "").strip()
    limit = int(request.query.get("limit", "5"))
    
    if not task:
        return web.json_response({"error": "Missing task parameter"}, status=400)
    
    indexer = _get_indexer()
    suggestions = indexer.suggest_for_task(task, limit=limit)
    return web.json_response({
        "task": task,
        "count": len(suggestions),
        "suggestions": suggestions,
    })


async def handle_skill_get(request: web.Request) -> web.Response:
    """GET /api/skills/{name} - Get specific skill manifest."""
    name = request.match_info.get("name", "").strip()
    if not name:
        return web.json_response({"error": "Missing skill name"}, status=400)
    
    indexer = _get_indexer()
    skill = indexer.get_skill(name)
    
    if not skill:
        return web.json_response({"error": f"Skill not found: {name}"}, status=404)
    
    return web.json_response(skill)


async def handle_skill_rebuild(request: web.Request) -> web.Response:
    """POST /api/skills/rebuild - Force rebuild the skill index."""
    global _indexer
    
    from src.skills.skill_indexer import SkillIndexer
    skills_dir = Path(__file__).parent.parent.parent / "src" / "skills" / "hub"
    _indexer = SkillIndexer(skills_dir)
    stats = _indexer.build_index()
    
    return web.json_response({
        "success": True,
        "stats": stats,
    })


def register_skill_index_routes(app: web.Application) -> None:
    """Register all skill index routes."""
    app.router.add_get("/api/skills/index", handle_skill_index)
    app.router.add_get("/api/skills/search", handle_skill_search)
    app.router.add_get("/api/skills/topics", handle_skill_topics)
    app.router.add_get("/api/skills/topic/{topic}", handle_skill_by_topic)
    app.router.add_get("/api/skills/suggest", handle_skill_suggest)
    app.router.add_get("/api/skills/{name}", handle_skill_get)
    app.router.add_post("/api/skills/rebuild", handle_skill_rebuild)
    
    logger.info("Skill index routes registered")
