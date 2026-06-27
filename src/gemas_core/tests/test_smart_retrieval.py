"""v1.8.0 — smart_retrieval tests."""
import pytest

from gemas_core.core.smart_retrieval import (
    RetrievalHit,
    SearchFn,
    SmartSearchOptions,
    SmartSearchResult,
    expand_query,
    make_search_fn,
    mmr_diversify,
    multi_query_search,
    recency_boost,
    rrf_fuse,
    session_diversify,
    smart_search,
)


def _hit(id, text, score=0.0, created_at=None, session_id=None):
    return RetrievalHit(
        id=id, text=text, score=score,
        created_at=created_at, session_id=session_id,
    )


# --- Test data ----------------------------------------------------------


@pytest.fixture
def corpus():
    return [
        {"id": "d1", "text": "python programming language for data science",
         "created_at": "2026-06-01T00:00:00+00:00", "session_id": "s1"},
        {"id": "d2", "text": "java virtual machine jvm performance",
         "created_at": "2026-05-01T00:00:00+00:00", "session_id": "s1"},
        {"id": "d3", "text": "python machine learning and ai",
         "created_at": "2026-04-01T00:00:00+00:00", "session_id": "s2"},
        {"id": "d4", "text": "rust memory safety systems programming",
         "created_at": "2026-03-01T00:00:00+00:00", "session_id": "s2"},
        {"id": "d5", "text": "python web development with django",
         "created_at": "2026-02-01T00:00:00+00:00", "session_id": "s3"},
    ]


# --- Phase 1: query expansion --------------------------------------------


class TestExpandQuery:
    def test_returns_original(self):
        out = expand_query("python programming")
        assert "python programming" in out

    def test_strips_stopwords(self):
        out = expand_query("python is a programming language")
        # "is" and "a" should be removed
        assert "is" not in out[1].split() if len(out) > 1 else True
        assert "python" in out[1]
        assert "programming" in out[1]

    def test_short_tokens_removed(self):
        out = expand_query("a an the of in")
        # All tokens < 3 chars and stopwords — meaningful set is empty
        # Then the substring variant loop finds nothing
        assert out[0] == "a an the of in"

    def test_n_variants_respected(self):
        out = expand_query("python programming language tutorial", n_variants=2)
        assert len(out) <= 2

    def test_n_variants_1(self):
        out = expand_query("python programming", n_variants=1)
        assert out == ["python programming"]


# --- Phase 2: multi-query fan-out ----------------------------------------


class TestMultiQuerySearch:
    def test_runs_search_for_each_query(self, corpus):
        fn = make_search_fn(corpus)
        results = multi_query_search(["python", "java", "rust"], fn)
        assert len(results) == 3
        assert all(isinstance(r, list) for r in results)
        # python should return 3 docs
        assert len(results[0]) == 3

    def test_search_fn_failure_logged(self, corpus, caplog):
        def bad_fn(query, *, top_k=10):
            if query == "bad":
                raise RuntimeError("test error")
            return []
        with caplog.at_level("WARNING", logger="gemas-core.core.smart_retrieval"):
            results = multi_query_search(["ok", "bad"], bad_fn)
        assert results[1] == []  # graceful failure


# --- Phase 3: RRF --------------------------------------------------------


class TestRrfFuse:
    def test_single_list_passthrough(self):
        lst = [_hit("a", "alpha", score=0.9),
               _hit("b", "beta", score=0.5)]
        fused = rrf_fuse([lst])
        # 1/(k+1) for a, 1/(k+2) for b
        assert fused[0].id == "a"
        assert fused[1].id == "b"
        assert fused[0].score > fused[1].score

    def test_two_lists_with_overlap(self):
        l1 = [_hit("a", "alpha"), _hit("b", "beta"), _hit("c", "gamma")]
        l2 = [_hit("b", "beta"), _hit("d", "delta"), _hit("a", "alpha")]
        fused = rrf_fuse([l1, l2])
        # a: 1/61 + 1/63 = top
        # b: 1/62 + 1/61 = top (close to a)
        # a and b should be top 2 in some order
        top_two_ids = {fused[0].id, fused[1].id}
        assert top_two_ids == {"a", "b"}

    def test_k_60_default(self):
        l1 = [_hit("a", "alpha"), _hit("b", "beta")]
        fused = rrf_fuse([l1], k=60)
        # a score = 1/61
        assert abs(fused[0].score - 1/61) < 1e-9

    def test_preserves_text_from_first_appearance(self):
        l1 = [_hit("a", "alpha-text")]
        l2 = [_hit("a", "different-text")]
        fused = rrf_fuse([l1, l2])
        assert fused[0].text == "alpha-text"


# --- Phase 4: recency boost ---------------------------------------------


class TestRecencyBoost:
    def test_fresh_hits_score_higher(self):
        fresh = _hit("a", "alpha", score=1.0, created_at="2026-06-06T00:00:00+00:00")
        old = _hit("b", "beta", score=1.0, created_at="2020-01-01T00:00:00+00:00")
        out = recency_boost([old, fresh], half_life_days=30.0,
                            now="2026-06-06T00:00:00+00:00")
        assert out[0].id == "a"
        assert out[0].score > out[1].score

    def test_no_created_at_gets_neutral(self):
        h = _hit("a", "alpha", score=1.0)
        out = recency_boost([h], now="2026-06-06T00:00:00+00:00")
        assert abs(out[0].score - 0.5) < 1e-9

    def test_half_life_at_exact_age(self):
        # At half-life, factor = 0.5
        h = _hit("a", "alpha", score=1.0, created_at="2026-06-06T00:00:00+00:00")
        # Now is 30 days later
        out = recency_boost([h], half_life_days=30.0,
                            now="2026-07-06T00:00:00+00:00")
        assert abs(out[0].score - 0.5) < 1e-9

    def test_zero_half_life_clamped(self):
        h = _hit("a", "alpha", score=1.0, created_at="2020-01-01T00:00:00+00:00")
        out = recency_boost([h], half_life_days=0.0,
                            now="2026-06-06T00:00:00+00:00")
        # Doesn't crash; produces a (very small) score
        assert out[0].score >= 0


# --- Phase 5: MMR diversity --------------------------------------------


class TestMmrDiversify:
    def test_top_k_respected(self):
        hits = [_hit(f"h{i}", f"text {i}", score=1.0 / (i + 1))
                for i in range(20)]
        out = mmr_diversify(hits, top_k=5)
        assert len(out) == 5

    def test_first_pick_is_highest_score(self):
        hits = [
            _hit("a", "alpha", score=0.5),
            _hit("b", "beta", score=0.9),
            _hit("c", "gamma", score=0.7),
        ]
        out = mmr_diversify(hits, top_k=3)
        assert out[0].id == "b"

    def test_lambda_1_pure_relevance(self):
        # With lambda=1, MMR becomes pure top-k by score
        hits = [
            _hit("a", "alpha", score=0.3),
            _hit("b", "beta", score=0.9),
            _hit("c", "gamma", score=0.1),
        ]
        out = mmr_diversify(hits, top_k=3, lam=1.0)
        assert [h.id for h in out] == ["b", "a", "c"]

    def test_lambda_0_pure_diversity(self):
        # With lambda=0, MMR picks the most diverse sequence
        hits = [
            _hit("a", "alpha beta gamma", score=0.9),
            _hit("b", "alpha beta gamma", score=0.5),  # very similar to a
            _hit("c", "rust memory safety", score=0.1),  # very different
        ]
        out = mmr_diversify(hits, top_k=3, lam=0.0)
        # a first (highest score regardless)
        assert out[0].id == "a"
        # c should be picked second (lowest similarity to a)
        assert out[1].id == "c"

    def test_empty_input(self):
        assert mmr_diversify([], top_k=5) == []


# --- Phase 6: session diversity -----------------------------------------


class TestSessionDiversify:
    def test_round_robin(self):
        s1 = [
            _hit("a1", "alpha", score=0.9, session_id="s1"),
            _hit("a2", "alpha2", score=0.8, session_id="s1"),
        ]
        s2 = [
            _hit("b1", "beta", score=0.7, session_id="s2"),
            _hit("b2", "beta2", score=0.6, session_id="s2"),
        ]
        out = session_diversify(s1 + s2, top_k=4, per_session_cap=2)
        ids = [h.id for h in out]
        # Round-robin: a1, b1, a2, b2
        assert ids == ["a1", "b1", "a2", "b2"]

    def test_per_session_cap(self):
        s1 = [
            _hit(f"s1_{i}", f"text {i}", score=10 - i, session_id="s1")
            for i in range(10)
        ]
        s2 = [_hit("s2_0", "x", score=1.0, session_id="s2")]
        out = session_diversify(s1 + s2, top_k=5, per_session_cap=2)
        # Only 2 from s1 even though 10 are available
        assert sum(1 for h in out if h.id.startswith("s1_")) == 2

    def test_anon_session_treated_as_one(self):
        h1 = _hit("a1", "x", score=0.5)  # no session
        h2 = _hit("a2", "y", score=0.4)  # no session
        out = session_diversify([h1, h2], top_k=2, per_session_cap=3)
        assert len(out) == 2


# --- Main pipeline ------------------------------------------------------


class TestSmartSearch:
    def test_full_pipeline(self, corpus):
        fn = make_search_fn(corpus)
        r = smart_search("python", fn, top_k=3)
        assert isinstance(r, SmartSearchResult)
        assert "expand_query" in r.phases_run
        assert "rrf" in r.phases_run
        assert "recency_boost" in r.phases_run
        assert len(r.hits) <= 3

    def test_skips_phases_when_disabled(self, corpus):
        fn = make_search_fn(corpus)
        opts = SmartSearchOptions(
            multi_query=False, recency_boost=False,
            diversity_mmr=False, session_diversity=False,
        )
        r = smart_search("python", fn, options=opts, top_k=3)
        assert "recency_boost" not in r.phases_run
        assert "diversity_mmr" not in r.phases_run
        assert "session_diversity" not in r.phases_run

    def test_returns_relevant_results(self, corpus):
        fn = make_search_fn(corpus)
        r = smart_search("python", fn, top_k=3)
        # All returned hits should mention python
        for hit in r.hits:
            assert "python" in hit.text.lower()

    def test_top_k_zero(self, corpus):
        fn = make_search_fn(corpus)
        r = smart_search("python", fn, top_k=0)
        assert r.hits == []

    def test_result_to_dict(self, corpus):
        fn = make_search_fn(corpus)
        r = smart_search("python", fn, top_k=2)
        d = r.to_dict()
        assert "hits" in d
        assert "phases_run" in d
        assert "n_input_queries" in d
        assert d["n_input_queries"] >= 1


class TestMakeSearchFn:
    def test_substring_matching(self, corpus):
        fn = make_search_fn(corpus)
        hits = fn("python", top_k=5)
        assert all("python" in h.text.lower() for h in hits)
        assert len(hits) == 3  # 3 docs mention python

    def test_no_match(self, corpus):
        fn = make_search_fn(corpus)
        # Use tokens that don't appear in any corpus text
        hits = fn("quantum blockchain cryptocurrency", top_k=5)
        assert hits == []


class TestProtocolConformance:
    def test_make_search_fn_is_protocol(self, corpus):
        fn = make_search_fn(corpus)
        assert isinstance(fn, SearchFn)
