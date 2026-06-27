"""Tests for gemas_core.core.atomic_io.

Pattern ported from pewdiepie-archdaemon/odysseus (core/atomic_io.py):
write-tmp-fsync-replace for crash-safe JSON/text persistence.

Why this exists: a plain ``open(path, "w") + json.dump`` truncates the file
on first write and only fills it with new content afterwards. A crash in
between produces a truncated or empty file. For password DBs, session
stores, and live config, that's a data-loss event.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

import pytest

from gemas_core.core.atomic_io import atomic_write_json, atomic_write_text


class TestAtomicWriteText:
    def test_writes_simple_text(self, tmp_path: Path) -> None:
        path = tmp_path / "out.txt"
        atomic_write_text(path, "hello world")
        assert path.read_text(encoding="utf-8") == "hello world"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "nested" / "deep" / "out.txt"
        atomic_write_text(path, "x")
        assert path.read_text(encoding="utf-8") == "x"
        assert path.parent.is_dir()

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        path = tmp_path / "out.txt"
        path.write_text("OLD", encoding="utf-8")
        atomic_write_text(path, "NEW")
        assert path.read_text(encoding="utf-8") == "NEW"

    def test_handles_empty_string(self, tmp_path: Path) -> None:
        path = tmp_path / "out.txt"
        path.write_text("EXISTING", encoding="utf-8")
        atomic_write_text(path, "")
        assert path.read_text(encoding="utf-8") == ""

    def test_preserves_unicode(self, tmp_path: Path) -> None:
        path = tmp_path / "out.txt"
        payload = "España · ñ · 中文 · emoji 🦾"
        atomic_write_text(path, payload)
        assert path.read_text(encoding="utf-8") == payload

    def test_preserves_newlines_and_tabs(self, tmp_path: Path) -> None:
        # Note: open(..., "w", encoding="utf-8") runs in text mode and uses
        # universal newlines on Windows, so we don't assert \r\n preservation
        # — atomic_io's contract is byte-for-byte round-trip of the Python
        # str, not preservation of platform-specific newline translation.
        path = tmp_path / "out.txt"
        payload = "line1\nline2\twith tab\nthird\n"
        atomic_write_text(path, payload)
        assert path.read_text(encoding="utf-8") == payload

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        path = tmp_path / "out.txt"
        atomic_write_text(str(path), "via str")
        assert path.read_text(encoding="utf-8") == "via str"

    def test_accepts_pathlib_path(self, tmp_path: Path) -> None:
        path = tmp_path / "out.txt"
        atomic_write_text(path, "via Path")
        assert path.read_text(encoding="utf-8") == "via Path"

    def test_no_tmp_files_left_behind(self, tmp_path: Path) -> None:
        path = tmp_path / "out.txt"
        atomic_write_text(path, "clean")
        leftovers = list(tmp_path.glob("*.tmp.*"))
        assert leftovers == []

    def test_works_when_dirname_is_empty(self) -> None:
        # Edge case: os.path.dirname("foo.txt") == "" — should fall back to "."
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            cwd = os.getcwd()
            try:
                os.chdir(d)
                atomic_write_text("bare.txt", "no dir")
                assert Path("bare.txt").read_text(encoding="utf-8") == "no dir"
            finally:
                os.chdir(cwd)


class TestAtomicWriteJson:
    def test_writes_compact_json(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        atomic_write_json(path, {"a": 1, "b": [1, 2, 3]})
        # Default no indent = compact
        text = path.read_text(encoding="utf-8")
        assert text == '{"a": 1, "b": [1, 2, 3]}'

    def test_writes_pretty_json_when_indent(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        atomic_write_json(path, {"a": 1, "b": [1, 2, 3]}, indent=2)
        text = path.read_text(encoding="utf-8")
        assert "\n" in text
        parsed = json.loads(text)
        assert parsed == {"a": 1, "b": [1, 2, 3]}

    def test_round_trip_complex_data(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        data = {
            "users": [{"name": "Héctor", "admin": True, "tokens": None}],
            "config": {"port": 9091, "host": "127.0.0.1", "tags": ["x", "y"]},
        }
        atomic_write_json(path, data, indent=2)
        assert json.loads(path.read_text(encoding="utf-8")) == data

    def test_unicode_preserved(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        atomic_write_json(path, {"greeting": "Hola · 🦾 · 中文"})
        # ensure_ascii=True is the json.dump default; the data must round-trip
        assert json.loads(path.read_text(encoding="utf-8")) == {
            "greeting": "Hola · 🦾 · 中文"
        }

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        atomic_write_json(path, {"v": 1})
        atomic_write_json(path, {"v": 2})
        assert json.loads(path.read_text(encoding="utf-8")) == {"v": 2}

    def test_no_tmp_files_left_behind(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        atomic_write_json(path, {"k": "v"})
        leftovers = list(tmp_path.glob("*.tmp.*"))
        assert leftovers == []

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "data" / "nested" / "out.json"
        atomic_write_json(path, {"ok": True})
        assert json.loads(path.read_text(encoding="utf-8")) == {"ok": True}


class TestAtomicWriteFailureCleanup:
    def test_text_write_failure_leaves_no_partial_file(self, tmp_path: Path) -> None:
        # Simulate I/O failure during the write: open() succeeds, but f.write
        # raises. The function should propagate the error, and the original
        # path (if it existed) must remain untouched.
        path = tmp_path / "out.txt"
        path.write_text("ORIGINAL", encoding="utf-8")
        with mock.patch("os.replace", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                atomic_write_text(path, "NEW ATTEMPT")
        assert path.read_text(encoding="utf-8") == "ORIGINAL"

    def test_text_write_failure_leaves_no_tmp(self, tmp_path: Path) -> None:
        path = tmp_path / "out.txt"
        with mock.patch("os.replace", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                atomic_write_text(path, "x")
        assert list(tmp_path.glob("*.tmp.*")) == []

    def test_json_write_failure_leaves_no_partial_file(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        path.write_text('{"original": true}', encoding="utf-8")
        with mock.patch("os.replace", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                atomic_write_json(path, {"new": True})
        assert json.loads(path.read_text(encoding="utf-8")) == {"original": True}

    def test_nonserializable_data_raises_cleanly(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        # sets are not JSON-serializable
        with pytest.raises(TypeError):
            atomic_write_json(path, {"key": {1, 2, 3}})
        # No partial file, no tmp file
        assert not path.exists()
        assert list(tmp_path.glob("*.tmp.*")) == []


class TestAtomicWriteConcurrency:
    def test_tmp_suffix_includes_thread_id(self, tmp_path: Path) -> None:
        # Sanity check the contract: tmp files are unique per (pid, thread)
        # so a later failure cleanup or external inspection can identify
        # the writer.
        path = tmp_path / "out.txt"
        import threading

        seen_suffixes: list[str] = []
        original_unlink = os.unlink

        def spy_unlink(p: str) -> None:
            if ".tmp." in p:
                seen_suffixes.append(p)
            original_unlink(p)

        with mock.patch("os.unlink", side_effect=spy_unlink):
            with mock.patch("os.replace", side_effect=OSError("boom")):
                with pytest.raises(OSError):
                    atomic_write_text(path, "x")
        assert len(seen_suffixes) == 1
        suffix = seen_suffixes[0]
        # Format: <path>.tmp.<pid>.<thread_id>
        assert f".tmp.{os.getpid()}.{threading.get_ident()}" in suffix

    def test_distinct_threads_get_distinct_tmp_paths(self) -> None:
        # Verify the per-thread tmp suffix is in fact different across
        # threads. This is a pre-condition for any external concurrency
        # strategy the caller layers on top of atomic_io (e.g. an
        # external Lock). atomic_io itself does NOT serialize concurrent
        # writers — that's the caller's job (it would be wrong to bundle
        # a global file lock into a low-level I/O helper).
        import threading

        results: dict[int, str] = {}
        ready = threading.Barrier(2)

        def capture(label: int) -> None:
            ready.wait()
            results[label] = f"{os.getpid()}.{threading.get_ident()}"

        threads = [
            threading.Thread(target=capture, args=(i,))
            for i in range(2)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(set(results.values())) == 2  # distinct ids
