"""
Gema Debugger - Analisis de errores y troubleshooting para SuperNEXUS v2.0
"""

import logging
import re
import traceback
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# Patrones comunes de error
_ERROR_PATTERNS = {
    "import": [r"ImportError", r"ModuleNotFoundError"],
    "type": [r"TypeError", r"AttributeError", r"NameError"],
    "index": [r"IndexError", r"KeyError"],
    "value": [r"ValueError"],
    "connection": [r"ConnectionError", r"TimeoutError", r"OSError"],
    "memory": [r"MemoryError", r"RecursionError"],
    "permission": [r"PermissionError"],
    "file": [r"FileNotFoundError"],
}


class DebuggerGem:
    async def execute(self, task: str, context: str = "") -> Dict:
        logger.info(f"DebuggerGem executing: {task[:80]}...")
        error_type = self._classify_error(task)
        suggestions = self._get_suggestions(error_type, task)
        return {
            "gema": "debugger",
            "task": task,
            "status": "processed",
            "error_type": error_type,
            "suggestions": suggestions,
            "content": f"Error clasificado: {error_type}\n\nSugerencias:\n" + "\n".join(f"- {s}" for s in suggestions),
        }

    async def analyze_error(self, error_text: str) -> Dict:
        error_type = self._classify_error(error_text)
        stack_frames = self._extract_stack_frames(error_text)
        suggestions = self._get_suggestions(error_type, error_text)
        return {
            "gema": "debugger",
            "status": "analyzed",
            "error_type": error_type,
            "stack_frames": stack_frames[:10],
            "suggestions": suggestions,
            "content": f"Tipo: {error_type}\nFrames: {len(stack_frames)}\n\n" + "\n".join(f"- {s}" for s in suggestions),
        }

    def _classify_error(self, text: str) -> str:
        """Clasifica el tipo de error por patrones."""
        text_lower = text.lower()
        for error_type, patterns in _ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return error_type
        return "unknown"

    def _extract_stack_frames(self, text: str) -> List[Dict]:
        """Extrae frames del stack trace."""
        frames = []
        pattern = r"File \"(.+?)\", line (\d+), in (.+)"
        for match in re.finditer(pattern, text):
            frames.append({
                "file": match.group(1),
                "line": int(match.group(2)),
                "function": match.group(3),
            })
        return frames

    def _get_suggestions(self, error_type: str, text: str) -> List[str]:
        """Genera sugerencias basadas en el tipo de error."""
        suggestions = []
        if error_type == "import":
            suggestions.extend([
                "Verificar que el módulo esté instalado: pip install <modulo>",
                "Revisar el nombre del módulo (case-sensitive)",
                "Verificar que el módulo esté en sys.path",
            ])
        elif error_type == "type":
            suggestions.extend([
                "Revisar los tipos de datos en la operación",
                "Verificar que los argumentos tengan el tipo correcto",
                "Usar isinstance() para verificar tipos antes de operar",
            ])
        elif error_type == "index":
            suggestions.extend([
                "Verificar que el índice/exista en el diccionario/lista",
                "Usar .get() con valor por defecto para diccionarios",
                "Verificar la longitud de la lista antes de acceder",
            ])
        elif error_type == "connection":
            suggestions.extend([
                "Verificar que el servidor esté corriendo",
                "Revisar la URL/host/puerto de conexión",
                "Verificar la conectividad de red",
                "Revisar firewall/proxy",
            ])
        elif error_type == "memory":
            suggestions.extend([
                "Optimizar uso de memoria (list comprehensions, generators)",
                "Revisar recursión infinita",
                "Usar itertools/iterables en vez de listas grandes",
            ])
        else:
            suggestions.append("Revisar el stack trace para la línea exacta del error")
        return suggestions
