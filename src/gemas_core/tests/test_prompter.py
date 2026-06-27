"""Tests para PrompterGem — worker de prompt engineering."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from gemas_core.workers.prompter import PrompterGem


# ============================================================
# Instantiation + to_dict
# ============================================================

def test_prompter_instantiation_no_ollama():
    g = PrompterGem()
    assert g.ollama is None
    assert g.history == []


def test_prompter_instantiation_with_ollama():
    mock = MagicMock()
    g = PrompterGem(ollama_client=mock)
    assert g.ollama is mock


def test_prompter_name_and_category():
    g = PrompterGem()
    assert g.name == "prompter"
    assert g.category == "core"


def test_prompter_to_dict():
    g = PrompterGem()
    d = g.to_dict()
    assert d["id"] == "prompter"
    assert d["type"] == "dedicated"
    assert d["ollama_configured"] is False
    assert d["knowledge_base"]["template_count"] == 13
    assert d["knowledge_base"]["pattern_count"] == 37


def test_prompter_to_dict_with_ollama():
    g = PrompterGem(ollama_client=MagicMock())
    d = g.to_dict()
    assert d["ollama_configured"] is True


# ============================================================
# detect_tool (public wrapper)
# ============================================================

def test_prompter_detect_tool():
    g = PrompterGem()
    assert g.detect_tool("for Cursor refactor") == "cursor"
    assert g.detect_tool("for Claude Code") == "claude_code"
    assert g.detect_tool("no tool here") == "auto"


# ============================================================
# execute (static analysis, no Ollama)
# ============================================================

def test_prompter_execute_minimal():
    g = PrompterGem()
    r = asyncio.run(g.execute("Write me a prompt for Cursor to refactor auth"))
    assert r["success"] is True
    assert r["gema"] == "PrompterGem"
    assert r["target_tool"] == "cursor"
    assert r["template_id"] == "G"  # File-Scope para IDE AI
    assert r["template"] == "File-Scope"
    assert "File:" in r["template_structure"]
    assert r["filled_prompt"]
    assert isinstance(r["audit_trail"], list)
    assert len(r["audit_trail"]) >= 5  # 7 steps + intermediate
    assert r["timestamp"]


def test_prompter_execute_midjourney():
    g = PrompterGem()
    r = asyncio.run(g.execute("Make a Midjourney prompt for cyberpunk samurai"))
    assert r["target_tool"] == "midjourney"
    assert r["template_id"] == "I"  # Visual Descriptor


def test_prompter_execute_claude_code():
    g = PrompterGem()
    r = asyncio.run(g.execute("Build a Claude Code prompt for REST API"))
    assert r["target_tool"] == "claude_code"
    assert r["template_id"] == "H"  # ReAct+Stop


def test_prompter_execute_target_tool_override():
    g = PrompterGem()
    # sin 'midjourney' en el texto, pero forzamos target_tool
    r = asyncio.run(g.execute("Make me a prompt", target_tool="midjourney"))
    assert r["target_tool"] == "midjourney"
    assert r["template_id"] == "I"


def test_prompter_execute_no_tool_detected():
    g = PrompterGem()
    r = asyncio.run(g.execute("do something"))
    assert r["target_tool"] == "auto"
    assert r["warnings"]
    assert any("tool" in w.lower() for w in r["warnings"])


def test_prompter_execute_detected_patterns():
    g = PrompterGem()
    r = asyncio.run(g.execute("help me with my code, no success criteria, totally broken"))
    pattern_names = [p["name"] for p in r["detected_patterns"]]
    # 'help me with my code' es pattern 1
    assert "vague_task_verb" in pattern_names


def test_prompter_execute_kb_metadata_included():
    g = PrompterGem()
    r = asyncio.run(g.execute("anything"))
    assert r["kb_metadata"]["template_count"] == 13
    assert r["kb_metadata"]["pattern_count"] == 37


def test_prompter_execute_warning_for_reasoning_model_cot():
    g = PrompterGem()
    # Chain of Thought template + modelo nativo de razonamiento
    r = asyncio.run(g.execute(
        "Use chain of thought with deepseek-r1 for math problem"
    ))
    assert any("Pattern 27" in w or "CoT" in w for w in r["warnings"])


# ============================================================
# optimize (with Ollama)
# ============================================================

def test_prompter_optimize_without_client_returns_static():
    g = PrompterGem()  # no ollama_client
    r = asyncio.run(g.optimize("Write me a prompt for Cursor"))
    assert r["success"] is True
    assert r["refined_prompt"] is None
    assert r["ollama_used"] is False
    assert "ollama_client" in r.get("note", "")


def test_prompter_optimize_with_mock_client():
    g = PrompterGem()
    mock_client = MagicMock()
    # ollama-python style async chat returns dict with message.content
    fake_response = {
        "message": {"role": "assistant", "content": "Here's your optimized prompt..."}
    }

    async def fake_chat(**kwargs):
        return fake_response

    mock_client.chat = fake_chat

    r = asyncio.run(g.optimize(
        "Write me a prompt for Cursor to refactor auth",
        ollama_client=mock_client,
    ))
    assert r["success"] is True
    assert r["ollama_used"] is True
    assert r["refined_prompt"] == "Here's your optimized prompt..."
    assert r["ollama_model"]


def test_prompter_optimize_with_sync_generate():
    g = PrompterGem()
    mock_client = MagicMock()
    fake_response = {"response": "Generated prompt text"}

    def fake_generate(**kwargs):
        return fake_response

    mock_client.generate = fake_generate
    # Remove chat attr to force generate path
    del mock_client.chat

    r = asyncio.run(g.optimize(
        "Write a prompt", ollama_client=mock_client,
    ))
    assert r["ollama_used"] is True
    assert r["refined_prompt"] == "Generated prompt text"


def test_prompter_optimize_uses_injected_client_over_self():
    """Si se pasa client en optimize(), sobrescribe self.ollama."""
    g = PrompterGem(ollama_client=MagicMock())  # self.ollama será ignorado
    injected = MagicMock()

    async def fake_chat(**kwargs):
        return {"message": {"content": "injected response"}}

    injected.chat = fake_chat

    r = asyncio.run(g.optimize("task", ollama_client=injected))
    assert r["ollama_used"] is True
    assert r["refined_prompt"] == "injected response"


def test_prompter_optimize_ollama_failure_does_not_break():
    g = PrompterGem()
    mock_client = MagicMock()
    mock_client.chat.side_effect = RuntimeError("ollama down")

    r = asyncio.run(g.optimize("task", ollama_client=mock_client))
    # Static analysis is still valid, refined_prompt is None
    assert r["success"] is True
    assert r["refined_prompt"] is None
    assert r["ollama_used"] is False
    assert "ollama_error" in r
    assert "ollama down" in r["ollama_error"]


def test_prompter_optimize_appends_to_history():
    g = PrompterGem()
    asyncio.run(g.optimize("task 1"))
    asyncio.run(g.optimize("task 2"))
    assert len(g.history) == 2


# ============================================================
# _extract_dimensions (internal)
# ============================================================

def test_extract_dimensions_role_detection():
    dims = PrompterGem._extract_dimensions("senior engineer needed")
    assert dims["role"] == "senior"


def test_extract_dimensions_audience_detection():
    dims = PrompterGem._extract_dimensions("for technical developer users")
    assert "technical" in dims["audience"]
    assert "developer" in dims["audience"]


def test_extract_dimensions_length_classification():
    short = PrompterGem._extract_dimensions("fix bug")
    medium = PrompterGem._extract_dimensions(" ".join(["word"] * 50))
    long_ = PrompterGem._extract_dimensions(" ".join(["word"] * 200))
    assert short["length"] == "short"
    assert medium["length"] == "medium"
    assert long_["length"] == "long"


def test_extract_dimensions_format_hints():
    dims = PrompterGem._extract_dimensions("return json with markdown formatting")
    assert "json" in dims["format_hints"]
    assert "markdown" in dims["format_hints"]


# ============================================================
# _compose_filled_prompt
# ============================================================

def test_compose_filled_prompt_template_A():
    g = PrompterGem()
    out = g._compose_filled_prompt(
        task="write doc", context="",
        dimensions={"role": "expert", "format_hints": []},
        template_id="A",
    )
    assert "expert" in out
    assert "write doc" in out


def test_compose_filled_prompt_template_H():
    g = PrompterGem()
    out = g._compose_filled_prompt(
        task="build API", context="empty project",
        dimensions={"role": "developer", "format_hints": []},
        template_id="H",
    )
    assert "build API" in out
    assert "empty project" in out
    assert "Stop Conditions" in out


def test_compose_filled_prompt_template_G():
    g = PrompterGem()
    out = g._compose_filled_prompt(
        task="refactor login", context="src/auth/login.ts",
        dimensions={"role": "developer", "format_hints": []},
        template_id="G",
    )
    assert "src/auth/login.ts" in out
    assert "refactor login" in out


def test_compose_filled_prompt_unknown_template():
    g = PrompterGem()
    out = g._compose_filled_prompt(
        task="anything", context="", dimensions={}, template_id="X"
    )
    # fallback returns the task itself
    assert "anything" in out


# ============================================================
# _build_ollama_system_prompt
# ============================================================

def test_ollama_system_prompt_includes_kb():
    g = PrompterGem()
    analysis = asyncio.run(g.execute("for Cursor refactor"))
    sp = g._build_ollama_system_prompt(analysis)
    assert "PROMPTER KNOWLEDGE BASE" in sp
    assert "13 templates" in sp
    assert "37 credit-killing patterns" in sp
    assert "DETECTED TOOL: cursor" in sp
    assert "RECOMMENDED TEMPLATE: G" in sp


def test_ollama_user_message_includes_task():
    g = PrompterGem()
    analysis = {"target_tool": "cursor", "template_id": "G",
                "detected_patterns": [], "warnings": []}
    msg = g._build_ollama_user_message("refactor auth", "src/auth.ts", analysis)
    assert "refactor auth" in msg
    assert "src/auth.ts" in msg
    assert "cursor" in msg


# ============================================================
# _call_ollama
# ============================================================

def test_call_ollama_with_sync_generate():
    mock_client = MagicMock()
    mock_client.generate.return_value = {"response": "out"}
    # Remove chat to force generate path
    if hasattr(mock_client, "chat"):
        del mock_client.chat
    out = asyncio.run(PrompterGem._call_ollama(
        mock_client, "sys", "user", "model"
    ))
    assert out == "out"


def test_call_ollama_with_async_chat():
    mock_client = MagicMock()

    async def fake_chat(**kwargs):
        return {"message": {"content": "async out"}}

    mock_client.chat = fake_chat
    out = asyncio.run(PrompterGem._call_ollama(
        mock_client, "sys", "user", "model"
    ))
    assert out == "async out"


def test_call_ollama_raises_for_bad_client():
    class BadClient:
        pass
    with pytest.raises(RuntimeError):
        asyncio.run(PrompterGem._call_ollama(BadClient(), "sys", "user", "m"))


# ============================================================
# Integration with builders (prompter is now dedicated)
# ============================================================

def test_prompter_loaded_by_build_standard_gemas():
    from pathlib import Path
    from gemas_core.builders import build_standard_gemas
    # Use the real manifests dir (not tmp_path, which would be empty)
    project_root = Path(__file__).resolve().parents[3]
    gemas_dir = project_root / "data" / "gemas"
    gemas = build_standard_gemas(gemas_dir=gemas_dir)
    assert "prompter" in gemas
    assert isinstance(gemas["prompter"], PrompterGem)
    # Total: 6 dedicated + 18 role = 24 (v1.6.0: +1 web_research)
    assert len(gemas) == 24
    # Verify 'prompter' is loaded as PrompterGem (not the legacy role-LLM)
    assert type(gemas["prompter"]).__name__ == "PrompterGem"
