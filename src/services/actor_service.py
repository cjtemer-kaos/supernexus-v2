"""Actor Service — init actor system on DirectorNexus."""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


class ActorService:

    @staticmethod
    def init_actor_system(director):
        from src.core.actor_base import ActorSystem, GemaActor, SupervisorActor, BackgroundCognition, RouterActor
        from src.core.adaptive_router import AdaptiveRouterActor

        director.actor_system = ActorSystem()
        gemas = list(getattr(director, 'gemas', {}).keys())
        director._actor_supervisor = SupervisorActor(actor_id="supervisor-v1")
        director.actor_system.register(director._actor_supervisor)
        for g in gemas:
            gema = director.gemas[g]
            director.actor_system.register(GemaActor(name=g, model=gema.model or "qwen2.5-coder:7b",
                provider_registry=director.provider_registry,
                tool_executor=getattr(director, '_multi_motor_tool_executor', None),
                get_tool_schemas=lambda: director.tool_caller.get_tool_schemas() if hasattr(director, 'tool_caller') else [],
                actor_id=f"gema-{g}"), parent=director._actor_supervisor)
        director._dmn_actor = BackgroundCognition(
            review_daemon=director.review_daemon, worker_manager=director.worker_manager,
            memory_consolidator=director.memory_consolidator, interval_s=120.0, actor_id="dmn-v1")
        director.actor_system.register(director._dmn_actor, parent=director._actor_supervisor)
        director._router_actor = RouterActor(director.actor_system, actor_id="router-v1")
        director.actor_system.register(director._router_actor, parent=director._actor_supervisor)
        if hasattr(director, '_adaptive_router'):
            director.actor_system.register(AdaptiveRouterActor(director._adaptive_router, director.actor_system,
                actor_id="adaptive-router-v1"), parent=director._actor_supervisor)
        if hasattr(director, '_self_learning'):
            director.actor_system.register(director._self_learning, parent=director._actor_supervisor)
