"""Execution Service — pure dispatch logic extracted from DirectorNexus.execute()."""
from __future__ import annotations
import json
import logging
from typing import Any

from src.core.provider_base import LLMMessage
from src.core.agent_runner import AgentRunner, AgentRunSpec
from src.core.model_registry import select_model, classify_task_type, TaskType
from src.core.gema_profiles import get_profile, filter_tools

try:
    from src.core.task_lifecycle import TaskLifecycle, TaskStatus
except ImportError:
    TaskLifecycle = None
    TaskStatus = None

logger = logging.getLogger(__name__)

# Map TaskType to provider names for dynamic selection
_TASK_PROVIDER_MAP = {
    TaskType.CODE: ["zen-north-mini-code-free", "zen-deepseek-v4-flash-free", "gema-con-fallback"],
    TaskType.RESEARCH: ["zen-deepseek-v4-flash-free", "gema-con-fallback"],
    TaskType.REASONING: ["zen-deepseek-v4-flash-free", "zen-nemotron-3-ultra-free", "gema-con-fallback"],
    TaskType.VISION: ["zen-mimo-v2.5-free", "gema-con-fallback"],
    TaskType.CREATIVE: ["zen-deepseek-v4-flash-free", "gema-con-fallback"],
    TaskType.ANALYSIS: ["zen-nemotron-3-ultra-free", "zen-deepseek-v4-flash-free", "gema-con-fallback"],
    TaskType.CHAT: ["zen-deepseek-v4-flash-free", "gema-con-fallback"],
    TaskType.FAST: ["zen-north-mini-code-free", "zen-deepseek-v4-flash-free", "gema-con-fallback"],
}


class ExecutionService:
    """Pure dispatch methods. Receives director, returns result dicts."""

    @staticmethod
    def identity_blurb(director) -> str:
        return (
            f"Soy {director.IDENTITY['name']} v{director.IDENTITY['version']}, {director.IDENTITY['role']}.\n"
            f"Tengo {len(director.gemas)} gemas especializadas y "
            f"{len(director.tool_registry.get_all()) if hasattr(director, 'tool_registry') else 0} herramientas registradas.\n"
            f"Arquitectura: {director.IDENTITY['architecture']}.\n"
            f"Proyecto actual: {director.current_project}."
        )

    @staticmethod
    async def try_scholar_gem(director, task: str, primary_gem: str, classification) -> dict | None:
        if primary_gem != "scholar" or "scholar" not in classification.selected_gems:
            return None
        try:
            from src.agents.scholar_gem import ScholarGem

            # Extract original task from brain-injected context
            search_query = task
            if "--- Tarea:" in task:
                search_query = task.split("--- Tarea:")[-1].strip()

            # Scholar investiga SIN LLM - solo fuentes crudas
            scholar = ScholarGem(web_researcher=director.web_researcher, llm_caller=None)
            research_result = await scholar.research(search_query, max_sources=3)
            await scholar.close()
            
            if not research_result.get("sources"):
                return None
            
            # Guardar en Sage (biblioteca + memoria)
            from src.agents.sage_gem import SageGem
            sage = SageGem()
            sources_text = "\n".join([
                f"- {s.get('title', '')}: {s.get('snippet', '')[:200]}"
                for s in research_result.get("sources", [])
            ])
            content_to_save = f"## {task}\n\n{sources_text}"
            sage.save_to_library(
                title=task[:100],
                content=content_to_save,
                topic=sage._infer_topic(content_to_save, task),
                source="scholar_research"
            )
            
            # Retornar SOLO las fuentes crudas
            logger.info(f"Routed to ScholarGem ({len(research_result.get('sources', []))} sources)")
            return {"success": True, "content": sources_text, "tool": "scholar", "model": "scholar_research",
                    "tokens_used": 0, "duration_ms": 0}
        except Exception as e:
            logger.warning(f"ScholarGem failed: {e}")
            return None

    @staticmethod
    def tool_schemas_for_gem(director, primary_gem: str) -> list:
        """Retorna los schemas de tools relevantes para la gema, NO todas.

        Patron openhuman profiles.rs: cada agente tiene allowed_tools especificos.
        Usa gema_profiles.get_profile() como source of truth (single source).
        """
        profile = get_profile(primary_gem)
        if profile.tools is None:
            return []
        if not hasattr(director, 'tool_caller'):
            return []

        all_schemas = director.tool_caller.get_tool_schemas()
        if not all_schemas:
            return []

        all_names = [s.get("function", {}).get("name", "") for s in all_schemas]
        allowed = filter_tools(all_names, profile)
        allowed_set = set(allowed)
        return [s for s in all_schemas if s.get("function", {}).get("name") in allowed_set]

    @staticmethod
    async def try_agent_runner(director, task: str, context: str, primary_gem: str, session) -> dict | None:
        # Dynamic model selection based on task type
        task_type = classify_task_type(task)
        provider_candidates = _TASK_PROVIDER_MAP.get(task_type, ["gema-con-fallback"])

        provider = None
        selected_provider_name = "gema-con-fallback"
        for pname in provider_candidates:
            p = director.provider_registry.get(pname)
            if p is not None:
                provider = p
                selected_provider_name = pname
                break

        if provider is None:
            return None

        try:
            task_prompt = f"Context:\n{context}\n\nTask: {task}" if context else task
            tool_schemas = ExecutionService.tool_schemas_for_gem(director, primary_gem)
            system_prompt = director._build_director_system_prompt()

            # Inject model capability awareness into system prompt
            from src.core.model_registry import select_model as registry_select, TaskType as _TT
            best_model = registry_select(task, task_type=task_type)
            system_prompt += f"\n\n[MODELO ACTIVO: {best_model.name} ({best_model.provider}) — {best_model.description}]"

            memory_ctx = director._get_memory_context(task)
            if memory_ctx:
                task_prompt = f"""{task_prompt}

## CONOCIMIENTO QUE HAS ESTUDIADO
Este conocimiento se inyectó automáticamente. REVISA si responde DIRECTAMENTE la pregunta.
- Si ES relevante: úsalo, aplica sus patrones y ejemplos.
- Si NO es relevante o no responde la pregunta: USA `research_scholar` para investigar en internet.
- NUNCA respondas con conocimiento irrelevante solo porque está en tu memoria.

{memory_ctx}"""

            session_history = session.get_messages_for_llm(max_messages=20, scrub=False)
            history_msgs = [LLMMessage(role=m["role"], content=m["content"]) for m in session_history if m.get("content")]
            messages = [LLMMessage(role="system", content=system_prompt)]
            if history_msgs:
                messages.extend(history_msgs)
            messages.append(LLMMessage(role="user", content=task_prompt))

            runner = AgentRunner(provider, tool_executor=director._multi_motor_tool_executor)
            profile = get_profile(primary_gem)
            spec = AgentRunSpec(messages=messages, tools_definitions=tool_schemas, max_iterations=8,
                               temperature=profile.temperature)
            runner_result = await runner.run(spec)
            if runner_result.stop_reason not in ("error", "empty_final_response"):
                total_tokens = runner_result.usage.get("prompt_tokens", 0) + runner_result.usage.get("completion_tokens", 0)
                content = runner_result.content or ""
                if not content.strip():
                    logger.warning(f"AgentRunner: gema {primary_gem} devolvio content vacio, marcando como failed")
                    return None
                return {"success": True, "content": content, "tool": primary_gem,
                        "model": provider.model, "tokens_used": total_tokens, "duration_ms": 0,
                        "tools_used": runner_result.tools_used, "provider_used": selected_provider_name}
        except Exception:
            logger.exception("AgentRunner failed, falling back")
        return None

    @staticmethod
    async def try_gema_fallback(director, task: str, context: str, primary_gem: str) -> dict | None:
        gema_result = await director.gema_host.execute_gema(primary_gem, "execute_task", {"task": task, "context": context})
        if isinstance(gema_result, dict) and ("error" not in gema_result or "note" in gema_result):
            manifest = director.gemas.get(primary_gem)
            model_name = ""
            if manifest is not None and hasattr(manifest, "model"):
                model_name = manifest.model
            content = gema_result.get("content", "") or gema_result.get("response", "") or ""
            if not content.strip():
                logger.warning(f"try_gema_fallback: gema {primary_gem} devolvio content vacio, probando ai_tools")
            else:
                return {"success": True, "content": content, "tool": primary_gem, "model": model_name,
                        "tokens_used": gema_result.get("metadata", {}).get("tokens_used", 0),
                        "duration_ms": gema_result.get("metadata", {}).get("execution_ms", 0)}
        try:
            return await director.ai_tools.quick_response(task=task, gem=primary_gem, context=context)
        except Exception:
            return None

    @staticmethod
    def mcp_call_result(director, task: str, context: str, start) -> Any:
        parts = task.split("__", 2)
        if len(parts) != 3:
            return None
        _, server, tool = parts
        mcp_args = {}
        if context:
            try: mcp_args = json.loads(context)
            except json.JSONDecodeError: mcp_args = {"query": context}
        return None  # caller handles async

    @staticmethod
    def build_result_data(director, ai_result: dict, classification, tokens_used: int) -> dict:
        content = ai_result.get("content", "") or ""
        return {
            "content": content,
            "tool_used": ai_result.get("tool", ""),
            "model_used": ai_result.get("model", ""),
            "tokens_used": tokens_used,
            "duration_ms": ai_result.get("duration_ms", 0),
            "classification": {"gems": classification.selected_gems, "engines": classification.selected_engines},
        }

    @staticmethod
    def classify_task(director, task: str, session_id: str):
        if director._app is not None and director._app.has("routing"):
            return director._app.get("routing").classify(task, session_id=session_id)
        return director.routing_brain.classify(task, session_id=session_id)
