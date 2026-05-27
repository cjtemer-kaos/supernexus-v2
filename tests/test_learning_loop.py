import pytest
from src.core.learning_loop import LearningLoop, LearningResult, LearningStrategy


def test_learning_strategy_detection():
    loop = LearningLoop()
    strategy = loop.detect_strategy("implementar circuit breaker")
    assert strategy in (LearningStrategy.SEARCH_WEB, LearningStrategy.SEARCH_REPOS,
                        LearningStrategy.SEARCH_SKILLS, LearningStrategy.SEARCH_BRAIN)


def test_knowledge_gap_detection():
    loop = LearningLoop()
    loop.register_known("code", "refactor", "test", "debug")
    assert loop.has_gap("implementar websockets con QUIC protocol") is True
    assert loop.has_gap("refactorizar un modulo") is False


def test_learning_result_creation():
    result = LearningResult(
        query="circuit breaker pattern",
        strategy=LearningStrategy.SEARCH_WEB,
        found=True,
        knowledge="Circuit breaker: open/half-open/closed states...",
        source="web:martinfowler.com",
        new_capability="circuit-breaker",
    )
    assert result.found is True
    assert result.new_capability == "circuit-breaker"


def test_known_capabilities_expansion():
    loop = LearningLoop()
    loop.register_known("code", "test")
    assert loop.has_gap("write code") is False
    loop.learn_capability("websocket")
    assert loop.has_gap("implementar websocket server") is False
