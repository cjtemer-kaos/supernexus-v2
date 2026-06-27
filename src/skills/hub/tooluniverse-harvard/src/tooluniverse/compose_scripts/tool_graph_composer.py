"""
Simplified and fixed tool_graph_composer.py
This version includes better error handling and avoids the 'unhashable type' issue.
"""

import json
import os
import pickle
from datetime import datetime


def compose(arguments, tooluniverse, call_tool):
    """
    Compose function for building tool compatibility graphs.

    Args:
        arguments: Dictionary with composition parameters
        tooluniverse: ToolUniverse instance
        call_tool: Function to call other tools

    Returns
        Dictionary with results and file paths
    """
    try:
        # Extract arguments with defaults
        output_path = arguments.get("output_path", "./tool_composition_graph")
        analysis_depth = arguments.get("analysis_depth", "detailed")
        min_compatibility_score = arguments.get("min_compatibility_score", 60)
        exclude_categories = arguments.get(
            "exclude_categories", ["tool_finder", "special_tools"]
        )
        max_tools_per_category = arguments.get("max_tools_per_category", 50)
        force_rebuild = arguments.get("force_rebuild", False)

        print(f"Starting tool graph composition with {analysis_depth} analysis...")

        # Check for existing graph
        cache_path = f"{output_path}_cache.pkl"
        if not force_rebuild and os.path.exists(cache_path):
            print("Loading cached graph...")
            return _load_cached_graph(cache_path, output_path)

        # Load all available tools
        tools = _load_all_tools(
            tooluniverse, exclude_categories, max_tools_per_category
        )
        print(f"Loaded {len(tools)} tools for analysis")

        if len(tools) == 0:
            return {
                "status": "error",
                "message": "No tools available for analysis after filtering",
                "tools_analyzed": 0,
                "edges_created": 0,
            }

        # Build the graph
        graph_data = _build_compatibility_graph(
            tools, analysis_depth, min_compatibility_score, call_tool
        )

        # Save the graph
        output_files = _save_graph(graph_data, output_path)

        # Cache the results
        cache_data = {
            "graph_data": graph_data,
            "output_files": output_files,
            "creation_time": datetime.now().isoformat(),
        }

        try:
            with open(cache_path, "wb") as f:
                pickle.dump(cache_data, f)
            print(f"Cached results to: {cache_path}")
        except Exception as e:
            print(f"Warning: Could not cache results: {e}")

        # Generate statistics
        stats = _generate_graph_stats(graph_data)

        # Prepare result
        result = {
            "status": "success",
            "graph_files": output_files,
            "statistics": stats,
            "tools_analyzed": len(tools),
            "edges_created": len(graph_data.get("edges", [])),
            "timestamp": datetime.now().isoformat(),
        }

        print("Tool graph composition completed successfully!")
        return result

    except Exception as e:
        print(f"Error in tool graph composition: {e}")
        import traceback

        traceback.print_exc()

        return {
            "status": "error",
            "message": str(e),
            "tools_analyzed": 0,
            "edges_created": 0,
            "timestamp": datetime.now().isoformat(),
        }


def _load_all_tools(tooluniverse, exclude_categories, max_per_category):
    """Load all available tools from ToolUniverse."""

    all_tools = []
    exclude_set = set(exclude_categories)  # Convert to set for faster lookup

    # Get all tools from ToolUniverse using all_tool_dict directly
    # Group tools by category based on their configuration
    tools_by_category = {}

    for tool_name, tool_config in tooluniverse.all_tool_dict.items():
        # Skip if tool_name is not a string (defensive programming)
        if not isinstance(tool_name, str):
            print(f"Skipping non-string tool name: {tool_name}")
            continue

        # Try to determine category from various sources
        category = "unknown"

        # Check if category is specified in tool config
        if isinstance(tool_config, dict) and "category" in tool_config:
            category = tool_config["category"]
        else:
            # Try to find category from tool_category_dicts
            for cat_name, tools_in_cat in tooluniverse.tool_category_dicts.items():
                if tool_name in tools_in_cat:
                    category = cat_name
                    break

        # Initialize category if not exists
        if category not in tools_by_category:
            tools_by_category[category] = []

        tools_by_category[category].append((tool_name, tool_config))

    # Process each category
    for category, category_tools in tools_by_category.items():
        # Skip excluded categories
        if category in exclude_set:
            print(f"Skipping category: {category}")
            continue

        # Limit tools per category for performance
        if len(category_tools) > max_per_category:
            category_tools = category_tools[:max_per_category]
            print(f"Limited {category} to {max_per_category} tools")

        # Add category information and convert to list format
        for tool_name, tool_config in category_tools:
            # Create a copy to avoid modifying the original
            if isinstance(tool_config, dict):
                tool_config = dict(tool_config)
            else:
                tool_config = {
                    "name": tool_name,
                    "description": "No description available",
                }

            tool_config["category"] = category
            tool_config["name"] = tool_name  # Ensure name is set
            all_tools.append(tool_config)

        print(f"Loaded {len(category_tools)} tools from {category}")

    return all_tools


def _build_compatibility_graph(tools, analysis_depth, min_score, call_tool):
    """Build the compatibility graph by analyzing tool pairs."""

    # Initialize graph data structure
    graph_data = {
        "nodes": [],
        "edges": [],
        "metadata": {
            "analysis_depth": analysis_depth,
            "min_compatibility_score": min_score,
            "creation_time": datetime.now().isoformat(),
            "total_tools": len(tools),
        },
    }

    # Add nodes (tools)
    for i, tool in enumerate(tools):
        node_data = {
            "id": tool.get("name", f"tool_{i}"),
            "name": tool.get("name", f"tool_{i}"),
            "type": tool.get("type", "unknown"),
            "description": tool.get("description", ""),
            "category": tool.get("category", "unknown"),
            "parameters": tool.get("parameter", {}),
        }
        graph_data["nodes"].append(node_data)

    # Analyze tool pairs for compatibility (limited for demo)
    total_pairs = min(len(tools) * (len(tools) - 1), 100)  # Limit for demo
    analyzed_pairs = 0

    print(f"Analyzing up to {total_pairs} tool pairs...")

    for i, source_tool in enumerate(tools):
        for j, target_tool in enumerate(tools):
            if i == j:  # Skip self-loops
                continue

            analyzed_pairs += 1
            if analyzed_pairs > total_pairs:
                print("Reached analysis limit for demo")
                break

            if analyzed_pairs % 10 == 0:
                progress = (analyzed_pairs / total_pairs) * 100
                print(f"Progress: {analyzed_pairs}/{total_pairs} ({progress:.1f}%)")

            try:
                # Create safe tool specifications for analysis
                source_spec = {
                    "name": source_tool.get("name", f"tool_{i}"),
                    "type": source_tool.get("type", "unknown"),
                    "description": source_tool.get("description", ""),
                    "parameter": source_tool.get("parameter", {}),
                }

                target_spec = {
                    "name": target_tool.get("name", f"tool_{j}"),
                    "type": target_tool.get("type", "unknown"),
                    "description": target_tool.get("description", ""),
                    "parameter": target_tool.get("parameter", {}),
                }

                # Analyze compatibility using the ToolCompatibilityAnalyzer
                compatibility_result = call_tool(
                    "ToolCompatibilityAnalyzer",
                    {
                        "source_tool": json.dumps(source_spec),
                        "target_tool": json.dumps(target_spec),
                        "analysis_depth": analysis_depth,
                    },
                )

                # Extract compatibility information from the analysis result
                compatibility_info = _extract_compatibility_info(compatibility_result)
                score = compatibility_info.get("compatibility_score", 0)

                # Create edge if compatibility score meets threshold
                if score >= min_score:
                    edge_data = {
                        "source": source_spec["name"],
                        "target": target_spec["name"],
                        "compatibility_score": score,
                        "confidence": compatibility_info.get("confidence", score),
                        "is_compatible": compatibility_info.get("is_compatible", False),
                        "automation_ready": compatibility_info.get(
                            "automation_ready", False
                        ),
                        "analysis_summary": str(compatibility_result)[
                            :500
                        ],  # Truncate for storage
                    }
                    graph_data["edges"].append(edge_data)

            except Exception as e:
                print(
                    f"Error analyzing {source_tool.get('name', 'unknown')} -> {target_tool.get('name', 'unknown')}: {e}"
                )
                continue

        if analyzed_pairs > total_pairs:
            break

    print(
        f"Created {len(graph_data['edges'])} compatible edges from {analyzed_pairs} analyzed pairs"
    )
    return graph_data


def _extract_compatibility_info(analysis_result):
    """Extract structured compatibility information from analysis result."""

    # Handle different result formats
    if isinstance(analysis_result, list) and len(analysis_result) > 0:
        analysis_result = analysis_result[0]

    # Convert result to string for analysis
    if isinstance(analysis_result, dict):
        if "content" in analysis_result:
            analysis_text = analysis_result["content"]
        elif "result" in analysis_result:
            analysis_text = analysis_result["result"]
        else:
            analysis_text = str(analysis_result)
    else:
        analysis_text = str(analysis_result)

    # Basic parsing to extract key information
    compatibility_score = 50  # Default moderate score
    is_compatible = False
    confidence = 50

    # Simple text analysis to determine compatibility
    analysis_lower = analysis_text.lower()

    # Look for compatibility indicators
    if "highly compatible" in analysis_lower:
        compatibility_score = 85
        is_compatible = True
        confidence = 90
    elif "compatible" in analysis_lower and "incompatible" not in analysis_lower:
        compatibility_score = 70
        is_compatible = True
        confidence = 75
    elif "partially compatible" in analysis_lower:
        compatibility_score = 60
        is_compatible = True
        confidence = 60
    elif "incompatible" in analysis_lower:
        compatibility_score = 20
        is_compatible = False
        confidence = 80

    # Look for automation indicators
    automation_ready = "automatic" in analysis_lower or "direct" in analysis_lower

    return {
        "compatibility_score": compatibility_score,
        "is_compatible": is_compatible,
        "confidence": confidence,
        "automation_ready": automation_ready,
    }


def _save_graph(graph_data, output_path):
    """Save the graph in multiple formats."""

    output_files = {}

    try:
        # Save as JSON
        json_path = f"{output_path}.json"
        with open(json_path, "w") as f:
            json.dump(graph_data, f, indent=2)
        output_files["json"] = json_path
        print(f"Saved JSON graph: {json_path}")

        # Save as pickle for Python use
        pickle_path = f"{output_path}.pkl"
        with open(pickle_path, "wb") as f:
            pickle.dump(graph_data, f)
        output_files["pickle"] = pickle_path
        print(f"Saved pickle graph: {pickle_path}")

    except Exception as e:
        print(f"Error saving graph: {e}")
        raise e

    return output_files


def _generate_graph_stats(graph_data):
    """Generate statistics about the graph."""

    try:
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        total_nodes = len(nodes)
        total_edges = len(edges)

        # Calculate edge density
        max_possible_edges = total_nodes * (total_nodes - 1) if total_nodes > 1 else 1
        edge_density = total_edges / max_possible_edges if max_possible_edges > 0 else 0

        # Calculate compatibility score statistics
        scores = [edge.get("compatibility_score", 0) for edge in edges]
        avg_score = sum(scores) / len(scores) if scores else 0
        high_score_edges = len([s for s in scores if s >= 80])

        # Calculate automation readiness
        automation_ready_edges = len(
            [e for e in edges if e.get("automation_ready", False)]
        )
        automation_percentage = (
            (automation_ready_edges / total_edges * 100) if total_edges > 0 else 0
        )

        # Category distribution
        categories = {}
        for node in nodes:
            cat = node.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "edge_density": edge_density,
            "compatibility_scores": {
                "average": avg_score,
                "count_high": high_score_edges,
            },
            "automation_ready_percentage": automation_percentage,
            "categories": categories,
        }

    except Exception as e:
        print(f"Error generating stats: {e}")
        return {
            "total_nodes": len(graph_data.get("nodes", [])),
            "total_edges": len(graph_data.get("edges", [])),
            "error": str(e),
        }


def _load_cached_graph(cache_path, output_path):
    """Load a previously cached graph."""

    try:
        with open(cache_path, "rb") as f:
            cache_data = pickle.load(f)

        graph_data = cache_data["graph_data"]
        output_files = cache_data["output_files"]

        # Generate fresh stats
        stats = _generate_graph_stats(graph_data)

        return {
            "status": "loaded_from_cache",
            "graph_files": output_files,
            "statistics": stats,
            "tools_analyzed": graph_data["metadata"]["total_tools"],
            "edges_created": len(graph_data["edges"]),
            "timestamp": cache_data["creation_time"],
            "cache_loaded": True,
        }

    except Exception as e:
        print(f"Error loading cached graph: {e}")
        # Return error status to trigger rebuild
        raise e
