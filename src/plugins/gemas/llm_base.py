"""
LLMGema — Base class para gemas que usan LLM local via Ollama.

Todas las gemas LLM heredan de esta clase y proveen:
  - system_prompt: instrucciones del sistema para la gema
  - model: modelo Ollama a usar (default: gemma4:12b)
  - execute(task): punto de entrada principal

La llamada Ollama es directa via HTTP — sin dependencias externas.
"""

import json
import logging
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"


def call_ollama(
    prompt: str,
    system: str = "",
    model: str = "gemma4:12b",
    temperature: float = 0.3,
    timeout: int = 180,
) -> str:
    """Call Ollama API directly. Returns the response text."""
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": temperature},
    }
    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return data.get("response", "")
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        return f"[Error calling LLM: {e}]"


class LLMGema:
    """Base class for LLM-backed gemas.

    Subclasses set:
        system_prompt: str   — role instructions
        model: str           — Ollama model name (default: gemma4:12b)
        max_tokens: int      — max response length hint
    """

    system_prompt: str = "Eres un asistente de IA."
    model: str = "gemma4:12b"
    max_tokens: int = 2048

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        """Call the LLM with the task and return structured result."""
        full_prompt = task
        if context:
            full_prompt = f"Contexto: {context}\n\nTarea: {task}"

        response = call_ollama(
            prompt=full_prompt,
            system=self.system_prompt,
            model=self.model,
            temperature=0.3,
        )

        return {
            "gema": self.__class__.__name__.lower().replace("gem", ""),
            "status": "completed",
            "task": task,
            "response": response,
            "model": self.model,
            "metadata": {
                "execution_mode": "llm_local",
                "model": self.model,
            },
        }
