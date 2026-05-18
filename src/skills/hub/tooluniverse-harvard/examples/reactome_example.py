# test_reactome.py

from tooluniverse import ToolUniverse

# Step 1: Initialize ToolUniverse and load all tools (including Reactome tools)
tooluni = ToolUniverse()
tooluni.load_tools()

# Step 2: Define some IDs that are valid in Content Service
VALID_PATHWAY_FOR_REACTIONS = (
    "R-HSA-73817"  # This ID returns reactions, but info and participants will 404
)

# Step 3: Define test queries for Reactome tools
test_queries = [
    # 3. Get all Reactions under a Pathway (using verified valid ID)
    {
        "name": "Reactome_get_pathway_reactions",
        "arguments": {"stId": VALID_PATHWAY_FOR_REACTIONS},
    },
]

# Step 4: Run all test queries
for idx, query in enumerate(test_queries):
    print(
        f"\n[{idx+1}] Running tool: {query['name']} with arguments: {query['arguments']}"
    )
    result = tooluni.run(query)

    # If result contains "error" key, consider it as "server error", print and continue to next
    if isinstance(result, dict) and "error" in result:
        print("⚠️ Received error response:")
        print(result)
        continue

    # Otherwise treat as "normal response", print example output
    print("✅ Success. Example output snippet:")
    if isinstance(result, list):
        print(f"List with {len(result)} items, example first item:")
        print(result[0])
    elif isinstance(result, dict):
        print("Returned dictionary, example first 3 key-value pairs:")
        count = 0
        for k, v in result.items():
            print(f"  {k}: {v}")
            count += 1
            if count >= 3:
                break
    else:
        # If result is None or other type, print repr directly
        s = repr(result)
        print(s if len(s) <= 200 else s[:200] + "…")

print("\n🎉 Reactome testing completed!")
