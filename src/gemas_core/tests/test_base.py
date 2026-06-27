"""Tests para gemas_core.base: GemaManifest + ManifestSchema."""
import json
import pytest
from pathlib import Path

from gemas_core.base import GemaManifest, ManifestSchema, GemaBase


def test_manifest_from_dict_minimal():
    m = GemaManifest.from_dict({"name": "code"})
    assert m.name == "code"
    assert m.model == ManifestSchema.DEFAULT_MODEL
    assert m.description == ""
    assert m.system_prompt == ""
    assert m.keywords == []
    assert m.category == "general"


def test_manifest_from_dict_full():
    data = {
        "name": "code",
        "model": "qwen2.5-coder:7b",
        "description": "Code review",
        "systemPrompt": "You are a code reviewer.",
        "semanticKeywords": ["code", "review"],
        "category": "code",
    }
    m = GemaManifest.from_dict(data)
    assert m.name == "code"
    assert m.model == "qwen2.5-coder:7b"
    assert m.system_prompt == "You are a code reviewer."
    assert m.keywords == ["code", "review"]
    assert m.category == "code"


def test_manifest_from_dict_missing_name():
    with pytest.raises(ValueError, match="missing required field 'name'"):
        GemaManifest.from_dict({"model": "x"})


def test_manifest_from_file(tmp_path: Path):
    p = tmp_path / "code.json"
    p.write_text(json.dumps({"name": "code", "model": "qwen"}), encoding="utf-8")
    m = GemaManifest.from_file(p)
    assert m.name == "code"
    assert m.model == "qwen"
    assert m.source_path == p


def test_manifest_to_dict_roundtrip():
    m = GemaManifest.from_dict({"name": "x", "description": "test"})
    d = m.to_dict()
    assert d["name"] == "x"
    assert d["description"] == "test"


def test_manifest_schema_required_field():
    assert ManifestSchema.FIELD_NAME in ManifestSchema.REQUIRED


def test_gema_base_is_abstract():
    with pytest.raises(TypeError):
        GemaBase()  # type: ignore


def test_gema_base_subclass_must_implement_execute():
    class BadGema(GemaBase):
        pass

    with pytest.raises(TypeError):
        BadGema()  # type: ignore
