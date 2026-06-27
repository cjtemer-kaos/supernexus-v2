"""
ScholarGem — Gema de investigación web multi-backend.

Por defecto usa HTTP simple. Clientes pueden inyectar web_researcher y
mcp_client más sofisticados (Playwright, Brave, firecrawl, exa, etc.) vía
el constructor o assignment post-init.

Backends por prioridad:
  1. web_researcher (inyectado)
  2. mcp_client (inyectado)
  3. HTTP simple (fallback)

All retrieved web content is treated as UNTRUSTED — the LLM may receive
it only via ``as_chat_messages()``, which wraps each source in a
sentinel-bounded user-role message (see
:mod:`gemas_core.core.prompt_security`).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..base import GemaBase
from ..core.prompt_security import untrusted_context_message
from src.security.ssrf_guard import ensure_safe_url

logger = logging.getLogger("gemas-core.workers.scholar")


class ScholarGem(GemaBase):
    """Gema de investigación web."""

    name = "scholar"
    description = "Investigación web multi-backend con síntesis y citaciones"
    category = "research"

    def __init__(
        self,
        web_researcher: Optional[Any] = None,
        mcp_client: Optional[Any] = None,
    ):
        self.search_history: List[Dict[str, Any]] = []
        self.web = web_researcher
        self.mcp = mcp_client

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        return await self.research(task)

    async def research(self, query: str, max_sources: int = 5) -> Dict[str, Any]:
        """Investiga una query en la web. Retorna dict con sources y summary."""
        logger.info(f"ScholarGem researching: {query}")
        result: Dict[str, Any] = {
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
                    "source": source.get("source", "unknown"),
                    "summary": content[:500],
                })

        result["summary"] = await self._synthesize(result["sources"], query)
        result["success"] = bool(result["sources"]) or bool(result["summary"])
        result["gema"] = "scholar"
        self.search_history.append(result)
        return result

    async def _search_web(self, query: str, max_sources: int) -> List[Dict[str, Any]]:
        """Búsqueda web. Override o inyecta web_researcher para custom backends."""
        if self.web and hasattr(self.web, "search"):
            return await self.web.search(query, max_results=max_sources)
        if self.mcp and hasattr(self.mcp, "brave_search"):
            return await self.mcp.brave_search(query, count=max_sources)
        # Fallback HTTP
        return await self._http_search(query, max_sources)

    async def _http_search(self, query: str, max_sources: int) -> List[Dict[str, Any]]:
        """HTTP search fallback via DuckDuckGo HTML."""
        try:
            import aiohttp
            url = "https://html.duckduckgo.com/html/"
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data={"q": query},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return []
                    text = await resp.text()
            return self._parse_ddg_html(text, max_sources)
        except Exception as e:
            logger.warning(f"ScholarGem http search failed: {e}")
            return []

    @staticmethod
    def _parse_ddg_html(html: str, max_sources: int) -> List[Dict[str, Any]]:
        """Parsea HTML de DuckDuckGo. Mínimo viable: extrae result__a links."""
        import re
        out: List[Dict[str, Any]] = []
        pattern = re.compile(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>',
            re.IGNORECASE,
        )
        for m in pattern.finditer(html):
            url = m.group(1)
            title = m.group(2).strip()
            if not url.startswith("http"):
                continue
            out.append({
                "url": url,
                "title": title,
                "snippet": "",
                "source": "duckduckgo",
            })
            if len(out) >= max_sources:
                break
        return out

    async def _fetch_and_analyze(self, url: str) -> Optional[str]:
        """Fetch + extract main text. Override para analisis mas sofisticado."""
        try:
            ensure_safe_url(url)
        except Exception as e:
            logger.warning(f"SSRF blocked: {url} — {e}")
            return None
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=15),
                    headers={"User-Agent": "Mozilla/5.0 NexusScholar"},
                ) as resp:
                    if resp.status != 200:
                        return None
                    html = await resp.text()
            return self._extract_text(html)
        except Exception as e:
            logger.debug(f"fetch failed for {url}: {e}")
            return None

    @staticmethod
    def _extract_text(html: str) -> str:
        """Extrae texto plano de HTML (best-effort, sin BeautifulSoup)."""
        import re
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()[:5000]

    async def _synthesize(self, sources: List[Dict[str, Any]], query: str) -> str:
        """Síntesis básica. Clientes pueden override para usar LLM."""
        if not sources:
            return f"No se encontraron fuentes para: {query}"
        parts = [f"Investigación sobre '{query}':", ""]
        for i, s in enumerate(sources, 1):
            parts.append(f"{i}. {s.get('title', s['url'])}")
            if s.get("summary"):
                parts.append(f"   {s['summary'][:200]}")
        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": "scholar",
            "name": "SCHOLAR",
            "description": self.description,
            "category": self.category,
            "type": "dedicated",
            "backends": (
                ["web_researcher", "mcp_client", "http_fallback"]
                if self.web or self.mcp
                else ["http_fallback"]
            ),
        }

    def as_chat_messages(
        self, label: str = "scholar"
    ) -> List[Dict[str, Any]]:
        """Wrap the most recent research result as untrusted chat messages.

        Each retrieved source becomes a separate ``role: user`` message
        with ``metadata.trusted = False`` and ``metadata.source =
        f"{label}[{i}].{url}"``. The synthesizer summary is omitted —
        by the time the caller has these messages, the LLM should
        re-synthesize the sources itself rather than trust a previously
        generated summary.

        Returns an empty list if ``research()`` has not been called yet.
        """
        if not self.search_history:
            return []
        last = self.search_history[-1]
        sources = last.get("sources", [])
        if not sources:
            return []
        # One message per source, each carries its URL in the label for
        # auditability.
        return [
            untrusted_context_message(
                f"{label}[{i}].{s.get('url', 'unknown')}",
                json.dumps(
                    {
                        "title": s.get("title", ""),
                        "snippet": s.get("snippet", ""),
                        "summary": s.get("summary", ""),
                        "source": s.get("source", "unknown"),
                    },
                    ensure_ascii=False,
                ),
            )
            for i, s in enumerate(sources)
        ]
