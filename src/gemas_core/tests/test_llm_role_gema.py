"""Tests para gemas_core.llm_role_gema: LLMRoleGema + load_all_role_gemas."""
import json
import pytest
from pathlib import Path

from gemas_core.llm_role_gema import LLMRoleGema, load_all_role_gemas


@pytest.fixture
def gemas_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data" / "gemas"
    d.mkdir(parents=True)
    (d / "code.json").write_text(
        json.dumps({
            "name": "code",
            "model": "qwen2.5-coder:7b",
            "description": "Code review",
            "systemPrompt": "You are a code reviewer.",
            "semanticKeywords": ["code", "review"],
            "category": "code",
        }),
        encoding="utf-8",
    )
    (d / "minimal.json").write_text(
        json.dumps({"name": "minimal"}),
        encoding="utf-8",
    )
    return d


def test_load_all_role_gemas(gemas_dir: Path):
    gemas = load_all_role_gemas(gemas_dir, ollama_url="http://localhost:1")
    assert "code" in gemas
    assert "minimal" in gemas
    assert len(gemas) == 2


def test_load_all_role_gemas_missing_dir(tmp_path: Path):
    gemas = load_all_role_gemas(tmp_path / "nonexistent")
    assert gemas == {}


def test_llm_role_gema_from_manifest(gemas_dir: Path):
    instance = LLMRoleGema(manifest_path=gemas_dir / "code.json")
    assert instance.name == "code"
    assert instance.model == "qwen2.5-coder:7b"
    assert instance.system_prompt == "You are a code reviewer."
    assert instance.keywords == ["code", "review"]
    assert instance.category == "code"


def test_llm_role_gema_minimal_builds_default_prompt(gemas_dir: Path):
    instance = LLMRoleGema(manifest_path=gemas_dir / "minimal.json")
    assert instance.name == "minimal"
    assert instance.system_prompt  # built by default
    assert "MINIMAL" in instance.system_prompt


def test_llm_role_gema_to_dict(gemas_dir: Path):
    instance = LLMRoleGema(manifest_path=gemas_dir / "code.json")
    d = instance.to_dict()
    assert d["id"] == "code"
    assert d["name"] == "CODE"
    assert d["type"] == "llm-role"
    assert d["has_system_prompt"] is True


def test_llm_role_gema_execute_ollama_unavailable(gemas_dir: Path):
    """Si Ollama no responde, execute retorna success=False con note."""
    instance = LLMRoleGema(
        manifest_path=gemas_dir / "code.json",
        ollama_url="http://127.0.0.1:1",
        timeout_s=2,
    )
    import asyncio
    result = asyncio.run(instance.execute("hello world"))
    assert result["success"] is False
    assert "ollama" in result.get("note", "").lower() or "error" in result


def test_llm_role_gema_ollama_url_strips_trailing_slash(gemas_dir: Path):
    instance = LLMRoleGema(
        manifest_path=gemas_dir / "code.json",
        ollama_url="http://127.0.0.1:11434/",
    )
    assert instance.ollama_url == "http://127.0.0.1:11434"
