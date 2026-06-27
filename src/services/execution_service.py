"""Execution Service — pure dispatch logic extracted from DirectorNexus.execute()."""
from __future__ import annotations
import json
import logging
from typing import Any

from src.core.provider_base import LLMMessage
from src.core.agent_runner import AgentRunner, AgentRunSpec

logger = logging.getLogger(__name__)


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
            scholar = ScholarGem(web_researcher=director.web_researcher)
            research_result = await scholar.research(task, max_sources=5)
            await scholar.close()
            sources_text = "\n".join(
                f"- {s['title']}: {s.get('snippet', '')[:200]}"
                for s in research_result.get("sources", [])
            )
            content = f"## Investigacion sobre: {task}\n\nFuentes encontradas:\n{sources_text}\n\nResumen:\n{research_result.get('summary', '')}"
            logger.info(f"Routed to ScholarGem ({len(research_result.get('sources', []))} sources)")
            return {"success": True, "content": content, "tool": "scholar", "model": "scholar_research",
                    "tokens_used": 0, "duration_ms": 0}
        except Exception as e:
            logger.warning(f"ScholarGem failed: {e}")
            return None

    @staticmethod
    def tool_schemas_for_gem(director, primary_gem: str) -> list:
        """Retorna los schemas de tools relevantes para la gema, NO todas.

        Patron openhuman profiles.rs: cada agente tiene allowed_tools especificos.
        Esto evita saturar el contexto del LLM (Zen free tiene 8K context).
        """
        _CONVERSATIONAL = {"ayuda", "sage"}
        if primary_gem in _CONVERSATIONAL:
            return []
        if not hasattr(director, 'tool_caller'):
            return []

        # Whitelist por gema — solo tools relevantes (inspirado en openhuman profiles.allowed_tools)
        _GEMA_TOOLS = {
            "code": ["read_file", "write_file", "grep_content", "list_dir", "execute_command", "research_scholar", "search_knowledge"],
            "engineer": ["read_file", "list_dir", "grep_content", "execute_command"],
            "debugger": ["read_file", "grep_content", "execute_command", "list_dir", "research_scholar"],
            "analyst": ["read_file", "grep_content", "list_dir", "execute_command"],
            "architect": ["read_file", "list_dir", "grep_content", "research_scholar"],
            "optimizer": ["read_file", "grep_content", "execute_command"],
            "tester": ["read_file", "execute_command", "grep_content", "list_dir"],
            "devops": ["execute_command", "read_file", "list_dir", "grep_content"],
            "security": ["read_file", "grep_content", "execute_command", "list_dir"],
            "scholar": ["web_search", "web_navigate", "web_fetch"],
            "vision": ["screenshot", "browser", "browser_snapshot", "browser_interact"],
            "design": ["read_file", "list_dir", "browser", "browser_snapshot"],
            "music": ["list_dir", "read_file"],
            "director": ["research_scholar", "search_knowledge", "web_search", "web_navigate", "web_fetch"],
            "creative": ["research_scholar", "search_knowledge"],
            "producer": ["execute_command", "read_file", "list_dir"],
            "prompter": ["read_file"],
            "trainer": ["read_file", "list_dir"],
            "biblioteca": ["read_file", "grep_content", "list_dir"],
            "opencode": ["read_file", "write_file", "grep_content", "execute_command", "list_dir", "web_search", "browser", "research_scholar", "search_knowledge"],
        }

        all_schemas = director.tool_caller.get_tool_schemas()
        if not all_schemas:
            return []

        allowed_names = _GEMA_TOOLS.get(primary_gem)
        if allowed_names is None:
            # gema desconocida → conservative: sin tools (chat puro)
            return []
        # Filtrar schemas por nombre
        return [s for s in all_schemas if s.get("function", {}).get("name") in allowed_names]

    @staticmethod
    async def try_agent_runner(director, task: str, context: str, primary_gem: str, session) -> dict | None:
        provider = director.provider_registry.get("gema-con-fallback")
        if provider is None:
            return None
        try:
            task_prompt = f"Context:\n{context}\n\nTask: {task}" if context else task
            tool_schemas = ExecutionService.tool_schemas_for_gem(director, primary_gem)
            system_prompt = director._build_director_system_prompt()

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
            spec = AgentRunSpec(messages=messages, tools_definitions=tool_schemas, max_iterations=8)
            runner_result = await runner.run(spec)
            if runner_result.stop_reason not in ("error", "empty_final_response"):
                total_tokens = runner_result.usage.get("prompt_tokens", 0) + runner_result.usage.get("completion_tokens", 0)
                # Patron nanobot: content vacio no es success
                content = runner_result.content or ""
                if not content.strip():
                    logger.warning(f"AgentRunner: gema {primary_gem} devolvio content vacio, marcando como failed")
                    return None
                return {"success": True, "content": content, "tool": primary_gem,
                        "model": provider.model, "tokens_used": total_tokens, "duration_ms": 0,
                        "tools_used": runner_result.tools_used}
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
