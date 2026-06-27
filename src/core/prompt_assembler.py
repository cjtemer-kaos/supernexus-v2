"""
Prompt Assembler - Three-tier prompt assembly with caching.
Absorbed from hermes-agent — names cleaned.
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PromptAssembler:
    """Three-tier prompt assembly: stable + context + volatile."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path(os.environ.get("APP_DATA", Path.home() / ".app")) / "prompts"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, str] = {}
        self._cache_hash: Optional[str] = None
        self._snapshot_file = self.data_dir / ".prompt_snapshot.json"

    def build_system_prompt(
        self,
        identity: str = "",
        tool_guidance: str = "",
        skills: str = "",
        environment: str = "",
        context_files: str = "",
        system_message: str = "",
        memory_snapshot: str = "",
        user_context: str = "",
        timestamp: str = "",
        session_info: str = "",
    ) -> str:
        """Build system prompt in three tiers for cache friendliness."""
        stable_parts = []
        if identity:
            stable_parts.append(identity)
        if tool_guidance:
            stable_parts.append(tool_guidance)
        if skills:
            stable_parts.append(skills)
        if environment:
            stable_parts.append(environment)

        context_parts = []
        if context_files:
            context_parts.append(context_files)
        if system_message:
            context_parts.append(system_message)

        volatile_parts = []
        if memory_snapshot:
            volatile_parts.append(memory_snapshot)
        if user_context:
            volatile_parts.append(user_context)
        if timestamp:
            volatile_parts.append(f"Current time: {timestamp}")
        if session_info:
            volatile_parts.append(session_info)

        stable = "\n\n".join(stable_parts)
        context = "\n\n".join(context_parts)
        volatile = "\n\n".join(volatile_parts)

        full = "\n\n".join(p for p in (stable, context, volatile) if p)

        self._cache_hash = hashlib.sha256(full.encode()).hexdigest()[:16]
        self._cache["full"] = full
        self._cache["stable"] = stable
        self._cache["context"] = context
        self._cache["volatile"] = volatile

        return full

    def get_cached(self) -> Optional[str]:
        return self._cache.get("full")

    def invalidate(self):
        self._cache.clear()
        self._cache_hash = None

    def save_snapshot(self):
        snapshot = {
            "hash": self._cache_hash,
            "timestamp": time.time(),
            "stable_length": len(self._cache.get("stable", "")),
            "context_length": len(self._cache.get("context", "")),
        }
        self._snapshot_file.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    def load_snapshot(self) -> Optional[Dict]:
        if self._snapshot_file.exists():
            try:
                return json.loads(self._snapshot_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None

    def validate_prompt(self, prompt: str, max_length: int = 100000) -> tuple:
        """Validate assembled prompt. Returns (ok, reason)."""
        if not prompt:
            return False, "Empty prompt"
        if len(prompt) > max_length:
            return False, f"Prompt too long ({len(prompt)} > {max_length})"
        return True, "ok"

    def get_stats(self) -> Dict:
        return {
            "cached": bool(self._cache),
            "hash": self._cache_hash,
            "stable_size": len(self._cache.get("stable", "")),
            "context_size": len(self._cache.get("context", "")),
            "volatile_size": len(self._cache.get("volatile", "")),
        }
