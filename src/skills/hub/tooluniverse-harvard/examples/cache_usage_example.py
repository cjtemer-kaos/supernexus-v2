"""
ToolUniverse cache usage example.

This script is meant to be read like documentation: it walks you through the
steps required to enable result caching, execute a tool twice with caching
enabled, inspect cache statistics, and dump/clear persisted entries. Each
section contains inline comments explaining the idea behind the code so you
can adapt it to your own project quickly.
"""

import os
from pathlib import Path
import time

os.environ.setdefault("TOOLUNIVERSE_LIGHT_IMPORT", "1")

from tooluniverse import ToolUniverse
from tooluniverse.base_tool import BaseTool


class DemoCacheTool(BaseTool):
    """Minimal tool that increments a counter each time it's executed."""

    call_count = 0
    STATIC_CACHE_VERSION = "1"

    def run(self, arguments, **kwargs):
        DemoCacheTool.call_count += 1
        value = arguments.get("value", 0)
        time.sleep(2.0)  # Simulate expensive work (visible delay)
        return {"value": value, "calls": DemoCacheTool.call_count}


def main():
    # ------------------------------------------------------------------
    # 1. Configure caching behavior.
    #
    # ToolUniverse turns caching on by default, but here we explicitly set
    # environment variables so readers can see the knobs:
    #   - TOOLUNIVERSE_CACHE_PATH: where persisted results live.
    #   - TOOLUNIVERSE_CACHE_ENABLED: toggles caching globally.
    #   - TOOLUNIVERSE_CACHE_PERSIST: enables the SQLite layer.
    # ------------------------------------------------------------------
    cache_dir = Path(os.environ.get("TOOLUNIVERSE_CACHE_DIR", Path.home() / ".tooluniverse"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TOOLUNIVERSE_CACHE_PATH", str(cache_dir / "example_cache.sqlite"))
    os.environ.setdefault("TOOLUNIVERSE_CACHE_ENABLED", "true")
    os.environ.setdefault("TOOLUNIVERSE_CACHE_PERSIST", "true")

    # ------------------------------------------------------------------
    # 2. Create a ToolUniverse instance and register our custom tool.
    #
    # By default ToolUniverse loads hundreds of predefined tools; to keep the
    # demo focused we pass tool_files={}, keep_default_tools=False so only the
    # DemoCacheTool exists.
    # ------------------------------------------------------------------
    tu = ToolUniverse(tool_files={}, keep_default_tools=False)
    tu.register_custom_tool(
        DemoCacheTool,
        tool_config={
            "name": "DemoCacheTool",
            "type": "DemoCacheTool",
            "description": "Simple tool to demonstrate caching.",
            "parameter": {
                "type": "object",
                "properties": {"value": {"type": "integer"}},
                "required": ["value"],
            },
        },
    )

    def call_tool(value: int):
        """Helper that runs the tool with caching enabled."""
        return tu.run_one_function(
            {"name": "DemoCacheTool", "arguments": {"value": value}},
            use_cache=True,
        )

    # ------------------------------------------------------------------
    # 3. Call the tool twice. The first invocation executes run(), the second
    #    retrieves the same payload from the cache (notice the counter stays 1).
    # ------------------------------------------------------------------
    print("First call (computes result)...")
    DemoCacheTool.call_count = 0
    start = time.time()
    result1 = call_tool(10)
    elapsed1 = time.time() - start
    print(result1)
    print(f"Elapsed time: {elapsed1:.2f} s")

    print("Second call with same arguments (cache hit)...")
    start = time.time()
    result2 = call_tool(10)
    elapsed2 = time.time() - start
    print(result2)
    print(f"Elapsed time: {elapsed2:.2f} s")

    print("Cache stats:")
    print(tu.get_cache_stats())

    # ------------------------------------------------------------------
    # 4. Dump cached entries. When persistence is enabled this shows the
    #    serialized payload, metadata, and hit counts stored on disk.
    # ------------------------------------------------------------------
    print("Dumping cached entries (persistent layer)...")
    for entry in tu.dump_cache():
        print(entry)

    # ------------------------------------------------------------------
    # 5. Clear everything and show stats again so you know how to reset the
    #    cache from your application or tests.
    # ------------------------------------------------------------------
    print("Clearing cache...")
    tu.clear_cache()
    print(tu.get_cache_stats())

    tu.close()


if __name__ == "__main__":
    main()
