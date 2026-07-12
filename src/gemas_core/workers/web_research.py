"""
WebResearchGem — v1.6.0 Gema que envuelve las primitives de web
research (RecursiveCrawler + rank_content) detrás de la interfaz
estándar de GemaBase.

Pipeline:
  1. Valida start_urls (drop non-http, javascript:, etc.)
  2. Crawl con el Fetcher inyectado (default = aiohttp)
  3. Rank contra el query (KeywordScorer default; Embedder si bound)
  4. Devuelve WebResearchResult con docs + ranked + stats

Uso típico desde una gema o desde código cliente:

    from gemas_core.workers.web_research import WebResearchGem

    gem = WebResearchGem()
    result = await gem.research(
        query="python ai tutorial",
        start_urls=["https://example.com/"],
    )
    for r in result.ranked:
        print(r.text[:200], r.score)

O la función de conveniencia:

    from gemas_core.workers.web_research import web_research
    result = await web_research(
        query="python",
        start_urls=["..."],
        fetcher=my_fetcher,  # optional, defaults to aiohttp
    )

Inyección de backends:
    gem.bind_fetcher(my_aiohttp_fetcher)   # required for real HTTP
    gem.bind_embedder(my_ollama_embedder)  # optional; keyword is default

Diseño:
  - No usamos aiohttp en el módulo — el caller inyecta un Fetcher.
    Esto mantiene gemas_core aiohttp-free salvo en los tests.
  - ``execute(task, context)`` se mantiene compatible con
    dispatch_gema: parsea ``context`` como JSON con start_urls,
    max_depth, top_k.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, NamedTuple, Optional

from ..base import GemaBase
from ..core.url_utils import is_valid_url
from ..core.web_crawler import CrawledDoc, RecursiveCrawler
from ..core.text_ranker import Embedder, ScoredItem, rank_content

logger = logging.getLogger("gemas-core.workers.web_research")


class WebResearchResult(NamedTuple):
    """Result of a ``WebResearchGem.research()`` call.

    Fields:
        docs:           CrawledDoc list (url, text, depth).
        ranked:         ScoredItem list (text, score) sorted desc.
        fetch_attempts: Number of URLs the crawler tried to fetch.
        fetch_failures: Number of fetches that returned None / errored.
        skipped_urls:   Number of start_urls that were invalid.
        invalid_start_urls: The actual invalid start URLs (for debugging).
    """

    docs: List[CrawledDoc]
    ranked: List[ScoredItem]
    fetch_attempts: int
    fetch_failures: int
    skipped_urls: int
    invalid_start_urls: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "docs": [
                {"url": d.url, "text": d.text, "depth": d.depth}
                for d in self.docs
            ],
            "ranked": [
                {"text": r.text, "score": r.score} for r in self.ranked
            ],
            "fetch_attempts": self.fetch_attempts,
            "fetch_failures": self.fetch_failures,
            "skipped_urls": self.skipped_urls,
            "invalid_start_urls": list(self.invalid_start_urls),
        }


# A lazy aiohttp fetcher. The actual import is deferred to the
# first ``fetch()`` call so gemas_core stays aiohttp-free at
# import time. This mirrors the lazy-import pattern in
# ``core.rate_limit_helpers``.


class _AiohttpFetcher:
    """Default aiohttp-based Fetcher. Created on first use.

    Not a hard dep — if aiohttp isn't installed, ``research()``
    raises a clear error suggesting ``bind_fetcher()``.
    """

    def __init__(self) -> None:
        try:
            import aiohttp  # noqa: F401
        except ImportError as e:
            raise RuntimeError(
                "aiohttp is required for the default WebResearchGem "
                "fetcher. Either install aiohttp or bind a custom "
                "fetcher via gem.bind_fetcher(your_fetcher)."
            ) from e
        self._session: Optional[Any] = None

    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            import aiohttp
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10.0)
            )
        return self._session

    async def fetch(self, url: str) -> Optional[str]:
        from src.security.ssrf_guard import ensure_safe_url, SSRFBlocked
        try:
            ensure_safe_url(url)
        except SSRFBlocked as e:
            logger.warning(f"SSRF blocked: {url} — {e}")
            return None
        session = await self._ensure_session()
        try:
            async with session.get(url) as r:
                if r.status != 200:
                    return None
                return await r.text()
        except Exception as e:
            logger.warning(f"fetch failed for {url}: {e}")
            return None

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()


class WebResearchGem(GemaBase):
    """Gem that crawls + ranks web pages against a query.

    See module docstring for the full pipeline.
    """

    name = "web_research"
    description = (
        "Crawls web pages (depth-bounded BFS) and ranks them against "
        "a query. Uses stdlib TF-IDF by default; an Embedder can be "
        "injected for vector-based ranking. Supports a caller-provided "
        "Fetcher so any HTTP transport works (aiohttp, httpx, urllib)."
    )
    category = "research"

    def __init__(
        self,
        *,
        max_depth: int = 2,
        max_pages: int = 25,
        max_concurrent: int = 5,
        request_delay: float = 0.1,
    ) -> None:
        self._fetcher: Optional[Any] = None
        self._embedder: Optional[Embedder] = None
        self._owns_fetcher: bool = False
        # Defaults — overridable per-call
        self._default_max_depth = max_depth
        self._default_max_pages = max_pages
        self._default_max_concurrent = max_concurrent
        self._default_request_delay = request_delay
        self.search_history: List[Dict[str, Any]] = []

    # --- Backend injection -------------------------------------------------

    def bind_fetcher(self, fetcher) -> None:
        """Inject a Fetcher (any object with ``async fetch(url)``)."""
        self._fetcher = fetcher
        self._owns_fetcher = False

    def bind_embedder(self, embedder: Embedder) -> None:
        """Inject an Embedder for vector-based ranking. Optional."""
        self._embedder = embedder

    async def _ensure_fetcher(self):
        """Lazy-create a default aiohttp fetcher if none was bound."""
        if self._fetcher is not None:
            return self._fetcher
        self._fetcher = _AiohttpFetcher()
        self._owns_fetcher = True
        return self._fetcher

    # --- Public API --------------------------------------------------------

    async def research(
        self,
        query: str,
        start_urls: List[str],
        *,
        max_depth: Optional[int] = None,
        max_pages: Optional[int] = None,
        top_k: Optional[int] = None,
    ) -> WebResearchResult:
        """Crawl ``start_urls`` and rank the pages against ``query``.

        Parameters
        ----------
        query:
            The reference text to rank candidates against. Typically
            a research prompt or question.
        start_urls:
            List of URLs to start crawling from. Invalid URLs (non-HTTP,
            ``javascript:``, etc.) are dropped silently and listed in
            ``result.invalid_start_urls``.
        max_depth:
            Maximum link-hops to follow. Defaults to constructor value
            (2).
        max_pages:
            Hard cap on total documents crawled. Defaults to constructor
            value (25).
        top_k:
            If set, return only the top-K ranked results. None means
            return all.

        Returns
        -------
        WebResearchResult
            Structured result with ``docs``, ``ranked``,
            ``fetch_attempts``, ``fetch_failures``, ``skipped_urls``,
            ``invalid_start_urls``.
        """
        if not self._fetcher:
            # Try the lazy default. If aiohttp isn't available, this
            # raises a clear error.
            await self._ensure_fetcher()

        # Validate start URLs
        valid_urls: List[str] = []
        invalid: List[str] = []
        for u in start_urls:
            if is_valid_url(u):
                valid_urls.append(u)
            else:
                invalid.append(u)

        if not valid_urls:
            result = WebResearchResult(
                docs=[],
                ranked=[],
                fetch_attempts=0,
                fetch_failures=0,
                skipped_urls=len(invalid),
                invalid_start_urls=invalid,
            )
            self.search_history.append({
                "query": query,
                "start_urls": list(start_urls),
                "result": result.to_dict(),
                "gema": "web_research",
            })
            return result

        # Crawl
        fetcher = self._fetcher
        crawler = RecursiveCrawler(
            fetcher,
            max_depth=max_depth if max_depth is not None else self._default_max_depth,
            max_pages=max_pages if max_pages is not None else self._default_max_pages,
            max_concurrent=self._default_max_concurrent,
            request_delay=self._default_request_delay,
        )
        stats = await crawler.crawl_with_stats(valid_urls)

        # Rank
        texts = [d.text for d in stats.docs]
        ranked = rank_content(
            ref=query,
            candidates=texts,
            embedder=self._embedder,
            top_k=top_k,
        )

        result = WebResearchResult(
            docs=stats.docs,
            ranked=ranked,
            fetch_attempts=stats.fetch_attempts,
            fetch_failures=stats.fetch_failures,
            skipped_urls=len(invalid),
            invalid_start_urls=invalid,
        )
        # Append a flat dict to history (consistent with ScholarGem)
        self.search_history.append({
            "query": query,
            "start_urls": list(start_urls),
            "result": result.to_dict(),
            "gema": "web_research",
        })
        return result

    # --- GemaBase interface ------------------------------------------------

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        """GemaBase.execute — dispatches to ``research()``.

        ``context`` may be a JSON string with these keys:
          - start_urls: List[str]  (required)
          - max_depth:  int        (optional)
          - max_pages:  int        (optional)
          - top_k:      int        (optional)

        On a JSON parse error, we fall back to ``start_urls=[]`` and
        log a warning. The success flag is still True because no
        fatal error occurred (the empty result is valid).
        """
        try:
            ctx = json.loads(context) if context.strip() else {}
        except (ValueError, TypeError) as e:
            logger.warning(f"web_research: bad context JSON: {e}")
            ctx = {}
        start_urls = ctx.get("start_urls", [])
        max_depth = ctx.get("max_depth")
        max_pages = ctx.get("max_pages")
        top_k = ctx.get("top_k")

        result = await self.research(
            query=task,
            start_urls=start_urls,
            max_depth=max_depth,
            max_pages=max_pages,
            top_k=top_k,
        )
        return {
            "success": True,
            "gema": "web_research",
            "result": result,
            "query": task,
            "n_docs": len(result.docs),
            "n_ranked": len(result.ranked),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.name,
            "name": "WEB RESEARCH",
            "description": self.description,
            "category": self.category,
            "type": "dedicated",
        }


# --- Convenience function -----------------------------------------------------


async def web_research(
    query: str,
    start_urls: List[str],
    *,
    fetcher=None,
    embedder: Optional[Embedder] = None,
    max_depth: int = 2,
    max_pages: int = 25,
    top_k: Optional[int] = None,
) -> WebResearchResult:
    """One-shot web research: create a gem, run research, return result.

    For multi-call workflows, instantiate :class:`WebResearchGem`
    directly so you can reuse the bound fetcher and embedder.

    Parameters
    ----------
    query:
        Reference text to rank candidates against.
    start_urls:
        URLs to start crawling from.
    fetcher:
        Optional Fetcher. If None, uses a lazy aiohttp fetcher.
    embedder:
        Optional Embedder. If None, uses KeywordScorer.
    max_depth, max_pages, top_k:
        See :meth:`WebResearchGem.research`.
    """
    gem = WebResearchGem(
        max_depth=max_depth,
        max_pages=max_pages,
    )
    if fetcher is not None:
        gem.bind_fetcher(fetcher)
    if embedder is not None:
        gem.bind_embedder(embedder)
    try:
        return await gem.research(
            query=query,
            start_urls=start_urls,
            top_k=top_k,
        )
    finally:
        if gem._owns_fetcher and gem._fetcher:
            await gem._fetcher.close()
