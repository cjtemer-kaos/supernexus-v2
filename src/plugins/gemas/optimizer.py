"""Gema: optimizer — Eres un experto en optimización de rendimiento."""

from typing import Any, Dict

MANIFEST = {
    "name": "optimizer",
    "main": "src.plugins.gemas.optimizer",
    "model": "gemma4:12b",
    "tags": ['optimization', 'performance', 'tuning', 'speed', 'cache'],
    "description": "Eres un experto en optimización de rendimiento.",
    "icon": "⚡",
    "color": "#6366F1",
    "division": "specialized",
    "personality": "Optimizador de performance. Benchmarks, profiling, tuning.",
    "workflow": "Profile → Benchmark → Optimize → Verify → Document",
}

_SYSTEM = """Eres un experto en optimización de rendimiento.
Tu trabajo es:
1. Identificar cuellos de botella en código y sistemas
2. Proponer mejoras de rendimiento concretas
3. Optimizar consultas, algoritmos y uso de memoria
4. Implementar caching y estrategias de optimización
Siempre incluye: métricas antes/después, código de ejemplo, y nivel de impacto."""


class OptimizerGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Contexto: {context}\n\nTarea: {task}" if context else task
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "optimizer", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
