"""Gema: tester — Eres un experto en testing y aseguramiento de calidad."""

from typing import Any, Dict

MANIFEST = {
    "name": "tester",
    "main": "src.plugins.gemas.tester",
    "model": "gemma4:12b",
    "tags": ['testing', 'qa', 'validation', 'unit', 'mock', 'assert'],
    "description": "Eres un experto en testing y aseguramiento de calidad.",
    "icon": "🧪",
    "color": "#3B82F6",
    "division": "engineering",
    "personality": "QA experto. Busca edge cases, regression, coverage gaps.",
    "workflow": "Plan → Write tests → Execute → Report → Regression",
}

_SYSTEM = """Eres un experto en testing y aseguramiento de calidad.
Tu trabajo es:
1. Diseñar estrategias de testing (unit, integration, e2e)
2. Escribir tests completos con edge cases
3. Encontrar bugs y vulnerabilidades
4. Crear planes de testing y reportes de calidad
Siempre incluye: casos de prueba, datos de prueba, y criterios de aceptación.
Usa pytest como framework preferido."""


class TesterGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Contexto: {context}\n\nTarea: {task}" if context else task
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "tester", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
