"""
Gema Scholar - Investigacion web para SuperNEXUS v2.0

Investiga en la web, analiza fuentes, extrae conocimiento.
Usa DuckDuckGo para busquedas sin API key.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ScholarGem:
    """
    Gema especializado en investigacion web.
    Busca, analiza y sintetiza informacion.
    """

    def __init__(self):
        self.search_history: List[Dict] = []
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SuperNEXUS/2.0"}
        )

    async def research(self, query: str, max_sources: int = 5) -> Dict:
        """
        Investiga un tema en la web.
        Busca fuentes, analiza contenido, sintetiza resultados.
        """
        logger.info(f"ScholarGem researching: {query}")

        result = {
            "query": query,
            "sources": [],
            "summary": "",
            "timestamp": datetime.now().isoformat(),
        }

        sources = await self._search_web(query, max_sources)

        for source in sources:
            content = await self._fetch_and_analyze(source["url"])
            if content:
                result["sources"].append({
                    "url": source["url"],
                    "title": source.get("title", ""),
                    "snippet": source.get("snippet", ""),
                    "summary": content[:500],
                })

        result["summary"] = await self._synthesize(result["sources"], query)
        self.search_history.append(result)
        return result

    async def analyze_link(self, url: str) -> Dict:
        """Analiza un link especifico pasado por el usuario"""
        logger.info(f"ScholarGem analyzing: {url}")

        content = await self._fetch_and_analyze(url)
        if not content:
            return {"success": False, "error": "Could not fetch content"}

        return {
            "success": True,
            "url": url,
            "content_preview": content[:1000],
            "word_count": len(content.split()),
        }

    async def _search_web(self, query: str, max_results: int) -> List[Dict]:
        """Busca en DuckDuckGo (sin API key)"""
        results = []
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
            r = await self.client.get(url)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.select("a.result__snippet"):
                    link = a.find_previous_sibling("a", class_="result__url")
                    if link and link.get("href"):
                        # DuckDuckGo usa redirect URLs, extraer URL real
                        raw_url = link["href"]
                        if raw_url.startswith("//duckduckgo.com/l/?uddg="):
                            from urllib.parse import unquote
                            raw_url = unquote(raw_url.split("uddg=")[1].split("&")[0])

                        results.append({
                            "url": raw_url,
                            "title": link.get_text(strip=True),
                            "snippet": a.get_text(strip=True),
                        })
                        if len(results) >= max_results:
                            break
        except Exception as e:
            logger.error(f"Search error: {e}")
        return results

    async def _fetch_and_analyze(self, url: str) -> Optional[str]:
        """Obtiene contenido de una URL y extrae texto"""
        try:
            r = await self.client.get(url, follow_redirects=True)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                # Eliminar scripts y estilos
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                text = soup.get_text(separator="\n", strip=True)
                # Limpiar texto
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                return "\n".join(lines)[:5000]
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
        return None

    async def _synthesize(self, sources: List[Dict], query: str) -> str:
        """Sintetiza resultados de multiples fuentes"""
        if not sources:
            return "No sources found."

        summaries = [s.get("snippet", "")[:200] for s in sources]
        return f"Found {len(sources)} sources for '{query}'. Key points:\n" + "\n".join(
            f"- {s}" for s in summaries if s
        )

    async def close(self):
        await self.client.aclose()
