from tooluniverse import ToolUniverse

# Step 1: Initialize tool universe
tooluni = ToolUniverse()
tooluni.load_tools()

test_queries = [
    {
        "name": "humanbase_ppi_analysis",
        "arguments": {"gene_list": ["TP53", "USP7"], "tissue": "brain"},
    },
]

for idx, query in enumerate(test_queries):
    print(
        f"\n[{idx+1}] Running tool: {query['name']} with arguments: {query['arguments']}"
    )
    result = tooluni.run(query)
    print("✅ Success. Example output snippet:")
    print(result if isinstance(result, dict) else str(result))
