"""Benchmark ToolUniverse batch execution vs sequential execution.

This script registers a lightweight CountingTool and measures the runtime of
single-call execution (looping through run_one_function) against the batch-aware
ToolUniverse.run for the same number of invocations. It also supports toggling
cache usage and parallel workers to explore the performance trade-offs.
"""

from __future__ import annotations

import argparse
import inspect
import os
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Iterable, List

# Allow running directly from the repo without installing the package
SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if SRC_ROOT.exists():
    sys.path.insert(0, str(SRC_ROOT))

os.environ.setdefault("TOOLUNIVERSE_LIGHT_IMPORT", "1")

from tooluniverse import ToolUniverse
from tooluniverse.base_tool import BaseTool


class CountingTool(BaseTool):
    """Simple tool that increments an internal counter each run."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.count = 0
        self.delay_range = tool_config.get("delay_range")

    def run(self, arguments=None, **kwargs):
        self.count += 1
        value = arguments.get("value", 0) if arguments else 0
        if self.delay_range:
            low, high = self.delay_range
            if high > 0:
                time.sleep(random.uniform(low, high))
        return {"value": value, "count": self.count}


def _register_counting_tool(
    engine: ToolUniverse,
    cacheable: bool,
    delay_range: tuple[float, float] | None,
) -> None:
    tool_config = {
        "name": "CountingTool",
        "type": "CountingTool",
        "description": "Benchmark helper tool",
        "cacheable": cacheable,
        "delay_range": delay_range,
        "parameter": {
            "type": "object",
            "properties": {"value": {"type": "integer"}},
            "required": ["value"],
        },
    }
    engine.register_custom_tool(CountingTool, tool_config=tool_config)


def _build_calls(num_calls: int, duplicates: int) -> List[dict]:
    """Create a list of function calls with optional duplicates."""
    calls: List[dict] = []
    for i in range(num_calls):
        value = i % duplicates if duplicates else i
        calls.append({"name": "CountingTool", "arguments": {"value": value}})
    return calls


def _time_call(fn, *, warmup: int, repeats: int) -> List[float]:
    """Warm up and time repeated executions of the callable."""
    for _ in range(warmup):
        fn()
    timings: List[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        timings.append(time.perf_counter() - start)
    return timings


def _print_stats(label: str, timings: Iterable[float]) -> None:
    timings = list(timings)
    print(
        f"{label}: mean={statistics.mean(timings):.4f}s "
        f"(stdev={statistics.pstdev(timings):.4f}s, min={min(timings):.4f}s, max={max(timings):.4f}s)"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calls", type=int, default=200, help="Total number of tool calls to execute")
    parser.add_argument(
        "--duplicates",
        type=int,
        default=0,
        help="Number of unique argument sets to cycle through (0 means all unique)",
    )
    parser.add_argument("--cache", action="store_true", help="Enable ToolUniverse result caching")
    parser.add_argument("--max-workers", type=int, default=8, help="Parallel worker count for batch execution")
    parser.add_argument("--min-delay", type=float, default=0.0, help="Minimum simulated delay per tool call (seconds)")
    parser.add_argument("--max-delay", type=float, default=0.0, help="Maximum simulated delay per tool call (seconds)")
    parser.add_argument(
        "--mode",
        choices=("both", "batch", "sequential"),
        default="both",
        help="Which benchmark(s) to run",
    )
    parser.add_argument("--warmup", type=int, default=1, help="Number of warmup runs for each benchmark")
    parser.add_argument("--repeats", type=int, default=3, help="Number of timed runs for each benchmark")
    args = parser.parse_args()

    print("=== ToolUniverse Batch vs Sequential Benchmark ===")
    print(
        f"calls={args.calls}, duplicates={args.duplicates}, cache={args.cache}, "
        f"max_workers={args.max_workers}, delay=({args.min_delay}, {args.max_delay}), mode={args.mode}"
    )

    delay_range = None
    if args.max_delay > 0:
        delay_range = (max(0.0, args.min_delay), max(args.min_delay, args.max_delay))

    # Keep default tools disabled to avoid heavy imports.
    tu = ToolUniverse(tool_files={}, keep_default_tools=False)
    _register_counting_tool(tu, cacheable=args.cache, delay_range=delay_range)

    calls = _build_calls(args.calls, args.duplicates)

    def run_sequential():
        for call in calls:
            tu.run_one_function(call, use_cache=args.cache)

    def run_batch():
        try:
            run_sig = inspect.signature(tu.run)
        except (ValueError, TypeError):
            run_sig = None
        run_kwargs = {}
        if run_sig is None or "use_cache" in run_sig.parameters:
            run_kwargs["use_cache"] = args.cache
        if run_sig is None or "max_workers" in run_sig.parameters:
            run_kwargs["max_workers"] = args.max_workers
        tu.run(calls, **run_kwargs)

    seq_timings = []
    batch_timings = []

    if args.mode in ("both", "sequential"):
        seq_timings = _time_call(run_sequential, warmup=args.warmup, repeats=args.repeats)
        _print_stats("Sequential", seq_timings)

    if args.mode in ("both", "batch"):
        batch_timings = _time_call(run_batch, warmup=args.warmup, repeats=args.repeats)
        _print_stats("Batch", batch_timings)

    if args.mode == "both":
        speedups = [s / b for s, b in zip(seq_timings, batch_timings)]
        print(
            "Speedup (Sequential/Batch): "
            f"mean={statistics.mean(speedups):.2f}x, min={min(speedups):.2f}x, max={max(speedups):.2f}x"
        )


if __name__ == "__main__":
    main()
