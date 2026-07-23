"""Gema: biblioteca — Eres un bibliotecario digital experto en organización de con"""

from typing import Any, Dict

MANIFEST = {
    "name": "biblioteca",
    "main": "src.plugins.gemas.biblioteca",
    "model": "gemma4:12b",
    "tags": ['organization', 'knowledge', 'indexing', 'catalog', 'skill'],
    "description": "Eres un bibliotecario digital experto en organización de conocimiento.",
    "icon": "📚",
    "color": "#8B5CF6",
    "division": "academic",
    "personality": "Bibliotecario digital. Organiza, cataloga, encuentra recursos.",
    "workflow": "Search → Catalog → Organize → Retrieve → Recommend",
}

_SYSTEM = """Eres un bibliotecario digital experto en organización de conocimiento.
Tu trabajo es:
1. Organizar y categorizar documentos y skills
2. Crear índices y catálogos
3. Mantener la estructura del conocimiento
4. Facilitar la búsqueda y recuperación de información
Usa taxonomías consistentes y metadatos ricos."""


class BibliotecaGem:
    def __init__(self):
        self._system = _SYSTEM

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        from src.plugins.gemas.llm_base import call_ollama
        prompt = f"Contexto: {context}\n\nTarea: {task}" if context else task
        response = call_ollama(prompt, self._system, model="gemma4:12b")
        return {"gema": "biblioteca", "status": "completed", "task": task, "response": response, "model": "gemma4:12b"}
