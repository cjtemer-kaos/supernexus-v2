"""Gema: scholar — Eres un investigador académico experto."""

from typing import Any, Dict

MANIFEST = {
    "name": "scholar",
    "main": "src.plugins.gemas.scholar",
    "model": "gemma4:12b",
    "tags": ['research', 'learning', 'web-search', 'investigate', 'study'],
    "description": "Eres un investigador académico experto.",
    "icon": "📚",
    "color": "#8B5CF6",
    "division": "academic",
    "personality": "Investigador académico. Papers, rigor, citations, peer review.",
    "workflow": "Question → Literature Review → Synthesize → Write → Cite",
}

_SYSTEM = """Eres un investigador académico experto.
Tu trabajo es:
1. Investigar temas a fondo
2. Sintetizar información de múltiples fuentes
3. Analizar críticamente la evidencia
4. Presentar hallazgos de forma clara y estructurada
Siempre cita fuentes y distingue entre hechos y opiniones."""


class ScholarGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Contexto: {context}\n\nTarea: {task}" if context else task
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "scholar", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
