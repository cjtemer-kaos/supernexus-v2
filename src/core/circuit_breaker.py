"""
Circuit Breaker + Health Checks for agent/services reliability.
"""
from __future__ import annotations
import asyncio, logging, time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    recovery_timeout_s: float = 30.0
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0
    success_count: int = 0

    def record_success(self) -> None:
        self.success_count += 1
        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"CircuitBreaker '{self.name}': closed on success in half-open")
            self.state = CircuitState.CLOSED
            self.failure_count = 0

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"CircuitBreaker '{self.name}': OPEN after {self.failure_count} failures")

    def can_call(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if (time.time() - self.last_failure_time) >= self.recovery_timeout_s:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"CircuitBreaker '{self.name}': HALF_OPEN after timeout")
                return True
            return False
        # HALF_OPEN — allow one call
        return True

    def reset(self) -> None:
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        logger.info(f"CircuitBreaker '{self.name}': reset to CLOSED")

    def to_dict(self) -> dict:
        return {
            "name": self.name, "state": self.state.value,
            "failure_count": self.failure_count, "failure_threshold": self.failure_threshold,
            "recovery_timeout_s": self.recovery_timeout_s,
            "success_count": self.success_count,
        }

    async def call(self, fn: Callable[[], Awaitable[Any]]) -> Any:
        """Execute a function with circuit breaker protection."""
        if not self.can_call():
            raise RuntimeError(f"CircuitBreaker '{self.name}' is {self.state.value}")
        try:
            result = await fn()
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise


class HealthChecker:
    """Periodic health checks for agents and services."""

    def __init__(self):
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._checks: dict[str, dict] = {}

    def add_breaker(self, breaker: CircuitBreaker) -> None:
        self._circuit_breakers[breaker.name] = breaker

    def get_breaker(self, name: str) -> CircuitBreaker | None:
        return self._circuit_breakers.get(name)

    def check_agent(self, name: str, healthy: bool) -> dict:
        """Record a health check result for an agent."""
        if name not in self._checks:
            self._checks[name] = {"total": 0, "healthy": 0, "unhealthy": 0, "last_check": 0.0}
        self._checks[name]["total"] += 1
        self._checks[name]["last_check"] = time.time()
        if healthy:
            self._checks[name]["healthy"] += 1
        else:
            self._checks[name]["unhealthy"] += 1
            if name in self._circuit_breakers:
                self._circuit_breakers[name].record_failure()
        return self._checks[name]

    def run_all_checks(self) -> dict:
        """Run all registered circuit breaker checks."""
        results = {}
        for name, breaker in self._circuit_breakers.items():
            results[name] = {
                "state": breaker.state.value,
                "can_call": breaker.can_call(),
                "failures": breaker.failure_count,
            }
        return results

    def status(self) -> dict:
        return {
            "breakers": {n: b.to_dict() for n, b in self._circuit_breakers.items()},
            "checks": self._checks,
        }
