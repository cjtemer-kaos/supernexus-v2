#!/usr/bin/env python3
"""Mentor Research Skill - Investigación de canales y mentores"""
import subprocess
import json

from pathlib import Path

class MentorResearchSkill:
    def __init__(self):
        self.name = "mentor_research"
        self.description = "Investiga y registra canales de YouTube y mentores"
        self.mentors_file = str(Path(__file__).parent.parent.parent / "brain" / "1_NEXUS" / "MENTORS.md")
    
    def info(self):
        return {"skill": self.name, "description": self.description}
    
    def search_youtube(self, query):
        """Busca canales en YouTube"""
        try:
            from playwright.sync_api import sync_playwright
            results = []
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"https://www.youtube.com/results?search_query={query}+channel")
                page.wait_for_timeout(2000)
                
                for result in page.query_selector_all("ytd-channel-renderer")[:5]:
                    try:
                        title = result.query_selector("#title")
                        link = result.query_selector("a")
                        if title and link:
                            results.append({
                                "name": title.text_content(),
                                "url": link.get_attribute("href")
                            })
                    except: pass
                browser.close()
            return {"query": query, "channels": results}
        except:
            return {"error": "Playwright no disponible. Instalar: pip install playwright && playwright install chromium"}
    
    def add_mentor(self, name, url, specialty, source=""):
        """Agrega un mentor al archivo"""
        entry = f"""
### {name}
- **Especialidad**: {specialty}
- **Canal**: {url}
- **Fuente**: {source}
- **Fecha agregada**: {subprocess.run(['date', '+%Y-%m-%d'], capture_output=True, text=True).stdout.strip()}
"""
        with open(self.mentors_file, "a") as f:
            f.write(entry)
        return {"added": name, "specialty": specialty}
    
    def list_mentors(self):
        """Lista mentores registrados"""
        try:
            with open(self.mentors_file, "r") as f:
                content = f.read()
            return {"mentors_file": self.mentors_file, "content": content[:500]}
        except:
            return {"error": "Archivo no encontrado"}
    
    def research_from_video(self, video_url):
        """Investiga el canal del video"""
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(video_url)
                page.wait_for_timeout(2000)
                
                channel_name = ""
                channel_link = ""
                
                # Buscar nombre del canal
                try:
                    channel_elem = page.query_selector("#channel-name a")
                    if channel_elem:
                        channel_name = channel_elem.text_content()
                        channel_link = channel_elem.get_attribute("href")
                except: pass
                
                browser.close()
                return {"channel": channel_name, "url": channel_link}
        except Exception as e:
            return {"error": str(e)}

if __name__ == "__main__":
    skill = MentorResearchSkill()
    print(json.dumps(skill.info(), indent=2))