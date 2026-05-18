from tooluniverse import ToolUniverse

# ...existing code to initialize the ToolUniverse...
tooluni = ToolUniverse()
tooluni.load_tools()

test_queries = [
    {
        "name": "SemanticScholar_search_papers",
        "arguments": {
            "query": "cancer immunotherapy",
            "limit": 3,
            # "api_key": "YOUR_API_KEY"  # Uncomment and add your API key if available
        },
    }
]

for idx, query in enumerate(test_queries):
    print(
        f"\n[{idx+1}] Running tool: {query['name']} with arguments: {query['arguments']}"
    )
    result = tooluni.run(query)
    print("✅ Success. Example output snippet:")
    print(result if isinstance(result, dict) else str(result))
