"""Tests for core/web_crawler.py — stdlib-only async recursive crawler.

RUFUS ``core/crawler.py::Crawler._crawl`` is a recursive async
crawler that:

  - caps depth via ``max_depth``,
  - dedupes via a ``url_tracker`` set,
  - throttles concurrent fetches via ``asyncio.Semaphore``,
  - extracts text from HTML (we reuse :mod:`gemas_core.core.html_text`),
  - discovers new links (we use a stdlib regex; bs4 is out).

The RUFUS implementation uses ``aiohttp`` for the actual HTTP
calls. gemas_core stays stdlib-only, so we use a ``Fetcher``
protocol — callers inject their own transport (aiohttp, httpx,
urllib3, or a mock in tests). The crawler itself is the algorithm.
"""
from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

import pytest

from gemas_core.core.web_crawler import (
    CrawledDoc,
    CrawlStats,
    RecursiveCrawler,
    extract_links,
)


# A deterministic, programmable fetcher for tests. Each URL is
# mapped to either a body string or ``None`` to simulate a fetch
# failure. The fetcher also records every URL it was asked for.
class _FakeFetcher:
    def __init__(self, pages: Dict[str, Optional[str]]) -> None:
        self._pages = pages
        self.calls: List[str] = []
        # Simulate a tiny bit of async work
        self._delay = 0.0

    async def fetch(self, url: str) -> Optional[str]:
        self.calls.append(url)
        if self._delay:
            await asyncio.sleep(self._delay)
        return self._pages.get(url)


def _crawler(pages: dict, **kwargs) -> RecursiveCrawler:
    fetcher = _FakeFetcher(pages)
    crawler = RecursiveCrawler(fetcher, **kwargs)
    # Attach for test introspection
    crawler._test_fetcher = fetcher  # type: ignore[attr-defined]
    return crawler


class TestExtractLinks:
    def test_finds_anchors(self):
        html = '<a href="/x">x</a><a href="/y">y</a>'
        links = extract_links(html, base="https://example.com/dir/")
        assert links == ["https://example.com/x", "https://example.com/y"]

    def test_deduplicates_within_page(self):
        html = '<a href="/x">1</a><a href="/x">2</a><a href="/y">3</a>'
        links = extract_links(html, base="https://example.com/dir/")
        assert links == ["https://example.com/x", "https://example.com/y"]

    def test_absolute_passthrough(self):
        html = '<a href="https://other.com/x">x</a>'
        links = extract_links(html, base="https://example.com/dir/")
        assert links == ["https://other.com/x"]

    def test_protocol_relative_uses_base_scheme(self):
        html = '<a href="//cdn.example.com/x.js">x</a>'
        links = extract_links(html, base="https://example.com/dir/")
        assert links == ["https://cdn.example.com/x.js"]

    def test_anchors_only_skipped(self):
        # Pure-fragment links don't go anywhere new; we skip them.
        html = '<a href="#section">go</a><a href="/x">x</a>'
        links = extract_links(html, base="https://example.com/dir/")
        assert links == ["https://example.com/x"]

    def test_javascript_href_skipped(self):
        html = '<a href="javascript:alert(1)">x</a><a href="/y">y</a>'
        links = extract_links(html, base="https://example.com/dir/")
        assert links == ["https://example.com/y"]

    def test_mailto_skipped(self):
        html = '<a href="mailto:a@b.c">m</a><a href="/y">y</a>'
        links = extract_links(html, base="https://example.com/")
        assert links == ["https://example.com/y"]

    def test_empty_href_skipped(self):
        html = '<a href="">x</a><a href="/y">y</a>'
        links = extract_links(html, base="https://example.com/")
        assert links == ["https://example.com/y"]

    def test_no_href_attr_skipped(self):
        html = '<a>no href</a><a href="/y">y</a>'
        links = extract_links(html, base="https://example.com/")
        assert links == ["https://example.com/y"]

    def test_no_base_returns_absolute_only(self):
        html = '<a href="/x">x</a><a href="https://other.com/y">y</a>'
        links = extract_links(html, base="")
        # /x has no base to resolve against → dropped
        # https://other.com/y → kept
        assert links == ["https://other.com/y"]

    def test_preserves_order(self):
        html = '<a href="/c">c</a><a href="/a">a</a><a href="/b">b</a>'
        links = extract_links(html, base="https://example.com/")
        assert links == [
            "https://example.com/c",
            "https://example.com/a",
            "https://example.com/b",
        ]

    def test_handles_malformed_html(self):
        html = '<a href="/x">x</a><a href="/y" unclosed'
        links = extract_links(html, base="https://example.com/")
        # The regex finds the href even if the tag isn't closed
        assert "https://example.com/x" in links
        assert "https://example.com/y" in links


class TestRecursiveCrawler:
    @pytest.mark.asyncio
    async def test_crawl_single_page(self):
        pages = {
            "https://example.com/": "<html><body>Hello</body></html>",
        }
        crawler = _crawler(pages, max_depth=0)
        docs = await crawler.crawl(["https://example.com/"])
        assert len(docs) == 1
        assert docs[0].url == "https://example.com/"
        assert "Hello" in docs[0].text
        assert docs[0].depth == 0

    @pytest.mark.asyncio
    async def test_crawl_follows_links_to_depth(self):
        pages = {
            "https://example.com/": (
                '<html><body>root</body>'
                '<a href="/a">a</a></html>'
            ),
            "https://example.com/a": (
                '<html><body>page a</body>'
                '<a href="/b">b</a></html>'
            ),
            "https://example.com/b": (
                '<html><body>page b</body></html>'
            ),
        }
        crawler = _crawler(pages, max_depth=2)
        docs = await crawler.crawl(["https://example.com/"])
        urls = [d.url for d in docs]
        assert "https://example.com/" in urls
        assert "https://example.com/a" in urls
        assert "https://example.com/b" in urls
        depths = {d.url: d.depth for d in docs}
        assert depths["https://example.com/"] == 0
        assert depths["https://example.com/a"] == 1
        assert depths["https://example.com/b"] == 2

    @pytest.mark.asyncio
    async def test_depth_limit_stops_recursion(self):
        pages = {
            "https://example.com/": '<a href="/a">a</a>',
            "https://example.com/a": '<a href="/b">b</a>',
            "https://example.com/b": '<a href="/c">c</a>',
            "https://example.com/c": 'final',
        }
        # max_depth=1 → / and /a only, not /b or /c
        crawler = _crawler(pages, max_depth=1)
        docs = await crawler.crawl(["https://example.com/"])
        urls = {d.url for d in docs}
        assert "https://example.com/" in urls
        assert "https://example.com/a" in urls
        assert "https://example.com/b" not in urls
        assert "https://example.com/c" not in urls

    @pytest.mark.asyncio
    async def test_dedupes_across_multiple_starts(self):
        # Two starting URLs share a common child. The child should
        # be crawled once, not twice.
        pages = {
            "https://example.com/": '<a href="/shared">s</a>',
            "https://example.com/other": '<a href="/shared">s</a>',
            "https://example.com/shared": 'shared content',
        }
        crawler = _crawler(pages, max_depth=2)
        docs = await crawler.crawl([
            "https://example.com/",
            "https://example.com/other",
        ])
        shared_docs = [d for d in docs if d.url == "https://example.com/shared"]
        assert len(shared_docs) == 1
        # Fetcher should have been called for the shared URL once
        fetcher: _FakeFetcher = crawler._test_fetcher  # type: ignore[attr-defined]
        assert fetcher.calls.count("https://example.com/shared") == 1

    @pytest.mark.asyncio
    async def test_fetch_failure_does_not_crash(self):
        # /missing → fetcher returns None (simulates 404 / 500)
        pages = {
            "https://example.com/": '<a href="/missing">m</a><a href="/real">r</a>',
            "https://example.com/real": 'real content',
        }
        crawler = _crawler(pages, max_depth=1)
        docs = await crawler.crawl(["https://example.com/"])
        urls = {d.url for d in docs}
        assert "https://example.com/real" in urls
        assert "https://example.com/missing" not in urls

    @pytest.mark.asyncio
    async def test_max_pages_truncates(self):
        # 3 start URLs, max_pages=2 → only 2 crawled
        pages = {
            f"https://example.com/{i}": f"page {i}" for i in range(3)
        }
        crawler = _crawler(pages, max_depth=0, max_pages=2)
        docs = await crawler.crawl([
            "https://example.com/0",
            "https://example.com/1",
            "https://example.com/2",
        ])
        assert len(docs) == 2

    @pytest.mark.asyncio
    async def test_empty_starts_returns_empty(self):
        pages: dict = {}
        crawler = _crawler(pages)
        docs = await crawler.crawl([])
        assert docs == []

    @pytest.mark.asyncio
    async def test_invalid_start_url_dropped(self):
        # A non-HTTP URL in the start list is silently dropped
        pages = {"https://example.com/": "ok"}
        crawler = _crawler(pages)
        docs = await crawler.crawl([
            "not a url",
            "javascript:alert(1)",
            "https://example.com/",
        ])
        urls = [d.url for d in docs]
        assert urls == ["https://example.com/"]

    @pytest.mark.asyncio
    async def test_max_concurrent_respected(self):
        # The crawler should never have more than max_concurrent
        # outstanding fetches at any point. We start with 5 URLs
        # at depth 0 so they're all in flight concurrently, and
        # verify the semaphore caps the in-flight count.
        in_flight = 0
        max_in_flight = 0
        lock = asyncio.Lock()

        class SlowFetcher:
            async def fetch(self, url: str) -> str:
                nonlocal in_flight, max_in_flight
                async with lock:
                    in_flight += 1
                    if in_flight > max_in_flight:
                        max_in_flight = in_flight
                await asyncio.sleep(0.01)
                async with lock:
                    in_flight -= 1
                return f"body of {url}"

        # 5 starts at depth 0, max_concurrent=3 → max 3 in flight
        starts = [f"https://example.com/{i}" for i in range(5)]
        pages = {u: f"p{i}" for i, u in enumerate(starts)}
        crawler = RecursiveCrawler(SlowFetcher(), max_depth=0, max_concurrent=3)
        await crawler.crawl(starts)
        # Cap is respected
        assert max_in_flight <= 3
        # Sanity: more than 1 actually in flight at some point
        assert max_in_flight >= 2

    @pytest.mark.asyncio
    async def test_text_extraction_applied(self):
        pages = {
            "https://example.com/": (
                "<html><body>"
                "<script>alert('x')</script>"
                "<p>visible</p>"
                "<style>body{color:red}</style>"
                "</body></html>"
            ),
        }
        crawler = _crawler(pages, max_depth=0)
        docs = await crawler.crawl(["https://example.com/"])
        assert len(docs) == 1
        assert "visible" in docs[0].text
        assert "alert" not in docs[0].text
        assert "color:red" not in docs[0].text

    @pytest.mark.asyncio
    async def test_dedup_set_preserved_across_calls(self):
        # After the first crawl, the dedup set should contain all
        # visited URLs. A second call with the same start URL
        # should NOT re-fetch.
        pages = {
            "https://example.com/": "hello",
        }
        crawler = _crawler(pages, max_depth=0)
        await crawler.crawl(["https://example.com/"])
        # Second crawl on the same URL
        await crawler.crawl(["https://example.com/"])
        # Should have only fetched it once
        fetcher: _FakeFetcher = crawler._test_fetcher  # type: ignore[attr-defined]
        assert fetcher.calls.count("https://example.com/") == 1

    @pytest.mark.asyncio
    async def test_dedup_set_resettable(self):
        pages = {"https://example.com/": "hello"}
        crawler = _crawler(pages, max_depth=0)
        await crawler.crawl(["https://example.com/"])
        crawler.reset()
        await crawler.crawl(["https://example.com/"])
        fetcher: _FakeFetcher = crawler._test_fetcher  # type: ignore[attr-defined]
        assert fetcher.calls.count("https://example.com/") == 2

    @pytest.mark.asyncio
    async def test_returned_docs_include_depth(self):
        pages = {
            "https://example.com/": '<a href="/a">a</a>',
            "https://example.com/a": 'leaf',
        }
        crawler = _crawler(pages, max_depth=2)
        docs = await crawler.crawl(["https://example.com/"])
        by_url = {d.url: d for d in docs}
        assert by_url["https://example.com/"].depth == 0
        assert by_url["https://example.com/a"].depth == 1

    @pytest.mark.asyncio
    async def test_crawled_doc_is_namedtuple(self):
        doc = CrawledDoc(url="u", text="t", depth=0)
        assert doc.url == "u"
        assert doc.text == "t"
        assert doc.depth == 0
        # Tuple-like access works
        u, t, d = doc
        assert (u, t, d) == ("u", "t", 0)

    @pytest.mark.asyncio
    async def test_stats_captured(self):
        pages = {
            "https://example.com/": '<a href="/a">a</a><a href="/missing">m</a>',
            "https://example.com/a": 'page a',
        }
        crawler = _crawler(pages, max_depth=2)
        stats = await crawler.crawl_with_stats(["https://example.com/"])
        assert isinstance(stats, CrawlStats)
        assert stats.docs is not None
        # We got 2 docs: / and /a. /missing was a fetch failure.
        assert len(stats.docs) == 2
        # 3 fetch attempts (start, /a, /missing), 1 failure.
        assert stats.fetch_attempts == 3
        assert stats.fetch_failures == 1
        # 3 URLs were *attempted* (the failed one is still counted
        # in ``_visited`` because we mark up-front to prevent
        # retries). Docs returned is 2 (excluding the failure).
        assert stats.urls_visited == 3

    @pytest.mark.asyncio
    async def test_max_depth_zero_means_only_starts(self):
        # With max_depth=0, we crawl the start URLs but don't
        # follow any links.
        pages = {
            "https://example.com/": '<a href="/a">a</a>',
            "https://example.com/a": "leaf",
        }
        crawler = _crawler(pages, max_depth=0)
        docs = await crawler.crawl(["https://example.com/"])
        urls = {d.url for d in docs}
        assert "https://example.com/" in urls
        assert "https://example.com/a" not in urls

    @pytest.mark.asyncio
    async def test_cycle_does_not_loop(self):
        # /a links back to /. With dedup, we should fetch each
        # exactly once and not infinite-loop.
        pages = {
            "https://example.com/": '<a href="/a">a</a>',
            "https://example.com/a": '<a href="/">home</a>',
        }
        crawler = _crawler(pages, max_depth=5)
        docs = await crawler.crawl(["https://example.com/"])
        # Should complete in finite time and produce 2 docs
        assert len(docs) == 2
        fetcher: _FakeFetcher = crawler._test_fetcher  # type: ignore[attr-defined]
        assert len(fetcher.calls) == 2

    @pytest.mark.asyncio
    async def test_concurrent_crawl_uses_asyncio_gather(self):
        # Sanity: verify that BFS-level parallelism actually
        # parallelises. With a slow fetcher and 3 starts at depth 0,
        # all three should be in flight at once.
        in_flight = 0
        max_in_flight = 0
        lock = asyncio.Lock()

        class SlowFetcher:
            async def fetch(self, url: str) -> str:
                nonlocal in_flight, max_in_flight
                async with lock:
                    in_flight += 1
                    if in_flight > max_in_flight:
                        max_in_flight = in_flight
                await asyncio.sleep(0.02)
                async with lock:
                    in_flight -= 1
                return f"body of {url}"

        fetcher = SlowFetcher()
        crawler = RecursiveCrawler(
            fetcher,
            max_depth=0,
            max_concurrent=10,
        )
        await crawler.crawl([
            "https://example.com/0",
            "https://example.com/1",
            "https://example.com/2",
        ])
        assert max_in_flight == 3  # all three in flight at once

    @pytest.mark.asyncio
    async def test_request_delay_throttles(self):
        # With request_delay=0.05 and 3 sequential starts, total
        # elapsed time should be >= 0.10.
        import time

        class DelayFetcher:
            async def fetch(self, url: str) -> str:
                return f"body of {url}"

        fetcher = DelayFetcher()
        crawler = RecursiveCrawler(
            fetcher,
            max_depth=0,
            max_concurrent=10,
            request_delay=0.05,
        )
        start = time.monotonic()
        await crawler.crawl([
            "https://example.com/0",
            "https://example.com/1",
            "https://example.com/2",
        ])
        elapsed = time.monotonic() - start
        # request_delay is the *minimum* gap between consecutive
        # fetches. With 3 fetches and 0.05s delay, we expect
        # at least 0.10s (between the 1st and 3rd).
        assert elapsed >= 0.08  # slight wiggle for Windows clock

    def test_invalid_max_depth_raises(self):
        with pytest.raises(ValueError):
            RecursiveCrawler(_FakeFetcher({}), max_depth=-1)

    def test_invalid_max_pages_raises(self):
        with pytest.raises(ValueError):
            RecursiveCrawler(_FakeFetcher({}), max_pages=0)

    def test_invalid_max_concurrent_raises(self):
        with pytest.raises(ValueError):
            RecursiveCrawler(_FakeFetcher({}), max_concurrent=0)

    def test_invalid_request_delay_raises(self):
        with pytest.raises(ValueError):
            RecursiveCrawler(_FakeFetcher({}), request_delay=-0.1)

    def test_fetcher_protocol_accepts_arbitrary_object(self):
        # Anything with a ``fetch`` method is a valid Fetcher.
        class HasFetch:
            async def fetch(self, url: str) -> str:
                return ""

        crawler = RecursiveCrawler(HasFetch())
        assert crawler.fetcher is not None
