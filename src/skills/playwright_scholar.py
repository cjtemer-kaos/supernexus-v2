#!/usr/bin/env python3
"""Playwright Scholar Skill - Navegación autónoma con Playwright"""
import json

class PlaywrightScholarSkill:
    def __init__(self):
        self.name = "playwright_scholar"
        self.description = "Navegación autónoma Chrome/Firefox via Playwright"
        self.available = False
        self._check()
    
    def _check(self):
        try:
            from playwright.sync_api import sync_playwright
            self.available = True
        except ImportError:
            self.available = False
    
    def search(self, query, browser="chromium"):
        if not self.available:
            return {"error": "Playwright no instalado. Ejecuta: pip install playwright && playwright install"}
        
        from playwright.sync_api import sync_playwright
        results = []
        
        with sync_playwright() as p:
            browser_instance = p[browser].launch(headless=True)
            page = browser_instance.new_page()
            
            try:
                page.goto(f"https://www.google.com/search?q={query}")
                page.wait_for_selector("h3")
                
                for item in page.query_selector_all("h3")[:5]:
                    try:
                        title = item.text_content()
                        link = item.evaluate("el => el.parentElement.href")
                        results.append({"title": title, "link": link})
                    except: pass
            finally:
                browser_instance.close()
        
        return {"query": query, "results": results}
    
    def research_url(self, url, instructions="Resumir"):
        if not self.available:
            return {"error": "Playwright no instalado"}
        
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser_instance = p.chromium.launch(headless=True)
            page = browser_instance.new_page()
            
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                # Extraer texto limpio directamente desde el navegador
                text_content = page.evaluate("""() => {
                    const scripts = document.querySelectorAll('script, style, nav, footer, iframe');
                    scripts.forEach(s => s.remove());
                    return document.body.innerText;
                }""")
                content = text_content[:3000] if text_content else "No content extracted"
                title = page.title()
            finally:
                browser_instance.close()
        
        return {"url": url, "title": title, "content": content[:1000], "next": instructions}
    
    def run(self, task="", mode="search", output_file=""):
        if mode == "search":
            return json.dumps(self.search(task), indent=2)
        elif mode == "research":
            return json.dumps(self.research_url(task), indent=2)
        return json.dumps({"error": "Modo inválido"})
    
    def vision_analyze(self, url, prompt="Describe esta página"):
        if not self.available:
            return {"error": "Playwright no instalado"}
        
        from playwright.sync_api import sync_playwright
        import os, tempfile, time
        from vision_skill import VisionSkill
        
        vision = VisionSkill()
        output = os.path.join(tempfile.gettempdir(), f"scholar_vision_{int(time.time())}.png")
        
        with sync_playwright() as p:
            browser_instance = p.chromium.launch(headless=True)
            page = browser_instance.new_page()
            
            try:
                page.goto(url, wait_until="networkidle")
                page.screenshot(path=output)
                analysis = vision.analyze(output, prompt)
                return {"url": url, "analysis": analysis}
            finally:
                browser_instance.close()
                if os.path.exists(output): os.remove(output)
    
    def info(self) -> dict:
        return {
            "skill": self.name,
            "description": self.description,
            "available": self.available,
            "methods": ["search(query)", "research_url(url)", "vision_analyze(url, prompt)", "run(task, mode)"]
        }

if __name__ == "__main__":
    print(json.dumps(PlaywrightScholarSkill().info(), indent=2))