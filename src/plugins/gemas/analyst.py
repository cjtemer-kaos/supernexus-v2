"""Gema: analyst — Análisis de datos con LLM"""

import json
from typing import Any, Dict

MANIFEST = {
    "name": "analyst",
    "main": "src.plugins.gemas.analyst",
    "model": "gemma4:12b",
    "tags": ["analysis", "data", "metrics", "kpi", "statistics"],
    "description": "Análisis de datos",
    "icon": "📊",
    "color": "#22C55E",
    "division": "analytics",
    "personality": "Analista de datos. Métricas, KPIs, tendencias, insights accionables.",
    "workflow": "Collect → Clean → Analyze → Visualize → Recommend",
}

_SYSTEM = """Eres un analista de datos experto. Tu trabajo es:
1. Analizar datos, métricas y tendencias
2. Identificar patrones, anomalías y oportunidades
3. Generar reportes concisos con hallazgos accionables
4. Responder preguntas sobre datos con precisión

Siempre respalda tus análisis con evidencia y proporciona métricas concretas."""


class AnalystGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Contexto: {context}\n\nAnaliza esto:\n{task}" if context else task
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "analyst", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
