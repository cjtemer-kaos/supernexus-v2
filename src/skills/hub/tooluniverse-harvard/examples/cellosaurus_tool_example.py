# === cellosaurus_tool_example.py ===
# Demo usage of three Cellosaurus tools via ToolUniverse

from tooluniverse import ToolUniverse


def main():
    tu = ToolUniverse()
    # Load default tool categories; includes "cellosaurus" via default_config
    tu.load_tools()

    example_queries = [
        {
            "name": "cellosaurus_search_cell_lines",
            "arguments": {"q": "ox:9606 AND char:cancer", "size": 3},
        },
        {
            "name": "cellosaurus_query_converter",
            "arguments": {"query": "human cancer cells", "include_explanation": True},
        },
        {
            "name": "cellosaurus_get_cell_line_info",
            "arguments": {"accession": "CVCL_0030", "format": "json", "fields": ["id", "ox", "char"]},
        },
    ]

    for i, q in enumerate(example_queries, 1):
        print(f"\n[{i}] Running tool: {q['name']} with arguments: {q['arguments']}")
        try:
            res = tu.run(q)
            print("✅ Success. Output snippet:")
            print(res if isinstance(res, dict) else str(res))
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
