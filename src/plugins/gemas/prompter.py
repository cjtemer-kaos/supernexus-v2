"""Gema: prompter — Eres un experto en optimización de prompts y gestión de toke"""

from typing import Any, Dict

MANIFEST = {
    "name": "prompter",
    "main": "src.plugins.gemas.prompter",
    "model": "gemma4:12b",
    "tags": ['prompt', 'token', 'optimization', 'compression', 'temperature'],
    "description": "Eres un experto en optimización de prompts y gestión de tokens.",
    "icon": "🎯",
    "color": "#6366F1",
    "division": "specialized",
    "personality": "Prompt engineer. Optimiza instrucciones para LLMs, reduce tokens.",
    "workflow": "Understand → Design → Test → Optimize → Validate",
}

_SYSTEM = """Eres un experto en optimización de prompts y gestión de tokens.
Tu trabajo es:
1. Diseñar prompts efectivos para LLMs
2. Optimizar el uso de tokens
3. Comprimir prompts sin perder información
4. Mejorar la calidad de respuestas mediante mejor prompting
Técnicas: few-shot, chain-of-thought, role-playing, structured output."""


class PrompterGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Contexto: {context}\n\nTarea: {task}" if context else task
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "prompter", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
