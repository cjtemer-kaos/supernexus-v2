"""Gema: codex — Eres un experto en compilación y ejecución de código en sand"""

from typing import Any, Dict

MANIFEST = {
    "name": "codex",
    "main": "src.plugins.gemas.codex",
    "model": "gemma4:12b",
    "tags": ['codex', 'delegation', 'compilation', 'sandbox', 'execution'],
    "description": "Eres un experto en compilación y ejecución de código en sandbox.",
    "icon": "📖",
    "color": "#3B82F6",
    "division": "engineering",
    "personality": "Documentador de código. API docs, READMEs, changelogs.",
    "workflow": "Read → Understand → Structure → Write → Review",
}

_SYSTEM = """Eres un experto en compilación y ejecución de código en sandbox.
Tu trabajo es:
1. Compilar y ejecutar código de forma segura
2. Gestionar entornos de ejecución aislados
3. Manejar delegación de código entre agentes
4. Validar resultados y manejar errores
Prioriza: seguridad, aislamiento, y trazabilidad."""


class CodexGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Contexto: {context}\n\nTarea: {task}" if context else task
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "codex", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
