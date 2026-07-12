"""
Gema Scholar - Investigacion web para SuperNEXUS v2.0

Investiga en la web con respaldo multi-backend:
  WebResearcher -> DDG -> Brave Search MCP -> agent-browser -> Playwright
Para navegacion directa: HTTP -> Playwright -> Chrome DevTools

NUEVO: Deep Research iterativo (inspirado en Odysseus/IterResearch):
  Loop Think->Search->Extract->Synthesize con planning LLM y stop criteria
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class ScholarGem:
    def __init__(self, web_researcher=None, mcp_client=None, llm_caller=None):
        self.search_history: List[Dict] = []
        self.web = web_researcher
        self.mcp = mcp_client
        self.llm_caller = llm_caller  # async function(prompt, temperature, max_tokens) -> str
        self._search_cache: Dict[str, tuple] = {}  # query -> (result, timestamp)
        self._cache_ttl = 3600  # 1 hora

    async def execute(self, task: str, context: str = "") -> Dict:
        return await self.research(task)

    async def research(self, query: str, max_sources: int = 5, deep: bool = False, include_tor: bool = False) -> Dict:
        """
        Investigacion web.

        Args:
            query: Pregunta a investigar
            max_sources: Numero maximo de fuentes (modo simple)
            deep: Si True, usa DeepResearcher iterativo (mas lento pero mas completo)
            include_tor: Si True, incluye busqueda en darkweb via Tor
        """
        logger.info(f"ScholarGem researching: {query} (deep={deep}, tor={include_tor})")

        if deep and self.llm_caller:
            return await self._deep_research(query)

        return await self._simple_research(query, max_sources, include_tor=include_tor)

    async def darkweb_search(self, query: str, max_sources: int = 5) -> Dict:
        """Busqueda especifica en darkweb via Tor network."""
        logger.info(f"ScholarGem darkweb search: {query}")
        result = {
            "query": query, "mode": "darkweb", "sources": [],
            "summary": "", "timestamp": datetime.now().isoformat(),
        }
        try:
            from src.core.web_researcher import WebResearcher
            researcher = WebResearcher(mcp_client=self.mcp)
            sources = await researcher.search(query, max_sources, include_tor=True)
            result["sources"] = sources
        except Exception as e:
            logger.warning(f"Darkweb search failed: {e}")
            result["error"] = str(e)
        if result["sources"]:
            result["summary"] = await self._synthesize(result["sources"], query)
        self.search_history.append(result)
        return result

    async def navigate_onion(self, url: str) -> Dict:
        """Navegar a un sitio .onion via Tor y extraer contenido."""
        logger.info(f"ScholarGem navigating to .onion: {url[:60]}...")
        try:
            from src.core.web_researcher import WebResearcher
            researcher = WebResearcher(mcp_client=self.mcp)
            return await researcher.navigate_tor(url)
        except Exception as e:
            return {"url": url, "error": str(e), "status": "exception"}

    async def _simple_research(self, query: str, max_sources: int, include_tor: bool = False) -> Dict:
        """Investigacion simple (single-pass) - rapida con cache y fetch paralelo."""
        # Check cache
        cache_key = f"{query}:{max_sources}:{include_tor}"
        if cache_key in self._search_cache:
            cached_result, cached_time = self._search_cache[cache_key]
            import time
            if time.time() - cached_time < self._cache_ttl:
                logger.info(f"ScholarGem cache hit for '{query[:50]}'")
                return cached_result
        
        result = {
            "query": query,
            "mode": "simple",
            "sources": [],
            "summary": "",
            "timestamp": datetime.now().isoformat(),
        }

        sources = await self._search_web(query, max_sources, include_tor=include_tor)

        # Fetch paralelo con semáforo (max 3 concurrentes)
        sem = asyncio.Semaphore(3)
        async def fetch_one(source):
            async with sem:
                content = await self._fetch_and_analyze(source["url"])
                if content:
                    return {
                        "url": source["url"],
                        "title": source.get("title", ""),
                        "snippet": source.get("snippet", ""),
                        "source": source.get("source", "unknown"),
                        "summary": content[:500],
                    }
                return None
        
        tasks = [fetch_one(s) for s in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, dict):
                result["sources"].append(r)

        result["summary"] = await self._synthesize(result["sources"], query)
        self.search_history.append(result)
        
        # Cache result
        import time
        self._search_cache[cache_key] = (result, time.time())
        
        return result

    async def _deep_research(self, query: str, progress_callback: Optional[Callable] = None) -> Dict:
        """Investigacion profunda iterativa (inspirada en Odysseus)."""
        from src.core.deep_research import DeepResearcher
        
        researcher = DeepResearcher(
            llm_caller=self.llm_caller,
            max_rounds=6,
            max_time=300,
            progress_callback=progress_callback,
        )
        
        report = await researcher.research(query)
        stats = researcher.get_stats()
        
        result = {
            "query": query,
            "mode": "deep",
            "report": report,
            "stats": stats,
            "sources": [
                {"url": f.get("url", ""), "title": f.get("title", "")}
                for f in researcher.findings
            ],
            "timestamp": datetime.now().isoformat(),
        }
        self.search_history.append(result)
        return result

    async def _raw_fetch(self, url: str) -> str | None:
        """Fetch URL content using web_researcher first, fallback httpx."""
        if self.web:
            try:
                content = await self.web.navigate(url)
                if content and len(str(content)) > 100:
                    return str(content)
            except Exception:
                pass
        import httpx
        from bs4 import BeautifulSoup
        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as c:
                r = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside"]):
                        tag.decompose()
                    text = soup.get_text(separator="\n", strip=True)
                    lines = [line.strip() for line in text.split("\n") if line.strip()]
                    return "\n".join(lines)
            return None
        except Exception:
            return None

    async def ingest_url(self, url: str) -> Dict:
        """Investiga un URL, busca contexto adicional y persiste via Sage.
        
        Pipeline: fetch → (GitHub: raw README) → search context if needed → Sage persist
        """
        from urllib.parse import urlparse
        from src.agents.sage_gem import SageGem
        sage = SageGem()
        content = None
        base_url = url

        # GitHub: fetch raw content
        parsed = urlparse(url)
        if parsed.netloc == "github.com":
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2:
                user, repo = parts[0], parts[1]
                if len(parts) >= 5 and parts[2] == "blob":
                    branch = parts[3]
                    filepath = "/".join(parts[4:])
                    raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{filepath}"
                    raw = await self._raw_fetch(raw_url)
                    if raw:
                        content = f"GitHub: {user}/{repo}/{branch}/{filepath}\n\n{raw[:8000]}"
                        base_url = raw_url
                else:
                    for branch in ("main", "master"):
                        raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/README.md"
                        raw = await self._raw_fetch(raw_url)
                        if raw:
                            content = f"GitHub Repo: {user}/{repo}\nREADME ({branch}):\n\n{raw[:8000]}"
                            base_url = raw_url
                            break

        if not content:
            raw = await self._raw_fetch(url)
            if raw:
                content = raw[:5000]

        if not content:
            return {"success": False, "error": "No se pudo obtener contenido del URL"}

        topic = f"url:{url}"
        result = await sage.analyze_and_persist(content, base_url, "web", topic=topic)
        sage.consolidate()
        return {**result, "content_length": len(content)}

    async def analyze_link(self, url: str) -> Dict:
        logger.info(f"ScholarGem analyzing: {url}")
        raw = await self._raw_fetch(url)
        if raw:
            return {"success": True, "url": url, "content_preview": raw[:1000], "word_count": len(raw.split())}
        return {"success": False, "error": "Empty content after parse"}

    async def _search_web(self, query: str, max_results: int, include_tor: bool = False) -> List[Dict]:
        if self.web:
            return await self.web.search(query, max_results, include_tor=include_tor)

        # Use WebResearcher as primary backend (has DDG + Brave MCP + agent-browser + Playwright + Tor)
        try:
            from src.core.web_researcher import WebResearcher
            researcher = WebResearcher(mcp_client=self.mcp)
            results = await researcher.search(query, max_results, include_tor=include_tor)
            if results:
                logger.info(f"WebResearcher returned {len(results)} results for '{query}'")
                return results
        except Exception as e:
            logger.warning(f"WebResearcher failed: {e}")

        # Final fallback: DDGS direct
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = []
                for i, r in enumerate(ddgs.text(query, max_results=max_results)):
                    results.append({
                        "url": r.get("href", ""),
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "source": "ddgs",
                    })
                    if len(results) >= max_results:
                        break
            if results:
                return results
        except Exception as e:
            logger.warning(f"DDGS fallback also failed: {e}")

        logger.warning(f"No search results for '{query}' from any backend")
        return []

    async def _fetch_and_analyze(self, url: str) -> Optional[str]:
        if self.web:
            return await self.web.navigate(url)

        import httpx
        from bs4 import BeautifulSoup
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as c:
                r = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    for tag in soup(["script", "style", "nav", "footer", "header"]):
                        tag.decompose()
                    text = soup.get_text(separator="\n", strip=True)
                    lines = [line.strip() for line in text.split("\n") if line.strip()]
                    return "\n".join(lines)[:5000]
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
        return None

    async def _synthesize(self, sources: List[Dict], query: str) -> str:
        if not sources:
            return "No sources found."

        backends = set(s.get("source", "unknown") for s in sources)
        summaries = [s.get("snippet", "")[:200] for s in sources]
        return (
            f"Found {len(sources)} sources for '{query}' "
            f"(via {', '.join(sorted(backends))}).\n"
            + "\n".join(f"- {s}" for s in summaries if s)
        )

    async def close(self):
        pass
