#!/usr/bin/env python3
"""Hermes Skill - Motor de búsqueda e investigación (Delegado a PC2)"""
import requests
import json

class HermesSkill:
    def __init__(self):
        self.name = "hermes"
        self.description = "Motor de búsqueda e investigación con Hermes Agent (Remoto PC2)"
        self.pc2_url = "http://100.83.38.20:9000/api"
    
    def info(self):
        return {
            "skill": self.name,
            "description": self.description,
            "location": "PC2 (Linux)"
        }
    
    def status(self):
        """Ver estado de Hermes en PC2"""
        try:
            r = requests.post(f"{self.pc2_url}/skills/execute", json={
                "skill": "hermes",
                "method": "info",
                "params": {}
            }, timeout=10)
            return r.json()
        except Exception as e:
            return {"error": f"PC2 offline o inalcanzable: {str(e)}"}
    
    def chat(self, prompt, model="deepseek-r1:7b"):
        """Envía mensaje a Hermes en PC2"""
        try:
            r = requests.post(f"{self.pc2_url}/skills/execute", json={
                "skill": "hermes",
                "method": "chat",
                "params": {"prompt": prompt, "model": model}
            }, timeout=120)
            return r.json()
        except Exception as e:
            return {"error": str(e)}
    
    def search(self, query):
        """Búsqueda web usando Hermes en PC2"""
        try:
            r = requests.post(f"{self.pc2_url}/skills/execute", json={
                "skill": "hermes",
                "method": "search",
                "params": {"query": query}
            }, timeout=60)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

def get_skill():
    return HermesSkill()