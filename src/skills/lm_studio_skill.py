"""
LM Studio Skill - Local AI Model Management
Control LM Studio for running local models via API
"""

import os
import json
import subprocess
import time
import requests
from pathlib import Path

LM_STUDIO_PATH = r"C:\Program Files\LM Studio\LM Studio.exe"
LM_STUDIO_PORT = 1234
LM_STUDIO_URL = f"http://localhost:{LM_STUDIO_PORT}"

class LMStudioSkill:
    def __init__(self):
        self.name = "lm_studio"
        self.description = "Gestión de modelos de IA locales mediante LM Studio."
        self.port = LM_STUDIO_PORT
        self.url = LM_STUDIO_URL

    def info(self):
        return {
            "skill": self.name,
            "description": self.description,
            "status": self.get_status()
        }
    
    def is_running(self) -> bool:
        """Check if LM Studio is running"""
        try:
            response = requests.get(f"{self.url}/v1/models", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def start(self) -> bool:
        """Start LM Studio"""
        if self.is_running():
            return True
        try:
            subprocess.Popen([LM_STUDIO_PATH])
            for _ in range(30):
                time.sleep(1)
                if self.is_running():
                    return True
        except Exception as e:
            print(f"Error starting LM Studio: {e}")
        return False
    
    def chat(self, prompt: str, model: str = None, max_tokens: int = 512) -> str:
        """Send chat request to LM Studio"""
        if not self.is_running():
            self.start()
        
        body = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                f"{self.url}/v1/chat/completions",
                json=body,
                timeout=120
            )
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            return f"Error: {e}"
    
    def list_models(self) -> list:
        """List available models"""
        try:
            response = requests.get(f"{self.url}/v1/models", timeout=5)
            data = response.json()
            return data.get("data", [])
        except:
            return []
    
    def get_status(self) -> dict:
        """Get LM Studio status"""
        return {
            "running": self.is_running(),
            "port": self.port,
            "url": self.url,
            "models": self.list_models()
        }

def handle(query: str) -> str:
    """Handle LM Studio queries"""
    skill = LMStudioSkill()
    
    query_lower = query.lower()
    
    if "status" in query_lower or "estado" in query_lower:
        status = skill.get_status()
        return json.dumps(status, indent=2)
    
    if "start" in query_lower or "iniciar" in query_lower:
        return "Started" if skill.start() else "Failed to start"
    
    if "list" in query_lower or "models" in query_lower:
        models = skill.list_models()
        return json.dumps(models, indent=2)
    
    if "chat" in query_lower or "ask" in query_lower:
        prompt = query.replace("chat", "").replace("ask", "").strip()
        return skill.chat(prompt)
    
    return skill.get_status()

def get_skill():
    return LMStudioSkill()