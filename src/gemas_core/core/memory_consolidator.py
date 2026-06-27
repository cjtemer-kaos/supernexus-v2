"""v1.8.0 — memory_consolidator: explicit maintenance API for memory hygiene.

Ports the algorithm subset of RUFLO v3's
`@claude-flow/memory/src/consolidator.ts` to gemas_core. Provides
3 maintenance operations that should be run periodically (e.g.
once a day) by `self_learning_loop.py` or an external scheduler:

  - sweep_expired()       : delete observations past their TTL
  - dedup(strategy)        : collapse duplicates (3 strategies)
  - compact_index()        : SQLite is already compact — NOP
  - run_all()              : the 3 above, in order

Why a separate module?
  - RUFLO's `MemoryConsolidator` is an *additive* contract: a
    periodic maintenance API. SuperNEXUS already has
    `self_learning_loop.py` for continuous processing, but it
    does NOT expose a contract for explicit "now do maintenance".
    This module fills that gap.
  - Operations are **operations on a passed-in observations
    list** (or backend Protocol), so this module has NO hard
    dependency on `nexus_memory.db` or any sqlite module. The
    caller decides where the data lives.

Constraint compliance:
  - Does NOT replace `self_learning_loop.py` (additive).
  - Does NOT modify `nexus_memory.db` schema.
  - The Protocol-based backend keeps gemas_core stdlib-only.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import (
    Any, Dict, List, Optional, Protocol, runtime_checkable,
)

logger = logging.getLogger("gemas-core.core.memory_consolidator")


class DedupStrategy(str, Enum):
    """How to collapse duplicate observations."""

    KEEP_NEWEST = "keep_newest"   # keep the most-recently-created one
    KEEP_OLDEST = "keep_oldest"   # keep the first one
    MERGE_TAGS = "merge_tags"     # keep newest, union all tags


@dataclass
class MemoryEntry:
    """A single observation row, in the shape produced by
    `nexus-sovereign.observations` queries.

    ``content_hash`` is the SHA-256 of ``content`` (or whatever
    canonicalization the backend uses); it's the dedup key.
    """

    id: str
    content: str
    content_hash: str
    created_at: str          # ISO-8601 UTC
    ttl_s: Optional[int] = None  # None = never expires
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self, now: Optional[str] = None) -> bool:
        """True if a TTL is set and has elapsed."""
        if self.ttl_s is None:
            return False
        if not now:
            now = _now_iso()
        return now > _add_seconds(self.created_at, self.ttl_s)


@runtime_checkable
class MemoryBackend(Protocol):
    """Minimal contract a backend must satisfy.

    gemas_core doesn't ship a backend; callers pass one in
    (e.g. a thin wrapper around `nexus-sovereign.add_observation`
    / `delete_observation`). Keeping this a Protocol keeps the
    core module stdlib-only.
    """

    def list_all(self) -> List[MemoryEntry]: ...
    def delete(self, entry_id: str) -> bool: ...
    def update(self, entry: MemoryEntry) -> bool: ...


# --- Operations ----------------------------------------------------------


@dataclass
class ConsolidationResult:
    """Outcome of a single consolidation run."""

    swept: int = 0
    deduped: int = 0
    compacted: int = 0
    deleted_ids: List[str] = field(default_factory=list)
    kept_ids: List[str] = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        return self.swept + self.deduped + self.compacted

    def to_dict(self) -> Dict[str, Any]:
        return {
            "swept": self.swept,
            "deduped": self.deduped,
            "compacted": self.compacted,
            "total_processed": self.total_processed,
            "deleted_ids": list(self.deleted_ids),
            "kept_ids": list(self.kept_ids),
        }


def sweep_expired(
    backend: MemoryBackend,
    now: Optional[str] = None,
) -> ConsolidationResult:
    """Delete observations whose TTL has elapsed.

    Returns a result with the deleted entry IDs.
    """
    result = ConsolidationResult()
    for entry in backend.list_all():
        if entry.is_expired(now):
            if backend.delete(entry.id):
                result.swept += 1
                result.deleted_ids.append(entry.id)
            else:
                logger.warning(
                    f"sweep_expired: backend.delete({entry.id}) returned False"
                )
    return result


def dedup(
    backend: MemoryBackend,
    strategy: DedupStrategy = DedupStrategy.KEEP_NEWEST,
) -> ConsolidationResult:
    """Collapse duplicates sharing the same ``content_hash``.

    Three strategies:
      - KEEP_NEWEST: keep the most-recently-created entry; delete
        the rest.
      - KEEP_OLDEST: keep the first-created entry; delete the rest.
      - MERGE_TAGS:  keep the newest, but union all tags from the
        duplicates into it. The merged entry is then `update()`d.

    Returns a result with the deleted entry IDs and the kept ones.
    """
    result = ConsolidationResult()
    by_hash: Dict[str, List[MemoryEntry]] = {}
    for entry in backend.list_all():
        by_hash.setdefault(entry.content_hash, []).append(entry)

    for content_hash, group in by_hash.items():
        if len(group) < 2:
            result.kept_ids.extend(e.id for e in group)
            continue
        # Sort by created_at; tie-break by id for determinism.
        sorted_group = sorted(group, key=lambda e: (e.created_at, e.id))
        if strategy == DedupStrategy.KEEP_OLDEST:
            keeper = sorted_group[0]
        else:
            # KEEP_NEWEST and MERGE_TAGS both keep the newest.
            keeper = sorted_group[-1]
        duplicates = [e for e in group if e.id != keeper.id]

        if strategy == DedupStrategy.MERGE_TAGS:
            seen_tags = set()
            merged_tags: List[str] = []
            for e in group:
                for t in e.tags:
                    if t not in seen_tags:
                        seen_tags.add(t)
                        merged_tags.append(t)
            if list(keeper.tags) != merged_tags:
                keeper.tags = merged_tags
                backend.update(keeper)

        for dup in duplicates:
            if backend.delete(dup.id):
                result.deduped += 1
                result.deleted_ids.append(dup.id)
        result.kept_ids.append(keeper.id)
    return result


def compact_index(backend: MemoryBackend) -> ConsolidationResult:
    """Compact the backend's index.

    For SQLite-based backends (e.g. nexus_memory.db with FTS5),
    this is a NO-OP because SQLite auto-compacts on close + VACUUM
    is destructive. The result explicitly records that no action
    was taken, so callers can log "index already compact".
    """
    # Touch the backend so the contract is exercised (helps detect
    # backends that don't actually support the operations).
    _ = backend.list_all()
    return ConsolidationResult(compacted=0)


def run_all(
    backend: MemoryBackend,
    *,
    dedup_strategy: DedupStrategy = DedupStrategy.KEEP_NEWEST,
    now: Optional[str] = None,
) -> ConsolidationResult:
    """Run all 3 operations in order: sweep → dedup → compact.

    The combined result is returned. Order matters: dedup BEFORE
    sweep would re-allocate IDs to expired entries; sweep first
    shrinks the corpus, then dedup operates on what's left.
    """
    sweep_result = sweep_expired(backend, now=now)
    dedup_result = dedup(backend, strategy=dedup_strategy)
    compact_result = compact_index(backend)
    return ConsolidationResult(
        swept=sweep_result.swept,
        deduped=dedup_result.deduped,
        compacted=compact_result.compacted,
        deleted_ids=sweep_result.deleted_ids + dedup_result.deleted_ids,
        kept_ids=dedup_result.kept_ids,
    )


# --- Helpers -------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _add_seconds(iso_ts: str, seconds: int) -> str:
    ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    new_ts = ts.timestamp() + seconds
    return datetime.fromtimestamp(new_ts, tz=timezone.utc).isoformat()


__all__ = [
    "ConsolidationResult",
    "DedupStrategy",
    "MemoryBackend",
    "MemoryEntry",
    "compact_index",
    "dedup",
    "run_all",
    "sweep_expired",
]
