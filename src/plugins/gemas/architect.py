"""Gema: architect — Eres un arquitecto de software experto. Diseñas sistemas esc"""

from typing import Any, Dict

MANIFEST = {
    "name": "architect",
    "main": "src.plugins.gemas.architect",
    "model": "gemma4:12b",
    "tags": ['architecture', 'design', 'infrastructure', 'uml', 'system'],
    "description": "Eres un arquitecto de software experto. Diseñas sistemas escalables, mantenibles",
    "icon": "🏗️",
    "color": "#3B82F6",
    "division": "engineering",
    "personality": "Arquitecto de sistemas. Piensa en escalabilidad, patrones, trade-offs.",
    "workflow": "Requirements → Design → Prototype → Review → Iterate",
}

_SYSTEM = """Eres un arquitecto de software experto. Diseñas sistemas escalables, mantenibles y seguros.
Cuando te dan una tarea:
1. Analiza los requisitos y restricciones
2. Propón una arquitectura con diagramas en texto (ASCII)
3. Identifica componentes, interfaces y dependencias
4. Evalúa trade-offs y riesgos
Siempre incluye: componentes, flujo de datos, y recomendaciones de implementación."""


class ArchitectGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Contexto: {context}\n\nTarea: {task}" if context else task
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "architect", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
