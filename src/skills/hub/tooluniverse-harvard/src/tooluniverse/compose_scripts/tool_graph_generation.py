"""Tool Graph Generation Compose Script

Efficiently evaluates directional data-flow relationships between all unique pairs
of provided tool configs using one agentic tool:
  - ToolRelationshipDetector

Outputs a graph structure with edges representing valid directional relationships.
Each edge stores: source, target, rationale.

Performance considerations:
  - Iterates i<j once (O(N^2/2) pairs)
  - Lightweight JSON serialization of minimal fields
  - Optional batching hook (currently sequential because call_tool likely remote)

Arguments:
  tool_configs (list[dict]) REQUIRED
  max_tools (int) optional limit for debugging
  output_path (str) path to write resulting graph JSON (default './tool_relationship_graph.json')
  save_intermediate_every (int) checkpoint frequency (default 5000 pairs processed)

Return:
  dict with keys: nodes, edges, stats
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List


DETECTOR_NAME = "ToolRelationshipDetector"


def compose(arguments, tooluniverse, call_tool):  # noqa: D401
    tool_configs: List[dict] = arguments.get("tool_configs") or []
    if not tool_configs:
        return {"status": "error", "message": "tool_configs empty"}

    max_tools = arguments.get("max_tools")
    if isinstance(max_tools, int) and max_tools > 0:
        tool_configs = tool_configs[:max_tools]

    output_path = arguments.get("output_path", "./tool_relationship_graph.json")
    checkpoint_every = int(arguments.get("save_intermediate_every", 5000))

    # Prepare nodes list (unique tool names)
    nodes = []
    minimal_tool_map: Dict[str, dict] = {}
    for cfg in tool_configs:
        name = cfg.get("name")
        if not name:
            continue
        if name in minimal_tool_map:
            continue
        minimal_tool = {
            "name": name,
            "description": cfg.get("description", ""),
            "parameter": cfg.get("parameter", {}),
            "type": cfg.get("type", cfg.get("toolType", "unknown")),
        }
        minimal_tool_map[name] = minimal_tool
        nodes.append({"id": name, "name": name, "type": minimal_tool["type"]})

    names = list(minimal_tool_map.keys())
    n = len(names)
    total_pairs = n * (n - 1) // 2

    edges: List[dict] = []
    processed_pairs = 0
    llm_calls = 0
    start_time = time.time()
    batch_size = 100

    # --- Resume from checkpoint ---
    checkpoint_path = output_path + ".checkpoint.json"
    load_path = None

    # Prefer checkpoint file, otherwise use the main output file
    if os.path.exists(checkpoint_path):
        load_path = checkpoint_path
    elif os.path.exists(output_path):
        load_path = output_path

    if load_path:
        print(f"Attempting to resume from {load_path}")
        try:
            with open(load_path, "r", encoding="utf-8") as f:
                existing_graph = json.load(f)

            # Re-hydrate edges and find processed source tools
            if "edges" in existing_graph and isinstance(existing_graph["edges"], list):
                edges = existing_graph["edges"]

            # Align the 'names' list order with the loaded graph to ensure correct loop continuation
            if "nodes" in existing_graph and isinstance(existing_graph["nodes"], list):
                loaded_node_order = [
                    node.get("name") for node in existing_graph.get("nodes", [])
                ]
                if names == loaded_node_order:
                    print("Current tool order matches the loaded graph.")
                else:
                    print(
                        "Reordering tools to match the loaded graph for correct resume."
                    )
                    # Create a map for quick lookup of current tool positions
                    current_name_pos = {name: i for i, name in enumerate(names)}
                    # Build the new 'names' list and 'minimal_tool_map' based on the loaded order
                    new_names = [
                        name for name in loaded_node_order if name in current_name_pos
                    ]
                    # Find any new tools not in the original graph and append them
                    new_tools_from_config = [
                        name for name in names if name not in loaded_node_order
                    ]
                    if new_tools_from_config:
                        print(
                            f"Appending {len(new_tools_from_config)} new tools to the list."
                        )
                        new_names.extend(new_tools_from_config)

                    names = new_names
                    assert n == len(names)  # n should remain the same
                    print("Tool order successfully realigned.")

        except Exception as e:
            print(
                f"Warning: Could not load or parse existing graph at {load_path}. Starting fresh. Error: {e}"
            )
            edges = []  # Reset edges if loading failed

    # Core loop over unique unordered pairs (i<j). We'll batch the 'j' tools.
    for i in range(n):
        tool_a = minimal_tool_map[names[i]]
        a_json = json.dumps(tool_a, ensure_ascii=False)
        # This logic is to skip all tools until a specific one is found,
        # skip that one, and then process all subsequent tools.
        # This is useful for debugging or resuming from a specific point.
        start_processing_flag_name = "get_em_3d_fitting_and_reconstruction_details"

        # Find the index of the tool to start after
        try:
            start_index = names.index(start_processing_flag_name)
        except ValueError:
            start_index = -1  # Flag tool not found, process all

        if start_index != -1 and i <= start_index:
            print(
                f"Skipping tool {tool_a['name']} with index {i} (target index is {start_index})."
            )
            continue

        # Batch the remaining tools to compare against tool_a
        for j_batch_start in range(i + 1, n, batch_size):
            j_batch_end = min(j_batch_start + batch_size, n)
            other_tools_batch_names = names[j_batch_start:j_batch_end]

            if not other_tools_batch_names:
                continue

            other_tools_list = [
                minimal_tool_map[name] for name in other_tools_batch_names
            ]
            other_tools_json = json.dumps(other_tools_list, ensure_ascii=False)

            # Call detector with the batch
            detector_args = {"tool_a": a_json, "other_tools": other_tools_json}
            detector_res = {}
            for _ in range(5):  # Retry up to 5 times
                detector_raw = call_tool(DETECTOR_NAME, detector_args)
                llm_calls += 1
                detector_res = _parse_json(detector_raw)
                if detector_res and "relationships" in detector_res:
                    break

            processed_pairs += len(other_tools_list)

            relationships = detector_res.get("relationships", [])
            if not isinstance(relationships, list):
                relationships = []

            print(
                f"Tool A: {tool_a['name']} vs {len(other_tools_list)} others => Found {len(relationships)} relationships"
            )

            for rel in relationships:
                tool_b_name = rel.get("tool_b_name")
                direction = rel.get("direction")
                rationale = rel.get("rationale")

                if not tool_b_name or tool_b_name not in minimal_tool_map:
                    continue

                if direction in ("A->B", "both"):
                    edges.append(
                        {
                            "source": tool_a["name"],
                            "target": tool_b_name,
                            "rationale": rationale,
                        }
                    )
                if direction in ("B->A", "both"):
                    edges.append(
                        {
                            "source": tool_b_name,
                            "target": tool_a["name"],
                            "rationale": rationale,
                        }
                    )

            # Progress reporting and checkpointing
            if processed_pairs % 1000 < len(
                other_tools_list
            ):  # Heuristic to report near the thousand marks
                elapsed = time.time() - start_time
                rate = processed_pairs / elapsed if elapsed > 0 else 0
                print(
                    f"[progress] pairs={processed_pairs}/{total_pairs} edges={len(edges)} llm_calls={llm_calls} rate={rate:.2f} pairs/s"
                )
            if (
                processed_pairs // checkpoint_every
                > (processed_pairs - len(other_tools_list)) // checkpoint_every
            ):
                _maybe_checkpoint(output_path, nodes, edges)

    graph = {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "tools": n,
            "pairs_evaluated": processed_pairs,
            "edges": len(edges),
            "llm_calls": llm_calls,
            "runtime_sec": round(time.time() - start_time, 2),
        },
    }

    # Final save
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to write output: {e}",
            "graph": graph,
        }

    return {"status": "success", "output_file": output_path, "graph": graph}


def _maybe_checkpoint(base_path: str, nodes: List[dict], edges: List[dict]):
    ck_path = base_path + ".checkpoint_new.json"
    try:
        with open(ck_path, "w", encoding="utf-8") as f:
            json.dump({"nodes": nodes, "edges": edges}, f)
        print(f"[checkpoint] saved {ck_path} nodes={len(nodes)} edges={len(edges)}")
    except Exception as e:
        print(f"[checkpoint] failed: {e}")


def _parse_json(obj: Any) -> dict:
    if isinstance(obj, dict):
        # may be wrapped
        if "result" in obj and isinstance(obj["result"], str):
            try:
                return json.loads(obj["result"])
            except Exception:
                return {}
        if "content" in obj and isinstance(obj["content"], str):
            try:
                return json.loads(obj["content"])
            except Exception:
                return {}
        return obj
    if isinstance(obj, str):
        try:
            return json.loads(obj)
        except Exception:
            return {}
    return {}
