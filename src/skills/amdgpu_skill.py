#!/usr/bin/env python3
"""AMD GPU Skill - Monitoreo de GPU AMD RX 570"""
import subprocess
import os

class AMDGPUController:
    def __init__(self):
        self.name = "amdgpu"
        self.description = "Control y monitoreo de GPU AMD"
    
    def info(self):
        return {
            "skill": self.name,
            "description": self.description,
            "gpu": "AMD RX 570",
            "tools": ["radeontop", "rocm-smi", "amdgp-top"]
        }
    
    def status(self):
        """Estado de la GPU"""
        try:
            result = subprocess.run(["radeontop", "-d", "-", "-l", "1"], capture_output=True, text=True, timeout=5)
            output = result.stdout if result.stdout else result.stderr
            return {"gpu_status": output.strip()}
        except:
            return {"error": "radeontop no disponible"}
    
    def info_gpu(self):
        """Información de la GPU"""
        result = subprocess.run(["lspci", "| grep -i vga"], capture_output=True, text=True)
        return {"gpu": result.stdout.strip()}
    
    def memory(self):
        """Uso de memoria VRAM"""
        try:
            result = subprocess.run(["radeontop", "-d", "-", "-l", "1"], capture_output=True, text=True, timeout=3)
            for line in result.stdout.split("\n"):
                if "vram" in line.lower():
                    return {"vram": line.strip()}
            return {"info": result.stdout[:200]}
        except:
            return {"error": "No se pudo obtener información de VRAM"}
    
    def temperature(self):
        """Temperatura de GPU"""
        result = subprocess.run(["sensors", "| grep -i amdgpu"], capture_output=True, text=True)
        return {"temp": result.stdout.strip() if result.stdout else "Sensor no disponible"}

if __name__ == "__main__":
    skill = AMDGPUController()
    print(skill.info())