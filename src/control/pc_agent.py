"""
PC Agent - Ejecucion de acciones en pantalla para SuperNEXUS v2
Funciones modulares para click, type, scroll, etc con soporte async
"""

import asyncio
import base64
import io
import json
import logging
import time
from pathlib import Path
from typing import Dict, Optional

import httpx
from PIL import Image

logger = logging.getLogger(__name__)

try:
    from mss import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

SCREENSHOT_DIR = Path.home() / "Pictures" / "ScreenCaptures"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
OLLAMA_SERVER = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5vl:2b"


def capture_screen(filename: str = None) -> tuple:
    """Captura pantalla (sync)"""
    if not MSS_AVAILABLE:
        raise RuntimeError("mss no disponible")
    with mss() as sct:
        screenshot = sct.grab(sct.monitors[1])
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
    if filename is None:
        filename = f"screen_{int(time.time())}.png"
    filepath = SCREENSHOT_DIR / filename
    img.save(str(filepath))
    return str(filepath), screenshot.width, screenshot.height


def capture_base64() -> str:
    """Captura y retorna base64 (sync)"""
    if not MSS_AVAILABLE:
        raise RuntimeError("mss no disponible")
    with mss() as sct:
        screenshot = sct.grab(sct.monitors[1])
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def get_screen_size() -> tuple:
    if PYAUTOGUI_AVAILABLE:
        return pyautogui.size()
    return (1920, 1080)


def get_cursor_pos() -> tuple:
    if PYAUTOGUI_AVAILABLE:
        return pyautogui.position()
    return (0, 0)


def click(x: int, y: int) -> str:
    if PYAUTOGUI_AVAILABLE:
        pyautogui.click(x, y)
    return f"Clicked ({x}, {y})"


def double_click(x: int, y: int) -> str:
    if PYAUTOGUI_AVAILABLE:
        pyautogui.doubleClick(x, y)
    return f"Double-clicked ({x}, {y})"


def right_click(x: int, y: int) -> str:
    if PYAUTOGUI_AVAILABLE:
        pyautogui.rightClick(x, y)
    return f"Right-clicked ({x}, {y})"


def move_to(x: int, y: int) -> str:
    if PYAUTOGUI_AVAILABLE:
        pyautogui.moveTo(x, y)
    return f"Moved to ({x}, {y})"


def type_text(text: str) -> str:
    if PYAUTOGUI_AVAILABLE:
        pyautogui.write(text)
    return f"Typed: {text}"


def hotkey(*keys) -> str:
    if PYAUTOGUI_AVAILABLE:
        pyautogui.hotkey(*keys)
    return f"Hotkey: {'+'.join(keys)}"


def press(key: str) -> str:
    if PYAUTOGUI_AVAILABLE:
        pyautogui.press(key)
    return f"Pressed: {key}"


def scroll(direction: str) -> str:
    if PYAUTOGUI_AVAILABLE:
        pyautogui.scroll(-300 if direction == "down" else 300)
    return f"Scrolled {direction}"


def highlight_element(x: int, y: int, duration: float = 0.5) -> str:
    if PYAUTOGUI_AVAILABLE:
        pyautogui.moveTo(x, y)
        time.sleep(0.1)
        pyautogui.moveRel(50, 0, duration=duration/4)
        pyautogui.moveRel(0, 50, duration=duration/4)
        pyautogui.moveRel(-50, 0, duration=duration/4)
        pyautogui.moveRel(0, -50, duration=duration/4)
    return f"Highlighted ({x}, {y})"


AVAILABLE_ACTIONS = {
    "click": click,
    "double_click": double_click,
    "right_click": right_click,
    "move_to": move_to,
    "type": type_text,
    "hotkey": hotkey,
    "press": press,
    "scroll": scroll,
    "highlight": highlight_element,
}


def execute_action(action_json) -> str:
    """Ejecuta accion desde JSON"""
    try:
        if isinstance(action_json, str):
            action = json.loads(action_json)
        else:
            action = action_json

        action_name = action.get("action", "").lower()
        if action_name == "none":
            return "No action needed"
        if action_name not in AVAILABLE_ACTIONS:
            return f"Unknown action: {action_name}"

        func = AVAILABLE_ACTIONS[action_name]
        if action_name in ("click", "double_click", "right_click", "move_to", "highlight"):
            return func(action.get("x", 0), action.get("y", 0))
        elif action_name == "type":
            return func(action.get("text", ""))
        elif action_name == "hotkey":
            return func(*action.get("keys", []))
        elif action_name == "press":
            return func(action.get("key", ""))
        elif action_name == "scroll":
            return func(action.get("direction", "down"))
        return "Action completed"
    except Exception as e:
        return f"Error executing: {e}"


async def analyze_with_ollama(image_b64: str, instruction: str,
                               model: str = DEFAULT_MODEL,
                               server: str = OLLAMA_SERVER) -> str:
    """Envia screenshot a Ollama para analisis"""
    prompt = f"""Eres un asistente de PC. Analiza esta screenshot y la instruccion: "{instruction}"
Responde en JSON con acciones. Ejemplo:
{{"action": "click", "x": 500, "y": 300}}
{{"action": "type", "text": "hola"}}
{{"action": "none"}}
Solo devuelve JSON."""

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            r = await client.post(f"{server}/api/generate", json={
                "model": model,
                "prompt": prompt,
                "images": [image_b64],
                "stream": False,
            })
            if r.status_code == 200:
                return r.json().get("response", "")
            return f"Error: HTTP {r.status_code}"
        except Exception as e:
            return f"Error: {e}"


async def simple_query(prompt_text: str, model: str = DEFAULT_MODEL,
                       server: str = OLLAMA_SERVER) -> str:
    """Consulta simple a Ollama sin imagen"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            r = await client.post(f"{server}/api/generate", json={
                "model": model,
                "prompt": prompt_text,
                "stream": False,
            })
            if r.status_code == 200:
                return r.json().get("response", "")
            return f"Error: HTTP {r.status_code}"
        except Exception as e:
            return f"Error: {e}"
