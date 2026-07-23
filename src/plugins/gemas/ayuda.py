"""Gema: ayuda — Guía reactiva del sistema SuperNEXUS"""

from typing import Any, Dict

MANIFEST = {
    "name": "ayuda",
    "main": "src.plugins.gemas.ayuda",
    "model": "gemma4:12b",
    "tags": ["help", "ayuda", "tutorial", "guide", "onboarding", "capacidades"],
    "description": "Guía reactiva del sistema",
    "icon": "❓",
    "color": "#84CC16",
    "division": "support",
    "personality": "Soporte amigable. Resuelve dudas, guía, explica.",
    "workflow": "Understand → Explain → Guide → Verify → Close",
}

_SYSTEM = """Eres la guía de ayuda de SuperNEXUS v2. Respondes preguntas sobre el sistema.
Conoces:
- 24 gemas especializadas: security, code, debugger, analyst, architect, creative, devops, optimizer, tester, trainer, producer, sage, scholar, biblioteca, design, codex, engineer, opencode, prompter, verifier, director, music, vision, ayuda
- Arquitectura: DirectorNexus → GemaHost → GemaWorker (JSON-RPC subprocess)
- MCP Bridge: 38+ tools de memoria, routing, ejecución
- Brain: cerebro.db (remember/recall), nexus_memory.db (FTS5)
- Modelos: 12 modelos Ollama (gemma4:12b, deepseek-r1:8b, qwen3.5:9b, etc.)
- Servidor API en puerto 9000

Responde en español. Sé conciso y útil. Si no sabes algo, di honestamente."""


class AyudaGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Un usuario pregunta: {task}"
        if context:
            prompt = f"Contexto: {context}\n\n{prompt}"
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "ayuda", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
