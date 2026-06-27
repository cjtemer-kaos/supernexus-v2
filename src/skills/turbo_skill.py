#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TurboRepo Skill - Monorepo management
Uso: Gestionar múltiples apps en un solo repo con Turborepo
"""
import subprocess
import json
import os

class TurboSkill:
    def __init__(self):
        self.name = "TurboSkill"
        self.available = self._check_available()
    
    def _check_available(self):
        try:
            subprocess.run(["turbo", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def run(self, command: str, cwd: str = ".") -> str:
        """Ejecuta un comando turbo"""
        if not self.available:
            return "[ERROR] Turbo no está instalado. Instalá: npm install -g turbo"
        try:
            result = subprocess.run(
                ["turbo"] + command.split(),
                capture_output=True,
                text=True,
                timeout=120,
                cwd=cwd
            )
            return result.stdout if result.returncode == 0 else f"[ERROR] {result.stderr}"
        except Exception as e:
            return f"[ERROR] {e}"
    
    def init(self, cwd: str = ".") -> str:
        """Inicializa un monorepo con Turbo"""
        return self.run("init", cwd)
    
    def add_app(self, name: str, cwd: str = ".") -> str:
        """Agrega una nueva app al monorepo"""
        apps_dir = os.path.join(cwd, "apps")
        os.makedirs(apps_dir, exist_ok=True)
        return f"[OK] Crear app en: {os.path.join(apps_dir, name)}"
    
    def add_package(self, name: str, cwd: str = ".") -> str:
        """Agrega un nuevo paquete compartido"""
        packages_dir = os.path.join(cwd, "packages")
        os.makedirs(packages_dir, exist_ok=True)
        return f"[OK] Crear paquete en: {os.path.join(packages_dir, name)}"
    
    def run_all(self, cwd: str = ".") -> str:
        """Ejecuta todas las tareas definidas en turbo.json"""
        return self.run("run", cwd)
    
    def build(self, cwd: str = ".") -> str:
        """Build de todos los paquetes/apps"""
        return self.run("build", cwd)
    
    def generate_config(self, cwd: str = ".") -> str:
        """Genera turbo.json básico"""
        config = {
            "pipeline": {
                "build": {
                    "dependsOn": ["^build"],
                    "outputs": ["dist/**", ".next/**"]
                },
                "test": {
                    "dependsOn": ["^build"]
                },
                "lint": {
                    "outputs": []
                },
                "dev": {
                    "cache": False
                }
            }
        }
        config_path = os.path.join(cwd, "turbo.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        return f"[OK] turbo.json creado en {config_path}"
    
    def info(self) -> dict:
        """Información de TurboRepo"""
        return {
            "skill": self.name,
            "available": self.available,
            "version": self.run("--version") if self.available else "N/A"
        }

if __name__ == "__main__":
    skill = TurboSkill()
    print(json.dumps(skill.info(), indent=2))
