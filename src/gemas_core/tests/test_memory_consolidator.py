"""v1.8.0 — memory_consolidator tests."""
from datetime import datetime, timezone, timedelta

from gemas_core.core.memory_consolidator import (
    ConsolidationResult,
    DedupStrategy,
    MemoryBackend,
    MemoryEntry,
    compact_index,
    dedup,
    run_all,
    sweep_expired,
)


# --- Test backend ---------------------------------------------------------


class _FakeBackend:
    """In-memory MemoryBackend for tests."""

    def __init__(self):
        self.entries: dict = {}  # id -> MemoryEntry
        self.deleted: list = []
        self.updates: list = []

    def add(self, e: MemoryEntry):
        self.entries[e.id] = e

    def list_all(self):
        return list(self.entries.values())

    def delete(self, entry_id: str) -> bool:
        if entry_id in self.entries:
            del self.entries[entry_id]
            self.deleted.append(entry_id)
            return True
        return False

    def update(self, entry: MemoryEntry) -> bool:
        if entry.id in self.entries:
            self.entries[entry.id] = entry
            self.updates.append(entry.id)
            return True
        return False


def _entry(id, content="x", hash_=None, created_at=None, ttl_s=None, tags=None):
    return MemoryEntry(
        id=id,
        content=content,
        content_hash=hash_ or ("h_" + content),
        created_at=created_at or "2026-06-06T00:00:00+00:00",
        ttl_s=ttl_s,
        tags=tags or [],
    )


# --- Tests --------------------------------------------------------------


class TestMemoryEntry:
    def test_is_expired_no_ttl(self):
        e = _entry("a")
        assert e.is_expired() is False

    def test_is_expired_future(self):
        e = _entry("a", created_at="2020-01-01T00:00:00+00:00", ttl_s=60)
        assert e.is_expired() is True

    def test_is_expired_recent(self):
        # TTL of 1 day, created 1 minute ago
        now = datetime.now(timezone.utc).isoformat()
        recent = (
            datetime.now(timezone.utc) - timedelta(minutes=1)
        ).isoformat()
        e = _entry("a", created_at=recent, ttl_s=86400)
        assert e.is_expired() is False


class TestSweepExpired:
    def test_deletes_expired(self):
        b = _FakeBackend()
        b.add(_entry("e1", ttl_s=None))  # never expires
        b.add(_entry("e2", ttl_s=86400,
                     created_at="2020-01-01T00:00:00+00:00"))  # expired
        b.add(_entry("e3", ttl_s=60,
                     created_at="2020-01-01T00:00:00+00:00"))  # expired
        r = sweep_expired(b)
        assert r.swept == 2
        assert set(r.deleted_ids) == {"e2", "e3"}
        assert "e1" in b.entries

    def test_nothing_to_sweep(self):
        b = _FakeBackend()
        b.add(_entry("e1", ttl_s=None))
        r = sweep_expired(b)
        assert r.swept == 0
        assert r.deleted_ids == []


class TestDedup:
    def test_keep_newest(self):
        b = _FakeBackend()
        b.add(_entry("a1", hash_="h1", created_at="2026-01-01T00:00:00+00:00"))
        b.add(_entry("a2", hash_="h1", created_at="2026-02-01T00:00:00+00:00"))
        b.add(_entry("a3", hash_="h1", created_at="2026-03-01T00:00:00+00:00"))
        b.add(_entry("b1", hash_="h2", created_at="2026-01-01T00:00:00+00:00"))
        r = dedup(b, strategy=DedupStrategy.KEEP_NEWEST)
        assert r.deduped == 2  # a1, a2
        assert set(r.kept_ids) == {"a3", "b1"}
        assert "a1" not in b.entries
        assert "a2" not in b.entries
        assert "a3" in b.entries

    def test_keep_oldest(self):
        b = _FakeBackend()
        b.add(_entry("a1", hash_="h1", created_at="2026-01-01T00:00:00+00:00"))
        b.add(_entry("a2", hash_="h1", created_at="2026-02-01T00:00:00+00:00"))
        b.add(_entry("a3", hash_="h1", created_at="2026-03-01T00:00:00+00:00"))
        r = dedup(b, strategy=DedupStrategy.KEEP_OLDEST)
        assert r.deduped == 2
        assert r.kept_ids == ["a1"]
        assert "a1" in b.entries
        assert "a2" not in b.entries

    def test_merge_tags(self):
        b = _FakeBackend()
        b.add(_entry("a1", hash_="h1", created_at="2026-01-01T00:00:00+00:00",
                     tags=["alpha", "beta"]))
        b.add(_entry("a2", hash_="h1", created_at="2026-02-01T00:00:00+00:00",
                     tags=["beta", "gamma"]))
        b.add(_entry("a3", hash_="h1", created_at="2026-03-01T00:00:00+00:00",
                     tags=["delta"]))
        r = dedup(b, strategy=DedupStrategy.MERGE_TAGS)
        assert r.deduped == 2
        # The newest (a3) should have all unique tags
        assert set(b.entries["a3"].tags) == {"alpha", "beta", "gamma", "delta"}

    def test_no_duplicates(self):
        b = _FakeBackend()
        b.add(_entry("a", hash_="h1"))
        b.add(_entry("b", hash_="h2"))
        r = dedup(b)
        assert r.deduped == 0
        assert set(r.kept_ids) == {"a", "b"}


class TestCompactIndex:
    def test_returns_zero_compacted(self):
        b = _FakeBackend()
        b.add(_entry("a"))
        r = compact_index(b)
        assert r.compacted == 0

    def test_no_delete_calls(self):
        b = _FakeBackend()
        b.add(_entry("a"))
        compact_index(b)
        assert b.deleted == []
        assert "a" in b.entries


class TestRunAll:
    def test_order_sweep_then_dedup(self):
        b = _FakeBackend()
        # Add: an expired entry, a fresh dup pair, a unique entry
        b.add(_entry("e1", ttl_s=60,
                     created_at="2020-01-01T00:00:00+00:00", hash_="h1"))
        b.add(_entry("e2", hash_="h2", created_at="2026-01-01T00:00:00+00:00"))
        b.add(_entry("e3", hash_="h2", created_at="2026-02-01T00:00:00+00:00"))
        b.add(_entry("e4", hash_="h3", created_at="2026-01-01T00:00:00+00:00"))
        r = run_all(b)
        assert r.swept == 1   # e1
        assert r.deduped == 1  # e2 (e3 kept)
        # Surviving: e3 (newer dup), e4
        assert set(b.entries.keys()) == {"e3", "e4"}


class TestConsolidationResult:
    def test_total_processed(self):
        r = ConsolidationResult(swept=1, deduped=2, compacted=0)
        assert r.total_processed == 3

    def test_to_dict(self):
        r = ConsolidationResult(swept=1, deduped=2, compacted=0,
                                deleted_ids=["a", "b"],
                                kept_ids=["c"])
        d = r.to_dict()
        assert d["swept"] == 1
        assert d["deduped"] == 2
        assert d["compacted"] == 0
        assert d["total_processed"] == 3
        assert d["deleted_ids"] == ["a", "b"]
        assert d["kept_ids"] == ["c"]


class TestProtocolConformance:
    def test_fake_backend_is_protocol(self):
        b = _FakeBackend()
        assert isinstance(b, MemoryBackend)
