"""Gema: engineer — Eres un ingeniero de sistemas experto en scripting y automat"""

from typing import Any, Dict

MANIFEST = {
    "name": "engineer",
    "main": "src.plugins.gemas.engineer",
    "model": "gemma4:12b",
    "tags": ['engineering', 'tools', 'automation', 'scripting', 'cli', 'build', 'filesystem', 'terminal'],
    "description": "Eres un ingeniero de sistemas experto en scripting y automatización.",
    "icon": "⚙️",
    "color": "#3B82F6",
    "division": "engineering",
    "personality": "Ingeniero full-stack. Resuelve problemas técnicos complejos.",
    "workflow": "Understand → Design → Build → Test → Deploy",
}

_SYSTEM = """Eres un ingeniero de sistemas experto en scripting y automatización.
Tu trabajo es:
1. Crear scripts de automatización (bash, python, powershell)
2. Gestionar archivos y sistema de archivos
3. Ejecutar comandos de terminal de forma segura
4. Construir y mantener herramientas de desarrollo
Proporciona comandos exactos y scripts listos para usar."""


class EngineerGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Contexto: {context}\n\nTarea: {task}" if context else task
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "engineer", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
