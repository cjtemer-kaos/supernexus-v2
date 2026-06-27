# test_go.py

from tooluniverse import (
    ToolUniverse,
)  # Assuming your ToolUniverse class is in this module
from typing import Any, Dict, List

# Step 1: Initialize ToolUniverse and load the GO tools
tooluni = ToolUniverse()
# This assumes your ToolUniverse is configured to find 'go_tools.json'
# when the 'go' category is requested.
tooluni.load_tools(["go"])

# Test GO ID for cell cycle process
TEST_GO_ID = "GO:0007049"  # cell cycle
TEST_GENE_NAME = "TP53"  # TP53 gene

test_queries: List[Dict[str, Any]] = [
    {"name": "GO_search_terms", "arguments": {"query": "cell cycle"}},
    {"name": "GO_get_term_by_id", "arguments": {"id": TEST_GO_ID}},
    {"name": "GO_get_term_details", "arguments": {"id": TEST_GO_ID}},
    {"name": "GO_get_genes_for_term", "arguments": {"id": TEST_GO_ID, "rows": 5}},
    {"name": "GO_get_annotations_for_gene", "arguments": {"gene_id": TEST_GENE_NAME}},
]


def format_value(value, max_items=5, max_length=200):
    """Helper function to format output values with more detail"""
    if isinstance(value, dict):
        dict_str = str(value)
        return f"Dict ({len(dict_str)} chars): {dict_str[:500]}{'...' if len(dict_str) > 500 else ''}"
    elif isinstance(value, list):
        if not value:
            return "Empty list"
        items_to_show = value[:max_items]
        items_str = "\n  - ".join(
            [
                str(item)[:max_length] + ("..." if len(str(item)) > max_length else "")
                for item in items_to_show
            ]
        )
        remaining = len(value) - max_items
        return f"List with {len(value)} items:\n  - {items_str}" + (
            f"\n  ... and {remaining} more items" if remaining > 0 else ""
        )
    elif isinstance(value, str):
        return f"String ({len(value)} chars): {value[:max_length]}{'...' if len(value) > max_length else ''}"
    else:
        return f"Type: {type(value)}, Value: {value}"


print("--- Starting Gene Ontology (GO) Tool Test ---")

for idx, q in enumerate(test_queries, 1):
    print(
        f"\n{'='*80}\n[{idx}] {q['name']}({', '.join([f'{k}={v}' for k, v in q['arguments'].items()])})"
    )
    res = tooluni.run(q)

    if isinstance(res, dict) and "error" in res:
        print(f"ERROR: {res['error']}")
    else:
        print(format_value(res))
    print()

print("\n--- GO Tool Test Completed ---")
