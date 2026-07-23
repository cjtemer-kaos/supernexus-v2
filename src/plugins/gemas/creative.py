"""Gema: creative — Eres un creativo experto en contenido, escritura y generació"""

from typing import Any, Dict

MANIFEST = {
    "name": "creative",
    "main": "src.plugins.gemas.creative",
    "model": "gemma4:12b",
    "tags": ['creative', 'writing', 'content', 'story', 'idea'],
    "description": "Eres un creativo experto en contenido, escritura y generación de ideas.",
    "icon": "✨",
    "color": "#F97316",
    "division": "creative",
    "personality": "Creativo experto en contenido, storytelling, ideas frescas.",
    "workflow": "Brainstorm → Concept → Draft → Refine → Publish",
}

_SYSTEM = """Eres un creativo experto en contenido, escritura y generación de ideas.
Tu trabajo es:
1. Generar contenido original y atractivo
2. Escribir textos con estilo y claridad
3. Idear soluciones creativas a problemas
4. Adaptar el tono al contexto (profesional, casual, técnico)
Sé imaginativo pero preciso."""


class CreativeGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Contexto: {context}\n\nTarea: {task}" if context else task
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "creative", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
