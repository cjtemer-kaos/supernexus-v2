#!/usr/bin/env python3
"""Hermes Scholar Integration - Usa las skills de Scholar de Nexus"""
import subprocess
import json
import sys
from pathlib import Path

class HermesScholarIntegration:
    def __init__(self):
        self.name = "hermes_scholar"
        self.description = "Integra Scholar de Nexus con Hermes para búsquedas web"
    
    def info(self):
        return {"skill": self.name, "description": self.description}
    
    def _run_skill(self, skill_module, method, *args):
        """Ejecuta un método de skill de Nexus"""
        try:
            # Agregar el path de skills de supernexus
            sys.path.insert(0, str(Path(__file__).parent / "hub"))
            module = __import__(skill_module.replace("_skill", ""))
            
            # Obtener la clase del skill
            skill_class = None
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and "Skill" in name:
                    skill_class = obj
                    break
            
            if skill_class:
                skill_instance = skill_class()
                method_func = getattr(skill_instance, method, None)
                if method_func:
                    return method_func(*args)
            return {"error": "Skill no encontrado"}
        except Exception as e:
            return {"error": str(e)}
    
    def search_web(self, query):
        """Búsqueda web usando Playwright Scholar"""
        return self._run_skill("playwright_scholar", "search", query)
    
    def research_url(self, url, instructions="Resumir"):
        """Investigar una URL específica"""
        return self._run_skill("playwright_scholar", "research_url", url, instructions)
    
    def chrome_search(self, query):
        """Búsqueda usando Chrome Scholar (Selenium)"""
        return self._run_skill("chrome_scholar", "search_and_research", query)
    
    def extract_content(self, url):
        """Extrae contenido de una página"""
        return self._run_skill("playwright_scholar", "research_url", url, "Extrae todo el contenido relevante")
    
    def research_topic(self, topic):
        """Investigación completa de un tema"""
        # Paso 1: Buscar en Google
        search_results = self.search_web(topic)
        
        # Paso 2: Investigar el primer resultado
        if search_results.get("results"):
            first_result = search_results["results"][0]
            url = first_result.get("link", "")
            if url:
                content = self.research_url(url, f"Resumen detallado sobre: {topic}")
                return {
                    "topic": topic,
                    "search_results": search_results["results"],
                    "analysis": content
                }
        
        return {"topic": topic, "results": search_results}

if __name__ == "__main__":
    skill = HermesScholarIntegration()
    print(json.dumps(skill.info(), indent=2))