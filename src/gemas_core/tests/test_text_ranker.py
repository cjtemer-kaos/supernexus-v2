"""Tests for core/text_ranker.py — stdlib-only content ranker.

RUFUS ``content_rankers/method.py::rank_content`` uses PyTorch /
numpy over Google embeddings, with cosine or euclidean similarity.
We can't depend on torch or numpy in gemas_core. Instead we ship:

  1. ``KeywordScorer`` — TF-IDF-ish, stdlib only. Falls back when
     no embedder is provided. Stable, deterministic, no network.
  2. ``rank_content`` — public function that picks a scoring
     backend based on whether an ``Embedder`` is provided. Returns
     a list of ``(text, score)`` tuples sorted descending.

The tests verify both backends share the same surface (return type,
sort order, length) so callers can swap freely.
"""
from __future__ import annotations

import math
from typing import List

import pytest

from gemas_core.core.text_ranker import (
    KeywordScorer,
    cosine_similarity_vectors,
    euclidean_similarity_vectors,
    rank_content,
    tokenize,
    ScoredItem,
)


# A tiny test embedder that just maps text to a 4-dim bag-of-words
# vector. Deterministic, fast, and lets us verify the dispatch
# path (embedder provided → use it) without any real model.
class _ToyEmbedder:
    """4-dim bag-of-words: counts of 'rust', 'python', 'ai', 'web'."""

    def __init__(self) -> None:
        self.calls: List[List[str]] = []

    def embed(self, texts: List[str]) -> List[List[float]]:
        self.calls.append(list(texts))
        out: List[List[float]] = []
        for t in texts:
            t = t.lower()
            out.append([
                float(t.count("rust")),
                float(t.count("python")),
                float(t.count("ai")),
                float(t.count("web")),
            ])
        return out


class TestTokenize:
    def test_simple_split(self):
        assert tokenize("hello world") == ["hello", "world"]

    def test_lowercases(self):
        assert tokenize("Hello WORLD") == ["hello", "world"]

    def test_strips_punctuation(self):
        assert tokenize("hello, world!") == ["hello", "world"]

    def test_drops_short_tokens(self):
        # "a" and "is" are 1-2 chars; we drop them as stopwords-like
        assert tokenize("a cat is on a mat") == ["cat", "mat"]

    def test_handles_unicode(self):
        # Non-ASCII alphanumerics survive
        assert tokenize("Héctor こんにちは") == ["héctor", "こんにちは"]

    def test_drops_pure_punctuation(self):
        assert tokenize("...!!! ???") == []

    def test_collapses_internal_whitespace(self):
        assert tokenize("foo   bar\t\tbaz") == ["foo", "bar", "baz"]

    def test_handles_empty(self):
        assert tokenize("") == []

    def test_keeps_hyphenated_words_together(self):
        # "state-of-the-art" is one token
        assert tokenize("state-of-the-art") == ["state-of-the-art"]


class TestKeywordScorer:
    def test_empty_ref_returns_zero_scores(self):
        scorer = KeywordScorer()
        # Whitespace-only ref tokenises to empty
        scores = scorer.score(ref="   ", candidates=["hello world"])
        assert scores == [0.0]

    def test_no_overlap_yields_zero(self):
        scorer = KeywordScorer()
        scores = scorer.score(
            ref="python ai", candidates=["web browser html css"],
        )
        assert scores == [0.0]

    def test_exact_match_yields_high_score(self):
        scorer = KeywordScorer()
        scores = scorer.score(
            ref="python ai",
            candidates=["python ai tutorial for beginners"],
        )
        # Score should be > 0 and reflect the overlap
        assert scores[0] > 0

    def test_idf_weighting(self):
        # If "rust" appears in *every* candidate, it should be weighted
        # less than a word that appears in only one.
        scorer = KeywordScorer()
        scores = scorer.score(
            ref="rust python",
            candidates=[
                "rust python ai tutorial",  # both
                "rust web dev guide",       # only "rust"
                "python ai intro",          # only "python"
                "cooking recipes",          # neither
            ],
        )
        # Document 0 has both → highest score
        # Documents 1 and 2 should be > 0 and 3 = 0
        assert scores[0] > scores[1] > 0
        assert scores[0] > scores[2] > 0
        assert scores[3] == 0.0

    def test_handles_unicode_ref(self):
        scorer = KeywordScorer()
        scores = scorer.score(
            ref="héctor",
            candidates=["héctor el crack", "no name here"],
        )
        # First candidate has the ref term → positive score
        assert scores[0] > 0
        # Second candidate doesn't → zero
        assert scores[1] == 0.0

    def test_idf_ln_smoothed(self):
        # Standard "smoothed" IDF: ln((N+1)/(df+1)) + 1
        # We verify it never returns 0 or negative weights.
        scorer = KeywordScorer()
        scores = scorer.score(
            ref="common",
            candidates=["common term", "common stuff", "common other"],
        )
        # "common" appears in all 3 → still positive score, just
        # weighted lower than rare terms.
        for s in scores:
            assert s >= 0.0
            assert math.isfinite(s)


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 0.0, 0.0]
        sim = cosine_similarity_vectors([v], [v])[0]
        assert math.isclose(sim, 1.0, abs_tol=1e-9)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        sim = cosine_similarity_vectors([a], [b])[0]
        assert math.isclose(sim, 0.0, abs_tol=1e-9)

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        sim = cosine_similarity_vectors([a], [b])[0]
        assert math.isclose(sim, -1.0, abs_tol=1e-9)

    def test_zero_vector_returns_zero(self):
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        sim = cosine_similarity_vectors([a], [b])[0]
        # Convention: zero vector has no direction, so 0.0
        assert sim == 0.0

    def test_pairwise_against_single_ref(self):
        # ref has shape (1, d), candidates have shape (n, d)
        ref = [[1.0, 0.0]]
        cands = [[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]]
        sims = cosine_similarity_vectors(ref, cands)
        assert len(sims) == 3
        assert math.isclose(sims[0], 1.0, abs_tol=1e-9)
        assert math.isclose(sims[1], 0.0, abs_tol=1e-9)
        assert math.isclose(sims[2], -1.0, abs_tol=1e-9)

    def test_mismatched_dimensions_raises(self):
        with pytest.raises(ValueError):
            cosine_similarity_vectors([[1.0, 0.0]], [[1.0, 0.0, 0.0]])

    def test_empty_lists_return_empty(self):
        assert cosine_similarity_vectors([], []) == []


class TestEuclideanSimilarity:
    def test_identical_returns_one(self):
        v = [1.0, 2.0, 3.0]
        sim = euclidean_similarity_vectors([v], [v])[0]
        # RUFUS uses 1 / (1 + distance); distance = 0 → 1.0
        assert math.isclose(sim, 1.0, abs_tol=1e-9)

    def test_far_apart_smaller(self):
        a = [0.0, 0.0]
        b = [10.0, 0.0]
        sim = euclidean_similarity_vectors([a], [b])[0]
        # distance = 10, similarity = 1/11
        assert math.isclose(sim, 1.0 / 11.0, abs_tol=1e-9)

    def test_pairwise(self):
        ref = [[0.0, 0.0]]
        cands = [[0.0, 0.0], [1.0, 0.0], [10.0, 0.0]]
        sims = euclidean_similarity_vectors(ref, cands)
        assert sims[0] > sims[1] > sims[2] > 0


class TestRankContent:
    def test_returns_scored_items(self):
        results = rank_content(
            ref="python ai",
            candidates=["python ai tutorial", "web browser", "python intro"],
        )
        assert all(isinstance(r, ScoredItem) for r in results)
        assert len(results) == 3

    def test_results_sorted_descending(self):
        results = rank_content(
            ref="python ai",
            candidates=["web browser", "python ai tutorial", "cooking recipes"],
        )
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_no_embedder_uses_keyword_scorer(self):
        # Without an embedder, scoring is purely lexical.
        results = rank_content(
            ref="python ai",
            candidates=[
                "python ai for beginners",   # high overlap
                "cooking recipes",            # no overlap
                "python web framework",       # partial overlap
            ],
        )
        # The first candidate should rank first
        assert results[0].text == "python ai for beginners"
        # The cooking one should rank last
        assert results[-1].text == "cooking recipes"

    def test_with_embedder_uses_embedding(self):
        embedder = _ToyEmbedder()
        results = rank_content(
            ref="python ai",
            candidates=[
                "rust web dev",                 # 0 0 0 0
                "python ai intro",              # 0 1 1 0
                "rust python web",              # 1 1 0 1
            ],
            embedder=embedder,
        )
        # embed() should have been called with the ref + all candidates
        assert len(embedder.calls) == 1
        # ref + 3 candidates = 4 inputs
        assert len(embedder.calls[0]) == 4
        # The "python ai intro" candidate should score highest
        assert results[0].text == "python ai intro"

    def test_metric_kwarg_euclidean(self):
        # With our toy embedder, identical vectors → 1.0 (euclidean
        # similarity = 1 / (1 + d) where d = 0). "rust web" has a
        # totally different vector → small similarity.
        embedder = _ToyEmbedder()
        results = rank_content(
            ref="python ai",
            candidates=["python ai", "rust web", "python ai extra"],
            embedder=embedder,
            metric="euclidean",
        )
        # Two candidates are identical to ref → tied at 1.0
        assert math.isclose(results[0].score, 1.0, abs_tol=1e-9)
        assert math.isclose(results[1].score, 1.0, abs_tol=1e-9)
        # "rust web" is far away → ~1/3
        assert math.isclose(results[2].score, 1.0 / 3.0, abs_tol=1e-9)

    def test_metric_unknown_raises(self):
        embedder = _ToyEmbedder()
        with pytest.raises(ValueError):
            rank_content(
                ref="x",
                candidates=["y"],
                embedder=embedder,
                metric="manhattan",
            )

    def test_empty_candidates_returns_empty(self):
        results = rank_content(ref="x", candidates=[])
        assert results == []

    def test_top_k_truncates(self):
        results = rank_content(
            ref="python",
            candidates=["a", "b", "c", "d", "e"],
            top_k=2,
        )
        assert len(results) == 2

    def test_top_k_larger_than_n_returns_all(self):
        results = rank_content(
            ref="python",
            candidates=["a", "b"],
            top_k=10,
        )
        assert len(results) == 2

    def test_top_k_zero_or_negative_raises(self):
        with pytest.raises(ValueError):
            rank_content(ref="x", candidates=["y"], top_k=0)
        with pytest.raises(ValueError):
            rank_content(ref="x", candidates=["y"], top_k=-1)

    def test_ref_can_be_list_of_strings(self):
        # Some callers may pass a list of refs; we average the
        # token overlap or take the union. Test that the API
        # accepts it.
        results = rank_content(
            ref=["python", "ai"],
            candidates=["python ai tutorial", "cooking recipes"],
        )
        assert len(results) == 2
        assert results[0].text == "python ai tutorial"

    def test_scored_item_is_namedtuple(self):
        # ScoredItem is exposed for callers who want to access .text
        # and .score explicitly
        r = ScoredItem(text="x", score=1.0)
        assert r.text == "x"
        assert r.score == 1.0
        # Should be hashable / tuple-like
        assert r[0] == "x"
        assert r[1] == 1.0

    def test_deterministic_keyword_ranking(self):
        # KeywordScorer should be deterministic across runs
        a = rank_content(
            ref="python ai",
            candidates=["python ai", "web", "python intro"],
        )
        b = rank_content(
            ref="python ai",
            candidates=["python ai", "web", "python intro"],
        )
        assert [r.text for r in a] == [r.text for r in b]
        assert [r.score for r in a] == [r.score for r in b]

    def test_consistent_breaking_ties(self):
        # When two candidates score exactly the same, the order
        # should be stable. We don't mandate a specific tiebreak,
        # only that it doesn't crash and is reproducible.
        r1 = rank_content(ref="x", candidates=["a", "b", "c"])
        r2 = rank_content(ref="x", candidates=["a", "b", "c"])
        assert [r.text for r in r1] == [r.text for r in r2]


class TestEmbedderProtocol:
    def test_toy_embedder_satisfies_protocol(self):
        # Static check: the Embedder protocol is a class with
        # an ``embed`` method that takes List[str] and returns
        # List[List[float]].
        emb = _ToyEmbedder()
        assert hasattr(emb, "embed")
        out = emb.embed(["a", "b"])
        assert isinstance(out, list)
        assert all(isinstance(v, list) for v in out)
        assert all(isinstance(x, float) for v in out for x in v)
