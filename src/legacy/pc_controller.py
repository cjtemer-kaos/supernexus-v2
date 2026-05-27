#!/usr/bin/env python3
"""
PC Controller - Control de PC con Ollama
Toma screenshot, analiza, ejecuta acciones automáticamente
"""

import base64
import io
import json
import os
import sys
import time
import locale
# Fix encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
import threading
from pathlib import Path
from mss import mss
from PIL import Image
import pyautogui
import requests

SCREENSHOT_DIR = Path.home() / "Pictures" / "ScreenCaptures"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA_SERVER = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:1.5b"

class PCController:
    def __init__(self, model=DEFAULT_MODEL):
        self.model = model
        self.running = False
        self.last_action = None
        
    def capture(self, filename=None):
        """Captura pantalla"""
        with mss() as sct:
            screenshot = sct.grab(sct.monitors[1])
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        
        if filename is None:
            filename = f"screen_{int(time.time())}.png"
        
        filepath = SCREENSHOT_DIR / filename
        img.save(str(filepath))
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        b64 = base64.b64encode(buffer.getvalue()).decode()
        
        return str(filepath), b64, screenshot.width, screenshot.height
    
    def ask_ollama(self, prompt, image_b64=None):
        """Consulta a Ollama"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        if image_b64:
            payload["images"] = [image_b64]
        
        try:
            r = requests.post(f"{OLLAMA_SERVER}/api/generate", 
                          json=payload, timeout=180)
            if r.status_code == 200:
                return r.json().get("response", "")
            else:
                return f"Error: {r.status_code}"
        except Exception as e:
            return f"Error: {e}"
    
    def parse_action(self, response):
        """Parsea respuesta JSON"""
        try:
            response = response.strip()
            # Limpiar markdown
            response = response.replace("```json", "").replace("```", "").strip()
            
            # Buscar { ... }
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                return json.loads(json_str)
        except Exception as e:
            pass
        return {"action": "none"}
    
    # Acciones
    def click(self, x, y):
        pyautogui.click(x, y)
        
    def double_click(self, x, y):
        pyautogui.doubleClick(x, y)
        
    def right_click(self, x, y):
        pyautogui.rightClick(x, y)
        
    def type(self, text):
        pyautogui.write(text)
        
    def hotkey(self, *keys):
        pyautogui.hotkey(*keys)
        
    def press(self, key):
        pyautogui.press(key)
        
    def scroll(self, direction):
        pyautogui.scroll(-300 if direction == "down" else 300)
    
    def execute(self, action):
        """Ejecuta acción"""
        # Asegurar que action es dict
        if isinstance(action, str):
            action = self.parse_action(action)
        
        action_type = action.get("action", "none")
        
        action_type = action.get("action", "none")
        
        if action_type == "none":
            return "No action"
        
        handlers = {
            "click": lambda: self.click(action.get("x", 0), action.get("y", 0)),
            "double_click": lambda: self.double_click(action.get("x", 0), action.get("y", 0)),
            "right_click": lambda: self.right_click(action.get("x", 0), action.get("y", 0)),
            "type": lambda: self.type(action.get("text", "")),
            "hotkey": lambda: self.hotkey(*action.get("keys", [])),
            "press": lambda: self.press(action.get("key", "")),
            "scroll": lambda: self.scroll(action.get("direction", "down")),
        }
        
        if action_type in handlers:
            handlers[action_type]()
            return f"Executed: {action_type}"
        
        return f"Unknown: {action_type}"
    
    def describe_screen(self):
        """Describe la pantalla actual"""
        filepath, b64, w, h = self.capture()
        
        prompt = f"""Analiza esta screenshot de {w}x{h}.
Cuenta qué ves: ventanas, botones, icons, texto visible.
Responde en menos de 100 palabras."""
        
        return self.ask_ollama(prompt, b64), filepath
    
    def follow_instruction(self, instruction):
        """Sigue una instrucción del usuario"""
        filepath, b64, w, h = self.capture()
        
        prompt = f"""Screenshot {w}x{h}. 
Instrucción: "{instruction}"

Responde SOLO con JSON:
- click x,y
- type text
- hotkey key1 key2
- press key
- scroll up/down
- none

{{"action": "click", "x": 500, "y": 300}}
{{"action": "type", "text": "hola"}}
{{"action": "hotkey", "keys": ["ctrl", "c"]}}
{{"action": "press", "key": "enter"}}
{{"action": "none"}}
"""
        
        response = self.ask_ollama(prompt, b64)
        action = self.parse_action(response)
        result = self.execute(action)
        
        return result, response[:500]
    
    def interactive(self):
        """Modo interactivo"""
        print("=" * 50)
        print("PC CONTROLLER - Modo Interactivo")
        print("=" * 50)
        print(f"Modelo: {self.model}")
        print("Escribe指令 o 'screenshot' o 'describe' o 'quit'")
        print()
        
        self.running = True
        
        while self.running:
            try:
                cmd = input("\n> ").strip()
                
                if not cmd:
                    continue
                
                if cmd.lower() in ["quit", "exit", "salir"]:
                    self.running = False
                    break
                
                if cmd.lower() == "screenshot":
                    path, _, w, h = self.capture()
                    print(f"[OK] {path}")
                    continue
                
                if cmd.lower() == "describe":
                    desc, path = self.describe_screen()
                    print(f"\n{desc}")
                    continue
                
                if cmd.lower() == "cursor":
                    pos = pyautogui.position()
                    print(f"Cursor: {pos}")
                    continue
                
                if cmd.lower() == "size":
                    size = pyautogui.size()
                    print(f"Screen: {size}")
                    continue
                
                result, response = self.follow_instruction(cmd)
                print(f"[{result}]")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        print("Chao!")

def main():
    controller = PCController()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        
        if cmd == "--interactive":
            controller.interactive()
        elif cmd == "screenshot":
            path, _, w, h = controller.capture()
            print(f"OK: {path} ({w}x{h})")
        elif cmd == "describe":
            desc, path = controller.describe_screen()
            print(desc)
        elif cmd == "cursor":
            pos = pyautogui.position()
            print(f"Cursor: {pos}")
        elif cmd == "size":
            size = pyautogui.size()
            print(f"Screen: {size}")
        else:
            result, _ = controller.follow_instruction(" ".join(sys.argv[1:]))
            print(result)
    else:
        controller.interactive()

if __name__ == '__main__':
    main()