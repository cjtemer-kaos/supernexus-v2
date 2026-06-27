"""Tests for workers/web_research.py — GemaBase wrapper around
the v1.5.0 web-research primitives.

The gem exposes ``execute(query, start_urls, ...)`` (inherited
from GemaBase) that:
  1. Validates the start URLs (drops invalid ones)
  2. Crawls with the injected Fetcher (default aiohttp)
  3. Ranks pages against the query (KeywordScorer by default,
     or injected Embedder if provided)
  4. Returns a WebResearchResult with docs + ranked

Tests use a MockFetcher (no real HTTP). Integration tests with
a real aiohttp test server live in the v1.5.0 smoke at
``temp/opencode/smoke_v150_rufus.py``.
"""
from __future__ import annotations

from typing import List, Optional

import pytest

from gemas_core import (
    CrawledDoc,
    ScoredItem,
)
from gemas_core.workers.web_research import (
    WebResearchGem,
    WebResearchResult,
    web_research,
)


class _MockFetcher:
    """Deterministic fetcher for tests."""

    def __init__(self, pages: dict) -> None:
        self._pages = pages
        self.calls: List[str] = []

    async def fetch(self, url: str) -> Optional[str]:
        self.calls.append(url)
        return self._pages.get(url)


# --- Manifest -----------------------------------------------------------------


class TestWebResearchGemManifest:
    def test_inherits_gema_base(self):
        from gemas_core.base import GemaBase
        assert issubclass(WebResearchGem, GemaBase)

    def test_class_name(self):
        # The builder looks up class via _class_name(gema_id) ==
        # "<id>.capitalize() + Gem" → "WebResearchGem"
        assert WebResearchGem.__name__ == "WebResearchGem"

    def test_id(self):
        gem = WebResearchGem()
        assert gem.name == "web_research"

    def test_description_nonempty(self):
        gem = WebResearchGem()
        assert isinstance(gem.description, str)
        assert len(gem.description) > 0

    def test_category(self):
        gem = WebResearchGem()
        # Research / web / knowledge / tool
        assert gem.category in (
            "research", "web", "knowledge", "tool", "rag"
        )

    def test_to_dict(self):
        gem = WebResearchGem()
        d = gem.to_dict()
        assert d["id"] == "web_research"
        assert d["name"]
        assert d["description"]
        assert d["category"]
        assert d["type"] == "dedicated"

    def test_appears_in_dedicated_ids(self):
        from gemas_core.builders import list_standard_dedicated_ids
        assert "web_research" in list_standard_dedicated_ids()


def _empty_gemas_dir():
    """Empty dir for the role-LLM loader; the dedicated web_research
    doesn't read any manifest file."""
    import tempfile
    from pathlib import Path
    return Path(tempfile.mkdtemp())


def test_registered_in_standard_gemas():
    from gemas_core.builders import build_standard_gemas
    gemas = build_standard_gemas(gemas_dir=_empty_gemas_dir())
    assert "web_research" in gemas


# --- Execute ------------------------------------------------------------------


class TestWebResearchExecute:
    @pytest.mark.asyncio
    async def test_execute_returns_web_research_result(self):
        gem = WebResearchGem()
        gem.bind_fetcher(_MockFetcher({
            "https://example.com/": "<p>hello world</p>",
        }))
        # WebResearchGem has a real execute(task, context) signature
        # from GemaBase. We call a higher-level method instead.
        result = await gem.research(
            query="hello",
            start_urls=["https://example.com/"],
        )
        assert isinstance(result, WebResearchResult)

    @pytest.mark.asyncio
    async def test_research_returns_docs(self):
        gem = WebResearchGem()
        gem.bind_fetcher(_MockFetcher({
            "https://example.com/": "<p>hello world</p>",
        }))
        result = await gem.research(
            query="hello",
            start_urls=["https://example.com/"],
        )
        assert len(result.docs) == 1
        assert result.docs[0].url == "https://example.com/"

    @pytest.mark.asyncio
    async def test_research_returns_ranked_results(self):
        gem = WebResearchGem()
        gem.bind_fetcher(_MockFetcher({
            "https://a.com/": "<p>python ai tutorial</p>",
            "https://b.com/": "<p>cooking recipes</p>",
        }))
        result = await gem.research(
            query="python ai",
            start_urls=["https://a.com/", "https://b.com/"],
        )
        assert len(result.ranked) == 2
        assert "python" in result.ranked[0].text.lower()
        assert "cooking" in result.ranked[-1].text.lower()

    @pytest.mark.asyncio
    async def test_research_drops_invalid_start_urls(self):
        gem = WebResearchGem()
        fetcher = _MockFetcher({})
        gem.bind_fetcher(fetcher)
        result = await gem.research(
            query="x",
            start_urls=[
                "not a url",
                "javascript:alert(1)",
                "https://valid.com/",
            ],
        )
        # Only the valid URL was passed to the fetcher
        assert fetcher.calls == ["https://valid.com/"]
        assert result.skipped_urls == 2
        assert "not a url" in result.invalid_start_urls
        assert "javascript:alert(1)" in result.invalid_start_urls

    @pytest.mark.asyncio
    async def test_research_respects_top_k(self):
        gem = WebResearchGem()
        gem.bind_fetcher(_MockFetcher({
            f"https://x.com/{i}": f"<p>page {i}</p>" for i in range(5)
        }))
        result = await gem.research(
            query="x",
            start_urls=[f"https://x.com/{i}" for i in range(5)],
            top_k=2,
        )
        assert len(result.ranked) == 2

    @pytest.mark.asyncio
    async def test_research_respects_max_depth(self):
        gem = WebResearchGem()
        gem.bind_fetcher(_MockFetcher({
            "https://x.com/": '<a href="/a">a</a>',
            "https://x.com/a": '<a href="/b">b</a>',
            "https://x.com/b": "leaf",
        }))
        result = await gem.research(
            query="x",
            start_urls=["https://x.com/"],
            max_depth=1,
        )
        urls = {d.url for d in result.docs}
        assert "https://x.com/" in urls
        assert "https://x.com/a" in urls
        assert "https://x.com/b" not in urls

    @pytest.mark.asyncio
    async def test_research_uses_embedder_when_bound(self):
        gem = WebResearchGem()
        gem.bind_fetcher(_MockFetcher({
            "https://a.com/": "<p>rust web</p>",
            "https://b.com/": "<p>python ai</p>",
        }))

        class Embedder:
            calls: List = []

            def embed(self, texts: List[str]) -> List[List[float]]:
                self.calls.append(list(texts))
                return [
                    [float(t.lower().count("python"))] for t in texts
                ]

        emb = Embedder()
        gem.bind_embedder(emb)
        result = await gem.research(
            query="python",
            start_urls=["https://a.com/", "https://b.com/"],
        )
        assert len(emb.calls) >= 1
        # The python page wins
        assert "python" in result.ranked[0].text.lower()

    @pytest.mark.asyncio
    async def test_research_records_fetch_failures(self):
        gem = WebResearchGem()
        gem.bind_fetcher(_MockFetcher({
            "https://x.com/": "ok",
            "https://missing.com/": None,  # fetcher returns None
        }))
        result = await gem.research(
            query="x",
            start_urls=["https://x.com/", "https://missing.com/"],
        )
        assert result.fetch_attempts == 2
        assert result.fetch_failures == 1
        assert len(result.docs) == 1
        assert result.docs[0].url == "https://x.com/"

    @pytest.mark.asyncio
    async def test_research_invalid_urls_in_result(self):
        gem = WebResearchGem()
        gem.bind_fetcher(_MockFetcher({}))
        result = await gem.research(
            query="x",
            start_urls=["a", "b", "https://valid.com/"],
        )
        assert result.skipped_urls == 2
        assert "a" in result.invalid_start_urls
        assert "b" in result.invalid_start_urls
        assert "https://valid.com/" not in result.invalid_start_urls

    @pytest.mark.asyncio
    async def test_research_without_fetcher_raises(self, monkeypatch):
        """Without a bound fetcher and without aiohttp, research() must
        raise a clear error (RuntimeError wrapping ImportError, or
        TypeError if aiohttp is replaced with None).

        Skipped if aiohttp is not available at all in the test env
        (the lazy import would naturally raise).
        """
        pytest.importorskip("aiohttp")
        # Pretend aiohttp is not installed by replacing the module
        import sys
        monkeypatch.setitem(sys.modules, "aiohttp", None)
        gem = WebResearchGem()
        with pytest.raises((RuntimeError, TypeError), match="."):
            await gem.research(query="x", start_urls=["https://a.com/"])

    @pytest.mark.asyncio
    async def test_research_empty_start_urls(self):
        gem = WebResearchGem()
        gem.bind_fetcher(_MockFetcher({}))
        result = await gem.research(query="x", start_urls=[])
        assert result.docs == []
        assert result.ranked == []
        assert result.skipped_urls == 0

    @pytest.mark.asyncio
    async def test_execute_dispatches_to_research(self):
        # The base execute(task, context) should call research()
        # for compatibility with dispatch_gema.
        gem = WebResearchGem()
        gem.bind_fetcher(_MockFetcher({
            "https://a.com/": "<p>hello</p>",
        }))
        result = await gem.execute(
            task="hello",
            context='{"start_urls": ["https://a.com/"]}',
        )
        assert result["success"] is True
        assert result["gema"] == "web_research"
        assert "result" in result

    @pytest.mark.asyncio
    async def test_execute_parses_context_json(self):
        gem = WebResearchGem()
        gem.bind_fetcher(_MockFetcher({
            "https://a.com/": "<p>hello</p>",
        }))
        result = await gem.execute(
            task="hello",
            context='{"start_urls": ["https://a.com/"], "top_k": 1}',
        )
        # top_k=1 means only 1 result in ranked
        assert len(result["result"].ranked) == 1

    @pytest.mark.asyncio
    async def test_execute_handles_bad_context_json(self):
        gem = WebResearchGem()
        gem.bind_fetcher(_MockFetcher({}))
        result = await gem.execute(task="x", context="not json")
        # Should fall back to defaults (empty start_urls → empty result)
        assert result["success"] is True  # success=True because no error
        assert result["result"].docs == []


# --- Result dataclass ---------------------------------------------------------


class TestWebResearchResult:
    def test_construction(self):
        r = WebResearchResult(
            docs=[],
            ranked=[],
            fetch_attempts=0,
            fetch_failures=0,
            skipped_urls=0,
            invalid_start_urls=[],
        )
        assert r.docs == []
        assert r.ranked == []
        assert r.fetch_attempts == 0

    def test_to_dict(self):
        r = WebResearchResult(
            docs=[CrawledDoc(url="u", text="t", depth=0)],
            ranked=[ScoredItem(text="t", score=1.0)],
            fetch_attempts=1,
            fetch_failures=0,
            skipped_urls=0,
            invalid_start_urls=[],
        )
        d = r.to_dict()
        assert d["docs"][0]["url"] == "u"
        assert d["ranked"][0]["text"] == "t"
        assert d["ranked"][0]["score"] == 1.0
        assert d["fetch_attempts"] == 1

    def test_to_dict_includes_invalid_urls(self):
        r = WebResearchResult(
            docs=[],
            ranked=[],
            fetch_attempts=0,
            fetch_failures=0,
            skipped_urls=1,
            invalid_start_urls=["bad"],
        )
        d = r.to_dict()
        assert d["invalid_start_urls"] == ["bad"]
        assert d["skipped_urls"] == 1


# --- Convenience function -----------------------------------------------------


class TestConvenienceFunction:
    @pytest.mark.asyncio
    async def test_web_research_function_basic(self):
        fetcher = _MockFetcher({
            "https://a.com/": "<p>hello world</p>",
        })
        result = await web_research(
            query="hello",
            start_urls=["https://a.com/"],
            fetcher=fetcher,
        )
        assert isinstance(result, WebResearchResult)
        assert len(result.docs) == 1

    @pytest.mark.asyncio
    async def test_web_research_function_passes_kwargs(self):
        fetcher = _MockFetcher({
            "https://a.com/": '<a href="https://a.com/1">one</a><a href="https://a.com/2">two</a>',
            "https://a.com/1": '<a href="https://a.com/2">two</a>',
            "https://a.com/2": "no links here",
        })
        result = await web_research(
            query="x",
            start_urls=["https://a.com/"],
            fetcher=fetcher,
            max_depth=2,
            top_k=2,
        )
        # / at depth 0, /1 at 1, /2 at 2 → 3 docs
        assert len(result.docs) == 3
        # top_k=2 → 2 ranked
        assert len(result.ranked) == 2
