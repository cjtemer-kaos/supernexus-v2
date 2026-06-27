"""Tests para prompter_knowledge.py — knowledge base estática (13 templates + 37 patterns)."""
from __future__ import annotations

import pytest

from gemas_core.workers import prompter_knowledge as pk


# ============================================================
# Metadata
# ============================================================

def test_kb_version():
    assert pk.KB_VERSION == "1.6.0"
    assert "nidhinjs/prompt-master" in pk.KB_SOURCE
    assert pk.KB_LICENSE == "MIT"


def test_categories_complete():
    expected = ("task", "context", "format", "scope", "reasoning", "agentic")
    assert pk.CATEGORIES == expected


def test_kb_metadata_counts():
    meta = pk.get_kb_metadata()
    assert meta["version"] == "1.6.0"
    assert meta["template_count"] == 13
    assert meta["pattern_count"] == 37
    assert len(meta["template_ids"]) == 13
    assert sum(meta["patterns_by_category"].values()) == 37


def test_patterns_by_category_distribution():
    # Distribución documentada en references/patterns.md
    expected = {"task": 7, "context": 6, "format": 6,
                "scope": 6, "reasoning": 5, "agentic": 7}
    assert pk.get_kb_metadata()["patterns_by_category"] == expected


# ============================================================
# Templates (A-M)
# ============================================================

def test_list_templates_has_13_ids():
    ids = pk.list_templates()
    assert len(ids) == 13
    assert ids == sorted(ids)  # A, B, C, ... M


def test_all_templates_have_required_fields():
    for tid, t in pk.TEMPLATES.items():
        assert "name" in t, f"template {tid} missing name"
        assert "full_name" in t, f"template {tid} missing full_name"
        assert "best_for" in t, f"template {tid} missing best_for"
        assert "fields" in t, f"template {tid} missing fields"
        assert "template" in t, f"template {tid} missing template"
        assert "example" in t, f"template {tid} missing example"
        assert len(t["fields"]) >= 1
        assert len(t["template"]) > 10


def test_get_template_by_id():
    t = pk.get_template("A")
    assert t is not None
    assert t["name"] == "RTF"
    assert "Role" in t["template"]


def test_get_template_case_insensitive():
    assert pk.get_template("a")["name"] == "RTF"
    assert pk.get_template("rtf")["name"] == "RTF"
    assert pk.get_template("RTF")["name"] == "RTF"


def test_get_template_unknown_returns_none():
    assert pk.get_template("Z") is None
    assert pk.get_template("") is None
    assert pk.get_template("nope") is None


def test_template_m_is_opus_47_brief():
    t = pk.get_template("M")
    assert t is not None
    assert "Opus 4.7" in t["full_name"] or "Opus" in t["full_name"]
    assert "Acceptance Criteria" in t["template"]


def test_template_h_has_stop_conditions():
    t = pk.get_template("H")
    assert "Stop Conditions" in t["template"]


def test_template_g_is_file_scope():
    t = pk.get_template("G")
    assert "File:" in t["template"]
    assert "Scope" in t["template"]


# ============================================================
# Patterns (37)
# ============================================================

def test_list_patterns_all_categories():
    all_p = pk.list_patterns()
    assert len(all_p) == 37


def test_list_patterns_single_category():
    task_patterns = pk.list_patterns(category="task")
    assert len(task_patterns) == 7
    assert all(p["id"] in range(1, 8) for p in task_patterns)


def test_list_patterns_invalid_category_returns_empty():
    assert pk.list_patterns(category="invalid") == []


def test_all_patterns_have_required_fields():
    for cat in pk.CATEGORIES:
        for p in pk.PATTERNS[cat]:
            assert "id" in p
            assert "name" in p
            assert "description" in p
            assert "before" in p
            assert "after" in p
            assert p["id"] in range(1, 38)


def test_pattern_ids_unique_and_sequential():
    seen = set()
    for cat in pk.CATEGORIES:
        for p in pk.PATTERNS[cat]:
            assert p["id"] not in seen, f"duplicate id {p['id']}"
            seen.add(p["id"])
    assert seen == set(range(1, 38))


def test_get_pattern_by_id():
    p = pk.get_pattern_by_id(1)
    assert p is not None
    assert p["name"] == "vague_task_verb"
    assert p["category"] == "task"

    p37 = pk.get_pattern_by_id(37)
    assert p37 is not None
    assert p37["name"] == "context_rot_long_sessions"
    assert p37["category"] == "agentic"


def test_get_pattern_by_id_invalid():
    assert pk.get_pattern_by_id(0) is None
    assert pk.get_pattern_by_id(38) is None
    assert pk.get_pattern_by_id(-1) is None


# ============================================================
# Detection heuristics
# ============================================================

def test_detect_pattern_empty_text():
    assert pk.detect_pattern("") == []
    assert pk.detect_pattern("   ") == []


def test_detect_pattern_matches_vague_verb():
    matches = pk.detect_pattern("help me with my code")
    names = [m["name"] for m in matches]
    assert "vague_task_verb" in names


def test_detect_pattern_matches_implicit_reference():
    matches = pk.detect_pattern("now add the other thing we discussed")
    names = [m["name"] for m in matches]
    assert "implicit_reference" in names


def test_detect_pattern_filtered_by_category():
    matches = pk.detect_pattern("help me with my code", category="task")
    assert all(m["category"] == "task" for m in matches)


def test_detect_pattern_enriches_matched_keywords():
    matches = pk.detect_pattern("help me with my code")
    assert matches
    for m in matches:
        assert "matched_keywords" in m
        assert isinstance(m["matched_keywords"], list)
        assert len(m["matched_keywords"]) > 0


# ============================================================
# Tool detection
# ============================================================

def test_detect_target_tool_claude_code():
    assert pk.detect_target_tool("Write me a prompt for Claude Code to build a REST API") == "claude_code"


def test_detect_target_tool_cursor():
    assert pk.detect_target_tool("Generate a Cursor prompt for refactoring auth") == "cursor"


def test_detect_target_tool_midjourney():
    assert pk.detect_target_tool("Make me a Midjourney prompt for cyberpunk samurai") == "midjourney"


def test_detect_target_tool_stable_diffusion():
    assert pk.detect_target_tool("Build a Stable Diffusion SDXL prompt for landscape") == "stable_diffusion"


def test_detect_target_tool_ollama():
    assert pk.detect_target_tool("I'm using ollama with llama 3") == "ollama"


def test_detect_target_tool_unknown_returns_auto():
    assert pk.detect_target_tool("Do something cool") == "auto"


def test_detect_target_tool_empty():
    assert pk.detect_target_tool("") == "auto"


# ============================================================
# Reasoning model detection
# ============================================================

@pytest.mark.parametrize("model", [
    "o1", "o1-mini", "o3", "o3-mini", "o4-mini",
    "deepseek-r1:8b", "deepseek r1",
    "qwen3", "qwen 3 thinking",
    "minimax-m3", "minimax thinking",
])
def test_is_reasoning_model_true(model):
    assert pk.is_reasoning_model(model) is True


@pytest.mark.parametrize("model", [
    "gemma4:latest", "qwen2.5-coder:7b", "llama3", "mistral",
    "claude-3-5-sonnet", "gpt-4o",
])
def test_is_reasoning_model_false(model):
    assert pk.is_reasoning_model(model) is False


def test_is_reasoning_model_empty():
    assert pk.is_reasoning_model("") is False
    assert pk.is_reasoning_model(None) is False  # type: ignore[arg-type]


# ============================================================
# format_with_template
# ============================================================

def test_format_with_template_basic():
    out = pk.format_with_template(
        "A", role="expert", task="write doc", format="markdown"
    )
    assert "expert" in out
    assert "write doc" in out
    assert "markdown" in out


def test_format_with_template_missing_field_keeps_placeholder():
    out = pk.format_with_template("A", role="expert")
    assert "expert" in out
    # task and format no provistos -> quedan como [task] y [format]
    assert "[task]" in out
    assert "[format]" in out


def test_format_with_template_unknown():
    out = pk.format_with_template("Z", task="x")
    assert "unknown template" in out


def test_format_with_template_by_name():
    out = pk.format_with_template("rtf", role="x", task="y", format="z")
    assert "x" in out
    assert "y" in out
    assert "z" in out


# ============================================================
# pick_template_for
# ============================================================

def test_pick_template_for_claude_code_returns_H():
    assert pk.pick_template_for("claude_code", "build a REST API") == "H"


def test_pick_template_for_cursor_returns_G():
    assert pk.pick_template_for("cursor", "refactor auth") == "G"


def test_pick_template_for_midjourney_returns_I():
    assert pk.pick_template_for("midjourney", "samurai") == "I"


def test_pick_template_for_comfyui_returns_K():
    assert pk.pick_template_for("comfyui", "landscape") == "K"


def test_pick_template_for_short_task_returns_A():
    # short input sin tool claro
    assert pk.pick_template_for("auto", "fix bug") == "A"


def test_pick_template_for_long_task_returns_C():
    long_task = " ".join(["word"] * 50)
    assert pk.pick_template_for("auto", long_task) == "C"


def test_pick_template_for_default_returns_B():
    # medium length, no tool
    medium = " ".join(["word"] * 15)
    assert pk.pick_template_for("auto", medium) == "B"


def test_pick_template_for_opus_47_returns_M():
    assert pk.pick_template_for("auto", "fix this on opus 4.7 please") == "M"


# ============================================================
# get_knowledge_summary
# ============================================================

def test_knowledge_summary_contains_all_template_names():
    summary = pk.get_knowledge_summary()
    for tid, t in pk.TEMPLATES.items():
        assert t["name"] in summary
        assert tid in summary


def test_knowledge_summary_contains_all_categories():
    summary = pk.get_knowledge_summary()
    for cat in pk.CATEGORIES:
        assert cat in summary


def test_knowledge_summary_has_version():
    summary = pk.get_knowledge_summary()
    assert "v1.6.0" in summary
    assert "MIT" in summary
