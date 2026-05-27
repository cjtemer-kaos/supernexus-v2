# tests/test_memory_triage.py
import pytest
from src.core.memory_triage import MemoryTriage, TriageResult, TriageGate


def test_trivial_message_rejected():
    triage = MemoryTriage()
    result = triage.evaluate("ok thanks")
    assert result.passed is False
    assert result.rejected_by == TriageGate.FUTURE_UTILITY


def test_valuable_message_passes():
    triage = MemoryTriage()
    result = triage.evaluate(
        "Circuit breaker pattern: open/half-open/closed states with exponential backoff for resilient architecture"
    )
    assert result.passed is True
    assert result.score > 2.0


def test_novelty_gate_rejects_duplicate():
    triage = MemoryTriage()
    triage.register_known("NEXUS uses SQLite pattern for memory cache and storage API")
    result = triage.evaluate("NEXUS uses SQLite pattern for memory cache and storage API")
    assert result.passed is False
    assert result.rejected_by == TriageGate.NOVELTY


def test_novelty_gate_accepts_new_info():
    triage = MemoryTriage()
    triage.register_known("NEXUS uses SQLite pattern for memory cache and storage API")
    result = triage.evaluate("Redis cache can be used as a concurrent distributed message broker with pub/sub pattern for async architecture and api design")
    assert result.passed is True


def test_safety_gate_catches_secrets():
    triage = MemoryTriage()
    result = triage.evaluate("The API key is sk-1234567890abcdef and password is hunter2 database security design")
    assert result.passed is False
    assert result.rejected_by == TriageGate.SAFETY


def test_safety_gate_catches_pii():
    triage = MemoryTriage()
    result = triage.evaluate("User database schema design SSN: 123-45-6789 credit card 4111-1111-1111-1111 security leak pattern")
    assert result.passed is False
    assert result.rejected_by == TriageGate.SAFETY


def test_factual_gate_low_confidence():
    triage = MemoryTriage()
    result = triage.evaluate("maybe perhaps I think this api pattern could possibly be a cache implementation design")
    assert result.factual_confidence < 0.5


def test_triage_returns_score():
    triage = MemoryTriage()
    result = triage.evaluate(
        "asyncio.gather runs coroutines concurrently and returns results in order"
    )
    assert 0 <= result.score <= 10
    assert isinstance(result.gates_passed, list)


def test_batch_evaluate():
    triage = MemoryTriage()
    results = triage.batch_evaluate([
        "ok", "thanks", "Circuit breaker uses 3 states for fault tolerance in async distributed architecture",
    ])
    assert len(results) == 3
    assert results[0].passed is False  # trivial
    assert results[2].passed is True   # valuable
