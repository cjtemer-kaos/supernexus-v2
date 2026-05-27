"""
Cache stress test for ToolUniverse.

This script repeatedly calls a real built-in tool (Tool_Finder_Keyword) with
different argument combinations to benchmark cache behaviour under load. It
reports timing statistics for first-time executions versus cached hits, along
with the final cache state.

Usage:
    python examples/cache_stress_test.py --iterations 200 --seed 42
"""

from __future__ import annotations

import argparse
import os
import random
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault("TOOLUNIVERSE_LIGHT_IMPORT", "1")

from tooluniverse import ToolUniverse


QUERY_POOL = [
    "drug discovery pipeline",
    "literature search cancer",
    "clinical trial adverse events",
    "gene expression atlas",
    "protein structure 3d",
    "uniprot annotations",
    "fda drug warnings",
    "metabolomics enrichment",
    "genomics england evidence",
    "semantic scholar publications",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stress test ToolUniverse cache.")
    parser.add_argument(
        "--iterations",
        type=int,
        default=int(os.environ.get("CACHE_STRESS_ITERATIONS", "120")),
        help="Number of tool calls to issue (default: 120 or CACHE_STRESS_ITERATIONS)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible sequences",
    )
    parser.add_argument(
        "--cache-path",
        type=str,
        default=None,
        help="Optional custom cache path (overrides TOOLUNIVERSE_CACHE_PATH)",
    )
    return parser.parse_args()


def configure_cache(cache_path: str | None):
    if cache_path:
        path = Path(cache_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        os.environ["TOOLUNIVERSE_CACHE_PATH"] = str(path)
    else:
        if "TOOLUNIVERSE_CACHE_PATH" in os.environ:
            return
        default_dir = Path.cwd() / ".tooluniverse_cache"
        default_dir.mkdir(parents=True, exist_ok=True)
        os.environ["TOOLUNIVERSE_CACHE_PATH"] = str(default_dir / "stress_cache.sqlite")


def main():
    args = parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    configure_cache(args.cache_path)

    tu = ToolUniverse()

    durations_by_key = defaultdict(list)
    call_counter = Counter()

    total_calls = args.iterations
    print(f"Running {total_calls} iterations against Tool_Finder_Keyword (use_cache=True)")

    for i in range(1, total_calls + 1):
        query = random.choice(QUERY_POOL)
        limit = random.choice([3, 5, 7, 10])
        key = (query, limit)

        start = time.time()
        tu.run_one_function(
            {
                "name": "Tool_Finder_Keyword",
                "arguments": {"description": query, "limit": limit},
            },
            use_cache=True,
        )
        elapsed = time.time() - start

        durations_by_key[key].append(elapsed)
        call_counter[key] += 1

        if i % max(1, total_calls // 10) == 0:
            print(f"  Progress: {i}/{total_calls} calls complete")

    tu_stats = tu.get_cache_stats()
    tu.close()

    first_call_times = []
    cached_call_times = []
    for timings in durations_by_key.values():
        if timings:
            first_call_times.append(timings[0])
            cached_call_times.extend(timings[1:])

    unique_requests = len(durations_by_key)
    cache_hits = total_calls - unique_requests

    print("\n=== Cache Stress Test Summary ===")
    print(f"Total calls issued      : {total_calls}")
    print(f"Unique argument combos  : {unique_requests}")
    print(f"Cache hits (est.)       : {cache_hits} ({cache_hits / total_calls:.1%})")
    print(f"Cache misses (est.)     : {unique_requests} ({unique_requests / total_calls:.1%})")

    if first_call_times:
        print(
            f"Average first-call time : {statistics.mean(first_call_times):.3f}s "
            f"(median {statistics.median(first_call_times):.3f}s)"
        )
    if cached_call_times:
        print(
            f"Average cached time     : {statistics.mean(cached_call_times):.3f}s "
            f"(median {statistics.median(cached_call_times):.3f}s)"
        )

    most_common = call_counter.most_common(5)
    if most_common:
        print("\nTop queries:")
        for (query, limit), count in most_common:
            print(f"  '{query}' (limit {limit}) -> {count} calls")

    print("\nCache backend stats:")
    print(tu_stats)


if __name__ == "__main__":
    main()
