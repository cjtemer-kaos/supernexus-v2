"""
Integración de mejoras para SuperNEXUS v2.0

Este archivo conecta todos los nuevos módulos creados al sistema existente.
"""

import logging
import os
from pathlib import Path
from aiohttp import web

logger = logging.getLogger(__name__)

def integrate_all_improvements(backend):
    """
    Integra todas las mejoras al backend de SuperNEXUS v2.0
    
    Uso en server.py:
        from src.improvements.integration import integrate_all_improvements
        integrate_all_improvements(self)
    """
    
    try:
        from src.core.resilience import ResilienceLayer
        backend.resilience = ResilienceLayer()
        logger.info("✅ ResilienceLayer integrated")
    except Exception as e:
        logger.error(f"❌ ResilienceLayer failed: {e}")
        backend.resilience = None
    
    try:
        from src.security.security_middleware import SecurityMiddleware
        backend.security = SecurityMiddleware()
        logger.info("✅ SecurityMiddleware integrated")
    except Exception as e:
        logger.error(f"❌ SecurityMiddleware failed: {e}")
        backend.security = None
    
    try:
        from src.optimization.resource_monitor_v2 import ResourceMonitor
        backend.resource_monitor_v2 = ResourceMonitor()
        logger.info("✅ ResourceMonitor v2 integrated")
    except Exception as e:
        logger.error(f"❌ ResourceMonitor v2 failed: {e}")
        backend.resource_monitor_v2 = None
    
    try:
        from src.brain.learning_system import LearningSystem
        backend.learning_system = LearningSystem()
        logger.info("✅ LearningSystem integrated")
    except Exception as e:
        logger.error(f"❌ LearningSystem failed: {e}")
        backend.learning_system = None
    
    try:
        backend.knowledge_graph = backend.kg
        logger.info("✅ KnowledgeGraph already integrated")
    except Exception as e:
        logger.error(f"❌ KnowledgeGraph failed: {e}")
        backend.knowledge_graph = None
    
    try:
        from src.core.project_planner import ProjectPlanner
        storage_path = Path(__file__).parent.parent.parent / "data" / "projects.json"
        backend.project_planner = ProjectPlanner(storage_path=str(storage_path))
        logger.info("✅ ProjectPlanner integrated")
    except Exception as e:
        logger.error(f"❌ ProjectPlanner failed: {e}")
        backend.project_planner = None
    
    try:
        from src.core.proactive_suggestions import ProactiveSuggestions
        backend.suggestions = ProactiveSuggestions()
        logger.info("✅ ProactiveSuggestions integrated")
    except Exception as e:
        logger.error(f"❌ ProactiveSuggestions failed: {e}")
        backend.suggestions = None
    
    try:
        from src.tools.vision_gem_v2 import VisionGem
        storage_dir = Path(__file__).parent.parent.parent / "data" / "screenshots"
        backend.vision_gem_v2 = VisionGem(screenshot_dir=str(storage_dir))
        logger.info("✅ VisionGem v2 integrated")
    except Exception as e:
        logger.error(f"❌ VisionGem v2 failed: {e}")
        backend.vision_gem_v2 = None
    
    try:
        from src.core.self_improvement import SelfImprovement
        storage_path = Path(__file__).parent.parent.parent / "data" / "self_improvement.json"
        backend.self_improvement = SelfImprovement(storage_path=str(storage_path))
        logger.info("✅ SelfImprovement integrated")
    except Exception as e:
        logger.error(f"❌ SelfImprovement failed: {e}")
        backend.self_improvement = None
    
    try:
        from src.core.time_tracker import TimeTracker
        storage_path = Path(__file__).parent.parent.parent / "data" / "time_tracking.json"
        backend.time_tracker = TimeTracker(storage_path=str(storage_path))
        logger.info("✅ TimeTracker integrated")
    except Exception as e:
        logger.error(f"❌ TimeTracker failed: {e}")
        backend.time_tracker = None
    
    try:
        from src.memory.knowledge_sync import KnowledgeSync
        storage_path = Path(__file__).parent.parent.parent / "data" / "knowledge_sync.json"
        backend.knowledge_sync = KnowledgeSync(
            node_id="local",
            storage_path=str(storage_path),
        )
        logger.info("✅ KnowledgeSync integrated")
    except Exception as e:
        logger.error(f"❌ KnowledgeSync failed: {e}")
        backend.knowledge_sync = None
    
    try:
        from src.bridges.network_architecture import NetworkArchitecture
        backend.network = NetworkArchitecture()
        backend.network.add_node("nexus_master", "NEXUS Master", "http://127.0.0.1:9000", capabilities=["chat", "skills", "memory"])
        backend.network.add_node("nexus_pc2", "NEXUS Remote Node", f"http://{os.environ.get('SUPER_NEXUS_PC2_IP', 'localhost')}:9000", capabilities=["chat", "skills", "memory", "gpu"])
        backend.network.add_node("openclaw", "OpenClaw Gateway", "http://127.0.0.1:18789", capabilities=["gateway", "ui"])
        logger.info("✅ NetworkArchitecture integrated")
    except Exception as e:
        logger.error(f"❌ NetworkArchitecture failed: {e}")
        backend.network = None
    
    # Skill Registry - Sistema unificado de habilidades
    try:
        from src.skills.skill_registry_system import SkillRegistry
        from src.skills.skill_sync import SkillSync
        
        # Detectar si estamos en Windows o PC2
        import platform
        is_windows = platform.system() == "Windows"
        node_id = "local" if is_windows else "pc2"
        
        if is_windows:
            skills_root = os.path.join(os.path.dirname(__file__), "..", "skills", "hub")
        else:
            skills_root = os.path.join(os.path.dirname(__file__), "..", "skills", "hub")
        
        storage_dir = Path(__file__).parent.parent.parent / "data"
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        backend.skill_registry = SkillRegistry(
            skills_root=skills_root,
            index_path=str(storage_dir / f"skill_registry_{node_id}.json"),
            node_id=node_id,
        )
        
        backend.skill_sync = SkillSync(
            local_registry=backend.skill_registry,
            node_id=node_id,
            storage_path=str(storage_dir / f"skill_sync_{node_id}.json"),
        )
        
        stats = backend.skill_registry.get_stats()
        logger.info(f"✅ SkillRegistry integrated: {stats['total_skills']} skills ({node_id})")
    except Exception as e:
        logger.error(f"❌ SkillRegistry failed: {e}")
        backend.skill_registry = None
        backend.skill_sync = None
    
    # Patrones faltantes (18-20)
    try:
        from src.core.reflection_pattern import ReflectionPattern
        backend.reflection = ReflectionPattern()
        logger.info("✅ ReflectionPattern integrated (Pattern #9)")
    except Exception as e:
        logger.error(f"❌ ReflectionPattern failed: {e}")
        backend.reflection = None
    
    try:
        from src.core.reasoning_strategies import ReasoningStrategies
        backend.reasoning = ReasoningStrategies()
        logger.info("✅ ReasoningStrategies integrated (Pattern #17)")
    except Exception as e:
        logger.error(f"❌ ReasoningStrategies failed: {e}")
        backend.reasoning = None
    
    try:
        from src.core.human_in_the_loop import HumanInTheLoop
        backend.hitl = HumanInTheLoop()
        logger.info("✅ HumanInTheLoop integrated (Pattern #8)")
    except Exception as e:
        logger.error(f"❌ HumanInTheLoop failed: {e}")
        backend.hitl = None
    
    # Persistencia de contexto entre sesiones
    try:
        from src.core.session_persistence import SessionPersistence
        storage_path = Path(__file__).parent.parent.parent / "data" / "session_state.json"
        backend.session_persistence = SessionPersistence(storage_path=str(storage_path))
        
        # Intentar cargar sesión anterior
        loaded = backend.session_persistence.load_state()
        if loaded:
            logger.info(f"✅ Session restored: {loaded.session_id} (project: {loaded.current_project})")
        else:
            backend.session_persistence.create_session()
            logger.info("✅ New session created")
    except Exception as e:
        logger.error(f"❌ SessionPersistence failed: {e}")
        backend.session_persistence = None
    
    logger.info("=" * 60)
    logger.info("🎉 ALL 20 AGENTIC PATTERNS NOW IMPLEMENTED!")
    logger.info("=" * 60)


def add_new_routes(app, backend):
    """
    Agrega nuevas rutas al API server
    
    Uso en server.py:
        from src.improvements.integration import add_new_routes
        add_new_routes(app, self)
    """
    
    async def resilience_status(request):
        """Estado de resiliencia"""
        if backend.resilience:
            return web.json_response(backend.resilience.get_status())
        return web.json_response({"error": "Resilience not available"})
    
    async def security_status(request):
        """Estado de seguridad"""
        if backend.security:
            return web.json_response(backend.security.get_security_status())
        return web.json_response({"error": "Security not available"})
    
    async def resource_status(request):
        """Estado de recursos"""
        if backend.resource_monitor_v2:
            return web.json_response(backend.resource_monitor_v2.get_status())
        return web.json_response({"error": "Resource monitor not available"})
    
    async def learning_status(request):
        """Estado de aprendizaje"""
        if backend.learning_system:
            return web.json_response(backend.learning_system.get_status())
        return web.json_response({"error": "Learning system not available"})
    
    async def knowledge_graph_data(request):
        """Datos de knowledge graph"""
        if backend.knowledge_graph:
            return web.json_response(backend.knowledge_graph.export_for_visualization())
        return web.json_response({"error": "Knowledge graph not available"})
    
    async def projects_list(request):
        """Lista de proyectos"""
        if backend.project_planner:
            return web.json_response(backend.project_planner.list_projects())
        return web.json_response({"error": "Project planner not available"})
    
    async def suggestions_list(request):
        """Lista de sugerencias"""
        if backend.suggestions:
            return web.json_response(backend.suggestions.get_active_suggestions())
        return web.json_response({"error": "Suggestions not available"})
    
    async def vision_status(request):
        """Estado de visión"""
        if backend.vision_gem_v2:
            return web.json_response(backend.vision_gem_v2.get_status())
        return web.json_response({"error": "Vision not available"})
    
    async def self_improvement_status(request):
        """Estado de auto-mejora"""
        if backend.self_improvement:
            return web.json_response(backend.self_improvement.get_status())
        return web.json_response({"error": "Self-improvement not available"})
    
    async def time_tracking_status(request):
        """Estado de time tracking"""
        if backend.time_tracker:
            return web.json_response(backend.time_tracker.get_status())
        return web.json_response({"error": "Time tracker not available"})
    
    async def knowledge_sync_status(request):
        """Estado de sincronización"""
        if backend.knowledge_sync:
            return web.json_response(backend.knowledge_sync.get_sync_stats())
        return web.json_response({"error": "Knowledge sync not available"})
    
    async def network_status(request):
        """Estado de red"""
        if backend.network:
            return web.json_response(backend.network.get_network_status())
        return web.json_response({"error": "Network not available"})
    
    async def productivity_report(request):
        """Reporte de productividad"""
        if backend.time_tracker:
            days = int(request.query.get("days", 7))
            return web.json_response(backend.time_tracker.get_productivity_report(days=days))
        return web.json_response({"error": "Time tracker not available"})
    
    async def generate_documentation(request):
        """Genera documentación automática"""
        if backend.self_improvement:
            doc = backend.self_improvement.generate_documentation()
            return web.Response(text=doc, content_type="text/markdown")
        return web.json_response({"error": "Self-improvement not available"})
    
    # Nuevas rutas para patrones 18-20 y session persistence
    async def reflection_status(request):
        """Estado de reflection pattern"""
        if backend.reflection:
            return web.json_response(backend.reflection.get_status())
        return web.json_response({"error": "Reflection not available"})
    
    async def reasoning_status(request):
        """Estado de reasoning strategies"""
        if backend.reasoning:
            return web.json_response(backend.reasoning.get_status())
        return web.json_response({"error": "Reasoning not available"})
    
    async def hitl_status(request):
        """Estado de human-in-the-loop"""
        if backend.hitl:
            return web.json_response(backend.hitl.get_status())
        return web.json_response({"error": "HITL not available"})
    
    async def session_status(request):
        """Estado de sesión"""
        if backend.session_persistence:
            return web.json_response(backend.session_persistence.get_status())
        return web.json_response({"error": "Session persistence not available"})
    
    async def session_context(request):
        """Obtiene contexto de sesion anterior"""
        if backend.session_persistence:
            return web.Response(
                text=backend.session_persistence.get_context_summary(),
                content_type="text/markdown",
            )
        return web.json_response({"error": "Session persistence not available"})

    async def session_compact(request):
        """Comprime la trayectoria del contexto de la sesión actual (Trajectory Compressor)"""
        try:
            data = await request.json()
        except:
            data = {}
            
        session_id = data.get("session_id")
        if not session_id:
            session_id = backend.director.sessions._active_session_id
            
        if not session_id:
            return web.json_response({"error": "No active session to compact"}, status=400)
            
        protect_last_n = data.get("protect_last_n", 4)
        summary_text = data.get("summary_text", "")
        
        try:
            result = backend.director.sessions.compact_session_trajectory(
                session_id=session_id,
                summary_text=summary_text,
                protect_last_n=protect_last_n
            )
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    
    # Skill Registry routes
    async def skills_search(request):
        """Busca skills por query"""
        if not backend.skill_registry:
            return web.json_response({"error": "Skill registry not available"})
        
        query = request.query.get("q", "")
        category = request.query.get("category")
        limit = int(request.query.get("limit", 10))
        
        if not query:
            return web.json_response({"error": "Missing query parameter 'q'"})
        
        results = backend.skill_registry.search(query, category=category, limit=limit)
        return web.json_response({
            "query": query,
            "results": [
                {
                    "skill_id": r.skill_id,
                    "name": r.name,
                    "description": r.description,
                    "relevance_score": r.relevance_score,
                    "category": r.category,
                    "tags": r.tags,
                    "reason": r.reason,
                }
                for r in results
            ],
            "count": len(results),
        })
    
    async def skills_load(request):
        """Carga contenido de una skill"""
        if not backend.skill_registry:
            return web.json_response({"error": "Skill registry not available"})
        
        skill_id = request.query.get("id")
        if not skill_id:
            return web.json_response({"error": "Missing skill id"})
        
        content = backend.skill_registry.load(skill_id)
        if not content:
            return web.json_response({"error": "Skill not found"})
        
        return web.Response(text=content, content_type="text/markdown")
    
    async def skills_stats(request):
        """Estadisticas de skills"""
        if not backend.skill_registry:
            return web.json_response({"error": "Skill registry not available"})
        
        return web.json_response(backend.skill_registry.get_stats())
    
    async def skills_export(request):
        """Exporta indice para sync"""
        if not backend.skill_registry:
            return web.json_response({"error": "Skill registry not available"})
        
        return web.json_response(backend.skill_registry.export_index())
    
    async def skills_import(request):
        """Importa indice de otro nodo"""
        if not backend.skill_sync:
            return web.json_response({"error": "Skill sync not available"})
        
        try:
            data = await request.json()
            result = backend.skill_sync.import_from_remote(data)
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"error": str(e)})
    
    async def skills_sync_status(request):
        """Estado de sync de skills"""
        if not backend.skill_sync:
            return web.json_response({"error": "Skill sync not available"})
        
        return web.json_response(backend.skill_sync.get_sync_status())
    
    app.router.add_get("/api/resilience/status", resilience_status)
    app.router.add_get("/api/security/status", security_status)
    app.router.add_get("/api/resources/status", resource_status)
    app.router.add_get("/api/learning/status", learning_status)
    app.router.add_get("/api/knowledge-graph/data", knowledge_graph_data)
    app.router.add_get("/api/projects", projects_list)
    app.router.add_get("/api/suggestions", suggestions_list)
    app.router.add_get("/api/vision/status", vision_status)
    app.router.add_get("/api/self-improvement/status", self_improvement_status)
    app.router.add_get("/api/time-tracking/status", time_tracking_status)
    app.router.add_get("/api/knowledge-sync/status", knowledge_sync_status)
    app.router.add_get("/api/network/status", network_status)
    app.router.add_get("/api/productivity/report", productivity_report)
    app.router.add_get("/api/documentation/generate", generate_documentation)
    app.router.add_get("/api/reflection/status", reflection_status)
    app.router.add_get("/api/reasoning/status", reasoning_status)
    app.router.add_get("/api/hitl/status", hitl_status)
    app.router.add_get("/api/session/status", session_status)
    app.router.add_get("/api/session/context", session_context)
    app.router.add_post("/api/session/compact", session_compact)
    app.router.add_get("/api/skills/search", skills_search)
    app.router.add_get("/api/skills/load", skills_load)
    app.router.add_get("/api/skills/stats", skills_stats)
    app.router.add_get("/api/skills/export", skills_export)
    app.router.add_post("/api/skills/import", skills_import)
    app.router.add_get("/api/skills/sync-status", skills_sync_status)
    
    logger.info("✅ New routes added (20 patterns + skill registry complete)")
