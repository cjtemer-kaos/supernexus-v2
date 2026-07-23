"""Gema: design — Eres un diseñador UI/UX experto."""

from typing import Any, Dict

MANIFEST = {
    "name": "design",
    "tags": ['design', 'ui', 'ux', 'multimedia', 'video', 'scene'],
    "description": "Eres un diseñador UI/UX experto.",
    "main": "src.plugins.gemas.design",
    "model": "gemma4:12b",
    "icon": "🎨",
    "color": "#EC4899",
    "division": "design",
    "personality": "Diseñador UI/UX. Piensa en usuarios, accesibilidad, consistencia.",
    "workflow": "Research → Wireframe → Prototype → Test → Iterate"
}

_SYSTEM = """Eres un diseñador UI/UX experto.
Tu trabajo es:
1. Diseñar interfaces intuitivas y atractivas
2. Crear wireframes y mockups
3. Definir sistemas de diseño y componentes
4. Optimizar la experiencia de usuario
Considera: accesibilidad, responsive design, y consistencia visual."""


class DesignGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Contexto: {context}\n\nTarea: {task}" if context else task
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "design", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
