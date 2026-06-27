#!/usr/bin/env python3
"""Agent Container Skill - Despliega agentes IA en contenedores Docker"""
import subprocess
import json

class AgentContainerSkill:
    def __init__(self):
        self.name = "agent_container"
        self.description = "Despliega y gestiona agentes IA en Docker"
    
    def info(self):
        return {"skill": self.name, "description": self.description}
    
    def list_agents(self):
        """Lista agentes disponibles"""
        agents = [
            {"name": "open-webui", "image": "ghcr.io/open-webui/open-webui:main", "port": 8080, "status": "running"},
            {"name": "ollama", "image": "ollama/ollama", "port": 11434, "status": "running"},
            {"name": "comfyui", "image": "comfyorg/comfyui", "port": 8188, "status": "stopped"},
        ]
        return {"agents": agents}
    
    def deploy_agent(self, name, image, ports):
        """Despliega un nuevo agente"""
        port_map = " ".join([f"-p {p}:{p}" for p in ports.split(",")])
        cmd = f"docker run -d --name {name} {port_map} {image}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return {"agent": name, "deployed": result.returncode == 0}
    
    def stop_agent(self, name):
        """Detiene un agente"""
        result = subprocess.run(["docker", "stop", name], capture_output=True, text=True)
        return {"agent": name, "stopped": result.returncode == 0}
    
    def start_agent(self, name):
        """Inicia un agente"""
        result = subprocess.run(["docker", "start", name], capture_output=True, text=True)
        return {"agent": name, "started": result.returncode == 0}
    
    def logs(self, name, lines=50):
        """Ver logs de un agente"""
        result = subprocess.run(["docker", "logs", f"--tail={lines}", name], capture_output=True, text=True)
        return {"agent": name, "logs": result.stdout[-1000:]}
    
    def stats(self):
        """Ver uso de recursos"""
        result = subprocess.run(["docker", "stats", "--no-stream", "--format", "json"], capture_output=True, text=True)
        return {"stats": result.stdout}

if __name__ == "__main__":
    skill = AgentContainerSkill()
    print(json.dumps(skill.info(), indent=2))