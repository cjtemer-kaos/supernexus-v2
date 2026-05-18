#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway Skill - Despliegue automático
Uso: Desplegar en Railway con git push
"""
import os
import json
import subprocess

class RailwaySkill:
    def __init__(self):
        self.name = "RailwaySkill"
        self.available = self._check_available()
    
    def _check_available(self):
        try:
            subprocess.run(["railway", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def run(self, command: str, cwd: str = ".") -> str:
        if not self.available:
            return "[ERROR] Railway CLI no está instalado. npm i -g @railway/cli"
        try:
            result = subprocess.run(
                ["railway"] + command.split(),
                capture_output=True,
                text=True,
                timeout=60,
                cwd=cwd
            )
            return result.stdout if result.returncode == 0 else f"[ERROR] {result.stderr}"
        except Exception as e:
            return f"[ERROR] {e}"
    
    def login(self) -> str:
        return self.run("login")
    
    def init(self, cwd: str = ".") -> str:
        return self.run("init", cwd)
    
    def link(self, project_id: str = "", cwd: str = ".") -> str:
        cmd = f"link {project_id}".strip()
        return self.run(cmd, cwd)
    
    def deploy(self, cwd: str = ".") -> str:
        return self.run("up", cwd)
    
    def logs(self, cwd: str = ".") -> str:
        return self.run("logs", cwd)
    
    def variables_get(self, cwd: str = ".") -> str:
        return self.run("variables", cwd)
    
    def variables_set(self, key: str, value: str, cwd: str = ".") -> str:
        return self.run(f"variables set {key}={value}", cwd)
    
    def status(self, cwd: str = ".") -> str:
        return self.run("status", cwd)
    
    def add_service(self, service: str, cwd: str = ".") -> str:
        """Agrega servicios (postgresql, redis, mysql)"""
        valid = ["postgresql", "redis", "mysql", "mongodb"]
        if service not in valid:
            return f"[ERROR] Servicio debe ser: {', '.join(valid)}"
        return self.run(f"add {service}", cwd)
    
    def info(self) -> dict:
        return {
            "skill": self.name,
            "available": self.available,
            "version": self.run("--version") if self.available else "N/A",
            "docs": "https://docs.railway.app"
        }

if __name__ == "__main__":
    skill = RailwaySkill()
    print(json.dumps(skill.info(), indent=2))
