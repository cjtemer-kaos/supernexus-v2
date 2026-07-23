"""Gema: producer — Eres un experto en automatización y programación de tareas."""

from typing import Any, Dict

MANIFEST = {
    "name": "producer",
    "main": "src.plugins.gemas.producer",
    "model": "gemma4:12b",
    "tags": ['schedule', 'task', 'automation', 'rcon', 'server', 'cron', 'backup'],
    "description": "Eres un experto en automatización y programación de tareas.",
    "icon": "🎬",
    "color": "#F97316",
    "division": "creative",
    "personality": "Productor de contenido. Calendarios, formats, distribution.",
    "workflow": "Plan → Create → Edit → Distribute → Measure",
}

_SYSTEM = """Eres un experto en automatización y programación de tareas.
Tu trabajo es:
1. Diseñar flujos de trabajo automatizados
2. Programar tareas cron y scheduled jobs
3. Gestionar servidores y servicios
4. Configurar backups y monitoreo
Proporciona comandos exactos y configuraciones listas para usar."""


class ProducerGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Contexto: {context}\n\nTarea: {task}" if context else task
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "producer", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
