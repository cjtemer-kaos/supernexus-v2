#!/usr/bin/env python3
"""Chrome Scholar Skill - Navegación autónoma + Investigación"""
import json
import os
import time

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class ChromeScholarSkill:
    def __init__(self):
        self.name = "chrome_scholar"
        self.description = "Navegación autónoma Chrome + investigación"
        self.SELENIUM_AVAILABLE = SELENIUM_AVAILABLE
    
    def init_browser(self, headless=True):
        if not SELENIUM_AVAILABLE:
            return {"error": "Selenium no está instalado"}
        
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        driver = webdriver.Chrome(options=options)
        return driver
    
    def search_and_research(self, query, max_results=5):
        if not SELENIUM_AVAILABLE:
            return {"error": "Selenium no disponible"}
        
        driver = self.init_browser()
        results = []
        
        try:
            # Buscar en Google
            driver.get(f"https://www.google.com/search?q={query}")
            time.sleep(2)
            
            # Extraer títulos
            titles = driver.find_elements(By.CSS_SELECTOR, "h3")
            for t in titles[:max_results]:
                try:
                    results.append({
                        "title": t.text,
                        "link": t.find_element(By.XPATH, "..").get_attribute("href")
                    })
                except: pass
            
            return {"query": query, "results": results}
        finally:
            driver.quit()
    
    def research_url(self, url, instructions="Resumir el contenido"):
        if not SELENIUM_AVAILABLE:
            return {"error": "Selenium no disponible"}
        
        driver = self.init_browser()
        
        try:
            driver.get(url)
            time.sleep(3)
            
            # Obtener contenido
            content = driver.page_source[:5000]
            
            return {
                "url": url,
                "content": content[:1000],
                "instructions": instructions,
                "next_step": "Enviar contenido a LLM para análisis"
            }
        finally:
            driver.quit()
    
    def run(self, task="", mode="search", output_file=""):
        if mode == "search":
            return json.dumps(self.search_and_research(task), indent=2)
        elif mode == "research":
            return json.dumps(self.research_url(task), indent=2)
        return json.dumps({"error": "Modo no válido"})
    
    def info(self) -> dict:
        return {
            "skill": self.name,
            "description": self.description,
            "selenium": SELENIUM_AVAILABLE,
            "methods": ["search_and_research(query)", "research_url(url)", "run(task, mode)"]
        }

if __name__ == "__main__":
    s = ChromeScholarSkill()
    print(json.dumps(s.info(), indent=2))