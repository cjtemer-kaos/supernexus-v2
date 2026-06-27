"""Tests para gemas_core.manifest_schema: validate_manifest + constants."""

from gemas_core.manifest_schema import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    DEFAULT_TIMEOUT_S,
    REQUIRED_FIELDS,
    STANDARD_CATEGORIES,
    validate_manifest,
)


def test_defaults():
    assert DEFAULT_MODEL == "gemma4:latest"
    assert DEFAULT_OLLAMA_URL == "http://127.0.0.1:11434"
    assert DEFAULT_TIMEOUT_S == 120


def test_required_fields():
    assert "name" in REQUIRED_FIELDS


def test_standard_categories_includes_general():
    assert "general" in STANDARD_CATEGORIES
    assert "code" in STANDARD_CATEGORIES
    assert "research" in STANDARD_CATEGORIES


def test_validate_manifest_valid():
    errors = validate_manifest({"name": "code", "model": "qwen"})
    assert errors == []


def test_validate_manifest_minimal():
    errors = validate_manifest({"name": "x"})
    assert errors == []


def test_validate_manifest_missing_name():
    errors = validate_manifest({"model": "qwen"})
    assert any("name" in e for e in errors)


def test_validate_manifest_empty_name():
    errors = validate_manifest({"name": ""})
    assert any("name" in e for e in errors)


def test_validate_manifest_not_dict():
    errors = validate_manifest("not a dict")
    assert any("not a dict" in e for e in errors)


def test_validate_manifest_invalid_model():
    errors = validate_manifest({"name": "x", "model": ""})
    assert any("model" in e for e in errors)


def test_validate_manifest_invalid_keywords():
    errors = validate_manifest({"name": "x", "semanticKeywords": "not a list"})
    assert any("semanticKeywords" in e for e in errors)


def test_validate_manifest_keywords_must_be_strings():
    errors = validate_manifest({"name": "x", "semanticKeywords": [1, 2, 3]})
    assert any("semanticKeywords[0]" in e for e in errors)
