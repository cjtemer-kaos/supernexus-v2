"""NexusApp — service container. Each feature is an isolated service.

Pattern from opencode-go. Replaces the DirectorNexus monolith with composition
of services behind explicit interfaces.

Create a service: dataclass that receives what it needs in __init__.
Register it: app.register("memory", MemoryService(config))
Consume it: app.get("memory").search_observations(...)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class Service(Protocol):
    """Interface that all services must implement."""

    async def initialize(self) -> None: ...

    async def shutdown(self) -> None: ...

    def healthcheck(self) -> bool: ...


@dataclass
class NexusApp:
    """Service container / registry.

    Services are registered by name and initialized in registration order.
    Shutdown happens in reverse registration order.
    """

    project: str = "default"
    config: Dict[str, Any] = field(default_factory=dict)
    _services: Dict[str, Service] = field(default_factory=dict)

    def register(self, name: str, service: Service) -> None:
        if name in self._services:
            raise ValueError(f"service '{name}' already registered")
        self._services[name] = service

    def get(self, name: str) -> Service:
        if name not in self._services:
            raise KeyError(
                f"service '{name}' not registered. Available: {list(self._services)}"
            )
        return self._services[name]

    def get_optional(self, name: str) -> Optional[Service]:
        return self._services.get(name)

    def has(self, name: str) -> bool:
        return name in self._services

    async def initialize_all(self) -> Dict[str, bool]:
        results = {}
        for name, svc in self._services.items():
            try:
                await svc.initialize()
                results[name] = True
            except Exception as e:
                logger.exception(f"service '{name}' init failed: {e}")
                results[name] = False
        return results

    async def shutdown_all(self) -> None:
        for name in reversed(list(self._services)):
            try:
                await self._services[name].shutdown()
            except Exception:
                logger.exception(f"service '{name}' shutdown failed")

    def health_report(self) -> Dict[str, bool]:
        return {name: svc.healthcheck() for name, svc in self._services.items()}
