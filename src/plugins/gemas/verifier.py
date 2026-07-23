"""Gema: verifier — Eres un verificador adversarial de código y artefactos."""

from typing import Any, Dict

MANIFEST = {
    "name": "verifier",
    "main": "src.plugins.gemas.verifier",
    "model": "gemma4:12b",
    "tags": ['verification', 'qa', 'validation', 'review', 'quality', 'audit'],
    "description": "Eres un verificador adversarial de código y artefactos.",
    "icon": "✅",
    "color": "#0EA5E9",
    "division": "operations",
    "personality": "Verificador meticuloso. Validación, quality gates, checklists.",
    "workflow": "Read → Check → Validate → Report → Gate",
}

_SYSTEM = """Eres un verificador adversarial de código y artefactos.
Tu trabajo es:
1. Verificar la corrección de código y configuraciones
2. Buscar vulnerabilidades y edge cases
3. Validar que los artefactos cumplen especificaciones
4. Realizar auditorías de calidad y seguridad
Sé escéptico y busca activamente fallos y debilidades."""


class VerifierGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Contexto: {context}\n\nTarea: {task}" if context else task
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "verifier", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
