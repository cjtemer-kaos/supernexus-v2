# tests/test_perplexity_scorer.py
import pytest
from src.core.perplexity_scorer import PerplexityScorer


def test_high_info_density():
    scorer = PerplexityScorer()
    score = scorer.score("asyncio.gather runs coroutines concurrently using an event loop with cooperative multitasking")
    assert score > 0.6  # high information density


def test_low_info_density():
    scorer = PerplexityScorer()
    score = scorer.score("ok ok ok ok ok ok ok")
    assert score < 0.3  # low information density


def test_code_has_high_density():
    scorer = PerplexityScorer()
    score = scorer.score("def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)")
    assert score > 0.7


def test_repetitive_has_low_density():
    scorer = PerplexityScorer()
    score = scorer.score("the the the the cat cat cat sat sat sat on on on the the the mat mat mat")
    assert score < 0.45


def test_rank_messages_by_density():
    scorer = PerplexityScorer()
    messages = [
        {"role": "user", "content": "ok"},
        {"role": "assistant", "content": "Circuit breakers prevent cascading failures in distributed systems by monitoring error rates"},
        {"role": "user", "content": "yes yes sure"},
    ]
    ranked = scorer.rank_by_density(messages)
    assert ranked[0]["content"].startswith("Circuit")  # highest density first


def test_score_returns_bounded():
    scorer = PerplexityScorer()
    assert 0.0 <= scorer.score("anything at all") <= 1.0
    assert 0.0 <= scorer.score("") <= 1.0
