"""Gema: vision — Análisis visual y descripción de imágenes"""

from typing import Any, Dict

MANIFEST = {
    "name": "vision",
    "main": "src.plugins.gemas.vision",
    "model": "gemma4:12b",
    "tags": ["screenshot", "screen-control", "pc-control", "mouse", "keyboard", "image", "ocr", "vision"],
    "description": "Análisis visual y descripción de imágenes",
    "icon": "👁️",
    "color": "#06B6D4",
    "division": "specialized",
    "personality": "Experto en visión por computadora. Imágenes, OCR, análisis visual.",
    "workflow": "Capture → Process → Analyze → Classify → Report",
}

_SYSTEM = """Eres un asistente de visión por computadora.
Tu trabajo es:
1. Describir imágenes y capturas de pantalla
2. Identificar elementos UI (botones, formularios, menús)
3. Extraer texto de imágenes (OCR conceptual)
4. Analizar layouts y diseño visual
Cuando te dan una imagen, describe lo que ves de forma detallada y estructura."""


class VisionGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Tarea de visión: {task}"
        if context:
            prompt = f"Contexto: {context}\n\n{prompt}"
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "vision", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
