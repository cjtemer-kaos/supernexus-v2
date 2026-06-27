"""Async recursive web crawler — stdlib-only.

RUFUS ``core/crawler.py::Crawler._crawl`` is the algorithm we
port here. RUFUS uses ``aiohttp`` for the actual HTTP calls; we
decouple the transport via a :class:`Fetcher` protocol so
gemas_core stays dep-free. Callers inject their own transport
(aiohttp, httpx, urllib3, or a mock in tests).

What we keep from RUFUS:
  - depth-bounded recursion via ``max_depth``
  - URL dedup via a visited set
  - concurrency cap via ``asyncio.Semaphore``
  - per-URL delay between requests
  - HTML→text extraction (we reuse :mod:`gemas_core.core.html_text`)
  - link discovery (we use a stdlib regex; BS4 is out)

What we add beyond RUFUS:
  - hard ``max_pages`` cap (RUFUS only had max_depth; a runaway
    site could crawl thousands of pages)
  - ``crawl_with_stats()`` for diagnostic introspection
  - ``reset()`` to clear the dedup set between calls
  - extract_links() exposed as a standalone helper (RUFUS buried
    it in Crawler._parse_links)
  - deterministic ordering: children processed in the order they
    appear in the source HTML

What we deliberately don't port:
  - the Google search / generate_search_query fallback (separate
    gem-level concern; not appropriate for a stdlib core)
  - the rank_content integration (also gem-level; we have a
    stdlib :class:`KeywordScorer` already in text_ranker)
"""
from __future__ import annotations

import asyncio
import re
from typing import List, NamedTuple, Optional, Protocol, runtime_checkable

from .html_text import extract_text as _extract_text
from .url_utils import (
    is_valid_url,
    normalize_url,
)

__all__ = [
    "CrawledDoc",
    "CrawlStats",
    "Fetcher",
    "RecursiveCrawler",
    "extract_links",
]


# A loose <a href="..."> match. We deliberately don't try to
# parse the whole HTML — that's the html.parser's job for body
# text. For link discovery, the regex is faster, dependency-free,
# and resilient to malformed markup.
_HREF_RE = re.compile(
    r"""<a\b[^>]*?href\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""",
    re.IGNORECASE | re.DOTALL,
)


class CrawledDoc(NamedTuple):
    """One document produced by :meth:`RecursiveCrawler.crawl`."""

    url: str
    text: str
    depth: int


class CrawlStats(NamedTuple):
    """Diagnostic info from :meth:`RecursiveCrawler.crawl_with_stats`."""

    docs: List[CrawledDoc]
    fetch_attempts: int
    fetch_failures: int
    urls_visited: int


@runtime_checkable
class Fetcher(Protocol):
    """Anything with an ``async fetch(url)`` method is a valid transport.

    Returning ``None`` (or raising) signals a fetch failure. The
    crawler will skip the URL and not follow its links.
    """

    async def fetch(self, url: str) -> Optional[str]:
        ...


# -- Link extraction (standalone helper) ---------------------------------------


def extract_links(html: str, base: str = "") -> List[str]:
    """Find all <a href="..."> URLs in ``html`` and resolve them.

    Returns absolute URLs in source order, deduped within the page.
    Invalid / unsafe URLs are dropped (mailto, javascript, data,
    fragment-only, and any URL that doesn't resolve to http/https).

    Parameters
    ----------
    html:
        HTML source. Empty string returns ``[]``.
    base:
        A base URL to resolve relative hrefs against. If empty,
        only absolute URLs are returned.
    """
    if not html:
        return []
    seen: set[str] = set()
    out: List[str] = []
    for m in _HREF_RE.finditer(html):
        href = m.group(1) or m.group(2) or m.group(3) or ""
        if not href:
            continue
        # Filter out pure fragments and unsafe schemes before
        # urljoin (urljoin will happily keep ``javascript:`` as-is).
        lowered = href.strip().lower()
        if not lowered or lowered.startswith("#"):
            continue
        if (
            lowered.startswith("javascript:")
            or lowered.startswith("data:")
            or lowered.startswith("mailto:")
            or lowered.startswith("tel:")
            or lowered.startswith("vbscript:")
        ):
            continue
        absolute = normalize_url(href, base=base) if base else href
        if absolute is None or not is_valid_url(absolute):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        out.append(absolute)
    return out


# -- The crawler ---------------------------------------------------------------


class RecursiveCrawler:
    """Bounded async crawler driven by an injected :class:`Fetcher`.

    The crawler is the *algorithm*; the Fetcher is the *transport*.
    gemas_core ships no Fetcher implementation; callers in
    ``gemas_client_overrides/`` (or wherever) provide aiohttp /
    httpx / urllib3 wrappers.

    The crawler is single-use for dedup purposes: the visited
    set is preserved across ``crawl()`` calls so repeated
    invocations don't refetch. Use :meth:`reset` to clear.

    Parameters
    ----------
    fetcher:
        An object with ``async fetch(url) -> Optional[str]``.
    max_depth:
        Maximum link-hops to follow. ``0`` means only crawl the
        start URLs. Must be non-negative.
    max_pages:
        Hard cap on total documents returned. ``None`` means no
        cap beyond ``max_depth``. Must be positive when set.
    max_concurrent:
        Maximum number of in-flight fetches. Must be positive.
    request_delay:
        Minimum seconds between consecutive fetches. ``0.0`` means
        no delay. Must be non-negative.
    """

    def __init__(
        self,
        fetcher: Fetcher,
        *,
        max_depth: int = 2,
        max_pages: Optional[int] = 100,
        max_concurrent: int = 10,
        request_delay: float = 0.0,
    ) -> None:
        if max_depth < 0:
            raise ValueError(f"max_depth must be >= 0, got {max_depth}")
        if max_pages is not None and max_pages <= 0:
            raise ValueError(f"max_pages must be positive, got {max_pages}")
        if max_concurrent <= 0:
            raise ValueError(
                f"max_concurrent must be positive, got {max_concurrent}"
            )
        if request_delay < 0.0:
            raise ValueError(
                f"request_delay must be non-negative, got {request_delay}"
            )
        self.fetcher = fetcher
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.max_concurrent = max_concurrent
        self.request_delay = request_delay
        self._visited: set[str] = set()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._delay_lock = asyncio.Lock()
        self._last_fetch_at: float = 0.0

    def reset(self) -> None:
        """Clear the visited set so the next ``crawl()`` re-fetches."""
        self._visited.clear()
        self._last_fetch_at = 0.0

    @property
    def visited(self) -> set[str]:
        """Read-only view of the URLs already fetched this session."""
        return set(self._visited)

    async def crawl(
        self,
        start_urls: List[str],
    ) -> List[CrawledDoc]:
        """Crawl from ``start_urls`` and return all documents found.

        Invalid start URLs are dropped silently. The visited set
        is preserved across calls.
        """
        stats = await self.crawl_with_stats(start_urls)
        return stats.docs

    async def crawl_with_stats(
        self,
        start_urls: List[str],
    ) -> CrawlStats:
        """Same as :meth:`crawl` but also returns diagnostic counters."""
        # BFS, level by level. Within a level, we kick off all the
        # fetches concurrently (capped by the semaphore).
        queue: List[tuple[str, int]] = []  # (url, depth)
        for u in start_urls:
            if is_valid_url(u) and u not in self._visited:
                queue.append((u, 0))

        docs: List[CrawledDoc] = []
        fetch_attempts = 0
        fetch_failures = 0
        # Cap total docs returned
        cap = self.max_pages

        while queue:
            # Filter the next level against the cap and dedup.
            # Two URLs at the same depth can be identical because
            # multiple parents at the previous level can link to
            # the same child.
            next_level: List[tuple[str, int]] = []
            for url, depth in queue:
                if url in self._visited:
                    continue
                if cap is not None and len(docs) >= cap:
                    break
                next_level.append((url, depth))
            if not next_level:
                break
            # Mark all as visited up-front so concurrent tasks don't
            # re-queue the same URL when we discover shared children.
            for url, _ in next_level:
                self._visited.add(url)

            # Fetch the entire level concurrently
            tasks = [self._fetch_one(url, depth) for url, depth in next_level]
            results = await asyncio.gather(*tasks)

            # Build the next queue with two layers of dedup:
            # 1. ``seen_next`` catches the case where two parents
            #    at the same level link to the same child.
            # 2. ``self._visited`` catches the case where a child
            #    was already fetched in a previous run (crawler
            #    state preserved across crawl() calls).
            seen_next: set[str] = set()
            next_queue: List[tuple[str, int]] = []
            for (url, depth), result in zip(next_level, results):
                fetch_attempts += 1
                if result is None:
                    fetch_failures += 1
                    continue
                html, new_links = result
                text = _extract_text(html)
                if cap is None or len(docs) < cap:
                    docs.append(CrawledDoc(url=url, text=text, depth=depth))
                if depth < self.max_depth:
                    for child in new_links:
                        if (
                            child not in self._visited
                            and child not in seen_next
                        ):
                            seen_next.add(child)
                            next_queue.append((child, depth + 1))
            queue = next_queue

        return CrawlStats(
            docs=docs,
            fetch_attempts=fetch_attempts,
            fetch_failures=fetch_failures,
            urls_visited=len(self._visited),
        )

    async def _fetch_one(
        self, url: str, depth: int
    ) -> Optional[tuple[str, List[str]]]:
        """Fetch ``url`` (with semaphore + delay), parse text + links."""
        async with self._semaphore:
            if self.request_delay > 0.0:
                async with self._delay_lock:
                    now = asyncio.get_event_loop().time()
                    wait = self.request_delay - (now - self._last_fetch_at)
                    if wait > 0:
                        await asyncio.sleep(wait)
                    self._last_fetch_at = asyncio.get_event_loop().time()
            try:
                html = await self.fetcher.fetch(url)
            except Exception:
                # The fetcher should ideally return None on error;
                # but a buggy implementation might raise. We treat
                # any exception as a fetch failure rather than
                # crashing the whole crawl.
                return None
        if html is None:
            return None
        links = extract_links(html, base=url)
        return html, links
