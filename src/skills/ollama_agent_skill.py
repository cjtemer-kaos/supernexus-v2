#!/usr/bin/env python3
"""Ollama Agent Skill - Gestiona agentes IA locales"""
import subprocess
import json
import requests

class OllamaAgentSkill:
    def __init__(self):
        self.name = "ollama_agent"
        self.description = "Gestiona agentes IA locales con Ollama"
        self.base_url = "http://localhost:11434"
    
    def info(self):
        return {"skill": self.name, "description": self.description}
    
    def list_models(self):
        """Lista modelos disponibles"""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return {"models": r.json().get("models", [])}
        except:
            return {"error": "Ollama no responde"}
    
    def pull_model(self, model_name):
        """Descarga un modelo"""
        result = subprocess.run(["ollama", "pull", model_name], capture_output=True, text=True)
        return {"model": model_name, "result": result.returncode == 0}
    
    def chat(self, model, prompt):
        """Envía mensaje a modelo"""
        try:
            r = requests.post(f"{self.base_url}/api/generate", 
                            json={"model": model, "prompt": prompt}, timeout=120)
            return {"response": r.json().get("response", "")}
        except Exception as e:
            return {"error": str(e)}
    
    def create_agent(self, name, system_prompt, model="deepseek-r1:7b"):
        """Crea un agente con system prompt"""
        agent_config = {
            "name": name,
            "model": model,
            "system": system_prompt
        }
        return {"agent": name, "config": agent_config, "status": "ready"}
    
    def run_agent(self, agent_name, task):
        """Ejecuta un agente con tarea"""
        return {"agent": agent_name, "task": task, "processing": True}

if __name__ == "__main__":
    skill = OllamaAgentSkill()
    print(json.dumps(skill.info(), indent=2))