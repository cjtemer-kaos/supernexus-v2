"""Brain: Health — checks de salud de subsistemas core de NEXUS.

El director consulta este modulo para saber que subsistemas estan vivos.
SystemManager usa estos como `health_check_fn` de cada capability.

Design:
    HealthBrain recibe el director como owner y consulta sus atributos.
    Cada check devuelve bool, sin nunca lanzar excepciones — degrada
    gracefully a False si algo falta.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict


# Umbral minimo de gemas para considerar el sistema "saludable"
MIN_GEMAS_FOR_HEALTHY: int = 21


class HealthBrain:
    """Checks de salud de los subsistemas principales."""

    def __init__(self, owner: Any):
        """
        Args:
            owner: el Director — espera atributos como ai_tools, sessions,
                gemas, provider_registry. Todos opcionales (default False).
        """
        self.owner = owner

    # ── Individual checks (compatible con director._health_*) ───────────

    def check_core(self) -> bool:
        """Sistema base operativo (ai_tools + sessions disponibles)."""
        return hasattr(self.owner, "ai_tools") and hasattr(self.owner, "sessions")

    def check_memory(self) -> bool:
        """Bases de memoria accesibles (nexus_memory.db responde)."""
        nexus_brain = Path.home() / ".nexus" / "brain"
        if not nexus_brain.exists():
            return False
        try:
            db_path = nexus_brain / "nexus_memory.db"
            if not db_path.exists():
                return False
            conn = sqlite3.connect(str(db_path), timeout=2.0)
            try:
                conn.execute("SELECT 1")
            finally:
                conn.close()
            return True
        except Exception:
            return False

    def check_gemas(self) -> bool:
        """Gemas cargadas (>= umbral minimo)."""
        gemas = getattr(self.owner, "gemas", {}) or {}
        return len(gemas) >= MIN_GEMAS_FOR_HEALTHY

    def check_providers(self) -> bool:
        """Al menos un proveedor LLM registrado (ollama por defecto)."""
        registry = getattr(self.owner, "provider_registry", None)
        if registry is None:
            return False
        try:
            return registry.get("ollama") is not None
        except Exception:
            return False

    # ── Aggregate ───────────────────────────────────────────────────────

    def check_all(self) -> Dict[str, bool]:
        """Snapshot de todos los checks."""
        return {
            "core": self.check_core(),
            "memory": self.check_memory(),
            "gemas": self.check_gemas(),
            "providers": self.check_providers(),
        }

    def summary(self) -> Dict[str, Any]:
        """Resumen numerico para /api/status."""
        checks = self.check_all()
        healthy = sum(1 for v in checks.values() if v)
        return {
            "healthy": healthy,
            "total": len(checks),
            "all_healthy": healthy == len(checks),
            "checks": checks,
        }
