"""v1.8.0 — smart_retrieval: 5-phase search pipeline.

Ports the algorithm subset of RUFLO v3's
`@claude-flow/memory/src/smart-retrieval.ts` (ADR-090) to
gemas_core. The 5 phases:

  1. query_expansion    : expand a single query into N variants
  2. multi_query        : fan-out to the SearchFn for each variant
  3. rrf                : Reciprocal Rank Fusion across the N result lists
  4. recency_boost      : re-score by freshness (half-life decay)
  5. mmr                : Maximal Marginal Relevance diversity

Phase 6 (`session_diversity`) is a NICE-TO-HAVE: round-robin across
distinct sessions to keep one session from dominating. Toggled
separately so callers can opt out.

Pluggable ``SearchFn`` interface: any callable that takes a query
string and returns a list of ``RetrievalHit`` objects. The default
wrapper around `brain_recall` (the existing MCP tool) is documented
in the README but NOT wired here — the function is the contract;
the wiring is the caller's responsibility (it would require an
aiohttp/HTTP dependency that gemas_core can't take on).

Constraint compliance:
  - Does NOT replace `retrieval_search` or `brain_recall`
    (additive; callers choose to use it).
  - stdlib-only (hashlib for the fallback content_hash).
  - No I/O. The pipeline operates on whatever the SearchFn returns.
"""
from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger("gemas-core.core.smart_retrieval")


# --- Types ---------------------------------------------------------------


@dataclass
class RetrievalHit:
    """A single search result."""

    id: str
    text: str
    score: float = 0.0
    created_at: Optional[str] = None  # ISO-8601 UTC
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class SearchFn(Protocol):
    """Callable contract for a search backend.

    Any object with this signature works: a function, a bound
    method, an instance with `__call__`, etc. This mirrors the
    `Fetcher` protocol pattern from `core.web_crawler`.
    """

    def __call__(self, query: str, *, top_k: int = 10) -> List[RetrievalHit]: ...


@dataclass
class SmartSearchOptions:
    """Toggles for the 4 phases.

    All default to True (the full pipeline). Set a flag to False
    to skip that phase — useful for benchmarking or for callers
    that have a backend that already does RRF internally.
    """

    multi_query: bool = True
    recency_boost: bool = True
    diversity_mmr: bool = True
    session_diversity: bool = True
    # Knobs
    n_query_variants: int = 3           # for multi_query
    recency_half_life_days: float = 30.0
    mmr_lambda: float = 0.7             # 0 = pure diversity, 1 = pure relevance
    rrf_k: int = 60                     # RRF constant (k smoothing)


@dataclass
class SmartSearchResult:
    """Final output of `smart_search()`."""

    hits: List[RetrievalHit]
    phases_run: List[str] = field(default_factory=list)
    n_input_queries: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": [h.__dict__ for h in self.hits],
            "phases_run": list(self.phases_run),
            "n_input_queries": self.n_input_queries,
        }


# --- Phase 1: query expansion -------------------------------------------

_WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)


def expand_query(query: str, n_variants: int = 3) -> List[str]:
    """Expand a query into N variants.

    Strategy (stdlib-only, no LLM dependency):
      1. The original query (always included).
      2. Drop-stopword variant.
      3. Substring variants for the longest N-1 terms.

    For more sophisticated expansion, callers can pre-expand the
    query and pass the result via `multi_query=False` with a
    custom SearchFn that handles expansion.
    """
    if n_variants < 1:
        return [query]
    out = [query]
    tokens = _WORD_RE.findall(query.lower())
    stopwords = {
        "a", "an", "the", "is", "of", "in", "on", "and", "or",
        "to", "for", "with", "by", "at", "as", "be", "this", "that",
    }
    meaningful = [t for t in tokens if t not in stopwords and len(t) >= 3]
    if meaningful:
        out.append(" ".join(meaningful))
    # Substring variants
    longest = sorted(meaningful, key=len, reverse=True)
    for term in longest[: n_variants - 1]:
        if term not in out:
            out.append(term)
    return out[:n_variants]


# --- Phase 2: multi-query fan-out ---------------------------------------


def multi_query_search(
    queries: List[str],
    search_fn: SearchFn,
    *,
    per_query_top_k: int = 10,
) -> List[List[RetrievalHit]]:
    """Run the SearchFn once per query, return the per-query result lists."""
    out: List[List[RetrievalHit]] = []
    for q in queries:
        try:
            hits = search_fn(q, top_k=per_query_top_k)
        except Exception as e:
            logger.warning(f"multi_query_search: search_fn failed for {q!r}: {e}")
            hits = []
        out.append(hits)
    return out


# --- Phase 3: RRF -------------------------------------------------------


def rrf_fuse(
    result_lists: List[List[RetrievalHit]],
    *,
    k: int = 60,
) -> List[RetrievalHit]:
    """Reciprocal Rank Fusion across N ranked lists.

    Each hit's final score is ``sum(1 / (k + rank_i))`` across all
    lists that contain it. Hits keep their original ``text`` and
    ``metadata`` from the first list they appear in.
    """
    scores: Dict[str, float] = {}
    by_id: Dict[str, RetrievalHit] = {}
    for lst in result_lists:
        for rank, hit in enumerate(lst, start=1):
            scores[hit.id] = scores.get(hit.id, 0.0) + 1.0 / (k + rank)
            if hit.id not in by_id:
                by_id[hit.id] = hit
    # Re-score + sort desc
    fused: List[RetrievalHit] = []
    for hid, base_hit in by_id.items():
        fused.append(RetrievalHit(
            id=base_hit.id,
            text=base_hit.text,
            score=scores[hid],
            created_at=base_hit.created_at,
            session_id=base_hit.session_id,
            metadata=dict(base_hit.metadata),
        ))
    fused.sort(key=lambda h: h.score, reverse=True)
    return fused


# --- Phase 4: recency boost ---------------------------------------------


def recency_boost(
    hits: List[RetrievalHit],
    *,
    half_life_days: float = 30.0,
    now: Optional[str] = None,
) -> List[RetrievalHit]:
    """Re-score hits by freshness using half-life decay.

    Newer hits get a multiplicative boost of 1.0; hits at the
    half-life age get 0.5; hits at 2x the half-life get 0.25, etc.

    Hits without a `created_at` get a 0.5 boost (neutral).
    """
    if not now:
        now = _now_iso()
    now_ts = _to_ts(now)
    if half_life_days <= 0:
        half_life_days = 1.0
    half_life_s = half_life_days * 86400.0

    out: List[RetrievalHit] = []
    for h in hits:
        if h.created_at is None:
            factor = 0.5
        else:
            age_s = max(0.0, now_ts - _to_ts(h.created_at))
            factor = math.pow(0.5, age_s / half_life_s)
        out.append(RetrievalHit(
            id=h.id,
            text=h.text,
            score=h.score * factor,
            created_at=h.created_at,
            session_id=h.session_id,
            metadata=dict(h.metadata),
        ))
    out.sort(key=lambda h: h.score, reverse=True)
    return out


# --- Phase 5: MMR diversity --------------------------------------------


def mmr_diversify(
    hits: List[RetrievalHit],
    *,
    top_k: int = 10,
    lam: float = 0.7,
    similarity_fn: Optional[Callable[[RetrievalHit, RetrievalHit], float]] = None,
) -> List[RetrievalHit]:
    """Maximal Marginal Relevance diversity.

    Greedy: pick the top-scoring hit first, then iteratively pick
    the hit that maximizes ``lam * score - (1 - lam) * max_sim``,
    where ``max_sim`` is its max similarity to already-picked hits.
    """
    if not hits:
        return []
    if similarity_fn is None:
        similarity_fn = _jaccard_text_similarity
    if lam < 0:
        lam = 0.0
    if lam > 1:
        lam = 1.0

    selected: List[RetrievalHit] = []
    pool = list(hits)
    # First pick: highest score
    pool.sort(key=lambda h: h.score, reverse=True)
    selected.append(pool.pop(0))

    while len(selected) < top_k and pool:
        best_idx = 0
        best_val = -math.inf
        for i, candidate in enumerate(pool):
            max_sim = max(similarity_fn(candidate, s) for s in selected)
            val = lam * candidate.score - (1 - lam) * max_sim
            if val > best_val:
                best_val = val
                best_idx = i
        selected.append(pool.pop(best_idx))
    return selected


def _jaccard_text_similarity(a: RetrievalHit, b: RetrievalHit) -> float:
    """Jaccard similarity on word sets; [0, 1]."""
    wa = set(_WORD_RE.findall(a.text.lower()))
    wb = set(_WORD_RE.findall(b.text.lower()))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


# --- Phase 6 (optional): session diversity -----------------------------


def session_diversify(
    hits: List[RetrievalHit],
    *,
    top_k: int = 10,
    per_session_cap: int = 3,
) -> List[RetrievalHit]:
    """Round-robin across sessions to prevent one session dominating.

    Hits without a `session_id` are treated as one anonymous session.
    """
    by_session: Dict[Optional[str], List[RetrievalHit]] = {}
    for h in hits:
        by_session.setdefault(h.session_id, []).append(h)
    # Sort each bucket by score
    for v in by_session.values():
        v.sort(key=lambda x: x.score, reverse=True)
    # Truncate each bucket to per_session_cap
    for sid in by_session:
        by_session[sid] = by_session[sid][:per_session_cap]
    # Round-robin
    out: List[RetrievalHit] = []
    cursors = {sid: 0 for sid in by_session}
    session_ids = list(by_session.keys())
    while len(out) < top_k:
        progressed = False
        for sid in session_ids:
            cur = cursors[sid]
            if cur >= len(by_session[sid]):
                continue
            out.append(by_session[sid][cur])
            cursors[sid] = cur + 1
            progressed = True
            if len(out) >= top_k:
                break
        if not progressed:
            break
    return out


# --- Main entry point ---------------------------------------------------


def smart_search(
    query: str,
    search_fn: SearchFn,
    *,
    options: Optional[SmartSearchOptions] = None,
    top_k: int = 10,
) -> SmartSearchResult:
    """Run the 5-phase pipeline.

    Phases (controlled by ``options``):
      1. expand_query  (always; produces N variants)
      2. multi_query   (skipped if options.multi_query=False;
                        then we use the original query only)
      3. rrf           (always; with k=1 input list, it's a no-op)
      4. recency_boost (skipped if options.recency_boost=False)
      5. mmr           (skipped if options.diversity_mmr=False;
                        then top_k just truncates)
      6. session_diversity (skipped if options.session_diversity=False;
                            only runs if there are >= 2 sessions)
    """
    opts = options or SmartSearchOptions()
    phases: List[str] = []

    # Phase 1: expand
    queries = expand_query(query, n_variants=opts.n_query_variants)
    phases.append("expand_query")

    # Phase 2: multi-query fan-out
    if opts.multi_query and len(queries) > 1:
        result_lists = multi_query_search(queries, search_fn)
        phases.append("multi_query")
    else:
        # Single query, single result list
        result_lists = [search_fn(queries[0], top_k=top_k * 2)]
        # We don't tag multi_query here because we only did one fetch

    # Phase 3: RRF
    fused = rrf_fuse(result_lists, k=opts.rrf_k)
    phases.append("rrf")

    # Phase 4: recency boost
    if opts.recency_boost:
        fused = recency_boost(fused, half_life_days=opts.recency_half_life_days)
        phases.append("recency_boost")

    # Phase 6 (run before MMR for less work): session diversity
    if opts.session_diversity:
        sessions = {h.session_id for h in fused if h.session_id is not None}
        if len(sessions) >= 2:
            fused = session_diversify(fused, top_k=top_k * 2)
            phases.append("session_diversity")

    # Phase 5: MMR
    if opts.diversity_mmr:
        fused = mmr_diversify(fused, top_k=top_k, lam=opts.mmr_lambda)
        phases.append("diversity_mmr")
    else:
        fused = fused[:top_k]

    return SmartSearchResult(
        hits=fused,
        phases_run=phases,
        n_input_queries=len(queries),
    )


# --- Helpers ------------------------------------------------------------


def _to_ts(iso_ts: str) -> float:
    return datetime.fromisoformat(iso_ts.replace("Z", "+00:00")).timestamp()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_search_fn(records: List[Dict[str, Any]]) -> SearchFn:
    """Convenience: build a SearchFn from a static list of records.

    Each record needs ``id`` and ``text``; ``created_at`` and
    ``session_id`` are optional. The SearchFn does case-insensitive
    substring matching and scores by token overlap (no LLM).
    """
    def _fn(query: str, *, top_k: int = 10) -> List[RetrievalHit]:
        q_tokens = set(_WORD_RE.findall(query.lower()))
        scored: List[RetrievalHit] = []
        for r in records:
            t = r.get("text", "")
            t_tokens = set(_WORD_RE.findall(t.lower()))
            if not q_tokens:
                continue
            overlap = len(q_tokens & t_tokens) / max(1, len(q_tokens))
            if overlap > 0:
                scored.append(RetrievalHit(
                    id=r["id"],
                    text=t,
                    score=overlap,
                    created_at=r.get("created_at"),
                    session_id=r.get("session_id"),
                    metadata=r.get("metadata", {}),
                ))
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:top_k]
    return _fn


__all__ = [
    "RetrievalHit",
    "SearchFn",
    "SmartSearchOptions",
    "SmartSearchResult",
    "expand_query",
    "make_search_fn",
    "mmr_diversify",
    "multi_query_search",
    "recency_boost",
    "rrf_fuse",
    "session_diversify",
    "smart_search",
]
