# tests/test_pointer_store.py
import pytest
import tempfile
import os
import time
from pathlib import Path
from src.core.pointer_store import PointerStore, Pointer


def test_small_content_passes_through():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = PointerStore(storage_dir=tmpdir)
        result = store.maybe_store("small content", source="test")
        assert result is None  # not stored, content is small


def test_large_content_stored_to_disk():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = PointerStore(storage_dir=tmpdir, threshold_bytes=100)
        large = "x" * 200
        pointer = store.maybe_store(large, source="test-output")
        assert pointer is not None
        assert isinstance(pointer, Pointer)
        assert os.path.exists(pointer.path)
        assert pointer.size_bytes == 200


def test_pointer_retrieve():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = PointerStore(storage_dir=tmpdir, threshold_bytes=50)
        content = "important data " * 10  # >50 bytes
        pointer = store.maybe_store(content, source="test")
        retrieved = store.retrieve(pointer.id)
        assert retrieved == content


def test_pointer_placeholder():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = PointerStore(storage_dir=tmpdir, threshold_bytes=50)
        content = "a" * 100
        pointer = store.maybe_store(content, source="analysis")
        placeholder = pointer.placeholder()
        assert "[POINTER:" in placeholder
        assert "100 bytes" in placeholder
        assert pointer.id in placeholder


def test_cleanup_old_pointers():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = PointerStore(storage_dir=tmpdir, threshold_bytes=50, max_age_hours=0)
        content = "b" * 100
        pointer = store.maybe_store(content, source="test")
        time.sleep(0.02)  # ensure created_at < cutoff on Windows
        cleaned = store.cleanup()
        assert cleaned >= 1
        assert not os.path.exists(pointer.path)


def test_list_pointers():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = PointerStore(storage_dir=tmpdir, threshold_bytes=50)
        store.maybe_store("c" * 100, source="a")
        store.maybe_store("d" * 100, source="b")
        pointers = store.list_pointers()
        assert len(pointers) == 2
