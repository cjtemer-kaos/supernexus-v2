#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bun Skill - JavaScript runtime más rápido que Node.js
Uso: Bun para package management, test runs, script execution
"""
import subprocess
import json
import os

class BunSkill:
    def __init__(self):
        self.name = "BunSkill"
        self.available = self._check_available()
    
    def _check_available(self):
        try:
            subprocess.run(["bun", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def run(self, command: str) -> str:
        """Ejecuta un comando bun"""
        if not self.available:
            return "[ERROR] Bun no está instalado. Instalá: curl -fsSL https://bun.sh/install | bash"
        try:
            result = subprocess.run(
                ["bun"] + command.split(),
                capture_output=True,
                text=True,
                timeout=120
            )
            return result.stdout if result.returncode == 0 else f"[ERROR] {result.stderr}"
        except Exception as e:
            return f"[ERROR] {e}"
    
    def install(self, package: str = "", cwd: str = ".") -> str:
        """Instala paquetes con bun"""
        cmd = f"install {package}".strip()
        return self.run(f"install {package}".strip())
    
    def create_project(self, name: str, template: str = "react") -> str:
        """Crea un nuevo proyecto con Bun"""
        templates = ["react", "next", "express", "bare"]
        if template not in templates:
            return f"[ERROR] Template debe ser uno de: {', '.join(templates)}"
        
        cmd_map = {
            "react": f"create react-app {name}",
            "next": f"create next-app {name}",
            "express": f"create express-app {name}",
            "bare": f"init {name}"
        }
        
        return self.run(cmd_map[template])
    
    def run_script(self, script: str, cwd: str = ".") -> str:
        """Ejecuta un script con bun"""
        return self.run(f"run {script}")
    
    def add_typescript(self, cwd: str = ".") -> str:
        """Agrega soporte TypeScript"""
        return self.run("add typescript --dev")
    
    def info(self) -> dict:
        """Información del entorno Bun"""
        return {
            "skill": self.name,
            "available": self.available,
            "version": self.run("--version") if self.available else "N/A"
        }

if __name__ == "__main__":
    skill = BunSkill()
    print(json.dumps(skill.info(), indent=2))
