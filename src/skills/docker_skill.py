#!/usr/bin/env python3
"""Docker Skill - Gestión de contenedores Docker"""
import subprocess
import json

class DockerSkill:
    def __init__(self):
        self.name = "docker"
        self.description = "Gestión de contenedores Docker y Docker Compose"
    
    def info(self):
        return {"skill": self.name, "description": self.description}
    
    def ps(self):
        """Contenedores activos"""
        result = subprocess.run(["docker", "ps", "--format", "json"], capture_output=True, text=True)
        return {"containers": result.stdout}
    
    def ps_all(self):
        """Todos los contenedores"""
        result = subprocess.run(["docker", "ps", "-a", "--format", "json"], capture_output=True, text=True)
        return {"containers": result.stdout}
    
    def images(self):
        """Imágenes disponibles"""
        result = subprocess.run(["docker", "images"], capture_output=True, text=True)
        return {"images": result.stdout}
    
    def logs(self, container_name, lines=50):
        """Ver logs de contenedor"""
        result = subprocess.run(["docker", "logs", "--tail", str(lines), container_name], capture_output=True, text=True)
        return {"container": container_name, "logs": result.stdout[-1000:]}
    
    def restart(self, container_name):
        """Reiniciar contenedor"""
        result = subprocess.run(["docker", "restart", container_name], capture_output=True, text=True)
        return {"container": container_name, "result": result.returncode == 0}
    
    def stop(self, container_name):
        """Detener contenedor"""
        result = subprocess.run(["docker", "stop", container_name], capture_output=True, text=True)
        return {"container": container_name, "result": result.returncode == 0}
    
    def start(self, container_name):
        """Iniciar contenedor"""
        result = subprocess.run(["docker", "start", container_name], capture_output=True, text=True)
        return {"container": container_name, "result": result.returncode == 0}
    
    def stats(self):
        """Estadísticas de contenedores"""
        result = subprocess.run(["docker", "stats", "--no-stream", "--format", "json"], capture_output=True, text=True)
        return {"stats": result.stdout}

if __name__ == "__main__":
    skill = DockerSkill()
    print(json.dumps(skill.info(), indent=2))