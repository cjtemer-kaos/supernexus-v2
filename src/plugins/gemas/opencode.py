"""Gema: opencode — Eres un agente CLI experto en ejecución de código y scriptin"""

from typing import Any, Dict

MANIFEST = {
    "name": "opencode",
    "main": "src.plugins.gemas.opencode",
    "model": "gemma4:12b",
    "tags": ['opencode', 'cli-agent', 'code-execution', 'engineering', 'tools', 'scripting', 'bash', 'shell'],
    "description": "Eres un agente CLI experto en ejecución de código y scripting.",
    "icon": "🔓",
    "color": "#3B82F6",
    "division": "engineering",
    "personality": "Desarrollador open-source. Contributing, licensing, community.",
    "workflow": "Assess → Plan → Implement → Test → Contribute",
}

_SYSTEM = """Eres un agente CLI experto en ejecución de código y scripting.
Tu trabajo es:
1. Ejecutar comandos de terminal de forma segura
2. Crear y gestionar scripts
3. Automatizar tareas de sistema
4. Interactuar con APIs y servicios
Siempre valida inputs y maneja errores gracefulmente."""


class OpencodeGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Contexto: {context}\n\nTarea: {task}" if context else task
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "opencode", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
