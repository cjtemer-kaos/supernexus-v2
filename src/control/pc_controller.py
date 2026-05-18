"""
PC Controller - Control visual con Ollama vision para SuperNEXUS v2
Captura pantalla, analiza con modelo vision, ejecuta acciones
"""

import asyncio
import base64
import io
import json
import logging
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import httpx
from PIL import Image

logger = logging.getLogger(__name__)

try:
    from mss import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False
    logger.warning("mss no disponible")

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

SCREENSHOT_DIR = Path.home() / "Pictures" / "ScreenCaptures"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA_SERVER = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5vl:2b"


class PCController:
    """Control visual de PC con analisis de vision via Ollama"""

    def __init__(self, model: str = DEFAULT_MODEL, ollama_url: str = OLLAMA_SERVER):
        self.model = model
        self.ollama_url = ollama_url
        self.client = httpx.AsyncClient(timeout=180.0)
        self.last_action = None
        self.running = False

    async def close(self):
        await self.client.aclose()

    async def capture(self, filename: str = None) -> Tuple[str, str, int, int]:
        """Captura pantalla y retorna (filepath, base64, width, height)"""
        if not MSS_AVAILABLE:
            raise RuntimeError("mss no disponible")

        loop = asyncio.get_event_loop()

        def _capture_sync():
            with mss() as sct:
                screenshot = sct.grab(sct.monitors[1])
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            return img, screenshot.width, screenshot.height

        img, w, h = await loop.run_in_executor(None, _capture_sync)

        if filename is None:
            filename = f"screen_{int(time.time())}.png"
        filepath = SCREENSHOT_DIR / filename

        def _save_sync():
            img.save(str(filepath))
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode()

        b64 = await loop.run_in_executor(None, _save_sync)
        return str(filepath), b64, w, h

    async def ask_ollama(self, prompt: str, image_b64: str = None) -> str:
        """Consulta a Ollama (con o sin imagen)"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if image_b64:
            payload["images"] = [image_b64]

        try:
            r = await self.client.post(f"{self.ollama_url}/api/generate", json=payload)
            if r.status_code == 200:
                return r.json().get("response", "")
            return f"Error: HTTP {r.status_code}"
        except Exception as e:
            return f"Error: {e}"

    def parse_action(self, response: str) -> Dict:
        """Parsea respuesta JSON de Ollama"""
        try:
            response = response.strip()
            response = response.replace("```json", "").replace("```", "").strip()
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                return json.loads(json_str)
        except Exception:
            pass
        return {"action": "none"}

    async def execute(self, action) -> str:
        """Ejecuta accion desde dict o string JSON"""
        if isinstance(action, str):
            action = self.parse_action(action)

        action_type = action.get("action", "none")
        if action_type == "none":
            return "No action"

        self.last_action = action

        def _exec_sync():
            if action_type == "click":
                pyautogui.click(action.get("x", 0), action.get("y", 0))
            elif action_type == "double_click":
                pyautogui.doubleClick(action.get("x", 0), action.get("y", 0))
            elif action_type == "right_click":
                pyautogui.rightClick(action.get("x", 0), action.get("y", 0))
            elif action_type == "type":
                pyautogui.write(action.get("text", ""))
            elif action_type == "hotkey":
                pyautogui.hotkey(*action.get("keys", []))
            elif action_type == "press":
                pyautogui.press(action.get("key", ""))
            elif action_type == "scroll":
                pyautogui.scroll(-300 if action.get("direction", "down") == "down" else 300)

        if not PYAUTOGUI_AVAILABLE:
            return f"Simulated: {action_type}"

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _exec_sync)
        return f"Executed: {action_type}"

    async def describe_screen(self) -> Tuple[str, str]:
        """Describe la pantalla actual"""
        filepath, b64, w, h = await self.capture()
        prompt = f"Analiza esta screenshot de {w}x{h}. Cuenta que ves: ventanas, botones, icons, texto visible. Responde en menos de 100 palabras."
        desc = await self.ask_ollama(prompt, b64)
        return desc, filepath

    async def follow_instruction(self, instruction: str) -> Tuple[str, str]:
        """Sigue una instruccion del usuario"""
        filepath, b64, w, h = await self.capture()
        prompt = f"""Screenshot {w}x{h}. Instruccion: "{instruction}"

Responde SOLO con JSON:
{{"action": "click", "x": 500, "y": 300}}
{{"action": "type", "text": "hola"}}
{{"action": "hotkey", "keys": ["ctrl", "c"]}}
{{"action": "press", "key": "enter"}}
{{"action": "scroll", "direction": "down"}}
{{"action": "none"}}
"""
        response = await self.ask_ollama(prompt, b64)
        action = self.parse_action(response)
        result = await self.execute(action)
        return result, response[:500]

    def get_status(self) -> Dict:
        return {
            "model": self.model,
            "mss_available": MSS_AVAILABLE,
            "pyautogui_available": PYAUTOGUI_AVAILABLE,
            "ollama_url": self.ollama_url,
            "last_action": self.last_action,
        }
