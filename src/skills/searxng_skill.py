import requests
import json

class SearXNGSkill:
    def __init__(self, base_url="http://100.83.38.20"):
        self.name = "searxng"
        self.description = "Búsqueda soberana multifuente (Google, Bing, DDG combinados)"
        self.base_url = base_url

    def search(self, query, categories="general", language="es-ES"):
        """Realiza una búsqueda en la instancia local de SearXNG"""
        url = f"{self.base_url}/search"
        params = {
            "q": query,
            "categories": categories,
            "language": language,
            "format": "json"
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                results = []
                for r in data.get("results", []):
                    results.append({
                        "title": r.get("title"),
                        "url": r.get("url"),
                        "snippet": r.get("content"),
                        "score": r.get("score", 0),
                        "engines": r.get("engines", [])
                    })
                return {"query": query, "results": results}
            else:
                return {"error": f"Status code {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def info(self):
        return {"skill": self.name, "description": self.description}

if __name__ == "__main__":
    skill = SearXNGSkill()
    # Test rápido
    res = skill.search("mejorar visión local IA RX 570")
    print(json.dumps(res, indent=2))
