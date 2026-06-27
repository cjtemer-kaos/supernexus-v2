"""Tests para gemas_core.builders: build_standard_gemas + IDs."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from gemas_core.builders import (
    build_standard_gemas,
    list_standard_dedicated_ids,
    list_standard_role_ids,
    list_all_standard_ids,
)
from gemas_core.base import GemaBase


@pytest.fixture
def gemas_dir(tmp_path: Path) -> Path:
    """Crea 4 manifests dedicados + 3 role-LLM en data/gemas/."""
    d = tmp_path / "data" / "gemas"
    d.mkdir(parents=True)

    dedicated_names = ("ayuda", "scholar", "sage", "biblioteca")
    for n in dedicated_names:
        (d / f"{n}.json").write_text(
            json.dumps({"name": n, "model": "x", "description": n}),
            encoding="utf-8",
        )
    for n in ("code", "architect", "tester"):
        (d / f"{n}.json").write_text(
            json.dumps({"name": n, "model": "x", "description": n}),
            encoding="utf-8",
        )
    return d


def test_list_standard_dedicated_ids():
    ids = list_standard_dedicated_ids()
    assert "ayuda" in ids
    assert "scholar" in ids
    assert "sage" in ids
    assert "biblioteca" in ids
    assert "prompter" in ids  # v1.1.0: promoted to dedicated
    assert "web_research" in ids  # v1.6.0: RUFUS primitives → gem
    assert len(ids) == 6


def test_list_standard_role_ids():
    ids = list_standard_role_ids()
    assert "code" in ids
    assert "architect" in ids
    assert "vision" in ids
    assert "prompter" not in ids  # v1.1.0: moved to dedicated
    assert len(ids) == 18


def test_list_all_standard_ids():
    ids = list_all_standard_ids()
    # v1.6.0: 6 dedicated + 18 role = 24
    assert len(ids) == 24
    assert set(list_standard_dedicated_ids()).issubset(set(ids))
    assert set(list_standard_role_ids()).issubset(set(ids))


def test_build_standard_gemas_loads_dedicated_and_role(gemas_dir: Path):
    gemas = build_standard_gemas(gemas_dir)
    # 4 dedicated (overridden) + 3 role from fixtures
    assert "ayuda" in gemas
    assert "scholar" in gemas
    assert "sage" in gemas
    assert "biblioteca" in gemas
    assert "code" in gemas
    assert "architect" in gemas
    assert "tester" in gemas
    # Dedicated gemas should be GemaBase subclasses, not LLMRoleGema
    from gemas_core.workers.ayuda import AyudaGem
    assert isinstance(gemas["ayuda"], AyudaGem)


def test_build_standard_gemas_dedicated_overrides_manifest(gemas_dir: Path):
    gemas = build_standard_gemas(gemas_dir)
    # 'ayuda' manifest exists but should be overridden by AyudaGem
    from gemas_core.workers.ayuda import AyudaGem
    from gemas_core.llm_role_gema import LLMRoleGema
    assert isinstance(gemas["ayuda"], AyudaGem)
    assert not isinstance(gemas["ayuda"], LLMRoleGema)
    # 'code' has no dedicated worker, so should be LLMRoleGema
    assert isinstance(gemas["code"], LLMRoleGema)


def test_build_standard_gemas_custom_workers_module(gemas_dir: Path):
    """Si se pasa un workers_module custom, se usa ese en vez del estándar."""
    class CustomAyuda(GemaBase):
        name = "ayuda"
        async def execute(self, task, context=""):
            return {"success": True, "gema": "custom_ayuda", "task": task}

    custom_workers = MagicMock()
    custom_workers.AyudaGem = CustomAyuda
    custom_workers.ScholarGem = None  # Missing — should be skipped
    custom_workers.SageGem = None
    custom_workers.BibliotecaGem = None

    gemas = build_standard_gemas(gemas_dir, workers_module=custom_workers)
    assert isinstance(gemas["ayuda"], CustomAyuda)
    # 'scholar' is not in custom_workers and should fall through to manifest
    # (but our fixture HAS a scholar.json manifest, so it'll be loaded as role)
    assert "scholar" in gemas


def test_build_standard_gemas_empty_dir(tmp_path: Path):
    gemas = build_standard_gemas(tmp_path / "nonexistent")
    # Should still have 4 dedicated (from default workers)
    assert "ayuda" in gemas
    assert "scholar" in gemas
    assert "sage" in gemas
    assert "biblioteca" in gemas
    # No role-LLM since no manifests
    assert "code" not in gemas
