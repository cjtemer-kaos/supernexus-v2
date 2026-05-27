#!/usr/bin/env python3
"""
Nexus Design Integration - OpenCode + Open CoDesign Fusion
Workflow: Design (Open CoDesign) → Code (OpenCode)
"""
import os
import subprocess
import time
import requests
from pathlib import Path

class NexusDesignSkill:
    name = "design"
    description = "Fusión completa: Open CoDesign → OpenCode. Diseña UI y genera código automáticamente."
    
    # Paths
    OPEN_CODESIGN = os.getenv("OPEN_CODESIGN_PATH", "Open CoDesign")
    OPENCODE_CLI = os.getenv("OPENCODE_CLI", "opencode")
    NEXUS_CORE = "http://localhost:9000"
    
    def is_codesign_running(self) -> bool:
        try:
            return requests.get("http://localhost:5173", timeout=2).status_code == 200
        except:
            return False
    
    def launch_codesign(self, prompt: str = None) -> dict:
        """Abre Open CoDesign con un prompt opcional"""
        try:
            if prompt:
                # Encode prompt in URL
                cmd = [self.OPEN_CODESIGN, f"--prompt={prompt}"]
            else:
                cmd = [self.OPEN_CODESIGN]
            
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            return {"status": "codesign_opened", "url": "http://localhost:5173"}
        except Exception as e:
            return {"error": str(e)}
    
    def generate_code(self, prompt: str) -> dict:
        """Usa OpenCode para generar código"""
        try:
            # Usar Nexus API para OpenCode
            r = requests.post(f"{self.NEXUS_CORE}/api/chat", json={
                "prompt": prompt,
                "gem": "codex",
                "engine": "codex"
            }, timeout=120)
            
            if r.status_code == 200:
                return {"status": "generated", "response": r.text}
            return {"error": r.text}
        except Exception as e:
            return {"error": str(e)}
    
    def design_to_code(self, design_prompt: str, implementation_prompt: str = None) -> dict:
        """
        Workflow completo: Diseño → Código
        1. Abre Open CoDesign con el prompt de diseño
        2. Genera código basado en la implementación deseada
        """
        # Paso 1: Abrir CoDesign
        result1 = self.launch_codesign(design_prompt)
        
        if "error" in result1:
            return result1
        
        # Paso 2: Generar código (opcional)
        if implementation_prompt:
            time.sleep(2)  # Esperar a que abra CoDesign
            result2 = self.generate_code(implementation_prompt)
            return {
                "status": "workflow_complete",
                "codesign": "opened at http://localhost:5173",
                "code_generation": result2
            }
        
        return {
            "status": "ready_for_design",
            "codesign": "opened",
            "next_step": "Diseña en Open CoDesign, luego ejecuta generate_code()"
        }
    
    # Comandos directos
    def open_design(self, prompt: str = "") -> dict:
        """Abre solo Open CoDesign"""
        return self.launch_codesign(prompt)
    
    def generate(self, task: str) -> dict:
        """Genera código con OpenCode"""
        return self.generate_code(task)
    
    def info(self) -> dict:
        return {
            "skill": self.name,
            "status": "ACTIVE",
            "components": {
                "open_codesign": self.OPEN_CODESIGN if os.path.exists(self.OPEN_CODESIGN) else "NOT_INSTALLED",
                "opencode_cli": self.OPENCODE_CLI if os.path.exists(self.OPENCODE_CLI) else "NOT_INSTALLED",
                "nexus": self.NEXUS_CORE
            },
            "methods": [
                "design_to_code(design_prompt, implementation_prompt)",
                "open_design(prompt)",
                "generate(task)"
            ]
        }


# Funciones rápidas
def design(description: str) -> dict:
    """Abre Open CoDesign para diseñar"""
    skill = NexusDesignSkill()
    return skill.open_design(description)

def implement(task: str) -> dict:
    """Genera código con OpenCode"""
    skill = NexusDesignSkill()
    return skill.generate(task)

def workflow(design_prompt: str, code_prompt: str = None) -> dict:
    """Diseño + Código automatico"""
    skill = NexusDesignSkill()
    return skill.design_to_code(design_prompt, code_prompt)


if __name__ == "__main__":
    skill = NexusDesignSkill()
    print("=== Nexus Design Fusion ===")
    print(skill.info())