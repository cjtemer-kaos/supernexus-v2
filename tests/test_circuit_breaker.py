import pytest
import time
from src.core.circuit_breaker import CircuitBreaker, CircuitState, HealthChecker


def test_starts_closed():
    cb = CircuitBreaker(name="test")
    assert cb.state == CircuitState.CLOSED
    assert cb.can_call() is True


def test_opens_after_failures():
    cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout_s=999)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.can_call() is False


def test_half_open_after_timeout():
    cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout_s=0.01)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    time.sleep(0.02)
    assert cb.can_call() is True
    assert cb.state == CircuitState.HALF_OPEN


def test_closes_on_success_in_half_open():
    cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout_s=0.01)
    cb.record_failure()
    time.sleep(0.02)
    cb.can_call()  # transitions to HALF_OPEN
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_health_check_healthy():
    hc = HealthChecker()
    cb = CircuitBreaker(name="agent-a", failure_threshold=3)
    hc.add_breaker(cb)
    result = hc.check_agent("agent-a", healthy=True)
    assert result["healthy"] == 1
    assert result["unhealthy"] == 0


def test_health_check_unhealthy():
    hc = HealthChecker()
    cb = CircuitBreaker(name="agent-b", failure_threshold=2)
    hc.add_breaker(cb)
    hc.check_agent("agent-b", healthy=False)
    hc.check_agent("agent-b", healthy=False)
    assert cb.state == CircuitState.OPEN


def test_checker_status():
    hc = HealthChecker()
    hc.add_breaker(CircuitBreaker(name="cb1"))
    hc.add_breaker(CircuitBreaker(name="cb2"))
    status = hc.status()
    assert len(status["breakers"]) == 2
    assert status["breakers"]["cb1"]["state"] == "closed"
