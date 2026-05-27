#!/usr/bin/env python3
"""
Basic test for list_built_in_tools including scan_all option.
Run directly: python tests/test_list_built_in_tools.py
"""

from tooluniverse import ToolUniverse  # noqa: E402


def main():
    tu = ToolUniverse()

    # Use predefined files (original behavior)
    tool_names = tu.list_built_in_tools(mode="list_name", scan_all=False)
    print(f"predefined tool names: {len(tool_names)}")

    # Scan all JSON files
    all_tool_names = tu.list_built_in_tools(mode="list_name", scan_all=True)
    print(f"all tool names (scan_all): {len(all_tool_names)}")

    # Get all tool specifications
    all_tool_specs = tu.list_built_in_tools(mode="list_spec", scan_all=True)
    print(f"all tool specs (scan_all): {len(all_tool_specs)}")

    # Organize all tools by type
    type_stats = tu.list_built_in_tools(mode="type", scan_all=True)
    print(
        f"type stats -> total_categories: {type_stats['total_categories']}, total_tools: {type_stats['total_tools']}"
    )


if __name__ == "__main__":
    main()
