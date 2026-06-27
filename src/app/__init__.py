"""NexusApp — service container. Each feature is an isolated service.

Pattern from opencode-go. Replaces the DirectorNexus monolith with composition
of services behind explicit interfaces.

Create a service: dataclass that receives what it needs in __init__.
Register it: app.register("memory", MemoryService(config))
Consume it: app.get("memory").search_observations(...)
"""
from src.app.registry import NexusApp, Service

__all__ = ["NexusApp", "Service"]
