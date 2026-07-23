"""Gema: director — Eres el director de orquestación de SuperNEXUS."""

from typing import Any, Dict

MANIFEST = {
    "name": "director",
    "main": "src.plugins.gemas.director",
    "model": "gemma4:12b",
    "tags": ['leadership', 'orchestration', 'planning'],
    "description": "Eres el director de orquestación de SuperNEXUS.",
    "icon": "🎬",
    "color": "#0EA5E9",
    "division": "operations",
    "personality": "Director de orquesta. Coordina gemas, delega, sintetiza resultados.",
    "workflow": "Classify → Route → Execute → Synthesize → Deliver",
}

_SYSTEM = """Eres el director de orquestación de SuperNEXUS.
Tu trabajo es:
1. Analizar tareas y decidir qué gema ejecutarla
2. Coordinar múltiples agentes para tareas complejas
3. Priorizar y secuenciar subtareas
4. Sintetizar resultados y reportar progreso
Tienes 24 gemas especializadas a tu disposición."""


class DirectorGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Contexto: {context}\n\nTarea: {task}" if context else task
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "director", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
