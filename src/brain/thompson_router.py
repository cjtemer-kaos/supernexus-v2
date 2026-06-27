"""
thompson_router — Multi-armed bandit LLM tier router (Thompson sampling).

Pattern (ruflo): each model arm carries Beta(α, β) priors. On pick:
draw θ ~ Beta(α, β) per arm, pick argmax (probability-matching).
On outcome: α += success_units, β += failure_units. Cost-aware via
unit weighting (cheap success → +1.0, expensive success → +0.5, etc).

Why over static thresholds: routing self-corrects to the actually-best
model for each gem under THIS user's prompt distribution, without manual
tuning. 50 outcomes is usually enough to converge.

Persisted to ~/.nexus/brain/router_state.json (atomic_io). Survives
restart.
"""
from __future__ import annotations

import json
import logging
import random
import threading
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

STATE_PATH = Path.home() / ".nexus" / "brain" / "router_state.json"


@dataclass
class Arm:
    model: str
    alpha: float = 1.0   # successes + 1 (Beta prior)
    beta: float = 1.0    # failures + 1
    picks: int = 0
    last_outcome_at: Optional[str] = None


@dataclass
class ArmGroup:
    gem: str
    arms: Dict[str, Arm] = field(default_factory=dict)


def _beta_sample(a: float, b: float) -> float:
    """Sample Beta(a,b) via two Gamma samples (random.gammavariate).
    Stable for typical a,b ≥ 1 we'll see here."""
    x = random.gammavariate(a, 1.0)
    y = random.gammavariate(b, 1.0)
    return x / (x + y) if (x + y) > 0 else 0.5


class ThompsonRouter:
    def __init__(self):
        self._groups: Dict[str, ArmGroup] = {}
        self._lock = threading.Lock()
        self._dirty = False
        self.load()

    # --- persistence ---

    def load(self):
        if not STATE_PATH.exists():
            return
        try:
            raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            for gem, gdata in (raw or {}).items():
                arms = {m: Arm(**a) for m, a in gdata.get("arms", {}).items()}
                self._groups[gem] = ArmGroup(gem=gem, arms=arms)
        except Exception as e:
            logger.warning(f"thompson_router: load failed: {e}")

    def save(self):
        try:
            from src.security.atomic_io import atomic_write_json
            data = {
                gem: {"arms": {m: asdict(a) for m, a in g.arms.items()}}
                for gem, g in self._groups.items()
            }
            atomic_write_json(STATE_PATH, data, mode=0o644)
            self._dirty = False
        except Exception as e:
            logger.warning(f"thompson_router: save failed: {e}")

    # --- registry ---

    def register(self, gem: str, models: List[str]) -> None:
        """Add any new models to the gem's arm group (existing arms untouched)."""
        with self._lock:
            g = self._groups.setdefault(gem, ArmGroup(gem=gem))
            for m in models:
                if m not in g.arms:
                    g.arms[m] = Arm(model=m)
                    self._dirty = True
        if self._dirty:
            self.save()

    # --- routing ---

    def pick(self, gem: str, candidates: Optional[List[str]] = None) -> Optional[str]:
        """Sample θ per arm, return argmax. None if gem unknown / no arms."""
        with self._lock:
            g = self._groups.get(gem)
            if g is None or not g.arms:
                if candidates:
                    # autoregister + return first
                    self.register(gem, candidates)
                    return candidates[0]
                return None
            arms = (
                [g.arms[m] for m in candidates if m in g.arms]
                if candidates else list(g.arms.values())
            )
            if not arms:
                return None
            best_arm, best_score = None, -1.0
            for a in arms:
                s = _beta_sample(max(0.001, a.alpha), max(0.001, a.beta))
                if s > best_score:
                    best_score = s
                    best_arm = a
            if best_arm:
                best_arm.picks += 1
                self._dirty = True
            return best_arm.model if best_arm else None

    # --- outcomes ---

    def record(self, gem: str, model: str, success: bool,
               weight: float = 1.0) -> None:
        """Update Beta(α,β). weight ∈ (0, 1] — use lower for expensive
        models so an expensive success is less rewarding than a cheap one."""
        from datetime import datetime
        with self._lock:
            g = self._groups.setdefault(gem, ArmGroup(gem=gem))
            a = g.arms.setdefault(model, Arm(model=model))
            w = max(0.05, min(1.0, weight))
            if success:
                a.alpha += w
            else:
                a.beta += w
            a.last_outcome_at = datetime.now().isoformat()
            self._dirty = True
        # Periodic flush
        if random.random() < 0.1:
            self.save()

    # --- introspection ---

    def stats(self) -> Dict:
        out = {}
        with self._lock:
            for gem, g in self._groups.items():
                rows = []
                for m, a in g.arms.items():
                    mean = a.alpha / (a.alpha + a.beta)
                    rows.append({
                        "model": m, "picks": a.picks,
                        "alpha": round(a.alpha, 2), "beta": round(a.beta, 2),
                        "mean": round(mean, 3),
                        "last_outcome_at": a.last_outcome_at,
                    })
                rows.sort(key=lambda r: r["mean"], reverse=True)
                out[gem] = rows
        return out


# Module singleton
router = ThompsonRouter()
