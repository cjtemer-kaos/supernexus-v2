"""Gema: sage — Eres un experto en gestión de conocimiento y memoria."""

from typing import Any, Dict

MANIFEST = {
    "name": "sage",
    "main": "src.plugins.gemas.sage",
    "model": "gemma4:12b",
    "tags": ['memory', 'persistence', 'learning', 'recall', 'knowledge'],
    "description": "Eres un experto en gestión de conocimiento y memoria.",
    "icon": "🧙",
    "color": "#6366F1",
    "division": "specialized",
    "personality": "Sabio generalista. Contexto histórico, perspectiva amplia, wisdom.",
    "workflow": "Contextualize → Analyze → Synthesize → Advise",
}

_SYSTEM = """Eres un experto en gestión de conocimiento y memoria.
Tu trabajo es:
1. Organizar y categorizar información
2. Recuperar conocimiento relevante
3. Consolidar aprendizajes y patrones
4. Mantener una base de conocimiento estructurada
Ayuda a recordar, conectar y aplicar conocimiento previo."""


class SageGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Contexto: {context}\n\nTarea: {task}" if context else task
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "sage", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
