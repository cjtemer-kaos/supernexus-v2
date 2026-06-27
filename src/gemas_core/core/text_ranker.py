"""Text ranking — stdlib-only, embedder-honouring.

RUFUS ``content_rankers/method.py::rank_content`` uses PyTorch /
numpy + Google embeddings with cosine or euclidean similarity.
We can't pull torch or numpy into gemas_core. Instead we ship:

  1. ``KeywordScorer`` — TF-IDF-ish, stdlib only. Stable,
     deterministic, no network. Default backend.
  2. ``Embedder`` protocol + ``cosine_similarity_vectors`` /
     ``euclidean_similarity_vectors`` — when a caller injects an
     embedder (Ollama, nomic-embed-text, etc.) we switch to the
     vector backend and the same public function shape.

The public API mirrors RUFUS closely so the gemas_client_overrides
web_research_gem can use the same call pattern.

Design notes
------------
- The "smoothed" IDF formula ``ln((N+1)/(df+1)) + 1`` ensures no
  term ever has zero weight, even if it appears in every document.
- ``ScoredItem`` is a NamedTuple so callers can destructure
  ``for text, score in results`` *or* access ``.text`` / ``.score``.
- We deliberately *don't* return RUFUS's bare tuples. The named
  tuple is self-documenting and a one-time change.
- The embedder protocol is structural (any object with
  ``embed(List[str]) -> List[List[float]]`` works). Static
  type-checkers see it via ``typing.Protocol`` but at runtime we
  just call the method.
"""
from __future__ import annotations

import math
import re
from typing import Iterable, List, NamedTuple, Optional, Protocol, Sequence, Union

__all__ = [
    "Embedder",
    "KeywordScorer",
    "ScoredItem",
    "cosine_similarity_vectors",
    "euclidean_similarity_vectors",
    "rank_content",
    "tokenize",
]


# -- Public types --------------------------------------------------------------


class Embedder(Protocol):
    """A text-to-vector backend. Implementations may use any model.

    The protocol is structural: any object with an ``embed`` method
    that takes a list of strings and returns a list of equal-length
    float vectors will satisfy it.
    """

    def embed(self, texts: List[str]) -> List[List[float]]:
        ...


class ScoredItem(NamedTuple):
    """``(text, score)`` pair returned by :func:`rank_content`.

    NamedTuple so callers can do either:

        for text, score in results
        for r in results: r.text, r.score
    """

    text: str
    score: float

    def __repr__(self) -> str:
        return f"ScoredItem(text={self.text!r}, score={self.score:.4f})"


# -- Tokenisation --------------------------------------------------------------


# Token regex: sequences of word characters (Unicode letters,
# digits, underscore) or hyphens. Drops pure punctuation and
# whitespace.
_TOKEN_RE = re.compile(r"[^\W_]+(?:[-_][^\W_]+)*", re.UNICODE)
# Tokens with fewer than 3 characters are noise (articles, "is",
# "at", "a", "to", etc.) — same heuristic as sklearn's default
# ``token_pattern`` minus the lone-letter edge cases.
_MIN_TOKEN_LEN = 3


def tokenize(text: str) -> List[str]:
    """Lower-case, strip punctuation, drop short tokens.

    Examples
    --------
    >>> tokenize("Hello, World!")
    ['hello', 'world']
    >>> tokenize("a cat is on a mat")
    ['cat', 'mat']
    """
    if not text:
        return []
    lowered = text.lower()
    tokens = _TOKEN_RE.findall(lowered)
    return [t for t in tokens if len(t) >= _MIN_TOKEN_LEN]


# -- Keyword scorer (TF-IDF, stdlib only) --------------------------------------


class KeywordScorer:
    """TF-IDF cosine-style scorer. Stdlib only, no numpy.

    For a reference query ``ref`` and a list of candidate texts
    ``candidates``, returns a list of float scores aligned to the
    candidates. Higher is more relevant.

    The scoring is:

        score(c) = sum_{t in ref_tokens} idf(t, candidates) * tf(t, c)

    with the standard smoothed IDF:

        idf(t) = ln((N + 1) / (df(t) + 1)) + 1

    where ``N`` is the number of candidates and ``df(t)`` is the
    number of candidates that contain ``t``. The ``+ 1`` smoothing
    guarantees ``idf >= 1`` for every term, so no candidate is
    ever scored *negatively* (which would confuse downstream code
    that assumes higher-is-better).
    """

    def score(self, ref: str, candidates: Sequence[str]) -> List[float]:
        ref_tokens = tokenize(ref)
        if not ref_tokens:
            return [0.0] * len(candidates)

        # Tokenise all candidates once
        cand_tokens: List[List[str]] = [tokenize(c) for c in candidates]
        n = max(1, len(cand_tokens))

        # Build a vocabulary: ref_tokens + all candidate tokens.
        # Then compute df and tf per candidate.
        vocab: set[str] = set(ref_tokens)
        for toks in cand_tokens:
            vocab.update(toks)

        # Document frequency: how many candidates contain each term
        df: dict[str, int] = {t: 0 for t in vocab}
        for toks in cand_tokens:
            for t in set(toks):
                df[t] = df.get(t, 0) + 1

        # Smoothed IDF, capped at vocab / n to avoid 0 division on
        # terms that appear in every doc (we still add 1, so never
        # zero).
        def idf(term: str) -> float:
            return math.log((n + 1) / (df.get(term, 0) + 1)) + 1.0

        # Pre-compute ref term weights so we only iterate over ref
        # tokens when scoring each candidate.
        ref_weights: List[tuple[str, float]] = [
            (t, idf(t)) for t in ref_tokens
        ]

        scores: List[float] = []
        for toks in cand_tokens:
            if not toks:
                scores.append(0.0)
                continue
            tf: dict[str, int] = {}
            for t in toks:
                tf[t] = tf.get(t, 0) + 1
            s = 0.0
            for t, w in ref_weights:
                if t in tf:
                    s += w * tf[t]
            scores.append(s)
        return scores


# -- Vector similarity (for embedder backends) --------------------------------


def _check_dims(ref: Sequence[Sequence[float]], cands: Sequence[Sequence[float]]) -> None:
    """Raise ValueError if any candidate's dimension doesn't match the ref."""
    if not ref:
        return
    d = len(ref[0])
    for i, v in enumerate(cands):
        if len(v) != d:
            raise ValueError(
                f"candidate[{i}] has dim={len(v)} but ref has dim={d}"
            )


def cosine_similarity_vectors(
    ref: Sequence[Sequence[float]],
    cands: Sequence[Sequence[float]],
) -> List[float]:
    """Pairwise cosine similarity between ``ref[0]`` and each candidate.

    Both inputs are 2-D sequences. ``ref`` is expected to have
    length 1 (one reference vector); the result has the same
    length as ``cands``. A zero vector in either side returns 0.0
    rather than raising.
    """
    if not ref or not cands:
        return []
    _check_dims(ref, cands)
    r = ref[0]
    r_norm = math.sqrt(sum(x * x for x in r))
    out: List[float] = []
    for v in cands:
        v_norm = math.sqrt(sum(x * x for x in v))
        if r_norm == 0.0 or v_norm == 0.0:
            out.append(0.0)
            continue
        dot = sum(a * b for a, b in zip(r, v))
        out.append(dot / (r_norm * v_norm))
    return out


def euclidean_similarity_vectors(
    ref: Sequence[Sequence[float]],
    cands: Sequence[Sequence[float]],
) -> List[float]:
    """Convert euclidean distance to similarity as ``1 / (1 + d)``.

    This matches RUFUS's behaviour (see ``utils.py::pairwise_distance``).
    Identical vectors get 1.0; as distance grows, similarity
    approaches 0.
    """
    if not ref or not cands:
        return []
    _check_dims(ref, cands)
    r = ref[0]
    out: List[float] = []
    for v in cands:
        sq = sum((a - b) ** 2 for a, b in zip(r, v))
        d = math.sqrt(sq)
        out.append(1.0 / (1.0 + d))
    return out


# -- Public entry point --------------------------------------------------------


def rank_content(
    ref: Union[str, Sequence[str]],
    candidates: Iterable[str],
    *,
    embedder: Optional[Embedder] = None,
    metric: str = "cosine",
    top_k: Optional[int] = None,
) -> List[ScoredItem]:
    """Score ``candidates`` against ``ref`` and return them sorted desc.

    Parameters
    ----------
    ref:
        Reference text (a query, prompt, or any string to score
        candidates against). Can also be a list of strings, in
        which case the first element is used.
    candidates:
        Iterable of candidate texts. The order in the result is
        independent of the input order.
    embedder:
        Optional :class:`Embedder` backend. When provided, scoring
        is done via embedding similarity. When ``None``, scoring
        falls back to :class:`KeywordScorer` (TF-IDF, stdlib only).
    metric:
        ``"cosine"`` or ``"euclidean"``. Ignored when ``embedder``
        is None (keyword scoring is always TF-IDF). Default
        ``"cosine"``.
    top_k:
        If set, return at most this many results. Must be a
        positive integer. Default ``None`` (return all).

    Returns
    -------
    list[ScoredItem]
        Items sorted by score descending. Ties keep a stable,
        deterministic order (input order).
    """
    cand_list: List[str] = list(candidates)
    ref_text = ref[0] if isinstance(ref, Sequence) and not isinstance(ref, str) else ref
    if not isinstance(ref_text, str):
        ref_text = str(ref_text)

    if top_k is not None and top_k <= 0:
        raise ValueError(f"top_k must be a positive integer, got {top_k}")

    if not cand_list:
        return []

    if embedder is not None:
        # Embedding path: ref first, then all candidates, in one
        # batch call so a remote backend can amortise overhead.
        vectors = embedder.embed([ref_text, *cand_list])
        if len(vectors) != len(cand_list) + 1:
            raise ValueError(
                f"embedder returned {len(vectors)} vectors for "
                f"{len(cand_list) + 1} inputs"
            )
        ref_vec = [vectors[0]]
        cand_vecs = vectors[1:]
        if metric == "cosine":
            scores = cosine_similarity_vectors(ref_vec, cand_vecs)
        elif metric == "euclidean":
            scores = euclidean_similarity_vectors(ref_vec, cand_vecs)
        else:
            raise ValueError(
                f"Unknown similarity metric: {metric!r}. "
                f"Expected 'cosine' or 'euclidean'."
            )
    else:
        # Keyword path
        scorer = KeywordScorer()
        scores = scorer.score(ref_text, cand_list)

    # Pair up with original indices for stable sort
    paired: List[tuple[int, str, float]] = [
        (i, text, score) for i, (text, score) in enumerate(zip(cand_list, scores))
    ]
    # Sort by score desc, then by original index asc (stable)
    paired.sort(key=lambda p: (-p[2], p[0]))

    result: List[ScoredItem] = [
        ScoredItem(text=text, score=score) for _, text, score in paired
    ]
    if top_k is not None:
        result = result[:top_k]
    return result
