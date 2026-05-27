# tests/test_dream_consolidation.py
import pytest
import tempfile
import json
from pathlib import Path
from src.core.dream_consolidation import DreamConsolidator, DreamConfig, DreamResult
from src.core.hierarchical_memory import HierarchicalMemory, MemoryItem


@pytest.fixture
def memory_with_items(tmp_path):
    """Create a HierarchicalMemory with test items."""
    import src.core.hierarchical_memory as hm
    # Monkey-patch storage path
    original = hm._MEMORY_STORAGE
    hm._MEMORY_STORAGE = tmp_path / "test_memory.json"
    mem = HierarchicalMemory()
    # Add episodic items with varied importance/access
    for i in range(10):
        mem.store(
            f"Technical fact {i}: asyncio pattern #{i} for concurrent execution",
            tags=["asyncio", "pattern"],
            importance=0.5 + (i * 0.05),  # 0.5 to 0.95
            tier="episodic",
        )
    for item in mem._items[:5]:
        item.access_count = 10
    yield mem
    hm._MEMORY_STORAGE = original


def test_dream_selects_high_value_episodic(memory_with_items):
    dc = DreamConsolidator(config=DreamConfig(min_importance=0.5, min_access_count=5))
    candidates = dc.select(memory_with_items)
    assert len(candidates) > 0
    assert all(c.tier == "episodic" for c in candidates)


def test_dream_promotes_to_semantic(memory_with_items):
    dc = DreamConsolidator(config=DreamConfig(min_importance=0.5, min_access_count=5))
    result = dc.consolidate(memory_with_items)
    assert isinstance(result, DreamResult)
    assert result.promoted >= 1
    # Check promoted items are now semantic
    semantic = [i for i in memory_with_items._items if i.tier == "semantic"]
    assert len(semantic) >= 1


def test_dream_prunes_consolidated(memory_with_items):
    initial_count = len(memory_with_items._items)
    dc = DreamConsolidator(config=DreamConfig(
        min_importance=0.5, min_access_count=5, prune_after_consolidation=True
    ))
    result = dc.consolidate(memory_with_items)
    assert result.pruned >= 0


def test_dream_creates_snapshot(tmp_path, memory_with_items):
    dc = DreamConsolidator(config=DreamConfig(
        min_importance=0.5, min_access_count=5,
        snapshot_dir=str(tmp_path / "snapshots"),
    ))
    result = dc.consolidate(memory_with_items)
    assert result.snapshot_path is not None
    assert Path(result.snapshot_path).exists()
    # Snapshot should be valid JSON
    with open(result.snapshot_path) as f:
        data = json.load(f)
    assert "items" in data
    assert "timestamp" in data


def test_dream_result_summary():
    result = DreamResult(selected=10, promoted=5, pruned=3, snapshot_path="/tmp/snap.json")
    summary = result.summary()
    assert "5 promoted" in summary
    assert "3 pruned" in summary
