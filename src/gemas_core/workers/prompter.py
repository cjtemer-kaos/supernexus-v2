"""
PrompterGem — Gema de prompt engineering basada en nidhinjs/prompt-master v1.6.0.

Usa la knowledge base de 13 templates + 37 credit-killing patterns para:
  1. Detectar el tool target (Claude Code, Cursor, Midjourney, etc.)
  2. Detectar heurísticamente patterns que aplican al prompt input
  3. Recomendar el mejor template
  4. Advertir sobre malas prácticas (e.g. CoT en reasoning models)
  5. Opcionalmente, llamar a Ollama con un system prompt enriquecido

Métodos principales:
    execute(task, context, target_tool) -> dict
        Análisis estático + recomendación de template. No llama a Ollama.
    optimize(task, context, target_tool, ollama_client, model) -> dict
        Como execute, pero llama a Ollama (inyectado) para refinar el prompt.
    detect_tool(text) -> str
        Heurística pública de detección de tool.
    audit(task, context, target_tool) -> dict
        Pipeline completo paso a paso (debugging).

Knowledge base: ver prompter_knowledge.py (datos estáticos).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..base import GemaBase
from . import prompter_knowledge as pk

logger = logging.getLogger("gemas-core.workers.prompter")


class PrompterGem(GemaBase):
    """Gema de prompt engineering con knowledge base de 13 templates + 37 patterns."""

    name = "prompter"
    description = (
        "Prompt engineering con knowledge base de 13 templates validados "
        "y 37 credit-killing patterns (nidhinjs/prompt-master v1.6.0, MIT)"
    )
    category = "core"

    def __init__(self, ollama_client: Optional[Any] = None):
        """Args:
            ollama_client: Cliente Ollama opcional (inyectable). Si None,
                optimize() retornará error si se llama.
        """
        self.ollama = ollama_client
        self.history: List[Dict[str, Any]] = []

    # ================================================================
    # Public API
    # ================================================================

    async def execute(
        self,
        task: str,
        context: str = "",
        target_tool: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Análisis estático del prompt: detecta tool, patterns, recomienda template.

        Args:
            task: La tarea del usuario (e.g. "Write me a prompt for Cursor to
                  refactor auth module").
            context: Contexto adicional opcional (stack, audiencia, etc.).
            target_tool: Override del tool target. Si None, detecta.

        Returns:
            Dict con:
              - success: bool
              - gema: "PrompterGem"
              - target_tool: tool detectado/override
              - template_id: ID del template recomendado (A-M)
              - template: nombre completo
              - template_structure: el template con campos
              - filled_prompt: el prompt con campos rellenados (si context OK)
              - detected_patterns: lista de patterns que aplican
              - warnings: advertencias (e.g. CoT en reasoning model)
              - audit_trail: 7 pasos del pipeline
              - kb_metadata: metadata de la knowledge base
              - timestamp
        """
        logger.info(f"PrompterGem execute: tool={target_tool} task={task[:80]}")
        return self.audit(task=task, context=context, target_tool=target_tool)

    async def optimize(
        self,
        task: str,
        context: str = "",
        target_tool: Optional[str] = None,
        ollama_client: Optional[Any] = None,
        model: str = "qwen2.5-coder:7b",
    ) -> Dict[str, Any]:
        """Como execute, pero refina el prompt vía Ollama (si está disponible).

        Args:
            task, context, target_tool: igual que execute().
            ollama_client: Cliente Ollama. Si None, usa self.ollama.
            model: Modelo a usar (default qwen2.5-coder:7b).

        Returns:
            Dict con todo lo de execute() + 'refined_prompt' (string) y
            'ollama_used' (bool). Si Ollama no está disponible, retorna
            success=True con refined_prompt=None y una nota.
        """
        client = ollama_client or self.ollama
        analysis = self.audit(task=task, context=context, target_tool=target_tool)

        out: Dict[str, Any] = {**analysis, "refined_prompt": None, "ollama_used": False}

        if client is None:
            out["note"] = (
                "ollama_client not provided; returning static analysis only. "
                "Inject ollama_client to enable prompt refinement via LLM."
            )
            out["success"] = True
            self.history.append(out)
            return out

        try:
            system_prompt = self._build_ollama_system_prompt(analysis)
            user_message = self._build_ollama_user_message(task, context, analysis)
            response = await self._call_ollama(
                client, system_prompt, user_message, model
            )
            out["refined_prompt"] = response
            out["ollama_used"] = True
            out["ollama_model"] = model
            out["success"] = True
        except Exception as e:
            logger.warning(f"PrompterGem optimize Ollama call failed: {e}")
            out["success"] = True  # análisis sigue siendo válido
            out["ollama_error"] = str(e)
            out["note"] = "static analysis OK, but Ollama refinement failed"

        self.history.append(out)
        return out

    def detect_tool(self, text: str) -> str:
        """Heurística pública para detectar el tool target."""
        return pk.detect_target_tool(text)

    def audit(
        self,
        task: str,
        context: str = "",
        target_tool: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Pipeline completo de análisis (7 pasos) — útil para debugging.

        Returns:
            Dict con audit_trail (lista de pasos) + resultado final.
        """
        steps: List[Dict[str, Any]] = []
        warnings: List[str] = []

        # Step 1: detectar target tool
        detected_tool = target_tool or pk.detect_target_tool(task + " " + context)
        if target_tool is None and detected_tool != "auto":
            steps.append({
                "step": 1, "name": "detect_target_tool",
                "result": detected_tool, "method": "keyword_match",
            })
        elif target_tool:
            detected_tool = target_tool
            steps.append({
                "step": 1, "name": "detect_target_tool",
                "result": detected_tool, "method": "override",
            })
        else:
            steps.append({
                "step": 1, "name": "detect_target_tool",
                "result": "auto", "method": "no_match",
            })
            warnings.append(
                "Could not detect target tool from input. Specify target_tool "
                "explicitly or include keywords like 'for Cursor', 'for Midjourney'."
            )

        # Step 2: extract 9 dimensions of intent (heuristic-light version)
        combined_text = f"{task} {context}"
        dimensions = self._extract_dimensions(combined_text)
        steps.append({
            "step": 2, "name": "extract_dimensions",
            "result": dimensions,
        })

        # Step 3: skipping clarifying questions (manual UI concern)

        # Step 4: pick best template
        template_id = pk.pick_template_for(detected_tool, task)
        template = pk.get_template(template_id)
        steps.append({
            "step": 4, "name": "pick_template",
            "result": template_id, "template_name": template["name"] if template else "?",
        })

        # Step 5: detect patterns
        detected_patterns = pk.detect_pattern(combined_text)
        steps.append({
            "step": 5, "name": "detect_patterns",
            "result_count": len(detected_patterns),
            "patterns": [p["name"] for p in detected_patterns],
        })

        # Step 6: token efficiency audit (heuristic: count words)
        word_count = len(combined_text.split())
        if word_count > 100:
            warnings.append(
                f"Input has {word_count} words. Consider scoping to the "
                f"relevant function/file (see pattern 25)."
            )
        steps.append({
            "step": 6, "name": "token_efficiency_audit",
            "word_count": word_count,
        })

        # Step 7: deliver (compose the final prompt structure)
        filled_prompt = self._compose_filled_prompt(
            task, context, dimensions, template_id
        )
        steps.append({
            "step": 7, "name": "deliver",
            "template_id": template_id,
            "filled_chars": len(filled_prompt),
        })

        # Reasoning model warning (pattern 27)
        if template_id == "E" or "chain of thought" in combined_text.lower():
            if "deepseek" in combined_text.lower() or "thinking" in combined_text.lower() \
                    or "o1" in combined_text.lower() or "o3" in combined_text.lower() \
                    or "minimax" in combined_text.lower():
                warnings.append(
                    "Pattern 27: CoT should NOT be added to reasoning-native models "
                    "(o1/o3/o4-mini, DeepSeek-R1, Qwen3 thinking, MiniMax thinking). "
                    "Consider switching to RTF (A) or CO-STAR (B)."
                )

        result: Dict[str, Any] = {
            "success": True,
            "gema": "PrompterGem",
            "target_tool": detected_tool,
            "template_id": template_id,
            "template": template["name"] if template else None,
            "template_full_name": template["full_name"] if template else None,
            "template_structure": template["template"] if template else None,
            "filled_prompt": filled_prompt,
            "dimensions": dimensions,
            "detected_patterns": detected_patterns,
            "warnings": warnings,
            "audit_trail": steps,
            "kb_metadata": pk.get_kb_metadata(),
            "timestamp": datetime.now().isoformat(),
        }
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": "prompter",
            "name": "PROMPTER",
            "description": self.description,
            "category": self.category,
            "type": "dedicated",
            "knowledge_base": pk.get_kb_metadata(),
            "ollama_configured": self.ollama is not None,
        }

    # ================================================================
    # Internal helpers
    # ================================================================

    @staticmethod
    def _extract_dimensions(text: str) -> Dict[str, Any]:
        """Extracción heurística de 9 dimensiones de intent (light version)."""
        text_lower = text.lower()
        # role
        role = "expert"
        for kw in ("senior", "principal", "staff", "junior", "lead"):
            if kw in text_lower:
                role = kw
                break
        # audience (heuristic)
        audience_hints: List[str] = []
        for hint in ("technical", "non-technical", "developer", "user",
                     "beginner", "expert", "executive", "manager", "founder"):
            if hint in text_lower:
                audience_hints.append(hint)
        # length (heuristic)
        word_count = len(text.split())
        if word_count <= 20:
            length = "short"
        elif word_count <= 100:
            length = "medium"
        else:
            length = "long"
        # format
        fmt_hints: List[str] = []
        for hint in ("markdown", "json", "yaml", "table", "bullet", "prose",
                     "code", "html", "xml"):
            if hint in text_lower:
                fmt_hints.append(hint)
        return {
            "role": role,
            "audience": audience_hints,
            "length": length,
            "word_count": word_count,
            "format_hints": fmt_hints,
        }

    def _compose_filled_prompt(
        self,
        task: str,
        context: str,
        dimensions: Dict[str, Any],
        template_id: str,
    ) -> str:
        """Compone un prompt rellenado con el template + dimensiones + context.

        Para templates simples (A, B) usa format_with_template.
        Para templates complejos (G, H, M) usa un esquema específico.
        """
        t = pk.get_template(template_id)
        if t is None:
            return task

        if template_id == "A":
            return pk.format_with_template(
                "A", role=dimensions.get("role", "expert"),
                task=task, format="prose",
            )
        if template_id == "B":
            return pk.format_with_template(
                "B",
                context=context or "Not provided",
                objective=task,
                style=dimensions.get("format_hints", ["conversational"])[0]
                if dimensions.get("format_hints") else "conversational",
                tone="neutral",
                audience=", ".join(dimensions.get("audience", [])) or "general",
                response=f"~{dimensions.get('word_count', 50) * 3} words",
            )
        if template_id == "C":
            return pk.format_with_template(
                "C", role=dimensions.get("role", "expert"),
                instructions=task, steps="[Define steps explicitly]",
                end_goal="[Define the end state]", narrowing="[Define constraints]",
            )
        if template_id == "G":
            return pk.format_with_template(
                "G", file=context or "src/<file>.ext",
                function_or_component="<name>",
                current_behavior="<describe current behavior>",
                desired_change=task,
                scope=context or "<exact scope>",
                constraints="- <list constraints>",
                done_when="<binary success condition>",
            )
        if template_id == "H":
            return pk.format_with_template(
                "H", objective=task,
                starting_state=context or "<current state>",
                target_state="<target state>",
                allowed_actions="- <list allowed actions>",
                forbidden_actions="- <list forbidden actions>",
                stop_conditions="<list stop conditions>",
                checkpoints="After each step output: ✅ [what was completed]",
            )
        if template_id == "M":
            return pk.format_with_template(
                "M", objective=task, context=context or "<context>",
                target_state="<target state>",
                scope="- Work only in: <files>",
                constraints="- <list constraints>",
                acceptance_criteria="- [ ] <criterion>",
                stop_conditions="<list>",
                progress="<checkpoint protocol>",
            )
        # Fallback: empty template with values
        return pk.format_with_template(template_id, **{"task": task, "context": context})

    def _build_ollama_system_prompt(self, analysis: Dict[str, Any]) -> str:
        """System prompt enriquecido con knowledge base para Ollama."""
        kb_summary = pk.get_knowledge_summary()
        return (
            "You are PrompterGem, a prompt engineering specialist.\n\n"
            f"{kb_summary}\n\n"
            "INSTRUCTIONS:\n"
            "1. Take the user's task and the detected target tool + template.\n"
            "2. Detect which patterns apply and refactor the prompt to avoid them.\n"
            "3. Fill the chosen template with concrete values (no placeholders).\n"
            "4. Output ONE single copyable prompt block, ready to paste.\n"
            "5. NEVER mention framework/template names to the user.\n"
            "6. NEVER add CoT instructions for reasoning-native models.\n"
            "7. Add a one-line strategy note after the prompt block.\n\n"
            f"DETECTED TOOL: {analysis['target_tool']}\n"
            f"RECOMMENDED TEMPLATE: {analysis['template_id']} ({analysis['template']})\n"
            f"DETECTED PATTERNS: "
            f"{[p['name'] for p in analysis['detected_patterns']]}\n"
            f"WARNINGS: {analysis['warnings']}\n"
        )

    def _build_ollama_user_message(
        self, task: str, context: str, analysis: Dict[str, Any]
    ) -> str:
        """User message con la task + context + analysis."""
        return (
            f"TASK:\n{task}\n\n"
            f"CONTEXT:\n{context or '(none provided)'}\n\n"
            f"REFINE the prompt for target tool '{analysis['target_tool']}' "
            f"using template '{analysis['template_id']}'.\n"
            f"Output: 1 copyable prompt block + 1-line strategy note."
        )

    @staticmethod
    async def _call_ollama(
        client: Any,
        system_prompt: str,
        user_message: str,
        model: str,
    ) -> str:
        """Llama a Ollama. Acepta tanto ollama-python sync como async.

        Para testing, inyecta un client con método `chat(messages, model)`
        o `generate(prompt, model, system)`.
        """
        # async ollama
        if hasattr(client, "chat") and callable(client.chat):
            import asyncio
            coro = client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            if asyncio.iscoroutine(coro):
                resp = await coro
            else:
                resp = coro
            if isinstance(resp, dict):
                return resp.get("message", {}).get("content", "") or resp.get("response", "")
            return str(resp)
        # sync ollama-python fallback
        if hasattr(client, "generate") and callable(client.generate):
            resp = client.generate(
                model=model,
                prompt=user_message,
                system=system_prompt,
            )
            if isinstance(resp, dict):
                return resp.get("response", "")
            return str(resp)
        raise RuntimeError(
            f"ollama_client must have 'chat' or 'generate' method, got {type(client)}"
        )
