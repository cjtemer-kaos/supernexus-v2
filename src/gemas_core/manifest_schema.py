"""
manifest_schema — Constantes y schema JSON para los manifests estándar.

Este módulo define:
  - DEFAULT_MODEL: modelo Ollama por defecto si el manifest no especifica uno.
  - OLLAMA_URL_DEFAULT: URL Ollama por defecto.
  - validate_manifest(data) -> List[str]: valida un dict y retorna lista de errores.

Los clientes pueden usar validate_manifest() en sus tests o al cargar gemas
dinámicamente para detectar manifests malformados.
"""
from __future__ import annotations

from typing import Any, Dict, List


DEFAULT_MODEL = "gemma4:latest"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT_S = 120

REQUIRED_FIELDS = ("name",)
OPTIONAL_FIELDS = (
    "model", "description", "systemPrompt", "semanticKeywords", "category",
    "version", "author", "dependencies",
)

# Categorías estándar. Los clientes pueden extender.
STANDARD_CATEGORIES = {
    "general", "code", "research", "design", "infrastructure",
    "security", "testing", "workflow", "data-ai", "business",
    "development",
}


def validate_manifest(data: Dict[str, Any]) -> List[str]:
    """Valida un manifest cargado de JSON. Retorna lista de errores (vacía = OK).

    Args:
        data: Dict cargado del manifest JSON.

    Returns:
        Lista de strings describiendo errores. Vacía si todo OK.
    """
    errors: List[str] = []
    if not isinstance(data, dict):
        return [f"manifest is not a dict: {type(data).__name__}"]

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"missing required field: '{field}'")
        elif not isinstance(data[field], str) or not data[field].strip():
            errors.append(f"required field '{field}' must be non-empty string")

    model = data.get("model")
    if model is not None and (not isinstance(model, str) or not model.strip()):
        errors.append("'model' must be non-empty string if present")

    description = data.get("description")
    if description is not None and not isinstance(description, str):
        errors.append("'description' must be string if present")

    sp = data.get("systemPrompt")
    if sp is not None and not isinstance(sp, str):
        errors.append("'systemPrompt' must be string if present")

    keywords = data.get("semanticKeywords")
    if keywords is not None:
        if not isinstance(keywords, list):
            errors.append("'semanticKeywords' must be list if present")
        else:
            for i, k in enumerate(keywords):
                if not isinstance(k, str):
                    errors.append(f"semanticKeywords[{i}] must be string")

    category = data.get("category")
    if category is not None and not isinstance(category, str):
        errors.append("'category' must be string if present")

    return errors
