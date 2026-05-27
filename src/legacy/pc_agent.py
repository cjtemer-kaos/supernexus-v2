#!/usr/bin/env python3
"""
PC Agent - Control de PC con Ollama
Captura pantalla, analiza con LLM, ejecuta acciones
"""

import base64
import io
import json
import os
import time
from pathlib import Path
from mss import mss
from PIL import Image
import pyautogui

SCREENSHOT_DIR = Path.home() / "Pictures" / "ScreenCaptures"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

def capture_screen(filename=None):
    """Captura la pantalla principal"""
    with mss() as sct:
        screenshot = sct.grab(sct.monitors[1])
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
    
    if filename is None:
        filename = f"screen_{int(time.time())}.png"
    
    filepath = SCREENSHOT_DIR / filename
    img.save(str(filepath))
    return str(filepath), screenshot.width, screenshot.height

def capture_base64():
    """Captura y retorna como base64"""
    with mss() as sct:
        screenshot = sct.grab(sct.monitors[1])
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

def click(x, y):
    """Click en coordenadas"""
    pyautogui.click(x, y)
    return f"Clicked ({x}, {y})"

def double_click(x, y):
    pyautogui.doubleClick(x, y)
    return f"Double-clicked ({x}, {y})"

def right_click(x, y):
    pyautogui.rightClick(x, y)
    return f"Right-clicked ({x}, {y})"

def move_to(x, y):
    pyautogui.moveTo(x, y)
    return f"Moved to ({x}, {y})"

def type(text):
    """Escribe texto"""
    pyautogui.write(text)
    return f"Typed: {text}"

def hotkey(*keys):
    """Presiona combinación de teclas"""
    pyautogui.hotkey(*keys)
    return f"Hotkey: {'+'.join(keys)}"

def press(key):
    """Presiona una tecla"""
    pyautogui.press(key)
    return f"Pressed: {key}"

def scroll(direction):
    """Scroll up o down"""
    pyautogui.scroll(-300 if direction == "down" else 300)
    return f"Scrolled {direction}"

def get_screen_size():
    """Obtiene tamaño de pantalla"""
    return pyautogui.size()

def get_cursor_pos():
    """Obtiene posición actual del cursor"""
    return pyautogui.position()

def highlight_element(x, y, duration=0.5):
    """Resalta un elemento moviendo el mouse en círculo"""
    pyautogui.moveTo(x, y)
    time.sleep(0.1)
    pyautogui.moveRel(50, 0, duration=duration/4)
    pyautogui.moveRel(0, 50, duration=duration/4)
    pyautogui.moveRel(-50, 0, duration=duration/4)
    pyautogui.moveRel(0, -50, duration=duration/4)

AVAILABLE_ACTIONS = {
    "click": click,
    "double_click": double_click,
    "right_click": right_click,
    "move_to": move_to,
    "type": type,
    "hotkey": hotkey,
    "press": press,
    "scroll": scroll,
    "highlight": highlight_element,
}

def analyze_with_ollama(image_b64, instruction, model="qwen3:latest", server="http://localhost:11434"):
    """Envía screenshot a Ollama para análisis"""
    import requests
    
    prompt = f"""Eres un asistente de PC. Analiza esta screenshot y la instrucción del usuario: "{instruction}"

Responde en JSON con acciones a ejecutar. Ejemplo:
{{"action": "click", "x": 500, "y": 300}}
{{"action": "type", "text": "hola"}}
{{"action": "hotkey", "keys": ["ctrl", "c"]}}
{{"action": "press", "key": "enter"}}

Solo devuelve JSON, sin texto extra. Si no necesitas acción, responde: {{"action": "none"}}
"""
    
    try:
        r = requests.post(f"{server}/api/generate", json={
            "model": model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False
        }, timeout=120)
        
        if r.status_code == 200:
            return r.json().get("response", "")
        else:
            return f"Error: {r.status_code} - {r.text}"
    except Exception as e:
        return f"Error: {e}"

def execute_action(action_json):
    """Ejecuta acción desde JSON"""
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
        
        if action_name in ["click", "double_click", "right_click", "move_to"]:
            return func(action["x"], action["y"])
        elif action_name == "type":
            return func(action["text"])
        elif action_name == "hotkey":
            return func(*action["keys"])
        elif action_name == "press":
            return func(action["key"])
        elif action_name == "scroll":
            return func(action["direction"])
        elif action_name == "highlight":
            return func(action["x"], action["y"])
        
        return "Action completed"
    except Exception as e:
        return f"Error executing: {e}"

def simple_query(prompt_text, model="qwen3:latest", server="http://localhost:11434"):
    """Consulta simple a Ollama sin imagen"""
    import requests
    
    try:
        r = requests.post(f"{server}/api/generate", json={
            "model": model,
            "prompt": prompt_text,
            "stream": False
        }, timeout=120)
        
        if r.status_code == 200:
            return r.json().get("response", "")
        else:
            return f"Error: {r.status_code}"
    except Exception as e:
        return f"Error: {e}"

def main():
    print("=" * 50)
    print("PC AGENT - Control de PC con Ollama")
    print("=" * 50)
    
    path, w, h = capture_screen()
    print(f"\n[OK] Screenshot: {path}")
    print(f"Resolution: {w}x{h}")
    
    print(f"\nCursor: {get_cursor_pos()}")
    print(f"Screen: {get_screen_size()}")
    
    print("\nAcciones disponibles:")
    for a in AVAILABLE_ACTIONS:
        print(f"  - {a}")

if __name__ == '__main__':
    main()