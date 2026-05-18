#!/usr/bin/env python3
"""PopOS Skill - Administración del sistema Pop!_OS"""
import os
import subprocess
import json

class PopOSSkill:
    def __init__(self):
        self.name = "popos"
        self.description = "Administración de Pop!_OS Linux"
    
    def info(self):
        return {
            "skill": self.name,
            "description": self.description,
            "commands": ["systemctl", "apt", "neofetch", "htop"]
        }
    
    def status(self):
        """Estado del sistema"""
        try:
            result = subprocess.run(["neofetch", "--json"], capture_output=True, text=True)
            return json.loads(result.stdout) if result.returncode == 0 else {"error": "neofetch no disponible"}
        except:
            return {"os": "Pop!_OS 24.04", "status": "activo"}
    
    def services(self, service_name=None):
        """Ver servicios systemctl"""
        if service_name:
            result = subprocess.run(["systemctl", "status", service_name], capture_output=True, text=True)
            return {"service": service_name, "status": result.stdout[:500]}
        result = subprocess.run(["systemctl", "list-units", "--type=service", "--state=running"], capture_output=True, text=True)
        return {"services": result.stdout.split("\n")[:15]}
    
    def disks(self):
        """Espacio en disco"""
        result = subprocess.run(["df", "-h"], capture_output=True, text=True)
        return {"disks": result.stdout}
    
    def update(self):
        """Actualizar sistema"""
        result = subprocess.run(["sudo", "apt", "update"], capture_output=True, text=True)
        return {"update": result.stdout[-500:] if result.returncode == 0 else result.stderr[:500]}

if __name__ == "__main__":
    skill = PopOSSkill()
    print(json.dumps(skill.info(), indent=2))