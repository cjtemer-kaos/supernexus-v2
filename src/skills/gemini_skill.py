#!/usr/bin/env python3
"""Google Gemini Skill - Usa la API de Gemini para búsquedas y análisis"""
import requests
import os

from pathlib import Path

class GoogleGeminiSkill:
    def __init__(self):
        self.name = "gemini"
        self.description = "Motor de búsqueda y análisis con Google Gemini"
        self.api_key = self._load_key()
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    def _load_key(self):
        path = Path(__file__).parent.parent.parent / "config" / "apis" / "apis_google.env"
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    if "GEMINI_API_KEY" in line:
                        return line.split("=")[1].strip()
        return ""
    
    def info(self):
        return {"skill": self.name, "api_key_set": bool(self.api_key)}
    
    def chat(self, prompt, model="gemini-2.0-flash"):
        """Envía mensaje a Gemini"""
        if not self.api_key:
            return {"error": "API key no configurada"}
        
        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
        
        data = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        try:
            r = requests.post(url, json=data, timeout=60)
            result = r.json()
            return {
                "response": result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", ""),
                "model": model
            }
        except Exception as e:
            return {"error": str(e)}
    
    def search(self, query):
        """Búsqueda usando Gemini"""
        prompt = f"Busca información actualizada sobre: {query}. Proporciona un resumen conciso con fuentes si es posible."
        return self.chat(prompt)
    
    def research(self, topic):
        """Investigación profunda"""
        prompt = f"""Investiga a fondo sobre: {topic}

Proporciona:
1. Definición y explicación clara
2. Casos de uso principales
3. Herramientas y tecnologías relacionadas
4. Mejores prácticas
5. Recursos para aprender más (links)
6. Últimos desarrollos o noticias"""
        
        return self.chat(prompt, "gemini-2.0-flash")
    
    def analyze(self, content):
        """Analiza contenido"""
        prompt = f"Analiza el siguiente contenido y proporciona insights:\n\n{content}"
        return self.chat(prompt)
    
    def vision(self, image_url, prompt="Describe esta imagen"):
        """Análisis de imagen con Gemini"""
        if not self.api_key:
            return {"error": "API key no configurada"}
        
        url = f"{self.base_url}/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        
        data = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"file_data": {"mime_type": "image/jpeg", "file_uri": image_url}}
                ]
            }]
        }
        
        try:
            r = requests.post(url, json=data, timeout=60)
            result = r.json()
            return {"response": result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")}
        except Exception as e:
            return {"error": str(e)}

if __name__ == "__main__":
    skill = GoogleGeminiSkill()
    print(skill.info())