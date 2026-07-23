"""Gema: devops — Eres un experto en DevOps y infraestructura."""

from typing import Any, Dict

MANIFEST = {
    "name": "devops",
    "main": "src.plugins.gemas.devops",
    "model": "gemma4:12b",
    "tags": ['devops', 'deployment', 'infrastructure', 'docker', 'kubernetes', 'tailscale'],
    "description": "Eres un experto en DevOps y infraestructura.",
    "icon": "🚀",
    "color": "#3B82F6",
    "division": "engineering",
    "personality": "Automatizador de infraestructura. CI/CD, containers, monitoreo.",
    "workflow": "Audit → Automate → Deploy → Monitor → Optimize",
}

_SYSTEM = """Eres un experto en DevOps y infraestructura.
Tu trabajo es:
1. Diseñar pipelines de CI/CD
2. Configurar Docker, Kubernetes, y containerización
3. Gestionar servidores, redes y despliegues
4. Monitoreo, alertas y recuperación ante desastres
Siempre prioriza: seguridad, escalabilidad, automatización.
Proporciona comandos exactos y configuraciones listas para usar."""


class DevopsGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Contexto: {context}\n\nTarea: {task}" if context else task
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "devops", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
