from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests

class ScholarWebSkill:
    status = "ENABLED"
    reason = "Utiliza duckduckgo_search API y Requests (sin navegador UI/Playwright)"

    def __init__(self):
        self.name = "scholar_web"
        self.description = "Búsqueda e investigación web ultrarrápida (Headless/API)"
    
    def info(self):
        return {"skill": self.name, "description": self.description, "status": self.status}
    
    def search(self, query, max_results=20):
        """Busca usando DuckDuckGo API con mayor profundidad"""
        results = []
        try:
            with DDGS() as ddgs:
                # Usamos un generador para obtener más resultados y filtrarlos después
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title"), 
                        "url": r.get("href"), 
                        "snippet": r.get("body"),
                        "source": "duckduckgo"
                    })
        except Exception as e:
            results = [{"error": str(e)}]
        
        return {"query": query, "results": results}
    
    def research_url(self, url, prompt="Resume el contenido"):
        """Investiga una URL específica usando requests nativo (Soporta Darkweb/Tor)"""
        content = ""
        title = "Sin título"
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            
            # Soporte nativo para Darkweb (.onion) a través del proxy local de Tor
            proxies = None
            if ".onion" in url:
                proxies = {
                    'http': 'socks5h://127.0.0.1:9050',
                    'https': 'socks5h://127.0.0.1:9050'
                }
                
            response = requests.get(url, headers=headers, proxies=proxies, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.title.string if soup.title else "Sin título"
                # Eliminar scripts y estilos para extraer solo texto limpio
                for script in soup(["script", "style", "nav", "footer"]):
                    script.extract()
                text = soup.get_text(separator=' ', strip=True)
                content = text[:3000] if text else ""
            else:
                content = f"Error: Status code {response.status_code}"
                
        except Exception as e:
            content = f"Error: {str(e)}"
            
        return {"url": url, "title": title, "content": content}
    
    def research_topic(self, topic, depth=3):
        """Investigación multifuente con síntesis avanzada"""
        search = self.search(topic, max_results=15)
        findings = []
        
        if search.get("results") and len(search["results"]) > 0:
            # Tomamos los mejores resultados según la profundidad solicitada
            top_sources = search["results"][:depth]
            
            for source in top_sources:
                if "url" in source:
                    res = self.research_url(source["url"])
                    findings.append({
                        "title": source["title"],
                        "url": source["url"],
                        "content": res.get("content", "")[:1500]
                    })
            
            return {
                "topic": topic,
                "sources_analyzed": len(findings),
                "data": findings
            }
        
        return {"topic": topic, "results": search.get("results", [])}

if __name__ == "__main__":
    skill = ScholarWebSkill()
    import json
    print(json.dumps(skill.info(), indent=2))