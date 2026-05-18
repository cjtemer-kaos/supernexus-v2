#!/usr/bin/env python3
"""API Manager Skill - Gestiona APIs de IA"""
import os
import requests

from pathlib import Path

class APIManagerSkill:
    def __init__(self):
        self.name = "api_manager"
        self.description = "Gestiona claves API de IA (Groq, OpenRouter, Google)"
        self.api_keys = {}
        self.load_keys()
    
    def load_keys(self):
        """Carga API keys desde archivos"""
        base = Path(__file__).parent.parent.parent / "config" / "apis"
        files = {
            "groq": "apis_groq.env",
            "openrouter": "apis_openrouter.env",
            "google": "apis_google.env"
        }
        for key_type, filename in files.items():
            path = os.path.join(base, filename)
            if os.path.exists(path):
                with open(path) as f:
                    for line in f:
                        if "API_KEY" in line:
                            self.api_keys[key_type] = line.split("=")[1].strip()
    
    def info(self):
        return {
            "skill": self.name,
            "apis_configured": list(self.api_keys.keys())
        }
    
    def status(self):
        """Verifica estado de cada API"""
        status = {}
        if "groq" in self.api_keys:
            status["groq"] = "✅ Configurado"
        if "openrouter" in self.api_keys:
            status["openrouter"] = "✅ Configurado"
        if "google" in self.api_keys:
            status["google"] = "✅ Configurado"
        return status
    
    def test_groq(self):
        """Prueba API de Groq"""
        if "groq" not in self.api_keys:
            return {"error": "Groq API no configurada"}
        
        headers = {"Authorization": f"Bearer {self.api_keys['groq']}"}
        r = requests.get("https://api.groq.com/openai/v1/models", headers=headers)
        return {"groq": "OK" if r.status_code == 200 else "ERROR"}
    
    def test_openrouter(self):
        """Prueba API de OpenRouter"""
        if "openrouter" not in self.api_keys:
            return {"error": "OpenRouter API no configurada"}
        
        headers = {"Authorization": f"Bearer {self.api_keys['openrouter']}"}
        r = requests.get("https://openrouter.ai/api/v1/models", headers=headers)
        return {"openrouter": "OK" if r.status_code == 200 else "ERROR"}
    
    def get_models_groq(self):
        """Lista modelos disponibles en Groq"""
        if "groq" not in self.api_keys:
            return {"error": "Groq no configurada"}
        
        headers = {"Authorization": f"Bearer {self.api_keys['groq']}"}
        r = requests.get("https://api.groq.com/openai/v1/models", headers=headers)
        if r.status_code == 200:
            return {"models": [m["id"] for m in r.json().get("data", [])[:10]]}
        return {"error": r.text}

if __name__ == "__main__":
    skill = APIManagerSkill()
    print(skill.info())