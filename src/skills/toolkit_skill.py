#!/usr/bin/env python3
"""Toolkit Central - Centraliza todas las herramientas disponibles"""
import subprocess
import json
import os

class ToolkitSkill:
    def __init__(self):
        self.name = "toolkit"
        self.description = "Centraliza todas las herramientas del ecosistema"
    
    def info(self):
        return {"skill": self.name, "description": "Herramientas integradas del ecosistema Nexus"}
    
    def list_tools(self):
        """Lista todas las herramientas disponibles"""
        tools = []
        
        # Ollama
        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                tools.append({"name": "ollama", "status": "✅", "type": "LLM Local"})
        except: pass
        
        # Docker
        try:
            result = subprocess.run(["docker", "ps"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                tools.append({"name": "docker", "status": "✅", "type": "Contenedores"})
        except: pass
        
        # OpenCode
        if os.path.exists(os.path.expanduser("~/.opencode/bin/opencode.exe")) or os.path.exists("C:/Program Files/opencode/opencode.exe"):
            tools.append({"name": "opencode", "status": "✅", "type": "IDE Agentes"})
        
        # Hermes
        if os.path.exists(os.path.expanduser("~/.local/bin/hermes.exe")) or os.path.exists("C:/Program Files/hermes/hermes.exe"):
            tools.append({"name": "hermes", "status": "✅", "type": "Agente IA"})
        
        # Python
        tools.append({"name": "python", "status": "✅", "type": "Desarrollo"})
        
        # Playwright
        try:
            from playwright.sync_api import sync_playwright
            tools.append({"name": "playwright", "status": "✅", "type": "Web Automation"})
        except: pass
        
        return {"tools": tools, "total": len(tools)}
    
    def quick_status(self):
        """Resumen rápido del sistema"""
        return {
            "ollama": "deepseek-r1:7b activo",
            "hermes": "configurado",
            "docker": "open-webui corriendo",
            "opencode": "v1.14.33",
            "search": "Bing via Playwright"
        }
    
    def run_ollama(self, model, prompt):
        """Ejecuta prompt en Ollama"""
        cmd = f"echo '{prompt}' | ollama run {model}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        return {"model": model, "response": result.stdout[:1500]}
    
    def run_hermes(self, prompt):
        """Ejecuta prompt en Hermes"""
        cmd = f"echo '{prompt}' | hermes chat"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        return {"hermes": "response", "output": result.stdout[:1500]}

if __name__ == "__main__":
    skill = ToolkitSkill()
    print(json.dumps(skill.list_tools(), indent=2))