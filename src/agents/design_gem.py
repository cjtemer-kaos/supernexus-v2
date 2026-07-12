"""
Gema Design - Generador de interfaces HTML/CSS/JS para SuperNEXUS v2.0

Usa LLM local para generar dashboards, landing pages, y componentes UI
con identidad visual personalizada.
"""

import json
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)

NEXUS_API = os.environ.get("NEXUS_API_BASE", "http://localhost:9000")


class DesignGem:
    def __init__(self):
        self.history = []

    async def execute(self, task: str, context: str = "") -> Dict:
        """Genera una interfaz HTML/CSS/JS basada en la descripcion."""
        logger.info(f"DesignGem executing: {task[:80]}...")

        prompt = self._build_prompt(task, context)

        # Call LLM via local NEXUS API
        html = await self._call_llm(prompt)

        if not html:
            return {"error": "LLM no disponible para generacion de diseno"}

        # Clean up: extract HTML if wrapped in markdown
        html = self._extract_html(html)

        result = {
            "gema": "design",
            "task": task,
            "status": "completed",
            "response": f"Diseno generado ({len(html)} chars)",
            "output": html,
            "content": html,
        }
        self.history.append(result)
        return result

    def _build_prompt(self, task: str, context: str) -> str:
        api_docs = """
APIS QUE DEBE INCLUIR (JS fetch calls):
- /api/obs/status -> {connected, streaming, recording, stream_time, dropped_frames}
- /api/obs/scenes -> {scenes: [{name, active}]}
- /api/obs/sources -> {sources: [{name, type, visible}]}
- /api/obs/streaming/start POST
- /api/obs/streaming/stop POST
- /api/obs/recording/start POST
- /api/obs/recording/stop POST
- /api/obs/scenes/switch POST {scene}
- /api/obs/source/visibility POST {source, visible}
- /api/sl/status -> {connected}
- /api/sl/alert/follow POST
- /api/sl/alert/subscription POST
- /api/sl/alert/donation POST
- /api/sl/alert/skip POST
- /api/sl/socket/start POST
- /api/sl/socket/stop POST"""

        context_block = f"\nCONTEXTO ADICIONAL: {context}" if context else ""

        return (
            "Eres un disenador web experto especializado en interfaces para streamers y gaming.\n"
            "Genera un archivo HTML COMPLETO y autocontenido (single file) con CSS y JS inline.\n"
            "\n"
            "IDENTIDAD VISUAL:\n"
            "- Marca: KaosMC (ninja, circuitos, gaming)\n"
            "- Color primario: neon green #00ff41\n"
            "- Fondos oscuros: #080808, #0a0a0a\n"
            "- Fonts: Orbitron (titulos), Rajdhani (cuerpo), Share Tech Mono (datos)\n"
            "- Estilo: cyberpunk gaming HUD, NO generico admin panel\n"
            "\n"
            "REGLAS ESTRICTAS:\n"
            "1. CERO sidebar tradicional. Layout radicalmente diferente.\n"
            "2. Canvas background interactivo (circuitos, particles, o algo unico)\n"
            "3. Animaciones cinematicas (glitch, morphing, pulse, orbit)\n"
            "4. CSS y JS inline en el HTML (single file)\n"
            "5. Google Fonts via CDN link\n"
            "6. Logo: kaos-green.png (en mismo directorio)\n"
            "7. Responsive basico\n"
            "\n"
            + api_docs +
            "\n\n"
            "TAREA DEL USUARIO:\n"
            + task +
            context_block +
            "\n\n"
            "Genera SOLO el codigo HTML completo, sin explicaciones, sin markdown fences.\n"
            "Empieza directamente con <!DOCTYPE html>"
        )

    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Llama al LLM via Ollama HTTP API directa."""
        import httpx

        models_to_try = ["qwen2.5-coder:7b", "nemotron-3-nano:4b", "qwen2.5:0.5b"]
        last_error = None
        for model in models_to_try:
            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    r = await client.post("http://localhost:11434/api/generate", json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"num_predict": 4096, "temperature": 0.4}
                    }, timeout=120)
                    if r.status_code == 200:
                        data = r.json()
                        text = data.get("response", "")
                        if text.strip():
                            return text.strip()
            except httpx.TimeoutException:
                logger.warning(f"Ollama {model} HTTP timeout")
            except Exception as e:
                last_error = e
                logger.warning(f"Ollama {model} failed: {e}")

        logger.warning(f"All LLM options exhausted, last error: {last_error}")
        return None

    def _extract_html(self, text: str) -> str:
        """Extrae HTML del texto, removiendo markdown fences si existen."""
        text = text.strip()
        # Remove markdown code fences
        if text.startswith("```html"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
