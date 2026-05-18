from tooluniverse import ToolUniverse

# Step 1: Initialize tool universe and load available tools
tooluni = ToolUniverse()
tooluni.load_tools()

# Define test queries based on the updated pubtator_tools.json
test_queries = [
    {
        "name": "PubTator3_EntityAutocomplete",
        "arguments": {"text": "BRAF", "entity_type": "GENE", "max_results": 5},
    },
    {
        "name": "PubTator3_EntityAutocomplete",
        "arguments": {"text": "TP53"},  # only required parameter
    },
    {
        "name": "PubTator3_LiteratureSearch",
        "arguments": {"query_text": "cancer", "page": 0, "page_size": 10},
    },
    {
        "name": "PubTator3_LiteratureSearch",
        "arguments": {"query_text": "diabetes"},  # minimal required args
    },
]

# Run individual test queries
for idx, query in enumerate(test_queries):
    try:
        print(
            f"\n[{idx+1}] Running tool: {query['name']} with arguments: {query['arguments']}"
        )
        result = tooluni.run(query)
        print("✅ Success. Output snippet:")
        print(result if isinstance(result, dict) else str(result)[:500])
    except Exception as e:
        print(f"❌ Failed running {query['name']}. Error: {e}")
