#!/usr/bin/env python3
"""
Tool Graph Generator Script

This script generates a compatibility graph for all tools in ToolUniverse.
It uses the ToolCompatibilityAnalyzer and ToolGraphComposer to analyze tool relationships.

Usage:
    python generate_tool_graph.py [options]

Examples:
    # Quick analysis with limited tools
    python generate_tool_graph.py --quick --max-tools 5

    # Detailed analysis of specific categories
    python generate_tool_graph.py --categories pubchem,chembl --analysis-depth detailed

    # Full comprehensive analysis (may take hours)
    python generate_tool_graph.py --analysis-depth comprehensive --force-rebuild
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directories to path for imports
script_dir = Path(__file__).parent
tooluniverse_dir = script_dir.parent
src_dir = tooluniverse_dir.parent
sys.path.insert(0, str(src_dir))

from tooluniverse import ToolUniverse  # noqa: E402


def parse_arguments():
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(
        description="Generate tool compatibility graph for ToolUniverse",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --quick --max-tools 10
  %(prog)s --categories pubchem,chembl,europepmc
  %(prog)s --analysis-depth comprehensive --output ./full_graph
  %(prog)s --force-rebuild --min-score 80
        """,
    )

    # Output options
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="./tool_composition_graph",
        help="Output path for graph files (default: ./tool_composition_graph)",
    )

    parser.add_argument(
        "--force-rebuild",
        "-f",
        action="store_true",
        help="Force rebuild even if cached graph exists",
    )

    # Analysis options
    parser.add_argument(
        "--analysis-depth",
        "-d",
        choices=["quick", "detailed", "comprehensive"],
        default="detailed",
        help="Analysis depth (default: detailed)",
    )

    parser.add_argument(
        "--min-score",
        "-s",
        type=int,
        default=60,
        help="Minimum compatibility score for edges (0-100, default: 60)",
    )

    # Tool selection options
    parser.add_argument(
        "--categories",
        "-c",
        type=str,
        help="Comma-separated list of tool categories to include (e.g., 'pubchem,chembl')",
    )

    parser.add_argument(
        "--exclude-categories",
        "-e",
        type=str,
        default="tool_finder,special_tools",
        help="Comma-separated list of categories to exclude (default: tool_finder,special_tools)",
    )

    parser.add_argument(
        "--max-tools",
        "-m",
        type=int,
        default=50,
        help="Maximum tools per category (default: 50)",
    )

    # Convenience options
    parser.add_argument(
        "--quick",
        "-q",
        action="store_true",
        help="Quick mode: use quick analysis and limit to 10 tools per category",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be analyzed without actually running",
    )

    return parser.parse_args()


def setup_analysis_parameters(args):
    """Setup analysis parameters based on arguments."""

    # Handle quick mode
    if args.quick:
        analysis_depth = "quick"
        max_tools = 10
        min_score = 70  # Higher threshold for quick mode
    else:
        analysis_depth = args.analysis_depth
        max_tools = args.max_tools
        min_score = args.min_score

    # Handle category selection
    if args.categories:
        include_categories = [cat.strip() for cat in args.categories.split(",")]
        exclude_categories = []
    else:
        include_categories = None
        exclude_categories = [cat.strip() for cat in args.exclude_categories.split(",")]

    return {
        "output_path": args.output,
        "analysis_depth": analysis_depth,
        "min_compatibility_score": min_score,
        "exclude_categories": exclude_categories,
        "include_categories": include_categories,
        "max_tools_per_category": max_tools,
        "force_rebuild": args.force_rebuild,
    }


def preview_analysis(tooluniverse, parameters):
    """Show what tools would be analyzed without running the analysis."""

    print("Analysis Preview")
    print("=" * 50)
    print(f"Analysis Depth: {parameters['analysis_depth']}")
    print(f"Min Compatibility Score: {parameters['min_compatibility_score']}")
    print(f"Max Tools per Category: {parameters['max_tools_per_category']}")
    print(f"Output Path: {parameters['output_path']}")
    print()

    # Show categories and tool counts
    categories = tooluniverse.tool_category_dicts
    exclude_set = set(parameters.get("exclude_categories", []))
    include_set = (
        set(parameters.get("include_categories", []))
        if parameters.get("include_categories")
        else None
    )

    total_tools = 0
    selected_categories = []

    for category, tools in categories.items():
        # Apply category filtering
        if include_set and category not in include_set:
            continue
        if category in exclude_set:
            continue

        tool_count = min(len(tools), parameters["max_tools_per_category"])
        total_tools += tool_count
        selected_categories.append((category, tool_count, len(tools)))

    print("Selected Categories:")
    for category, selected_count, total_count in selected_categories:
        status = (
            f"({selected_count}/{total_count})"
            if selected_count < total_count
            else f"({total_count})"
        )
        print(f"  {category}: {status}")

    print(f"\nTotal tools to analyze: {total_tools}")
    print(f"Estimated tool pairs: {total_tools * (total_tools - 1)}")

    # Time estimates
    if parameters["analysis_depth"] == "quick":
        est_time_per_pair = 2  # seconds
    elif parameters["analysis_depth"] == "detailed":
        est_time_per_pair = 5  # seconds
    else:  # comprehensive
        est_time_per_pair = 10  # seconds

    total_pairs = total_tools * (total_tools - 1)
    est_total_time = total_pairs * est_time_per_pair

    print("\nEstimated Analysis Time:")
    print(f"  Per pair: ~{est_time_per_pair} seconds")
    print(f"  Total: ~{est_total_time // 3600}h {(est_total_time % 3600) // 60}m")

    return total_tools > 0


def run_graph_generation(tooluniverse, parameters, verbose=False):
    """Run the graph generation process."""

    print("Starting Tool Graph Generation")
    print("=" * 50)

    start_time = time.time()

    try:
        # Prepare arguments for ToolGraphComposer
        composer_args = {
            "output_path": parameters["output_path"],
            "analysis_depth": parameters["analysis_depth"],
            "min_compatibility_score": parameters["min_compatibility_score"],
            "exclude_categories": parameters["exclude_categories"],
            "max_tools_per_category": parameters["max_tools_per_category"],
            "force_rebuild": parameters["force_rebuild"],
        }

        # Add include_categories if specified
        if parameters.get("include_categories"):
            # For include_categories, we need to modify exclude_categories
            all_categories = set(tooluniverse.tool_category_dicts.keys())
            include_set = set(parameters["include_categories"])
            composer_args["exclude_categories"] = list(all_categories - include_set)

        if verbose:
            print("Composer arguments:")
            print(json.dumps(composer_args, indent=2))
            print()

        # Run the composition
        result = tooluniverse.run(
            json.dumps([{"name": "ToolGraphComposer", "arguments": composer_args}])
        )

        # Handle result formatting
        if isinstance(result, list) and len(result) > 0:
            result = result[0]

        end_time = time.time()
        duration = end_time - start_time

        # Display results
        print("Graph Generation Complete!")
        print("-" * 30)
        print(
            f"Duration: {duration // 3600:.0f}h {(duration % 3600) // 60:.0f}m {duration % 60:.1f}s"
        )

        if isinstance(result, dict):
            if result.get("status") == "success":
                print("✅ Status: Success")

                # Show files created
                if "graph_files" in result:
                    print("\nGenerated Files:")
                    for format_type, file_path in result["graph_files"].items():
                        if os.path.exists(file_path):
                            file_size = os.path.getsize(file_path)
                            print(
                                f"  {format_type.upper()}: {file_path} ({file_size:,} bytes)"
                            )

                # Show statistics
                if "statistics" in result:
                    stats = result["statistics"]
                    print("\nGraph Statistics:")
                    print(f"  Tools Analyzed: {result.get('tools_analyzed', 'N/A')}")
                    print(f"  Nodes: {stats.get('total_nodes', 'N/A')}")
                    print(f"  Edges: {stats.get('total_edges', 'N/A')}")
                    print(f"  Edge Density: {stats.get('edge_density', 0):.3f}")

                    if "compatibility_scores" in stats:
                        scores = stats["compatibility_scores"]
                        print(
                            f"  Avg Compatibility Score: {scores.get('average', 0):.1f}"
                        )
                        print(f"  High-Quality Edges: {scores.get('count_high', 0)}")

                    if "automation_ready_percentage" in stats:
                        print(
                            f"  Automation Ready: {stats['automation_ready_percentage']:.1f}%"
                        )

                return True
            else:
                print("❌ Status: Failed")
                print(f"Error: {result.get('message', 'Unknown error')}")
                return False
        else:
            print("❌ Unexpected result format")
            print(result)
            return False

    except Exception as e:
        print(f"❌ Error during graph generation: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return False


def main():
    """Main function."""

    args = parse_arguments()

    print("ToolUniverse Graph Generator")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Initialize ToolUniverse
    if args.verbose:
        print("Initializing ToolUniverse...")

    try:
        tu = ToolUniverse()
        tu.load_tools()

        if args.verbose:
            print(f"Loaded {len(tu.all_tool_dict)} tools")
            print(f"Categories: {len(tu.tool_category_dicts)}")
            print()

    except Exception as e:
        print(f"❌ Failed to initialize ToolUniverse: {e}")
        return 1

    # Setup parameters
    parameters = setup_analysis_parameters(args)

    # Show preview
    if not preview_analysis(tu, parameters):
        print("❌ No tools selected for analysis. Check your category filters.")
        return 1

    # Dry run mode
    if args.dry_run:
        print(
            "\n✅ Dry run complete. Use --force-rebuild to actually generate the graph."
        )
        return 0

    # Confirmation for large analyses
    total_categories = len(
        [
            cat
            for cat in tu.tool_category_dicts.keys()
            if cat not in parameters.get("exclude_categories", [])
        ]
    )

    if (
        not args.quick
        and total_categories > 5
        and parameters["max_tools_per_category"] > 20
    ):
        response = input("\nThis may take a very long time. Continue? (y/N): ")
        if response.lower() != "y":
            print("Cancelled.")
            return 0

    print("\n" + "=" * 60)

    # Run the generation
    success = run_graph_generation(tu, parameters, verbose=args.verbose)

    if success:
        print("\n🎉 Graph generation completed successfully!")
        print(f"Files saved to: {parameters['output_path']}.*")
        print("\nTo visualize the graph, run:")
        print(f"python visualize_tool_graph.py {parameters['output_path']}.json")
        return 0
    else:
        print("\n❌ Graph generation failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
