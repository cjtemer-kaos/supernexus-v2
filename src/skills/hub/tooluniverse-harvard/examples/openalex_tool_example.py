# === openfda_test_all_tools.py ===

from tooluniverse import ToolUniverse

# Step 1: Initialize tool universe
tooluni = ToolUniverse()
tooluni.load_tools()

# Step 2: Define test queries for the openalex tool
test_queries = [
    {
        "name": "openalex_literature_search",
        "arguments": {
            "search_keywords": "cancer",
            "max_results": 10,
            "year_from": 2020,
            "year_to": 2023,
            "open_access": True,
        },
    },
]

# Step 3: Run all test queries
for idx, query in enumerate(test_queries):
    print(
        f"\n[{idx+1}] Running tool: {query['name']} with arguments: {query['arguments']}"
    )
    result = tooluni.run(query)
    print("✅ Success. Example output snippet:")
    print(
        result if isinstance(result, dict) else str(result)
    )  # Print snippet if result is big
