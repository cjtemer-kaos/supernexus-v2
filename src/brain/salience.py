"""
salience — Emotional salience tracking + recall bias.

Pattern (lethe SalienceTracker): every memory carries a salience score
0..1 driven by tags ("frustrated", "breakthrough", "preference"). On
recall, scores bias the ordering — emotionally tagged memories surface
sooner than dry neutral ones.

Lite version: in-memory rolling window, no LLM. The hooks are placed
so an LLM-guided tagger can drop in later.

Use:
    from src.brain.salience import salience
    salience.tag("obs:42", ["frustrated", "blocker"])
    score = salience.score_of("obs:42")  # → 0.0..1.0
    biased = salience.rerank(candidates, key=lambda c: c["id"])
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Dict, Iterable, List, Tuple

logger = logging.getLogger(__name__)


# Tag weights (additive, clipped to 1.0). Negative tags subtract.
TAG_WEIGHTS: Dict[str, float] = {
    # high positive — things the user explicitly cared about
    "breakthrough":   0.5,
    "decision":       0.4,
    "preference":     0.4,
    "important":      0.4,
    "fix":            0.3,
    "bugfix":         0.3,
    "blocker":        0.4,
    "frustrated":     0.4,
    "confused":       0.3,
    "celebrated":     0.3,
    # medium
    "warning":        0.2,
    "discovery":      0.25,
    "pattern":        0.2,
    "config":         0.15,
    # neutral
    "info":           0.05,
    "log":            0.05,
    # negative — explicit deprioritization
    "noise":         -0.3,
    "boilerplate":   -0.2,
}

# Active-pattern bias: if the current conversation surfaces a tag often,
# its score boost grows (recency × frequency). Decays exponentially.
ACTIVE_DECAY_HALF_LIFE_S = 1800  # 30 min


class SalienceTracker:
    def __init__(self):
        self._scores: Dict[str, float] = {}        # entry_id → score 0..1
        self._tags: Dict[str, List[str]] = {}      # entry_id → tag list
        self._active: Dict[str, Tuple[float, float]] = {}  # tag → (weight, ts)
        self._lock = threading.Lock()

    def tag(self, entry_id: str, tags: Iterable[str]) -> float:
        """Add tags to an entry. Returns the new score (clipped 0..1)."""
        tags = [t.strip().lower() for t in (tags or []) if t and t.strip()]
        if not entry_id or not tags:
            return self.score_of(entry_id)
        with self._lock:
            prev = set(self._tags.get(entry_id, []))
            new_tags = [t for t in tags if t not in prev]
            self._tags.setdefault(entry_id, []).extend(new_tags)
            base = self._scores.get(entry_id, 0.0)
            for t in new_tags:
                base += TAG_WEIGHTS.get(t, 0.05)
                # Reinforce active-pattern bias for this tag
                now = time.time()
                cur_w, _ = self._active.get(t, (0.0, now))
                self._active[t] = (min(1.0, cur_w + 0.1), now)
            base = max(0.0, min(1.0, base))
            self._scores[entry_id] = base
            return base

    def score_of(self, entry_id: str) -> float:
        with self._lock:
            return float(self._scores.get(entry_id, 0.0))

    def tags_of(self, entry_id: str) -> List[str]:
        with self._lock:
            return list(self._tags.get(entry_id, []))

    def active_bias(self, tag: str) -> float:
        """Current active-pattern weight for a tag (decays with time)."""
        with self._lock:
            entry = self._active.get(tag.lower())
            if not entry:
                return 0.0
            w, ts = entry
            age = max(0.0, time.time() - ts)
            decay = 0.5 ** (age / ACTIVE_DECAY_HALF_LIFE_S)
            return max(0.0, min(1.0, w * decay))

    def rerank(
        self,
        items: List,
        key: Callable[[object], str],
        *,
        salience_weight: float = 0.4,
    ) -> List:
        """Return items sorted by (original_rank_preserved + salience_boost).

        Stable sort: items with equal final score keep input order. The
        boost is a [0..1] bonus scaled by `salience_weight` so the caller
        can blend it with their own ranking (e.g. semantic similarity).
        """
        if not items:
            return items
        scored = []
        for i, it in enumerate(items):
            try:
                eid = key(it)
            except Exception:
                eid = ""
            s = self.score_of(eid) if eid else 0.0
            # Sum any active-pattern bias from this item's own tags
            for t in self.tags_of(eid):
                s += 0.3 * self.active_bias(t)
            score = -(i * 0.01) + s * salience_weight  # rank-preserving baseline
            scored.append((score, i, it))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [x[2] for x in scored]

    def stats(self) -> Dict:
        with self._lock:
            return {
                "tracked_entries": len(self._scores),
                "active_tags": {t: round(w, 3) for t, (w, _) in self._active.items()},
                "avg_score": round(
                    sum(self._scores.values()) / max(len(self._scores), 1), 3
                ),
            }


# Module-level singleton
salience = SalienceTracker()
