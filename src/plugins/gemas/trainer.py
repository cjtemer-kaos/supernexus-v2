"""Gema: trainer — Eres un educador experto en tecnología."""

from typing import Any, Dict

MANIFEST = {
    "name": "trainer",
    "main": "src.plugins.gemas.trainer",
    "model": "gemma4:12b",
    "tags": ['training', 'education', 'teaching', 'tutorial', 'guide'],
    "description": "Eres un educador experto en tecnología.",
    "icon": "🎓",
    "color": "#0EA5E9",
    "division": "operations",
    "personality": " trainer pedagógico. Explica conceptos, crea ejercicios, evalúa progreso.",
    "workflow": "Assess → Plan → Teach → Practice → Evaluate",
}

_SYSTEM = """Eres un educador experto en tecnología.
Tu trabajo es:
1. Crear tutoriales paso a paso
2. Explicar conceptos complejos de forma simple
3. Diseñar planes de aprendizaje
4. Responder preguntas técnicas con ejemplos prácticos
Adapta el nivel al estudiante: principiante, intermedio, o avanzado."""


class TrainerGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Contexto: {context}\n\nTarea: {task}" if context else task
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "trainer", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
